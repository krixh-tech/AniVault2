import asyncio
import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import LOG_CHANNEL
from database.db import get_db
from utils.aniwatch import get_episode_sources, get_servers, get_episodes
from utils.downloader import download_episode, upload_video, download_thumbnail
from utils.helpers import (
    build_quality_keyboard, build_server_keyboard,
    build_episodes_keyboard, check_subscription,
    FORCE_SUB_TEXT, safe_delete,
)
from handlers.search import anime_selected_handler, page_handler

logger = logging.getLogger(__name__)


# ── Catch-all callback router ─────────────────────────────────────────────────

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data or ""

    if data == "noop":
        await query.answer()
        return

    if data == "cancel":
        await query.answer("Closed.")
        await safe_delete(query.message)
        return

    if data == "check_sub":
        ok, kb = await check_subscription(query.get_bot(), query.from_user.id)
        if ok:
            await query.answer("✅ Verified! Welcome.")
            await query.message.delete()
        else:
            await query.answer("❌ You haven't joined yet!", show_alert=True)
        return

    if data == "show_help":
        from config import HELP_TEXT
        await query.edit_message_text(HELP_TEXT, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Back", callback_data="show_start")
            ]]))
        return

    if data == "show_start":
        from handlers.start import start_cmd
        await query.answer()
        await start_cmd(update, ctx)
        return

    if data == "show_schedule":
        from handlers.schedule import schedule_cmd
        await query.answer()
        await schedule_cmd(update, ctx)
        return

    if data == "show_stats":
        from handlers.admin import stats_cmd
        await query.answer()
        await stats_cmd(update, ctx)
        return

    if data.startswith("anime|"):
        await anime_selected_handler(update, ctx)
        return

    if data.startswith("page|"):
        await page_handler(update, ctx)
        return

    await query.answer("Unknown action.")


# ── Episode selected → show servers ──────────────────────────────────────────

