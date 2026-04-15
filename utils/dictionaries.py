import logging

import aiofiles
import pymorphy3

from core.config import BASE_WORDS_FILE, USER_WORDS_FILE, USER_EMOJI_FILE, RE_WORD

STORAGE = {}
ALL_WORDS_LIST = []
EMOJI_STORAGE = {}
PHRASE_STORAGE = set()  # Хранилище целых строк из lib.txt
PHRASE_ANAGRAM_MAP = {}  # Ключ: отсортированные буквы фразы -> значение: оригинальная фраза

morph = pymorphy3.MorphAnalyzer()


def parse_and_add_word(seed: str, seen_words_set: set = None):
    global STORAGE, ALL_WORDS_LIST
    paradigms = morph.parse(seed)

    is_single_add = seen_words_set is None
    if is_single_add:
        seen_words_set = set(ALL_WORDS_LIST)

    added_new = False
    for p in paradigms:
        for form in p.lexeme:
            wf = form.word
            if wf in seen_words_set:
                continue
            seen_words_set.add(wf)
            added_new = True

            letters = [c for c in wf if c != "-"]
            key = "".join(sorted(letters))
            STORAGE.setdefault(key, set()).add(wf)

            if is_single_add:
                ALL_WORDS_LIST.append(wf)

    if is_single_add and added_new:
        ALL_WORDS_LIST.sort()


async def load_dictionaries():
    global STORAGE, ALL_WORDS_LIST, EMOJI_STORAGE, PHRASE_STORAGE, PHRASE_ANAGRAM_MAP
    STORAGE.clear()
    ALL_WORDS_LIST.clear()
    EMOJI_STORAGE.clear()
    PHRASE_STORAGE.clear()
    PHRASE_ANAGRAM_MAP.clear()

    USER_WORDS_FILE.touch(exist_ok=True)
    USER_EMOJI_FILE.touch(exist_ok=True)

    seen_words = set()

    # Загружаем lib.txt с сохранением целых строк
    if BASE_WORDS_FILE.exists():
        async with aiofiles.open(BASE_WORDS_FILE, mode="r", encoding="utf-8") as f:
            async for line in f:
                line = line.strip()
                if line:
                    # Сохраняем целую строку в нижнем регистре для проверки
                    PHRASE_STORAGE.add(line.lower())
                    # Создаем ключ из отсортированных букв для проверки анаграмм
                    phrase_key = "".join(
                        sorted([c for c in line.lower() if c.isalpha()])
                    )
                    PHRASE_ANAGRAM_MAP[phrase_key] = line.lower()
                    # Парсим слова из строки для пословной проверки
                    seeds = RE_WORD.findall(line.lower())
                    for seed in seeds:
                        parse_and_add_word(seed, seen_words)

    # Загружаем ulib.txt только пословно
    if USER_WORDS_FILE.exists():
        async with aiofiles.open(USER_WORDS_FILE, mode="r", encoding="utf-8") as f:
            content = await f.read()
            seeds = RE_WORD.findall(content.lower())
            for seed in seeds:
                parse_and_add_word(seed, seen_words)

    ALL_WORDS_LIST = sorted(list(seen_words))

    async with aiofiles.open(USER_EMOJI_FILE, mode="r", encoding="utf-8") as f:
        async for line in f:
            if ":" in line:
                emojis, desc = line.split(":", 1)
                EMOJI_STORAGE[emojis.strip().replace(" ", "")] = desc.strip().title()

    logging.info(
        f"Словари загружены: {len(ALL_WORDS_LIST):,} слов, {len(PHRASE_STORAGE):,} фраз, {len(EMOJI_STORAGE)} ребусов."
    )


async def sync_emoji_file():
    async with aiofiles.open(USER_EMOJI_FILE, mode="w", encoding="utf-8") as f:
        for emojis, desc in EMOJI_STORAGE.items():
            await f.write(f"{emojis} : {desc.strip().title()}\n")
