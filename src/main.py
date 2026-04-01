import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from src.config import TELEGRAM_BOT_TOKEN
from src.db.links import init_db
from src.handlers import commands, messages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    await init_db()
    logger.info("Database initialized")

    bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode=ParseMode.HTML)
    bot["pending_tag"] = {}

    dp = Dispatcher()
    dp.include_router(commands.router)
    dp.include_router(messages.router)

    logger.info("Starting bot polling...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
