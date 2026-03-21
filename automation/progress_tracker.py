"""
progress_tracker.py
-------------------
Thin wrapper around *tqdm* that provides a consistent progress-bar
interface for long-running member-add and message-forward operations.
"""

from __future__ import annotations

from tqdm import tqdm


class ProgressTracker:
    """Create, update, and close a tqdm progress bar."""

    def __init__(self) -> None:
        self._bar: tqdm | None = None

    def start(self, total: int, desc: str = "Processing") -> None:
        """Initialise a new progress bar with *total* items."""
        self._bar = tqdm(total=total, desc=desc, unit="item")

    def update(self, n: int = 1) -> None:
        """Advance the progress bar by *n* steps."""
        if self._bar is not None:
            self._bar.update(n)

    def close(self) -> None:
        """Close the bar and flush output."""
        if self._bar is not None:
            self._bar.close()
            self._bar = None
