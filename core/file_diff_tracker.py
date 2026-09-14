# -*- coding: utf-8 -*-
"""
工作空间文件差异追踪器 (FileDiffTracker)
- 实时追踪 AI 在工作空间中创建、编辑与修改的文件差异
- 基于 difflib 精确计算新增行数 (+)、删除行数 (-) 与逐行 Diff 标记
- 支持一键接收变更 (Accept) 与一键物理回滚还原 (Reject / Revert)
- 支持多会话与多任务隔离追踪
"""
import os
import difflib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any


class FileChangeRecord:
    def __init__(
        self,
        rel_path: str,
        abs_path: str,
        status: str = "modified",  # "created" | "modified" | "deleted"
        before_content: str = "",
        after_content: str = "",
        session_id: str = "",
        timestamp: str = "",
        added_lines: Optional[int] = None,
        removed_lines: Optional[int] = None,
        **kwargs
    ):
        self.rel_path = rel_path.replace("\\", "/")
        self.abs_path = str(Path(abs_path).resolve())
        self.status = status
        self.before_content = before_content or ""
        self.after_content = after_content or ""
        self.session_id = str(session_id or "")
        self.timestamp = timestamp or datetime.now().strftime("%H:%M:%S")
        self.is_accepted = False
        self.is_rejected = False

        # 计算新增行与删除行数（若外部显式传入则直接使用，否则通过 diff 计算）
        if added_lines is not None and removed_lines is not None:
            self.added_lines = int(added_lines)
            self.removed_lines = int(removed_lines)
        else:
            self.added_lines, self.removed_lines = self._calc_diff_counts()

    def _calc_diff_counts(self) -> Tuple[int, int]:
        before_lines = self.before_content.splitlines(keepends=True)
        after_lines = self.after_content.splitlines(keepends=True)
        added = 0
        removed = 0
        diff = difflib.ndiff(before_lines, after_lines)
        for line in diff:
            if line.startswith("+ "):
                added += 1
            elif line.startswith("- "):
                removed += 1
        return added, removed

    def get_diff_blocks(self) -> List[Dict[str, Any]]:
        """
        生成带有行号、变动类型、着色标识的差异列表
        每项格式：
        {
            "type": "add" | "del" | "same",
            "old_no": int or "",
            "new_no": int or "",
            "text": str
        }
        """
        before_lines = self.before_content.splitlines(keepends=False)
        after_lines = self.after_content.splitlines(keepends=False)
        
        diff = difflib.ndiff(before_lines, after_lines)
        blocks = []
        old_lineno = 1
        new_lineno = 1

        for item in diff:
            flag = item[:2]
            text = item[2:]
            if flag == "- ":
                blocks.append({
                    "type": "del",
                    "mark": "-",
                    "old_no": old_lineno,
                    "new_no": "",
                    "text": text
                })
                old_lineno += 1
            elif flag == "+ ":
                blocks.append({
                    "type": "add",
                    "mark": "+",
                    "old_no": "",
                    "new_no": new_lineno,
                    "text": text
                })
                new_lineno += 1
            elif flag == "  ":
                blocks.append({
                    "type": "same",
                    "mark": " ",
                    "old_no": old_lineno,
                    "new_no": new_lineno,
                    "text": text
                })
                old_lineno += 1
                new_lineno += 1
            # 忽略 "? " 字符内微变动提示行
        return blocks

    def to_dict(self) -> dict:
        return {
            "rel_path": self.rel_path,
            "abs_path": self.abs_path,
            "status": self.status,
            "added_lines": self.added_lines,
            "removed_lines": self.removed_lines,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "is_accepted": self.is_accepted,
            "is_rejected": self.is_rejected
        }


