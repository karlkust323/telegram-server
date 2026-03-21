"""
state_manager.py
----------------
Reads and writes lightweight JSON state files so the tool can
resume from the last processed user or message after a restart.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StateManager:
    """Persist and load resume state to/from a JSON file."""

    def __init__(self, state_file: str = "state.json") -> None:
        self.path = Path(state_file)
        self._state: dict[str, Any] = {}
        self._load()

    # -- internal --------------------------------------------------------------

    def _load(self) -> None:
        """Load state from disk if the file exists."""
        if self.path.exists():
            try:
                self._state = json.loads(self.path.read_text(encoding="utf-8"))
                logger.info("Loaded resume state from %s", self.path)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not read state file (%s); starting fresh", exc)
                self._state = {}

    def _save(self) -> None:
        """Flush current state to disk."""
        self.path.write_text(
            json.dumps(self._state, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # -- public API ------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the persisted state."""
        return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Store a value and immediately flush to disk."""
        self._state[key] = value
        self._save()

    def clear(self) -> None:
        """Wipe the state file."""
        self._state = {}
        self._save()
