from telegram.ext import Application, CommandHandler
from handlers.start import start_cmd, help_cmd
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

def main():

    app = Application.builder().token(BOT_TOKEN).build()

    # commands
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))

    print("Bot Started Successfully")

    app.run_polling()

if __name__ == "__main__":
    main()
