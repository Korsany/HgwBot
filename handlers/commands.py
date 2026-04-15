from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    text = (
        "Привет! Я магический дешифратор анаграмм и ребусов. 🪄\n\n"
        "Просто отправь мне бессвязный набор букв или эмодзи, и я попробую понять, что это значит! "
        "Поддерживаются дефисы (например: <code>само-собой-собой</code>).\n\n"
        "<blockquote><b>📝 Как работают анаграммы:</b>\n"
        "Кидаешь: <code>гоанв ляд таосстр</code>\n"
        "Ответ: <b>Вагон Для Старост</b>\n\n"
        "<i>Знаки в ответе:</i>\n"
        "• Слэш <code>/</code> — несколько вариантов (кот/ток)\n"
        "• Тильда <code>~</code> — есть похожее слово (~Яблоко)\n"
        "• Вопрос <code>[?]</code> — не распознано ([авбг?])</blockquote>\n"
        "<blockquote><b>🍎 Как работают эмодзи:</b>\n"
        "Кидаешь: 🍎🦊\n"
        "Ответ: <b>Лиса с яблоком</b></blockquote>\n"
        "<blockquote><b>➕ Добавить слова/эмодзи:</b> Используй <b>/new</b>!\n"
        "Для слов: <code>/new синхрофазотрон яблоко</code>\n"
        "Для ребусов (с переносом строки):\n"
        "<code>/new 🍎🦊\nЛиса с яблоком</code></blockquote>"
    )
    await message.answer(text)


@router.message(Command("profile"))
async def cmd_profile(message: Message, user: dict):
    text = (
        f"👤 <b>Профиль:</b> {user['full_name']}\n"
        f"🗓 <b>С нами с:</b> {user['created_at']}\n\n"
        f"🔮 <b>Расшифровано ребусов:</b> {user['total_requests']:,}\n"
        f"📜 <b>Одобрено предложек:</b> {user['approved_proposals']:,}\n\n"
        f"⚡️ <b>Лимит на сегодня:</b> {user['daily_requests']}/{user['max_daily_limit']}"
    )
    await message.answer(text)
