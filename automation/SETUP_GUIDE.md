# Step-by-Step Setup Guide

This guide walks you through getting the Telegram Automation Tool running from scratch. Follow each step completely before moving to the next.

---

## Step 1: Install Python

You need Python 3.9 or newer on your computer.

**Check if you already have it:**

Open a terminal (Command Prompt on Windows, Terminal on Mac/Linux) and type:

```bash
python3 --version
```

You should see something like `Python 3.10.12` or `Python 3.11.5`. Any version 3.9+ works.

**If you don't have Python:**

- **Windows**: Download from https://www.python.org/downloads/ -- during install, check the box that says "Add Python to PATH"
- **Mac**: Run `brew install python3` (requires Homebrew: https://brew.sh)
- **Linux**: Run `sudo apt install python3 python3-pip` (Ubuntu/Debian) or `sudo dnf install python3 python3-pip` (Fedora)

**Verify pip is available too:**

```bash
pip3 --version
```

You should see something like `pip 23.2.1 from ...`. If not, install it:

```bash
python3 -m ensurepip --upgrade
```

---

## Step 2: Get the Code

You need to download the automation tool from GitHub.

**Option A -- Using git (recommended):**

```bash
git clone -b feature/telegram-automation-tool https://github.com/karlkust323/telegram-server.git
cd telegram-server/automation
```

**Option B -- Download as ZIP:**

1. Go to https://github.com/karlkust323/telegram-server/tree/feature/telegram-automation-tool
2. Click the green "Code" button, then "Download ZIP"
3. Extract the ZIP file
4. Open a terminal and navigate into the `automation` folder:
   ```bash
   cd path/to/telegram-server/automation
   ```

**Verify you're in the right place:**

```bash
ls
```

You should see files like `main.py`, `client_manager.py`, `config.example.yaml`, etc.

---

## Step 3: Install Dependencies

The tool needs three Python libraries: Telethon (Telegram client), tqdm (progress bars), and PyYAML (config files).

Run this command from inside the `automation` folder:

```bash
pip3 install -r requirements.txt
```

You should see output like:

```
Successfully installed telethon-1.36.0 tqdm-4.66.1 pyyaml-6.0.1 ...
```

**If you get a permission error**, try:

```bash
pip3 install --user -r requirements.txt
```

---

## Step 4: Get Telegram API Credentials

Telegram requires you to register an "application" to use their API. This is free and takes about 2 minutes.

1. Open your browser and go to: **https://my.telegram.org**

2. Enter your phone number (the same one linked to your Telegram account) and click "Next"

3. Telegram will send a login code **to your Telegram app** (not SMS). Open your Telegram app, find the code, and enter it on the website.

4. Once logged in, click **"API development tools"**

5. Fill in the form:
   - **App title**: anything you want (e.g. "My Automation Tool")
   - **Short name**: anything (e.g. "myautotool")
   - **Platform**: Desktop
   - **Description**: optional

6. Click **"Create application"**

7. You will now see two important values:
   - **api_id**: a number like `12345678`
   - **api_hash**: a string like `a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4`

**Write these down or keep the page open.** You will need them in the next step.

**Important**: Never share your api_id and api_hash publicly. They are tied to your Telegram account.

---

## Step 5: Create Your Configuration File

The tool reads all its settings from a YAML file. You need to create one.

**Copy the example config:**

```bash
cp config.example.yaml config.yaml
```

**Now open `config.yaml` in a text editor** (Notepad, VS Code, nano, vim, etc.) and fill in your values:

```yaml
# Replace these with YOUR actual values from Step 4
api_id: 12345678
api_hash: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"

# Your Telegram phone number with country code
phone_number: "+1234567890"

# Leave this as-is (Telethon creates a session file with this name)
session_name: "telegram_session"

# The chat you want to PULL data FROM
# Use a username like "@channelname" or a numeric ID like -1001234567890
source_chat: "@source_channel"

# The chat you want to PUSH data TO
target_chat: "@target_group"

# What to do: "members" (add users) or "messages" (forward messages)
mode: "members"

# Seconds to wait between each API call (don't go below 1.0)
delay_secs: 1.5

# How many times to retry on errors before giving up
max_retries: 3

# For message mode: download and re-upload media files?
forward_media: false

# For message mode: send oldest messages first?
oldest_first: true

# Where to save progress for resume capability
state_file: "state.json"
```

**How to find chat usernames or IDs:**

- **Username**: If the group/channel has a public link like `t.me/example_channel`, the username is `@example_channel`
- **Numeric ID**: You can use a bot like @userinfobot in Telegram -- forward a message from the chat to this bot and it will show the chat ID

**Save the file and close the editor.**

---

## Step 5B: Setting Up Multiple Accounts (Optional)

If you want to use multiple Telegram accounts for faster operation (the tool rotates between them when one hits a rate limit), you can configure an `accounts` list instead of a single account.

**Why use multiple accounts?**

- Each Telegram account has a daily limit of roughly 30-50 member additions
- With 3 accounts, you can effectively add ~90-150 members per day
- When account 1 hits a FloodWaitError, the tool instantly switches to account 2 instead of sleeping

**Requirements for each account:**

- Each account needs its own phone number (a real Telegram account)
- Each account needs its own api_id and api_hash from https://my.telegram.org
- Each account must be a member of both the source and target chats
- Each account must have admin rights in the target chat (for member-adding mode)

**How to set it up:**

1. For each phone number, go to https://my.telegram.org, log in, and create an API application (same process as Step 4). Note down each api_id and api_hash.

2. Edit your `config.yaml` to use the `accounts` list format:

```yaml
accounts:
  - api_id: 11111111
    api_hash: "hash_for_account_1"
    phone_number: "+1111111111"
    session_name: "session_account_1"
  - api_id: 22222222
    api_hash: "hash_for_account_2"
    phone_number: "+2222222222"
    session_name: "session_account_2"
  - api_id: 33333333
    api_hash: "hash_for_account_3"
    phone_number: "+3333333333"
    session_name: "session_account_3"

# The rest of the config stays the same
source_chat: "@source_channel"
target_chat: "@target_group"
mode: "members"
delay_secs: 1.5
max_retries: 3
```

3. On first run, the tool will prompt you for the login code for **each account** one at a time:

```
Enter the code sent to +1111111111 (account 1): 12345
Enter the code sent to +2222222222 (account 2): 67890
Enter the code sent to +3333333333 (account 3): 11111
```

After that, each account's session is saved separately and you won't be prompted again.

**How rotation works:**

- The tool starts working with account 1
- When account 1 gets a FloodWaitError (rate limit), it immediately switches to account 2
- If account 2 also gets rate-limited, it switches to account 3
- Only when ALL accounts are rate-limited does it sleep through the wait
- This means the tool can keep working almost continuously

**Single account is still fine:**

If you only have one account, just use the simple format from Step 5. The tool works exactly the same way -- it just can't rotate when rate-limited.

---

## Step 6: First Run -- Authentication

The first time you run the tool, Telethon needs to authenticate with your Telegram account. This is a one-time process.

Run:

```bash
python3 main.py --mode members
```

**What happens:**

1. The tool connects to Telegram's servers
2. Telegram sends a **login code to your Telegram app** (check your "Saved Messages" or the Telegram notification)
3. The terminal will prompt you:
   ```
   Enter the code sent to +1234567890: 
   ```
4. Type the code and press Enter

**If successful**, you will see output like:

```
2024-01-15 10:30:00 [INFO] client_manager: Authenticated as YourName (id=123456789)
2024-01-15 10:30:01 [INFO] member_adder: Starting member adder for source @source_channel -> target @target_group
```

A file called `telegram_session.session` is now saved in your folder. **This stores your login so you won't need the code again** on future runs.

**If you get an error about 2FA (two-factor authentication):**
If your Telegram account has a password set, you may need to enter it too. The current tool handles phone+code auth. If you use 2FA, you can add password support by modifying `client_manager.py`.

---

## Step 7: Running in Member-Add Mode

This mode pulls members from the source chat and adds them to the target chat.

**Prerequisites:**
- You must be a **member** of the source chat
- You must be an **admin** in the target chat (with "Add Members" permission)
- The source chat must be a group or a supergroup (channels don't expose member lists to non-admins in most cases)

**Run it:**

```bash
python3 main.py --mode members
```

**What you will see:**

```
2024-01-15 10:30:00 [INFO] member_adder: Starting member adder for source @source_group -> target @target_group
2024-01-15 10:30:02 [INFO] member_adder: Found 150 participants in source
2024-01-15 10:30:05 [INFO] member_adder: 23 users already in target -- will be skipped
Adding members:  15%|████                      | 22/150 [00:33<03:12,  1.50s/item]
```

The progress bar updates in real time. The tool:
- Skips bots and deleted accounts
- Skips users already in the target
- Skips users with privacy restrictions (they don't allow being added to groups)
- Waits 1.5 seconds between each add (configurable)
- Handles Telegram's rate limits automatically

**If interrupted** (Ctrl+C or network drop), just run the same command again. It resumes from where it stopped.

---

## Step 8: Running in Message-Forward Mode

This mode copies messages from the source chat to the target chat, including metadata like sender, date, views, and reactions.

**Prerequisites:**
- You must be able to **read** messages in the source chat
- You must be able to **write** messages in the target chat

**Run it:**

```bash
python3 main.py --mode messages
```

**What you will see:**

```
2024-01-15 10:30:00 [INFO] message_forwarder: Starting message forwarder for source @source_channel -> target @target_group
2024-01-15 10:30:10 [INFO] message_forwarder: Fetched 500 messages from source
Forwarding messages:   5%|██                        | 25/500 [00:38<12:10,  1.55s/item]
```

Each forwarded message in the target will look like:

```
[msg_id=1234] [date=2024-01-10T15:30:00+00:00] [sender=987654321] [views=1500] [Reactions: 👍 12, ❤️ 5]
This is the original message text that was in the source chat.
```

**If interrupted**, just run again -- it resumes from the last forwarded message.

---

## Step 9: Using CLI Overrides

You don't have to edit `config.yaml` every time you want to change settings. You can override them from the command line:

**Change the mode:**
```bash
python3 main.py --mode messages
```

**Change source and target:**
```bash
python3 main.py --mode members --source-chat @group_a --target-chat @group_b
```

**Slow down the delay (safer, less likely to hit rate limits):**
```bash
python3 main.py --mode members --delay 3.0
```

**Enable debug logging (shows every detail):**
```bash
python3 main.py --mode messages --debug
```

**Use a different config file:**
```bash
python3 main.py --config production.yaml --mode members
```

**See all available options:**
```bash
python3 main.py --help
```

---

## Step 10: Troubleshooting Common Issues

### "FloodWaitError: sleeping for X seconds"

This is normal. Telegram is telling the tool to slow down. The tool automatically waits the required time and continues. If you see this often, increase `delay_secs` in your config (try 2.0 or 3.0).

### "User has privacy restrictions -- skipping"

The user's Telegram settings prevent them from being added to groups by non-contacts. Nothing you can do about this.

### "Admin rights required in target chat"

You need to be an admin in the target group/channel with the "Add Members" permission. Ask the group owner to make you an admin.

### "Cannot access the target channel (private or banned)"

The target chat is private and your account doesn't have access, or your account has been banned from it.

### "Session not authorised"

Your `.session` file is invalid or expired. Delete the `telegram_session.session` file and run the tool again to re-authenticate.

### The tool crashed -- will I lose progress?

No. The tool saves its progress to `state.json` after every single user/message. Run the command again and it continues from where it stopped.

### I want to start fresh (re-process everything)

Delete the state file:
```bash
rm state.json
```

Then run the tool again.

### Where are the detailed logs?

Check `automation.log` in the same directory. It contains DEBUG-level logs with every action the tool took.

```bash
cat automation.log
```

Or open it in a text editor.

---

## Quick Reference

| Task | Command |
|---|---|
| Add members | `python3 main.py --mode members` |
| Forward messages | `python3 main.py --mode messages` |
| Use custom config | `python3 main.py --config my.yaml --mode members` |
| Override source/target | `python3 main.py --mode members --source-chat @src --target-chat @dst` |
| Slower rate limit | `python3 main.py --mode members --delay 3.0` |
| Debug logging | `python3 main.py --mode messages --debug` |
| Reset progress | `rm state.json` |
| View logs | `cat automation.log` |
| See help | `python3 main.py --help` |
