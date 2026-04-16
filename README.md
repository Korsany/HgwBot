# Техническое описание проекта

Telegram-бот для дешифровки анаграмм и эмодзи-ребусов с системой модерации и администрирования.

## Структура проекта

```
HgwBot/
├── main.py                 # Точка входа, инициализация бота
├── core/                   # Ядро приложения
│   ├── config.py          # Конфигурация, константы, регулярные выражения
│   ├── middleware.py      # Middleware для обработки пользователей
│   └── states.py          # FSM состояния для редакторов и зелий
├── database/              # Работа с базой данных
│   └── db.py             # Инициализация БД, функции доступа
├── handlers/              # Обработчики команд и сообщений
│   ├── commands.py       # /start, /profile
│   ├── proposals.py      # /new и модерация предложений
│   ├── admin.py          # /admin и редакторы слов/эмодзи
│   ├── potions.py        # /potions - дневник зелий
│   └── decipher.py       # Основной дешифратор сообщений
├── keyboards/             # Inline-клавиатуры
│   └── __init__.py       # Фабрики клавиатур для модерации, редакторов и зелий
├── utils/                 # Вспомогательные утилиты
│   ├── helpers.py        # Команды бота, загрузка логов, бэкап
│   └── dictionaries.py   # Загрузка и управление словарями
├── lib.txt               # Базовый словарь слов
├── ulib.txt              # Пользовательские слова
└── slib.txt              # Эмодзи-ребусы
```

## База данных (SQLite)

### Таблица `users`
Хранит информацию о пользователях бота.

| Поле | Тип | Описание |
|------|-----|----------|
| `tg_id` | INTEGER PRIMARY KEY | Telegram ID пользователя |
| `username` | TEXT | Username пользователя |
| `full_name` | TEXT | Полное имя |
| `created_at` | TEXT | Дата регистрации |
| `is_admin` | INTEGER | Уровень админа (0 - обычный, 1 - модератор, 2 - владелец) |
| `daily_requests` | INTEGER | Количество запросов за день |
| `max_daily_limit` | INTEGER | Максимальный лимит запросов в день (по умолчанию 100) |
| `total_requests` | INTEGER | Общее количество запросов |
| `last_request_date` | TEXT | Дата последнего запроса |
| `is_banned` | INTEGER | Статус бана (0 - не забанен, 1 - забанен) |
| `approved_proposals` | INTEGER | Количество одобренных предложений |

### Таблица `proposals`
Хранит предложения пользователей на модерацию.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | ID предложения |
| `type` | TEXT | Тип предложения ('word' или 'emoji') |
| `content` | TEXT | Содержимое (слово или эмодзи) |
| `description` | TEXT | Описание (для эмодзи-ребусов) |
| `user_id` | INTEGER | Telegram ID автора |

### Таблица `settings`
Хранит настройки бота.

| Поле | Тип | Описание |
|------|-----|----------|
| `key` | TEXT PRIMARY KEY | Ключ настройки |
| `value` | TEXT | Значение настройки |

**Используемые настройки:**
- `admin_group` - ID группы для модерации и уведомлений

### Таблица `potions`
Хранит рецепты зелий.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | ID зелья |
| `name` | TEXT | Название зелья |
| `ingredients` | TEXT | Ингредиенты и их количество |
| `quality` | TEXT | Качество зелья (❌🍀, ⚖️, ✨) |
| `added_by` | INTEGER | Telegram ID автора |
| `created_at` | TEXT | Дата и время добавления |

### Таблица `potion_access`
Управление доступом к системе зелий.

| Поле | Тип | Описание |
|------|-----|----------|
| `user_id` | INTEGER PRIMARY KEY | Telegram ID пользователя с доступом |

## Основные модули

### `main.py`
**Функции:**
- `create_bot()` → Bot - Создание экземпляра бота
- `create_dispatcher()` → Dispatcher - Настройка диспетчера с роутерами
- `on_shutdown(bot)` - Корректное завершение работы
- `main()` - Основная функция запуска

