"""
OpenClaw Agent — Main Orchestrator for YOUTUBEDROP
Runs both Telegram and Discord bots concurrently.
"""

import asyncio
import logging
import signal
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.text import Text

from .config import settings
from .database import Database
from .processor import YouTubeProcessor
from .telegram_bot import TelegramBot
from .discord_bot import DiscordBot

console = Console()


def setup_logging():
    """Configure logging with rich output."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="%H:%M:%S",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


class OpenClawAgent:
    """
    The OpenClaw Agent — central orchestrator for YOUTUBEDROP.
    Manages Telegram and Discord bots, database, and processing pipeline.
    """

    def __init__(self):
        self.db = Database(settings.database_url)
        self.processor = YouTubeProcessor(self.db)
        self.telegram_bot: TelegramBot = None
        self.discord_bot: DiscordBot = None
        self._running = False

    async def start(self):
        """Start the OpenClaw agent and all bot integrations."""
        setup_logging()
        logger = logging.getLogger("openclaw")

        # Banner
        banner = Text()
        banner.append("  ╔═══════════════════════════════════════╗\n", style="bold red")
        banner.append("  ║     🐾 YOUTUBEDROP — OpenClaw Agent   ║\n", style="bold red")
        banner.append("  ║   Send YouTube links. We ingest them. ║\n", style="bold red")
        banner.append("  ╚═══════════════════════════════════════╝", style="bold red")
        console.print(banner)
        console.print()

        # Connect database
        await self.db.connect()
        logger.info("Database connected")

        # Ensure download directory exists
        settings.download_dir.mkdir(parents=True, exist_ok=True)

        # Start bots
        tasks = []

        has_telegram = bool(settings.telegram_bot_token and settings.telegram_bot_token != "your_telegram_bot_token_here")
        has_discord = bool(settings.discord_bot_token and settings.discord_bot_token != "your_discord_bot_token_here")

        if not has_telegram and not has_discord:
            console.print(
                "[bold red]ERROR:[/] No bot tokens configured!\n"
                "Set TELEGRAM_BOT_TOKEN and/or DISCORD_BOT_TOKEN in your .env file.\n"
                "See .env.example for reference."
            )
            sys.exit(1)

        if has_telegram:
            self.telegram_bot = TelegramBot(
                token=settings.telegram_bot_token,
                db=self.db,
                processor=self.processor,
            )
            await self.telegram_bot.start()
            console.print("[green]✓[/] Telegram bot started")

        if has_discord:
            self.discord_bot = DiscordBot(
                db=self.db,
                processor=self.processor,
            )
            tasks.append(asyncio.create_task(
                self.discord_bot.start(settings.discord_bot_token)
            ))
            console.print("[green]✓[/] Discord bot starting...")

        self._running = True
        console.print(
            Panel(
                f"[bold green]OpenClaw Agent is running![/]\n\n"
                f"Telegram: {'✅ Active' if has_telegram else '⬜ Not configured'}\n"
                f"Discord:  {'✅ Active' if has_discord else '⬜ Not configured'}\n"
                f"Downloads: {settings.download_dir.resolve()}\n"
                f"Audio only: {settings.audio_only}\n"
                f"Transcripts: {settings.download_transcript}\n\n"
                f"Send a YouTube link from your phone or iPad!",
                title="Status",
                border_style="green",
            )
        )

        # Wait for tasks (Discord runs as a task, Telegram polls internally)
        if tasks:
            await asyncio.gather(*tasks)
        else:
            # If only Telegram, just wait forever
            while self._running:
                await asyncio.sleep(1)

    async def stop(self):
        """Gracefully stop all bots."""
        logger = logging.getLogger("openclaw")
        self._running = False

        if self.telegram_bot:
            await self.telegram_bot.stop()
            logger.info("Telegram bot stopped")

        if self.discord_bot:
            await self.discord_bot.close()
            logger.info("Discord bot stopped")

        await self.db.close()
        logger.info("Database closed")
        console.print("[bold yellow]OpenClaw Agent shut down.[/]")


def main():
    """Entry point for the OpenClaw agent."""
    agent = OpenClawAgent()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Handle shutdown signals
    def shutdown_handler():
        loop.create_task(agent.stop())

    try:
        if sys.platform != "win32":
            loop.add_signal_handler(signal.SIGINT, shutdown_handler)
            loop.add_signal_handler(signal.SIGTERM, shutdown_handler)
    except NotImplementedError:
        pass  # Windows doesn't support signal handlers in asyncio

    try:
        loop.run_until_complete(agent.start())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/]")
        loop.run_until_complete(agent.stop())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
