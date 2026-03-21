"""
scheduler.py
------------
Scheduler: runs the automation tool on a recurring timer so it can
continuously sync new members or messages without manual re-runs.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class Scheduler:
    """Run an async job on a fixed interval.

    Parameters
    ----------
    interval_minutes:
        Time between runs in minutes.
    job:
        An async callable (no args) to execute each cycle.
    max_runs:
        Stop after this many runs.  0 means run indefinitely.
    """

    def __init__(
        self,
        interval_minutes: float,
        job: Callable[[], Coroutine[Any, Any, None]],
        max_runs: int = 0,
    ) -> None:
        self.interval = interval_minutes * 60  # convert to seconds
        self.job = job
        self.max_runs = max_runs
        self._run_count = 0

    async def start(self) -> None:
        """Begin the scheduling loop.

        Runs the job immediately on first call, then sleeps for
        *interval* seconds between subsequent runs.
        """
        logger.info(
            "Scheduler started: interval=%.1f min, max_runs=%s",
            self.interval / 60,
            self.max_runs or "unlimited",
        )

        while True:
            self._run_count += 1
            logger.info("Scheduler: starting run %d", self._run_count)

            try:
                await self.job()
            except Exception as exc:  # noqa: BLE001
                logger.error("Scheduler: job failed on run %d: %s", self._run_count, exc)

            if self.max_runs and self._run_count >= self.max_runs:
                logger.info("Scheduler: reached max_runs (%d) -- stopping", self.max_runs)
                break

            logger.info(
                "Scheduler: sleeping %.1f minutes before next run...",
                self.interval / 60,
            )
            await asyncio.sleep(self.interval)
