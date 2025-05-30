# bot.py
from telegram.ext import ApplicationBuilder
from config import TOKEN
from handlers.user_handlers import setup_handlers


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    setup_handlers(app)
    print("🤖 Бот запущен. Жди сообщений в Telegram!")
    app.run_polling()


if __name__ == "__main__":
    main()