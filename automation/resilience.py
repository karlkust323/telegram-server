"""
resilience.py
-------------
ResilienceManager: handles rate-limiting, FloodWaitError sleeps,
and generic retry-with-backoff logic for all Telethon operations.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine, TypeVar

from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ResilienceManager:
    """Centralised resilience logic shared by MemberAdder and MessageForwarder."""

    def __init__(self, delay_secs: float = 1.0, max_retries: int = 3) -> None:
        self.delay_secs = delay_secs
        self.max_retries = max_retries

    # -- helpers ---------------------------------------------------------------

    async def sleep_for(self, delay: float | None = None) -> None:
        """Respectful sleep between consecutive API calls.

        Uses the configured *delay_secs* when no explicit delay is given.
        """
        actual = delay if delay is not None else self.delay_secs
        if actual > 0:
            await asyncio.sleep(actual)

    async def handle_flood_wait(self, error: FloodWaitError) -> None:
        """Parse the wait duration from a FloodWaitError and sleep it out."""
        wait_seconds: int = error.seconds
        logger.warning(
            "Encountered FloodWaitError: sleeping for %d seconds", wait_seconds
        )
        await asyncio.sleep(wait_seconds)

    async def retry_with_backoff(
        self,
        fn: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        max_retries: int | None = None,
        base_delay: float = 1.0,
        **kwargs: Any,
    ) -> T:
        """Execute *fn* with exponential backoff on transient errors.

        Parameters
        ----------
        fn:
            An async callable to invoke.
        max_retries:
            Override the instance-level max_retries for this call.
        base_delay:
            Starting delay in seconds; doubles on every retry.
        *args, **kwargs:
            Forwarded to *fn*.

        Returns
        -------
        The return value of *fn* on success.

        Raises
        ------
        The last caught exception if all retries are exhausted.
        """
        retries = max_retries if max_retries is not None else self.max_retries
        last_exc: BaseException | None = None

        for attempt in range(1, retries + 1):
            try:
                return await fn(*args, **kwargs)
            except FloodWaitError as exc:
                # FloodWaitError tells us exactly how long to wait.
                await self.handle_flood_wait(exc)
                last_exc = exc
            except (ConnectionError, TimeoutError, OSError) as exc:
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Transient error on attempt %d/%d: %s  -- retrying in %.1fs",
                    attempt,
                    retries,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
                last_exc = exc

        # All retries exhausted -- re-raise so the caller can decide to skip.
        raise last_exc  # type: ignore[misc]
