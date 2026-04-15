import logging

import aiofiles
import aiosqlite
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from core.config import RE_WORD, USER_WORDS_FILE
from database.db import get_admin_group
from utils.dictionaries import (
    STORAGE,
    EMOJI_STORAGE,
    parse_and_add_word,
    sync_emoji_file,
)
from keyboards import get_moderation_keyboard

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("new"))
async def cmd_new(message: Message, bot, db, user: dict):
    raw_text = message.text[4:].strip()
    if not raw_text:
        return await message.answer(
            "<b>Формат использования:</b>\n/new слово1 слово2\n<i>ИЛИ</i>\n/new 🍎🦊\nЛиса с яблоком"
        )

    admin_chat = await get_admin_group()
    if not admin_chat:
        return await message.answer(
            "Группа модерации не привязана. Используйте /admin set_group"
        )

    user_info = f"{message.from_user.full_name} (ID: {message.from_user.id})"

    if "\n" in raw_text:
        emojis, desc = raw_text.split("\n", 1)
        clean_emojis, desc = emojis.strip().replace(" ", ""), desc.strip().title()

        if clean_emojis in EMOJI_STORAGE:
            return await message.answer(
                f"Этот ребус уже есть в базе.\nОтвет: <code>{EMOJI_STORAGE[clean_emojis]}</code>"
            )

        cursor = await db.execute(
            "INSERT INTO proposals (type, content, description, user_id) VALUES (?,?,?,?)",
            ("emoji", clean_emojis, desc, message.from_user.id),
        )
        prop_id = cursor.lastrowid
        await db.commit()

        kb = get_moderation_keyboard(prop_id)
        await bot.send_message(
            admin_chat,
            f"<b>Новая предложка (эмодзи)</b>\nОт: {user_info}\n\nЭмодзи: {clean_emojis}\nОтвет: {desc}",
            reply_markup=kb,
        )
        await message.answer("Ребус отправлен на модерацию.")

    else:
        words = RE_WORD.findall(raw_text.lower())
        added_count = 0

        for w in words:
            letters = "".join(sorted([c for c in w if c != "-"]))
            if letters in STORAGE and w in STORAGE[letters]:
                continue

            cursor = await db.execute(
                "INSERT INTO proposals (type, content, user_id) VALUES (?,?,?)",
                ("word", w, message.from_user.id),
            )
            prop_id = cursor.lastrowid

            kb = get_moderation_keyboard(prop_id)
            await bot.send_message(
                admin_chat,
                f"<b>Новая предложка (слово)</b>\nОт: {user_info}\n\nСлово: <code>{w}</code>",
                reply_markup=kb,
            )
            added_count += 1

        await db.commit()

        if added_count == 0:
            await message.answer("Все эти слова уже есть в базе.")
        else:
            await message.answer(f"Отправлено на модерацию новых слов: {added_count}.")


async def _safe_edit_text(message, text, **kwargs):
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось отредактировать сообщение: {e}")
        return False
    return True


@router.callback_query(F.data.startswith("prp_"))
async def moderation_cb(call: CallbackQuery, db, bot):
    parts = call.data.split("_")
    action, prop_id = parts[1], int(parts[2])
    reason_code = parts[3] if len(parts) > 3 else None

    async with db.execute(
        "SELECT type, content, description, user_id FROM proposals WHERE id = ?",
        (prop_id,),
    ) as cursor:
        prop = await cursor.fetchone()

    if not prop:
        return await call.answer(
            "Предложка не найдена (возможно, уже обработана).", show_alert=True
        )

    prop_type, content, desc, author_id = prop[0], prop[1], prop[2], prop[3]

    if action == "a":
        if prop_type == "word":
            async with aiofiles.open(USER_WORDS_FILE, mode="a", encoding="utf-8") as f:
                await f.write(f"{content}\n")
            parse_and_add_word(content)
            success = await _safe_edit_text(
                call.message, f"<b>Одобрено слово:</b> <code>{content}</code>"
            )
            notify_text = f"Слово <code>{content}</code> добавлено в словарь."
            logger.info(f"Одобрено слово: {content} от пользователя {author_id}")
        else:
            EMOJI_STORAGE[content] = desc
            await sync_emoji_file()

            try:
                author = await bot.get_chat(author_id)
                author_name = author.first_name
            except Exception:
                author_name = "Пользователь"

            success = await _safe_edit_text(
                call.message,
                f"<b>Одобрен ребус:</b>\n{content}\n{desc}\n<i>от {author_name}</i>",
            )
            notify_text = f"Ребус {content} ({desc}) добавлен в базу."
            logger.info(f"Одобрен ребус: {content} от пользователя {author_id}")

        await db.execute(
            "UPDATE users SET approved_proposals = approved_proposals + 1 WHERE tg_id = ?",
            (author_id,),
        )
        await db.execute("DELETE FROM proposals WHERE id = ?", (prop_id,))
        await db.commit()

    else:
        reasons = {
            "typo": "Опечатка",
            "dup": "Уже есть в базе",
            "spam": "Спам/Некорректный формат",
        }
        reason_text = reasons.get(reason_code, "Отклонено модератором")

        await _safe_edit_text(
            call.message, f"<b>Отклонено ({reason_text}):</b> {content}"
        )
        notify_text = (
            f"Предложение <code>{content}</code> отклонено.\nПричина: {reason_text}."
        )
        logger.info(f"Отклонена предложка #{prop_id}: {reason_text}")

        await db.execute("DELETE FROM proposals WHERE id = ?", (prop_id,))
        await db.commit()

    await call.answer("Обработано!")

    try:
        await bot.send_message(author_id, notify_text)
    except Exception:
        logger.debug(f"Не удалось отправить уведомление пользователю {author_id}")
