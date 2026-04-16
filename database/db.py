import aiosqlite
from core.config import DB_FILE

_ADMIN_GROUP_CACHE = None
_ADMIN_GROUP_TS = 0


async def init_db():
    async with aiosqlite.connect(DB_FILE, timeout=30.0) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=30000")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                created_at TEXT,
                is_admin INTEGER DEFAULT 0,
                daily_requests INTEGER DEFAULT 0,
                max_daily_limit INTEGER DEFAULT 100,
                total_requests INTEGER DEFAULT 0,
                last_request_date TEXT,
                is_banned INTEGER DEFAULT 0,
                approved_proposals INTEGER DEFAULT 0
            )
        """)

        async with db.execute("PRAGMA table_info(users)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]
            if columns and "approved_proposals" not in columns:
                await db.execute(
                    "ALTER TABLE users ADD COLUMN approved_proposals INTEGER DEFAULT 0"
                )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                content TEXT,
                description TEXT,
                user_id INTEGER
            )
        """)
        await db.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS potions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                quality TEXT NOT NULL,
                added_by INTEGER,
                created_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS potion_access (
                user_id INTEGER PRIMARY KEY
            )
        """)

        await db.commit()


async def get_admin_group() -> int | None:
    global _ADMIN_GROUP_CACHE, _ADMIN_GROUP_TS
    from datetime import datetime

    now = datetime.now().timestamp()

    if _ADMIN_GROUP_CACHE is not None and now - _ADMIN_GROUP_TS < 300:
        return _ADMIN_GROUP_CACHE

    async with aiosqlite.connect(DB_FILE, timeout=30.0) as db:
        await db.execute("PRAGMA busy_timeout=30000")
        async with db.execute(
            "SELECT value FROM settings WHERE key='admin_group'"
        ) as cursor:
            row = await cursor.fetchone()
            result = int(row[0]) if row else None

    _ADMIN_GROUP_CACHE, _ADMIN_GROUP_TS = result, now
    return result
