import asyncio
import logging
import signal

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from core.config import BOT_TOKEN
from core.middleware import CoreMiddleware
from database.db import init_db
from utils.dictionaries import load_dictionaries
from utils.helpers import setup_bot_commands, backup_scheduler
from handlers import commands, proposals, admin, decipher, potions

logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    return Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    router = Router()

    router.message.middleware(CoreMiddleware())
    router.callback_query.middleware(CoreMiddleware())

    router.include_router(commands.router)
    router.include_router(proposals.router)
    router.include_router(admin.router)
    router.include_router(potions.router)
    router.include_router(decipher.router)

    dp.include_router(router)

    return dp


async def on_shutdown(bot: Bot):
    logger.info("Бот завершает работу...")
    await bot.delete_webhook()
    await bot.session.close()
    logger.info("Бот остановлен")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    logger.info("Инициализация базы данных...")
    await init_db()

    logger.info("Загрузка словарей...")
    await load_dictionaries()

    bot = create_bot()
    dp = create_dispatcher()

    dp.shutdown.register(on_shutdown)

    await setup_bot_commands(bot)

    stop_event = asyncio.Event()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    backup_task = asyncio.create_task(backup_scheduler(bot, stop_event))

    logger.info("Бот успешно запущен!")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        stop_event.set()
        backup_task.cancel()
        try:
            await backup_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
