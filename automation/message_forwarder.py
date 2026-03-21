"""
message_forwarder.py
--------------------
MessageForwarder: fetches messages from a source chat and re-posts
them (with metadata) into a target chat.  Supports resume, progress
tracking, and optional media forwarding.
"""

from __future__ import annotations

import logging
from typing import Any

from telethon import TelegramClient
from telethon.errors import (
    ChannelPrivateError,
    ChatWriteForbiddenError,
    FloodWaitError,
)
from telethon.tl.types import Message

from client_manager import TelegramClientManager
from progress_tracker import ProgressTracker
from resilience import ResilienceManager
from state_manager import StateManager

logger = logging.getLogger(__name__)


def _format_reactions(message: Message) -> str:
    """Build a human-readable reactions string, e.g. 'Reactions: 👍 5, ❤️ 3'.

    Returns an empty string when no reaction data is available.
    """
    if not getattr(message, "reactions", None):
        return ""
    results = getattr(message.reactions, "results", None)
    if not results:
        return ""

    parts: list[str] = []
    for r in results:
        emoji = getattr(r.reaction, "emoticon", None) or "?"
        count = r.count
        parts.append(f"{emoji} {count}")
    return "Reactions: " + ", ".join(parts)


class MessageForwarder:
    """Fetch messages from *source_chat* and post them into *target_chat*.

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
        self._forward_media: bool = config.get("forward_media", False)
        self._oldest_first: bool = config.get("oldest_first", True)
        self._resilience = ResilienceManager(
            delay_secs=config.get("delay_secs", 1.0),
            max_retries=config.get("max_retries", 3),
        )
        self._progress = ProgressTracker()
        self._state = StateManager(config.get("state_file", "state.json"))

    # -- data fetching ---------------------------------------------------------

    async def get_messages(self) -> list[Message]:
        """Fetch all messages from the source chat.

        If *oldest_first* is True the list is sorted oldest-to-newest.
        """
        logger.info("Fetching messages from %s ...", self._source)
        entity = await self._client.get_entity(self._source)

        messages: list[Message] = []
        async for msg in self._client.iter_messages(entity, limit=None):
            if isinstance(msg, Message):
                messages.append(msg)

        logger.info("Fetched %d messages from source", len(messages))

        if self._oldest_first:
            messages.sort(key=lambda m: m.id)

        return messages

    # -- forwarding logic ------------------------------------------------------

    async def forward_message(self, message: Message) -> bool:
        """Compose and send a single message into the target chat.

        Text messages are re-sent with metadata header.  Media is
        optionally downloaded and re-uploaded when *forward_media* is True.

        Returns True on success, False on skip/failure.
        """
        target_entity = await self._client.get_entity(self._target)

        # Build a metadata header for context.
        header_parts: list[str] = [
            f"[msg_id={message.id}]",
            f"[date={message.date.isoformat() if message.date else '?'}]",
        ]
        if message.sender_id:
            header_parts.append(f"[sender={message.sender_id}]")
        if getattr(message, "views", None):
            header_parts.append(f"[views={message.views}]")
        if getattr(message, "forwards", None):
            header_parts.append(f"[forwards={message.forwards}]")

        reactions_str = _format_reactions(message)
        if reactions_str:
            header_parts.append(f"[{reactions_str}]")

        if message.reply_to and getattr(message.reply_to, "reply_to_msg_id", None):
            header_parts.append(f"[reply_to={message.reply_to.reply_to_msg_id}]")

        header = " ".join(header_parts)
        body = message.text or ""
        full_text = f"{header}\n{body}".strip()

        async def _send() -> None:
            # If media forwarding is enabled and the message has media,
            # download it and re-upload to the target.
            if self._forward_media and message.media:
                file_path = await self._client.download_media(message)
                if file_path:
                    await self._client.send_file(
                        target_entity,
                        file_path,
                        caption=full_text,
                    )
                    return

            # Text-only (or media skipped).
            if full_text:
                await self._client.send_message(target_entity, full_text)

        try:
            await self._resilience.retry_with_backoff(_send)
            logger.info(
                "Forwarding message ID %d from %s to %s",
                message.id,
                self._source,
                self._target,
            )
            return True

        except ChatWriteForbiddenError:
            logger.error("No write permission in target chat %s", self._target)
            return False
        except ChannelPrivateError:
            logger.error("Cannot access target channel (private or banned)")
            return False
        except FloodWaitError as exc:
            await self._resilience.handle_flood_wait(exc)
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error("Error forwarding message %d: %s", message.id, exc)
            return False

    # -- main loop -------------------------------------------------------------

    async def run(self) -> None:
        """Execute the message-forwarding workflow with progress and resume."""
        logger.info(
            "Starting message forwarder for source %s -> target %s",
            self._source,
            self._target,
        )

        messages = await self.get_messages()
        if not messages:
            logger.info("No messages found in source chat -- nothing to do")
            return

        # Resume support: skip messages already processed in a prior run.
        last_processed_id: int | None = self._state.get("last_processed_message_id")
        skip = last_processed_id is not None

        forwarded_count = 0
        skipped_count = 0

        self._progress.start(total=len(messages), desc="Forwarding messages")

        for msg in messages:
            if skip:
                if msg.id == last_processed_id:
                    skip = False
                self._progress.update()
                continue

            # Skip empty service messages with no text and no media.
            if not msg.text and not msg.media:
                self._progress.update()
                skipped_count += 1
                continue

            success = await self.forward_message(msg)
            if success:
                forwarded_count += 1
            else:
                skipped_count += 1

            self._state.set("last_processed_message_id", msg.id)
            self._progress.update()

            await self._resilience.sleep_for()

        self._progress.close()
        logger.info(
            "Message forwarder finished: %d forwarded, %d skipped out of %d total",
            forwarded_count,
            skipped_count,
            len(messages),
        )
