import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import START_TEXT, HELP_TEXT
from utils.helpers import (
    check_subscription, register_user, FORCE_SUB_TEXT
)
from database.db import get_db

logger = logging.getLogger(__name__)


async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg  = update.effective_message

    await register_user(user)

    db = get_db()
    if await db.is_banned(user.id):
        await msg.reply_text("🚫 You are banned from using this bot.")
        return

    # Force-subscribe check
    ok, kb = await check_subscription(update.get_bot(), user.id)
    if not ok:
        await msg.reply_text(FORCE_SUB_TEXT, reply_markup=kb, parse_mode="HTML")
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Search Anime", switch_inline_query_current_chat=""),
            InlineKeyboardButton("📖 Help", callback_data="show_help"),
        ],
        [
            InlineKeyboardButton("📢 Updates Channel", url="https://t.me/cantarella_updates"),
            InlineKeyboardButton("⭐ Rate Bot", url="https://t.me/cantarella_bot"),
        ],
        [
            InlineKeyboardButton("🗓 Schedule", callback_data="show_schedule"),
            InlineKeyboardButton("📊 Stats", callback_data="show_stats"),
        ],
    ])

    await msg.reply_text(
        START_TEXT.format(name=user.first_name),
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Back to Start", callback_data="show_start")]
    ])
    await msg.reply_text(HELP_TEXT, parse_mode="HTML", reply_markup=keyboard)
