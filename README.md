# YT StatGrab

Tracks YouTube channel statistics over time and sends daily reports to Telegram — automatically via GitHub Actions or manually from your local machine.

## What it does

Every day at **09:00 UTC** GitHub Actions:
1. Fetches views, subscribers and video count for each tracked channel via YouTube Data API
2. Appends results to **Google Sheets**
3. Generates a growth chart (`growth_chart.png`)
4. Sends to Telegram: a stats table with deltas + the chart image

**Example Telegram message:**
```
📊 Stats — 2026-02-28

@YevgeniyKovalenko
  👥 Subscribers: 5,160 (+40)
  👁 Views:       341,503 (+2,444)
  🎬 Videos:      203

@neuropros
  👥 Subscribers: 3,190 (+50)
  👁 Views:       87,112 (+1,726)
  🎬 Videos:      88 (+1)
```

## Project structure

```
├── main.py                        # Fetch stats → save to Google Sheet → run visualize.py
├── visualize.py                   # Read Google Sheet → generate chart + send to Telegram
├── sheets_client.py               # Shared OAuth2 auth module for Google Sheets
├── setup_sheets.py                # One-time local OAuth flow (gitignored)
├── bot.py                         # Telegram bot for managing channels (local only)
├── channels.txt                   # Empty template — real channels stored as GitHub Secret
├── requirements.txt
└── .github/workflows/collect.yml  # GitHub Actions schedule
```

## Setup

### 1. Clone & install dependencies

```bash
git clone https://github.com/justajazz/YT_statsgrab.git
cd YT_statsgrab
pip install -r requirements.txt
```

### 2. Get a YouTube Data API v3 key

Go to [Google Cloud Console](https://console.cloud.google.com/), create a project, enable **YouTube Data API v3**, and generate an API key.

### 3. Create a Telegram bot

Talk to [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` → copy the token.
Get your chat ID by messaging [@userinfobot](https://t.me/userinfobot).

### 4. Set up Google Sheets

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → enable **Google Sheets API**
2. Create credentials → **OAuth 2.0 Client ID** (Desktop app) → download `credentials.json` to project root
3. Run the setup script (opens browser for authorization):
   ```bash
   python setup_sheets.py
   ```
4. Create a new Google Sheet — copy its ID from the URL (`/spreadsheets/d/<ID>/edit`)
5. In the sheet, add a header row in row 1: `Date | ChannelName | Views | Subscribers | Videos`

### 5. Add channels to track

Edit `channels.txt` — one channel per line. Supported formats:

```
https://www.youtube.com/@ChannelHandle
@ChannelHandle
UCxxxxxxxxxxxxxxxxxxxxxx
```

### 6. Set environment variables

```bash
export YOUTUBE_API_KEY=your_key_here
export TELEGRAM_BOT_TOKEN=your_token_here
export TELEGRAM_CHAT_ID=your_chat_id_here
export GOOGLE_SHEET_ID=your_sheet_id_here
```

## Running locally

```bash
python main.py    # collect stats, save to Google Sheet, generate chart, send to Telegram
```

No git commit needed — data goes to Google Sheets, not a file.

## Telegram bot (local)

`bot.py` runs on your local machine and lets you manage channels directly from Telegram.
It only responds to messages from your own `TELEGRAM_CHAT_ID` — all other users are rejected.

> **Note:** The bot works only while your computer is on and connected to the internet.
> GitHub Actions handles data collection independently — the bot is not required for that.

### Commands

| Command | Action |
|---|---|
| `/list` | Show currently tracked channels |
| `/add <channel>` | Add a channel (URL or @handle) |
| `/remove <channel>` | Remove a channel |
| `/run` | Collect stats right now |

### Auto-start on Windows login

The recommended approach is Windows Task Scheduler — it starts the bot at login and automatically restarts it if it crashes.

Create `run_bot.ps1` in the project folder:
```powershell
Set-Location "C:\path\to\YT_statsgrab"
& "C:\path\to\YT_statsgrab\.venv\Scripts\python.exe" "C:\path\to\YT_statsgrab\bot.py"
```

Then register the scheduled task in PowerShell:
```powershell
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -NonInteractive -File `"C:\path\to\YT_statsgrab\run_bot.ps1`"" `
    -WorkingDirectory "C:\path\to\YT_statsgrab"

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$settings = New-ScheduledTaskSettingsSet `
    -RestartCount 99 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit 0 `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName "YT_StatGrab_Bot" -Action $action -Trigger $trigger -Settings $settings -Force
```

The bot will start automatically in the background every time you log in, and restart within 1 minute if it crashes.

## GitHub Actions setup

Add these secrets to your repository (**Settings → Secrets and variables → Actions**):

| Secret | Value |
|---|---|
| `YOUTUBE_API_KEY` | YouTube Data API v3 key |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Telegram chat ID |
| `GOOGLE_SHEET_ID` | Google Sheet ID |
| `GOOGLE_TOKEN_JSON` | Contents of `token.json` (generated by setup_sheets.py) |
| `CHANNELS_LIST` | List of channels to track (one per line) |

The workflow writes `token.json` and `channels.txt` from secrets before running, so no sensitive data is stored in the repository.

The workflow runs daily at 09:00 UTC and can also be triggered manually from the **Actions** tab.

## Chart

The generated chart includes:
- One subplot per channel showing **total views over time**
- A combined subplot showing **% growth from the first recorded date**

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | YouTube API & Telegram API calls |
| `pandas` | Data aggregation |
| `matplotlib` | Chart generation |
| `python-telegram-bot` | Telegram bot (bot.py) |
| `gspread` | Google Sheets read/write |
| `google-auth` | OAuth2 authentication |
| `google-auth-oauthlib` | OAuth2 browser flow |
