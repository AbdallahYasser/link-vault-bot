import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

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

    bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await bot.set_my_commands([
        BotCommand(command="list",       description="Browse links by tag"),
        BotCommand(command="find",       description="Search by title or tag — /find <keyword>"),
        BotCommand(command="review",     description="All links grouped by topic"),
        BotCommand(command="archive",    description="Links you've finished"),
        BotCommand(command="tags",       description="Your tag tree with counts"),
        BotCommand(command="tag",        description="Change tag — /tag <id> <tag>"),
        BotCommand(command="retag",      description="AI retag — /retag <id> or retag all"),
        BotCommand(command="duplicates", description="Find and merge similar tags"),
        BotCommand(command="done",       description="Mark as finished — /done <id>"),
        BotCommand(command="pin",        description="Pin to top — /pin <id>"),
        BotCommand(command="later",      description="Snooze to end of list — /later <id>"),
        BotCommand(command="title",      description="Update title — /title <id> <text>"),
        BotCommand(command="del",        description="Delete a link — /del <id>"),
        BotCommand(command="export",     description="Download links as a .json file"),
        BotCommand(command="reading",    description="Reading timer — /reading <id> <minutes>"),
        BotCommand(command="help",       description="All commands"),
    ])
    logger.info("Bot commands registered")

    dp = Dispatcher()
    dp.include_router(commands.router)
    dp.include_router(messages.router)

    logger.info("Starting bot polling...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
