# -*- coding: utf-8 -*-
"""
桌宠定时提醒与日程管理器 (Pet Scheduler & Persistent Recurring Task Manager)
支持单次提醒与周期性循环任务（每日定时、每周定时、固定间隔），
到点通过 PyQt5 信号触发桌宠动作、系统通知及自动化流水线执行，支持磁盘持久化存储。
"""
import sys
import time
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except Exception:
        try:
            cleaned = [str(a).encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8") for a in args]
            print(*cleaned, **kwargs)
        except Exception:
            pass

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TASKS_FILE = DATA_DIR / "scheduled_tasks.json"



class PetScheduler(QObject):
    """全局定时提醒与日程调度器 (Qt Signal 线程安全 + 磁盘持久化)"""
    
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
        self._ensure_storage()
        self._load_from_storage()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        PetScheduler._instance = self

    def _ensure_storage(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            if not TASKS_FILE.exists():
                TASKS_FILE.write_text(json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[Scheduler] Failed to ensure storage: {e}")

    def _save_to_storage(self):
        try:
            with self._lock:
                serialized = []
                for r in self._reminders:
                    item = dict(r)
                    if isinstance(item.get("trigger_dt"), datetime):
                        item["trigger_dt_str"] = item["trigger_dt"].isoformat()
                        del item["trigger_dt"]
                    serialized.append(item)
                TASKS_FILE.write_text(json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[Scheduler] Failed to save tasks to storage: {e}")

    def _load_from_storage(self):
        try:
            if not TASKS_FILE.exists():
                return
            content = TASKS_FILE.read_text(encoding="utf-8").strip()
            if not content:
                return
            items = json.loads(content)
            now = datetime.now()
            max_id = 0

            for it in items:
                rid = it.get("id", 1)
                if rid > max_id:
                    max_id = rid

                dt_str = it.get("trigger_dt_str")
                if dt_str:
                    try:
                        it["trigger_dt"] = datetime.fromisoformat(dt_str)
                    except Exception:
                        it["trigger_dt"] = now + timedelta(minutes=10)
                else:
                    it["trigger_dt"] = now + timedelta(minutes=10)

                # 如果是过去的未完成周期任务，自动向后推进到下一个周期
                repeat = it.get("repeat", "once")
                if it.get("status") == "pending" and it["trigger_dt"] <= now:
                    if repeat == "daily":
                        while it["trigger_dt"] <= now:
                            it["trigger_dt"] += timedelta(days=1)
                        it["trigger_timestamp"] = it["trigger_dt"].timestamp()
                        it["time_str"] = it["trigger_dt"].strftime("%H:%M:%S")
                    elif repeat == "weekly":
                        while it["trigger_dt"] <= now:
                            it["trigger_dt"] += timedelta(days=7)
                        it["trigger_timestamp"] = it["trigger_dt"].timestamp()
                        it["time_str"] = it["trigger_dt"].strftime("%H:%M:%S")
                    elif repeat == "interval" and it.get("interval_sec", 0) > 0:
                        sec = it["interval_sec"]
                        while it["trigger_dt"] <= now:
                            it["trigger_dt"] += timedelta(seconds=sec)
                        it["trigger_timestamp"] = it["trigger_dt"].timestamp()
                        it["time_str"] = it["trigger_dt"].strftime("%H:%M:%S")
                    else:
                        it["status"] = "expired"

                self._reminders.append(it)

            self._next_id = max_id + 1
            safe_print(f"[Scheduler] Loaded {len(self._reminders)} tasks from storage (next ID: {self._next_id})")
        except Exception as e:
            safe_print(f"[Scheduler] Failed to load tasks: {e}")

    def add_reminder(
        self, 
        content: str, 
        minutes_later: float = 0, 
        seconds_later: float = 0, 
        target_time_str: Optional[str] = None,
        title: str = "⏰ 专属提醒",
        motion: str = "nod",
        repeat: str = "once",
        interval_sec: float = 0,
        start_date: str = "",
        end_date: str = "",
        expert: str = "",
        skill: str = "",
        model: str = "",
        permission: str = "standard",
        push_wecom: bool = False,
        push_wechat: bool = False,
        meta: Optional[Dict] = None
    ) -> Dict:
        """
        添加一个定时提醒或周期性自动化任务
        :param content: 提醒或 Prompt 内容
        :param minutes_later: 相对时间（分钟）
        :param seconds_later: 相对时间（秒）
        :param target_time_str: 目标时间，格式如 '15:30' 或 '2026-08-25 15:30:00'
        :param title: 提醒标题
        :param motion: 触发时桌宠做的动作
        :param repeat: 循环类型 ('once', 'daily', 'weekly', 'interval')
        :param interval_sec: 循环间隔秒数
        """
        now = datetime.now()
        trigger_dt = None

        if target_time_str:
            target_str = target_time_str.strip().replace("/", "-")
            try:
                if len(target_str) <= 8 and ":" in target_str and "-" not in target_str:
                    parts = [int(p) for p in target_str.split(":")]
                    h, m = parts[0], parts[1]
                    s = parts[2] if len(parts) > 2 else 0
                    trigger_dt = now.replace(hour=h, minute=m, second=s, microsecond=0)
                    if trigger_dt <= now and repeat != "once":
                        trigger_dt += timedelta(days=1)
                elif " " in target_str:
                    fmt = "%Y-%m-%d %H:%M:%S" if target_str.count(":") >= 2 else "%Y-%m-%d %H:%M"
                    trigger_dt = datetime.strptime(target_str, fmt)
                else:
                    trigger_dt = datetime.fromisoformat(target_str)
            except Exception as e:
                print(f"[Scheduler] Failed to parse target time {target_time_str}: {e}")

        if trigger_dt is None:
            total_sec = float(minutes_later) * 60 + float(seconds_later)
            if total_sec <= 0:
                total_sec = interval_sec if interval_sec > 0 else 60
            trigger_dt = now + timedelta(seconds=total_sec)

        # 智能格式化前端展示的时间描述
        if repeat == "once" and trigger_dt.date() != now.date():
            display_time_str = trigger_dt.strftime("%Y/%m/%d %H:%M")
        elif repeat == "interval" and interval_sec > 0:
            h = int(interval_sec // 3600)
            display_time_str = f"每{h}小时" if h > 0 else f"{int(interval_sec//60)}分钟"
        else:
            display_time_str = trigger_dt.strftime("%H:%M:%S")

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
                "time_str": display_time_str,
                "motion": motion,
                "repeat": repeat,
                "interval_sec": interval_sec,
                "start_date": start_date.strip(),
                "end_date": end_date.strip(),
                "expert": expert.strip(),
                "skill": skill.strip(),
                "model": model.strip(),
                "permission": permission.strip() if permission else "standard",
                "push_wecom": bool(push_wecom),
                "push_wechat": bool(push_wechat),
                "meta": meta or {},
                "status": "pending"
            }
            self._reminders.append(item)
            safe_print(f"[Scheduler] Task created #{rid} (repeat={repeat}): {title} at {item['time_str']}")

        self._save_to_storage()
        return item

    def get_reminder_by_id(self, reminder_id: int) -> Optional[Dict]:
        """根据 ID 获取单个任务完整信息"""
        with self._lock:
            for r in self._reminders:
                if r["id"] == reminder_id:
                    return dict(r)
        return None

    def update_reminder(
        self,
        reminder_id: int,
        content: str,
        target_time_str: Optional[str] = None,
        title: str = "⏰ 专属提醒",
        repeat: str = "once",
        interval_sec: float = 0,
        start_date: str = "",
        end_date: str = "",
        expert: str = "",
        skill: str = "",
        model: str = "",
        permission: str = "standard",
        push_wecom: bool = False,
        push_wechat: bool = False
    ) -> bool:
        """编辑更新现有定时任务"""
        now = datetime.now()
        trigger_dt = None

        if target_time_str:
            target_str = target_time_str.strip().replace("/", "-")
            try:
                if len(target_str) <= 8 and ":" in target_str and "-" not in target_str:
                    parts = [int(p) for p in target_str.split(":")]
                    h, m = parts[0], parts[1]
                    s = parts[2] if len(parts) > 2 else 0
                    trigger_dt = now.replace(hour=h, minute=m, second=s, microsecond=0)
                    if trigger_dt <= now and repeat != "once":
                        trigger_dt += timedelta(days=1)
                elif " " in target_str:
                    fmt = "%Y-%m-%d %H:%M:%S" if target_str.count(":") >= 2 else "%Y-%m-%d %H:%M"
                    trigger_dt = datetime.strptime(target_str, fmt)
                else:
                    trigger_dt = datetime.fromisoformat(target_str)
            except Exception as e:
                print(f"[Scheduler] Failed to parse target time {target_time_str}: {e}")

        if trigger_dt is None:
            total_sec = interval_sec if interval_sec > 0 else 60
            trigger_dt = now + timedelta(seconds=total_sec)

        if repeat == "once" and trigger_dt.date() != now.date():
            display_time_str = trigger_dt.strftime("%Y/%m/%d %H:%M")
        elif repeat == "interval" and interval_sec > 0:
            h = int(interval_sec // 3600)
            display_time_str = f"每{h}小时" if h > 0 else f"{int(interval_sec//60)}分钟"
        else:
            display_time_str = trigger_dt.strftime("%H:%M:%S")

        updated = False
        with self._lock:
            for r in self._reminders:
                if r["id"] == reminder_id:
                    r["title"] = title
                    r["content"] = content
                    r["trigger_dt"] = trigger_dt
                    r["trigger_timestamp"] = trigger_dt.timestamp()
                    r["time_str"] = display_time_str
                    r["repeat"] = repeat
                    r["interval_sec"] = interval_sec
                    r["start_date"] = start_date.strip()
                    r["end_date"] = end_date.strip()
                    r["expert"] = expert.strip()
                    r["skill"] = skill.strip()
                    r["model"] = model.strip()
                    r["permission"] = permission.strip() if permission else "standard"
                    r["push_wecom"] = bool(push_wecom)
                    r["push_wechat"] = bool(push_wechat)
                    r["status"] = "pending"
                    updated = True
                    safe_print(f"[Scheduler] Task #{reminder_id} updated: {title} at {display_time_str}")
                    break

        if updated:
            self._save_to_storage()
        return updated

    def trigger_reminder_now(self, reminder_id: int) -> bool:
        """立即测试触发指定的任务（模拟时间到达，用于一键验证闭环）"""
        target_r = None
        with self._lock:
            for r in self._reminders:
                if r["id"] == reminder_id:
                    target_r = dict(r)
                    break
        if target_r:
            safe_print(f"[Scheduler] Manual test trigger #{reminder_id}: {target_r.get('title')}")
            self.reminder_triggered.emit(
                target_r["id"],
                target_r.get("title", "自动化任务"),
                target_r.get("content", ""),
                target_r.get("motion", "nod")
            )
            return True
        return False

    def get_all_reminders(self) -> List[Dict]:
        """获取所有待触发的提醒"""
        with self._lock:
            now_ts = time.time()
            return [
                {
                    "id": r["id"],
                    "title": r.get("title", "⏰ 提醒"),
                    "content": r["content"],
                    "time": r.get("time_str", ""),
                    "repeat": r.get("repeat", "once"),
                    "start_date": r.get("start_date", ""),
                    "end_date": r.get("end_date", ""),
                    "expert": r.get("expert", ""),
                    "skill": r.get("skill", ""),
                    "model": r.get("model", ""),
                    "permission": r.get("permission", "standard"),
                    "push_wecom": r.get("push_wecom", False),
                    "push_wechat": r.get("push_wechat", False),
                    "remain_sec": int(max(0, r["trigger_timestamp"] - now_ts)),
                    "status": r["status"]
                }
                for r in self._reminders if r["status"] == "pending"
            ]

    def cancel_reminder(self, reminder_id: int) -> bool:
        """取消指定的提醒"""
        cancelled = False
        with self._lock:
            for r in self._reminders:
                if r["id"] == reminder_id and r["status"] == "pending":
                    r["status"] = "cancelled"
                    cancelled = True
                    print(f"[Scheduler] Reminder cancelled #{reminder_id}")
                    break
        if cancelled:
            self._save_to_storage()
        return cancelled

    def _worker_loop(self):
        """后台轮询线程（精确到秒，支持周期自动滚动与生效日期区间过滤）"""
        while self._running:
            try:
                now_ts = time.time()
                today_str = datetime.now().strftime("%Y-%m-%d")
                to_fire = []
                need_save = False

                with self._lock:
                    for r in self._reminders:
                        if r["status"] == "pending" and now_ts >= r["trigger_timestamp"]:
                            # 1. 检查生效日期区间
                            s_date = r.get("start_date", "")
                            e_date = r.get("end_date", "")
                            if s_date and today_str < s_date:
                                # 未到生效日期，周期任务跳过本次，顺延至明天
                                r["trigger_dt"] += timedelta(days=1)
                                r["trigger_timestamp"] = r["trigger_dt"].timestamp()
                                need_save = True
                                continue
                            if e_date and today_str > e_date:
                                # 已过生效截止日期，该任务自动停止
                                r["status"] = "expired"
                                need_save = True
                                continue

                            repeat = r.get("repeat", "once")
                            to_fire.append(dict(r))
                            need_save = True

                            # 周期任务自动计算下一次触发时间
                            if repeat == "daily":
                                r["trigger_dt"] += timedelta(days=1)
                                r["trigger_timestamp"] = r["trigger_dt"].timestamp()
                                r["time_str"] = r["trigger_dt"].strftime("%H:%M:%S")
                                safe_print(f"[Scheduler] Daily task #{r['id']} rolled over to {r['time_str']}")
                            elif repeat == "weekly":
                                r["trigger_dt"] += timedelta(days=7)
                                r["trigger_timestamp"] = r["trigger_dt"].timestamp()
                                r["time_str"] = r["trigger_dt"].strftime("%H:%M:%S")
                                safe_print(f"[Scheduler] Weekly task #{r['id']} rolled over to {r['time_str']}")
                            elif repeat == "interval" and r.get("interval_sec", 0) > 0:
                                r["trigger_dt"] += timedelta(seconds=r["interval_sec"])
                                r["trigger_timestamp"] = r["trigger_dt"].timestamp()
                                r["time_str"] = r["trigger_dt"].strftime("%H:%M:%S")
                                safe_print(f"[Scheduler] Interval task #{r['id']} rolled over to {r['time_str']}")
                            else:
                                r["status"] = "fired"

                if need_save:
                    self._save_to_storage()

                for r in to_fire:
                    safe_print(f"[Scheduler] Firing task #{r['id']}: {r['title']}")
                    self.reminder_triggered.emit(r["id"], r["title"], r["content"], r.get("motion", "nod"))

            except Exception as e:
                safe_print(f"[Scheduler] Worker error: {e}")
            time.sleep(0.8)
