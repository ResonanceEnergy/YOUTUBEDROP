"""
Discord Bot for YOUTUBEDROP
Send YouTube links from your phone/iPad via Discord.
"""

import asyncio
import logging
import discord
from discord.ext import commands

from .youtube_parser import extract_video_id, extract_all_video_ids, is_youtube_link, make_url
from .database import Database, DropStatus
from .processor import YouTubeProcessor

logger = logging.getLogger("openclaw.discord")


class DiscordBot(commands.Bot):
    """Discord bot that accepts YouTube links and ingests them into YOUTUBEDROP."""

    def __init__(self, db: Database, processor: YouTubeProcessor):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix="!yt ",
            intents=intents,
            description="YOUTUBEDROP — OpenClaw Agent. Drop YouTube links to ingest them!",
        )
        self.db = db
        self.processor = processor
        self._setup_commands()

    def _setup_commands(self):
        """Register bot commands."""

        @self.command(name="help", help="Show help message")
        async def help_cmd(ctx: commands.Context):
            embed = discord.Embed(
                title="🎬 YOUTUBEDROP — OpenClaw Agent",
                description="Drop any YouTube link and I'll ingest it!",
                color=discord.Color.red(),
            )
            embed.add_field(
                name="How to use",
                value=(
                    "• Just paste a YouTube link in any channel I'm in\n"
                    "• `!yt status <video_id>` — check processing status\n"
                    "• `!yt recent` — show last 10 drops\n"
                    "• `!yt stats` — show overall statistics\n"
                ),
                inline=False,
            )
            embed.add_field(
                name="Supported links",
                value="Standard, Shorts, Mobile shares, Music, Live, Embeds",
                inline=False,
            )
            await ctx.send(embed=embed)

        @self.command(name="status", help="Check status of a video")
        async def status_cmd(ctx: commands.Context, video_id: str = None):
            if not video_id:
                await ctx.send("Usage: `!yt status <video_id>`")
                return

            drop = await self.db.get_drop(video_id)
            if not drop:
                await ctx.send(f"No drop found for `{video_id}`")
                return

            status_emoji = {
                "pending": "⏳",
                "downloading": "⬇️",
                "processing": "⚙️",
                "complete": "✅",
                "failed": "❌",
            }
            emoji = status_emoji.get(drop["status"], "❓")

            embed = discord.Embed(
                title=f"{emoji} {drop['title'] or video_id}",
                url=make_url(video_id),
                color=discord.Color.green() if drop["status"] == "complete" else discord.Color.orange(),
            )
            embed.add_field(name="Status", value=drop["status"], inline=True)
            embed.add_field(name="Channel", value=drop["channel"] or "Unknown", inline=True)
            embed.add_field(name="Duration", value=f"{drop['duration']}s", inline=True)
            if drop["status"] == "failed":
                embed.add_field(name="Error", value=drop["error_message"][:200], inline=False)
            await ctx.send(embed=embed)

        @self.command(name="recent", help="Show recent drops")
        async def recent_cmd(ctx: commands.Context):
            drops = await self.db.get_recent_drops(limit=10)
            if not drops:
                await ctx.send("No drops yet! Send me a YouTube link.")
                return

            embed = discord.Embed(
                title="📦 Recent Drops",
                color=discord.Color.blue(),
            )
            for d in drops:
                status_emoji = {"complete": "✅", "failed": "❌", "pending": "⏳", "downloading": "⬇️"}.get(d["status"], "❓")
                title = d["title"] or d["video_id"]
                embed.add_field(
                    name=f"{status_emoji} {title}",
                    value=f"[Watch]({make_url(d['video_id'])}) | `{d['status']}`",
                    inline=False,
                )
            await ctx.send(embed=embed)

        @self.command(name="stats", help="Show drop statistics")
        async def stats_cmd(ctx: commands.Context):
            stats = await self.db.get_stats()
            embed = discord.Embed(
                title="📊 YOUTUBEDROP Stats",
                color=discord.Color.gold(),
            )
            embed.add_field(name="Total", value=str(stats.get("total", 0)), inline=True)
            embed.add_field(name="✅ Complete", value=str(stats.get("complete", 0)), inline=True)
            embed.add_field(name="⏳ Pending", value=str(stats.get("pending", 0)), inline=True)
            embed.add_field(name="⬇️ Downloading", value=str(stats.get("downloading", 0)), inline=True)
            embed.add_field(name="❌ Failed", value=str(stats.get("failed", 0)), inline=True)
            await ctx.send(embed=embed)

    async def on_ready(self):
        """Called when bot is ready."""
        logger.info(f"Discord bot logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for YouTube drops",
            )
        )

    async def on_message(self, message: discord.Message):
        """Handle incoming messages — look for YouTube links."""
        # Don't respond to ourselves
        if message.author == self.user:
            return

        # Process commands first
        await self.process_commands(message)

        # Check for YouTube links in any message
        if not message.content or message.content.startswith("!yt "):
            return

        video_ids = extract_all_video_ids(message.content)
        if not video_ids:
            return  # Silently ignore non-YouTube messages (unlike Telegram, no spam)

        source_user = f"{message.author.display_name} ({message.author.name})"

        for vid in video_ids:
            url = make_url(vid)
            drop_id = await self.db.add_drop(
                video_id=vid,
                url=url,
                source="discord",
                source_user=source_user,
                source_platform="discord",
            )

            if drop_id is None:
                await message.reply(
                    f"⚡ Already have this one: `{vid}`\nUse `!yt status {vid}` to check it.",
                    mention_author=False,
                )
                continue

            processing_msg = await message.reply(
                f"📥 **Dropped!** Ingesting `{vid}`...",
                mention_author=False,
            )

            # Process in background
            asyncio.create_task(
                self._process_and_notify(message, processing_msg, vid)
            )

    async def _process_and_notify(
        self,
        original_msg: discord.Message,
        processing_msg: discord.Message,
        video_id: str,
    ):
        """Process a video and edit the processing message with results."""
        try:
            drop = await self.processor.process(video_id)
            embed = discord.Embed(
                title=f"✅ {drop['title']}",
                url=make_url(video_id),
                color=discord.Color.green(),
            )
            embed.add_field(name="Channel", value=drop["channel"] or "Unknown", inline=True)
            embed.add_field(name="Duration", value=f"{drop['duration']}s", inline=True)
            embed.add_field(
                name="Transcript",
                value="📝 Saved" if drop["transcript"] else "📝 Not available",
                inline=True,
            )
            if drop.get("thumbnail_url"):
                embed.set_thumbnail(url=drop["thumbnail_url"])
            await processing_msg.edit(content="", embed=embed)

        except Exception as e:
            await processing_msg.edit(
                content=f"❌ **Failed to process** `{video_id}`\nError: {str(e)[:200]}"
            )
