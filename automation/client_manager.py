"""
client_manager.py
-----------------
TelegramClientManager: owns the Telethon TelegramClient, handles
authentication (phone + code), session persistence, and clean shutdown.
"""

from __future__ import annotations

import logging
from typing import Any

from telethon import TelegramClient

logger = logging.getLogger(__name__)


class TelegramClientManager:
    """Manage the lifecycle of a single Telethon client session.

    Parameters
    ----------
    config:
        A dict-like object with at least *api_id*, *api_hash*,
        *phone_number*, and optionally *session_name*.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._api_id: int = int(config["api_id"])
        self._api_hash: str = str(config["api_hash"])
        self._phone: str = str(config["phone_number"])
        self._session: str = config.get("session_name", "telegram_session")
        self._client: TelegramClient | None = None

    # -- public API ------------------------------------------------------------

    async def connect(self) -> None:
        """Create the client, connect, and authenticate if necessary.

        On first run (no .session file) the user will be prompted for
        the login code sent via Telegram.
        """
        self._client = TelegramClient(self._session, self._api_id, self._api_hash)
        await self._client.connect()

        if not await self._client.is_user_authorized():
            logger.info("Session not authorised -- requesting login code for %s", self._phone)
            await self._client.send_code_request(self._phone)
            code = input(f"Enter the code sent to {self._phone}: ")
            await self._client.sign_in(self._phone, code)

        me = await self._client.get_me()
        logger.info("Authenticated as %s (id=%s)", me.first_name, me.id)

    async def disconnect(self) -> None:
        """Gracefully close the connection."""
        if self._client is not None:
            await self._client.disconnect()
            logger.info("Client disconnected")

    def get_client(self) -> TelegramClient:
        """Return the underlying TelegramClient instance.

        Raises RuntimeError if *connect()* has not been called yet.
        """
        if self._client is None:
            raise RuntimeError("Client not connected. Call connect() first.")
        return self._client