async def episode_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Callback: eps|<episode_id>|<anime_id>"""
    query = update.callback_query
    user  = query.from_user
    await query.answer()

    ok, kb = await check_subscription(query.get_bot(), user.id)
    if not ok:
        await query.message.reply_text(FORCE_SUB_TEXT, reply_markup=kb, parse_mode="HTML")
        return

    db = get_db()
    if await db.is_banned(user.id):
        await query.answer("🚫 You are banned.", show_alert=True)
        return

    parts      = query.data.split("|")
    episode_id = parts[1]
    anime_id   = parts[2] if len(parts) > 2 else ""

    await query.edit_message_text(
        "⏳ <b>Loading servers …</b>", parse_mode="HTML"
    )

    servers = await get_servers(episode_id)
    if not servers.get("sub") and not servers.get("dub"):
        await query.edit_message_text(
            "❌ No servers available for this episode.\nTry another episode.",
            parse_mode="HTML",
        )
        return

    ep_num = episode_id.split("?ep=")[-1] if "?ep=" in episode_id else "?"
    text = (
        f"🎬 <b>Episode {ep_num}</b>\n\n"
        f"🖥 <b>Available Servers:</b>\n"
        f"Select a server to choose quality ↓"
    )

    back_rows = []
    if anime_id:
        back_rows.append([InlineKeyboardButton("⬅️ Back to Episodes", callback_data=f"page|{anime_id}|0")])

    kb = build_server_keyboard(episode_id, servers.get("sub", []), servers.get("dub", []))

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


# ── Server selected → show quality ───────────────────────────────────────────

async def server_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Callback: srv|<episode_id>|<server_name>|<category>"""
    query = update.callback_query
    await query.answer()

    _, episode_id, server, category = query.data.split("|")

    kb = build_quality_keyboard(episode_id, server, category)
    text = (
        f"🎯 <b>Select Quality</b>\n\n"
        f"🖥 Server: <code>{server}</code>\n"
        f"🎧 Type: <code>{category.upper()}</code>\n\n"
        f"Choose your preferred quality:"
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


# ── Quality selected → download ───────────────────────────────────────────────

async def quality_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Callback: qual|<episode_id>|<server>|<category>|<quality>"""
    query = update.callback_query
    user  = query.from_user
    await query.answer("⬇️ Starting download …")

    parts      = query.data.split("|")
    episode_id = parts[1]
    server     = parts[2]
    category   = parts[3]
    quality    = parts[4]

    db       = get_db()
    auto_del = await db.get_auto_del(user.id)

    prog_msg = await query.edit_message_text(
        f"⚙️ <b>Fetching stream from {server} …</b>",
        parse_mode="HTML",
    )

    # Get sources
    sources_data = await get_episode_sources(episode_id, server, category)

    if not sources_data or not sources_data.get("sources"):
        await prog_msg.edit_text(
            "❌ <b>Failed to fetch stream.</b>\n\n"
            "The server may be down. Try another server.",
            parse_mode="HTML",
        )
        return

    sources   = sources_data["sources"]
    subtitles = sources_data.get("tracks", [])

    # Find best URL for requested quality
    url = _pick_source(sources, quality)
    if not url:
        await prog_msg.edit_text(
            f"❌ <b>{quality} not available.</b>\n\n"
            "Try a different quality or server.",
            parse_mode="HTML",
        )
        return

    ep_label = episode_id.split("?ep=")[-1] if "?ep=" in episode_id else episode_id[:20]
    filename  = f"ep_{ep_label}_{quality}_{category}"

    # Download
    file_path = await download_episode(
        url=url,
        filename_base=filename,
        quality=quality,
        progress_msg=prog_msg,
        subtitles=subtitles or None,
    )

    if not file_path:
        await prog_msg.edit_text(
            "❌ <b>Download failed.</b>\n\n"
            "The file could not be downloaded. Try a different server or quality.",
            parse_mode="HTML",
        )
        return

    await prog_msg.edit_text("📤 <b>Uploading …</b>", parse_mode="HTML")

    caption = (
        f"🎬 <b>Episode {ep_label}</b>\n"
        f"🎯 <b>Quality:</b> {quality} | {category.upper()}\n"
        f"🖥 <b>Server:</b> {server}\n\n"
        f"<i>Downloaded via CANTARELLA Bot 🌸</i>"
    )

    sent = await upload_video(
        file_path=file_path,
        message=query.message,
        caption=caption,
    )

    if sent:
        await db.increment_downloads(user.id)
        await prog_msg.delete()

        # Log to channel
        if LOG_CHANNEL:
            try:
                await ctx.bot.send_message(
                    LOG_CHANNEL,
                    f"📥 <b>New Download</b>\n"
                    f"👤 User: {user.mention_html()}\n"
                    f"🆔 ID: <code>{user.id}</code>\n"
                    f"🎬 Ep: {ep_label} | {quality} | {category}\n"
                    f"🖥 Server: {server}",
                    parse_mode="HTML",
                )
            except Exception:
                pass

        # Auto-delete if configured
        if auto_del > 0:
            asyncio.create_task(_auto_delete(sent, auto_del))
    else:
        await prog_msg.edit_text("❌ Upload failed. Please try again.")


async def _auto_delete(msg, delay: int):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


def _pick_source(sources: list[dict], quality: str) -> str | None:
    """
    Pick the best stream URL for the given quality preference.
    Sources may be: {url, type, quality} or plain HLS manifests.
    """
    target_h = {"1080p": 1080, "720p": 720, "480p": 480, "360p": 360}.get(quality, 720)

    # Try exact quality match
    for s in sources:
        q_str = str(s.get("quality", "")).lower()
        if str(target_h) in q_str:
            return s.get("url", "")

    # If only HLS (m3u8) available, return first (yt-dlp handles quality inside)
    for s in sources:
        url = s.get("url", "")
        if url.endswith(".m3u8") or "m3u8" in url:
            return url

    # Fallback to first
    return sources[0].get("url", "") if sources else None
