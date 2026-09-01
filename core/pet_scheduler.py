# -*- coding: utf-8 -*-
"""
桌宠定时提醒与日程管理器 (Pet Scheduler & Reminder Manager)
支持相对时间（如 10分钟后、30秒后）和绝对时间（如 15:30）的定时任务，
到点通过 PyQt5 信号触发桌宠气泡弹窗、动作与系统通知。
"""
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal


class PetScheduler(QObject):
    """全局定时提醒与日程调度器 (Qt Signal 线程安全)"""
    
    # 提醒触发信号: (reminder_id, title, content, motion)
    reminder_triggered = pyqtSignal(int, str, str, str)

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = PetScheduler()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._reminders: List[Dict] = []
        self._next_id = 1
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        PetScheduler._instance = self

    def add_reminder(
        self, 
        content: str, 
        minutes_later: float = 0, 
        seconds_later: float = 0, 
        target_time_str: Optional[str] = None,
        title: str = "⏰ 专属提醒",
        motion: str = "nod"
    ) -> Dict:
        """
        添加一个定时提醒
        :param content: 提醒内容
        :param minutes_later: 多少分钟后
        :param seconds_later: 多少秒后
        :param target_time_str: 目标时间，格式如 '15:30' 或 '2026-08-25 15:30:00'
        :param title: 提醒标题
        :param motion: 触发时桌宠做的动作
        """
        now = datetime.now()
        trigger_dt = None

        if target_time_str:
            target_str = target_time_str.strip()
            # 尝试解析 HH:MM 或 HH:MM:SS
            try:
                if len(target_str) <= 8 and ":" in target_str:
                    parts = [int(p) for p in target_str.split(":")]
                    h, m = parts[0], parts[1]
                    s = parts[2] if len(parts) > 2 else 0
                    trigger_dt = now.replace(hour=h, minute=m, second=s, microsecond=0)
                    if trigger_dt <= now:
                        # 如果时间已过，视为明天该时间
                        trigger_dt += timedelta(days=1)
                else:
                    trigger_dt = datetime.fromisoformat(target_str)
            except Exception as e:
                print(f"[Scheduler] Failed to parse target time {target_time_str}: {e}")

        if trigger_dt is None:
            total_sec = float(minutes_later) * 60 + float(seconds_later)
            if total_sec <= 0:
                total_sec = 60 # 默认至少 1 分钟
            trigger_dt = now + timedelta(seconds=total_sec)

        with self._lock:
            rid = self._next_id
            self._next_id += 1
            item = {
                "id": rid,
                "title": title,
                "content": content,
                "trigger_dt": trigger_dt,
                "trigger_timestamp": trigger_dt.timestamp(),
                "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "time_str": trigger_dt.strftime("%H:%M:%S"),
                "motion": motion,
                "status": "pending"
            }
            self._reminders.append(item)
            print(f"[Scheduler] OK reminder created #{rid}: {content} at {item['time_str']}")
            return item

    def get_all_reminders(self) -> List[Dict]:
        """获取所有待触发的提醒"""
        with self._lock:
            now_ts = time.time()
            return [
                {
                    "id": r["id"],
                    "content": r["content"],
                    "time": r["time_str"],
                    "remain_sec": int(max(0, r["trigger_timestamp"] - now_ts)),
                    "status": r["status"]
                }
                for r in self._reminders if r["status"] == "pending"
            ]

    def cancel_reminder(self, reminder_id: int) -> bool:
        """取消指定的提醒"""
        with self._lock:
            for r in self._reminders:
                if r["id"] == reminder_id and r["status"] == "pending":
                    r["status"] = "cancelled"
                    print(f"[Scheduler] OK reminder cancelled #{reminder_id}")
                    return True
        return False

    def _worker_loop(self):
        """后台轮询线程（精确到秒）"""
        while self._running:
            try:
                now_ts = time.time()
                to_fire = []
                with self._lock:
                    for r in self._reminders:
                        if r["status"] == "pending" and now_ts >= r["trigger_timestamp"]:
                            r["status"] = "fired"
                            to_fire.append(r)

                for r in to_fire:
                    print(f"[Scheduler] OK reminder fired: {r['content']}")
                    self.reminder_triggered.emit(r["id"], r["title"], r["content"], r["motion"])

            except Exception as e:
                print(f"[Scheduler] Worker error: {e}")
            time.sleep(0.8)