### `core/config.py`
**Константы:**
- `BOT_TOKEN` - Токен Telegram бота
- `DB_FILE` - Путь к файлу базы данных
- `MSK_TZ` - Московская временная зона
- `ITEMS_PER_PAGE_WORDS` - Количество слов на странице редактора (10)
- `ITEMS_PER_PAGE_EMOJI` - Количество эмодзи на странице редактора (5)
- `BACKUP_INTERVAL_SECONDS` - Интервал бэкапа БД (86400 сек = 24 часа)
- `BASE_WORDS_FILE` - Базовый словарь (lib.txt)
- `USER_WORDS_FILE` - Пользовательские слова (ulib.txt)
- `USER_EMOJI_FILE` - Эмодзи-ребусы (slib.txt)

**Регулярные выражения:**
- `RE_WORD` - Поиск слов с дефисами
- `RE_CLEAN` - Очистка от спецсимволов
- `RE_HAS_LETTERS` - Проверка наличия букв

**Пасхалки:**
- `EASTER_EGGS` - Словарь заклинаний из Гарри Поттера

### `core/middleware.py`
**Класс `CoreMiddleware`:**
- Регистрация новых пользователей
- Проверка бана
- Сброс дневного счётчика запросов
- Фильтрация групповых чатов
- Передача данных пользователя в handlers

### `database/db.py`
**Функции:**
- `init_db()` - Инициализация базы данных и создание таблиц
- `get_admin_group()` → int | None - Получение ID группы администраторов (с кешированием на 5 минут)

### `handlers/commands.py`
**Обработчики:**
- `cmd_start(message, state)` - Команда /start - приветствие и инструкция
- `cmd_profile(message, user)` - Команда /profile - статистика пользователя

### `handlers/proposals.py`
**Функции:**
- `cmd_new(message, bot, db_factory, user)` - Команда /new для предложения слов/эмодзи
- `moderation_cb(call, db_factory, bot)` - Обработка кнопок модерации (одобрение/отклонение)
- `_safe_edit_text(message, text, **kwargs)` - Безопасное редактирование сообщений

**Callback данные:**
- `prp_a_{id}` - Одобрить предложение
- `prp_r_{id}_{reason}` - Отклонить (typo/dup/spam)

### `handlers/admin.py`
**Функции:**
- `cmd_admin(message, command, user, db_factory)` - Панель администратора
- `clamp_page(page, total_items, per_page)` → int - Ограничение номера страницы
- `send_words_editor(target, page, query)` - Интерфейс редактора слов
- `send_emoji_editor(target, page, query)` - Интерфейс редактора эмодзи
- `editor_words_cb(call, state)` - Обработка кнопок редактора слов
- `editor_emoji_cb(call, state)` - Обработка кнопок редактора эмодзи
- `search_word_result(message, state)` - Результат поиска слов
- `search_emoji_result(message, state)` - Результат поиска эмодзи

**Команды админа:**
- `/admin` - Справка
- `/admin stat` - Статистика
- `/admin set_group` - Привязать группу модерации
- `/admin edit_words` - Редактор слов
- `/admin edit_emoji` - Редактор эмодзи
- `/admin set_admin [id] [0/1/2]` - Управление правами (только владелец)
- `/admin set_limit [id] [число]` - Изменить лимит (только владелец)
- `/admin ban [id]` - Забанить (только владелец)
- `/admin unban [id]` - Разбанить (только владелец)
- `/admin potion_add [id]` - Дать доступ к зельям (только владелец)
- `/admin potion_remove [id]` - Убрать доступ к зельям (только владелец)
- `/admin potion_list` - Список пользователей с доступом к зельям (только владелец)

**Callback данные:**
- `ew_pg_{page}` - Переключение страницы слов
- `ew_srch` - Поиск слова
- `ew_del_{word}` - Удалить слово
- `ee_pg_{page}` - Переключение страницы эмодзи
- `ee_srch` - Поиск эмодзи
- `ee_del_{emoji}` - Удалить эмодзи

### `handlers/potions.py`
**Функции:**
- `cmd_potions(message, user, db)` - Команда /potions - открыть дневник зелий
- `has_potion_access(db, user_id)` → bool - Проверка доступа к системе зелий
- `send_potions_list(target, page, db, query)` - Отправка списка зелий с пагинацией
- `potions_callback(call, state, db, user)` - Обработка всех callback'ов зелий
- `add_potion_name(message, state)` - Получение названия зелья
- `add_potion_ingredients(message, state)` - Получение ингредиентов
- `search_potion_result(message, state, db)` - Результат поиска зелий

