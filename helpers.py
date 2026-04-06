import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update, User
from telegram.error import TelegramError

from config import ADMINS, FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, OWNER_ID
from database.db import get_db

logger = logging.getLogger(__name__)


# ── Permission checks ─────────────────────────────────────────────────────────

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


async def is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID or user_id in ADMINS:
        return True
    db = get_db()
    return await db.is_admin(user_id)


# ── Force-subscribe ───────────────────────────────────────────────────────────

async def check_subscription(bot: Bot, user_id: int) -> tuple[bool, InlineKeyboardMarkup | None]:
    """
    Returns (is_subscribed, join_keyboard).
    If the user has joined all required channels → (True, None).
    """
    channels = [c for c in [FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2] if c]
    if not channels:
        return True, None

    buttons = []
    not_joined = []

    for ch in channels:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status in ("left", "kicked", "banned"):
                not_joined.append(ch)
                chat = await bot.get_chat(ch)
                invite = chat.invite_link or f"https://t.me/{ch.lstrip('@')}"
                buttons.append([InlineKeyboardButton(f"📢 Join {chat.title}", url=invite)])
        except TelegramError as e:
            logger.warning("Force-sub check error for %s: %s", ch, e)

    if not_joined:
        buttons.append([InlineKeyboardButton("✅ I Joined – Continue", callback_data="check_sub")])
        return False, InlineKeyboardMarkup(buttons)

    return True, None


FORCE_SUB_TEXT = (
    "🔒 <b>Join Required!</b>\n\n"
    "You must join our channel(s) to use this bot.\n"
    "Click the buttons below, then tap <b>I Joined</b>."
)


# ── User registration helper ──────────────────────────────────────────────────

async def register_user(user: User):
    db = get_db()
    await db.add_user(
        user_id=user.id,
        name=user.full_name,
        username=user.username or "",
    )


# ── Keyboard builders ─────────────────────────────────────────────────────────

def build_quality_keyboard(episode_id: str, server: str, category: str) -> InlineKeyboardMarkup:
    qualities = ["360p", "480p", "720p", "1080p"]
    rows = []
    row  = []
    for q in qualities:
        row.append(
            InlineKeyboardButton(q, callback_data=f"qual|{episode_id}|{server}|{category}|{q}")
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def build_server_keyboard(episode_id: str, servers_sub: list, servers_dub: list) -> InlineKeyboardMarkup:
    rows = []

    if servers_sub:
        rows.append([InlineKeyboardButton("── SUB ──", callback_data="noop")])
        row = []
        for srv in servers_sub[:4]:
            name = srv.get("serverName", srv.get("name", "hd-1"))
            row.append(
                InlineKeyboardButton(
                    f"🎧 {name}",
                    callback_data=f"srv|{episode_id}|{name}|sub",
                )
            )
            if len(row) == 2:
                rows.append(row)
                row = []
        if row:
            rows.append(row)

    if servers_dub:
        rows.append([InlineKeyboardButton("── DUB ──", callback_data="noop")])
        row = []
        for srv in servers_dub[:4]:
            name = srv.get("serverName", srv.get("name", "hd-1"))
            row.append(
                InlineKeyboardButton(
                    f"🔊 {name}",
                    callback_data=f"srv|{episode_id}|{name}|dub",
                )
            )
            if len(row) == 2:
                rows.append(row)
                row = []
        if row:
            rows.append(row)

    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


def build_episodes_keyboard(
    anime_id: str,
    episodes: list[dict],
    page: int = 0,
    page_size: int = 20,
) -> InlineKeyboardMarkup:
    start = page * page_size
    end   = start + page_size
    page_eps = episodes[start:end]

    rows = []
    row  = []
    for ep in page_eps:
        num = ep["number"]
        ep_id = ep["episode_id"]
        label = f"{'⚡' if ep.get('is_filler') else ''}{num}"
        row.append(
            InlineKeyboardButton(label, callback_data=f"eps|{ep_id}|{anime_id}")
        )
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page|{anime_id}|{page-1}"))
    if end < len(episodes):
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"page|{anime_id}|{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton("❌ Close", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


# ── Misc ──────────────────────────────────────────────────────────────────────

def truncate(text: str, max_len: int = 200) -> str:
    return text if len(text) <= max_len else text[:max_len - 3] + "…"


def mention(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{name}</a>'


async def safe_delete(msg):
    try:
        await msg.delete()
    except Exception:
        pass
