import logging
from datetime import datetime

import aiosqlite
from aiogram.types import Message
from aiogram.enums import ChatType
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from core.config import MSK_TZ, DB_FILE
from database.db import get_admin_group

logger = logging.getLogger(__name__)


class CoreMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        tg_user = event.from_user
        if not tg_user:
            return await handler(event, data)

        today = datetime.now(MSK_TZ).strftime("%Y-%m-%d")

        async with aiosqlite.connect(DB_FILE, timeout=30.0) as db:
            await db.execute("PRAGMA busy_timeout=30000")
            db.row_factory = aiosqlite.Row

            await db.execute(
                "INSERT INTO users (tg_id, username, full_name, created_at, last_request_date) VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                (tg_user.id, tg_user.username, tg_user.full_name, today, today),
            )

            async with db.execute(
                "SELECT * FROM users WHERE tg_id = ?", (tg_user.id,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                logger.warning(f"Пользователь {tg_user.id} не найден после INSERT")
                return

            user_data = dict(row)

            if user_data["is_banned"]:
                logger.info(f"Забаненный пользователь {tg_user.id} заблокирован")
                return

            if user_data["last_request_date"] != today:
                user_data["daily_requests"] = 0
                await db.execute(
                    "UPDATE users SET daily_requests = 0, last_request_date = ? WHERE tg_id = ?",
                    (today, tg_user.id),
                )
                await db.commit()

            if (
                isinstance(event, Message)
                and event.chat
                and event.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
            ):
                is_admin_cmd = event.text and event.text.startswith("/admin")
                if not (is_admin_cmd and user_data["is_admin"] >= 1):
                    admin_group = await get_admin_group()
                    if event.chat.id != admin_group:
                        return
                    if not event.text or not event.text.startswith("/"):
                        return

            data["user"] = user_data
            data["db"] = db

            return await handler(event, data)
