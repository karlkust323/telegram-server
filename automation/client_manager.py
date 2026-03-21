"""
client_manager.py
-----------------
TelegramClientManager: owns one or more Telethon TelegramClient instances,
handles authentication, session persistence, proxy configuration, and
clean shutdown.

Supports two configuration styles:
  1. Single account  -- api_id / api_hash / phone_number at the top level.
  2. Multiple accounts -- an ``accounts`` list, each with its own credentials.

Each account can optionally specify a ``proxy`` dict for SOCKS5/HTTP routing.
"""

from __future__ import annotations

import logging
from typing import Any

import socks  # PySocks -- required only when proxies are configured
from telethon import TelegramClient

logger = logging.getLogger(__name__)


def _parse_proxy(proxy_cfg: dict[str, Any] | None) -> tuple | None:
    """Convert a proxy config dict into the tuple Telethon expects.

    Expected dict format::

        proxy:
          type: socks5          # socks5 | socks4 | http
          host: "127.0.0.1"
          port: 9050
          username: ""          # optional
          password: ""          # optional

    Returns None when no proxy is configured.
    """
    if not proxy_cfg:
        return None

    proxy_types = {
        "socks5": socks.SOCKS5,
        "socks4": socks.SOCKS4,
        "http": socks.HTTP,
    }
    ptype = proxy_types.get(str(proxy_cfg.get("type", "socks5")).lower())
    if ptype is None:
        logger.warning("Unknown proxy type '%s' -- ignoring proxy", proxy_cfg.get("type"))
        return None

    host = str(proxy_cfg["host"])
    port = int(proxy_cfg["port"])
    username = proxy_cfg.get("username") or None
    password = proxy_cfg.get("password") or None

    # Telethon expects: (type, host, port, True, username, password)
    # The 4th element (rdns) tells PySocks to resolve DNS remotely.
    return (ptype, host, port, True, username, password)


class TelegramClientManager:
    """Manage the lifecycle of one or more Telethon client sessions.

    Parameters
    ----------
    config:
        Parsed YAML config dict.  Accepts either a single-account layout
        (api_id, api_hash, phone_number at top level) or a multi-account
        layout (an ``accounts`` list of dicts each containing those keys).
        Each account may include a ``proxy`` dict.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._accounts: list[dict[str, Any]] = self._parse_accounts(config)
        self._clients: list[TelegramClient] = []
        self._current_index: int = 0

    # -- internal helpers ------------------------------------------------------

    @staticmethod
    def _parse_accounts(config: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalise config into a list of account dicts."""
        if "accounts" in config and isinstance(config["accounts"], list):
            return config["accounts"]
        return [
            {
                "api_id": config["api_id"],
                "api_hash": config["api_hash"],
                "phone_number": config["phone_number"],
                "session_name": config.get("session_name", "telegram_session"),
                "proxy": config.get("proxy"),
            }
        ]

    # -- public API ------------------------------------------------------------

    @property
    def account_count(self) -> int:
        """How many accounts are configured."""
        return len(self._accounts)

    async def connect(self) -> None:
        """Create clients for every configured account and authenticate them."""
        for idx, acct in enumerate(self._accounts):
            api_id = int(acct["api_id"])
            api_hash = str(acct["api_hash"])
            phone = str(acct["phone_number"])
            session = acct.get("session_name", f"telegram_session_{idx}")
            proxy = _parse_proxy(acct.get("proxy"))

            if proxy:
                logger.info("Account %d: using proxy %s:%s", idx + 1, proxy[1], proxy[2])

            client = TelegramClient(session, api_id, api_hash, proxy=proxy)
            await client.connect()

            if not await client.is_user_authorized():
                logger.info(
                    "Account %d: session not authorised -- requesting login code for %s",
                    idx + 1,
                    phone,
                )
                await client.send_code_request(phone)
                code = input(f"Enter the code sent to {phone} (account {idx + 1}): ")
                await client.sign_in(phone, code)

            me = await client.get_me()
            logger.info(
                "Account %d: authenticated as %s (id=%s)",
                idx + 1,
                me.first_name,
                me.id,
            )
            self._clients.append(client)

        logger.info("All %d account(s) connected", len(self._clients))

    async def disconnect(self) -> None:
        """Gracefully close every client connection."""
        for client in self._clients:
            await client.disconnect()
        logger.info("All clients disconnected")

    def get_client(self) -> TelegramClient:
        """Return the *current* active TelegramClient."""
        if not self._clients:
            raise RuntimeError("No clients connected. Call connect() first.")
        return self._clients[self._current_index]

    def get_next_client(self) -> TelegramClient:
        """Rotate to the next account and return its client."""
        if not self._clients:
            raise RuntimeError("No clients connected. Call connect() first.")
        self._current_index = (self._current_index + 1) % len(self._clients)
        logger.info(
            "Rotated to account %d/%d",
            self._current_index + 1,
            len(self._clients),
        )
        return self._clients[self._current_index]

    def get_current_index(self) -> int:
        """Return the zero-based index of the currently active account."""
        return self._current_index
