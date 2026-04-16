from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    search_word_mode = State()
    search_emoji_mode = State()


class PotionStates(StatesGroup):
    add_potion_name = State()
    add_potion_ingredients = State()
    add_potion_quality = State()
    search_potion_mode = State()
