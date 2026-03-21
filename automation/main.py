#!/usr/bin/env python3
"""
main.py
-------
Entry point for the Telegram Automation Tool.

Usage examples
--------------
    # Run in member-adder mode (reads config.yaml by default)
    python main.py --mode members

    # Run in message-forwarder mode with a custom config
    python main.py --config my_config.yaml --mode messages

    # Override source/target from the CLI
    python main.py --mode members --source-chat @my_source --target-chat @my_target

    # Enable debug logging
    python main.py --mode messages --debug
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
from member_adder import MemberAdder
from message_forwarder import MessageForwarder


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(debug: bool = False) -> None:
    """Configure logging to console (INFO) and file (DEBUG)."""
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Console handler -- INFO (or DEBUG when --debug is passed).
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if debug else logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    # File handler -- always DEBUG for post-mortem analysis.
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
        description="Telegram Automation Tool -- add members or forward messages between chats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py --mode members\n"
            "  python main.py --config my.yaml --mode messages --debug\n"
            "  python main.py --mode members --source-chat @src --target-chat @dst --delay 2.0\n"
        ),
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to the YAML configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "--mode",
        choices=["members", "messages"],
        default=None,
        help='Operation mode: "members" or "messages" (overrides config)',
    )
    parser.add_argument("--source-chat", default=None, help="Override source chat")
    parser.add_argument("--target-chat", default=None, help="Override target chat")
    parser.add_argument("--delay", type=float, default=None, help="Override delay between API calls (seconds)")
    parser.add_argument("--debug", action="store_true", help="Enable verbose DEBUG logging")
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def _async_main(config: dict[str, Any]) -> None:
    """Instantiate the client, pick the right worker, and run it."""
    manager = TelegramClientManager(config)
    await manager.connect()

    try:
        mode = config["mode"]
        if mode == "members":
            worker = MemberAdder(manager, config)
        elif mode == "messages":
            worker = MessageForwarder(manager, config)
        else:
            logging.error("Unknown mode: %s", mode)
            return

        await worker.run()
    finally:
        await manager.disconnect()


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    _setup_logging(debug=args.debug)
    logger = logging.getLogger(__name__)

    # Load and merge config.
    config = _load_config(args.config)

    # CLI overrides take precedence.
    if args.mode:
        config["mode"] = args.mode
    if args.source_chat:
        config["source_chat"] = args.source_chat
    if args.target_chat:
        config["target_chat"] = args.target_chat
    if args.delay is not None:
        config["delay_secs"] = args.delay

    # Validate required keys.
    for key in ("api_id", "api_hash", "phone_number", "source_chat", "target_chat", "mode"):
        if key not in config:
            sys.exit(f"Missing required config key: {key}")

    logger.info("Mode: %s | Source: %s | Target: %s", config["mode"], config["source_chat"], config["target_chat"])

    asyncio.run(_async_main(config))


if __name__ == "__main__":
    main()
