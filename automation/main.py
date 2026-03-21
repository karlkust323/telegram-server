#!/usr/bin/env python3
"""
main.py
-------
Entry point for the Telegram Automation Tool.

Usage examples
--------------
    # Member-add mode (one-shot)
    python main.py --mode members

    # Message-forward mode with custom config
    python main.py --config my_config.yaml --mode messages

    # Export-only mode (scrape to CSV/JSON without forwarding)
    python main.py --mode export-members
    python main.py --mode export-messages

    # Scheduled mode (repeat every 30 minutes)
    python main.py --mode messages --schedule 30

    # Override source/target + debug logging
    python main.py --mode members --source-chat @src --target-chat @dst --debug
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

from client_manager import TelegramClientManager
from exporter import DataExporter
from member_adder import MemberAdder
from message_forwarder import MessageForwarder
from scheduler import Scheduler


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(debug: bool = False) -> None:
    """Configure logging to console (INFO) and file (DEBUG)."""
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if debug else logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    file_handler = logging.FileHandler("automation.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )

    root.addHandler(console)
    root.addHandler(file_handler)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def _load_config(path: str) -> dict[str, Any]:
    """Read a YAML configuration file and return its contents as a dict."""
    config_path = Path(path)
    if not config_path.exists():
        sys.exit(f"Configuration file not found: {config_path}")
    with config_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        sys.exit("Invalid configuration file -- expected a YAML mapping at top level")
    return data


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Telegram Automation Tool -- add members, forward messages, export data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py --mode members\n"
            "  python main.py --mode messages --schedule 30\n"
            "  python main.py --mode export-members --export-format csv\n"
            "  python main.py --config prod.yaml --mode messages --debug\n"
        ),
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to the YAML configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "--mode",
        choices=["members", "messages", "export-members", "export-messages"],
        default=None,
        help="Operation mode (overrides config)",
    )
    parser.add_argument("--source-chat", default=None, help="Override source chat")
    parser.add_argument("--target-chat", default=None, help="Override target chat")
    parser.add_argument("--delay", type=float, default=None, help="Override delay between API calls (seconds)")
    parser.add_argument("--debug", action="store_true", help="Enable verbose DEBUG logging")
    parser.add_argument(
        "--schedule",
        type=float,
        default=None,
        metavar="MINUTES",
        help="Run on a recurring schedule (interval in minutes). Omit for one-shot.",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=0,
        help="Max scheduled runs before stopping (0 = unlimited, default: 0)",
    )
    parser.add_argument(
        "--export-format",
        choices=["json", "csv", "both"],
        default="both",
        help="Export format for export-members / export-messages modes (default: both)",
    )
    parser.add_argument(
        "--export-dir",
        default="exports",
        help="Directory for exported files (default: exports)",
    )
    return parser


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------

async def _run_worker(manager: TelegramClientManager, config: dict[str, Any]) -> None:
    """Pick the right worker based on config['mode'] and run it."""
    mode = config["mode"]
    logger = logging.getLogger(__name__)

    if mode == "members":
        worker = MemberAdder(manager, config)
        await worker.run()

    elif mode == "messages":
        worker = MessageForwarder(manager, config)
        await worker.run()

    elif mode == "export-members":
        exporter = DataExporter(config.get("export_dir", "exports"))
        client = manager.get_client()
        entity = await client.get_entity(config["source_chat"])
        members = await client.get_participants(entity, aggressive=True)
        fmt = config.get("export_format", "both")
        if fmt in ("json", "both"):
            exporter.export_members_json(members)
        if fmt in ("csv", "both"):
            exporter.export_members_csv(members)

    elif mode == "export-messages":
        exporter = DataExporter(config.get("export_dir", "exports"))
        client = manager.get_client()
        entity = await client.get_entity(config["source_chat"])
        from telethon.tl.types import Message as _Msg
        messages = []
        async for msg in client.iter_messages(entity, limit=None):
            if isinstance(msg, _Msg):
                messages.append(msg)
        fmt = config.get("export_format", "both")
        if fmt in ("json", "both"):
            exporter.export_messages_json(messages)
        if fmt in ("csv", "both"):
            exporter.export_messages_csv(messages)

    else:
        logger.error("Unknown mode: %s", mode)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def _async_main(config: dict[str, Any]) -> None:
    """Connect, optionally wrap in a scheduler, and run."""
    manager = TelegramClientManager(config)
    await manager.connect()

    try:
        schedule_mins = config.get("schedule")

        if schedule_mins and schedule_mins > 0:
            # Wrap the worker in a recurring scheduler.
            async def job() -> None:
                await _run_worker(manager, config)

            sched = Scheduler(
                interval_minutes=schedule_mins,
                job=job,
                max_runs=config.get("max_runs", 0),
            )
            await sched.start()
        else:
            await _run_worker(manager, config)

    finally:
        await manager.disconnect()


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    _setup_logging(debug=args.debug)
    logger = logging.getLogger(__name__)

    config = _load_config(args.config)

    # CLI overrides.
    if args.mode:
        config["mode"] = args.mode
    if args.source_chat:
        config["source_chat"] = args.source_chat
    if args.target_chat:
        config["target_chat"] = args.target_chat
    if args.delay is not None:
        config["delay_secs"] = args.delay
    if args.schedule is not None:
        config["schedule"] = args.schedule
    if args.max_runs:
        config["max_runs"] = args.max_runs
    config["export_format"] = args.export_format
    config["export_dir"] = args.export_dir

    # Validate credentials.
    has_accounts = "accounts" in config and isinstance(config.get("accounts"), list) and len(config["accounts"]) > 0
    has_single = all(k in config for k in ("api_id", "api_hash", "phone_number"))
    if not has_accounts and not has_single:
        sys.exit("Config must provide either top-level api_id/api_hash/phone_number or an 'accounts' list")

    # Export modes only need source_chat; add modes need both.
    if config.get("mode", "").startswith("export"):
        for key in ("source_chat", "mode"):
            if key not in config:
                sys.exit(f"Missing required config key: {key}")
    else:
        for key in ("source_chat", "target_chat", "mode"):
            if key not in config:
                sys.exit(f"Missing required config key: {key}")

    logger.info("Mode: %s | Source: %s | Target: %s", config["mode"], config["source_chat"], config.get("target_chat", "N/A"))

    asyncio.run(_async_main(config))


if __name__ == "__main__":
    main()
