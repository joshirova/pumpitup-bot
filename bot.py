# bot.py
from telegram.ext import ApplicationBuilder
from config import TELEGRAM_TOKEN
from handlers.user_handlers import setup_handlers


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()  # ← заменили TOKEN на TELEGRAM_TOKEN
    setup_handlers(app)
    print("🤖 Бот запущен. Жди сообщений в Telegram!")
    app.run_polling()


if __name__ == "__main__":
    main()
    