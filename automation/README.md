# Telegram Automation Tool

A production-grade, async Python tool built on **Telethon** for two core workflows:

1. **Member Adder** -- scrape participants from a source Telegram group/channel and add them to a target group/channel.
2. **Message Forwarder** -- export messages (text + metadata) from a source chat and re-post them into a target chat, preserving structure and reaction info.

---

## Prerequisites

- Python 3.10 or later
- A Telegram account
- An **api_id** and **api_hash** from <https://my.telegram.org>

## Installation

```bash
cd automation
pip install -r requirements.txt
```

## Configuration

1. Copy the example config:

```bash
cp config.example.yaml config.yaml
```

2. Edit `config.yaml` and fill in your credentials and chat identifiers:

```yaml
api_id: 12345678
api_hash: "your_api_hash_here"
phone_number: "+1234567890"
session_name: "telegram_session"
source_chat: "@source_channel"
target_chat: "@target_group"
mode: "members"        # or "messages"
delay_secs: 1.5
max_retries: 3
forward_media: false
oldest_first: true
state_file: "state.json"
```

## Usage

### Add Members

```bash
python main.py --mode members
```

### Forward Messages

```bash
python main.py --mode messages
```

### CLI Options

| Flag | Description |
|---|---|
| `--config FILE` | Path to config file (default: `config.yaml`) |
| `--mode MODE` | `members` or `messages` (overrides config) |
| `--source-chat CHAT` | Override source chat |
| `--target-chat CHAT` | Override target chat |
| `--delay SECS` | Override delay between API calls |
| `--debug` | Enable verbose DEBUG logging |

### Examples

```bash
# Custom config + message mode + debug logging
python main.py --config prod.yaml --mode messages --debug

# Override chats from CLI
python main.py --mode members --source-chat @src_group --target-chat @dst_group --delay 2.0
```

## Resume Capability

The tool persists its progress in a JSON state file (`state.json` by default). If interrupted, re-running the same command will pick up from where it left off. Delete `state.json` to start fresh.

## Project Structure

```
automation/
  main.py               # CLI entry point
  client_manager.py     # Telethon session management
  member_adder.py       # Member-add workflow
  message_forwarder.py  # Message-forward workflow
  resilience.py         # Rate-limiting, retry, FloodWaitError handling
  progress_tracker.py   # tqdm progress bar wrapper
  state_manager.py      # JSON-based resume state
  config.example.yaml   # Sample configuration
  requirements.txt      # Python dependencies
```

## Multi-Account Rotation

For higher throughput, configure multiple Telegram accounts. The tool rotates between them when one hits a rate limit:

```yaml
accounts:
  - api_id: 11111111
    api_hash: "hash_1"
    phone_number: "+1111111111"
    session_name: "session_account_1"
  - api_id: 22222222
    api_hash: "hash_2"
    phone_number: "+2222222222"
    session_name: "session_account_2"
```

Each account needs its own API credentials from https://my.telegram.org and must be a member of both source and target chats. When account 1 gets rate-limited, the tool instantly switches to account 2 instead of sleeping. Single-account config still works as before.

See [SETUP_GUIDE.md](SETUP_GUIDE.md) (Step 5B) for detailed instructions.

## Rate Limiting and Resilience

- Configurable delay between every API call (`delay_secs`).
- Automatic handling of `FloodWaitError` -- the tool sleeps for exactly the duration Telegram requires.
- Exponential backoff on transient network errors.
- Errors that exceed the retry limit are logged and skipped; the tool does not crash.

## Ethical Use and Limitations

This tool is intended for **legitimate** purposes only:

- **Community management** -- consolidating members across groups you administer.
- **Content syndication / backup** -- mirroring public messages into a private archive.
- **Academic research** -- analysing information flow in public chats.

**Do not** use this tool to:

- Spam users or add people to groups without consent.
- Scrape private conversations or personal data.
- Violate Telegram's Terms of Service or anti-spam policies.

Aggressive usage (high-speed adding, mass-messaging) **will** result in your account being restricted or banned by Telegram.

## License

This project is provided as-is for educational and legitimate automation purposes.
