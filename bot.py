import asyncio
import logging
import sys
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, InlineQueryHandler
)
from config import BOT_TOKEN, LOG_CHANNEL
from handlers.start import start_cmd, help_cmd
from handlers.search import search_cmd, inline_query_handler
from handlers.download import (
    button_handler, quality_handler,
    episode_handler, server_handler
)
from handlers.admin import (
    broadcast_cmd, ban_cmd, unban_cmd,
    restart_cmd, ping_cmd, stats_cmd,
    add_admin_cmd, remove_admin_cmd, logs_cmd
)
from handlers.manage import manage_cmd
from handlers.schedule import schedule_cmd, track_cmd, untrack_cmd
from handlers.autodel import autodel_cmd
from database.db import Database

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("cantarella.log"),
        logging.StreamHandler(sys.stdout)
    ],
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

db = Database()


async def post_init(app: Application):
    await db.connect()
    bot = app.bot
    try:
        if LOG_CHANNEL:
            await bot.send_message(
                LOG_CHANNEL,
                "✅ <b>CANTARELLA Bot Started!</b>\n\n"
                "🌸 <i>AniwatchTv Downloader is now online.</i>",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.warning(f"Could not send startup message: {e}")
    logger.info("✅ CANTARELLA Bot Started Successfully!")


async def post_shutdown(app: Application):
    await db.close()
    logger.info("Bot shut down cleanly.")


def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # ── Commands ──────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("schedule", schedule_cmd))
    app.add_handler(CommandHandler("track", track_cmd))
    app.add_handler(CommandHandler("untrack", untrack_cmd))
    app.add_handler(CommandHandler("manage", manage_cmd))
    app.add_handler(CommandHandler("autodel", autodel_cmd))
    app.add_handler(CommandHandler("ping", ping_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("restart", restart_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("addadmin", add_admin_cmd))
    app.add_handler(CommandHandler("removeadmin", remove_admin_cmd))
    app.add_handler(CommandHandler("logs", logs_cmd))

    # ── Inline query ──────────────────────────────────────────────
    app.add_handler(InlineQueryHandler(inline_query_handler))

    # ── Callback queries ──────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(episode_handler,  pattern=r"^eps\|"))
    app.add_handler(CallbackQueryHandler(quality_handler,  pattern=r"^qual\|"))
    app.add_handler(CallbackQueryHandler(server_handler,   pattern=r"^srv\|"))
    app.add_handler(CallbackQueryHandler(button_handler))   # catch-all

    # ── Plain messages → search ───────────────────────────────────
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, search_cmd)
    )

    # ── Job queue: anime schedule tracker ────────────────────────
    jq = app.job_queue
    if jq:
        jq.run_repeating(
            callback=lambda ctx: asyncio.create_task(
                __import__("handlers.schedule", fromlist=["check_airing"])
                .check_airing(ctx)
            ),
            interval=3600,   # every hour
            first=60,
            name="schedule_tracker",
        )

    logger.info("🚀 Starting polling …")
    app.run_polling(allowed_updates=["message", "callback_query", "inline_query"])


if __name__ == "__main__":
    main()
