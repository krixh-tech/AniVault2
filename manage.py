import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from utils.helpers import is_admin

logger = logging.getLogger(__name__)

MANAGE_TEXT = (
    "⚙️ <b>CANTARELLA – Management Panel</b>\n\n"
    "Choose an action below:"
)


def _manage_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Stats",       callback_data="show_stats"),
            InlineKeyboardButton("🏓 Ping",        callback_data="mgmt_ping"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast",   callback_data="mgmt_broadcast_prompt"),
            InlineKeyboardButton("📋 Logs",        callback_data="mgmt_logs"),
        ],
        [
            InlineKeyboardButton("🔄 Restart",     callback_data="mgmt_restart"),
            InlineKeyboardButton("🗓 Schedule",     callback_data="show_schedule"),
        ],
        [
            InlineKeyboardButton("❌ Close",        callback_data="cancel"),
        ],
    ])


async def manage_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(user.id):
        await update.effective_message.reply_text("🚫 Admin only.")
        return

    await update.effective_message.reply_text(
        MANAGE_TEXT,
        parse_mode="HTML",
        reply_markup=_manage_keyboard(),
    )


# The button callbacks are handled by the main button_handler via the
# "mgmt_*" pattern; extend button_handler if you want more panel actions.
