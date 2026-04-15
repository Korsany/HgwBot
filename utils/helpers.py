import asyncio
import logging
from datetime import datetime

import aiohttp
from aiogram import Bot
from aiogram.types import BotCommand, FSInputFile

from core.config import MSK_TZ, BACKUP_INTERVAL_SECONDS, DB_FILE
from database.db import get_admin_group

logger = logging.getLogger(__name__)


async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="📖 Инструкция"),
        BotCommand(command="quiz", description="🎮 Игра-Квиз"),
        BotCommand(command="profile", description="👤 Мой профиль"),
        BotCommand(command="new", description="➕ Предложить слово/ребус"),
    ]
    await bot.set_my_commands(commands)


async def upload_log(content: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.pastes.dev/post", data=content.encode("utf-8")
            ) as resp:
                res = await resp.json()
                return f"https://pastes.dev/{res['key']}"
    except Exception:
        logger.exception("Не удалось выгрузить лог на pastes.dev")
        return "Не удалось выгрузить лог"


async def backup_scheduler(bot: Bot, stop_event: asyncio.Event):
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=BACKUP_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            pass

        if stop_event.is_set():
            break

        admin_group = await get_admin_group()
        if admin_group:
            try:
                await bot.send_document(
                    admin_group,
                    FSInputFile(DB_FILE),
                    caption=f"Бэкап БД ({datetime.now(MSK_TZ).strftime('%d.%m.%Y')})",
                )
                logger.info("Ежедневный бэкап отправлен")
            except Exception:
                logger.exception("Ошибка при отправке бэкапа")
