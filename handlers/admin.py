import logging

import aiofiles
import aiosqlite
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from core.config import (
    RE_WORD,
    USER_WORDS_FILE,
    ITEMS_PER_PAGE_WORDS,
    ITEMS_PER_PAGE_EMOJI,
)
from core.states import AdminStates
from utils.dictionaries import (
    STORAGE,
    ALL_WORDS_LIST,
    EMOJI_STORAGE,
    parse_and_add_word,
    sync_emoji_file,
)
from keyboards import get_words_editor_keyboard, get_emoji_editor_keyboard

logger = logging.getLogger(__name__)

router = Router()


def clamp_page(page: int, total_items: int, per_page: int) -> int:
    total_pages = max(1, (total_items - 1) // per_page + 1)
    return max(0, min(page, total_pages - 1))


async def _safe_edit_text(message, text, **kwargs):
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось отредактировать сообщение: {e}")
        return False
    return True


@router.message(Command("admin"))
async def cmd_admin(message: Message, command, user: dict, db):
    if user["is_admin"] < 1:
        return

    args = command.args.split() if command.args else []

    if not args:
        help_text = (
            "<b>Панель администратора</b>\n\n"
            "<b>Контент:</b>\n"
            "• <code>/admin stat</code> — Общая статистика\n"
            "• <code>/admin edit_words</code> — Редактор слов\n"
            "• <code>/admin edit_emoji</code> — Редактор ребусов\n\n"
            "<b>Системные:</b>\n"
            "• <code>/admin set_group</code> — Привязать текущий чат\n"
        )

        if user["is_admin"] >= 2:
            help_text += (
                "\n<b>Управление людьми (Только Владелец):</b>\n"
                "• <code>/admin set_admin [id] [0/1]</code> — Назначить/Снять админа\n"
                "• <code>/admin set_limit [id] [число]</code> — Изменить лимит\n"
                "• <code>/admin ban [id]</code> — Бан\n"
                "• <code>/admin unban [id]</code> — Разбан"
            )

        return await message.answer(help_text)

    sub = args[0].lower()

    if sub == "stat":
        await message.answer(
            f"<b>Статистика:</b>\n"
            f"Слов в словаре: {len(ALL_WORDS_LIST):,}\n"
            f"Эмодзи-ребусов: {len(EMOJI_STORAGE):,}"
        )

    elif sub == "set_group":
        await db.execute(
            "INSERT INTO settings (key, value) VALUES ('admin_group', ?) ON CONFLICT(key) DO UPDATE SET value=?",
            (str(message.chat.id), str(message.chat.id)),
        )
        await db.commit()
        await message.answer("Группа модерации привязана.")
        logger.info(f"Группа модерации установлена: {message.chat.id}")

    elif sub == "edit_words":
        await send_words_editor(message, 0)

    elif sub == "edit_emoji":
        await send_emoji_editor(message, 0)

    else:
        if user["is_admin"] < 2:
            return await message.answer("Недостаточно прав. Нужен уровень Владельца.")

        if sub == "set_admin" and len(args) == 3:
            try:
                target_id = int(args[1])
                level = int(args[2])
                if level not in [0, 1, 2]:
                    raise ValueError

                await db.execute(
                    "UPDATE users SET is_admin = ? WHERE tg_id = ?",
                    (level, target_id),
                )
                await db.commit()

                status = (
                    "Снят с должности"
                    if level == 0
                    else (
                        "Назначен Модератором" if level == 1 else "Назначен Владельцем"
                    )
                )
                await message.answer(
                    f"Пользователь <code>{target_id}</code>: {status} ({level})."
                )
            except ValueError:
                await message.answer(
                    "Ошибка. Пример: <code>/admin set_admin 123456789 1</code>"
                )

        elif sub == "set_limit" and len(args) == 3:
            try:
                target_id = int(args[1])
                limit = int(args[2])
                await db.execute(
                    "UPDATE users SET max_daily_limit = ? WHERE tg_id = ?",
                    (limit, target_id),
                )
                await db.commit()
                await message.answer(
                    f"Лимит запросов для <code>{target_id}</code> изменен на {limit}."
                )
                logger.info(f"Лимит пользователя {target_id} изменён на {limit}")
            except ValueError:
                await message.answer("ID и лимит должны быть числами.")

        elif sub == "ban" and len(args) == 2:
            try:
                target_id = int(args[1])
                await db.execute(
                    "UPDATE users SET is_banned = 1 WHERE tg_id = ?", (target_id,)
                )
                await db.commit()
                await message.answer(f"Пользователь <code>{target_id}</code> забанен.")
                logger.info(f"Пользователь {target_id} забанен")
            except ValueError:
                await message.answer("ID должен быть числом.")

        elif sub == "unban" and len(args) == 2:
            try:
                target_id = int(args[1])
                await db.execute(
                    "UPDATE users SET is_banned = 0 WHERE tg_id = ?", (target_id,)
                )
                await db.commit()
                await message.answer(f"Пользователь <code>{target_id}</code> разбанен.")
                logger.info(f"Пользователь {target_id} разбанен")
            except ValueError:
                await message.answer("ID должен быть числом.")


async def send_words_editor(target, page: int, query: str = None):
    words = []
    if USER_WORDS_FILE.exists():
        async with aiofiles.open(USER_WORDS_FILE, mode="r", encoding="utf-8") as f:
            words = (await f.read()).split()

    if query:
        words = [w for w in words if query.lower() in w.lower()]

    page = clamp_page(page, len(words), ITEMS_PER_PAGE_WORDS)
    markup = get_words_editor_keyboard(
        words, page, len(words), ITEMS_PER_PAGE_WORDS, query
    )
    txt = f"<b>Редактор слов</b>" + (f"\nФильтр: <code>{query}</code>" if query else "")

    if isinstance(target, Message):
        await target.answer(txt, reply_markup=markup)
    else:
        await _safe_edit_text(target.message, txt, reply_markup=markup)


@router.callback_query(F.data.startswith("ew_"))
async def editor_words_cb(call: CallbackQuery, state: FSMContext):
    parts = call.data.split("_", 2)
    action = parts[1]

    data = await state.get_data()
    query = data.get("qw")

    if action == "pg":
        if parts[2] == "0_reset":
            await state.update_data(qw=None)
            query = None
            page = 0
        else:
            page = int(parts[2])
        await send_words_editor(call, page, query)

    elif action == "srch":
        await call.message.answer("Отправьте часть слова для поиска:")
        await state.set_state(AdminStates.search_word_mode)
        await call.answer()

    elif action == "del":
        word_to_del = parts[2]
        if USER_WORDS_FILE.exists():
            async with aiofiles.open(USER_WORDS_FILE, mode="r", encoding="utf-8") as f:
                words = (await f.read()).split()
            if word_to_del in words:
                words.remove(word_to_del)
                async with aiofiles.open(
                    USER_WORDS_FILE, mode="w", encoding="utf-8"
                ) as f:
                    await f.write("\n".join(words))
                if word_to_del in ALL_WORDS_LIST:
                    ALL_WORDS_LIST.remove(word_to_del)
                key = "".join(sorted([c for c in word_to_del if c != "-"]))
                if key in STORAGE and word_to_del in STORAGE[key]:
                    STORAGE[key].remove(word_to_del)
                    if not STORAGE[key]:
                        del STORAGE[key]

                await call.answer(f"Удалено: {word_to_del}")
                await send_words_editor(call, 0, query)
                logger.info(f"Удалено слово: {word_to_del}")
            else:
                await call.answer("Слово не найдено в ulib.txt")


@router.message(AdminStates.search_word_mode)
async def search_word_result(message: Message, state: FSMContext):
    await state.update_data(qw=message.text.lower())
    await send_words_editor(message, 0, message.text.lower())
    await state.set_state(None)


async def send_emoji_editor(target, page: int, query: str = None):
    items = list(EMOJI_STORAGE.items())
    if query:
        query_l = query.lower()
        items = [i for i in items if query_l in i[0].lower() or query_l in i[1].lower()]

    page = clamp_page(page, len(items), ITEMS_PER_PAGE_EMOJI)
    markup = get_emoji_editor_keyboard(
        items, page, len(items), ITEMS_PER_PAGE_EMOJI, query
    )
    txt = f"<b>Редактор ребусов</b>" + (
        f"\nФильтр: <code>{query}</code>" if query else ""
    )

    if isinstance(target, Message):
        await target.answer(txt, reply_markup=markup)
    else:
        await _safe_edit_text(target.message, txt, reply_markup=markup)


@router.callback_query(F.data.startswith("ee_"))
async def editor_emoji_cb(call: CallbackQuery, state: FSMContext):
    parts = call.data.split("_", 2)
    action = parts[1]

    data = await state.get_data()
    query = data.get("qe")

    if action == "pg":
        if parts[2] == "0_reset":
            await state.update_data(qe=None)
            query = None
            page = 0
        else:
            page = int(parts[2])
        await send_emoji_editor(call, page, query)

    elif action == "srch":
        await call.message.answer("Отправьте эмодзи или текст для поиска:")
        await state.set_state(AdminStates.search_emoji_mode)
        await call.answer()

    elif action == "del":
        em_to_del = parts[2]
        if em_to_del in EMOJI_STORAGE:
            del EMOJI_STORAGE[em_to_del]
            await sync_emoji_file()
            await call.answer("Удалено!")
            await send_emoji_editor(call, 0, query)
            logger.info(f"Удалён ребус: {em_to_del}")
        else:
            await call.answer("Уже удалено.")


@router.message(AdminStates.search_emoji_mode)
async def search_emoji_result(message: Message, state: FSMContext):
    await state.update_data(qe=message.text)
    await send_emoji_editor(message, 0, message.text)
    await state.set_state(None)
