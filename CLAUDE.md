# YT_statsgrab — Project Context

## What this project does
Tracks YouTube channel statistics over time and sends daily reports to Telegram.

## Architecture
- **`main.py`** — fetches stats via YouTube Data API v3, saves to CSV, then calls `visualize.py`
- **`visualize.py`** — reads CSV, generates `growth_chart.png`, builds HTML stats table with deltas, sends to Telegram
- **`bot.py`** — Telegram bot for local use only (NOT used in GitHub Actions); commands: `/start`, `/list`, `/add <channel>`, `/remove <channel>`, `/run`
- **`channels.txt`** — list of channels to track (supports @handles, full URLs, channel IDs)
- **`cumulative_stats.csv`** — append-only log of daily stats (Date, ChannelName, Views, Subscribers, Videos); tracked in git, committed back by GitHub Actions after each run
- **`growth_chart.png`** — generated chart (per-channel views + combined % growth subplot); gitignored
- **`.github/workflows/collect.yml`** — GitHub Actions runs `main.py` daily at 09:00 UTC, commits updated CSV back to `master`

## Channels tracked
- @YevgeniyKovalenko
- @neuropros

## Environment variables / secrets
- `YOUTUBE_API_KEY` — YouTube Data API v3 key
- `TELEGRAM_BOT_TOKEN` — Telegram bot token
- `TELEGRAM_CHAT_ID` — Telegram chat/channel ID to post to

## Telegram messages sent per run
1. Text message: HTML stats table with latest values + deltas vs previous day
   - Format: per-channel block with Subscribers, Views, Videos each showing `value (+delta)`
   - Built by `build_stats_message(df)` in `visualize.py`
2. Photo: `growth_chart.png`

## Key behaviors
- `cumulative_stats.csv` is append-only — multiple runs on same day create duplicate rows
- Duplicates are handled: `group_by_day()` takes max Views per day for charts; `build_stats_message()` uses `drop_duplicates(keep="last")` per channel per day
- `visualize.py` uses `matplotlib.use('Agg')` — headless, no GUI
- GitHub Actions commits only `cumulative_stats.csv` (not the chart PNG)
- Default branch is `master` (not `main`)
- GitHub Actions secrets: `YOUTUBE_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## Dependencies
See `requirements.txt`: `requests`, `pandas`, `matplotlib`, `python-telegram-bot>=20.0`

## Local run workflow
```bash
git pull                          # get latest CSV from GitHub Actions
python main.py                    # collect stats, generate chart, send to Telegram
git add cumulative_stats.csv
git commit -m "Update stats"
git push
```

## bot.py usage (local only)
```bash
python bot.py                     # requires TELEGRAM_BOT_TOKEN in env
```
- `/add https://youtube.com/@channel` — adds channel to channels.txt
- `/remove @channel` — removes channel from channels.txt
- `/list` — shows tracked channels
- `/run` — triggers main.py (requires YOUTUBE_API_KEY in env)

## GitHub repo
https://github.com/justajazz/YT_statsgrab
