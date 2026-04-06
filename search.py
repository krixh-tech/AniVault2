import logging
from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultArticle, InputTextMessageContent,
    Update,
)
from telegram.ext import ContextTypes

from utils.aniwatch import search_anime, get_anime_info, get_episodes
from utils.helpers import (
    check_subscription, register_user, FORCE_SUB_TEXT,
    build_episodes_keyboard, truncate,
)
from database.db import get_db

logger = logging.getLogger(__name__)

# In-memory search result cache per user  {user_id: [anime_dict]}
_cache: dict[int, list[dict]] = {}


async def search_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg  = update.effective_message
    text = (msg.text or "").strip()

    await register_user(user)

    db = get_db()
    if await db.is_banned(user.id):
        await msg.reply_text("🚫 You are banned from using this bot.")
        return

    ok, kb = await check_subscription(update.get_bot(), user.id)
    if not ok:
        await msg.reply_text(FORCE_SUB_TEXT, reply_markup=kb, parse_mode="HTML")
        return

    # Extract query
    if ctx.args:
        query = " ".join(ctx.args)
    elif text and not text.startswith("/"):
        query = text
    else:
        await msg.reply_text(
            "🔍 <b>Search Anime</b>\n\nSend me an anime name!\n\n"
            "<i>Example: Naruto, Attack on Titan, One Piece …</i>",
            parse_mode="HTML",
        )
        return

    wait = await msg.reply_text(f"🔍 Searching for <b>{query}</b> …", parse_mode="HTML")

    results = await search_anime(query)

    if not results:
        await wait.edit_text(
            "❌ <b>No results found.</b>\n\n"
            "Try a different spelling or use the full title.",
            parse_mode="HTML",
        )
        return

    _cache[user.id] = results

    # Build keyboard: one button per result
    rows = []
    for idx, anime in enumerate(results):
        ep_info = ""
        if anime.get("sub_ep"):
            ep_info += f"📺 Sub:{anime['sub_ep']}"
        if anime.get("dub_ep"):
            ep_info += f"  🔊 Dub:{anime['dub_ep']}"
        label = f"{anime['name']} [{anime['type']}]"
        rows.append([
            InlineKeyboardButton(
                truncate(label, 60),
                callback_data=f"anime|{idx}",
            )
        ])

    rows.append([InlineKeyboardButton("❌ Close", callback_data="cancel")])

    text_out = f"🔍 <b>Results for:</b> {query}\n\n"
    text_out += "\n".join(
        f"<b>{i+1}.</b> {a['name']} [{a['type']}]"
        for i, a in enumerate(results)
    )

    await wait.edit_text(
        text_out,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def anime_selected_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Called when user taps an anime from search results (anime|idx callback)."""
    query = update.callback_query
    user  = query.from_user
    await query.answer()

    data = query.data  # "anime|idx"
    idx  = int(data.split("|")[1])

    cached = _cache.get(user.id, [])
    if idx >= len(cached):
        await query.edit_message_text("❌ Session expired. Please search again.")
        return

    anime = cached[idx]
    anime_id = anime["id"]

    wait_text = (
        f"⏳ <b>Fetching episodes for</b> {anime['name']} …"
    )
    await query.edit_message_text(wait_text, parse_mode="HTML")

    episodes = await get_episodes(anime_id)
    if not episodes:
        await query.edit_message_text(
            "❌ No episodes found for this anime.",
            parse_mode="HTML",
        )
        return

    info = await get_anime_info(anime_id)
    desc = truncate(info.get("description", "No description."), 300) if info else ""

    caption = (
        f"🌸 <b>{anime['name']}</b>\n"
        f"📺 <b>Type:</b> {anime.get('type', '?')}\n"
        f"🎬 <b>Episodes:</b> {len(episodes)}\n\n"
        f"<i>{desc}</i>\n\n"
        f"👇 <b>Select an episode to download:</b>"
    )

    kb = build_episodes_keyboard(anime_id, episodes, page=0)

    if anime.get("poster"):
        try:
            await query.message.reply_photo(
                photo=anime["poster"],
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb,
            )
            await query.message.delete()
            return
        except Exception:
            pass

    await query.edit_message_text(caption, parse_mode="HTML", reply_markup=kb)


async def page_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handles pagination callback: page|anime_id|page_num"""
    query = update.callback_query
    await query.answer()

    _, anime_id, page_str = query.data.split("|")
    page = int(page_str)

    episodes = await get_episodes(anime_id)
    if not episodes:
        await query.answer("❌ Could not load episodes.", show_alert=True)
        return

    kb = build_episodes_keyboard(anime_id, episodes, page=page)
    try:
        await query.edit_message_reply_markup(reply_markup=kb)
    except Exception:
        pass


# ── Inline query (type anime name in any chat) ────────────────────────────────

async def inline_query_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    inline = update.inline_query
    if not inline:
        return

    query = (inline.query or "").strip()
    if len(query) < 2:
        await inline.answer([], cache_time=0)
        return

    results_data = await search_anime(query)

    items = []
    for a in results_data[:8]:
        desc = f"{a['type']} | Sub: {a.get('sub_ep',0)} | Dub: {a.get('dub_ep',0)}"
        items.append(
            InlineQueryResultArticle(
                id=a["id"],
                title=a["name"],
                description=desc,
                thumbnail_url=a.get("poster", ""),
                input_message_content=InputTextMessageContent(
                    message_text=f"/search {a['name']}",
                ),
            )
        )

    await inline.answer(items, cache_time=30)
