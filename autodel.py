import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import AUTO_DELETE_DEFAULT
from database.db import get_db

logger = logging.getLogger(__name__)


async def autodel_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /autodel <minutes>   → set auto-delete time
    /autodel off         → disable auto-delete
    /autodel             → show current setting
    """
    msg  = update.effective_message
    user = update.effective_user
    db   = get_db()

    current = await db.get_auto_del(user.id)
    current_min = current // 60

    if not ctx.args:
        status = "disabled ❌" if current == 0 else f"{current_min} minute(s) ✅"
        await msg.reply_text(
            f"🧹 <b>Auto-Delete Settings</b>\n\n"
            f"Current setting: <b>{status}</b>\n\n"
            f"Usage:\n"
            f"• /autodel &lt;minutes&gt; – set timer (e.g. /autodel 10)\n"
            f"• /autodel off – disable auto-delete\n"
            f"• /autodel 0 – disable auto-delete",
            parse_mode="HTML",
        )
        return

    arg = ctx.args[0].lower()

    if arg in ("off", "0", "disable", "none"):
        await db.set_auto_del(user.id, 0)
        await msg.reply_text(
            "🧹 <b>Auto-delete disabled.</b>\n\n"
            "Downloaded files will not be auto-deleted.",
            parse_mode="HTML",
        )
        return

    try:
        minutes = int(arg)
        if minutes < 1:
            raise ValueError
        if minutes > 1440:  # max 24 hours
            await msg.reply_text("❌ Maximum is 1440 minutes (24 hours).")
            return

        seconds = minutes * 60
        await db.set_auto_del(user.id, seconds)
        await msg.reply_text(
            f"✅ <b>Auto-delete set to {minutes} minute(s).</b>\n\n"
            f"Downloads will be deleted after {minutes} min.",
            parse_mode="HTML",
        )
    except ValueError:
        await msg.reply_text(
            "❌ Invalid value. Use a number of minutes or 'off'.\n\n"
            "Example: /autodel 10"
        )
