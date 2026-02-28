# YT StatGrab

Tracks YouTube channel statistics over time and sends daily reports to Telegram — automatically via GitHub Actions or manually from your local machine.

## What it does

Every day at **09:00 UTC** GitHub Actions:
1. Fetches views, subscribers and video count for each tracked channel via YouTube Data API
2. Appends results to `cumulative_stats.csv`
3. Generates a growth chart (`growth_chart.png`)
4. Sends to Telegram: a stats table with deltas + the chart image

**Example Telegram message:**
```
📊 Stats — 2026-02-28

@YevgeniyKovalenko
  👥 Subscribers: 5,160 (+40)
  👁 Views:       341,503 (+2,444)
  🎬 Videos:      203 (-1)

@neuropros
  👥 Subscribers: 3,190 (+50)
  👁 Views:       87,112 (+1,726)
  🎬 Videos:      88 (+1)
```

## Project structure

```
├── main.py                        # Fetch stats → save CSV → run visualize.py
├── visualize.py                   # Generate chart + send to Telegram
├── bot.py                         # Telegram bot for managing channels (local only)
├── channels.txt                   # List of channels to track
├── cumulative_stats.csv           # Accumulated stats log (tracked in git)
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

### 4. Set environment variables

```bash
export YOUTUBE_API_KEY=your_key_here
export TELEGRAM_BOT_TOKEN=your_token_here
export TELEGRAM_CHAT_ID=your_chat_id_here
```

### 5. Add channels to track

Edit `channels.txt` — one channel per line. Supported formats:

```
https://www.youtube.com/@ChannelHandle
@ChannelHandle
UCxxxxxxxxxxxxxxxxxxxxxx
```

## Running locally

```bash
git pull                          # sync latest CSV from GitHub Actions
python main.py                    # collect stats, generate chart, send to Telegram
git add cumulative_stats.csv
git commit -m "Update stats"
git push
```

## Telegram bot (local)

Manage tracked channels directly from Telegram:

```bash
python bot.py
```

| Command | Action |
|---|---|
| `/list` | Show currently tracked channels |
| `/add <channel>` | Add a channel (URL or @handle) |
| `/remove <channel>` | Remove a channel |
| `/run` | Collect stats right now |

> `bot.py` is for local use only — GitHub Actions does not use it.

## GitHub Actions setup

Add these three secrets to your repository
(**Settings → Secrets and variables → Actions**):

| Secret | Value |
|---|---|
| `YOUTUBE_API_KEY` | YouTube Data API v3 key |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Telegram chat ID |

The workflow runs daily at 09:00 UTC and can also be triggered manually from the **Actions** tab.

## Chart

The generated chart includes:
- One subplot per channel showing **total views over time**
- A combined subplot showing **% growth from the first recorded date**

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | YouTube API & Telegram API calls |
| `pandas` | CSV handling & data aggregation |
| `matplotlib` | Chart generation |
| `python-telegram-bot` | Telegram bot (bot.py) |
