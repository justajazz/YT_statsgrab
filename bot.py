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

import os
import sys
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

CHANNELS_FILE = "channels.txt"


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
    channels = read_channels()
    if not channels:
        await update.message.reply_text("No channels tracked. Use /add to add one.")
    else:
        lines = ["📋 <b>Tracked channels:</b>"] + [f"  • {c}" for c in channels]
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    await update.message.reply_text(f"✅ Added: <code>{channel}</code>", parse_mode="HTML")


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    await update.message.reply_text(f"🗑 Removed: <code>{channel}</code>", parse_mode="HTML")


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
