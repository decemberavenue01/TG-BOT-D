import aiosqlite
from pathlib import Path
import os
from typing import Optional, List, Tuple, Union

DB_PATH = Path("bot_database.sqlite3")

if not DB_PATH.parent.exists():
    os.makedirs(DB_PATH.parent)

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.db = None  # Сюда запишем соединение

    async def init_db(self):
        self.db = await aiosqlite.connect(self.db_path)
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                is_subscribed BOOLEAN DEFAULT 1,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS join_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                chat_id INTEGER NOT NULL,
                chat_title TEXT,
                status TEXT DEFAULT 'pending',
                approved_by INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await self.db.execute("""
            INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_approve', 'true')
        """)
        await self.db.commit()

    async def close(self):
        if self.db:
            await self.db.close()

    # Настройки
    async def get_setting(self, key: str) -> Optional[str]:
        async with self.db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_setting(self, key: str, value: str):
        await self.db.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, value))
        await self.db.commit()

    # Пользователи
    async def add_user(self, user_id: int):
        await self.db.execute("""
            INSERT OR IGNORE INTO users (user_id) VALUES (?)
        """, (user_id,))
        await self.db.commit()

    # Заявки
    async def add_request(self, user_id: int, username: Optional[str], full_name: Optional[str], chat_id: int, chat_title: str) -> int:
        cursor = await self.db.execute("""
            INSERT INTO join_requests (user_id, username, full_name, chat_id, chat_title)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, full_name, chat_id, chat_title))
        await self.db.commit()
        return cursor.lastrowid

    async def get_request_by_id(self, request_id: int) -> Optional[Tuple]:
        async with self.db.execute("SELECT * FROM join_requests WHERE id = ?", (request_id,)) as cursor:
            return await cursor.fetchone()

    async def get_pending_requests(self) -> List[Tuple]:
        async with self.db.execute("SELECT * FROM join_requests WHERE status = 'pending'") as cursor:
            return await cursor.fetchall()

    async def approve_request(self, request_id: int, approved_by: int):
        await self.db.execute("""
            UPDATE join_requests SET status = 'approved', approved_by = ?
            WHERE id = ?
        """, (approved_by, request_id))
        await self.db.commit()

    async def reject_request(self, request_id: int, rejected_by: int):
        await self.db.execute("""
            UPDATE join_requests SET status = 'rejected', approved_by = ?
            WHERE id = ?
        """, (rejected_by, request_id))
        await self.db.commit()

    async def auto_approve_request(self, user_id: int, chat_id: int):
        await self.db.execute("""
            UPDATE join_requests SET status = 'approved', approved_by = -1
            WHERE user_id = ? AND chat_id = ? AND status = 'pending'
        """, (user_id, chat_id))
        await self.db.commit()

    async def get_all_users(self) -> List[Tuple]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id FROM users WHERE is_subscribed = 1") as cursor:
                return await cursor.fetchall()

# Глобальный объект базы
db = Database()
