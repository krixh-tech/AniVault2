"""
Download anime episodes using yt-dlp (supports HLS / m3u8 streams).
"""
import asyncio
import logging
import os
import re
import time
from pathlib import Path

import yt_dlp
from telegram import Message

from config import DOWNLOAD_DIR, MAX_FILE_SIZE_MB

logger = logging.getLogger(__name__)

DOWNLOAD_PATH = Path(DOWNLOAD_DIR)
DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)

# ── Progress bar helpers ──────────────────────────────────────────────────────

def _bar(pct: float, width: int = 16) -> str:
    filled = int(width * pct / 100)
    return "█" * filled + "░" * (width - filled)


def _human(size_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _speed(bps: float) -> str:
    return _human(bps) + "/s"


# ── Core download function ────────────────────────────────────────────────────

async def download_episode(
    url: str,
    filename_base: str,
    quality: str,
    progress_msg: Message,
    subtitles: list | None = None,
) -> Path | None:
    """
    Download a single episode stream.
    Returns the Path to the downloaded file, or None on failure.
    """
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", filename_base)
    out_path   = DOWNLOAD_PATH / f"{safe_name}.%(ext)s"
    final_path: Path | None = None

    last_update   = [0.0]
    UPDATE_EVERY  = 3  # seconds

    async def _edit(text: str):
        try:
            await progress_msg.edit_text(text, parse_mode="HTML")
        except Exception:
            pass

    def progress_hook(d: dict):
        nonlocal final_path

        status = d.get("status")
        if status == "downloading":
            now = time.time()
            if now - last_update[0] < UPDATE_EVERY:
                return
            last_update[0] = now

            total     = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            spd       = d.get("speed", 0) or 0
            eta       = d.get("eta", 0) or 0
            pct       = (downloaded / total * 100) if total else 0

            bar  = _bar(pct)
            text = (
                f"⬇️ <b>Downloading …</b>\n\n"
                f"<code>[{bar}] {pct:.1f}%</code>\n\n"
                f"📦 <b>Size:</b> {_human(downloaded)} / {_human(total)}\n"
                f"⚡️ <b>Speed:</b> {_speed(spd)}\n"
                f"⏱ <b>ETA:</b> {eta}s\n"
                f"🎬 <b>Quality:</b> {quality}"
            )
            asyncio.get_event_loop().call_soon_threadsafe(
                lambda: asyncio.ensure_future(_edit(text))
            )

        elif status == "finished":
            final_path = Path(d["filename"])

    # Resolve best format string for requested quality
    height_map = {
        "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "720p":  "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "480p":  "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
        "360p":  "bestvideo[height<=360]+bestaudio/best[height<=360]/best",
        "best":  "bestvideo+bestaudio/best",
    }
    fmt = height_map.get(quality, height_map["720p"])

    ydl_opts = {
        "format":            fmt,
        "outtmpl":           str(out_path),
        "progress_hooks":    [progress_hook],
        "quiet":             True,
        "no_warnings":       True,
        "merge_output_format": "mp4",
        "postprocessors":    [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
        "http_headers":      {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://aniwatch.to/",
        },
        "concurrent_fragment_downloads": 5,
        "retries":           5,
        "fragment_retries":  10,
    }

    # Add subtitle download if tracks provided
    if subtitles:
        ydl_opts["writesubtitles"]      = True
        ydl_opts["subtitleslangs"]      = ["en"]
        ydl_opts["embedsubtitles"]      = True

    try:
        await _edit(
            f"⚙️ <b>Preparing download …</b>\n\n"
            f"🎬 <b>Quality:</b> {quality}\n"
            f"🌐 <b>Processing stream …</b>"
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: _do_download(url, ydl_opts)
        )

        if final_path and final_path.exists():
            size_mb = final_path.stat().st_size / (1024 * 1024)
            if size_mb > MAX_FILE_SIZE_MB:
                logger.warning("File too large: %.1f MB", size_mb)
                final_path.unlink(missing_ok=True)
                return None
            return final_path

        # Fallback: find mp4 in download dir
        for f in DOWNLOAD_PATH.glob(f"{safe_name}*.mp4"):
            return f
        return None

    except Exception as e:
        logger.error("Download error: %s", e)
        return None


def _do_download(url: str, opts: dict):
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])


# ── Upload with progress ──────────────────────────────────────────────────────

async def upload_video(
    file_path: Path,
    message: Message,
    caption: str,
    thumb_path: Path | None = None,
) -> Message | None:
    """Upload a local video file to Telegram with progress indicator."""

    last_update = [0.0]
    UPDATE_EVERY = 4

    progress_msg = await message.reply_text(
        "📤 <b>Uploading to Telegram …</b>\n\n<code>[░░░░░░░░░░░░░░░░] 0%</code>",
        parse_mode="HTML",
    )

    async def _progress(current: int, total: int):
        now = time.time()
        if now - last_update[0] < UPDATE_EVERY:
            return
        last_update[0] = now
        pct = current / total * 100 if total else 0
        bar = _bar(pct)
        try:
            await progress_msg.edit_text(
                f"📤 <b>Uploading to Telegram …</b>\n\n"
                f"<code>[{bar}] {pct:.1f}%</code>\n\n"
                f"📦 {_human(current)} / {_human(total)}",
                parse_mode="HTML",
            )
        except Exception:
            pass

    try:
        with open(file_path, "rb") as f:
            sent = await message.reply_video(
                video=f,
                caption=caption,
                parse_mode="HTML",
                supports_streaming=True,
                thumbnail=open(thumb_path, "rb") if thumb_path and thumb_path.exists() else None,
                write_timeout=60,
                read_timeout=60,
                connect_timeout=30,
                progress=_progress,
            )
        await progress_msg.delete()
        return sent
    except Exception as e:
        logger.error("Upload error: %s", e)
        try:
            await progress_msg.edit_text(f"❌ Upload failed: {e}")
        except Exception:
            pass
        return None
    finally:
        file_path.unlink(missing_ok=True)
        if thumb_path:
            thumb_path.unlink(missing_ok=True)


# ── Thumbnail downloader ──────────────────────────────────────────────────────

async def download_thumbnail(url: str, name: str) -> Path | None:
    if not url:
        return None
    import aiohttp
    thumb_path = DOWNLOAD_PATH / f"thumb_{name}.jpg"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    thumb_path.write_bytes(await r.read())
                    return thumb_path
    except Exception as e:
        logger.warning("Thumbnail download failed: %s", e)
    return None
