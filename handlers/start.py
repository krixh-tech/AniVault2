from telegram import Update
from telegram.ext import ContextTypes

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello!\n\nAnime Downloader Bot is running 🚀"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n/start - start bot\n/help - help menu"
    )