class FileDiffTracker:
    """全局文件差异追踪器单例"""
    _instance = None

    def __init__(self):
        # 结构: abs_path -> FileChangeRecord (最新一次变更记录)
        self._records: Dict[str, FileChangeRecord] = {}
        # 结构: session_id -> List[abs_path]
        self._session_index: Dict[str, List[str]] = {}
        # 观察者回调列表
        self._change_listeners = []

    @classmethod
    def get_instance(cls) -> "FileDiffTracker":
        if cls._instance is None:
            cls._instance = FileDiffTracker()
        return cls._instance

    def add_listener(self, callback):
        """注册文件变更监听回调 fn(record: FileChangeRecord)"""
        if callback not in self._change_listeners:
            self._change_listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._change_listeners:
            self._change_listeners.remove(callback)

    def record_change(
        self,
        rel_path: str,
        abs_path: str,
        before_content: str,
        after_content: str,
        session_id: str = ""
    ) -> FileChangeRecord:
        """记录一次文件变动"""
        abs_p = str(Path(abs_path).resolve())
        status = "created" if not before_content else "modified"
        if before_content and not after_content:
            status = "deleted"

        rec = FileChangeRecord(
            rel_path=rel_path,
            abs_path=abs_p,
            status=status,
            before_content=before_content,
            after_content=after_content,
            session_id=session_id
        )
        self._records[abs_p] = rec

        sid_str = str(session_id or "")
        if sid_str:
            self._session_index.setdefault(sid_str, [])
            if abs_p not in self._session_index[sid_str]:
                self._session_index[sid_str].append(abs_p)

        # 触发监听回调
        for cb in self._change_listeners:
            try:
                cb(rec)
            except Exception:
                pass

        return rec

    def get_record(self, abs_path: str) -> Optional[FileChangeRecord]:
        abs_p = str(Path(abs_path).resolve())
        return self._records.get(abs_p)

    def get_session_records(self, session_id: str) -> List[FileChangeRecord]:
        """获取指定会话下的所有变更记录"""
        sid_str = str(session_id or "")
        paths = self._session_index.get(sid_str, [])
        return [self._records[p] for p in paths if p in self._records]

    def get_recent_records(self, limit: int = 10) -> List[FileChangeRecord]:
        """获取最近的文件变更记录"""
        all_recs = list(self._records.values())
        return all_recs[-limit:]

    def revert_change(self, abs_path: str) -> Tuple[bool, str]:
        """一键撤回丢弃变更 (Reject / Revert)"""
        abs_p = str(Path(abs_path).resolve())
        rec = self._records.get(abs_p)
        if not rec:
            return False, "未找到该文件的变更历史"

        target_file = Path(abs_p)
        try:
            if rec.status == "created":
                # 如果原本是新建的文件，撤回即删除该文件
                if target_file.exists():
                    target_file.unlink()
            else:
                # 恢复修改前的内容
                target_file.write_text(rec.before_content, encoding="utf-8")
            
            rec.is_rejected = True
            rec.is_accepted = False
            return True, f"已成功还原文件：{rec.rel_path}"
        except Exception as e:
            return False, f"还原文件失败: {e}"

    def accept_change(self, abs_path: str) -> Tuple[bool, str]:
        """一键确认接收变更 (Accept / Re-apply)"""
        abs_p = str(Path(abs_path).resolve())
        rec = self._records.get(abs_p)
        if not rec:
            return False, "未找到该文件的变更历史"
        target_file = Path(abs_p)
        try:
            # 若之前曾被撤回（如新建文件被物理删除或修改被回退），再次点击接收时重新落地新内容
            if rec.status != "deleted":
                needs_write = False
                if not target_file.exists():
                    needs_write = True
                else:
                    try:
                        current_txt = target_file.read_text(encoding="utf-8")
                        if current_txt != rec.after_content:
                            needs_write = True
                    except Exception:
                        needs_write = True
                if needs_write:
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    target_file.write_text(rec.after_content, encoding="utf-8")

            rec.is_accepted = True
            rec.is_rejected = False
            return True, f"已确认接纳文件变更：{rec.rel_path}"
        except Exception as e:
            return False, f"接纳变更失败: {e}"

    def clear_session(self, session_id: str):
        sid_str = str(session_id or "")
        if sid_str in self._session_index:
            for p in self._session_index[sid_str]:
                self._records.pop(p, None)
            self._session_index.pop(sid_str, None)

    def clear(self):
        """清空所有记录"""
        self._records.clear()
        self._session_index.clear()
