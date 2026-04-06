import logging
from datetime import datetime

import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import TIMEZONE
from database.db import get_db
from utils.aniwatch import get_schedule, get_episodes, search_anime
from utils.helpers import truncate

logger = logging.getLogger(__name__)
IST = pytz.timezone(TIMEZONE)


# ── /schedule ─────────────────────────────────────────────────────────────────

async def schedule_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    cb  = update.callback_query

    if cb:
        await cb.answer()

    wait = await (cb.edit_message_text if cb else msg.reply_text)(
        "⏳ <b>Fetching today's schedule …</b>", parse_mode="HTML"
    )

    now_ist = datetime.now(IST)
    date_str = now_ist.strftime("%Y-%m-%d")
    schedule = await get_schedule(date_str)

    if not schedule:
        text = (
            "🗓 <b>Anime Schedule</b>\n\n"
            "No airing anime found for today.\n"
            "<i>Data provided by Aniwatch</i>"
        )
        await wait.edit_text(text, parse_mode="HTML")
        return

    lines = [f"🗓 <b>Airing Schedule – {now_ist.strftime('%d %b %Y')} (IST)</b>\n"]
    for i, a in enumerate(schedule[:25], 1):
        name     = a.get("name") or a.get("title", "Unknown")
        airing_at = a.get("airingAt") or a.get("time", "")
        ep        = a.get("episode") or a.get("ep", "?")
        lines.append(f"<b>{i}.</b> {truncate(name, 40)} — Ep {ep}"
                     + (f" @ {airing_at}" if airing_at else ""))

    lines.append("\n<i>🌸 Use /track &lt;name&gt; to get notified!</i>")

    await wait.edit_text("\n".join(lines), parse_mode="HTML")


# ── /track ────────────────────────────────────────────────────────────────────

async def track_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    user = update.effective_user

    if not ctx.args:
        await msg.reply_text(
            "📌 <b>Track an Anime</b>\n\n"
            "Usage: /track &lt;anime name&gt;\n\n"
            "I'll notify you when a new episode is available!",
            parse_mode="HTML",
        )
        return

    query = " ".join(ctx.args)
    wait  = await msg.reply_text(f"🔍 Searching for <b>{query}</b> …", parse_mode="HTML")

    results = await search_anime(query)
    if not results:
        await wait.edit_text("❌ Anime not found.")
        return

    # If multiple, ask user to pick
    if len(results) == 1:
        anime = results[0]
        db    = get_db()
        await db.track_anime(user.id, anime["id"], anime["name"])
        await wait.edit_text(
            f"✅ <b>Now tracking:</b> {anime['name']}\n\n"
            f"I'll notify you when new episodes drop! 🔔",
            parse_mode="HTML",
        )
        return

    rows = [
        [InlineKeyboardButton(
            truncate(a["name"], 50),
            callback_data=f"track_pick|{a['id']}|{a['name'][:30]}"
        )]
        for a in results[:8]
    ]
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])

    await wait.edit_text(
        f"🔍 Multiple results for <b>{query}</b>. Pick one:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(rows),
    )


# ── /untrack ─────────────────────────────────────────────────────────────────

async def untrack_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.effective_message
    user = update.effective_user

    db      = get_db()
    tracked = await db.get_tracked(user.id)

    if not tracked:
        await msg.reply_text("📌 You are not tracking any anime.")
        return

    if ctx.args:
        # Try to match by name
        query = " ".join(ctx.args).lower()
        match = next((t for t in tracked if query in t["anime_name"].lower()), None)
        if match:
            await db.untrack_anime(user.id, match["anime_id"])
            await msg.reply_text(f"✅ Untracked: <b>{match['anime_name']}</b>", parse_mode="HTML")
            return
        else:
            await msg.reply_text("❌ No tracked anime matched that name.")
            return

    # Show list with untrack buttons
    rows = [
        [InlineKeyboardButton(
            f"❌ {truncate(t['anime_name'], 40)}",
            callback_data=f"untrack|{t['anime_id']}"
        )]
        for t in tracked
    ]
    rows.append([InlineKeyboardButton("Close", callback_data="cancel")])

    await msg.reply_text(
        "📌 <b>Your tracked anime:</b>\nTap to untrack:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(rows),
    )


# ── Background job: check for new episodes ───────────────────────────────────

async def check_airing(ctx: ContextTypes.DEFAULT_TYPE):
    """
    Runs hourly. Checks all tracked anime for new episodes
    and notifies users.
    """
    db      = get_db()
    tracked = await db.get_all_tracked()

    if not tracked:
        return

    notified: dict[tuple, bool] = {}

    for entry in tracked:
        uid       = entry["user_id"]
        anime_id  = entry["anime_id"]
        anime_name = entry["anime_name"]
        last_ep   = entry.get("last_ep", 0)

        cache_key = (anime_id,)
        if cache_key not in notified:
            episodes = await get_episodes(anime_id)
            notified[cache_key] = episodes
        else:
            episodes = notified[cache_key]

        if not episodes:
            continue

        latest_ep = max(e["number"] for e in episodes)
        if latest_ep > last_ep:
            # New episode!
            await db.update_last_ep(uid, anime_id, latest_ep)

            # Find episode id for the latest ep
            latest_data = next((e for e in episodes if e["number"] == latest_ep), None)
            ep_id = latest_data["episode_id"] if latest_data else ""

            kb = None
            if ep_id:
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        f"📥 Download Ep {latest_ep}",
                        callback_data=f"eps|{ep_id}|{anime_id}"
                    )
                ]])

            try:
                await ctx.bot.send_message(
                    uid,
                    f"🔔 <b>New Episode Available!</b>\n\n"
                    f"🌸 <b>{anime_name}</b>\n"
                    f"📺 Episode {latest_ep} is out!\n\n"
                    f"<i>Tap below to download 👇</i>",
                    parse_mode="HTML",
                    reply_markup=kb,
                )
            except Exception as e:
                logger.warning("Could not notify user %s: %s", uid, e)
