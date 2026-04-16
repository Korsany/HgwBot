import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from core.config import MSK_TZ
from core.states import PotionStates
from keyboards import (
    get_potions_keyboard,
    get_potion_detail_keyboard,
    get_quality_keyboard,
)

logger = logging.getLogger(__name__)

router = Router()

ITEMS_PER_PAGE = 8

INGREDIENTS = [
    "луноросянка",
    "кристалл лунного камня",
    "пыльца визгоплюща",
    "серебристая слизь лукотруса",
    "нить акромантула",
    "шип гиппогрифа",
    "пепельный мох",
    "копытная стружка фестрала",
    "порошок рога двурога",
    "желчь болотной жабы",
]


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


async def has_potion_access(db, user_id: int) -> bool:
    """Проверка доступа к системе зелий"""
    async with db.execute(
        "SELECT user_id FROM potion_access WHERE user_id = ?", (user_id,)
    ) as cursor:
        return await cursor.fetchone() is not None


@router.message(Command("potions"))
async def cmd_potions(message: Message, user: dict, db):
    """Главная команда для работы с зельями"""
    logger.info(f"Команда /potions от пользователя {user['tg_id']}")

    has_access = await has_potion_access(db, user["tg_id"])
    logger.info(f"Доступ к зельям: {has_access}")

    if not has_access:
        logger.info("Отказано в доступе")
        return await message.answer("У вас нет доступа к дневнику зелий.")

    logger.info("Отправка списка зелий")
    await send_potions_list(message, 0, db)
    logger.info("Список зелий отправлен")


async def send_potions_list(target, page: int, db, query: str = None):
    """Отправка списка зелий"""
    logger.info(f"send_potions_list вызвана: page={page}, query={query}")

    sql = "SELECT id, name, ingredients, quality FROM potions"
    params = []

    if query:
        sql += " WHERE name LIKE ? OR ingredients LIKE ?"
        params = [f"%{query}%", f"%{query}%"]

    sql += " ORDER BY created_at DESC"

    async with db.execute(sql, params) as cursor:
        potions = await cursor.fetchall()

    logger.info(f"Найдено зелий: {len(potions)}")

    page = clamp_page(page, len(potions), ITEMS_PER_PAGE)
    markup = get_potions_keyboard(potions, page, len(potions), ITEMS_PER_PAGE, query)

    txt = f"<b>📖 Дневник зелий</b>\n\nВсего рецептов: {len(potions)}"
    if query:
        txt += f"\n🔍 Фильтр: <code>{query}</code>"

    logger.info(f"Отправка сообщения: {txt[:50]}...")

    if isinstance(target, Message):
        await target.answer(txt, reply_markup=markup)
    else:
        await _safe_edit_text(target.message, txt, reply_markup=markup)

    logger.info("Сообщение отправлено")


@router.callback_query(F.data.startswith("pot_"))
async def potions_callback(call: CallbackQuery, state: FSMContext, db, user: dict):
    """Обработка всех callback'ов зелий"""
    if not await has_potion_access(db, user["tg_id"]):
        return await call.answer("Нет доступа", show_alert=True)

    parts = call.data.split("_", 2)
    action = parts[1]

    data = await state.get_data()
    query = data.get("pot_query")

    if action == "pg":
        if parts[2] == "0_reset":
            await state.update_data(pot_query=None)
            query = None
            page = 0
        else:
            page = int(parts[2])
        await send_potions_list(call, page, db, query)
        await call.answer()

    elif action == "add":
        await call.message.answer(
            "📝 <b>Добавление нового зелья</b>\n\nВведите название зелья:"
        )
        await state.set_state(PotionStates.add_potion_name)
        await call.answer()

    elif action == "srch":
        await call.message.answer(
            "🔍 Введите текст для поиска (название или ингредиент):"
        )
        await state.set_state(PotionStates.search_potion_mode)
        await call.answer()

    elif action == "view":
        potion_id = int(parts[2])
        async with db.execute(
            "SELECT name, ingredients, quality, created_at FROM potions WHERE id = ?",
            (potion_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            name, ingredients, quality, created_at = row
            txt = (
                f"<b>{quality} {name}</b>\n\n"
                f"<b>Ингредиенты:</b>\n{ingredients}\n\n"
                f"<i>Добавлено: {created_at}</i>"
            )
            markup = get_potion_detail_keyboard(potion_id)
            await _safe_edit_text(call.message, txt, reply_markup=markup)
        else:
            await call.answer("Зелье не найдено", show_alert=True)

    elif action == "del":
        potion_id = int(parts[2])
        await db.execute("DELETE FROM potions WHERE id = ?", (potion_id,))
        await db.commit()
        await call.answer("Рецепт удалён")
        await send_potions_list(call, 0, db, query)
        logger.info(f"Удалено зелье ID {potion_id} пользователем {user['tg_id']}")

    elif action == "back":
        await send_potions_list(call, 0, db, query)
        await call.answer()

    elif action == "cancel":
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.message.answer("Отменено.")
        await state.clear()
        await call.answer()

    elif action == "q":
        quality = parts[2]
        data = await state.get_data()
        name = data.get("pot_name")
        ingredients = data.get("pot_ingredients")

        created_at = datetime.now(MSK_TZ).strftime("%Y-%m-%d %H:%M")

        await db.execute(
            "INSERT INTO potions (name, ingredients, quality, added_by, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, ingredients, quality, user["tg_id"], created_at),
        )
        await db.commit()

        try:
            await call.message.delete()
        except Exception:
            pass

        await call.message.answer(
            f"✅ Зелье добавлено!\n\n"
            f"<b>{quality} {name}</b>\n"
            f"Ингредиенты: {ingredients}"
        )
        await state.clear()
        await call.answer()
        logger.info(f"Добавлено зелье '{name}' пользователем {user['tg_id']}")


@router.message(PotionStates.add_potion_name)
async def add_potion_name(message: Message, state: FSMContext):
    """Получение названия зелья"""
    await state.update_data(pot_name=message.text.strip())
    await message.answer(
        "📝 Теперь введите ингредиенты.\n\n"
        "<b>Формат:</b>\n"
        "<code>луноросянка 4</code>\n"
        "или\n"
        "<code>пыльца визгоплюща 1\n"
        "кристалл лунного камня 2</code>\n\n"
        "<b>Доступные ингредиенты:</b>\n" + "\n".join(f"• {ing}" for ing in INGREDIENTS)
    )
    await state.set_state(PotionStates.add_potion_ingredients)


@router.message(PotionStates.add_potion_ingredients)
async def add_potion_ingredients(message: Message, state: FSMContext):
    """Получение ингредиентов зелья"""
    await state.update_data(pot_ingredients=message.text.strip())
    await message.answer(
        "📝 Выберите качество зелья:", reply_markup=get_quality_keyboard()
    )
    await state.set_state(None)


@router.message(PotionStates.search_potion_mode)
async def search_potion_result(message: Message, state: FSMContext, db):
    """Результат поиска зелий"""
    await state.update_data(pot_query=message.text.lower())
    await send_potions_list(message, 0, db, message.text.lower())
    await state.set_state(None)
