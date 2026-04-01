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
        BotCommand(command="list",       description="All unread links (or /list <tag>)"),
        BotCommand(command="review",     description="Weekend review — grouped by topic"),
        BotCommand(command="find",       description="Search — /find <keyword>"),
        BotCommand(command="tags",       description="Your full tag tree"),
        BotCommand(command="reading",    description="Start timer — /reading <id> <minutes>"),
        BotCommand(command="done",       description="Archive a link — /done <id>"),
        BotCommand(command="later",      description="Snooze to end of list — /later <id>"),
        BotCommand(command="pin",        description="Pin to top — /pin <id>"),
        BotCommand(command="tag",        description="Set tag — /tag <id> <tag>"),
        BotCommand(command="retag",      description="AI retag — /retag <id> or all"),
        BotCommand(command="title",       description="Set title — /title <id> <new title>"),
        BotCommand(command="del",        description="Delete a link — /del <id>"),
        BotCommand(command="duplicates", description="Scan and show all duplicate groups"),
        BotCommand(command="archive",    description="Browse done links"),
        BotCommand(command="help",       description="Full command reference"),
    ])
    logger.info("Bot commands registered")

    dp = Dispatcher()
    dp.include_router(commands.router)
    dp.include_router(messages.router)

    logger.info("Starting bot polling...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
