import os
from dotenv import load_dotenv

load_dotenv()

# ── Core ──────────────────────────────────────────────────────────────────────
BOT_TOKEN          = os.environ.get("BOT_TOKEN", "")
BOT_USERNAME       = os.environ.get("BOT_USERNAME", "cantarella_bot")
OWNER_ID           = int(os.environ.get("OWNER_ID", 0))

# ── Telegram API (for Pyrogram-style tasks if needed) ────────────────────────
API_ID             = int(os.environ.get("API_ID", 0))
API_HASH           = os.environ.get("API_HASH", "")

# ── Database ─────────────────────────────────────────────────────────────────
MONGO_URI          = os.environ.get("MONGO_URI", "")
DB_NAME            = os.environ.get("DB_NAME", "cantarella")

# ── Channels / Groups ─────────────────────────────────────────────────────────
LOG_CHANNEL        = int(os.environ.get("LOG_CHANNEL", 0))
FORCE_SUB_CHANNEL  = os.environ.get("FORCE_SUB_CHANNEL", "")   # @username or -100xxx
FORCE_SUB_CHANNEL2 = os.environ.get("FORCE_SUB_CHANNEL2", "")  # optional second channel

# ── Admins ────────────────────────────────────────────────────────────────────
_admin_env         = os.environ.get("ADMINS", "")
ADMINS: list[int]  = [int(x) for x in _admin_env.split() if x.strip().lstrip("-").isdigit()]

# ── Download settings ─────────────────────────────────────────────────────────
DOWNLOAD_DIR       = os.environ.get("DOWNLOAD_DIR", "./downloads")
MAX_FILE_SIZE_MB   = int(os.environ.get("MAX_FILE_SIZE_MB", 2000))  # Telegram limit ~2 GB
DEFAULT_QUALITY    = os.environ.get("DEFAULT_QUALITY", "1080p")
PREFERRED_SERVER   = os.environ.get("PREFERRED_SERVER", "hd-1")   # hd-1, hd-2, megacloud

# ── Auto-delete ───────────────────────────────────────────────────────────────
AUTO_DELETE_DEFAULT = int(os.environ.get("AUTO_DELETE_DEFAULT", 600))  # seconds (10 min)

# ── Aniwatch API ──────────────────────────────────────────────────────────────
ANIWATCH_API_BASE  = os.environ.get(
    "ANIWATCH_API_BASE",
    "https://aniwatch-api.vercel.app"
)

# ── Timezone ──────────────────────────────────────────────────────────────────
TIMEZONE           = "Asia/Kolkata"   # IST

# ── Messages ──────────────────────────────────────────────────────────────────
START_TEXT = """
✨ <b>CANTARELLA – AniwatchTv Downloader</b> ✨

Hey {name}! 🌸
I'm your premium anime downloader bot.

<b>What I can do:</b>
🔍 Search any anime from Aniwatch
📥 Download in 360p / 480p / 720p / 1080p
🗓 Track airing schedule (IST)
⚡️ Fast downloads with live progress
🔔 Auto-notify for new episodes

<b>Get started:</b>
Send me an anime name or use /search

<i>Made with ❤️ by CANTARELLA</i>
"""

HELP_TEXT = """
📖 <b>CANTARELLA – Command Guide</b>

<b>General</b>
/start – Welcome message
/help – This guide
/search &lt;name&gt; – Search anime
/schedule – Today's airing anime (IST)
/ping – Bot latency
/stats – Bot statistics

<b>Tracking</b>
/track &lt;name&gt; – Auto-notify new episodes
/untrack &lt;name&gt; – Remove tracking

<b>Settings</b>
/autodel &lt;minutes&gt; – Auto-delete downloads
/manage – Inline management panel

<b>Admin Only</b>
/broadcast – Send message to all users
/ban &lt;user_id&gt; – Ban a user
/unban &lt;user_id&gt; – Unban a user
/addadmin &lt;user_id&gt; – Add admin
/removeadmin &lt;user_id&gt; – Remove admin
/restart – Restart the bot
/logs – Get bot logs
"""
