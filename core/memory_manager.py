# -*- coding: utf-8 -*-
"""
记忆管理器 - 支持多会话分类、会话切换、历史记录持久化存储与清理
"""
import sqlite3
import contextlib
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class MemoryManager:
    """本地会话与记忆系统（SQLite - 支持 WAL 高并发模式与安全事务）"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    @contextlib.contextmanager
    def _db_session(self):
        """获取并管理生命周期的数据库连接，确保用完即关闭"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self):
        """初始化多会话数据库表"""
        with self._db_session() as conn:
            # 历史会话分类表 (支持工作空间归属)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    workspace_name TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            try:
                conn.execute("ALTER TABLE sessions ADD COLUMN workspace_name TEXT DEFAULT '';")
            except Exception:
                pass
            # 会话消息表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)
            # 遗留兼容表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_msg TEXT NOT NULL,
                    ai_reply TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()

    def create_session(self, title: str = "新任务会话", workspace_name: str = "") -> int:
        """创建一个新会话并绑定工作空间"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._db_session() as conn:
            cursor = conn.execute(
                "INSERT INTO sessions (title, workspace_name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (title, workspace_name, now, now)
            )
            conn.commit()
            return cursor.lastrowid

    def get_all_sessions(self) -> List[Dict]:
        """获取所有历史会话列表"""
        with self._db_session() as conn:
            rows = conn.execute(
                "SELECT id, title, workspace_name, created_at, updated_at FROM sessions ORDER BY id DESC"
            ).fetchall()
        return [
            {"id": r[0], "title": r[1], "workspace_name": r[2] or "", "created_at": r[3], "updated_at": r[4]}
            for r in rows
        ]

    def update_session_workspace(self, session_id: int, workspace_name: str):
        """更新会话归属的工作空间"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._db_session() as conn:
            conn.execute(
                "UPDATE sessions SET workspace_name = ?, updated_at = ? WHERE id = ?",
                (workspace_name, now, session_id)
            )
            conn.commit()

    def update_session_title(self, session_id: int, title: str):
        """更新会话标题"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._db_session() as conn:
            conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, session_id)
            )
            conn.commit()

    def add_message(self, session_id: int, role: str, content: str):
        """向指定会话添加一条消息"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._db_session() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, now)
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id)
            )
            conn.commit()

    def get_session_messages(self, session_id: int) -> List[Dict]:
        """获取某个会话的所有消息"""
        with self._db_session() as conn:
            rows = conn.execute(
                "SELECT id, role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            ).fetchall()
        return [
            {"id": r[0], "role": r[1], "content": r[2], "timestamp": r[3]}
            for r in rows
        ]

    def delete_session(self, session_id: int):
        """删除指定会话及其所有消息"""
        with self._db_session() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()

    def clear_session_messages(self, session_id: int):
        """清空某个会话的消息"""
        with self._db_session() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.commit()

    def clear_all(self):
        """清空所有历史会话与数据库记录"""
        with self._db_session() as conn:
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM sessions")
            conn.execute("DELETE FROM conversations")
            conn.commit()