**Callback данные:**
- `pot_pg_{page}` - Переключение страницы
- `pot_add` - Добавить новое зелье
- `pot_srch` - Поиск зелья
- `pot_view_{id}` - Просмотр детальной информации
- `pot_del_{id}` - Удалить зелье
- `pot_back` - Вернуться к списку
- `pot_cancel` - Отменить добавление
- `pot_q_{quality}` - Выбор качества зелья

**Ингредиенты:**
- луноросянка
- кристалл лунного камня
- пыльца визгоплюща
- серебристая слизь лукотруса
- нить акромантула
- шип гиппогрифа
- пепельный мох
- копытная стружка фестрала
- порошок рога двурога
- желчь болотной жабы

### `handlers/decipher.py`
**Функции:**
- `main_handler(message, user, db_factory, bot)` - Основной дешифратор всех сообщений

**Логика работы:**
1. Проверка на пасхалки
2. Проверка лимита запросов
3. Попытка распознать эмодзи-ребус
4. Разбор анаграмм:
   - Точное совпадение → возвращает все варианты через `/`
   - Похожее слово (cutoff 0.72) → возвращает с `~`
   - Не распознано → возвращает `[слово?]`
5. Обновление статистики пользователя
6. Отправка логов ошибок в группу модерации

### `utils/dictionaries.py`
**Глобальные хранилища:**
- `STORAGE` - dict[str, set[str]] - Словарь анаграмм (ключ = отсортированные буквы)
- `ALL_WORDS_LIST` - list[str] - Список всех слов для поиска похожих
- `EMOJI_STORAGE` - dict[str, str] - Словарь эмодзи-ребусов

**Функции:**
- `parse_and_add_word(seed, seen_words_set)` - Парсинг слова через pymorphy3, добавление всех форм
- `load_dictionaries()` - Загрузка всех словарей в память (lib.txt + ulib.txt + slib.txt)
- `sync_emoji_file()` - Синхронизация EMOJI_STORAGE с файлом slib.txt

### `utils/helpers.py`
**Функции:**
- `setup_bot_commands(bot)` - Установка команд бота в меню
- `upload_log(content)` → str - Загрузка лога ошибки на pastes.dev
- `backup_scheduler(bot, stop_event)` - Фоновая задача ежедневного бэкапа БД

### `keyboards/__init__.py`
**Функции:**
- `get_moderation_keyboard(prop_id)` → InlineKeyboardMarkup - Клавиатура модерации
- `get_words_editor_keyboard(words, page, total_items, per_page, query)` → InlineKeyboardMarkup
- `get_emoji_editor_keyboard(items, page, total_items, per_page, query)` → InlineKeyboardMarkup
- `get_potions_keyboard(potions, page, total_items, per_page, query)` → InlineKeyboardMarkup - Список зелий
- `get_potion_detail_keyboard(potion_id)` → InlineKeyboardMarkup - Детальный просмотр зелья
- `get_quality_keyboard()` → InlineKeyboardMarkup - Выбор качества зелья

## Алгоритм дешифровки анаграмм

1. Текст разбивается на токены (слова)
2. Каждый токен очищается от спецсимволов (кроме дефиса)
3. Буквы токена сортируются и формируют ключ
4. Поиск в `STORAGE` по ключу:
   - Найдено → возвращаются все варианты
   - Не найдено → используется `difflib.get_close_matches` с cutoff=0.72
   - Ничего похожего → помечается как нераспознанное

## Система прав доступа

- **0** - Обычный пользователь (лимит 100 запросов/день)
- **1** - Модератор (без лимита, доступ к модерации и редакторам)
- **2** - Владелец (полный доступ, управление пользователями)

## Запуск

```bash
python main.py
```

Бот автоматически:
- Инициализирует базу данных
- Загружает словари в память
- Настраивает команды
- Запускает фоновую задачу бэкапа
- Начинает polling
