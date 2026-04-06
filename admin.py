import asyncio
import logging
import os
import sys
import time

from telegram import Update
from telegram.ext import ContextTypes

from config import OWNER_ID, LOG_CHANNEL
from database.db import get_db
from utils.helpers import is_admin, is_owner, mention

logger = logging.getLogger(__name__)

START_TIME = time.time()


def _uptime() -> str:
    secs  = int(time.time() - START_TIME)
    hours = secs // 3600
    mins  = (secs % 3600) // 60
    secs  = secs % 60
    return f"{hours}h {mins}m {secs}s"


# ── Guards ────────────────────────────────────────────────────────────────────

async def _require_admin(update: Update) -> bool:
    user = update.effective_user
    if not await is_admin(user.id):
        await update.effective_message.reply_text("🚫 Admin only.")
        return False
    return True


async def _require_owner(update: Update) -> bool:
    if update.effective_user.id != OWNER_ID:
        await update.effective_message.reply_text("🚫 Owner only.")
        return False
    return True


# ── /ping ─────────────────────────────────────────────────────────────────────

async def ping_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    start = time.time()
    msg   = await update.effective_message.reply_text("🏓 Pinging …")
    latency = (time.time() - start) * 1000
    await msg.edit_text(
        f"🏓 <b>Pong!</b>\n\n"
        f"⚡️ <b>Latency:</b> {latency:.1f} ms\n"
        f"⏱ <b>Uptime:</b> {_uptime()}",
        parse_mode="HTML",
    )


# ── /stats ────────────────────────────────────────────────────────────────────

async def stats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    db   = get_db()
    users = await db.total_users()
    dls   = await db.total_downloads()
    admins = await db.get_all_admins()

    text = (
        "📊 <b>CANTARELLA – Stats</b>\n\n"
        f"👥 <b>Total Users:</b> {users}\n"
        f"📥 <b>Total Downloads:</b> {dls}\n"
        f"🛡 <b>Admins:</b> {len(admins)}\n"
        f"⏱ <b>Uptime:</b> {_uptime()}\n\n"
        f"<i>🌸 Powered by CANTARELLA Bot</i>"
    )

    cb = update.callback_query
    if cb:
        await cb.answer()
        await cb.edit_message_text(text, parse_mode="HTML")
    else:
        await update.effective_message.reply_text(text, parse_mode="HTML")


# ── /broadcast ────────────────────────────────────────────────────────────────

async def broadcast_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return

    msg  = update.effective_message
    text = msg.text_html.split(None, 1)[1] if len(msg.text or "").split() > 1 else None

    if not text:
        await msg.reply_text(
            "📢 Usage: /broadcast &lt;message&gt;\n\nSupports HTML formatting.",
            parse_mode="HTML",
        )
        return

    db       = get_db()
    user_ids = await db.get_all_user_ids()

    sent = failed = 0
    status = await msg.reply_text(f"📢 Broadcasting to {len(user_ids)} users …")

    for uid in user_ids:
        try:
            await ctx.bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)   # rate limit

    await status.edit_text(
        f"✅ <b>Broadcast complete!</b>\n\n"
        f"✔️ Sent: {sent}\n❌ Failed: {failed}",
        parse_mode="HTML",
    )


# ── /ban ──────────────────────────────────────────────────────────────────────

async def ban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return

    msg = update.effective_message
    if not ctx.args:
        await msg.reply_text("Usage: /ban <user_id>")
        return

    try:
        uid = int(ctx.args[0])
    except ValueError:
        await msg.reply_text("❌ Invalid user ID.")
        return

    db = get_db()
    await db.ban_user(uid)
    await msg.reply_text(f"🚫 User <code>{uid}</code> has been banned.", parse_mode="HTML")

    if LOG_CHANNEL:
        await ctx.bot.send_message(
            LOG_CHANNEL,
            f"🚫 <b>User Banned</b>\nID: <code>{uid}</code>\n"
            f"By: {mention(update.effective_user.id, update.effective_user.full_name)}",
            parse_mode="HTML",
        )


# ── /unban ────────────────────────────────────────────────────────────────────

async def unban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return

    msg = update.effective_message
    if not ctx.args:
        await msg.reply_text("Usage: /unban <user_id>")
        return

    uid = int(ctx.args[0])
    db  = get_db()
    await db.unban_user(uid)
    await msg.reply_text(f"✅ User <code>{uid}</code> has been unbanned.", parse_mode="HTML")


# ── /addadmin ─────────────────────────────────────────────────────────────────

async def add_admin_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _require_owner(update):
        return

    msg = update.effective_message
    if not ctx.args:
        await msg.reply_text("Usage: /addadmin <user_id>")
        return

    uid = int(ctx.args[0])
    db  = get_db()
    await db.add_admin(uid)
    await msg.reply_text(f"✅ User <code>{uid}</code> is now an admin.", parse_mode="HTML")


# ── /removeadmin ──────────────────────────────────────────────────────────────

async def remove_admin_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _require_owner(update):
        return

    msg = update.effective_message
    if not ctx.args:
        await msg.reply_text("Usage: /removeadmin <user_id>")
        return

    uid = int(ctx.args[0])
    db  = get_db()
    await db.remove_admin(uid)
    await msg.reply_text(f"✅ Admin <code>{uid}</code> has been removed.", parse_mode="HTML")


# ── /restart ──────────────────────────────────────────────────────────────────

async def restart_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _require_owner(update):
        return

    await update.effective_message.reply_text("🔄 Restarting bot …")
    os.execv(sys.executable, [sys.executable] + sys.argv)


# ── /logs ─────────────────────────────────────────────────────────────────────

async def logs_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await _require_admin(update):
        return

    msg = update.effective_message
    log_file = "cantarella.log"

    if not os.path.exists(log_file):
        await msg.reply_text("❌ No log file found.")
        return

    try:
        with open(log_file, "rb") as f:
            await msg.reply_document(
                document=f,
                filename="cantarella.log",
                caption="📋 <b>Bot Logs</b>",
                parse_mode="HTML",
            )
    except Exception as e:
        await msg.reply_text(f"❌ Error sending logs: {e}")
