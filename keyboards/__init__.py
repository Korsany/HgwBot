"""
Фабрики InlineKeyboardMarkup для бота
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_moderation_keyboard(prop_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для модерации предложки"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Одобрить", callback_data=f"prp_a_{prop_id}")],
            [
                InlineKeyboardButton(
                    text="Опечатка", callback_data=f"prp_r_{prop_id}_typo"
                ),
                InlineKeyboardButton(
                    text="Уже есть", callback_data=f"prp_r_{prop_id}_dup"
                ),
                InlineKeyboardButton(
                    text="Спам", callback_data=f"prp_r_{prop_id}_spam"
                ),
            ],
        ]
    )


def get_words_editor_keyboard(
    words: list, page: int, total_items: int, per_page: int, query: str = None
) -> InlineKeyboardMarkup:
    """Клавиатура для редактора слов"""
    total_pages = max(1, (total_items - 1) // per_page + 1)
    kb = []

    start = page * per_page
    end = start + per_page
    for w in words[start:end]:
        kb.append([InlineKeyboardButton(text=f"{w}", callback_data=f"ew_del_{w}")])

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="Назад", callback_data=f"ew_pg_{page - 1}")
        )
    nav.append(
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="none")
    )
    if (page + 1) * per_page < total_items:
        nav.append(
            InlineKeyboardButton(text="Далее", callback_data=f"ew_pg_{page + 1}")
        )

    kb.append(nav)
    kb.append(
        [
            InlineKeyboardButton(text="Поиск", callback_data="ew_srch"),
            InlineKeyboardButton(text="Сброс", callback_data="ew_pg_0_reset"),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_emoji_editor_keyboard(
    items: list, page: int, total_items: int, per_page: int, query: str = None
) -> InlineKeyboardMarkup:
    """Клавиатура для редактора эмодзи"""
    total_pages = max(1, (total_items - 1) // per_page + 1)
    kb = []

    start = page * per_page
    end = start + per_page
    for ems, desc in items[start:end]:
        kb.append(
            [
                InlineKeyboardButton(
                    text=f"{ems} — {desc}", callback_data=f"ee_del_{ems}"
                )
            ]
        )

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="Назад", callback_data=f"ee_pg_{page - 1}")
        )
    nav.append(
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="none")
    )
    if (page + 1) * per_page < total_items:
        nav.append(
            InlineKeyboardButton(text="Далее", callback_data=f"ee_pg_{page + 1}")
        )

    kb.append(nav)
    kb.append(
        [
            InlineKeyboardButton(text="Поиск", callback_data="ee_srch"),
            InlineKeyboardButton(text="Сброс", callback_data="ee_pg_0_reset"),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_potions_keyboard(
    potions: list, page: int, total_items: int, per_page: int, query: str = None
) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра зелий"""
    total_pages = max(1, (total_items - 1) // per_page + 1)
    kb = []

    start = page * per_page
    end = start + per_page
    for potion_id, name, ingredients, quality in potions[start:end]:
        quality_emoji = {"❌🍀": "❌🍀", "⚖️": "⚖️", "✨": "✨"}.get(quality, quality)
        kb.append(
            [
                InlineKeyboardButton(
                    text=f"{quality_emoji} {name}",
                    callback_data=f"pot_view_{potion_id}",
                )
            ]
        )

    if total_items > 0:
        nav = []
        if page > 0:
            nav.append(
                InlineKeyboardButton(text="◀️", callback_data=f"pot_pg_{page - 1}")
            )
        nav.append(
            InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="none")
        )
        if (page + 1) * per_page < total_items:
            nav.append(
                InlineKeyboardButton(text="▶️", callback_data=f"pot_pg_{page + 1}")
            )
        kb.append(nav)

    kb.append(
        [
            InlineKeyboardButton(text="➕ Добавить", callback_data="pot_add"),
            InlineKeyboardButton(text="🔍 Поиск", callback_data="pot_srch"),
        ]
    )

    if query:
        kb.append(
            [InlineKeyboardButton(text="🔄 Сброс", callback_data="pot_pg_0_reset")]
        )

    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_potion_detail_keyboard(potion_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для детального просмотра зелья"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Удалить", callback_data=f"pot_del_{potion_id}"
                )
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="pot_back")],
        ]
    )


def get_quality_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора качества зелья"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌🍀 Неудачное", callback_data="pot_q_❌🍀")],
            [InlineKeyboardButton(text="⚖️ Неплохое", callback_data="pot_q_⚖️")],
            [InlineKeyboardButton(text="✨ Идеальное", callback_data="pot_q_✨")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="pot_cancel")],
        ]
    )
