from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    search_word_mode = State()
    search_emoji_mode = State()
