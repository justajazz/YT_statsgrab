# Context for Claude — YT_statsgrab

Paste this file at the start of a new Claude session to restore project context.

---

## What this project does

Tracks YouTube channel statistics over time. Every day GitHub Actions:
1. Fetches views, subscribers, video count via YouTube Data API v3
2. Appends data to **Google Sheets** (replaced CSV)
3. Generates a growth chart (`growth_chart.png`)
4. Sends stats table + chart to Telegram

## GitHub repo
https://github.com/justajazz/YT_statsgrab (default branch: `master`)

## File structure
- `main.py` — fetch stats → append to Google Sheet → call visualize.py
- `visualize.py` — read Google Sheet → generate chart → send to Telegram
- `sheets_client.py` — shared OAuth2 auth module (gspread)
- `setup_sheets.py` — one-time local OAuth flow, gitignored
- `bot.py` — local-only Telegram bot (/start, /list, /add, /remove, /run)
- `channels.txt` — tracked channels (gitignored locally via skip-worktree)
- `.github/workflows/collect.yml` — daily 09:00 UTC + workflow_dispatch

## Environment variables / secrets
- `YOUTUBE_API_KEY` — YouTube Data API v3
- `TELEGRAM_BOT_TOKEN` — Telegram bot token
- `TELEGRAM_CHAT_ID` — Telegram chat ID
- `GOOGLE_SHEET_ID` — Google Sheet ID
- `GOOGLE_TOKEN_JSON` — OAuth2 token JSON (for GitHub Actions)

## Key architectural decisions
- **Google Sheets** instead of CSV — data in the cloud, no git commits needed after each run
- **OAuth2** auth for Sheets (one-time browser login locally, token stored as GitHub Secret)
- **bot.py** runs locally via Windows Task Scheduler (auto-restart on crash, runs at login)
- **channels.txt** is in git as empty template; local changes hidden via `git update-index --skip-worktree`

## Local run workflow
```bash
python main.py    # fetch → Sheets → chart → Telegram
```
No git commit needed — data goes to Google Sheets.

## Bot setup (Windows)
- Runs as scheduled task `YT_StatGrab_Bot` via Task Scheduler
- Restarts automatically within 1 min if it crashes
- `run_bot.ps1` in project root — used by the task (gitignored)

## Google Sheets setup (one-time)
1. Google Cloud Console → enable Sheets API → create OAuth 2.0 Client ID (Desktop) → download credentials.json
2. Run `python setup_sheets.py` → browser login → token.json created
3. Add to GitHub Secrets: `GOOGLE_SHEET_ID`, `GOOGLE_TOKEN_JSON` (contents of token.json)

## Dependencies
`requests`, `pandas`, `matplotlib`, `python-telegram-bot>=20.0`, `gspread>=6.0`, `google-auth`, `google-auth-oauthlib`

## Ideas for future development
- Alert when a channel grows unusually fast (spike detection)
- Weekly/monthly summary report (separate workflow)
- `/stats` command in bot — show latest table without running full collection
- New video detection (`videoCount` delta → add "🎬 new video!" to report)

## Workflow rules
- After any script changes → always push to GitHub
- If logic changes → update README.md too
- At end of session → update FOR_CLAUDE.md and memory if needed
