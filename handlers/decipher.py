import difflib
import logging
import traceback

from aiogram import Router
from aiogram.types import Message

from core.config import RE_HAS_LETTERS, RE_CLEAN, EASTER_EGGS
from utils.dictionaries import (
    STORAGE,
    ALL_WORDS_LIST,
    EMOJI_STORAGE,
    PHRASE_STORAGE,
    PHRASE_ANAGRAM_MAP,
)
from utils.helpers import upload_log
from database.db import get_admin_group

logger = logging.getLogger(__name__)

router = Router()


@router.message()
async def main_handler(message: Message, user: dict, db, bot):
    text = message.text
    if not text or text.startswith("/"):
        return

    lower_text = text.lower().strip()

    if lower_text in EASTER_EGGS:
        return await message.reply(EASTER_EGGS[lower_text])

    if user["is_admin"] < 1 and user["daily_requests"] >= user["max_daily_limit"]:
        return await message.reply(
            f"❌ Ваш лимит запросов на сегодня исчерпан ({user['max_daily_limit']})."
        )

    try:
        clean_emojis = text.replace(" ", "").strip()

        if clean_emojis in EMOJI_STORAGE:
            result_msg = f"<code>{EMOJI_STORAGE[clean_emojis]}</code>"
        else:
            has_letters = bool(RE_HAS_LETTERS.search(text))

            if not has_letters:
                result_msg = (
                    "Эмодзи не распознаны. Используй /new чтобы пополнить Гримуар!"
                )
            else:
                # Этап 1: Проверка точного совпадения с целой строкой из lib.txt
                if lower_text in PHRASE_STORAGE:
                    result_msg = lower_text.title()
                else:
                    # Этап 1.5: Проверка анаграммы фразы
                    phrase_key = "".join(sorted([c for c in lower_text if c.isalpha()]))
                    if phrase_key in PHRASE_ANAGRAM_MAP:
                        result_msg = PHRASE_ANAGRAM_MAP[phrase_key].title()
                    else:
                        # Этап 2: Пословная проверка (старый способ)
                        final_words = []
                        for token in text.lower().split():
                            cleaned_token = RE_CLEAN.sub("", token)
                            if not cleaned_token:
                                continue

                            key = "".join(
                                sorted([c for c in cleaned_token if c != "-"])
                            )
                            matches = STORAGE.get(key)

                            if matches:
                                final_words.append(
                                    "/".join([w.title() for w in sorted(matches)])
                                )
                            else:
                                close = difflib.get_close_matches(
                                    cleaned_token.replace("-", ""),
                                    ALL_WORDS_LIST,
                                    n=1,
                                    cutoff=0.72,
                                )
                                if close:
                                    final_words.append(f"~{close[0].title()}")
                                else:
                                    final_words.append(f"[{token}?]")

                        result_msg = (
                            " ".join(final_words)
                            if final_words
                            else "Ничего не распознавалось."
                        )

        await db.execute(
            "UPDATE users SET daily_requests = daily_requests + 1, total_requests = total_requests + 1 WHERE tg_id = ?",
            (user["tg_id"],),
        )
        await db.commit()

        logger.debug(
            f"Пользователь {user['tg_id']}: запрос '{text[:50]}...' → ответ получен"
        )
        await message.answer(result_msg)

    except Exception:
        error_log = traceback.format_exc()
        logger.exception(f"Ошибка при обработке запроса от {user['tg_id']}")

        paste_link = await upload_log(error_log)

        admin_group = await get_admin_group()
        if admin_group:
            await bot.send_message(admin_group, f"Ошибка обработки. Лог: {paste_link}")

        err_text = "Внутренняя ошибка... Техники уже в курсе!"
        await message.reply(err_text)
