"""
Telegram Bot for YOUTUBEDROP
Send YouTube links from your phone/iPad via Telegram.
"""

import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from .youtube_parser import extract_video_id, extract_all_video_ids, is_youtube_link, make_url
from .database import Database, DropStatus
from .processor import YouTubeProcessor

logger = logging.getLogger("openclaw.telegram")


class TelegramBot:
    """Telegram bot that accepts YouTube links and ingests them into YOUTUBEDROP."""

    def __init__(self, token: str, db: Database, processor: YouTubeProcessor):
        self.token = token
        self.db = db
        self.processor = processor
        self.app: Application = None

    async def start(self):
        """Build and start the Telegram bot."""
        self.app = (
            Application.builder()
            .token(self.token)
            .build()
        )

        # Register handlers
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("recent", self._cmd_recent))
        self.app.add_handler(CommandHandler("stats", self._cmd_stats))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        # Set bot commands menu
        await self.app.bot.set_my_commands([
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help"),
            BotCommand("status", "Check status of a video (use: /status VIDEO_ID)"),
            BotCommand("recent", "Show recent drops"),
            BotCommand("stats", "Show drop statistics"),
        ])

        # Start polling
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot started and polling for messages")

    async def stop(self):
        """Stop the Telegram bot."""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            logger.info("Telegram bot stopped")

    # ── Command Handlers ─────────────────────────────────────────────

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "🎬 *YOUTUBEDROP — OpenClaw Agent*\n\n"
            "Drop any YouTube link and I'll ingest it!\n\n"
            "Just paste a YouTube URL and I'll:\n"
            "• Download the audio/video\n"
            "• Extract the transcript\n"
            "• Save all metadata\n\n"
            "Supports: standard links, shorts, mobile shares, music links\n\n"
            "Type /help for all commands.",
            parse_mode="Markdown",
        )

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        await update.message.reply_text(
            "📋 *Commands*\n\n"
            "• Send any YouTube link → auto-ingests it\n"
            "• `/status <video_id>` → check processing status\n"
            "• `/recent` → show last 10 drops\n"
            "• `/stats` → show overall statistics\n\n"
            "💡 You can send multiple links in one message!",
            parse_mode="Markdown",
        )

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        if not context.args:
            await update.message.reply_text("Usage: `/status <video_id>`", parse_mode="Markdown")
            return

        video_id = context.args[0]
        drop = await self.db.get_drop(video_id)
        if not drop:
            await update.message.reply_text(f"No drop found for `{video_id}`", parse_mode="Markdown")
            return

        status_emoji = {
            "pending": "⏳",
            "downloading": "⬇️",
            "processing": "⚙️",
            "complete": "✅",
            "failed": "❌",
        }
        emoji = status_emoji.get(drop["status"], "❓")
        msg = (
            f"{emoji} *{drop['title'] or video_id}*\n"
            f"Status: `{drop['status']}`\n"
            f"Channel: {drop['channel']}\n"
            f"Duration: {drop['duration']}s\n"
        )
        if drop["status"] == "failed":
            msg += f"Error: {drop['error_message']}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _cmd_recent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /recent command."""
        drops = await self.db.get_recent_drops(limit=10)
        if not drops:
            await update.message.reply_text("No drops yet! Send me a YouTube link.")
            return

        lines = ["📦 *Recent Drops*\n"]
        for d in drops:
            status_emoji = {"complete": "✅", "failed": "❌", "pending": "⏳", "downloading": "⬇️"}.get(d["status"], "❓")
            title = d["title"] or d["video_id"]
            lines.append(f"{status_emoji} [{title}]({make_url(d['video_id'])})")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True)

    async def _cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command."""
        stats = await self.db.get_stats()
        await update.message.reply_text(
            f"📊 *YOUTUBEDROP Stats*\n\n"
            f"Total drops: {stats.get('total', 0)}\n"
            f"✅ Complete: {stats.get('complete', 0)}\n"
            f"⏳ Pending: {stats.get('pending', 0)}\n"
            f"⬇️ Downloading: {stats.get('downloading', 0)}\n"
            f"❌ Failed: {stats.get('failed', 0)}",
            parse_mode="Markdown",
        )

    # ── Message Handler ──────────────────────────────────────────────

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages — look for YouTube links."""
        text = update.message.text
        if not text:
            return

        video_ids = extract_all_video_ids(text)
        if not video_ids:
            await update.message.reply_text(
                "🤔 I didn't find any YouTube links in that message.\n"
                "Send me a YouTube URL to ingest!"
            )
            return

        user = update.message.from_user
        source_user = f"{user.first_name or ''} {user.last_name or ''}".strip()
        if user.username:
            source_user += f" (@{user.username})"

        for vid in video_ids:
            url = make_url(vid)
            drop_id = await self.db.add_drop(
                video_id=vid,
                url=url,
                source="telegram",
                source_user=source_user,
                source_platform="telegram",
            )

            if drop_id is None:
                await update.message.reply_text(
                    f"⚡ Already have this one: `{vid}`\n"
                    f"Use `/status {vid}` to check it.",
                    parse_mode="Markdown",
                )
                continue

            await update.message.reply_text(
                f"📥 *Dropped!* Ingesting...\n`{vid}`",
                parse_mode="Markdown",
            )

            # Process in background
            context.application.create_task(
                self._process_and_notify(update, vid),
                name=f"process_{vid}",
            )

    async def _process_and_notify(self, update: Update, video_id: str):
        """Process a video and send completion notification."""
        try:
            drop = await self.processor.process(video_id)
            await update.message.reply_text(
                f"✅ *Done!*\n"
                f"📺 *{drop['title']}*\n"
                f"📺 Channel: {drop['channel']}\n"
                f"⏱ Duration: {drop['duration']}s\n"
                f"{'📝 Transcript saved' if drop['transcript'] else '📝 No transcript available'}",
                parse_mode="Markdown",
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ *Failed to process* `{video_id}`\n"
                f"Error: {str(e)[:200]}",
                parse_mode="Markdown",
            )
