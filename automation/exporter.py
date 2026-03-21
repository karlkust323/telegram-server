"""
exporter.py
-----------
DataExporter: writes scraped members or messages to CSV and/or JSON
files for backup, analysis, or import into other tools.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from telethon.tl.types import Message, User

logger = logging.getLogger(__name__)


class DataExporter:
    """Export Telegram data to structured files.

    Parameters
    ----------
    output_dir:
        Directory where export files are written.  Created if missing.
    """

    def __init__(self, output_dir: str = "exports") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _ts() -> str:
        """Short timestamp for filenames."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # -- member export ---------------------------------------------------------

    def export_members_json(self, members: list[User], filename: str | None = None) -> Path:
        """Write member data to a JSON file and return the path."""
        path = self.output_dir / (filename or f"members_{self._ts()}.json")
        data: list[dict[str, Any]] = []
        for m in members:
            data.append({
                "user_id": m.id,
                "first_name": m.first_name,
                "last_name": m.last_name,
                "username": m.username,
                "phone": m.phone,
                "bot": m.bot,
                "deleted": m.deleted,
            })
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        logger.info("Exported %d members to %s", len(data), path)
        return path

    def export_members_csv(self, members: list[User], filename: str | None = None) -> Path:
        """Write member data to a CSV file and return the path."""
        path = self.output_dir / (filename or f"members_{self._ts()}.csv")
        fields = ["user_id", "first_name", "last_name", "username", "phone", "bot", "deleted"]
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            for m in members:
                writer.writerow({
                    "user_id": m.id,
                    "first_name": m.first_name or "",
                    "last_name": m.last_name or "",
                    "username": m.username or "",
                    "phone": m.phone or "",
                    "bot": m.bot,
                    "deleted": m.deleted,
                })
        logger.info("Exported %d members to %s", len(members), path)
        return path

    # -- message export --------------------------------------------------------

    @staticmethod
    def _reactions_str(message: Message) -> str:
        """Build reactions string from a message."""
        if not getattr(message, "reactions", None):
            return ""
        results = getattr(message.reactions, "results", None)
        if not results:
            return ""
        parts = []
        for r in results:
            emoji = getattr(r.reaction, "emoticon", None) or "?"
            parts.append(f"{emoji} {r.count}")
        return ", ".join(parts)

    def export_messages_json(self, messages: list[Message], filename: str | None = None) -> Path:
        """Write message data to a JSON file and return the path."""
        path = self.output_dir / (filename or f"messages_{self._ts()}.json")
        data: list[dict[str, Any]] = []
        for msg in messages:
            data.append({
                "message_id": msg.id,
                "date": msg.date.isoformat() if msg.date else None,
                "sender_id": msg.sender_id,
                "text": msg.text or "",
                "reply_to_msg_id": (
                    msg.reply_to.reply_to_msg_id
                    if msg.reply_to and hasattr(msg.reply_to, "reply_to_msg_id")
                    else None
                ),
                "views": getattr(msg, "views", None),
                "forwards": getattr(msg, "forwards", None),
                "reactions": self._reactions_str(msg),
            })
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        logger.info("Exported %d messages to %s", len(data), path)
        return path

    def export_messages_csv(self, messages: list[Message], filename: str | None = None) -> Path:
        """Write message data to a CSV file and return the path."""
        path = self.output_dir / (filename or f"messages_{self._ts()}.csv")
        fields = [
            "message_id", "date", "sender_id", "text",
            "reply_to_msg_id", "views", "forwards", "reactions",
        ]
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            for msg in messages:
                writer.writerow({
                    "message_id": msg.id,
                    "date": msg.date.isoformat() if msg.date else "",
                    "sender_id": msg.sender_id or "",
                    "text": msg.text or "",
                    "reply_to_msg_id": (
                        msg.reply_to.reply_to_msg_id
                        if msg.reply_to and hasattr(msg.reply_to, "reply_to_msg_id")
                        else ""
                    ),
                    "views": getattr(msg, "views", None) or "",
                    "forwards": getattr(msg, "forwards", None) or "",
                    "reactions": self._reactions_str(msg),
                })
        logger.info("Exported %d messages to %s", len(messages), path)
        return path
