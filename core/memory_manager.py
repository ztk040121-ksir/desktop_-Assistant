"""
记忆管理器 - 使用 SQLite 存储对话历史和用户偏好
"""
import sqlite3
import asyncio
from datetime import datetime
from pathlib import Path


class MemoryManager:
    """本地记忆系统（SQLite）"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_msg TEXT NOT NULL,
                    ai_reply TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_prefs (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    async def save_conversation(self, user_msg: str, ai_reply: str):
        """保存一条对话记录"""
        def _save():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO conversations (user_msg, ai_reply, timestamp) VALUES (?, ?, ?)",
                    (user_msg, ai_reply, datetime.now().isoformat())
                )
                conn.commit()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _save)

    def get_recent_conversations(self, limit: int = 50) -> list[dict]:
        """获取最近的对话记录"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, user_msg, ai_reply, timestamp FROM conversations "
                "ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [
            {"id": r[0], "user": r[1], "ai": r[2], "time": r[3]}
            for r in reversed(rows)
        ]

    def search_conversations(self, keyword: str) -> list[dict]:
        """按关键词搜索记忆"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, user_msg, ai_reply, timestamp FROM conversations "
                "WHERE user_msg LIKE ? OR ai_reply LIKE ? ORDER BY id DESC LIMIT 50",
                (f"%{keyword}%", f"%{keyword}%")
            ).fetchall()
        return [{"id": r[0], "user": r[1], "ai": r[2], "time": r[3]} for r in reversed(rows)]

    def delete_conversation(self, cid: int):
        """删除指定的一条对话"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM conversations WHERE id = ?", (cid,))
            conn.commit()

    def clear_conversations(self):
        """清空所有对话历史"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM conversations")
            conn.commit()

    def get_conversation_count(self) -> int:
        """获取对话总数"""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
