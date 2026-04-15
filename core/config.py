import os
import re
from pathlib import Path
from datetime import timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_FILE = "bot_database.sqlite"
MSK_TZ = timezone(timedelta(hours=3))

ITEMS_PER_PAGE_WORDS = 10
ITEMS_PER_PAGE_EMOJI = 5

BACKUP_INTERVAL_SECONDS = 86400

BASE_WORDS_FILE = Path("lib.txt")
USER_WORDS_FILE = Path("ulib.txt")
USER_EMOJI_FILE = Path("slib.txt")

RE_WORD = re.compile(r"[а-яёa-z]+(?:-[а-яёa-z]+)*", re.IGNORECASE)
RE_CLEAN = re.compile(r"[^а-яёa-z-]", re.IGNORECASE)
RE_HAS_LETTERS = re.compile(r"[а-яёa-z]", re.IGNORECASE)

EASTER_EGGS = {
    "авада кедавра": "🛡 <b>Протего!</b> Меня так просто не взять, магл.",
    "люмос": "💡 <i>*Стало чуточку светлее*</i>\nПродолжаем читать руны.",
    "нокс": "🌑 <i>*Свет погас*</i>\nВо тьме анаграммы читаются хуже.",
    "круцио": "Боль мне неведома, я всего лишь программный код Тома Марволо. 🐍",
    "империо": "Моя воля принадлежит только создателю. 🪄",
    "экспеллиармус": "Упс, моя клавиатура улетела... Шучу. Пиши ребус! ⌨️",
}
