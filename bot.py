"""
Telegram bot for managing YouTube channels tracking.
Run locally: python bot.py

Commands:
  /start   - Show available commands
  /list    - List tracked channels
  /add     - Add a channel (URL, @handle, or channel ID)
  /remove  - Remove a channel
  /run     - Collect stats now and send chart to Telegram
"""

import base64
import os
import sys
import subprocess
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

CHANNELS_FILE = "channels.txt"
GITHUB_REPO = "justajazz/YT_statsgrab"
GITHUB_SECRET_NAME = "CHANNELS_LIST"


def sync_github_secret(channels: list[str]) -> bool:
    """Update CHANNELS_LIST GitHub secret with current channel list.
    Requires GITHUB_TOKEN env var (PAT with repo scope).
    Returns True on success, False if token missing or request fails.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return False

    try:
        from nacl import encoding, public as nacl_public
    except ImportError:
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        resp = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/public-key",
            headers=headers,
            timeout=10,
        )
        if not resp.ok:
            return False
        key_data = resp.json()

        pk = nacl_public.PublicKey(key_data["key"].encode("utf-8"), encoding.Base64Encoder())
        sealed_box = nacl_public.SealedBox(pk)
        encrypted = base64.b64encode(sealed_box.encrypt("\n".join(channels).encode("utf-8"))).decode("utf-8")

        resp = requests.put(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/{GITHUB_SECRET_NAME}",
            headers=headers,
            json={"encrypted_value": encrypted, "key_id": key_data["key_id"]},
            timeout=10,
        )
        return resp.ok
    except Exception:
        return False


def is_authorized(update: Update) -> bool:
    allowed = os.environ.get("TELEGRAM_CHAT_ID")
    return str(update.effective_chat.id) == allowed


async def deny(update: Update) -> None:
    await update.message.reply_text("Not authorized.")


def read_channels() -> list[str]:
    try:
        with open(CHANNELS_FILE, encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip() and not l.startswith("#")]
    except FileNotFoundError:
        return []


def write_channels(channels: list[str]) -> None:
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        for ch in channels:
            f.write(ch + "\n")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await deny(update)
    text = (
        "📺 <b>YouTube Stats Bot</b>\n\n"
        "Commands:\n"
        "  /list — show tracked channels\n"
        "  /add &lt;channel&gt; — add a channel\n"
        "  /remove &lt;channel&gt; — remove a channel\n"
        "  /run — collect stats now\n\n"
        "Channel formats accepted:\n"
        "  @handle, full URL, or UCxxxxxxx ID"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await deny(update)
    channels = read_channels()
    if not channels:
        await update.message.reply_text("No channels tracked. Use /add to add one.")
    else:
        lines = ["📋 <b>Tracked channels:</b>"] + [f"  • {c}" for c in channels]
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await deny(update)
    if not context.args:
        await update.message.reply_text("Usage: /add <channel_url_or_handle>")
        return

    channel = " ".join(context.args).strip()
    channels = read_channels()

    if channel in channels:
        await update.message.reply_text(f"Already tracking: <code>{channel}</code>", parse_mode="HTML")
        return

    channels.append(channel)
    write_channels(channels)
    synced = sync_github_secret(channels)
    sync_note = " GitHub secret updated." if synced else ""
    await update.message.reply_text(f"✅ Added: <code>{channel}</code>{sync_note}", parse_mode="HTML")


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await deny(update)
    if not context.args:
        await update.message.reply_text("Usage: /remove <channel_url_or_handle>")
        return

    channel = " ".join(context.args).strip()
    channels = read_channels()

    if channel not in channels:
        await update.message.reply_text(
            f"Not found: <code>{channel}</code>\nUse /list to see tracked channels.",
            parse_mode="HTML",
        )
        return

    channels.remove(channel)
    write_channels(channels)
    synced = sync_github_secret(channels)
    sync_note = " GitHub secret updated." if synced else ""
    await update.message.reply_text(f"🗑 Removed: <code>{channel}</code>{sync_note}", parse_mode="HTML")


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return await deny(update)
    if not os.environ.get("YOUTUBE_API_KEY"):
        await update.message.reply_text(
            "❌ YOUTUBE_API_KEY is not set. Cannot collect data."
        )
        return

    await update.message.reply_text("⏳ Collecting stats, please wait...")

    result = subprocess.run(
        [sys.executable, "main.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode == 0:
        await update.message.reply_text("✅ Done! Chart and stats sent above.")
    else:
        error_tail = result.stderr[-800:] if result.stderr else result.stdout[-800:]
        await update.message.reply_text(
            f"❌ Error during collection:\n<pre>{error_tail}</pre>",
            parse_mode="HTML",
        )


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable is not set.")
        sys.exit(1)

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("run", cmd_run))

    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
