import os
import aiohttp
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

DOWNLOAD_DIR = "downloads"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)


async def download_episode(url: str, file_name: str):
    file_path = os.path.join(DOWNLOAD_DIR, file_name)

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None

            with open(file_path, "wb") as f:
                while True:
                    chunk = await resp.content.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)

    return file_path


async def upload_video(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str):
    msg = await update.message.reply_text("📤 Uploading video...")

    try:
        await update.message.reply_video(
            video=open(file_path, "rb"),
            caption="🎬 Episode Downloaded Successfully!"
        )

        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Upload failed: {e}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def handle_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please provide video URL")
        return

    url = context.args[0]

    status = await update.message.reply_text("⬇️ Downloading episode...")

    file_path = await download_episode(url, "episode.mp4")

    if not file_path:
        await status.edit_text("❌ Download failed")
        return

    await status.edit_text("✅ Download complete!")

    await upload_video(update, context, file_path)
