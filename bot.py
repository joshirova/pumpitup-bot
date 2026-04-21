# bot.py
import asyncio
from telegram.ext import ApplicationBuilder
from config import TELEGRAM_TOKEN

# Импортируем только функцию настройки, которая создаёт все нужные связи
from handlers.user_handlers import setup_handlers

def main():
    print("⚙️ Настройка приложения...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем все команды и обработчики из одного файла
    setup_handlers(app)
    
    print("🤖 Бот PumpItUp запущен! Ждите сообщения от пользователя.")
    try:
        app.run_polling()
    except KeyboardInterrupt:
        print("\n❌ Бот остановлен пользователем.")

if __name__ == "__main__":
    main()