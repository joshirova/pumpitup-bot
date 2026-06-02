import asyncio
from telegram import Bot
from config import TELEGRAM_TOKEN

async def main():
    bot = Bot(TELEGRAM_TOKEN)
    me = await bot.get_me()
    print("Бот найден:", me.username)

asyncio.run(main())