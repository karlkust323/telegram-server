"""
member_adder.py
---------------
MemberAdder: fetches participants from a source group/channel and
adds them one-by-one to a target group/channel, with resilience,
rate-limiting, and resume support.
"""

from __future__ import annotations

import logging
from typing import Any

from telethon import TelegramClient
from telethon.errors import (
    ChatAdminRequiredError,
    ChannelPrivateError,
    FloodWaitError,
    UserAlreadyParticipantError,
    UserNotMutualContactError,
    UserPrivacyRestrictedError,
)
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import User

from client_manager import TelegramClientManager
from progress_tracker import ProgressTracker
from resilience import ResilienceManager
from state_manager import StateManager

logger = logging.getLogger(__name__)


class MemberAdder:
    """Scrape members from *source_chat* and add them to *target_chat*.

    Parameters
    ----------
    client_manager:
        An already-connected TelegramClientManager.
    config:
        Parsed configuration dict.
    """

    def __init__(self, client_manager: TelegramClientManager, config: dict[str, Any]) -> None:
        self._client: TelegramClient = client_manager.get_client()
        self._source = config["source_chat"]
        self._target = config["target_chat"]
        self._resilience = ResilienceManager(
            delay_secs=config.get("delay_secs", 1.0),
            max_retries=config.get("max_retries", 3),
        )
        self._progress = ProgressTracker()
        self._state = StateManager(config.get("state_file", "state.json"))

    # -- data fetching ---------------------------------------------------------

    async def get_participants(self) -> list[User]:
        """Fetch all participants from the source chat."""
        logger.info("Fetching participants from %s ...", self._source)
        entity = await self._client.get_entity(self._source)
        participants: list[User] = await self._client.get_participants(entity, aggressive=True)
        logger.info("Found %d participants in source", len(participants))
        return participants

    async def _get_target_user_ids(self) -> set[int]:
        """Return a set of user IDs already present in the target chat."""
        entity = await self._client.get_entity(self._target)
        members = await self._client.get_participants(entity, aggressive=True)
        return {m.id for m in members}

    # -- adding logic ----------------------------------------------------------

    async def add_user(self, user: User) -> bool:
        """Invite *user* into the target chat.

        Returns True on success, False if the user was skipped.
        """
        target_entity = await self._client.get_entity(self._target)

        async def _invite() -> None:
            await self._client(InviteToChannelRequest(target_entity, [user]))

        try:
            await self._resilience.retry_with_backoff(_invite)
            logger.info(
                "Added user %s (id=%d) to %s",
                user.first_name or user.username or "?",
                user.id,
                self._target,
            )
            return True

        except UserAlreadyParticipantError:
            logger.debug("User %d already in target -- skipping", user.id)
            return False
        except UserPrivacyRestrictedError:
            logger.warning("User %d has privacy restrictions -- skipping", user.id)
            return False
        except UserNotMutualContactError:
            logger.warning("User %d is not a mutual contact -- skipping", user.id)
            return False
        except ChatAdminRequiredError:
            logger.error("Admin rights required in target chat to add members")
            return False
        except ChannelPrivateError:
            logger.error("Cannot access the target channel (private or banned)")
            return False
        except FloodWaitError as exc:
            # If retry_with_backoff itself exhausted retries on flood, handle gracefully.
            await self._resilience.handle_flood_wait(exc)
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error adding user %d: %s", user.id, exc)
            return False

    # -- main loop -------------------------------------------------------------

    async def run(self) -> None:
        """Execute the member-addition workflow with progress and resume."""
        logger.info(
            "Starting member adder for source %s -> target %s",
            self._source,
            self._target,
        )

        participants = await self.get_participants()
        if not participants:
            logger.info("No participants found in source chat -- nothing to do")
            return

        # Determine which users are already in target to skip them.
        existing_ids = await self._get_target_user_ids()
        logger.info("%d users already in target -- will be skipped", len(existing_ids))

        # Resume support: skip users we have already processed in a prior run.
        last_processed_id: int | None = self._state.get("last_processed_user_id")
        skip = last_processed_id is not None

        added_count = 0
        skipped_count = 0

        self._progress.start(total=len(participants), desc="Adding members")

        for user in participants:
            # Fast-forward past already-processed users when resuming.
            if skip:
                if user.id == last_processed_id:
                    skip = False
                self._progress.update()
                continue

            # Skip bots and deleted accounts.
            if user.bot or user.deleted:
                self._progress.update()
                skipped_count += 1
                continue

            # Skip users already in the target.
            if user.id in existing_ids:
                self._progress.update()
                skipped_count += 1
                continue

            success = await self.add_user(user)
            if success:
                added_count += 1
            else:
                skipped_count += 1

            # Persist progress so we can resume later.
            self._state.set("last_processed_user_id", user.id)
            self._progress.update()

            # Rate-limit between additions.
            await self._resilience.sleep_for()

        self._progress.close()
        logger.info(
            "Member adder finished: %d added, %d skipped out of %d total",
            added_count,
            skipped_count,
            len(participants),
        )
