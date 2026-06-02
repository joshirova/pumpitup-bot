"""PumpItUp — Telegram-бот для подбора персональных тренировок.

Запуск:
    python bot.py

Перед запуском создайте .env файл со строкой:
    TELEGRAM_TOKEN=<ваш токен от @BotFather>
"""

from telegram.ext import ApplicationBuilder, CommandHandler

from config import TELEGRAM_TOKEN
from handlers.conversation import cmd_help, get_conversation_handler


def main() -> None:
    if not TELEGRAM_TOKEN:
        raise SystemExit("TELEGRAM_TOKEN не задан в .env. См. README.md")

    print("⚙️  Запуск PumpItUp...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(get_conversation_handler())
    app.add_handler(CommandHandler("help", cmd_help))

    print("🤖 Бот запущен. Ctrl+C для остановки.")
    app.run_polling()


if __name__ == "__main__":
    main()
