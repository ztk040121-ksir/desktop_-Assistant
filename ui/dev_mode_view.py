# -*- coding: utf-8 -*-
"""
独立代码开发模式主视图 (Dev IDE Mode View)
- 100% 独立页面架构，与 Work 模式完全物理隔离
- Antigravity / Cursor 风格的现代 IDE 布局：
  1. 顶部菜单栏：【文件】、【编辑】、【查看】、【终端】
  2. 左侧资源管理器 (Explorer)：树形目录浏览、打开文件夹、新建/删除文件
  3. 中间多标签代码编辑器：Tab 多文件切换、行号高亮、Ctrl+S 保存、Markdown 预览
  4. 中间下方抽屉控制台：沙箱终端（带一键运行当前脚本）与模型执行日志
  5. 最右侧 AI 智能体工作流：模型选择、思考轨迹卡片、代码变更审查与快捷对话
"""
import os
import sys
import re
import json
import time
import shutil
import threading
import asyncio
import subprocess
import html
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer, QDir, QPoint, QByteArray, QEvent
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QPushButton,
    QTabWidget, QPlainTextEdit, QTextEdit, QTextBrowser, QLineEdit, QComboBox,
    QFrame, QScrollArea, QFileSystemModel, QTreeView, QMenu, QAction,
    QFileDialog, QMessageBox, QShortcut, QSizePolicy, QDialog, QApplication,
    QStackedWidget, QToolButton, QLayout
)
from PyQt5.QtGui import QFont, QColor, QIcon, QKeySequence, QPixmap, QPainter, QTextCursor, QFontMetrics, QImage
from PyQt5.QtSvg import QSvgRenderer

from ui.code_editor import CodeEditor
from ui.dev_extension_manager import DEFAULT_DEV_PERSONAS, DevExtensionManagerDialog
from core.mcp_tool_bridge import MCPToolBridge


def create_history_icon(color: str = "#858585", hover_color: str = "#ffffff") -> QIcon:
    """生成"会话历史"时钟图标（纯 QPainter 绘制，不依赖 SVG 文件）。
    修复历史遗留 bug：dev_mode_view.py 里一直调用 create_history_icon / create_trash_icon，
    但函数定义从未存在，导致 `NameError`。"""
    size = 64
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))  # 透明背景
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    try:
        c = QColor(color)
        # 圆环（时钟外圈）
        pen = p.pen()
        pen.setColor(c)
        pen.setWidth(4)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(8, 8, size - 16, size - 16)
        # 时针与分针
        p.drawLine(32, 32, 32, 18)   # 12 点方向
        p.drawLine(32, 32, 44, 38)   # 3 点方向
        # 中心点
        p.setBrush(c)
        p.drawEllipse(28, 28, 8, 8)
    except Exception:
        pass
    p.end()
    return QIcon(pm)


def create_trash_icon(color: str = "#7d8590") -> QIcon:
    """生成"垃圾桶"图标（纯 QPainter 绘制，不依赖 SVG 文件）。"""
    size = 64
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))  # 透明背景
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    try:
        c = QColor(color)
        pen = p.pen()
        pen.setColor(c)
        pen.setWidth(4)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        # 垃圾桶顶盖
        p.drawLine(14, 16, 50, 16)
        # 桶身
        p.drawLine(20, 22, 20, 50)
        p.drawLine(44, 22, 44, 50)
        p.drawLine(20, 50, 44, 50)
        # 把手
        p.drawLine(22, 22, 26, 16)
        p.drawLine(42, 22, 38, 16)
        # 桶身竖条纹
        p.drawLine(28, 24, 28, 46)
        p.drawLine(36, 24, 36, 46)
    except Exception:
        pass
    p.end()
    return QIcon(pm)


# ── 文件类型图标缓存（QSvgRenderer → QPixmap → QIcon）──
_DEV_FILE_ICON_CACHE: dict = {}


def get_dev_file_icon(name_or_path: str, is_dark: bool = True) -> "QIcon":
    """根据文件名/扩展名返回对应的彩色小图标（16×16，带缓存）。"""
    from pathlib import Path as _P
    ext  = _P(name_or_path).suffix.lower()
    name = _P(name_or_path).name.lower()

    if name in ('implementation_plan.md',) or name.startswith('plan_'):
        key = 'plan'
    elif ext in ('.py', '.pyw'):
        key = 'python'
    elif ext in ('.md', '.markdown'):
        key = 'markdown'
    elif ext in ('.json', '.json5'):
        key = 'json'
    elif ext in ('.js', '.jsx', '.ts', '.tsx'):
        key = 'js'
    elif ext in ('.html', '.htm', '.xml'):
        key = 'html'
    elif ext in ('.css', '.scss', '.less'):
        key = 'css'
    elif ext in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.webp', '.ico'):
        key = 'image'
    elif ext in ('.diff', '.patch') or 'diff' in name:
        key = 'diff'
    else:
        key = 'file'

    cache_key = f'{key}_{is_dark}'
    if cache_key in _DEV_FILE_ICON_CACHE:
        return _DEV_FILE_ICON_CACHE[cache_key]

    fg_file = '#9da5b4' if is_dark else '#64748b'
    _SVGS = {
        'python': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">'
                   '<path fill="#3776AB" d="M7.9 1c-3.6 0-3.4 1.6-3.4 1.6l0 1.6h3.5v.5H3.1C1.5 4.7 1.5 6.4 1.5 6.4l0 1.9c0 1.6 1.4 1.6 1.4 1.6h.9V8.6c0-1.7 1.5-1.7 1.5-1.7h3.4c1.4 0 1.4-1.3 1.4-1.3V3.1c0-1.6-1.8-2.1-1.8-2.1zm-1.8 1a.6.6 0 1 1 0 1.2.6.6 0 0 1 0-1.2z"/>'
                   '<path fill="#FFD43B" d="M8.1 15c3.6 0 3.4-1.6 3.4-1.6l0-1.6H8v-.5h4.9c1.6 0 1.6-1.7 1.6-1.7l0-1.9c0-1.6-1.4-1.6-1.4-1.6h-.9v1.3c0 1.7-1.5 1.7-1.5 1.7H8.8c-1.4 0-1.4 1.3-1.4 1.3v3.5c0 1.6 1.8 2.1 1.8 2.1zm1.8-1a.6.6 0 1 1 0-1.2.6.6 0 0 1 0 1.2z"/>'
                   '</svg>'),
        'markdown': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" fill="#42a5f5">'
                    '<path d="M1 3.5A1.5 1.5 0 0 1 2.5 2h11A1.5 1.5 0 0 1 15 3.5v9a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 1 12.5v-9zM2.5 3a.5.5 0 0 0-.5.5v9a.5.5 0 0 0 .5.5h11a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-11z"/>'
                    '<path d="M3 10.5V5.5h1.5l1.5 2 1.5-2H9v5H7.5V8L6 10 4.5 8v2.5H3zm7-3.5h1V5.5h1.5V7h1l-1.75 2.5L10 7z"/>'
                    '</svg>'),
        'plan': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="#a855f7" stroke-width="1.3">'
                 '<rect x="2.5" y="2" width="11" height="12" rx="2"/>'
                 '<path d="M5 5.5h6M5 8h6M5 10.5h4" stroke-linecap="round"/>'
                 '</svg>'),
        'json': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">'
                 '<text x="8" y="12" font-size="11" font-weight="bold" fill="#fbc02d" font-family="Consolas,monospace" text-anchor="middle">{}</text>'
                 '</svg>'),
        'js': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">'
               '<rect x="2" y="2" width="12" height="12" rx="2" fill="#f7df1e"/>'
               '<text x="8" y="11.5" font-size="8.5" font-weight="bold" fill="#000" font-family="Arial,sans-serif" text-anchor="middle">JS</text>'
               '</svg>'),
        'html': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="#e44d26" stroke-width="1.4" stroke-linecap="round">'
                 '<polyline points="5 5 2 8 5 11"/><polyline points="11 5 14 8 11 11"/><line x1="9" y1="4" x2="7" y2="12"/>'
                 '</svg>'),
        'css': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="#42a5f5" stroke-width="1.5" stroke-linecap="round">'
                '<line x1="6" y1="2" x2="4" y2="14"/><line x1="12" y1="2" x2="10" y2="14"/>'
                '<line x1="3" y1="6" x2="14" y2="6"/><line x1="2" y1="10" x2="13" y2="10"/>'
                '</svg>'),
        'image': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="#e0af68" stroke-width="1.2">'
                  '<rect x="2" y="2" width="12" height="12" rx="1.5"/>'
                  '<circle cx="5.5" cy="5.5" r="1.2" fill="#e0af68"/>'
                  '<path d="M2.5 12l3.5-4.5 2.5 3 2.5-3.5 2.5 5"/>'
                  '</svg>'),
        'diff': ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="#56b6c2" stroke-width="1.3" stroke-linecap="round">'
                 '<circle cx="4" cy="4" r="2"/><circle cx="4" cy="12" r="2"/><circle cx="12" cy="8" r="2"/>'
                 '<path d="M4 6v4M4 6c2 0 6 1 6 2"/>'
                 '</svg>'),
        'file': (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="{fg_file}" stroke-width="1.2">'
                 '<path d="M3 2.5C3 1.67 3.67 1 4.5 1h5l4.5 4.5v8c0 .83-.67 1.5-1.5 1.5h-8A1.5 1.5 0 0 1 3 13.5v-11z"/>'
                 '<polyline points="9.5 1 9.5 5.5 14 5.5"/>'
                 '</svg>'),
    }
    svg_data = _SVGS.get(key, _SVGS['file'])
    try:
        from PyQt5.QtSvg import QSvgRenderer as _SVGRend
        renderer = _SVGRend(QByteArray(svg_data.encode('utf-8')))
        pm = QPixmap(32, 32)
        pm.fill(QColor(0, 0, 0, 0))
        p = QPainter(pm)
        renderer.render(p)
        p.end()
        icon = QIcon(pm)
        _DEV_FILE_ICON_CACHE[cache_key] = icon
        return icon
    except Exception:
        return QIcon()


class ElidedLabel(QLabel):
    """带省略号的标签：文本过长时自动截断加 ...，完整文本通过 tooltip 展示。
    修复历史遗留 bug：ConvoItemWidget 里一直调用 ElidedLabel 但类定义从未存在。"""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._full_text = text or ""
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def setText(self, text: str):
        self._full_text = text or ""
        self._refresh_elided()
        super().setText(self._full_text)

    def resizeEvent(self, event):
        self._refresh_elided()
        super().resizeEvent(event)

    def _refresh_elided(self):
        fm = self.fontMetrics()
        elided = fm.elidedText(self._full_text, Qt.ElideRight, max(10, self.width()))
        super().setText(elided)


# 去除文本中的 emoji（含扩展表情、杂项符号、变体选择符）
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\u2600-\u27BF"
    "\u2B00-\u2BFF"
    "\uFE0F"
    "\U0001F1E6-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)


def strip_emojis(text: str) -> str:
    """去掉文本中的 emoji（历史遗留 bug：被大量调用但从未定义）"""
    if not text:
        return text
    try:
        return _EMOJI_RE.sub("", text)
    except Exception:
        return text


def extract_thought_process(text: str):
    """
    提取大模型的思考过程 (<think>...</think>)，确保思考过程与最终正文彻底分离。
    返回: (clean_content, thought_text)
    （历史遗留 bug：被引用但从未定义，实现移植自 scratch/test_thought_helper.py）
    """
    if not text:
        return "", ""
    thought_text = ""
    clean_content = text
    if "<think>" in text:
        if "</think>" in text:
            m = re.search(r'<think>(.*?)</think>', text, flags=re.DOTALL)
            if m:
                thought_text = m.group(1).strip()
            clean_content = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        else:
            parts = text.split("<think>", 1)
            clean_content = parts[0].strip()
            thought_text = parts[1].strip()
    return clean_content, thought_text


def clean_markdown_tables(text: str) -> str:
    """
    清洗大模型输出的 Markdown 表格：剔除表格中断裂产生的孤立空行。
    （历史遗留 bug：被引用但从未定义，实现移植自 scratch/test_thought_helper.py）
    """
    if not text or "|" not in text:
        return text

    lines = text.split("\n")
    cleaned_lines = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        is_broken_empty_pipe = bool(re.match(r"^\|\s*(\|\s*)*$", stripped) or stripped == "|")
        prev_is_table = (len(cleaned_lines) > 0 and "|" in cleaned_lines[-1] and not cleaned_lines[-1].strip().startswith("```"))

        next_table_line = False
        j = i + 1
        while j < n:
            next_s = lines[j].strip()
            if next_s:
                if "|" in next_s and not next_s.startswith("```"):
                    next_table_line = True
                break
            j += 1

        if prev_is_table and next_table_line:
            if is_broken_empty_pipe or not stripped:
                i += 1
                continue

        cleaned_lines.append(line)
        i += 1

    return "\n".join(cleaned_lines)


def format_relative_time(dt_str: str) -> str:
    """把 'YYYY-MM-DD HH:MM:SS' 转成 '刚刚 / N分钟前 / N小时前 / 昨天 / N天前'。
    （历史遗留 bug：dev_mode_view.py 里被调用但从未定义，chat_window.py 有同款实现）"""
    try:
        dt = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
        diff = datetime.now() - dt
        secs = int(diff.total_seconds())
        if secs < 60:
            return "刚刚"
        elif secs < 3600:
            return f"{secs // 60}分钟前"
        elif secs < 86400:
            return f"{secs // 3600}小时前"
        elif secs < 172800:
            return "昨天"
        else:
            return f"{secs // 86400}天前"
    except Exception:
        return "近期"


class ExploredStepWidget(QWidget):
    """
    探索与分析条目组件 (对齐截图 1、2)
    默认显示：Explored 1 file, 1 folder > 或 Exploring 1 file ▾
    点击可展开折叠，展示 Analyzed 📁 scratch > 与 Analyzed 🐍 xxx #L1-80
    """
    open_file_requested = pyqtSignal(str, int)  # (file_path, line_no)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_expanded = True
        self.analyzed_items = []  # [(path, line_range, item_type)]

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(3)

        self.header_btn = QPushButton("Exploring...")
        self.header_btn.setCursor(Qt.PointingHandCursor)
        self.header_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #8b949e; border: none;
                font-size: 11px; font-family: 'Segoe UI', 'Microsoft YaHei UI';
                text-align: left; padding: 2px 0;
            }
            QPushButton:hover { color: #c9d1d9; }
        """)
        self.header_btn.clicked.connect(self._toggle)
        lay.addWidget(self.header_btn)

        self.items_container = QWidget()
        self.items_lay = QVBoxLayout(self.items_container)
        self.items_lay.setContentsMargins(14, 0, 0, 0)
        self.items_lay.setSpacing(3)
        lay.addWidget(self.items_container)

    def add_item(self, path: str, line_range: str = "", item_type: str = "file"):
        if (path, line_range, item_type) in self.analyzed_items:
            return
        self.analyzed_items.append((path, line_range, item_type))

        row = QWidget()
        r_lay = QHBoxLayout(row)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(6)

        label_text = f"• {path}"
        if line_range:
            label_text += f" <span style='color:#58a6ff;'>{line_range}</span>"

        lbl = QLabel(label_text)
        lbl.setCursor(Qt.PointingHandCursor)
        lbl.setStyleSheet("""
            QLabel {
                color: #8b949e; font-size: 11px; font-family: 'Cascadia Code', Consolas, monospace;
            }
            QLabel:hover {
                color: #58a6ff;
            }
        """)
        
        start_line = 1
        if line_range and "#L" in line_range:
            try:
                part = line_range.split("#L")[1].split("-")[0]
                start_line = int(part)
            except Exception:
                start_line = 1
        lbl.mousePressEvent = lambda e, p=path, l=start_line: self.open_file_requested.emit(p, l)
        
        r_lay.addWidget(lbl)
        r_lay.addStretch()
        self.items_lay.addWidget(row)
        self._update_header()

    def _update_header(self):
        file_cnt = sum(1 for item in self.analyzed_items if item[2] != "folder")
        folder_cnt = sum(1 for item in self.analyzed_items if item[2] == "folder")
        
        parts = []
        if file_cnt > 0:
            parts.append(f"{file_cnt} file" if file_cnt == 1 else f"{file_cnt} files")
        if folder_cnt > 0:
            parts.append(f"{folder_cnt} folder" if folder_cnt == 1 else f"{folder_cnt} folders")
        
        counts_str = ", ".join(parts) if parts else "1 file"
        arrow = "▾" if self.is_expanded else "›"
        self.header_btn.setText(f"Explored {counts_str} {arrow}")

    def _toggle(self):
        self.is_expanded = not self.is_expanded
        self.items_container.setVisible(self.is_expanded)
        self._update_header()


class EditedStepWidget(QFrame):
    """
    Edited [filename] +add -del 步骤卡片 (对齐 Antigravity IDE)
    带 Open Diff 交互胶囊，点击直接打开 Diff 差异比对并自动平滑跳转定位！
    """
    open_file_requested = pyqtSignal(str)
    open_diff_requested = pyqtSignal(str)

    def __init__(self, rel_path: str, action: str, added: int = 0, removed: int = 0, abs_path: str = "", parent=None):
        super().__init__(parent)
        self.rel_path = rel_path.replace("\\", "/")
        self.abs_path = abs_path
        self.action = action
        self.added = added
        self.removed = removed

        self.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
                padding: 1px 0;
            }
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 1, 0, 1)
        lay.setSpacing(6)

        edited_txt = QLabel("Edited")
        edited_txt.setStyleSheet("color: #8b949e; font-size: 11.5px; font-family: 'Segoe UI', 'Microsoft YaHei UI';")
        lay.addWidget(edited_txt)

        self.file_pill = QPushButton(f"{Path(self.rel_path).name}")
        self.file_pill.setCursor(Qt.PointingHandCursor)
        self.file_pill.setToolTip(f"点击在主屏幕代码编辑器打开 `{self.rel_path}`")
        self.file_pill.setStyleSheet("""
            QPushButton {
                background-color: #262b32; color: #abb2bf; border: 1px solid #363c46;
                border-radius: 4px; padding: 2px 8px; font-size: 11px;
                font-family: 'Cascadia Code', Consolas; font-weight: bold;
            }
            QPushButton:hover { background-color: #313742; color: #61afef; border-color: #61afef; }
        """)
        target_p = self.abs_path if (self.abs_path and Path(self.abs_path).is_absolute()) else self.rel_path
        self.file_pill.clicked.connect(lambda: self.open_file_requested.emit(target_p))
        lay.addWidget(self.file_pill)

        diff_tag = QLabel(f"<span style='color:#3fb950; font-weight:bold;'>+{added}</span> <span style='color:#f85149; font-weight:bold;'>-{removed}</span>")
        diff_tag.setStyleSheet("font-size: 11px; font-family: 'Cascadia Code', Consolas;")
        lay.addWidget(diff_tag)

        self.open_diff_btn = QPushButton("Open Diff")
        self.open_diff_btn.setCursor(Qt.PointingHandCursor)
        self.open_diff_btn.setToolTip("在主屏幕打开 Diff 差异比对并自动平滑定位到变更代码处")
        self.open_diff_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b3038; color: #abb2bf; border: 1px solid #3e4451;
                border-radius: 4px; padding: 2px 8px; font-size: 10.5px;
                font-family: 'Segoe UI', 'Microsoft YaHei UI'; font-weight: 500;
            }
            QPushButton:hover {
                background-color: #094771; color: #ffffff; border-color: #61afef;
            }
        """)
        self.open_diff_btn.clicked.connect(lambda: self.open_diff_requested.emit(target_p))
        lay.addWidget(self.open_diff_btn)

        lay.addStretch()


class CommandStepWidget(QWidget):
    """
    终端命令执行卡片 (对齐 Antigravity IDE: Ran pytest ...)
    显示: Ran command ▾ / >
    展开后展示暗色控制台卡片，包含执行命令、错误与输出
    """
    def __init__(self, cmd_str: str, output_text: str = "", exit_code: int = 0, parent=None):
        super().__init__(parent)
        self.cmd_str = cmd_str
        self.output_text = output_text
        self.exit_code = exit_code
        self.is_expanded = True

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(3)

        self.header_btn = QPushButton()
        self.header_btn.setCursor(Qt.PointingHandCursor)
        self.header_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #8b949e; border: none;
                font-size: 11px; font-family: 'Cascadia Code', Consolas;
                text-align: left; padding: 2px 0;
            }
            QPushButton:hover { color: #c9d1d9; }
        """)
        self.header_btn.clicked.connect(self._toggle)
        lay.addWidget(self.header_btn)

        self.console_card = QFrame()
        self.console_card.setStyleSheet("""
            QFrame {
                background-color: #121316;
                border: 1px solid #282c34;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        cc_lay = QVBoxLayout(self.console_card)
        cc_lay.setContentsMargins(6, 4, 6, 4)
        cc_lay.setSpacing(4)

        c_top = QHBoxLayout()
        c_top.setSpacing(6)
        
        err_badge = "<span style='color:#f85149; font-weight:bold;'>[failed] </span>" if exit_code != 0 else ""
        c_prompt_lbl = QLabel(f"{err_badge}<span style='color:#61afef;'>workspace</span> &gt; {cmd_str}")
        c_prompt_lbl.setStyleSheet("color: #abb2bf; font-size: 11px; font-family: 'Cascadia Code', Consolas;")
        c_top.addWidget(c_prompt_lbl, 1)

        copy_btn = QPushButton("Copy")
        copy_btn.setToolTip("复制终端输出")
        copy_btn.setStyleSheet("background: transparent; border: 1px solid #333; border-radius: 3px; color: #858585; font-size: 10px; padding: 1px 5px;")
        def _copy():
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(output_text or cmd_str)
        copy_btn.clicked.connect(_copy)
        c_top.addWidget(copy_btn)
        cc_lay.addLayout(c_top)

        if output_text:
            out_view = QTextBrowser()
            out_view.setPlainText(output_text)
            lines_cnt = len(output_text.splitlines())
            out_view.setFixedHeight(min(160, max(45, lines_cnt * 18 + 10)))
            text_color = "#f85149" if ("Traceback" in output_text or exit_code != 0) else "#abb2bf"
            out_view.setStyleSheet(f"""
                QTextBrowser {{
                    background: transparent;
                    color: {text_color};
                    border: none;
                    font-size: 10.5px;
                    font-family: 'Cascadia Code', Consolas, monospace;
                    line-height: 1.35;
                }}
            """)
            cc_lay.addWidget(out_view)

        lay.addWidget(self.console_card)
        self._update_header()

    def _update_header(self):
        arrow = "▾" if self.is_expanded else "›"
        short_cmd = self.cmd_str[:42] + ("..." if len(self.cmd_str) > 42 else "")
        err_icon = "[failed] " if self.exit_code != 0 else ""
        self.header_btn.setText(f"{err_icon}Ran {short_cmd} {arrow}")

    def _toggle(self):
        self.is_expanded = not self.is_expanded
        self.console_card.setVisible(self.is_expanded)
        self._update_header()


class FileChangeItemWidget(QFrame):
    """单个变动文件的交互条目卡片 (支持单独对比、独立撤销还原、点击打开)"""
    open_file_requested = pyqtSignal(str)
    open_diff_requested = pyqtSignal(str)
    single_accept_requested = pyqtSignal(str)
    single_revert_requested = pyqtSignal(str)

    def __init__(self, rel_path: str, action: str, added: int = 0, removed: int = 0, abs_path: str = "", parent=None):
        super().__init__(parent)
        self.rel_path = rel_path.replace("\\", "/")
        self.abs_path = abs_path or ""
        self.action = action
        self.added = added
        self.removed = removed
        self.is_reverted = False

        # 用于信号发射的路径：优先绝对路径（tracker 以绝对路径作为 key），降级到 rel_path
        self._emit_path = self.abs_path if (self.abs_path and Path(self.abs_path).is_absolute()) else self.rel_path

        self.setObjectName("FileChangeItemWidget")
        self.setStyleSheet("""
            QFrame#FileChangeItemWidget {
                background-color: #282c34;
                border: 1px solid #353b45;
                border-radius: 5px;
                padding: 1px;
            }
            QFrame#FileChangeItemWidget:hover {
                background-color: #2f343f;
                border-color: #61afef;
            }
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(6)

        # 动作徽章 (新建/修改)
        is_create = action in ["created", "新建文件"]
        badge_bg = "#2e7d32" if is_create else "#1565c0"
        badge_txt = "新建" if is_create else "修改"
        badge_lbl = QLabel(f" {badge_txt} ")
        badge_lbl.setStyleSheet(f"background-color: {badge_bg}; color: white; border-radius: 3px; font-size: 10px; font-weight: bold; padding: 1px 3px;")
        lay.addWidget(badge_lbl)

        # 文件路径 (点击可在编辑器打开)
        self.name_lbl = QLabel(self.rel_path)
        self.name_lbl.setStyleSheet("color: #e5c07b; font-size: 11.5px; font-family: 'Cascadia Code', Consolas; font-weight: bold;")
        self.name_lbl.setCursor(Qt.PointingHandCursor)
        self.name_lbl.setToolTip("点击在中间主屏幕代码编辑器中查看该文件")
        lay.addWidget(self.name_lbl)

        # 增删行数徽章 (+25 -0)
        diff_lbl = QLabel(f"<span style='color:#98c379'>+{added}</span> <span style='color:#e06c75'>-{removed}</span>")
        diff_lbl.setTextFormat(Qt.RichText)
        diff_lbl.setStyleSheet("font-size: 11px; font-family: 'Cascadia Code', Consolas;")
        lay.addWidget(diff_lbl)

        lay.addStretch()

        # 按钮 1: Diff 对比
        self.diff_btn = QPushButton("Diff")
        self.diff_btn.setToolTip("在中间主屏幕打开详细代码差异比对视图")
        self.diff_btn.setCursor(Qt.PointingHandCursor)
        self.diff_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b4048; color: #abb2bf; border: none;
                border-radius: 3px; padding: 2px 7px; font-size: 10.5px;
            }
            QPushButton:hover { background-color: #4b5263; color: #ffffff; }
        """)
        self.diff_btn.clicked.connect(lambda: self.open_diff_requested.emit(self._emit_path))
        lay.addWidget(self.diff_btn)

        # 按钮 2: 独立撤销还原 / 重新接纳
        self.action_btn = QPushButton("Revert")
        self.action_btn.setToolTip("单独放弃/撤销此文件的修改")
        self.action_btn.setCursor(Qt.PointingHandCursor)
        self.action_btn.setStyleSheet("""
            QPushButton {
                background-color: #3f1e24; color: #ff7b72; border: 1px solid #5c282d;
                border-radius: 3px; padding: 2px 7px; font-size: 10.5px;
            }
            QPushButton:hover { background-color: #5c282d; color: #ff9999; }
        """)
        self.action_btn.clicked.connect(self._toggle_action)
        lay.addWidget(self.action_btn)

        # 单击文件名触发在编辑器打开
        self.name_lbl.mousePressEvent = lambda e: self.open_file_requested.emit(self._emit_path)

    def _toggle_action(self):
        if not self.is_reverted:
            self.is_reverted = True
            self.action_btn.setText("Accept")
            self.action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e3a24; color: #7ee787; border: 1px solid #285430;
                    border-radius: 3px; padding: 2px 7px; font-size: 10.5px;
                }
                QPushButton:hover { background-color: #285430; color: #a3f7ad; }
            """)
            self.single_revert_requested.emit(self._emit_path)
        else:
            self.is_reverted = False
            self.action_btn.setText("Revert")
            self.action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3f1e24; color: #ff7b72; border: 1px solid #5c282d;
                    border-radius: 3px; padding: 2px 7px; font-size: 10.5px;
                }
                QPushButton:hover { background-color: #5c282d; color: #ff9999; }
            """)
            self.single_accept_requested.emit(self._emit_path)


def _extract_balanced_json(text: str, start: int) -> Optional[str]:
    """从 start 处的 '{' 开始，按字符串/转义语义找到匹配的 '}'，返回完整 JSON 文本"""
    n = len(text)
    if start >= n or text[start] != '{':
        return None
    depth = 0
    in_str = False
    escape = False
    i = start
    while i < n:
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        i += 1
    return None


def _is_tool_call_json(json_text: str) -> bool:
    """判断一段 JSON 文本是否为工具调用对象（含 name/tool + args/params）"""
    try:
        data = json.loads(json_text)
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    t_name = data.get("name") or data.get("tool") or data.get("tool_name") or data.get("function")
    args = data.get("args") or data.get("parameters") or data.get("params")
    return bool(t_name) and isinstance(args, dict)


def _remove_json_tool_calls(text: str) -> str:
    """遍历文本，使用平衡括号 + json 解析移除所有独立工具调用 JSON"""
    result = []
    n = len(text)
    i = 0
    while i < n:
        if text[i] == '{':
            candidate = _extract_balanced_json(text, i)
            if candidate and _is_tool_call_json(candidate):
                i += len(candidate)
                continue
        result.append(text[i])
        i += 1
    return "".join(result)


def sanitize_tool_json_artifacts(text: str) -> str:
    """彻底清洗任何残留在正文中的工具调用代码块与原始 JSON 字符 (拒绝裸露 raw JSON)"""
    if not text:
        return ""
    import re
    # 1. 剔除 ```tool ... ``` 与 ```json {"name": ...} ``` 代码块
    text = re.sub(
        r'```(?:tool|json)?\s*\{[\s\S]*?"(?:name|tool|function)"[\s\S]*?\}\s*```',
        '', text, flags=re.IGNORECASE
    )
    # 2. 剔除多行或单行的独立 JSON 工具调用：{"name": "...", "args": {...}}
    #    先对简单情况做快速清洗，再用平衡括号+json解析兜底处理含未转义 } 的复杂 content
    text = re.sub(
        r'\{\s*"(?:name|tool|function)"\s*:\s*"[^"]+"\s*,\s*"(?:args|parameters|params)"\s*:\s*\{[\s\S]*?\}\s*\}',
        '', text
    )
    text = _remove_json_tool_calls(text)
    # 3. 剔除 TOOL: name {...}
    text = re.sub(r'TOOL:\s*[a-zA-Z0-9_-]+\s*\{[\s\S]*?\}', '', text)
    # 4. 剔除内部协议标记
    text = re.sub(r':::tool_call:[^:\n]+:[^:\n]+(?::[^:\n]+)?:::', '', text)
    text = re.sub(r'\[\[WORKSPACE_[^\]]+\]\]', '', text)
    # 5. 剔除遗留的系统标记
    text = re.sub(r'>\s*\*\*\[代码已自动写入磁盘文件并在主屏幕编辑器中打开\]\*\*[\s\S]*?\*（共\s*\d+\s*行源码已落地就绪[^）]*）\*', '', text)
    # 6. 剔除连续空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def render_plan_to_packaged_html(plan_markdown: str, is_dark: bool = True, code_blocks_store: Optional[List[str]] = None) -> str:
    """
    将技术方案 Markdown 渲染为企业级现代化工程设计文档 (GitHub / Notion 级包装):
    - 结构化卡片排版、分阶段执行路线图胶囊、NEW/MODIFY/DELETE 变动徽章
    - 1:1 像素级复刻办公模式 CodeBlockCard：极客深色卡片、语言标示、复制按钮与 Pygments One-Dark 丰富语法高亮
    """
    clean_md = strip_emojis(sanitize_tool_json_artifacts(plan_markdown))
    if not clean_md:
        clean_md = "*(暂无方案详细内容)*"

    # 替换 [NEW], [MODIFY], [DELETE] 徽章为高质感彩色标签（严谨消费首尾可能出现的所有反引号，避免 Markdown 表格管道符被行内代码吞噬）
    clean_md = re.sub(
        r'`?\[NEW\]`?\s*`?([a-zA-Z0-9_\-/\.\\\(\)]+)`?',
        r'<span style="background-color:rgba(46,160,67,0.25); color:#3fb950; border:1px solid rgba(46,160,67,0.4); padding:1px 6px; border-radius:4px; font-size:11px; font-weight:bold;">NEW</span> <code style="color:#79c0ff; font-weight:600;">\1</code>',
        clean_md
    )
    clean_md = re.sub(
        r'`?\[MODIFY\]`?\s*`?([a-zA-Z0-9_\-/\.\\\(\)]+)`?',
        r'<span style="background-color:rgba(210,153,34,0.25); color:#d29922; border:1px solid rgba(210,153,34,0.4); padding:1px 6px; border-radius:4px; font-size:11px; font-weight:bold;">MODIFY</span> <code style="color:#e3b341; font-weight:600;">\1</code>',
        clean_md
    )
    clean_md = re.sub(
        r'`?\[DELETE\]`?\s*`?([a-zA-Z0-9_\-/\.\\\(\)]+)`?',
        r'<span style="background-color:rgba(248,81,73,0.25); color:#f85149; border:1px solid rgba(248,81,73,0.4); padding:1px 6px; border-radius:4px; font-size:11px; font-weight:bold;">DELETE</span> <code style="color:#ff7b72; font-weight:600;">\1</code>',
        clean_md
    )

    # 替换 Stage 标题为现代步骤胶囊（纯净工程排版，坚决去除小火箭等图标）
    clean_md = re.sub(
        r'(?m)^###?\s*(Stage\s*\d+[^:\n]*:?[^\n]*)',
        r'<div style="background-color:rgba(56,139,253,0.12); border-left:3px solid #388bfd; padding:6px 12px; border-radius:0 6px 6px 0; margin:12px 0 6px 0; color:#79c0ff; font-weight:bold; font-size:13.5px;">\1</div>',
        clean_md
    )

    # 封装代码块为企业级卡片（1:1 对齐办公模式 CodeBlockCard 视觉与 One-Dark 丰富语法高亮）
    LANG_ALIASES = {
        "linux": "bash",
        "terminal": "bash",
        "console": "bash",
        "shell": "bash",
        "sh": "bash",
        "zsh": "bash",
        "cmd": "bat",
        "dos": "bat",
        "py": "python",
        "python3": "python",
        "golang": "go",
        "js": "javascript",
        "ts": "typescript",
        "yml": "yaml",
        "docker": "dockerfile",
    }

    def _package_code_blocks(text: str) -> str:
        def _code_repl(m):
            raw_lang = (m.group(1) or "").strip().lower()
            lang_display = raw_lang if raw_lang and raw_lang != "text" else "code"
            code_content = m.group(2).strip("\r\n")

            # 注册到外部 code_blocks_store，避免在 QUrl 中传递 Base64 因大小写归一化导致损坏
            if code_blocks_store is not None:
                block_idx = len(code_blocks_store)
                code_blocks_store.append(code_content)
                copy_href = f"copy://block/{block_idx}"
            else:
                hex_code = code_content.encode('utf-8', errors='replace').hex()
                copy_href = f"copy://hex/{hex_code}"

            # 1:1 对齐办公模式 CodeBlockCard 的 Pygments One-Dark 丰富语法高亮
            lookup_lang = LANG_ALIASES.get(raw_lang, raw_lang)
            highlighted = ""
            try:
                import pygments
                from pygments.lexers import get_lexer_by_name, TextLexer
                from pygments.formatters import HtmlFormatter
                lexer = None
                if lookup_lang:
                    try:
                        lexer = get_lexer_by_name(lookup_lang)
                    except Exception:
                        pass
                if not lexer:
                    try:
                        lexer = get_lexer_by_name("text")
                    except Exception:
                        lexer = TextLexer()

                style_name = 'one-dark' if 'one-dark' in pygments.styles.get_all_styles() else 'monokai'
                formatter = HtmlFormatter(noclasses=True, style=style_name, nowrap=False)
                highlighted = pygments.highlight(code_content, lexer, formatter)
                highlighted = highlighted.replace('line-height: 125%', 'line-height: 145%')
                highlighted = highlighted.replace('background: #282C34', 'background: transparent').replace('background: #272822', 'background: transparent')
            except Exception:
                highlighted = f'<pre style="margin:0; padding:0; line-height:145%; font-family:\'JetBrains Mono\', Consolas, monospace; color:#f1f5f9;">{html.escape(code_content)}</pre>'

            return (
                f'<table class="code-card" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #30363d; margin:14px 0; border-collapse:collapse; background-color:#161b22;">'
                f'<tr style="background-color:#21262d; border-bottom:1px solid #30363d;">'
                f'<td align="left" style="padding:6px 14px; color:#8b949e; font-family:Consolas, \'JetBrains Mono\', monospace; font-size:11.5px; font-weight:bold; border:none; border-bottom:1px solid #30363d;">{lang_display.upper()}</td>'
                f'<td align="right" style="padding:6px 14px; border:none; border-bottom:1px solid #30363d;">'
                f'<a href="{copy_href}" style="color:#58a6ff; font-family:\'Segoe UI\', \'Microsoft YaHei UI\', sans-serif; font-size:11px; text-decoration:none; font-weight:bold; padding:2px 8px; border:1px solid #30363d; background-color:#21262d; border-radius:3px;">[复制代码]</a>'
                f'</td>'
                f'</tr>'
                f'<tr>'
                f'<td colspan="2" style="padding:12px 14px; background-color:#161b22; border:none; font-family:Consolas, \'JetBrains Mono\', \'Fira Code\', monospace; font-size:12.5px; line-height:145%;">'
                f'{highlighted}'
                f'</td>'
                f'</tr>'
                f'</table>'
            )
        return re.sub(r'```([a-zA-Z0-9_\+#\.\-]*)[\r\n]+(.*?)```', _code_repl, text, flags=re.DOTALL)

    clean_md = _package_code_blocks(clean_md)

    try:
        import markdown
        body_html = markdown.markdown(clean_md, extensions=['tables'])
    except Exception:
        body_html = f"<pre style='color:#c9d1d9; white-space:pre-wrap;'>{html.escape(clean_md)}</pre>"

    css = """
    <style>
        body {
            background-color: #0d1117;
            color: #c9d1d9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei UI", sans-serif;
            font-size: 13px;
            line-height: 1.68;
            padding: 18px 24px 40px 24px;
        }
        h1 {
            color: #58a6ff;
            font-size: 18px;
            border-bottom: 2px solid #30363d;
            padding-bottom: 8px;
            margin-top: 6px;
            margin-bottom: 16px;
        }
        h2 {
            color: #79c0ff;
            font-size: 14.5px;
            background: rgba(33,38,45,0.9);
            border: 1px solid #30363d;
            border-left: 4px solid #58a6ff;
            padding: 8px 14px;
            border-radius: 6px;
            margin-top: 20px;
            margin-bottom: 12px;
        }
        h3 {
            color: #d2a8ff;
            font-size: 13.5px;
            border-left: 3px solid #bc8cff;
            padding-left: 8px;
            margin-top: 14px;
            margin-bottom: 8px;
        }
        p {
            color: #e6edf3;
            margin-top: 4px;
            margin-bottom: 8px;
        }
        ul, ol {
            color: #e6edf3;
            margin-top: 4px;
            margin-bottom: 10px;
            padding-left: 22px;
        }
        li {
            margin-bottom: 4px;
            line-height: 1.6;
        }
        code {
            background-color: #161b22;
            color: #79c0ff;
            border: 1px solid #30363d;
            border-radius: 4px;
            padding: 2px 6px;
            font-family: 'JetBrains Mono', Consolas, monospace;
            font-size: 12px;
        }
        pre {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 12px 14px;
            margin: 12px 0;
            overflow-x: auto;
        }
        pre code {
            background-color: transparent;
            border: none;
            color: #e6edf3;
            font-family: 'JetBrains Mono', Consolas, monospace;
            font-size: 12px;
            line-height: 1.5;
            padding: 0;
        }
        blockquote {
            background-color: #161b22;
            border-left: 4px solid #388bfd;
            color: #8b949e;
            padding: 8px 14px;
            margin: 10px 0;
            border-radius: 0 6px 6px 0;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 14px 0;
            border: 1px solid #30363d;
            border-radius: 6px;
        }
        th {
            background-color: #21262d;
            color: #f0f6fc;
            padding: 8px 12px;
            border: 1px solid #30363d;
            font-weight: bold;
            text-align: left;
        }
        td {
            padding: 7px 12px;
            border: 1px solid #30363d;
            color: #c9d1d9;
        }
        tr:nth-child(even) {
            background-color: #161b22;
        }
        tr:hover {
            background-color: #21262d;
        }
        table.code-card {
            border: 1px solid #30363d !important;
            margin: 14px 0 !important;
            border-collapse: collapse !important;
            background-color: #161b22 !important;
            width: 100% !important;
        }
        table.code-card td {
            border: none !important;
        }
        table.code-card tr {
            background-color: transparent !important;
        }
        div.highlight {
            background: transparent !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
        }
        div.highlight pre {
            background: transparent !important;
            border: none !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 145% !important;
            font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, 'Microsoft YaHei UI', monospace !important;
            font-size: 13px !important;
        }
        span {
            font-style: normal !important;
        }
    </style>
    """
    return f"<!DOCTYPE html><html><head>{css}</head><body>{body_html}</body></html>"


def _is_plan_document(text: str) -> bool:
    """
    多维度严谨判定是否为完整的技术实施方案文档。
    必须满足工程方案的结构特征（具有明确的方案大标题 + 核心工程章节，如文件变更矩阵、落地路线图等）。
    严禁将普通的日常问答、问候、或者简单的数字编号列表误判为实施方案！
    """
    if not text or len(text.strip()) < 120:
        return False

    # 1. 方案文档大标题（通常位于开头几行）
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    first_few_lines = "\n".join(lines[:8])
    has_plan_title = any(
        kw in first_few_lines for kw in [
            "技术落地实施方案", "技术实施方案", "技术落地方案",
            "Implementation Plan", "架构落地实施方案", "工程落地实施方案"
        ]
    ) or any(
        line.startswith("# ") and ("方案" in line or "Plan" in line)
        for line in lines[:8]
    )

    # 2. 核心工程方案章节（真实实施方案的核心要素）
    plan_sections = [
        "文件变更矩阵", "File Change Matrix", "文件变更清单", "Proposed Changes",
        "落地路线图", "Implementation Roadmap", "实施路线图",
        "验收准则与自动化测试", "Verification Plan", "验证计划与准则",
        "边界风险评估", "Risks & Mitigations", "风险与防御对策",
        "目标与架构设计背景", "Goal & Architecture"
    ]
    section_hits = sum(1 for sec in plan_sections if sec in text)

    # 严格判定规则：
    # ① 具有明确的方案大标题，且至少包含 1 个专业方案章节；
    # ② 或者包含至少 2 个高置信度核心章节（如文件变更清单 + 落地路线图/验收准则）
    if has_plan_title and section_hits >= 1:
        return True
    if section_hits >= 2:
        return True

    return False


class ImageViewerWidget(QWidget):
    """
    通用图片预览组件 (作为 QWidget 嵌入到编辑器多标签区域 / Tab 中):
    - 自适应缩放至 tab 内容区尺寸 (按比例缩放，保持原始宽高比)
    - 顶栏显示文件名 + 尺寸信息 + 缩放/还原/关闭按钮
    - 鼠标 Ctrl+滚轮放大缩小，tab 可拉伸
    - 双击图片切换"原始尺寸 ↔ 适配窗口"
    """
    IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff", ".tif"}

    def __init__(self, image_path: str, dev_view=None, parent=None):
        super().__init__(parent)
        self._image_path = image_path
        self._dev_view = dev_view
        self._fit_to_window = True  # 默认适配窗口
        self._zoom_factor = 1.0
        self._orig_pixmap: Optional[QPixmap] = None
        self._loaded_ok = False

        d = True  # 默认按暗色主题绘制（开发模式主皮肤）
        bg = "#1e1e1e" if d else "#ffffff"
        fg = "#e6edf3" if d else "#1f2937"
        sub = "#8b949e"
        border = "#2d2d2d" if d else "#e2e8f0"

        self.setStyleSheet(f"""
            QWidget {{ background-color: {bg}; color: {fg}; }}
            QLabel {{ color: {fg}; }}
            QPushButton {{
                background-color: transparent; color: {fg};
                border: 1px solid {border}; border-radius: 4px;
                padding: 3px 10px; font-size: 11px;
            }}
            QPushButton:hover {{ background-color: #094771; border-color: #1f6feb; color: #ffffff; }}
            QScrollArea {{ background-color: {bg}; border: none; }}
            QScrollBar:vertical {{
                background: #1e1e1e; width: 12px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #424242; border-radius: 4px; min-height: 24px; margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{ background: #616161; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal {{
                background: #1e1e1e; height: 12px; margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: #424242; border-radius: 4px; min-width: 24px; margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{ background: #616161; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 1. 顶栏：文件名 + 尺寸 + 操作按钮
        top = QWidget()
        top.setFixedHeight(38)
        top.setStyleSheet(f"background-color: #161b22; border-bottom: 1px solid {border}; padding: 0 12px;")
        t_lay = QHBoxLayout(top)
        t_lay.setContentsMargins(12, 0, 12, 0)
        t_lay.setSpacing(8)

        title = Path(image_path).name if image_path else "图片预览"
        self.title_lbl = QLabel(f"🖼  <b>{title}</b>")
        self.title_lbl.setStyleSheet(f"color: {fg}; font-size: 12.5px; font-family: 'Segoe UI', 'Microsoft YaHei UI';")
        t_lay.addWidget(self.title_lbl)
        t_lay.addStretch()

        self.size_lbl = QLabel("")
        self.size_lbl.setStyleSheet(f"color: {sub}; font-size: 11px;")
        t_lay.addWidget(self.size_lbl)

        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setFixedSize(28, 24)
        self.btn_zoom_out.setToolTip("缩小 (Ctrl+-)")
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        t_lay.addWidget(self.btn_zoom_out)

        self.btn_zoom_reset = QPushButton("100%")
        self.btn_zoom_reset.setFixedSize(56, 24)
        self.btn_zoom_reset.setToolTip("还原到 100% 原始尺寸 (双击图片也可切换)")
        self.btn_zoom_reset.clicked.connect(self._zoom_reset)
        t_lay.addWidget(self.btn_zoom_reset)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(28, 24)
        self.btn_zoom_in.setToolTip("放大 (Ctrl++)")
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        t_lay.addWidget(self.btn_zoom_in)

        if self._dev_view and hasattr(self._dev_view, 'editor_tab_widget'):
            self.btn_close = QPushButton("✕ 关闭")
            self.btn_close.setFixedSize(70, 24)
            self.btn_close.setToolTip("关闭当前图片预览 Tab")
            self.btn_close.clicked.connect(self._close_self_tab)
            t_lay.addWidget(self.btn_close)
        else:
            self.btn_close = None

        lay.addWidget(top)

        # 2. 滚动区域 + 标签
        self.scroll = QScrollArea()
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setWidgetResizable(False)  # 由我们手动管理 QLabel 尺寸
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet(f"background-color: {bg}; color: {sub}; font-size: 13px;")
        self.img_label.setText("⚠️ 加载中...")
        self.img_label.setMinimumSize(1, 1)  # 避免初始 0 尺寸导致首次渲染失败
        # 关键修复：双击事件用成员方法，确保 self 正确
        self.img_label.mouseDoubleClickEvent = self._on_img_double_click
        self.scroll.setWidget(self.img_label)
        lay.addWidget(self.scroll, 1)

        self._load_image()

    def _close_self_tab(self):
        if not (self._dev_view and hasattr(self._dev_view, 'editor_tab_widget')):
            return
        tw = self._dev_view.editor_tab_widget
        for idx in range(tw.count()):
            if tw.widget(idx) is self:
                tw.removeTab(idx)
                return

    def _on_img_double_click(self, event):
        self._toggle_fit()

    def _load_image(self):
        try:
            p = Path(self._image_path)
            if not p.exists():
                self.img_label.setText(f"⚠️ 图片不存在\n\n{self._image_path}")
                self.size_lbl.setText("")
                return
            # SVG 走 QSvgRenderer；其它走 QPixmap
            if p.suffix.lower() == ".svg":
                renderer = QSvgRenderer(str(p))
                if not renderer.isValid():
                    self.img_label.setText(f"⚠️ SVG 解析失败\n\n{self._image_path}")
                    return
                pm = QPixmap(1024, 768)
                pm.fill(Qt.transparent)
                painter = QPainter(pm)
                renderer.render(painter)
                painter.end()
                self._orig_pixmap = pm
                self.size_lbl.setText(f"SVG · 渲染 1024×768")
            else:
                pm = QPixmap(str(p))
                if pm.isNull():
                    self.img_label.setText(f"⚠️ 图片加载失败 (可能缺少对应格式插件)\n\n{self._image_path}")
                    return
                self._orig_pixmap = pm
                self.size_lbl.setText(f"{pm.width()} × {pm.height()} px · {p.stat().st_size // 1024} KB")
            self._loaded_ok = True
        except Exception as e:
            self.img_label.setText(f"⚠️ 加载异常：{e}")

    def _render_image(self):
        if not self._orig_pixmap or not self._loaded_ok:
            return
        # 取 viewport 实际可用区域
        area_w = max(50, self.scroll.viewport().width() - 4)
        area_h = max(50, self.scroll.viewport().height() - 4)
        pm = self._orig_pixmap
        if self._fit_to_window:
            scaled = pm.scaled(area_w, area_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.img_label.setPixmap(scaled)
            # 关键修复：fit 模式下也要让 QLabel 大小等于 scaled，QScrollArea 才能正确居中
            self.img_label.setFixedSize(scaled.size())
            self._zoom_factor = scaled.width() / max(1, pm.width())
            self.btn_zoom_reset.setText(f"{int(self._zoom_factor * 100)}%")
        else:
            factor = self._zoom_factor
            new_w = max(1, int(pm.width() * factor))
            new_h = max(1, int(pm.height() * factor))
            scaled = pm.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.img_label.setPixmap(scaled)
            self.img_label.setFixedSize(scaled.size())
            self.btn_zoom_reset.setText(f"{int(factor * 100)}%")

    def _toggle_fit(self):
        self._fit_to_window = not self._fit_to_window
        if not self._fit_to_window:
            self._zoom_factor = 1.0
        self._render_image()

    def _zoom_in(self):
        if self._fit_to_window:
            self._fit_to_window = False
            self._zoom_factor = 1.0
        self._zoom_factor = min(8.0, self._zoom_factor * 1.25)
        self._render_image()

    def _zoom_out(self):
        if self._fit_to_window:
            return
        self._zoom_factor = max(0.1, self._zoom_factor / 1.25)
        self._render_image()

    def _zoom_reset(self):
        self._fit_to_window = True
        self._zoom_factor = 1.0
        self._render_image()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 关键修复：tab 尺寸变化 / 初始化后都要重新渲染
        if self._fit_to_window:
            QTimer.singleShot(0, self._render_image)

    def showEvent(self, event):
        super().showEvent(event)
        # 关键修复：刚加入 tab 时 viewport 还没布局好，延迟到下一帧再渲染
        QTimer.singleShot(20, self._render_image)
        QTimer.singleShot(120, self._render_image)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Plus, Qt.Key_Equal) and (event.modifiers() & Qt.ControlModifier):
            self._zoom_in()
        elif event.key() == Qt.Key_Minus and (event.modifiers() & Qt.ControlModifier):
            self._zoom_out()
        elif event.key() == Qt.Key_0 and (event.modifiers() & Qt.ControlModifier):
            self._zoom_reset()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self._zoom_in()
            else:
                self._zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    @classmethod
    def is_image_file(cls, path: str) -> bool:
        try:
            return Path(path).suffix.lower() in cls.IMAGE_EXTS
        except Exception:
            return False

    @classmethod
    def open_in_editor_tab(cls, dev_view, image_path: str):
        """在 dev_view 的 editor_tab_widget 中以新 Tab 打开图片预览"""
        p = Path(image_path)
        if not dev_view or not hasattr(dev_view, 'editor_tab_widget'):
            return None
        tab_title = f"🖼 {p.name}"
        # 检查是否已打开同一图片
        for idx in range(dev_view.editor_tab_widget.count()):
            w = dev_view.editor_tab_widget.widget(idx)
            if isinstance(w, ImageViewerWidget) and getattr(w, '_image_path', '') == str(p.resolve()):
                dev_view.editor_tab_widget.setCurrentIndex(idx)
                return w
        viewer = cls(str(p.resolve()), dev_view=dev_view, parent=dev_view)
        idx = dev_view.editor_tab_widget.addTab(viewer, tab_title)
        dev_view.editor_tab_widget.setCurrentIndex(idx)
        # 如果有 FileDiffTracker，记录一次查看
        try:
            from core.file_diff_tracker import FileDiffTracker
            tracker = FileDiffTracker.get_instance()
            abs_p = str(p.resolve())
            if not tracker.get_record(abs_p):
                tracker.record_change(
                    rel_path=p.name,
                    abs_path=abs_p,
                    before_content="",
                    after_content=f"[图片预览] {p.name}",
                    session_id=getattr(dev_view, '_current_session_id', '') or ""
                )
        except Exception:
            pass
        return viewer


class TerminalEdit(QTextEdit):
    """
    单一终端控件 — 显示 + 输入合二为一：
    - 用户直接在终端里敲命令（光标处插入字符，本地回显）
    - Enter (无 Shift): 把输入区所有非空行作为命令一次性发给 PTY（多行批量执行）
    - Shift + Enter: 在框内插入换行（多行编辑）
    - cmd 的「重发整行」回显由父控件 _on_pty_output 处理，本控件只负责本地插入
    - Backspace 仅在输入区内有效（不破坏之前的输出）
    """
    submitRequested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 禁用中文输入法吞键（空格/回车/-/引号这些键经常被 IME 拦截）
        self.setAttribute(Qt.WA_InputMethodEnabled, False)
        self.setInputMethodHints(Qt.ImhPreferLatin)
        # 输入区起点：光标允许移动到的最左位置。父控件每次显示新 prompt 时会调用
        # _set_input_anchor_at_end() 把这个值更新到文档末尾。
        self._input_anchor = 0

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        key = event.key()
        mods = event.modifiers()
        text = event.text() or ""
        # 关键兜底：PyQt5 某些平台 event.text() 对符号/空格返回空字符串，用 key 转回
        if not text and Qt.Key_Space <= key <= Qt.Key_AsciiTilde:
            text = chr(key)

        # Ctrl+C：有选区 → 复制到剪贴板；无选区 → 作为中断信号(SIGINT \x03)转发 PTY。
        # 这是标准终端（Windows Terminal / VS Code 集成终端）的约定：选中文本时
        # Ctrl+C 是复制，没选中时 Ctrl+C 是中断当前正在跑的命令。
        # 必须放在下方"光标位置修正"之前——否则选区落在历史输出区时，会被
        # setPosition(_input_anchor) 清掉，导致复制永远拿不到内容。
        if (mods & Qt.ControlModifier) and key == Qt.Key_C:
            if cursor.hasSelection():
                self.copy()
            else:
                self.submitRequested.emit('\x03')
            return
        # Ctrl+L: 清屏 form feed 直接转发 PTY
        if (mods & Qt.ControlModifier) and key == Qt.Key_L:
            self.submitRequested.emit('\x0c')
            return

        # Ctrl+V (含 Ctrl+Shift+V / 任何带 Ctrl 的 V): 拦截走标准 paste()，
        # 从而进入我们重写的 insertFromMimeData，按"粘贴进输入区"语义处理。
        # 千万不能落到下面的 `if text:` 把 'V' 字符插入到终端（Qt.Key_V=0x56 会
        # 被 chr() 救出 'V'，从而变成"按 Ctrl+V 打出字母 V"的常见 bug）。
        if (mods & Qt.ControlModifier) and key == Qt.Key_V and not (mods & Qt.AltModifier):
            self.paste()
            return

        # Ctrl+Insert 也是常见"粘贴"快捷键，Win/Linux 终端/Cmd 历史常见组合
        if (mods & Qt.ControlModifier) and key == Qt.Key_Insert:
            self.paste()
            return

        # 不让光标越过输入区起点（防止破坏之前的输出行）。
        # 只对"编辑/输入"动作生效；复制(Ctrl+C)/粘贴(Ctrl+V)已在上方处理，不受影响。
        if cursor.position() < self._input_anchor:
            cursor.setPosition(self._input_anchor)
            self.setTextCursor(cursor)

        if key in (Qt.Key_Return, Qt.Key_Enter):
            if mods & Qt.ShiftModifier:
                # Shift+Enter: 插入换行（多行编辑）
                cursor.insertText('\n')
                self.setTextCursor(cursor)
                return
            # 普通 Enter: 提交输入区所有非空行
            full = self.toPlainText()
            input_text = full[self._input_anchor:]
            lines = [ln for ln in input_text.split('\n') if ln.strip()]
            if lines:
                # 在输入区后插入换行，让 cmd 的回显/输出自然落在下一行
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.End)
                cursor.insertText('\n')
                self.setTextCursor(cursor)
                # 提交（multi-line 命令在 _on_submit_requested 里会被逐条写到 PTY）
                self.submitRequested.emit('\n'.join(lines))
                # 输入区起点重置到文档末尾
                cursor.movePosition(QTextCursor.End)
                self._input_anchor = cursor.position()
                self.setTextCursor(cursor)
            return

        if key == Qt.Key_Backspace:
            if cursor.position() > self._input_anchor:
                cursor.deletePreviousChar()
                self.setTextCursor(cursor)
            return

        if text:
            cursor.insertText(text)
            self.setTextCursor(cursor)

    def insertFromMimeData(self, source):
        """
        重写 QTextEdit 的粘贴入口，覆盖以下入口：
        - Ctrl+V / Ctrl+Shift+V / Ctrl+Insert 触发的 paste()
        - 右键菜单的"粘贴"
        - 程序化调用 paste()

        语义：
        - 粘贴纯文本 → 插入到当前输入区（_input_anchor 之后），
          多行按行分块但不引入额外空行（粘贴时 \n 已是用户自己的换行意图）。
        - 粘贴图片或非文本 → 走 QTextEdit 默认行为（仍可能被粘贴成 base64 文本，
          但本控件是终端，通常不需要图片粘贴）。
        """
        if source is None:
            return
        # 仅处理纯文本：html 也降级为 text（终端不渲染富文本）
        text = ""
        if source.hasText():
            text = source.text()
        elif source.hasHtml():
            text = source.html()  # 退化路径；正常情况用户复制的就是纯文本
        if not text:
            return

        # 把光标强制拉到 _input_anchor 之后（粘贴不应污染历史输出区）
        cursor = self.textCursor()
        cursor.setPosition(self._input_anchor)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        # 把当前输入区已存在的"残留未提交内容"也清掉，避免粘贴后粘连
        # （如果当前输入区为空，这步就是 no-op）
        cursor.removeSelectedText()
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        # 按 \n 切分，逐段插入（每段一个 block），保留用户的换行意图
        first = True
        for part in text.split('\n'):
            if not first:
                cursor.insertBlock()
            first = False
            if part:
                cursor.insertText(part)
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_input_anchor_at_end(self):
        """父控件在显示新 prompt 后调用，把输入区起点挪到当前光标末尾。"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._input_anchor = cursor.position()
        self.setTextCursor(cursor)

    def append_text(self, text: str):
        """父控件调用：在文档末尾追加纯文本（已剥离 ANSI），并把光标挪到末尾。"""
        if not text:
            return
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        # 把 \n 转为 QTextEdit 的换行（用 insertBlock 产生新段落，避免和现有 block 拼接）
        parts = text.split('\n')
        for i, part in enumerate(parts):
            if i > 0:
                cursor.insertBlock()
            if part:
                cursor.insertText(part)
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    def replace_input_area(self, new_text: str):
        """父控件调用：替换输入区内容（处理 cmd 重发整行的回显）。"""
        cursor = self.textCursor()
        # 选中从输入区起点到文档末尾的内容
        cursor.setPosition(self._input_anchor)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        if new_text:
            cursor.insertText(new_text)
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())


class InteractiveTerminalWidget(QWidget):
    """
    真正的交互式终端 (基于 Windows ConPTY / pywinpty):
    - 单 QTextEdit 同时承担显示与输入（用户直接在终端里敲命令，没有独立输入框）
    - Enter / Shift+Enter 多行批量执行
    - cmd 的「重发整行」回显由 _on_pty_output 检测并替换输入区，不会重复显示
    - 顶栏极简：当前路径 + 清屏按钮
    """
    # 用 Qt Signal 跨线程安全传递 PTY 输出（比 QTimer.singleShot 可靠，sleep 时不丢消息）
    pty_output_signal = pyqtSignal(str)
    pty_closed_signal = pyqtSignal()

    ANSI_SGR_RE = re.compile(r'\x1b\[([0-9;]*)m')
    ANSI_CSI_RE = re.compile(r'\x1b\[[0-9;?]*[ -/]*[@-~]')
    ANSI_OSC_RE = re.compile(r'\x1b\][\s\S]*?(?:\x07|\x1b\\|\x9c)')
    _COLOR_MAP = {
        0: '#abb2bf', 1: '#e06c75', 2: '#98c379', 3: '#e5c07b',
        4: '#61afef', 5: '#c678dd', 6: '#56b6c2', 7: '#dcdfe4',
    }
    _BRIGHT_MAP = {
        0: '#5c6370', 1: '#ff7b72', 2: '#7ee787', 3: '#ffd580',
        4: '#79c0ff', 5: '#d2a8ff', 6: '#7ed3de', 7: '#ffffff',
    }
    _OSC_TERM_RE = re.compile(r'\x07|\x1b\\|\x9c')

    def __init__(self, workspace_root: str, parent=None):
        super().__init__(parent)
        self.workspace_root = workspace_root
        self.history: List[str] = []
        self.history_idx = 0
        self._pty = None
        self._reader_thread: Optional[threading.Thread] = None
        self._ansi_buffer = ""  # 缓存跨 chunk 的不完整 ANSI 序列
        self._osc_pending = False  # 是否处于 OSC 累积模式
        self._exit_status: Optional[int] = None
        self._closed = False
        self._known_prompt = None  # cmd 提示符（如 "C:\...>"），用于识别「cmd 重发整行」模式

        # —— 抑制 cmd "重发整行" 回显残留的状态机 ——
        # 用户回车提交命令后，cmd 会把 `\r<prompt><用户命令>\n` 重发一次，
        # PTY 时序偶尔会把 prompt 段和 command 段拆成两个 chunk：
        #   chunk A: \rC:\...\测试>
        #   chunk B: java --version\n
        # A 被单 prompt 分支处理，B 落到"无 prompt 分支"——以往会原样追加到
        # 锚点前，导致屏幕上多出一行重复命令。
        # 现在：在 _on_submit_requested 中把本次提交的命令列表记到
        # _last_submitted_cmds 并开启 _suppress_echo_until_prompt；
        # 在 _handle_plain 看到下一个 prompt 时清空这两个状态。
        self._last_submitted_cmds: List[str] = []
        self._suppress_echo_until_prompt = False

        # Qt Signal 跨线程通信：后台线程 emit，主线程 slot（线程安全，sleep 时不丢消息）
        self.pty_output_signal.connect(self._feed_output)
        self.pty_closed_signal.connect(self._on_pty_exit)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 顶栏：极简风（参照 Windows Terminal），只留一个清屏按钮 + 当前目录
        bar = QWidget()
        bar.setFixedHeight(28)
        bar.setStyleSheet("background-color: #161b22; border-bottom: 1px solid #2d2d2d;")
        b_lay = QHBoxLayout(bar)
        b_lay.setContentsMargins(10, 0, 10, 0)
        b_lay.setSpacing(8)

        self.path_lbl = QLabel(self.workspace_root)
        self.path_lbl.setStyleSheet("color: #79c0ff; font-size: 11px; font-family: 'Cascadia Code', Consolas, monospace;")
        b_lay.addWidget(self.path_lbl)
        b_lay.addStretch()

        self.btn_clear_screen = QPushButton("清屏")
        self.btn_clear_screen.setCursor(Qt.PointingHandCursor)
        self.btn_clear_screen.setToolTip("清空终端输出（cls）")
        self.btn_clear_screen.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #8b949e;
                border: 1px solid #30363d; border-radius: 4px;
                padding: 2px 10px; font-size: 11px;
            }
            QPushButton:hover { background-color: #21262d; color: #ffffff; border-color: #58a6ff; }
        """)
        self.btn_clear_screen.clicked.connect(self._clear_screen)
        b_lay.addWidget(self.btn_clear_screen)

        lay.addWidget(bar)

        # 单一终端控件：同时承担显示与输入（用户直接在终端里敲命令）
        self.terminal = TerminalEdit(self)
        self.terminal.setStyleSheet("""
            QTextEdit {
                background-color: #0c0c0c;
                color: #cccccc;
                border: none;
                font-family: 'Cascadia Code', Consolas, 'Courier New', monospace;
                font-size: 13px;
                padding: 8px 12px;
                selection-background-color: #264f78;
            }
        """)
        self.terminal.setAcceptRichText(False)
        self.terminal.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.terminal.submitRequested.connect(self._on_submit_requested)
        lay.addWidget(self.terminal, 1)

        # 启动 ConPTY
        self._start_pty()

    # ── ConPTY 生命周期 ────────────────────────────────────────
    def _start_pty(self):
        try:
            # 直接 import：依赖桌宠运行所用的 Python (anaconda 3.10) 自带的 pywinpty
            from winpty import PtyProcess
            self._pty = PtyProcess.spawn(
                'cmd.exe',
                cwd=self.workspace_root,
                dimensions=(120, 40),
            )
            self._closed = False
            self._exit_status = None
            # 主动预热：短暂 sleep 后主动 read 一次 banner，避免后台线程阻塞时用户看到空白
            import time as _t
            _t.sleep(0.6)
            try:
                _initial = self._pty.read(8192)
                if _initial:
                    self._feed_output(_initial)
            except Exception:
                pass
            # 启动后台持续读取线程
            self._reader_thread = threading.Thread(target=self._read_output_loop, daemon=True)
            self._reader_thread.start()
        except Exception as e:
            self._pty = None
            self._append_before_input(f"[ConPTY 启动失败] {e}")
            self._append_before_input(
                "anaconda 环境已自带 pywinpty 2.0.10，若仍失败请确认依赖。\n"
            )

    def _restart_pty(self):
        self._close_pty()
        self._append_before_input("--- 终端已重启 ---\n")
        # PTY 重启 = 全新的 cmd 会话，旧的提交命令记录不再有意义，清空抑制窗口
        self._suppress_echo_until_prompt = False
        self._last_submitted_cmds = []
        self._start_pty()

    def _close_pty(self):
        self._closed = True
        if self._pty is not None:
            try:
                self._pty.close()
            except Exception:
                pass
            self._pty = None

    def _read_output_loop(self):
        try:
            while not self._closed and self._pty is not None:
                try:
                    if not self._pty.isalive():
                        break
                    data = self._pty.read()
                    if data is None or data == "":
                        break
                    self._emit_output(data)
                except Exception:
                    break
        finally:
            self._emit_done()

    # ── ANSI 解析 & 输出处理 ──────────────────────────────────
    def _feed_output(self, text: str):
        """
        处理 PTY 输出：
        1. 剥 ANSI / OSC / CSI 等控制序列
        2. 检测 cmd 的 prompt 模式（<drive>:\<path>>）
        3. 识别「cmd 重发整行」: 一次 PTY chunk 内出现两个 prompt（前一个 = 重发，后一个 = 新 prompt）
           → 抑制重发内容，仅显示中间的输出 + 新 prompt
        4. 在输入区起点之前用 append_text，在起点之后用 replace_input_area（避免破坏用户输入）
        """
        if not text:
            return
        self._ansi_buffer += text
        buf = self._ansi_buffer
        plain_parts = []
        pos = 0
        n = len(buf)

        if self._osc_pending:
            term_m = self._OSC_TERM_RE.search(buf)
            if term_m:
                self._osc_pending = False
                pos = term_m.end()
            else:
                self._ansi_buffer = buf
                return

        while pos < n:
            ch = buf[pos]
            if ch == '\x1b':
                m = self.ANSI_SGR_RE.match(buf, pos)
                if m:
                    pos = m.end()
                    continue
                m2 = self.ANSI_CSI_RE.match(buf, pos)
                if m2:
                    pos = m2.end()
                    continue
                m3 = self.ANSI_OSC_RE.match(buf, pos)
                if m3:
                    pos = m3.end()
                    continue
                if pos + 1 < n and buf[pos + 1] == ']':
                    term_m = self._OSC_TERM_RE.search(buf, pos + 2)
                    if term_m:
                        pos = term_m.end()
                        continue
                    self._osc_pending = True
                    self._ansi_buffer = buf
                    if plain_parts:
                        self._handle_plain(''.join(plain_parts))
                    return
                break
            elif ch == '\r':
                # CR 在 cmd 输出中表示「重定位到行首」，通常后跟 LF；我们不渲染 CR 本身
                pos += 1
                continue
            elif ch == '\n':
                plain_parts.append('\n')
                pos += 1
                continue
            seg_start = pos
            while pos < n and buf[pos] not in ('\x1b', '\r', '\n'):
                pos += 1
            if pos > seg_start:
                plain_parts.append(buf[seg_start:pos])

        self._ansi_buffer = buf[pos:]
        if plain_parts:
            self._handle_plain(''.join(plain_parts))

    def _last_user_command_after_prompt(self) -> str:
        """
        从 self._input_anchor 之前的文档中，提取用户上一次敲入的命令（即最后一个
        prompt 之后的那一行非空内容）。返回的字符串不含末尾换行符。
        """
        all_text = self.terminal.toPlainText()
        before = all_text[:self.terminal._input_anchor]
        for line in reversed(before.rstrip('\n').split('\n')):
            if '>' in line:
                return line.split('>', 1)[1]
        return ''

    def _handle_plain(self, plain: str):
        """根据 plain 中是否含 cmd prompt 来决定：追加新内容 / 替换输入区"""
        if not plain:
            return
        # prompt 模式：C:\<...路径>>  (允许 ANSI 已被剥掉，所以这里是纯文本)
        prompt_re = re.compile(r'([A-Z]:\\[^>\r\n]*?)>')
        matches = list(prompt_re.finditer(plain))

        # —— 强抑制：PTY 把"重发整行"切成两段时，仅剩 command 段会落到这里。
        # 例：cmd 输出 `\rC:\...\测试>java --version\n` 偶尔被切成两 chunk：
        #   [A] \rC:\...\测试>
        #   [B] java --version\n
        # A 走"单 prompt"分支处理，B 走这里。无 prompt 时若 plain 整段就是
        # 用户刚敲过的某条命令，直接吃掉（cmd 的"重发回显"语义上不该出现）。
        # 仅抑制"无 \n 的单行命令"，多行文本一定是真正的输出。
        if (
            not matches
            and self._suppress_echo_until_prompt
            and self._last_submitted_cmds
        ):
            plain_stripped = plain.rstrip('\n').rstrip('\r').strip()
            if (
                plain_stripped
                and '\n' not in plain_stripped
                and plain_stripped in self._last_submitted_cmds
            ):
                # 命中抑制：什么都不显示
                return

        if not matches:
            # 没有 prompt：当作普通输出追加
            self._append_before_input(plain)
            return

        if len(matches) == 1:
            # 单个 prompt = 初始 banner 后的第一个 prompt（或普通命令完成后的新 prompt）
            m = matches[0]
            before = plain[:m.start()]
            prompt_str = plain[m.start():m.end()]
            after = plain[m.end():]

            # 关键：抑制 cmd 的「重发整行」回显。
            # 背景：用户敲回车后，cmd 在收到 \r 时会输出 `\r<prompt><当前命令>\n`
            # （即把光标回到行首再写 prompt+当前输入），在真终端里这一行会"覆盖"
            # 之前的输入行，但 QTextEdit 是插入模式，会变成追加。
            # "多个 prompt" 分支只在 PTY 一次性输出两个 prompt 时才能正确抑制重发；
            # PTY 分块（重发整行独立 flush）时这里会落到"单个 prompt"分支，
            # 于是屏幕上出现两次 `java --version` 这种重复。
            # 修复：如果 plain = `prompt + 用户上一次命令 + \n`，就跳过（不显示）。
            after_stripped = after.rstrip('\n')
            if after_stripped:
                last_cmd = self._last_user_command_after_prompt()
                if last_cmd and after_stripped == last_cmd:
                    # cmd 重发整行，抑制（避免屏幕上出现重复命令）
                    # cmd 已经把"重发回显"送完，这一轮抑制窗口可以关闭
                    self._suppress_echo_until_prompt = False
                    self._last_submitted_cmds = []
                    return

            self._current_prompt = m.group(1)
            # 把 prompt 之前的内容 + prompt + prompt 之后的内容追加到输入区前
            combined = before + prompt_str + after
            self._append_before_input(combined)
            # 输入区起点挪到当前文档末尾（用户从此处开始敲下一条命令）
            self.terminal.set_input_anchor_at_end()
            # 看到下一个 prompt：关闭抑制窗口、清空本次提交命令记录
            self._suppress_echo_until_prompt = False
            self._last_submitted_cmds = []
            return

        # 多个 prompt：最后一个 = 新 prompt，倒数第二个 = cmd 重发整行的回显
        re_emit = matches[-2]
        new_prompt = matches[-1]
        self._current_prompt = new_prompt.group(1)

        # 重发 prompt 的前缀（\r\n）剥掉
        leading = plain[:re_emit.start()].lstrip('\r\n')
        # 重发回显中含 user 当时输入的命令：prompt + input
        # 我们要抑制这部分，仅显示 prompt 与新 prompt 之间的内容（即命令的真正输出）
        between = plain[re_emit.end():new_prompt.start()].rstrip('\r\n')
        # 新 prompt 之后的内容（如果有的话，比如 prompt 行尾部有内容）
        after_new = plain[new_prompt.end():]

        # 把 leading 和 between 当作「输出内容」追加到输入区前
        output_section = (leading + ('\n' if leading and between else '') + between).rstrip('\n')
        if output_section:
            self._append_before_input(output_section + '\n')
        # 显示新 prompt
        self._append_before_input(plain[new_prompt.start():new_prompt.end()])
        if after_new:
            # prompt 行尾部还有内容（罕见，比如启动脚本注入的尾巴）—— 也追加
            self._append_before_input(after_new)
        # 输入区起点挪到末尾
        self.terminal.set_input_anchor_at_end()
        # 看到新 prompt：关闭抑制窗口、清空本次提交命令记录
        self._suppress_echo_until_prompt = False
        self._last_submitted_cmds = []

    def _append_before_input(self, text: str):
        """
        把 text 插入到输入区起点之前（即追加到已固定的输出区，不会污染用户当前输入行）。
        text 中可能含 \\n，但 \\r 已被 _feed_output 剥掉。

        关键：插入完成后必须把 self._input_anchor 推进到当前 cursor position。
        否则下一个 chunk（特别是 cmd 的「新 prompt」）会以旧 anchor 为插入点，
        被插到更早的 chunk 前面，导致 PTY 输出顺序在屏幕上颠倒
        （例：java --version 的结果出现在新 prompt 之后才被显示）。
        """
        if not text:
            return
        anchor = self.terminal._input_anchor
        cursor = self.terminal.textCursor()
        cursor.setPosition(anchor)
        # 把 text 按 \\n 切分，逐段插入（每段一个 block）
        first = True
        for part in text.split('\n'):
            if not first:
                cursor.insertBlock()
            first = False
            if part:
                cursor.insertText(part)
        # 关键修复：anchor 必须跟随新插入的内容后移，
        # 这样后续 _append_before_input 调用都在"已显示内容"之后追加。
        self.terminal._input_anchor = cursor.position()
        # 滚到底
        sb = self.terminal.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_submit_requested(self, text: str):
        """
        TerminalEdit 提交信号：
        - text 是以 \\n 拼接的命令（多行 = 一次性粘贴的多条命令）
        - 普通命令：每行独立写到 PTY（每条带 \\r\\n，cmd 才会真正执行）；
          一次性 send 多行会让 cmd 把它们当成一行命令一次性"按回车"，
          行间没有 prompt 间隔，行为不可预期。逐条发送则每条都能独立产出
          一个新 prompt，行为贴合"在 cmd 里一行一行回车"。
        - 控制字符（\\x03 / \\x0c）：直接转发给 PTY（Ctrl+C / Ctrl+L），
          这两个字符本身就是完整指令，不能再加 \\r\\n
        - 同步把本次提交的命令列表记下来，供 _handle_plain 在 cmd 的"重发整行
          回显被 PTY chunk 切碎"时做精准抑制（避免屏幕上多出一行重复命令）
        """
        if self._pty is None or self._closed:
            return
        if not text:
            return
        # 控制字符：原样转发，且不计入 _last_submitted_cmds
        if text in ('\x03', '\x0c'):
            try:
                self._pty.write(text)
            except Exception as e:
                self._append_before_input(f"[PTY 写入失败] {e}")
            return

        # 普通命令：逐条 strip + 逐条写 PTY
        lines = [ln for ln in text.split('\n') if ln.strip()]
        if not lines:
            return
        try:
            for ln in lines:
                self._pty.write(ln + '\r\n')
        except Exception as e:
            self._append_before_input(f"[PTY 写入失败] {e}")
            return

        # 记录本次提交的命令，状态机一直保持"抑制 cmd 重发整行回显"直到
        # _handle_plain 拿到下一个 prompt 为止。
        self._last_submitted_cmds = list(lines)
        self._suppress_echo_until_prompt = True

    def _emit_output(self, text: str):
        self.pty_output_signal.emit(text)

    def _emit_done(self):
        self.pty_closed_signal.emit()

    def _on_pty_exit(self):
        code = None
        try:
            if self._pty is not None:
                code = self._pty.exitstatus
        except Exception:
            code = None
        self._closed = True
        if code not in (None, 0):
            self._append_before_input(f"[进程已退出，退出码 {code}]")

    def focus_input(self):
        """切到交互终端 tab 时让 TerminalEdit 拿到焦点 + 光标到末尾"""
        self.terminal.setFocus()
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.terminal.setTextCursor(cursor)

    def focus_terminal(self):
        self.focus_input()

    def _clear_screen(self):
        # 直接清空 QTextEdit + 显示当前 prompt + 重置 anchor。
        # 不再写 cls 给 PTY：cmd 的 cls 会输出 ANSI 清屏序列（被 _feed_output 剥掉，
        # 对 QTextEdit 无效）并且会回显 `C:\...>cls` 一行，反而把"清屏"按钮按下后
        # 残留的那一行带回来。cmd 内部是否清屏不影响 QTextEdit 显示，
        # 用户看的是 QTextEdit，所以只需把 QTextEdit 清空 + 显示 prompt 即可。
        self.terminal.clear()
        prompt = getattr(self, '_current_prompt', None) or self.workspace_root
        self._append_before_input(prompt + '>')
        # 把输入区起点挪到 prompt 之后（用户从此处开始敲下一条命令）
        self.terminal.set_input_anchor_at_end()
        # 滚到底
        sb = self.terminal.verticalScrollBar()
        sb.setValue(sb.maximum())
        # 同步清空抑制 cmd 重发整行的窗口（清屏=丢弃过去所有命令记录）
        self._suppress_echo_until_prompt = False
        self._last_submitted_cmds = []

    def shutdown(self):
        """程序退出时释放 PTY 资源"""
        self._close_pty()

    def showEvent(self, event):
        """每次被 QStackedWidget 切到可见时把焦点给 TerminalEdit"""
        super().showEvent(event)
        QTimer.singleShot(0, self.terminal.setFocus)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if not self.terminal.hasFocus():
            self.terminal.setFocus()


def _generate_plan_chat_summary(clean_full: str, plan_file_name: str = "implementation_plan.md") -> str:
    """
    为右侧 AI 问答对话流生成轻量级的大概步骤和流程总结 (对齐用户需求：
    AI 聊天框只呈现精炼的步骤与流程，详细文档全部沉淀在 implementation_plan.md 并在主屏幕渲染展示)
    """
    clean_full = sanitize_tool_json_artifacts(clean_full)
    lines = [ln.strip() for ln in clean_full.splitlines() if ln.strip()]

    # 提取标题
    title = "技术落地实施方案"
    for ln in lines[:10]:
        if ln.startswith("# "):
            title = ln.lstrip("# ").strip()
            break
        elif ln.startswith("## ") and title == "技术落地实施方案":
            title = ln.lstrip("# ").strip()

    # 提取关键步骤与阶段
    steps = []
    import re
    for ln in lines:
        if re.match(r'^###?\s*(?:阶段|步骤|Stage|Step|\d+[\.、])', ln, re.I):
            s = re.sub(r'^###?\s*', '', ln).strip()
            if s and s not in steps:
                steps.append(s)
        elif re.match(r'^(?:[一二三四五六七八九十]+[、\.]|\d+[\.、])\s*', ln):
            s = re.sub(r'^(?:[一二三四五六七八九十]+[、\.]|\d+[\.、])\s*', '', ln).strip()
            if s and not any(k in s for k in ["目标与架构", "文件变更", "落地路线", "风险评估", "验收准则"]):
                if s not in steps:
                    steps.append(s)
        elif re.match(r'^\d+[\.、]\s+\*\*', ln):
            m = re.match(r'^\d+[\.、]\s+\*\*([^\*]+)\*\*', ln)
            if m:
                s = m.group(1).strip()
                if s and s not in steps:
                    steps.append(s)
        elif re.match(r'^(?:Proposed Changes|技术架构|Verification Plan|验证方案|实施规划)', ln, re.I):
            if ln not in steps:
                steps.append(ln)

    res = []
    clean_title = strip_emojis(title).strip()
    res.append(f"### {clean_title} · 方案规划概要\n")
    res.append("已为您深入梳理系统现状并设计了严谨的技术落地实施方案。核心执行阶段与流程概要如下：\n")
    if steps:
        for idx, s in enumerate(steps[:6], 1):
            s_clean = strip_emojis(s).strip()
            res.append(f"**{idx}.** {s_clean}")
    else:
        res.append("1. **系统调研与依赖梳理**：定位受影响文件与核心调用链路。")
        res.append("2. **核心架构与模块落地**：按规划编写并验证新增与修改的代码模块。")
        res.append("3. **综合测试与回归验证**：运行测试脚本，确保全流程零报错运行。")

    res.append(f"\n> **提示**：完整的技术落地文档（包含详细架构图、文件改动矩阵、关键代码设计与测试用例）已写入并在中间主屏幕 **`方案: {plan_file_name}`** 中展示。您可以直接在中间窗口进行审阅或编辑，确认无误后点击下方 **【批准并执行 (Process)】** 即可开始自动化代码落地。")
    return "\n\n".join(res)


class PlanPreviewArea(QScrollArea):
    """
    技术落地实施方案现代极客预览视图 (GitHub / Notion 级包装 + 1:1 像素级复刻办公模式 CodeBlockCard):
    - 结构化排版、分阶段执行路线图胶囊、NEW/MODIFY/DELETE 变动徽章
    - 代码块直接采用办公模式 CodeBlockCard 控件：极客深色卡片、语言指示、Pygments One-Dark 丰富语法高亮、原生复制按钮（绿色对勾反馈）
    - 彻底解决代码块点击复制失效、格式错乱及无语法高亮问题
    """
    def __init__(self, is_dark: bool = True, dev_view=None, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.dev_view = dev_view
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self._apply_style()

        self.container = QWidget()
        bg_col = "#0d1117" if self.is_dark else "#ffffff"
        self.container.setStyleSheet(f"background-color: {bg_col};")
        self.lay = QVBoxLayout(self.container)
        self.lay.setContentsMargins(24, 18, 24, 36)
        self.lay.setSpacing(14)
        self.setWidget(self.container)
        self._content_widgets = []
        self._raw_markdown = ""

    def _apply_style(self):
        bg = "#0d1117" if self.is_dark else "#ffffff"
        handle_bg = "#30363d" if self.is_dark else "#d0d7de"
        handle_hover = "#8b949e" if self.is_dark else "#57606a"
        self.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {bg};
            }}
            QScrollBar:vertical {{
                width: 8px;
                background: transparent;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {handle_bg};
                border-radius: 4px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {handle_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

    def set_dark(self, is_dark: bool):
        self.is_dark = is_dark
        self._apply_style()
        bg_col = "#0d1117" if self.is_dark else "#ffffff"
        self.container.setStyleSheet(f"background-color: {bg_col};")
        for w in self._content_widgets:
            if hasattr(w, 'set_dark'):
                w.set_dark(is_dark)
        if self._raw_markdown:
            self.set_content(self._raw_markdown)

    def set_content(self, plan_markdown: str):
        self._raw_markdown = plan_markdown or ""
        while self.lay.count() > 0:
            item = self.lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._content_widgets.clear()

        clean_md = strip_emojis(sanitize_tool_json_artifacts(self._raw_markdown))
        if not clean_md.strip():
            lbl = QLabel("<p style='color:#8b949e; font-style:italic;'>（暂无方案详细内容）</p>")
            self.lay.addWidget(lbl)
            self.lay.addStretch()
            return

        from ui.chat_window import CodeBlockCard

        pattern = re.compile(r'^[ \t]*```([a-zA-Z0-9_\+#\.\-]*)[ \t]*\r?\n([\s\S]*?)^[ \t]*```[ \t]*(?:\r?\n|$)', re.MULTILINE)
        last = 0
        for m in pattern.finditer(clean_md):
            if m.start() > last:
                t = clean_md[last:m.start()].strip()
                if t:
                    self._add_text_widget(t)
            raw_lang = (m.group(1) or "").strip().lower()
            code_body = m.group(2).rstrip('\r\n')
            card = CodeBlockCard(lang=raw_lang, code=code_body, is_dark=self.is_dark, parent=self.container)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.lay.addWidget(card)
            self._content_widgets.append(card)
            last = m.end()

        if last < len(clean_md):
            tail = clean_md[last:].strip()
            if tail:
                self._add_text_widget(tail)

        self.lay.addStretch()

    def _add_text_widget(self, raw_text: str):
        clean_t = re.sub(
            r'`?\[NEW\]`?\s*`?([a-zA-Z0-9_\-/\.\\\(\)]+)`?',
            r'<span style="background-color:rgba(46,160,67,0.25); color:#3fb950; border:1px solid rgba(46,160,67,0.4); padding:1px 6px; border-radius:4px; font-size:11px; font-weight:bold;">NEW</span> <code style="color:#79c0ff; font-weight:600;">\1</code>',
            raw_text
        )
        clean_t = re.sub(
            r'`?\[MODIFY\]`?\s*`?([a-zA-Z0-9_\-/\.\\\(\)]+)`?',
            r'<span style="background-color:rgba(210,153,34,0.25); color:#d29922; border:1px solid rgba(210,153,34,0.4); padding:1px 6px; border-radius:4px; font-size:11px; font-weight:bold;">MODIFY</span> <code style="color:#e3b341; font-weight:600;">\1</code>',
            clean_t
        )
        clean_t = re.sub(
            r'`?\[DELETE\]`?\s*`?([a-zA-Z0-9_\-/\.\\\(\)]+)`?',
            r'<span style="background-color:rgba(248,81,73,0.25); color:#f85149; border:1px solid rgba(248,81,73,0.4); padding:1px 6px; border-radius:4px; font-size:11px; font-weight:bold;">DELETE</span> <code style="color:#ff7b72; font-weight:600;">\1</code>',
            clean_t
        )
        clean_t = re.sub(
            r'(?m)^###?\s*(Stage\s*\d+[^:\n]*:?[^\n]*)',
            r'<div style="background-color:rgba(56,139,253,0.12); border-left:3px solid #388bfd; padding:6px 12px; border-radius:0 6px 6px 0; margin:12px 0 6px 0; color:#79c0ff; font-weight:bold; font-size:13.5px;">\1</div>',
            clean_t
        )
        clean_t = clean_markdown_tables(clean_t)

        try:
            import markdown
            body_html = markdown.markdown(clean_t, extensions=['tables'])
        except Exception:
            body_html = html.escape(clean_t).replace('\n', '<br>')

        d = self.is_dark
        text_fg = "#c9d1d9" if d else "#1f2328"
        h1_col = "#58a6ff" if d else "#0969da"
        h2_col = "#79c0ff" if d else "#0969da"
        h2_bg = "rgba(33,38,45,0.9)" if d else "#f6f8fa"
        h2_border = "#30363d" if d else "#d0d7de"
        h3_col = "#d2a8ff" if d else "#8250df"
        table_border = "#30363d" if d else "#d0d7de"
        th_bg = "#21262d" if d else "#f6f8fa"
        th_fg = "#f0f6fc" if d else "#1f2328"
        code_bg = "rgba(110,118,129,0.2)" if d else "#eff1f3"
        code_fg = "#79c0ff" if d else "#0550ae"

        styled_html = f"""
        <div style="color: {text_fg}; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei UI', sans-serif; font-size: 13px; line-height: 1.65;">
        <style>
            h1 {{ color: {h1_col}; font-size: 18px; border-bottom: 2px solid {table_border}; padding-bottom: 8px; margin: 8px 0 14px 0; }}
            h2 {{ color: {h2_col}; font-size: 14.5px; background: {h2_bg}; border: 1px solid {h2_border}; border-left: 4px solid {h1_col}; padding: 7px 12px; border-radius: 6px; margin: 16px 0 10px 0; }}
            h3 {{ color: {h3_col}; font-size: 13.5px; border-left: 3px solid {h3_col}; padding-left: 8px; margin: 12px 0 6px 0; }}
            p {{ color: {text_fg}; margin: 4px 0 8px 0; }}
            ul, ol {{ margin: 4px 0 8px 0; padding-left: 20px; }}
            li {{ color: {text_fg}; margin: 3px 0; }}
            table {{ border-collapse: collapse; width: 100%; margin: 10px 0; border: 1px solid {table_border}; border-radius: 6px; }}
            th {{ background-color: {th_bg}; color: {th_fg}; padding: 8px 12px; border: 1px solid {table_border}; font-weight: bold; text-align: left; }}
            td {{ padding: 7px 12px; border: 1px solid {table_border}; color: {text_fg}; }}
            code {{ background-color: {code_bg}; color: {code_fg}; padding: 2px 6px; border-radius: 4px; font-family: Consolas, monospace; font-size: 12px; }}
            blockquote {{ border-left: 3px solid #388bfd; margin: 8px 0; padding: 6px 12px; background: rgba(56,139,253,0.08); color: #8b949e; border-radius: 0 4px 4px 0; }}
        </style>
        {body_html}
        </div>
        """

        lbl = QLabel(self.container)
        lbl.setTextFormat(Qt.RichText)
        lbl.setWordWrap(True)
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        lbl.setOpenExternalLinks(True)
        lbl.setStyleSheet("background: transparent; border: none;")
        lbl.setText(styled_html)
        self.lay.addWidget(lbl)
        self._content_widgets.append(lbl)


class PlanDocumentViewerWidget(QWidget):
    """
    主屏幕技术落地实施方案全能视图 (Plan Document Studio):
    - 预览模式 (Preview Mode): GitHub/Notion 级精美富文本包装，阶段胶囊、变动徽章与 1:1 办公模式 CodeBlockCard 高亮代码块
    - 直接编辑模式 (In-Place Edit Mode): 内置 Markdown 源码编辑器，可直接修改方案并保存更新
    - 导出与分享: [📥 导出] [📋 复制]
    - 批准分步执行: [Process]
    """
    def __init__(self, plan_content: str, plan_file_path: Optional[str] = None, dev_view=None, parent=None):
        super().__init__(parent)
        self.plan_content = sanitize_tool_json_artifacts(strip_emojis(plan_content))
        self.plan_file_path = plan_file_path
        self.dev_view = dev_view

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 1. 顶部操作工具条
        self.top_bar = QWidget()
        self.top_bar.setFixedHeight(40)
        self.top_bar.setStyleSheet("background-color: #21252b; border-bottom: 1px solid #181a1f; padding: 0 10px;")
        t_lay = QHBoxLayout(self.top_bar)
        t_lay.setContentsMargins(12, 0, 12, 0)
        t_lay.setSpacing(8)

        title_name = Path(plan_file_path).name if plan_file_path else "implementation_plan.md"
        self.title_lbl = QLabel(f"📋 <b>技术落地实施方案</b> <span style='color:#8b949e; font-size:11.5px;'>({title_name})</span>")
        self.title_lbl.setStyleSheet("color: #dcdfe4; font-size: 13px; font-family: 'Segoe UI', 'Microsoft YaHei UI';")
        t_lay.addWidget(self.title_lbl)

        self.status_tag = QLabel("待用户批准 (Pending Approval)")
        self.status_tag.setStyleSheet("background-color: rgba(56, 139, 253, 0.15); color: #58a6ff; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;")
        t_lay.addWidget(self.status_tag)

        t_lay.addStretch()

        # 模式切换按钮：[✏️ 编辑方案] / [👁️ 预览方案]
        self.btn_toggle_mode = QPushButton("✏️ 编辑方案")
        self.btn_toggle_mode.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_mode.setStyleSheet("""
            QPushButton {
                background-color: #2b313a; color: #abb2bf; border: 1px solid #3c424d;
                border-radius: 4px; padding: 3px 10px; font-size: 11.5px;
            }
            QPushButton:hover { background-color: #353b45; color: #ffffff; }
        """)
        self.btn_toggle_mode.clicked.connect(self._toggle_edit_mode)
        t_lay.addWidget(self.btn_toggle_mode)

        # 保存按钮
        self.btn_save = QPushButton("💾 保存")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #2b313a; color: #abb2bf; border: 1px solid #3c424d;
                border-radius: 4px; padding: 3px 10px; font-size: 11.5px;
            }
            QPushButton:hover { background-color: #353b45; color: #58a6ff; }
        """)
        self.btn_save.clicked.connect(self._save_plan)
        t_lay.addWidget(self.btn_save)

        # 导出按钮
        self.btn_export = QPushButton("📥 导出")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setToolTip("选择本地目录导出并保存为 Markdown 文件")
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #2b313a; color: #abb2bf; border: 1px solid #3c424d;
                border-radius: 4px; padding: 3px 10px; font-size: 11.5px;
            }
            QPushButton:hover { background-color: #353b45; color: #ffffff; }
        """)
        self.btn_export.clicked.connect(self._do_export)
        t_lay.addWidget(self.btn_export)

        # 复制全文按钮
        self.btn_copy = QPushButton("📋 复制")
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.setToolTip("复制方案 Markdown 纯文本到剪贴板")
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #2b313a; color: #abb2bf; border: 1px solid #3c424d;
                border-radius: 4px; padding: 3px 10px; font-size: 11.5px;
            }
            QPushButton:hover { background-color: #353b45; color: #ffffff; }
        """)
        self.btn_copy.clicked.connect(self._do_copy)
        t_lay.addWidget(self.btn_copy)

        # 在独立代码编辑器打开
        self.btn_open_tab = QPushButton("在新标签页编辑")
        self.btn_open_tab.setCursor(Qt.PointingHandCursor)
        self.btn_open_tab.setStyleSheet("""
            QPushButton {
                background-color: #2b313a; color: #abb2bf; border: 1px solid #3c424d;
                border-radius: 4px; padding: 3px 10px; font-size: 11.5px;
            }
            QPushButton:hover { background-color: #353b45; color: #ffffff; }
        """)
        self.btn_open_tab.clicked.connect(self._open_in_code_editor)
        t_lay.addWidget(self.btn_open_tab)

        # 批准并立即分步执行按钮 (Process)
        self.btn_proceed = QPushButton("Process")
        self.btn_proceed.setCursor(Qt.PointingHandCursor)
        self.btn_proceed.setToolTip("批准并分步执行技术方案 (Process)")
        self.btn_proceed.setStyleSheet("""
            QPushButton {
                background-color: #238636; color: white; border: 1px solid #2ea043;
                border-radius: 4px; padding: 4px 16px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2ea043; border-color: #3fb950; }
        """)
        self.btn_proceed.clicked.connect(self._on_proceed)
        t_lay.addWidget(self.btn_proceed)

        lay.addWidget(self.top_bar)

        # 2. 方案多态工作容器 (QStackedWidget)
        self.stack = QStackedWidget()

        # Page 0: 现代极客富文本渲染视图 (嵌入真实 1:1 CodeBlockCard 控件)
        is_dark = getattr(self.dev_view, 'is_dark', True)
        self.preview_area = PlanPreviewArea(is_dark=is_dark, dev_view=self.dev_view, parent=self)
        self.browser = self.preview_area  # 保持属性兼容
        self.preview_area.set_content(self.plan_content)
        self.stack.addWidget(self.preview_area)

        # Page 1: 内嵌源码直接编辑视图
        self.editor_page = QWidget()
        e_lay = QVBoxLayout(self.editor_page)
        e_lay.setContentsMargins(0, 0, 0, 0)
        e_lay.setSpacing(0)

        self.plan_edit = QTextEdit()
        self.plan_edit.setPlainText(self.plan_content)
        self.plan_edit.setStyleSheet("""
            QTextEdit {
                background-color: #161b22;
                color: #e6edf3;
                border: none;
                padding: 16px 20px;
                font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.5;
            }
        """)
        e_lay.addWidget(self.plan_edit, 1)

        # 编辑页底栏
        edit_bar = QWidget()
        edit_bar.setFixedHeight(36)
        edit_bar.setStyleSheet("background-color: #161b22; border-top: 1px solid #30363d; padding: 0 12px;")
        eb_lay = QHBoxLayout(edit_bar)
        eb_lay.setContentsMargins(12, 0, 12, 0)
        eb_lay.setSpacing(10)

        tip_lbl = QLabel("💡 提示：您可在此直接增删和修改方案；完成后点击右侧「保存并切回预览」，系统将自动落盘并更新。")
        tip_lbl.setStyleSheet("color: #8b949e; font-size: 11.5px; font-family: 'Microsoft YaHei UI';")
        eb_lay.addWidget(tip_lbl)
        eb_lay.addStretch()

        btn_save_preview = QPushButton("💾 保存并切回预览")
        btn_save_preview.setCursor(Qt.PointingHandCursor)
        btn_save_preview.setStyleSheet("""
            QPushButton {
                background-color: #238636; color: #ffffff; border: none;
                border-radius: 4px; padding: 3px 12px; font-size: 11.5px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)
        btn_save_preview.clicked.connect(self._save_and_switch_to_preview)
        eb_lay.addWidget(btn_save_preview)

        e_lay.addWidget(edit_bar)
        self.stack.addWidget(self.editor_page)

        lay.addWidget(self.stack, 1)

    def set_plan_content(self, plan_content: str, plan_file_path: Optional[str] = None):
        self.plan_content = sanitize_tool_json_artifacts(strip_emojis(plan_content))
        if plan_file_path:
            self.plan_file_path = plan_file_path
            title_name = Path(plan_file_path).name
            self.title_lbl.setText(f"📋 <b>技术落地实施方案</b> <span style='color:#8b949e; font-size:11.5px;'>({title_name})</span>")
        self.preview_area.set_content(self.plan_content)
        self.plan_edit.setPlainText(self.plan_content)

    def _toggle_edit_mode(self):
        if self.stack.currentIndex() == 0:
            self.plan_edit.setPlainText(self.plan_content)
            self.stack.setCurrentIndex(1)
            self.btn_toggle_mode.setText("👁️ 预览方案")
            self.plan_edit.setFocus()
        else:
            self._save_and_switch_to_preview()

    def _save_plan(self):
        if self.stack.currentIndex() == 1:
            self.plan_content = self.plan_edit.toPlainText().strip()
        if self.plan_file_path:
            try:
                Path(self.plan_file_path).write_text(self.plan_content, encoding="utf-8")
            except Exception as e:
                print(f"[PlanDocumentViewer] 保存失败: {e}")
        self.preview_area.set_content(self.plan_content)
        self.btn_save.setText("✅ 已保存")
        QTimer.singleShot(1500, lambda: self.btn_save.setText("💾 保存"))

    def _save_and_switch_to_preview(self):
        self._save_plan()
        self.stack.setCurrentIndex(0)
        self.btn_toggle_mode.setText("✏️ 编辑方案")

    def _do_export(self):
        default_name = Path(self.plan_file_path).name if self.plan_file_path else "implementation_plan.md"
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出技术落地实施方案 Markdown 文档",
            default_name,
            "Markdown 文档 (*.md);;所有文件 (*.*)"
        )
        if out_path:
            try:
                Path(out_path).write_text(self.plan_content, encoding="utf-8")
                self.btn_export.setText("✅ 已导出")
                QTimer.singleShot(1800, lambda: self.btn_export.setText("📥 导出"))
                if self.dev_view and hasattr(self.dev_view, 'terminal_output'):
                    self.dev_view.terminal_output.append(f"<span style='color:#98c379'>✅ 已成功导出实施方案至: <code>{out_path}</code></span>")
            except Exception as e:
                if self.dev_view and hasattr(self.dev_view, 'terminal_output'):
                    self.dev_view.terminal_output.append(f"<span style='color:#e06c75'>❌ 导出实施方案失败: {e}</span>")

    def _do_copy(self):
        txt = self.plan_content.strip()
        if txt:
            QApplication.clipboard().setText(txt)
            self.btn_copy.setText("✅ 已复制")
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("📋 复制"))

    def _open_in_code_editor(self):
        if self.dev_view and hasattr(self.dev_view, 'open_file_in_editor') and self.plan_file_path:
            self._save_plan()
            self.dev_view.open_file_in_editor(self.plan_file_path)

    def _on_proceed(self):
        self._save_plan()
        self.status_tag.setText("已批准分步执行")
        self.status_tag.setStyleSheet("background-color: rgba(46, 160, 67, 0.2); color: #3fb950; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;")
        self.btn_proceed.setEnabled(False)
        self.btn_proceed.setText("✅ Processed")
        if self.dev_view and hasattr(self.dev_view, '_execute_plan_proceed'):
            self.dev_view._execute_plan_proceed()



class DiffViewerWidget(QWidget):
    """主屏幕现代极客风格代码差异比对视图 (Diff Viewer) - 智能折叠未修改代码并平滑跳转变动行"""
    def __init__(self, rec, file_path: str, dev_view, parent=None):
        super().__init__(parent)
        self.rec = rec
        self.file_path = file_path
        self.dev_view = dev_view
        self.first_diff_lineno = 1

        # 若 rec 为空，尝试从 FileDiffTracker 或磁盘获取/补齐记录
        if not self.rec:
            p = Path(file_path)
            from core.file_diff_tracker import FileDiffTracker
            tracker = FileDiffTracker.get_instance()
            self.rec = tracker.get_record(str(p.resolve()))
            if not self.rec:
                for r in tracker.get_recent_records(50):
                    if r.rel_path == file_path or Path(r.abs_path).resolve() == p.resolve() or Path(r.rel_path).name == p.name:
                        self.rec = r
                        self.file_path = r.abs_path
                        break
            if not self.rec and p.exists():
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                    self.rec = tracker.record_change(
                        rel_path=p.name,
                        abs_path=str(p.resolve()),
                        before_content="",
                        after_content=content
                    )
                except Exception:
                    pass

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 顶栏工具条
        self.top_bar = QWidget()
        self.top_bar.setFixedHeight(36)
        self.top_bar.setStyleSheet("background-color: #21252b; border-bottom: 1px solid #181a1f; padding: 0 10px;")
        t_lay = QHBoxLayout(self.top_bar)
        t_lay.setContentsMargins(10, 0, 10, 0)
        t_lay.setSpacing(10)

        rel_name = self.rec.rel_path if self.rec else Path(file_path).name
        parent_dir = str(Path(self.rec.abs_path if self.rec else file_path).parent).replace("\\", "/")
        if parent_dir == ".":
            parent_dir = ""
        added = self.rec.added_lines if self.rec else 0
        removed = self.rec.removed_lines if self.rec else 0

        dir_span = f" <span style='color:#8b949e; font-size:11.5px; margin-left:6px;'>{parent_dir}</span>" if parent_dir else ""
        self.lbl = QLabel(f"<b>{rel_name}</b>{dir_span}")
        self.lbl.setStyleSheet("color: #dcdfe4; font-size: 12.5px; font-family: 'Segoe UI', 'Microsoft YaHei UI';")
        t_lay.addWidget(self.lbl)

        self.diff_counts = QLabel(f"<span style='color:#3fb950; font-weight:bold;'>+{added}</span> <span style='color:#f85149; font-weight:bold;'>-{removed}</span>")
        self.diff_counts.setStyleSheet("font-size: 11.5px; font-family: 'Cascadia Code', Consolas; margin-left:8px;")
        t_lay.addWidget(self.diff_counts)
        t_lay.addStretch()

        self.btn_accept = QPushButton("确认接纳此文件")
        self.btn_accept.setCursor(Qt.PointingHandCursor)
        self.btn_accept.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32; color: white; border: none;
                border-radius: 4px; padding: 3px 10px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background-color: #388e3c; }
        """)
        self.btn_accept.clicked.connect(self._accept_this)
        t_lay.addWidget(self.btn_accept)

        self.btn_revert = QPushButton("↩️ 还原撤销此文件")
        self.btn_revert.setCursor(Qt.PointingHandCursor)
        self.btn_revert.setStyleSheet("""
            QPushButton {
                background-color: #c62828; color: white; border: none;
                border-radius: 4px; padding: 3px 10px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        self.btn_revert.clicked.connect(self._revert_this)
        t_lay.addWidget(self.btn_revert)

        lay.addWidget(self.top_bar)

        # 内容区 (QTextBrowser 渲染带行号的红绿高亮 HTML Diff)
        self.browser = QTextBrowser()
        is_dark = getattr(self.dev_view, 'is_dark', True)
        self.apply_theme(is_dark)
        lay.addWidget(self.browser, 1)

    def apply_theme(self, is_dark: bool):
        d = is_dark
        top_bg = "#21252b" if d else "#f8f8f8"
        border_b = "#181a1f" if d else "#e5e5e5"
        self.top_bar.setStyleSheet(f"background-color: {top_bg}; border-bottom: 1px solid {border_b}; padding: 0 10px;")
        lbl_fg = "#dcdfe4" if d else "#1f2328"
        self.lbl.setStyleSheet(f"color: {lbl_fg}; font-size: 12.5px; font-family: 'Segoe UI', 'Microsoft YaHei UI';")
        browser_bg = "#1e1e1e" if d else "#ffffff"
        browser_fg = "#d4d4d4" if d else "#24292e"
        self.browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {browser_bg};
                color: {browser_fg};
                border: none;
                font-family: 'Cascadia Code', Consolas, 'Courier New', monospace;
                font-size: 12px;
                padding: 6px;
            }}
        """)
        # 关键：PlanDocumentViewerWidget 整体没设 setStyleSheet，会保持默认 system 白底——
        # dark 主题下也白。两套独立：dark 用 #1e1e1e，light 用 #ffffff。
        widget_bg = "#1e1e1e" if d else "#ffffff"
        try:
            self.setStyleSheet(f"QWidget {{ background-color: {widget_bg}; }}")
        except Exception:
            pass
        self._render_diff()

    def _append_same_line(self, lines_html: list, b: dict):
        d = getattr(self.dev_view, 'is_dark', True)
        old_no = str(b.get("old_no") or "")
        new_no = str(b.get("new_no") or "")
        raw_text = html.escape(b.get("text", ""))
        fg = "#abb2bf" if d else "#24292e"
        num_fg = "#5c6370" if d else "#9ca3af"
        lines_html.append(
            f"<div style='color:{fg}; padding:2px 4px; white-space:pre; border-left:3px solid transparent;'>"
            f"<span style='color:{num_fg}; display:inline-block; width:36px; text-align:right; margin-right:8px; user-select:none;'>{old_no}</span>"
            f"<span style='color:{num_fg}; display:inline-block; width:36px; text-align:right; margin-right:12px; user-select:none;'>{new_no}</span>"
            f"<span style='color:{num_fg}; margin-right:6px;'> </span>{raw_text}</div>"
        )

    def _render_diff(self):
        if not self.rec:
            p = Path(self.file_path)
            if p.exists():
                try:
                    from core.file_diff_tracker import FileDiffTracker
                    tracker = FileDiffTracker.get_instance()
                    content = p.read_text(encoding="utf-8", errors="replace")
                    self.rec = tracker.record_change(
                        rel_path=p.name,
                        abs_path=str(p.resolve()),
                        before_content="",
                        after_content=content
                    )
                except Exception:
                    pass

        if not self.rec:
            self.browser.setHtml("<div style='color:#858585; padding:20px;'>⚠️ 未找到该文件的修改历史记录，当前已是最新的落盘文件。</div>")
            return

        if hasattr(self, 'diff_counts') and self.rec:
            added = self.rec.added_lines
            removed = self.rec.removed_lines
            self.diff_counts.setText(f"<span style='color:#3fb950; font-weight:bold;'>+{added}</span> <span style='color:#f85149; font-weight:bold;'>-{removed}</span>")

        d = getattr(self.dev_view, 'is_dark', True)
        blocks = self.rec.get_diff_blocks()
        lines_html = []
        lines_html.append("<div style='font-family:Consolas,\"Cascadia Code\",monospace; font-size:12px; line-height:1.45;'>")

        first_diff_anchor = False
        self.first_diff_lineno = 1

        i = 0
        n = len(blocks)
        while i < n:
            b = blocks[i]
            t = b.get("type", "same")

            if t == "same":
                j = i
                while j < n and blocks[j].get("type") == "same":
                    j += 1
                same_count = j - i
                if same_count > 8:
                    for k in range(i, i + 3):
                        self._append_same_line(lines_html, blocks[k])
                    folded = same_count - 6
                    fold_bg = "#16191f" if d else "#f6f8fa"
                    fold_fg_c = "#8b949e" if d else "#57606a"
                    fold_border = "#282c34" if d else "#d0d7de"
                    lines_html.append(
                        f"<div style='background-color:{fold_bg}; color:{fold_fg_c}; text-align:center; padding:6px 0; margin:4px 0; "
                        f"font-size:11px; border-top:1px solid {fold_border}; border-bottom:1px solid {fold_border}; font-family:Consolas,monospace; user-select:none;'>"
                        f"↕ +{folded} more lines</div>"
                    )
                    for k in range(j - 3, j):
                        self._append_same_line(lines_html, blocks[k])
                else:
                    for k in range(i, j):
                        self._append_same_line(lines_html, blocks[k])
                i = j
            else:
                old_no = str(b.get("old_no") or "")
                new_no = str(b.get("new_no") or "")
                raw_text = html.escape(b.get("text", ""))
                anchor_tag = ""
                if not first_diff_anchor:
                    first_diff_anchor = True
                    anchor_tag = "<a name='target_first_diff' id='target_first_diff'></a>"
                    try:
                        self.first_diff_lineno = int(b.get("new_no") or b.get("old_no") or 1)
                    except Exception:
                        self.first_diff_lineno = 1
                if t == "add":
                    add_bg = "#1c3823" if d else "#e6ffec"
                    add_fg = "#7ee787" if d else "#1a7f37"
                    add_border = "#3fb950" if d else "#2da44e"
                    lines_html.append(
                        f"<div style='background-color:{add_bg}; color:{add_fg}; padding:2px 4px; white-space:pre; border-left:3px solid {add_border};'>"
                        f"{anchor_tag}"
                        f"<span style='color:{add_border}; display:inline-block; width:36px; text-align:right; margin-right:8px; user-select:none;'></span>"
                        f"<span style='color:{add_border}; display:inline-block; width:36px; text-align:right; margin-right:12px; user-select:none;'>{new_no}</span>"
                        f"<span style='color:{add_border}; font-weight:bold; margin-right:6px;'>+</span>{raw_text}</div>"
                    )
                elif t == "del":
                    del_bg = "#3b1d22" if d else "#ffebe9"
                    del_fg = "#ff7b72" if d else "#cf222e"
                    del_border = "#f85149" if d else "#cf222e"
                    lines_html.append(
                        f"<div style='background-color:{del_bg}; color:{del_fg}; padding:2px 4px; white-space:pre; border-left:3px solid {del_border};'>"
                        f"{anchor_tag}"
                        f"<span style='color:{del_border}; display:inline-block; width:36px; text-align:right; margin-right:8px; user-select:none;'>{old_no}</span>"
                        f"<span style='color:{del_border}; display:inline-block; width:36px; text-align:right; margin-right:12px; user-select:none;'></span>"
                        f"<span style='color:{del_border}; font-weight:bold; margin-right:6px;'>-</span>{raw_text}</div>"
                    )
                i += 1

        lines_html.append("</div>")
        self.browser.setHtml("".join(lines_html))

        if first_diff_anchor:
            QTimer.singleShot(40, lambda: self.browser.scrollToAnchor("target_first_diff"))
            QTimer.singleShot(120, lambda: self.browser.scrollToAnchor("target_first_diff"))
            QTimer.singleShot(250, lambda: self.browser.scrollToAnchor("target_first_diff"))


    def _accept_this(self):
        target_p = self.rec.abs_path if (self.rec and self.rec.abs_path) else str(Path(self.file_path).resolve())
        self.dev_view._on_single_accept(target_p)
        self.btn_accept.setText("✅ 已确认接纳")
        self.btn_accept.setStyleSheet("""
            QPushButton {
                background-color: #1e3a24; color: #7ee787; border: 1px solid #2e7d32;
                border-radius: 4px; padding: 3px 10px; font-size: 11px; font-weight: bold;
            }
        """)
        self.btn_revert.setText("↩️ 撤销接纳")
        self.btn_revert.setEnabled(True)

    def _revert_this(self):
        target_p = self.rec.abs_path if (self.rec and self.rec.abs_path) else str(Path(self.file_path).resolve())
        self.dev_view._on_single_reject(target_p)
        self.btn_revert.setText("↩️ 已还原撤销")
        self.btn_revert.setStyleSheet("""
            QPushButton {
                background-color: #3f1e24; color: #ff7b72; border: 1px solid #c62828;
                border-radius: 4px; padding: 3px 10px; font-size: 11px; font-weight: bold;
            }
        """)
        self.btn_accept.setText("重新接纳")
        self.btn_accept.setEnabled(True)


class AgentTrajectoryWidget(QFrame):
    """
    Antigravity IDE 风格的一体化 AI 交互问答轮次组件 (Unified Turn Card)
    """
    accept_changes_signal = pyqtSignal(str)
    reject_changes_signal = pyqtSignal(str)
    open_file_signal = pyqtSignal(str)
    open_diff_signal = pyqtSignal(str)
    single_accept_signal = pyqtSignal(str)
    single_reject_signal = pyqtSignal(str)

    @property
    def stats_lbl(self):
        return self.capsule_stat_btn

    @property
    def item_widgets(self):
        return {r[0]: r for r in self.file_records}

    def __init__(self, parent=None, is_dark=True):
        super().__init__(parent)
        self.is_dark = is_dark
        self.is_expanded = True
        self.file_changes = []  # rel_path list
        self.file_records = []  # [(rel_p, abs_p, action, added, removed)]
        self.current_state = "pending"
        self.drawer_expanded = False
        self.explored_files = 0
        self.explored_searches = 0
        self._cached_summary = ""  # apply_theme 时用来强制重渲 summary_browser

        self.setObjectName("AgentTrajectoryWidget")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        # 注意：此 setStyleSheet 仅第一次构造时设置；后续主题切换由 apply_theme() 重写。
        self.apply_theme(is_dark)

        self.layout = QVBoxLayout(self)
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)
        self.layout.setContentsMargins(10, 8, 10, 8)
        self.layout.setSpacing(6)

        # 1. 顶部 Header
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(24)
        self.header_widget.setCursor(Qt.PointingHandCursor)
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(4)

        self.thought_lbl = QLabel("Thinking...")
        self.thought_lbl.setStyleSheet("color: #8b949e; font-size: 11.5px; font-weight: 500; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;")
        self.header_layout.addWidget(self.thought_lbl)

        self.header_layout.addStretch()

        self.toggle_btn = QPushButton("▴")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #8b949e; border: none; font-size: 11px;
            }
            QPushButton:hover { color: #c9d1d9; }
        """)
        self.toggle_btn.clicked.connect(self._toggle_expand)
        self.header_layout.addWidget(self.toggle_btn)

        self.header_widget.mousePressEvent = lambda e: self._toggle_expand()
        self.layout.addWidget(self.header_widget)

        self._start_time = time.time()
        self._is_done = False
        self._log_count = 0
        self._processing_files = {}

        # 2. 详细执行过程容器 (对齐用户需求：展开可查看当前执行状态、执行日志、思考过程、处理中的文件)
        self.details_container = QWidget()
        self.details_layout = QVBoxLayout(self.details_container)
        self.details_layout.setContentsMargins(4, 4, 4, 4)
        self.details_layout.setSpacing(6)

        # 2.1 动态执行状态条 (当前模型正在执行什么 + 实时计时)
        self.status_bar_widget = QFrame()
        self.status_bar_widget.setStyleSheet("""
            QFrame {
                background-color: #1a1e24;
                border: 1px solid #282d37;
                border-radius: 6px;
            }
        """)
        sb_lay = QHBoxLayout(self.status_bar_widget)
        sb_lay.setContentsMargins(8, 6, 8, 6)
        sb_lay.setSpacing(8)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #58a6ff; font-size: 11px;")
        sb_lay.addWidget(self.status_dot)

        self.working_lbl = QLabel("正在分析用户需求并规划执行方案...")
        self.working_lbl.setStyleSheet("""
            color: #e6edf3; font-size: 11.5px; font-weight: 500;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
        """)
        sb_lay.addWidget(self.working_lbl, 1)

        self.timer_lbl = QLabel("(已耗时 0.0s)")
        self.timer_lbl.setStyleSheet("color: #8b949e; font-size: 10.5px; font-family: 'Cascadia Code', Consolas;")
        sb_lay.addWidget(self.timer_lbl)

        self.details_layout.addWidget(self.status_bar_widget)

        # 2.2 正在处理的文件面板 (实时展示正在读取、探索、修改或落盘的文件，仅在发生文件交互时显示)
        self.files_section = QFrame()
        self.files_section.setStyleSheet("""
            QFrame {
                background-color: #181b20;
                border: 1px solid #282d37;
                border-radius: 6px;
            }
        """)
        self.files_section.setVisible(False)
        f_main_lay = QVBoxLayout(self.files_section)
        f_main_lay.setContentsMargins(8, 6, 8, 6)
        f_main_lay.setSpacing(4)

        f_hdr = QHBoxLayout()
        f_hdr_title = QLabel("📄 处理中的文件:")
        f_hdr_title.setStyleSheet("color: #abb2bf; font-size: 11px; font-weight: bold; font-family: 'Segoe UI', 'Microsoft YaHei UI';")
        f_hdr.addWidget(f_hdr_title)

        self.files_count_lbl = QLabel("0 个文件")
        self.files_count_lbl.setStyleSheet("""
            background-color: rgba(56, 139, 253, 0.15); color: #58a6ff;
            border-radius: 8px; padding: 1px 6px; font-size: 10px; font-weight: bold;
        """)
        f_hdr.addWidget(self.files_count_lbl)
        f_hdr.addStretch()
        f_main_lay.addLayout(f_hdr)

        self.files_cards_container = QWidget()
        self.files_cards_layout = QVBoxLayout(self.files_cards_container)
        self.files_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.files_cards_layout.setSpacing(3)
        f_main_lay.addWidget(self.files_cards_container)

        self.details_layout.addWidget(self.files_section)

        # 2.3 思考过程面板 (实时展示大模型的真实思维链推理过程，仅当捕获到真实 <think> 时动态展示)
        self.thought_section = QFrame()
        self.thought_section.setStyleSheet("""
            QFrame {
                background-color: #181b20;
                border: 1px solid #282d37;
                border-radius: 6px;
            }
        """)
        self.thought_section.setVisible(False)
        self._has_real_thought = False
        t_main_lay = QVBoxLayout(self.thought_section)
        t_main_lay.setContentsMargins(8, 6, 8, 6)
        t_main_lay.setSpacing(4)

        t_hdr = QHBoxLayout()
        t_hdr_title = QLabel("💭 思考过程 (Reasoning):")
        t_hdr_title.setStyleSheet("color: #abb2bf; font-size: 11px; font-weight: bold; font-family: 'Segoe UI', 'Microsoft YaHei UI';")
        t_hdr.addWidget(t_hdr_title)

        self.thought_badge = QLabel("思考推理中")
        self.thought_badge.setStyleSheet("""
            background-color: rgba(229, 192, 123, 0.15); color: #e5c07b;
            border-radius: 8px; padding: 1px 6px; font-size: 10px; font-weight: bold;
        """)
        t_hdr.addWidget(self.thought_badge)
        t_hdr.addStretch()
        t_main_lay.addLayout(t_hdr)

        self.thought_browser = QTextBrowser()
        self.thought_browser.setMaximumHeight(130)
        self.thought_browser.setMinimumHeight(60)
        self.thought_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #13161a;
                color: #abb2bf;
                border: 1px solid #21262d;
                border-radius: 4px;
                padding: 6px;
                font-size: 11px;
                font-family: 'Segoe UI', 'Microsoft YaHei UI', -apple-system, sans-serif;
                line-height: 1.5;
            }
        """)
        self.thought_browser.setPlainText("")
        t_main_lay.addWidget(self.thought_browser)

        self.details_layout.addWidget(self.thought_section)

        # 2.4 执行日志面板 (实时时序日志流：工具调用、命令执行、状态码)
        self.log_section = QFrame()
        self.log_section.setStyleSheet("""
            QFrame {
                background-color: #181b20;
                border: 1px solid #282d37;
                border-radius: 6px;
            }
        """)
        l_main_lay = QVBoxLayout(self.log_section)
        l_main_lay.setContentsMargins(8, 6, 8, 6)
        l_main_lay.setSpacing(4)

        l_hdr = QHBoxLayout()
        l_hdr_title = QLabel("📋 执行日志 (Execution Logs):")
        l_hdr_title.setStyleSheet("color: #abb2bf; font-size: 11px; font-weight: bold; font-family: 'Segoe UI', 'Microsoft YaHei UI';")
        l_hdr.addWidget(l_hdr_title)

        self.log_count_lbl = QLabel("0 条记录")
        self.log_count_lbl.setStyleSheet("""
            background-color: rgba(97, 175, 239, 0.15); color: #61afef;
            border-radius: 8px; padding: 1px 6px; font-size: 10px; font-weight: bold;
        """)
        l_hdr.addWidget(self.log_count_lbl)
        l_hdr.addStretch()
        l_main_lay.addLayout(l_hdr)

        self.log_browser = QTextBrowser()
        self.log_browser.setMaximumHeight(110)
        self.log_browser.setMinimumHeight(55)
        self.log_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #111418;
                color: #abb2bf;
                border: 1px solid #21262d;
                border-radius: 4px;
                padding: 4px 6px;
                font-size: 10.5px;
                font-family: 'Cascadia Code', Consolas, monospace;
                line-height: 1.4;
            }
        """)
        l_main_lay.addWidget(self.log_browser)

        self.details_layout.addWidget(self.log_section)

        # 2.5 详细时序步骤条目 (ExploredStepWidget, CommandStepWidget, EditedStepWidget)
        self.timeline_layout = QVBoxLayout()
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_layout.setSpacing(4)
        self.details_layout.addLayout(self.timeline_layout)
        self.timeline_widgets = []

        self.explored_lbl = QLabel("")
        self.explored_lbl.setStyleSheet("color: #8b949e; font-size: 11px; font-family: 'Segoe UI', 'Microsoft YaHei UI';")
        self.explored_lbl.setVisible(False)
        self.details_layout.addWidget(self.explored_lbl)

        self.edited_layout = QVBoxLayout()
        self.commands_layout = QVBoxLayout()

        self._live_timer = QTimer(self)
        self._live_timer.timeout.connect(self._on_live_timer_tick)
        self._live_timer.start(250)

        self.layout.addWidget(self.details_container)

        # 3. 中部：AI 回答总结
        fg_color = "#e6edf3" if self.is_dark else "#1f2328"
        link_color = "#79c0ff" if self.is_dark else "#1d4ed8"
        pre_bg     = "#0c0c0c" if self.is_dark else "#f3f4f6"
        code_bg    = "#21262d" if self.is_dark else "#e2e8f0"
        self.summary_browser = QTextBrowser()
        self.summary_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent;
                color: {fg_color};
                border: none;
                font-size: 12.5px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei UI', Roboto, sans-serif;
                padding: 4px 2px;
            }}
        """)
        # 关键：QTextBrowser 的 Markdown 渲染由 QTextDocument 控制，QSS 的 color 不会
        # 自动渗透到 defaultCharFormat。必须额外 setDefaultStyleSheet 才能让 Markdown 文本
        # 真的用对颜色。
        self.summary_browser.document().setDefaultStyleSheet(f"""
            body {{ color: {fg_color}; font-size: 12.5px;
                   font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                   'Microsoft YaHei UI', Roboto, sans-serif; }}
            a    {{ color: {link_color}; }}
            pre  {{ background: {pre_bg}; color: {fg_color}; }}
            code {{ background: {code_bg}; color: {fg_color}; }}
        """)
        self.summary_browser.setOpenExternalLinks(True)
        self.summary_browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.summary_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.summary_browser.document().setDocumentMargin(4)
        self.summary_browser.setVisible(False)
        self.layout.addWidget(self.summary_browser)

        # 4. 底部：Antigravity IDE 风格审查胶囊条
        self.review_banner = QFrame()
        self.review_banner.setObjectName("ReviewBanner")
        self.review_banner.setStyleSheet("""
            QFrame#ReviewBanner {
                background-color: #1a1d22;
                border: 1px solid #30363d;
                border-radius: 6px;
                margin-top: 4px;
            }
        """)
        self.review_banner.setVisible(False)
        self.review_bar_widget = self.review_banner
        self.rb_main_layout = QVBoxLayout(self.review_banner)
        self.rb_main_layout.setContentsMargins(8, 6, 8, 6)
        self.rb_main_layout.setSpacing(4)

        self.rb_top_row = QHBoxLayout()
        self.rb_top_row.setContentsMargins(0, 0, 0, 0)
        self.rb_top_row.setSpacing(6)

        self.capsule_stat_btn = QPushButton("0 files changed")
        self.capsule_stat_btn.setCursor(Qt.PointingHandCursor)
        self.capsule_stat_btn.setToolTip("点击展开变更文件，并立即在主屏幕打开 Diff 代码比对并定位跳转")
        self.capsule_stat_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #abb2bf; border: none;
                font-size: 11.5px; font-family: 'Segoe UI', 'Microsoft YaHei UI';
                font-weight: 500; text-align: left; padding: 2px 4px;
            }
            QPushButton:hover { color: #61afef; }
        """)
        self.capsule_stat_btn.clicked.connect(self._on_capsule_clicked)
        self.rb_top_row.addWidget(self.capsule_stat_btn)
        self.rb_top_row.addStretch()

        self.review_btn = QPushButton("Review")
        self.review_btn.setCursor(Qt.PointingHandCursor)
        self.review_btn.setToolTip("在中间主屏幕打开 Diff 代码比对并自动跳转定位到修改处")
        self.review_btn.setStyleSheet("""
            QPushButton {
                background-color: #2c313a; color: #abb2bf; border: 1px solid #3e4451;
                border-radius: 4px; padding: 2px 10px; font-size: 11px; font-weight: 500;
            }
            QPushButton:hover { background-color: #3e4451; color: #ffffff; }
        """)
        self.review_btn.clicked.connect(self._on_review_clicked)
        self.rb_top_row.addWidget(self.review_btn)

        self.accept_btn = QPushButton("Accept")
        self.accept_btn.setCursor(Qt.PointingHandCursor)
        self.accept_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e3a24; color: #7ee787; border: 1px solid #2e7d32;
                border-radius: 4px; padding: 2px 10px; font-size: 11px; font-weight: 500;
            }
            QPushButton:hover { background-color: #2e7d32; color: #ffffff; }
        """)
        self.accept_btn.clicked.connect(self._on_accept)
        self.rb_top_row.addWidget(self.accept_btn)

        self.reject_btn = QPushButton("Revert")
        self.reject_btn.setCursor(Qt.PointingHandCursor)
        self.reject_btn.setStyleSheet("""
            QPushButton {
                background-color: #2c313a; color: #f85149; border: 1px solid #482327;
                border-radius: 4px; padding: 2px 10px; font-size: 11px; font-weight: 500;
            }
            QPushButton:hover { background-color: #482327; color: #ff7b72; }
        """)
        self.reject_btn.clicked.connect(self._on_reject)
        self.rb_top_row.addWidget(self.reject_btn)

        self.rb_main_layout.addLayout(self.rb_top_row)

        self.drawer_container = QWidget()
        self.drawer_container.setVisible(False)
        self.drawer_layout = QVBoxLayout(self.drawer_container)
        self.drawer_layout.setContentsMargins(4, 4, 4, 2)
        self.drawer_layout.setSpacing(4)
        self.files_drawer = self.drawer_container
        self.files_drawer_layout = self.drawer_layout
        self.rb_main_layout.addWidget(self.drawer_container)

        self.layout.addWidget(self.review_banner)

    def _on_live_timer_tick(self):
        if not self._is_done and hasattr(self, 'timer_lbl'):
            elapsed = time.time() - self._start_time
            self.timer_lbl.setText(f"(已耗时 {elapsed:.1f}s)")

    def apply_theme(self, is_dark: bool):
        """把 AI 回复卡片 + 卡内已知子 widget 按主题刷样式。
        __init__ 里所有 setStyleSheet 都写死深色（capsule_stat_btn / review_btn /
        accept_btn / reject_btn / timer_lbl / thought_lbl / toggle_btn / 各种 header / drawer /
        FileChangeItem 等），这里对每个已知子 widget 用 is_dark 重写覆盖。
        """
        self.is_dark = is_dark
        d = is_dark

        # 1) 外壳
        bg     = '#21252b' if d else '#f8fafc'
        border = '#333842' if d else '#cbd5e1'
        try:
            self.setStyleSheet(f"""
                QFrame#AgentTrajectoryWidget {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: 8px;
                    margin: 4px 0;
                }}
            """)
        except Exception:
            pass

        # 1.5) 审查胶囊条（review_banner）—— 之前写死 #1a1d22 深色导致 light 主题下整条深色
        rb_bg = '#1a1d22' if d else '#f1f5f9'
        rb_border = '#30363d' if d else '#cbd5e1'
        try:
            if hasattr(self, 'review_banner') and self.review_banner is not None:
                self.review_banner.setStyleSheet(f"""
                    QFrame#ReviewBanner {{
                        background-color: {rb_bg};
                        border: 1px solid {rb_border};
                        border-radius: 6px;
                        margin-top: 4px;
                    }}
                """)
        except Exception:
            pass

        # 2) 思考摘要 / 时间 / 状态 / 等价行（foreground 即可）
        text_secondary = '#8b949e' if d else '#64748b'
        text_primary   = '#e6edf3' if d else '#1f2328'
        text_dim       = '#a1a1aa' if d else '#94a3b8'
        for attr in ('thought_lbl', 'timer_lbl', 'status_lbl',
                     'summary_lbl', 'thought_text'):
            w = getattr(self, attr, None)
            if w is None:
                continue
            try:
                w.setStyleSheet(
                    f"color: {text_secondary}; font-size: 11.5px; font-weight: 500;"
                    f" font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',"
                    f" 'Microsoft YaHei UI', sans-serif; background: transparent; border: none;"
                )
            except Exception:
                pass

        # 3) Capsule 状态按钮 / Review / Accept / Reject 等按钮组
        chip_bg     = '#21262d' if d else '#e2e8f0'
        chip_border = '#30363d' if d else '#cbd5e1'
        chip_fg     = '#c9d1d9' if d else '#1f2328'
        chip_hover  = '#30363d' if d else '#cbd5e1'
        accent      = '#3b82f6' if d else '#3b82f6'

        for attr in ('capsule_stat_btn', 'review_btn'):
            b = getattr(self, attr, None)
            if b is None:
                continue
            try:
                b.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {chip_fg};
                        border: none;
                        font-size: 11.5px;
                        font-family: 'Segoe UI', 'Microsoft YaHei UI';
                        font-weight: 500; text-align: left; padding: 2px 4px;
                    }}
                    QPushButton:hover {{ color: {accent}; }}
                """)
            except Exception:
                pass

        # Accept / Reject 按钮（语义色：绿/红）
        accept_bg     = '#1e3a24' if d else '#dcfce7'
        accept_border = '#2e7d32' if d else '#16a34a'
        accept_fg     = '#7ee787' if d else '#166534'
        accept_hover  = '#2e7d32' if d else '#86efac'
        reject_bg     = '#2c313a' if d else '#fee2e2'
        reject_border = '#482327' if d else '#dc2626'
        reject_fg     = '#f85149' if d else '#991b1b'
        reject_hover  = '#482327' if d else '#fca5a5'

        for attr, sty in (
            ('accept_btn', f"""
                QPushButton {{
                    background-color: {accept_bg};
                    color: {accept_fg};
                    border: 1px solid {accept_border};
                    border-radius: 4px;
                    padding: 2px 10px;
                    font-size: 11px; font-weight: 500;
                }}
                QPushButton:hover {{ background-color: {accept_hover}; color: white; }}
            """),
            ('reject_btn', f"""
                QPushButton {{
                    background-color: {reject_bg};
                    color: {reject_fg};
                    border: 1px solid {reject_border};
                    border-radius: 4px;
                    padding: 2px 10px;
                    font-size: 11px; font-weight: 500;
                }}
                QPushButton:hover {{ background-color: {reject_hover}; color: white; }}
            """),
        ):
            b = getattr(self, attr, None)
            if b is not None:
                try:
                    b.setStyleSheet(sty)
                except Exception:
                    pass

        # 4) toggle 按钮
        toggle = getattr(self, 'toggle_btn', None)
        if toggle is not None:
            try:
                toggle.setStyleSheet(
                    f"background: transparent; color: {text_dim};"
                    f" border: none; font-size: 14px; padding: 0 4px;"
                )
            except Exception:
                pass

        # 5) summary_browser —— 关键：__init__ 里硬编码 fg_color = "#e6edf3" if self.is_dark else "#1f2328"，
        # 切到 dark 后如果 apply_theme 不重写，文字色仍是 #1f2328（深）落在黑底上完全看不见。
        # QTextBrowser 的 Markdown 渲染由 QTextDocument 控制，QSS 的 color 不会自动渗透。
        # 必须额外用 setDefaultStyleSheet 才能让 Markdown 文本真的用对的颜色。
        sb = getattr(self, 'summary_browser', None)
        if sb is not None:
            try:
                sb.setStyleSheet(f"""
                    QTextBrowser {{
                        background-color: transparent;
                        color: {text_primary};
                        border: none;
                        font-size: 12.5px;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei UI', Roboto, sans-serif;
                        padding: 4px 2px;
                    }}
                """)
                # 关键：QTextDocument 的 defaultStyleSheet 决定 Markdown 渲染颜色
                sb.document().setDefaultStyleSheet(f"""
                    body {{ color: {text_primary}; font-size: 12.5px;
                           font-family: -apple-system, BlinkMacSystemFont,
                           'Segoe UI', 'Microsoft YaHei UI', Roboto, sans-serif; }}
                    a    {{ color: {'#3b82f6' if d else '#1d4ed8'}; }}
                    pre  {{ background: {'#0c0c0c' if d else '#f3f4f6'};
                            color: {text_primary}; }}
                    code {{ background: {'#21262d' if d else '#e2e8f0'};
                            color: {text_primary}; }}
                """)
                # setDefaultStyleSheet 不会自动 re-render 已有内容。
                # 用缓存的 markdown 重新 setMarkdown，强制用新的 defaultStyleSheet 重新渲染。
                cached = getattr(self, '_cached_summary', '')
                if cached:
                    try:
                        self.summary_browser.setMarkdown(cached)
                    except Exception:
                        pass
            except Exception:
                pass

        # 6) 兜底：递归把所有 QLabel / QPushButton 染色（针对未在上方列出的子 widget）
        try:
            for w in self.findChildren(QLabel):
                if w is None or w == self:
                    continue
                # 已显式设过的跳过
                if w in (getattr(self, 'thought_lbl', None),
                         getattr(self, 'timer_lbl', None),
                         getattr(self, 'status_lbl', None),
                         getattr(self, 'summary_lbl', None),
                         getattr(self, 'thought_text', None)):
                    continue
                # 仅当 styleSheet 看起来还是深色时才覆盖（避免误伤）
                cur = (w.styleSheet() or '').strip()
                if cur and ('#21' in cur or '#1e' in cur or '#33' in cur or '#0c' in cur):
                    # 只覆盖 color + background，保留 font-size / font-weight / font-family
                    # 避免字体大小/粗细被改回 QLabel 默认值
                    import re as _re
                    keep = ';'.join(
                        ln for ln in cur.split(';')
                        if ln.strip() and not _re.match(r'\s*(color|background)\s*:', ln)
                    )
                    w.setStyleSheet(keep + f"; color: {text_primary}; background: transparent;")
        except Exception:
            pass
        try:
            for w in self.findChildren(QPushButton):
                if w is None or w == self:
                    continue
                # 已显式设过的跳过
                if w in (getattr(self, 'capsule_stat_btn', None),
                         getattr(self, 'review_btn', None),
                         getattr(self, 'accept_btn', None),
                         getattr(self, 'reject_btn', None),
                         getattr(self, 'toggle_btn', None)):
                    continue
                cur = (w.styleSheet() or '').strip()
                if cur and ('#21' in cur or '#1e' in cur or '#33' in cur):
                    w.setStyleSheet(
                        f"QPushButton {{ background: transparent; color: {text_primary};"
                        f" border: 1px solid {chip_border}; border-radius: 4px;"
                        f" padding: 2px 8px; }}"
                    )
        except Exception:
            pass

        # 7) plan_card（如果存在）：刷 card 样式 + info_lbl 文本颜色
        pc = getattr(self, '_plan_card', None)
        if pc is not None:
            try:
                if d:
                    bg_a, bg_b = '#1a202c', '#141822'
                    border_c, border_l, border_l_h = '#30363d', '#388bfd', '#58a6ff'
                    hover_a, hover_b = '#1f2636', '#171c28'
                    info_color, hint_color = '#c9d1d9', '#8b949e'
                    file_color, file_bg, file_border = '#58a6ff', 'rgba(56,139,253,0.12)', 'rgba(56,139,253,0.28)'
                else:
                    bg_a, bg_b = '#eff6ff', '#dbeafe'
                    border_c, border_l, border_l_h = '#bfdbfe', '#3b82f6', '#1d4ed8'
                    hover_a, hover_b = '#dbeafe', '#bfdbfe'
                    info_color, hint_color = '#1f2328', '#64748b'
                    file_color, file_bg, file_border = '#1d4ed8', 'rgba(59,130,246,0.10)', 'rgba(59,130,246,0.30)'
                pc.setStyleSheet(f"""
                    QFrame#planProceedCard {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {bg_a}, stop:1 {bg_b});
                        border: 1px solid {border_c};
                        border-left: 3px solid {border_l};
                        border-radius: 6px;
                        padding: 6px 14px;
                        margin: 6px 0 4px 0;
                    }}
                    QFrame#planProceedCard:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {hover_a}, stop:1 {hover_b});
                        border: 1px solid {border_l};
                        border-left: 3px solid {border_l_h};
                    }}
                """)
            except Exception:
                pass
        # 刷新 info_lbl 的 HTML（用对的颜色）
        pln = getattr(self, '_plan_card_info_lbl', None)
        if pln is not None:
            try:
                fn = getattr(self, '_plan_card_file_name', 'implementation_plan.md')
                if d:
                    info_color, hint_color = '#c9d1d9', '#8b949e'
                    file_color, file_bg, file_border = '#58a6ff', 'rgba(56,139,253,0.12)', 'rgba(56,139,253,0.28)'
                else:
                    info_color, hint_color = '#1f2328', '#64748b'
                    file_color, file_bg, file_border = '#1d4ed8', 'rgba(59,130,246,0.10)', 'rgba(59,130,246,0.30)'
                pln.setText(
                    f"<span style='color: {info_color}; font-size: 12px; font-weight: 500;'>实施方案已就绪:</span> "
                    f"<span style='color: {file_color}; font-family: 'Cascadia Code', Consolas, monospace; font-size: 11.5px; font-weight: 600; background: {file_bg}; padding: 2px 7px; border-radius: 4px; border: 1px solid {file_border};'>{fn}</span> "
                    f"<span style='color: {hint_color}; font-size: 11px; margin-left: 6px;'>(双击打开方案)</span>"
                )
            except Exception:
                pass

    def add_log(self, level: str, message: str):
        """追加一条带时间戳的执行日志"""
        t_str = time.strftime("%H:%M:%S")
        color_map = {
            "INFO": "#58a6ff",
            "USER": "#79c0ff",
            "SYSTEM": "#d2a8ff",
            "MODEL": "#d2a8ff",
            "THINK": "#e5c07b",
            "TOOL": "#f0883e",
            "EXPLORE": "#7ee787",
            "DIFF": "#3fb950",
            "CMD": "#56b6c2",
            "WARN": "#f59e0b",
            "ERROR": "#f85149",
            "SUCCESS": "#7ee787",
            "RUN": "#61afef",
        }
        c = color_map.get(level.upper(), "#abb2bf")
        log_html = f"<span style='color:#636d83;'>[{t_str}]</span> <span style='color:{c}; font-weight:bold;'>[{level}]</span> <span style='color:#c9d1d9;'>{message}</span>"
        if hasattr(self, 'log_browser'):
            self.log_browser.append(log_html)
            self.log_browser.verticalScrollBar().setValue(self.log_browser.verticalScrollBar().maximum())
        self._log_count += 1
        if hasattr(self, 'log_count_lbl'):
            self.log_count_lbl.setText(f"{self._log_count} 条记录")

    def set_thought_content(self, text: str):
        """实时更新大模型思考与推理过程（仅当捕获到真实思维链时展示）"""
        if not text or not text.strip():
            return
        self._has_real_thought = True
        if hasattr(self, 'thought_section'):
            self.thought_section.setVisible(True)
        if hasattr(self, 'thought_browser'):
            self.thought_browser.setPlainText(text)
            self.thought_browser.verticalScrollBar().setValue(self.thought_browser.verticalScrollBar().maximum())
        if hasattr(self, 'thought_badge') and not self._is_done:
            self.thought_badge.setText("思考推理中")

    def update_processing_file(self, file_path: str, action_desc: str, is_done: bool = False, abs_path: str = ""):
        """更新处理中的文件状态"""
        clean_p = file_path.replace("\\", "/")
        self._processing_files[clean_p] = (action_desc, is_done, abs_path or clean_p)
        self._refresh_processing_files_ui()

    def _refresh_processing_files_ui(self):
        """刷新处理中的文件卡片列表"""
        if not hasattr(self, 'files_cards_layout'):
            return
        while self.files_cards_layout.count():
            item = self.files_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._processing_files:
            if hasattr(self, 'files_section'):
                self.files_section.setVisible(False)
            if hasattr(self, 'files_count_lbl'):
                self.files_count_lbl.setText("0 个文件")
            return

        if hasattr(self, 'files_section'):
            self.files_section.setVisible(True)
        if hasattr(self, 'files_count_lbl'):
            self.files_count_lbl.setText(f"{len(self._processing_files)} 个文件")

        for p_clean, (act_txt, done_flag, abs_p) in self._processing_files.items():
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #21262d;
                    border: 1px solid #30363d;
                    border-radius: 4px;
                }
                QFrame:hover {
                    background-color: #262c36;
                    border-color: #58a6ff;
                }
            """)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(6, 3, 6, 3)
            c_lay.setSpacing(6)

            file_icon = QLabel("📄")
            file_icon.setStyleSheet("font-size: 11px;")
            c_lay.addWidget(file_icon)

            f_name = Path(p_clean).name
            f_dir = str(Path(p_clean).parent).replace("\\", "/")
            if f_dir == ".":
                f_dir = ""
            name_lbl = QLabel(f"<b>{f_name}</b>" + (f" <span style='color:#636d83; font-size:10px;'>({f_dir})</span>" if f_dir else ""))
            name_lbl.setStyleSheet("color: #e5c07b; font-size: 11px; font-family: 'Cascadia Code', Consolas;")
            c_lay.addWidget(name_lbl)
            c_lay.addStretch()

            b_bg = "rgba(63, 185, 80, 0.15)" if done_flag else "rgba(56, 139, 253, 0.15)"
            b_fg = "#3fb950" if done_flag else "#58a6ff"
            st_lbl = QLabel(act_txt)
            st_lbl.setStyleSheet(f"background-color: {b_bg}; color: {b_fg}; border-radius: 3px; font-size: 10px; font-weight: bold; padding: 1px 5px;")
            c_lay.addWidget(st_lbl)

            open_btn = QPushButton("查看 ›")
            open_btn.setCursor(Qt.PointingHandCursor)
            open_btn.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #58a6ff; border: none; font-size: 10.5px;
                }
                QPushButton:hover { text-decoration: underline; }
            """)
            open_btn.clicked.connect(lambda checked, fp=p_clean: self.open_file_signal.emit(fp))
            c_lay.addWidget(open_btn)

            card.mousePressEvent = lambda e, fp=p_clean: self.open_file_signal.emit(fp)
            card.setCursor(Qt.PointingHandCursor)

            self.files_cards_layout.addWidget(card)

    def _toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.details_container.setVisible(self.is_expanded)
        self.toggle_btn.setText("▴" if self.is_expanded else "▾")

    def _on_explore_file_clicked(self, file_path: str, line_no: int = 1):
        if ":" in file_path and line_no == 1:
            try:
                p, l = file_path.rsplit(":", 1)
                file_path = p
                line_no = int(l)
            except Exception:
                pass
        self.open_file_signal.emit(f"{file_path}:{line_no}")

    def add_explore_item(self, path: str, line_range: str = "", item_type: str = "file"):
        """添加文件或目录探索分析步骤 (对齐 Antigravity IDE)"""
        clean_p = path.replace("\\", "/")
        act_txt = f"切片读取 ({line_range})" if line_range else f"检索探索 ({item_type})"
        self.update_processing_file(clean_p, act_txt, is_done=False)
        self.add_log("EXPLORE", f"探索分析: {clean_p} {act_txt}")

        exp_w = None
        for w in self.timeline_widgets:
            if isinstance(w, ExploredStepWidget):
                exp_w = w
                break
        if exp_w is None:
            exp_w = ExploredStepWidget(self)
            exp_w.open_file_requested.connect(self._on_explore_file_clicked)
            self.timeline_layout.addWidget(exp_w)
            self.timeline_widgets.append(exp_w)

        exp_w.add_item(path, line_range, item_type)
        self.explored_files = len(exp_w.analyzed_items)
        self.explored_searches = max(1, self.explored_searches)
        self.explored_lbl.setText(f"Explored {self.explored_files} files, {self.explored_searches} searches ›")

    def update_explored(self, files_cnt: int = 1, searches_cnt: int = 1):
        """更新探索检索状态 (对齐 Antigravity IDE: Explored 2 files, 5 searches ›)"""
        self.explored_files = max(self.explored_files, files_cnt)
        self.explored_searches = max(self.explored_searches, searches_cnt)
        self.explored_lbl.setText(f"Explored {self.explored_files} files, {self.explored_searches} searches ›")
        exp_w = None
        for w in self.timeline_widgets:
            if isinstance(w, ExploredStepWidget):
                exp_w = w
                break
        if exp_w is None:
            exp_w = ExploredStepWidget(self)
            exp_w.open_file_requested.connect(self._on_explore_file_clicked)
            self.timeline_layout.addWidget(exp_w)
            self.timeline_widgets.append(exp_w)
        exp_w._update_header()

    def set_working_status(self, text: str):
        """更新运行中状态文字（状态变更时写入日志）"""
        if not text:
            self.working_lbl.setVisible(False)
            return
        if hasattr(self, 'working_lbl'):
            if self.working_lbl.text() == text:
                return
            self.working_lbl.setText(text)
            self.working_lbl.setVisible(True)
        self.add_log("RUN", text)

    def set_status(self, status: str):
        """兼容状态设置接口"""
        if status in ("done", "finished", "stopped"):
            self.set_working_status("")
            self._is_done = True
            if hasattr(self, '_live_timer') and self._live_timer.isActive():
                self._live_timer.stop()

    def set_thought_time(self, seconds: float):
        """执行完毕：将顶部详细执行步骤自动折叠收起为 Worked for Xs › (对齐 Antigravity IDE)"""
        self._is_done = True
        if hasattr(self, '_live_timer') and self._live_timer.isActive():
            self._live_timer.stop()
        cost_str = f"{seconds:.1f}s" if seconds < 60 else f"{int(seconds//60)}m {int(seconds%60)}s"
        self.thought_lbl.setText(f"Worked for {cost_str} ›")
        self.thought_lbl.setStyleSheet("color: #8b949e; font-size: 11.5px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-weight: 500;")
        self.is_expanded = False
        self.details_container.setVisible(False)
        self.toggle_btn.setText("▾")
        if hasattr(self, 'working_lbl'):
            self.working_lbl.setText(f"全部任务执行完毕，方案与代码已就绪 (耗时 {cost_str})")
        if hasattr(self, 'status_dot'):
            self.status_dot.setStyleSheet("color: #3fb950; font-size: 11px;")
        if hasattr(self, 'timer_lbl'):
            self.timer_lbl.setText(f"(总耗时 {cost_str})")
        if getattr(self, '_has_real_thought', False):
            if hasattr(self, 'thought_section'):
                self.thought_section.setVisible(True)
            if hasattr(self, 'thought_badge'):
                self.thought_badge.setText("思考完成")
                self.thought_badge.setStyleSheet("background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border-radius: 8px; padding: 1px 6px; font-size: 10px; font-weight: bold;")
        else:
            if hasattr(self, 'thought_section'):
                self.thought_section.setVisible(False)
        self.add_log("SUCCESS", f"任务全流程闭环完成，总耗时 {cost_str}")

    def add_step(self, icon: str, text: str, highlight: bool = False):
        """添加常规思考步骤"""
        step_lbl = QLabel(f"{icon} {text}")
        color = "#e5c07b" if highlight else "#abb2bf"
        step_lbl.setStyleSheet(f"color: {color}; font-size: 11.5px; font-family: 'Cascadia Code', Consolas;")
        self.timeline_layout.addWidget(step_lbl)

    def add_command_step(self, cmd: str, output: str = "", exit_code: int = 0):
        """添加终端命令执行记录 (对齐截图 1、2、3 中的 Ran & python ...)"""
        cmd_w = CommandStepWidget(cmd, output, exit_code, self)
        self.timeline_layout.addWidget(cmd_w)
        self.timeline_widgets.append(cmd_w)

        # 记录终端沙箱真实日志
        self.add_log("CMD", f"沙箱终端执行: {cmd} (退出码: {exit_code})")

        # 兼容已有单元测试中的 commands_layout
        cmd_box = QWidget()
        c_lay = QVBoxLayout(cmd_box)
        title_lbl = QLabel(f"Ran <code>{cmd}</code> ▾")
        c_lay.addWidget(title_lbl)
        self.commands_layout.addWidget(cmd_box)

    def add_file_change(self, rel_path: str, action: str, added: int = 0, removed: int = 0, abs_path: str = ""):
        """执行中记录并渲染 Edited 文件条目 (对齐截图 1、2)，并同步刷新底部 Review 条 (对齐截图 3、5)"""
        clean_rel = rel_path.replace("\\", "/")
        # 防重复保护：如果时间线末端已是同一文件的同一变动（相同增删行），避免物理总线与流式解析双重追加
        if self.timeline_widgets and isinstance(self.timeline_widgets[-1], EditedStepWidget):
            last_w = self.timeline_widgets[-1]
            if last_w.rel_path == clean_rel and last_w.added == added and last_w.removed == removed:
                return
        if clean_rel in self.file_changes:
            # 更新已有记录 (用于底部审查胶囊聚合)
            for idx, r in enumerate(self.file_records):
                if r[0] == clean_rel:
                    self.file_records[idx] = (clean_rel, abs_path or r[1], action, added, removed)
                    break
        else:
            self.file_changes.append(clean_rel)
            self.file_records.append((clean_rel, abs_path, action, added, removed))

            # 兼容已有单元测试中的 edited_layout (不设置 parent 且显式隐藏，杜绝浮动在卡片左上角 (0, 0))
            item_w = FileChangeItemWidget(clean_rel, action, added, removed, abs_path=abs_path)
            item_w.hide()
            item_w.open_file_requested.connect(self.open_file_signal)
            item_w.open_diff_requested.connect(self.open_diff_signal)
            item_w.single_accept_requested.connect(self.single_accept_signal)
            item_w.single_revert_requested.connect(self.single_reject_signal)
            self.edited_layout.addWidget(item_w)

        # 1. 在时序时间线中追加 EditedStepWidget (带 Open Diff 悬浮/直接跳转)
        edited_step = EditedStepWidget(clean_rel, action, added, removed, abs_path, self)
        edited_step.open_file_requested.connect(self.open_file_signal)
        edited_step.open_diff_requested.connect(self.open_diff_signal)
        self.timeline_layout.addWidget(edited_step)
        self.timeline_widgets.append(edited_step)

        # 2. 激活并刷新顶部处理中文件面板与日志 (对齐真实文件落盘)
        self.update_processing_file(clean_rel, f"写入变更 (+{added}/-{removed})", is_done=True, abs_path=abs_path)
        self.add_log("DIFF", f"文件修改落盘: {clean_rel} (+{added}/-{removed})")

        # 3. 激活并刷新底部 Review 审查胶囊栏 (对齐截图 3、5)
        self.review_bar_widget.setVisible(True)
        self._update_review_capsule_ui()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'summary_browser') and self.summary_browser.isVisible():
            doc = self.summary_browser.document()
            vp_w = max(240, self.summary_browser.viewport().width())
            doc.setTextWidth(vp_w)
            h = int(doc.size().height()) + 20
            self.summary_browser.setFixedHeight(max(36, h))

    def set_summary_text(self, text: str):
        """流式与最终更新纯粹的总结说明内容，自适应调整高度以自然嵌入滚动流"""
        clean = strip_emojis((text or "").strip())
        if not clean:
            self.summary_browser.setVisible(False)
            self._cached_summary = ""
            return

        self._cached_summary = clean
        self.summary_browser.setVisible(True)
        # 重新应用当前主题的 defaultStyleSheet 再 setMarkdown，确保 Markdown 颜色随主题
        try:
            self._apply_default_summary_style()
        except Exception:
            pass
        self.summary_browser.setMarkdown(clean)
        # 自适应调整高度以避免内嵌滚动条
        doc = self.summary_browser.document()
        vp_w = self.summary_browser.viewport().width()
        if vp_w < 100:
            vp_w = max(280, self.width() - 36 if self.width() > 50 else 400)
        doc.setTextWidth(vp_w)
        h = int(doc.size().height()) + 20
        self.summary_browser.setFixedHeight(max(36, h))
        self.updateGeometry()

    def _apply_default_summary_style(self):
        """把当前主题的 defaultStyleSheet 应用到 summary_browser 的 QTextDocument。
        QTextBrowser 的 Markdown 渲染由 QTextDocument 的 defaultCharFormat 控制，
        QSS 的 color 不会自动渗透，必须用 setDefaultStyleSheet。"""
        d = getattr(self, 'is_dark', True)
        text_primary = '#e6edf3' if d else '#1f2328'
        link_color  = '#79c0ff' if d else '#1d4ed8'
        pre_bg      = '#0c0c0c' if d else '#f3f4f6'
        code_bg     = '#21262d' if d else '#e2e8f0'
        sb = getattr(self, 'summary_browser', None)
        if sb is None:
            return
        try:
            sb.document().setDefaultStyleSheet(f"""
                body {{ color: {text_primary}; font-size: 12.5px;
                       font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                       'Microsoft YaHei UI', Roboto, sans-serif; }}
                a    {{ color: {link_color}; }}
                pre  {{ background: {pre_bg}; color: {text_primary}; }}
                code {{ background: {code_bg}; color: {text_primary}; }}
            """)
        except Exception:
            pass

    def _update_review_capsule_ui(self):
        """刷新底部 Review 审查胶囊条文本与下挂文件抽屉 (对齐截图 4、5)"""
        n = len(self.file_records)
        total_add = sum(r[3] for r in self.file_records)
        total_del = sum(r[4] for r in self.file_records)
        file_unit = "file" if n == 1 else "files"
        arrow = "▾" if self.drawer_expanded else "›"

        # 对齐截图 5：1 file changed  +16 -15  >
        self.capsule_stat_btn.setText(f"{n} {file_unit} changed  +{total_add} -{total_del}  {arrow}")

        # 刷新下挂变动文件卡片抽屉 (对齐截图 4 右下角: dev_mode_view.py  ui/Demo/desk_tools/ui)
        while self.files_drawer_layout.count():
            item = self.files_drawer_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for rel_p, abs_p, action, added, removed in self.file_records:
            row_card = QFrame()
            row_card.setStyleSheet("""
                QFrame {
                    background-color: #23272e;
                    border: 1px solid #313640;
                    border-radius: 5px;
                    padding: 3px 6px;
                }
                QFrame:hover {
                    background-color: #2c313a;
                    border-color: #61afef;
                }
            """)
            r_lay = QHBoxLayout(row_card)
            r_lay.setContentsMargins(6, 4, 6, 4)
            r_lay.setSpacing(6)

            f_lbl = QLabel(f"<b>{rel_p}</b> <span style='color:#636d83; font-size:10.5px;'>{abs_p or rel_p}</span>")
            f_lbl.setStyleSheet("color: #abb2bf; font-size: 11.5px; font-family: 'Cascadia Code', Consolas;")
            r_lay.addWidget(f_lbl)
            r_lay.addStretch()

            diff_tag = QLabel(f"<span style='color:#3fb950;'>+{added}</span> <span style='color:#f85149;'>-{removed}</span>")
            diff_tag.setStyleSheet("font-size: 11px; font-family: 'Cascadia Code', Consolas;")
            r_lay.addWidget(diff_tag)

            target_p = abs_p if (abs_p and Path(abs_p).is_absolute()) else rel_p

            diff_btn = QPushButton("查看对比 ›")
            diff_btn.setCursor(Qt.PointingHandCursor)
            diff_btn.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #61afef; border: none; font-size: 10.5px;
                }
                QPushButton:hover { text-decoration: underline; }
            """)
            diff_btn.clicked.connect(lambda checked, p=target_p: self.open_diff_signal.emit(p))
            r_lay.addWidget(diff_btn)

            # 点击整行卡片均可打开对应 Diff 并跳转定位！
            row_card.mousePressEvent = lambda e, p=target_p: self.open_diff_signal.emit(p)
            row_card.setCursor(Qt.PointingHandCursor)

            self.files_drawer_layout.addWidget(row_card)

    def _on_capsule_clicked(self):
        """
        点击底栏文件变更统计条 (对齐用户需求：点击最后面这个变更代码的行数这里，弹出这次变更的文件，并自动跳转定位):
        1. 弹出并切换下挂变动文件卡片抽屉 (对齐截图 4)
        2. 如果有文件变更，直接在中间主屏幕打开 Diff 比对视图并自动平滑定位跳转到变更行！
        """
        if not self.file_records:
            return
        
        # 无论单文件还是多文件，均弹出下挂卡片抽屉
        self.drawer_expanded = not self.drawer_expanded
        self.files_drawer.setVisible(self.drawer_expanded)
        self._update_review_capsule_ui()

        # 核心交互：直接在主屏幕打开 Diff 视图并自动平滑定位跳转到变更代码处！
        r0 = self.file_records[0]
        target_file = r0[1] if (len(r0) > 1 and r0[1] and Path(r0[1]).is_absolute()) else r0[0]
        self.open_diff_signal.emit(target_file)

    def _on_review_clicked(self):
        """点击 Review 按钮：展开下挂文件抽屉，并在主屏幕打开 Diff 并自动平滑跳转定位"""
        if not self.file_records:
            return
        self.drawer_expanded = True
        self.files_drawer.setVisible(True)
        self._update_review_capsule_ui()
        r0 = self.file_records[0]
        target_file = r0[1] if (len(r0) > 1 and r0[1] and Path(r0[1]).is_absolute()) else r0[0]
        self.open_diff_signal.emit(target_file)


    def _on_accept(self):
        """用户点击【接收】：进入已接收状态，但绝不禁用撤回按钮！"""
        if not self.file_records and not self.file_changes:
            return
        if self.current_state == "accepted":
            return

        self.current_state = "accepted"
        self.accept_btn.setText("已接收")
        self.accept_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e3a24; color: #7ee787; border: 1px solid #2e7d32;
                border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background-color: #285430; }
        """)

        # 撤回按钮保持 100% 可随时反悔！
        self.reject_btn.setEnabled(True)
        self.reject_btn.setText("Revert")
        self.reject_btn.setStyleSheet("""
            QPushButton {
                background-color: #2c313a; color: #f85149; border: 1px solid #482327;
                border-radius: 4px; padding: 2px 10px; font-size: 11px; font-weight: 500;
            }
            QPushButton:hover { background-color: #482327; color: #ff7b72; }
        """)

        paths = []
        for r in self.file_records:
            p = r[1] if (len(r) > 1 and r[1] and Path(r[1]).is_absolute()) else r[0]
            paths.append(p)
        if not paths:
            paths = list(self.file_changes)
        self.accept_changes_signal.emit(",".join(paths))

    def _on_reject(self):
        """用户点击【Revert】：物理还原代码，接收按钮转换为【Restore】"""
        if not self.file_records and not self.file_changes:
            return
        if self.current_state == "rejected":
            return

        self.current_state = "rejected"
        self.reject_btn.setText("Reverted")
        self.reject_btn.setStyleSheet("""
            QPushButton {
                background-color: #3f1e24; color: #ff7b72; border: 1px solid #c62828;
                border-radius: 4px; padding: 2px 10px; font-size: 11px; font-weight: 500;
            }
            QPushButton:hover { background-color: #50252b; }
        """)

        # 接收按钮转换为【Restore】，保持 100% 可重新恢复！
        self.accept_btn.setEnabled(True)
        self.accept_btn.setText("Restore")
        self.accept_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e3a24; color: #7ee787; border: 1px solid #2e7d32;
                border-radius: 4px; padding: 2px 10px; font-size: 11px; font-weight: 500;
            }
            QPushButton:hover { background-color: #2e7d32; color: #ffffff; }
        """)

        paths = []
        for r in self.file_records:
            p = r[1] if (len(r) > 1 and r[1] and Path(r[1]).is_absolute()) else r[0]
            paths.append(p)
        if not paths:
            paths = list(self.file_changes)
        self.reject_changes_signal.emit(",".join(paths))

    def add_plan_proceed_card(self, on_proceed_fn, on_preview_fn=None, plan_file_name="implementation_plan.md"):
        """为技术方案追加专属的现代卡片：双击卡片直接预览，Process 按钮启动落地"""
        if hasattr(self, '_plan_card') and self._plan_card:
            return
        card = QFrame()
        card.setObjectName("planProceedCard")
        card.setCursor(Qt.PointingHandCursor)
        card.setToolTip(f"💡 双击卡片直接在中间主屏幕打开方案文档预览 ({plan_file_name})")
        # 用 self.is_dark 参数化样式：之前写死深色导致 light 主题下字看不清
        d = self.is_dark
        if d:
            bg_a, bg_b = '#1a202c', '#141822'
            border_c, border_l, border_l_h = '#30363d', '#388bfd', '#58a6ff'
            hover_a, hover_b = '#1f2636', '#171c28'
            info_color, hint_color = '#c9d1d9', '#8b949e'
            file_color, file_bg, file_border = '#58a6ff', 'rgba(56,139,253,0.12)', 'rgba(56,139,253,0.28)'
            btn_bg, btn_bg_h, btn_bg_p, btn_border, btn_border_h = '#238636', '#2ea043', '#1e7e34', '#2ea043', '#3fb950'
        else:
            bg_a, bg_b = '#eff6ff', '#dbeafe'
            border_c, border_l, border_l_h = '#bfdbfe', '#3b82f6', '#1d4ed8'
            hover_a, hover_b = '#dbeafe', '#bfdbfe'
            info_color, hint_color = '#1f2328', '#64748b'
            file_color, file_bg, file_border = '#1d4ed8', 'rgba(59,130,246,0.10)', 'rgba(59,130,246,0.30)'
            btn_bg, btn_bg_h, btn_bg_p, btn_border, btn_border_h = '#16a34a', '#15803d', '#166534', '#16a34a', '#22c55e'
        card.setStyleSheet(f"""
            QFrame#planProceedCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {bg_a}, stop:1 {bg_b});
                border: 1px solid {border_c};
                border-left: 3px solid {border_l};
                border-radius: 6px;
                padding: 6px 14px;
                margin: 6px 0 4px 0;
            }}
            QFrame#planProceedCard:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {hover_a}, stop:1 {hover_b});
                border: 1px solid {border_l};
                border-left: 3px solid {border_l_h};
            }}
        """)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(12)

        # 方案文件标题与双击提示（颜色按主题切换）
        info_lbl = QLabel(
            f"<span style='color: {info_color}; font-size: 12px; font-weight: 500;'>实施方案已就绪:</span> "
            f"<span style='color: {file_color}; font-family: Consolas, monospace; font-size: 11.5px; font-weight: 600; background: {file_bg}; padding: 2px 7px; border-radius: 4px; border: 1px solid {file_border};'>{plan_file_name}</span> "
            f"<span style='color: {hint_color}; font-size: 11px; margin-left: 6px;'>(双击打开方案)</span>"
        )
        info_lbl.setStyleSheet("background: transparent; border: none;")
        info_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(info_lbl, 1)

        def _on_card_double_click(event):
            if event.button() == Qt.LeftButton:
                if on_preview_fn:
                    on_preview_fn()
        card.mouseDoubleClickEvent = _on_card_double_click

        btn_proceed = QPushButton("Process")
        btn_proceed.setCursor(Qt.PointingHandCursor)
        btn_proceed.setToolTip("批准并分步执行实施方案 (Process)")
        btn_proceed.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
                border: 1px solid {btn_border};
                border-radius: 4px;
                padding: 5px 18px;
                min-width: 68px;
            }}
            QPushButton:hover {{
                background-color: {btn_bg_h};
                border-color: {btn_border_h};
            }}
            QPushButton:pressed {{
                background-color: {btn_bg_p};
            }}
        """)
        btn_proceed.clicked.connect(on_proceed_fn)
        lay.addWidget(btn_proceed)

        # 保存引用：apply_theme 时刷新
        self._plan_card = card
        self._plan_card_info_lbl = info_lbl
        self._plan_card_file_name = plan_file_name
        self.layout.addWidget(card)


class ConvoItemWidget(QFrame):
    """历史会话列表单条项目组件 (对齐 Antigravity IDE 布局)"""
    clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)

    def __init__(self, session_data: dict, is_current: bool = False, parent=None):
        super().__init__(parent)
        self.session_id = session_data["id"]
        self.session_title = session_data.get("title", "未命名会话")
        self.updated_at = session_data.get("updated_at") or session_data.get("created_at", "")
        self.is_current = is_current
        self.is_selected = False

        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("ConvoItemWidget")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 2, 8, 2)
        lay.setSpacing(8)

        # 标题 (左侧：使用自适应省略号标签，确保绝不挤压右侧元素或撑出横向滚动条)
        self.title_lbl = ElidedLabel(self.session_title)
        self.title_lbl.setToolTip(self.session_title)
        self.title_lbl.setStyleSheet("""
            QLabel {
                color: #e6edf3;
                font-size: 12px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: transparent;
                border: none;
            }
        """)
        lay.addWidget(self.title_lbl, 1)

        # 相对时间 (右侧)
        rel_time = format_relative_time(self.updated_at)
        self.time_lbl = QLabel(rel_time)
        self.time_lbl.setStyleSheet("""
            QLabel {
                color: #7d8590;
                font-size: 11px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: transparent;
                border: none;
            }
        """)
        lay.addWidget(self.time_lbl)

        # 删除图标按钮 (🗑)
        self.del_btn = QPushButton()
        self.del_btn.setFixedSize(20, 20)
        self.del_btn.setIcon(create_trash_icon("#7d8590"))
        self.del_btn.setIconSize(QSize(13, 13))
        self.del_btn.setToolTip("删除此会话记录")
        self.del_btn.setCursor(Qt.PointingHandCursor)
        self.del_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(248, 81, 73, 0.25);
            }
        """)
        self.del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.session_id))
        lay.addWidget(self.del_btn)

        self._update_style(False)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._update_style(False)

    def _update_style(self, is_hover: bool):
        if self.is_selected:
            bg = "#1f385c"
            border = "1px solid #388bfd"
        elif is_hover:
            bg = "#2c313a"
            border = "1px solid transparent"
        elif self.is_current:
            bg = "#21262d"
            border = "1px solid #30363d"
        else:
            bg = "transparent"
            border = "1px solid transparent"

        self.setStyleSheet(f"""
            QFrame#ConvoItemWidget {{
                background-color: {bg};
                border: {border};
                border-radius: 6px;
            }}
        """)

    def enterEvent(self, event):
        self._update_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.del_btn.underMouse():
                self.clicked.emit(self.session_id)
        super().mousePressEvent(event)


class PastConversationsDialog(QDialog):
    """Antigravity IDE 风格会话历史记录选择浮窗"""
    session_selected = pyqtSignal(int)
    session_deleted = pyqtSignal(int)

    def __init__(self, memory_manager, current_session_id: Optional[int], workspace_root: str = "", parent=None):
        super().__init__(parent)
        self.memory = memory_manager
        self.current_session_id = current_session_id
        self.workspace_root = workspace_root
        self.all_items: List[ConvoItemWidget] = []
        self.selected_index = 0

        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setFixedSize(390, 440)

        self.setStyleSheet("""
            PastConversationsDialog {
                background-color: #1e2228;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(10, 10, 10, 8)
        main_lay.setSpacing(6)

        # 1. 顶部搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search all convos...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background-color: #16191d;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QLineEdit:focus {
                border: 1px solid #388bfd;
                background-color: #1a1e24;
            }
        """)
        self.search_edit.textChanged.connect(self._on_search_changed)
        main_lay.addWidget(self.search_edit)

        # 2. 列表滚动区 (禁用横向滚动条，精细控制右侧留白避免遮挡选中框)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                border-radius: 3px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #58a6ff;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                height: 0px;
                background: transparent;
                border: none;
            }
            QScrollBar:horizontal {
                height: 0px;
                border: none;
                background: transparent;
            }
            QScrollBar::handle:horizontal,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                width: 0px;
                height: 0px;
                background: transparent;
                border: none;
            }
        """)

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(4, 4, 8, 4)
        self.list_layout.setSpacing(3)
        self.scroll_area.setWidget(self.list_container)
        main_lay.addWidget(self.scroll_area, 1)

        # 3. 底部导航键盘提示 (↑ ↓ to navigate, ↵ to select)
        footer = QWidget()
        footer.setFixedHeight(22)
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(4, 0, 4, 0)
        f_lay.setSpacing(8)

        lbl_nav = QLabel("↑ ↓ to navigate")
        lbl_nav.setStyleSheet("color: #7d8590; font-size: 11px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;")
        f_lay.addWidget(lbl_nav)

        f_lay.addStretch()

        lbl_select = QLabel("↵ to select")
        lbl_select.setStyleSheet("color: #7d8590; font-size: 11px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;")
        f_lay.addWidget(lbl_select)

        main_lay.addWidget(footer)

        self._load_sessions()

    def _on_search_changed(self, text: str):
        self._load_sessions(text)

    def _load_sessions(self, filter_text: str = ""):
        while self.list_layout.count() > 0:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count() > 0:
                    sub = item.layout().takeAt(0)
                    if sub.widget(): sub.widget().deleteLater()

        self.all_items.clear()
        if not self.memory:
            return

        all_sessions = self.memory.get_all_sessions()
        filter_lower = filter_text.strip().lower()
        if filter_lower:
            filtered = [s for s in all_sessions if filter_lower in s.get("title", "").lower()]
        else:
            filtered = all_sessions

        if not filtered:
            empty_lbl = QLabel("No conversations found")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #7d8590; font-size: 12px; padding: 30px;")
            self.list_layout.addWidget(empty_lbl)
            self.list_layout.addStretch()
            return

        current_sess = None
        recent_sess = []

        for s in filtered:
            if s["id"] == self.current_session_id and not filter_lower:
                current_sess = s
            else:
                recent_sess.append(s)

        # 1. 渲染 Current
        if current_sess:
            lbl_curr = QLabel("Current")
            lbl_curr.setStyleSheet("color: #7d8590; font-size: 11px; font-weight: 600; padding: 4px 6px 2px 6px;")
            self.list_layout.addWidget(lbl_curr)

            item_w = ConvoItemWidget(current_sess, is_current=True, parent=self)
            item_w.clicked.connect(self._on_item_clicked)
            item_w.delete_clicked.connect(self._on_item_delete_clicked)
            self.list_layout.addWidget(item_w)
            self.all_items.append(item_w)

        # 2. 渲染 Recent
        if recent_sess:
            lbl_rec = QLabel("Recent")
            lbl_rec.setStyleSheet("color: #7d8590; font-size: 11px; font-weight: 600; padding: 6px 6px 2px 6px;")
            self.list_layout.addWidget(lbl_rec)

            for s in recent_sess:
                item_w = ConvoItemWidget(s, is_current=False, parent=self)
                item_w.clicked.connect(self._on_item_clicked)
                item_w.delete_clicked.connect(self._on_item_delete_clicked)
                self.list_layout.addWidget(item_w)
                self.all_items.append(item_w)

        self.list_layout.addStretch()
        self.selected_index = 0
        self._update_item_selection()

    def _update_item_selection(self):
        for idx, item in enumerate(self.all_items):
            item.set_selected(idx == self.selected_index)

    def _move_selection(self, delta: int):
        if not self.all_items:
            return
        self.selected_index = max(0, min(len(self.all_items) - 1, self.selected_index + delta))
        self._update_item_selection()
        target_item = self.all_items[self.selected_index]
        self.scroll_area.ensureWidgetVisible(target_item)

    def _select_current_item(self):
        if 0 <= self.selected_index < len(self.all_items):
            sid = self.all_items[self.selected_index].session_id
            self._on_item_clicked(sid)

    def _on_item_clicked(self, session_id: int):
        self.session_selected.emit(session_id)
        self.close()

    def _on_item_delete_clicked(self, session_id: int):
        if self.memory:
            self.memory.delete_session(session_id)
        self.session_deleted.emit(session_id)
        self._load_sessions(self.search_edit.text())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Down:
            self._move_selection(1)
            event.accept()
        elif event.key() == Qt.Key_Up:
            self._move_selection(-1)
            event.accept()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._select_current_item()
            event.accept()
        elif event.key() == Qt.Key_Escape:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)



class DevModeView(QWidget):
    """代码开发模式主视图 (IDE 风格四栏/三栏布局)"""
    open_file_requested = pyqtSignal(str)
    ai_chunk_signal = pyqtSignal(str)
    ai_done_signal = pyqtSignal(str)
    ai_error_signal = pyqtSignal(str)
    file_diff_recorded_signal = pyqtSignal(object)
    test_finished_signal = pyqtSignal(int, str, str, float, str)

    def __init__(self, config: dict, ai_engine, memory=None, save_config_fn=None, parent=None):
        super().__init__(parent)
        self.test_finished_signal.connect(self._on_test_finished)
        self.config = config
        self.ai_engine = ai_engine
        self.memory = memory
        if self.memory is None:
            try:
                from core.memory_manager import MemoryManager
                db_p = Path.cwd() / "memory.db"
                self.memory = MemoryManager(db_p)
            except Exception as e:
                print(f"[DevModeView] 初始化 MemoryManager 异常: {e}")
        self._current_session_id: Optional[int] = None
        self.save_config_fn = save_config_fn
        self.is_dark = (config.get("ui_theme", "light") == "dark")

        # 当前工作空间目录
        self.workspace_root = config.get("workspace_dir", "")
        if not self.workspace_root or not Path(self.workspace_root).exists():
            self.workspace_root = str(Path.cwd().resolve())

        self.opened_editors: Dict[str, CodeEditor] = {}
        self._current_ai_lbl = None
        self._current_traj = None
        self._is_generating = False
        self._generated_files = []
        self._dev_message_queue: List = []
        self._attached_image_path: Optional[str] = None
        # 方案审批门控：记录当前活跃方案文档路径与审批状态
        self._current_plan_file_path: str = ""
        self._pending_plan_approval: bool = False

        # 挂载底层文件差异追踪监听总线 (100% 捕获真实磁盘文件新建与修改)
        try:
            from core.file_diff_tracker import FileDiffTracker
            FileDiffTracker.get_instance().add_listener(self._on_tracker_file_changed)
            self.file_diff_recorded_signal.connect(self._handle_file_diff_record)
        except Exception as e:
            print(f"[DevModeView] 挂载 FileDiffTracker 监听总线异常: {e}")

        self._init_ui()
        self._connect_ai_signals()
        self._init_session_state()
        self._organize_and_cleanup_plans()

    def _init_ui(self):
        self.setStyleSheet("""
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #3e4451;
                border-radius: 4px;
                min-height: 28px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5c6370;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background: transparent;
                height: 8px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #3e4451;
                border-radius: 4px;
                min-width: 28px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #5c6370;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: transparent;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
            }
        """)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 顶部专业菜单栏
        self.menu_bar = self._create_dev_menu_bar()
        main_layout.addWidget(self.menu_bar)

        # 2. 核心水平分割容器 (Explorer | Editor & Console | AI Assistant)
        self.h_splitter = QSplitter(Qt.Horizontal)
        self.h_splitter.setHandleWidth(4)
        self.h_splitter.setChildrenCollapsible(True)
        self.h_splitter.setStyleSheet("""
            QSplitter::handle:horizontal {
                background-color: #2b2b2b;
                width: 4px;
            }
            QSplitter::handle:horizontal:hover {
                background-color: #007acc;
            }
        """)

        # 2.1 左侧资源管理器 (Explorer) - 允许完全覆盖折叠至 0 宽度
        self.explorer_panel = self._create_explorer_panel()
        self.h_splitter.addWidget(self.explorer_panel)
        self.h_splitter.setCollapsible(0, True)
        self.h_splitter.splitterMoved.connect(self._on_h_splitter_moved)

        # 2.2 中间主体区域 (代码多标签编辑器 + 底部控制台)
        self.center_splitter = QSplitter(Qt.Vertical)
        self.center_splitter.setHandleWidth(2)
        self.center_splitter.setStyleSheet("""
            QSplitter::handle { background-color: #2b2b2b; }
        """)

        self.editor_tab_widget = self._create_editor_tabs()
        self.center_splitter.addWidget(self.editor_tab_widget)

        self.console_panel = self._create_console_panel()
        self.center_splitter.addWidget(self.console_panel)

        self.center_splitter.setSizes([560, 220])
        self.h_splitter.addWidget(self.center_splitter)

        # 2.3 最右侧 AI 助手面板
        self.ai_panel = self._create_ai_agent_panel()
        self.h_splitter.addWidget(self.ai_panel)

        # 默认宽度比例: 资源管理器(220px), 编辑器主体(580px), AI助手(380px)
        self.h_splitter.setSizes([220, 580, 380])
        main_layout.addWidget(self.h_splitter, 1)

        # 启动时智能恢复上次记忆的工作空间目录与所有已打开文件标签页
        self._restore_dev_workspace_session_state()

        # 首启立即按 self.is_dark 刷一遍主题：之前 _create_*() 里很多样式表写死深色，
        # 只在运行时切主题才刷新；config 起步就是 light 的话就不会触发 apply_theme，
        # 因此强制这里首刷一次。
        try:
            self.apply_theme(self.is_dark)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════
    #  1. 顶部菜单栏
    # ══════════════════════════════════════════════════════════
    def _create_dev_menu_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(34)
        bar.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #2d2d2d;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(6)

        # 菜单按钮统一样式
        btn_style = """
            QPushButton {
                background: transparent; color: #cccccc; border: none;
                border-radius: 4px; padding: 4px 8px; font-size: 12px;
                font-family: 'Segoe UI', 'Microsoft YaHei UI';
            }
            QPushButton:hover { background-color: #333333; color: #ffffff; }
        """

        # 文件菜单
        self.file_menu_btn = QPushButton("文件 (F) ▾")
        self.file_menu_btn.setStyleSheet(btn_style)
        self.file_menu = QMenu(self)
        self.file_menu.setStyleSheet("""
            QMenu {
                background-color: #252526; color: #cccccc; border: 1px solid #3c3c3c;
                padding: 4px 0; font-size: 12px; font-family: 'Segoe UI', 'Microsoft YaHei UI';
            }
            QMenu::item { padding: 5px 24px; }
            QMenu::item:selected { background-color: #094771; color: #ffffff; }
        """)
        
        act_new_file = self.file_menu.addAction("新建文件\tCtrl+N")
        act_new_file.triggered.connect(self._action_new_file)
        act_open_file = self.file_menu.addAction("打开文件...\tCtrl+O")
        act_open_file.triggered.connect(self._action_open_file)
        act_open_folder = self.file_menu.addAction("打开文件夹...\tCtrl+K Ctrl+O")
        act_open_folder.triggered.connect(self._action_open_folder)
        self.file_menu.addSeparator()
        act_save = self.file_menu.addAction("保存\tCtrl+S")
        act_save.triggered.connect(self._action_save_current)
        act_close_tab = self.file_menu.addAction("关闭当前编辑器\tCtrl+W")
        act_close_tab.triggered.connect(self._action_close_current_tab)

        self.file_menu_btn.setMenu(self.file_menu)
        lay.addWidget(self.file_menu_btn)

        # 编辑菜单
        self.edit_menu_btn = QPushButton("编辑 (E) ▾")
        self.edit_menu_btn.setStyleSheet(btn_style)
        self.edit_menu = QMenu(self)
        self.edit_menu.setStyleSheet(self.file_menu.styleSheet())
        act_undo = self.edit_menu.addAction("撤销\tCtrl+Z")
        act_undo.triggered.connect(lambda: self._get_current_editor() and self._get_current_editor().undo())
        act_redo = self.edit_menu.addAction("重做\tCtrl+Y")
        act_redo.triggered.connect(lambda: self._get_current_editor() and self._get_current_editor().redo())
        self.edit_menu.addSeparator()
        act_select_all = self.edit_menu.addAction("全选\tCtrl+A")
        act_select_all.triggered.connect(lambda: self._get_current_editor() and self._get_current_editor().selectAll())
        self.edit_menu_btn.setMenu(self.edit_menu)
        lay.addWidget(self.edit_menu_btn)

        # 查看菜单
        self.view_menu_btn = QPushButton("查看 (V) ▾")
        self.view_menu_btn.setStyleSheet(btn_style)
        self.view_menu = QMenu(self)
        self.view_menu.setStyleSheet(self.file_menu.styleSheet())
        act_toggle_explorer = self.view_menu.addAction("切换资源管理器显示")
        act_toggle_explorer.triggered.connect(self._toggle_explorer)
        act_toggle_console = self.view_menu.addAction("切换底部终端显示")
        act_toggle_console.triggered.connect(self._toggle_console)
        act_toggle_ai = self.view_menu.addAction("切换 AI 助手显示")
        act_toggle_ai.triggered.connect(self._toggle_ai_panel)
        act_toggle_minimap = self.view_menu.addAction("显示侧边代码缩略图 (Minimap)")
        act_toggle_minimap.setCheckable(True)
        act_toggle_minimap.setChecked(False)
        act_toggle_minimap.triggered.connect(self._toggle_minimap)
        self.view_menu_btn.setMenu(self.view_menu)
        lay.addWidget(self.view_menu_btn)

        # 终端菜单
        self.term_menu_btn = QPushButton("终端 (T) ▾")
        self.term_menu_btn.setStyleSheet(btn_style)
        self.term_menu = QMenu(self)
        self.term_menu.setStyleSheet(self.file_menu.styleSheet())
        # 新增：把底部控制台显示出来并切到"交互终端"页。
        # 用户点 console_panel 右上角的"收起"按钮后，console_panel 整体隐藏；
        # 之前只能通过顶栏菜单「查看 (V) ▾ → 切换底部终端显示」重新打开，
        # 但很多人不知道那条路径。在最直接的「终端 (T) ▾」里加一个"打开交互终端"
        # 入口最自然。
        act_open_term = self.term_menu.addAction("打开交互终端")
        act_open_term.triggered.connect(self._open_interactive_terminal)
        self.term_menu.addSeparator()
        act_run_cur = self.term_menu.addAction("运行当前 Python 文件\tF5")
        act_run_cur.triggered.connect(self._run_current_file)
        act_clear_term = self.term_menu.addAction("清空终端输出")
        act_clear_term.triggered.connect(self._clear_terminal)
        self.term_menu_btn.setMenu(self.term_menu)
        lay.addWidget(self.term_menu_btn)

        # 扩展菜单 (MCP 与 Skill 扩展管理)
        self.ext_menu_btn = QPushButton("扩展 (X) ▾")
        self.ext_menu_btn.setStyleSheet(btn_style)
        self.ext_menu = QMenu(self)
        self.ext_menu.setStyleSheet(self.file_menu.styleSheet())
        act_ext_center = self.ext_menu.addAction("MCP 与 Skill 扩展管理中心...")
        act_ext_center.triggered.connect(self._open_extension_manager)
        self.ext_menu.addSeparator()
        act_dev_persona = self.ext_menu.addAction("开发者身份设定与自定义...")
        act_dev_persona.triggered.connect(self._open_extension_manager)
        self.ext_menu_btn.setMenu(self.ext_menu)
        lay.addWidget(self.ext_menu_btn)

        # 快捷键 F5 运行
        self.shortcut_run = QShortcut(QKeySequence("F5"), self)
        self.shortcut_run.activated.connect(self._run_current_file)
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self._action_save_current)

        lay.addSpacing(16)
        self.ws_path_lbl = QLabel(f"{Path(self.workspace_root).name}")
        self.ws_path_lbl.setToolTip(self.workspace_root)
        self.ws_path_lbl.setStyleSheet("color: #858585; font-size: 11.5px; font-family: 'Segoe UI';")
        lay.addWidget(self.ws_path_lbl)

        lay.addStretch()
        return bar

    def _switch_back_to_work(self):
        p = self.parent()
        while p:
            if hasattr(p, '_switch_app_mode'):
                p._switch_app_mode(0)
                return
            p = p.parent()

    def _update_dev_mode_capsule_style(self):
        if not hasattr(self, 'mode_capsule') or not hasattr(self, 'btn_mode_work') or not hasattr(self, 'btn_mode_dev'):
            return
        d = self.is_dark
        capsule_bg = "#27272a" if d else "#e2e8f0"
        capsule_border = "#3f3f46" if d else "#cbd5e1"
        self.mode_capsule.setStyleSheet(f"""
            QFrame {{
                background-color: {capsule_bg};
                border: 1px solid {capsule_border};
                border-radius: 7px;
            }}
        """)
        # 在开发模式下，开发按钮为高亮蓝 (#0e639c)，办公按钮为透明待选状态 (对齐截图)
        self.btn_mode_work.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {'#a1a1aa' if d else '#64748b'}; border: none;
                border-radius: 5px; padding: 2px 4px; font-size: 11px;
                font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
            }}
            QPushButton:hover {{ color: {'#ffffff' if d else '#0f172a'}; background-color: {'#333338' if d else '#f1f5f9'}; }}
        """)
        self.btn_mode_dev.setStyleSheet("""
            QPushButton {
                background-color: #0e639c; color: #ffffff; border: none;
                border-radius: 5px; padding: 2px 4px; font-size: 11px; font-weight: bold;
                font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
            }
        """)

    def _on_dev_pet_toggle(self):
        p = self.parent()
        while p:
            if hasattr(p, '_toggle_pet_visible'):
                p._toggle_pet_visible()
                self.update_pet_btn_state()
                return
            p = p.parent()
        curr = self.config.get("pet", {}).get("enabled", self.config.get("pet_enabled", True))
        new_val = not curr
        self.config.setdefault("pet", {})["enabled"] = new_val
        self.config["pet_enabled"] = new_val
        if self.save_config_fn:
            try:
                self.save_config_fn(self.config)
            except Exception:
                pass
        self.update_pet_btn_state()
        self.set_status("桌宠已开启" if new_val else "桌宠已关闭")

    def _on_dev_sound_toggle(self):
        p = self.parent()
        while p:
            if hasattr(p, '_toggle_sound_muted'):
                p._toggle_sound_muted()
                self.update_sound_btn_state()
                return
            p = p.parent()
        curr = self.config.get("sound_enabled", True)
        new_val = not curr
        self.config["sound_enabled"] = new_val
        if self.save_config_fn:
            try:
                self.save_config_fn(self.config)
            except Exception:
                pass
        self.update_sound_btn_state()
        self.set_status("🔊 全局声音已开启" if new_val else "🔇 全局已静音 (所有声音关闭)")

    def update_pet_btn_state(self):
        """更新开发模式下桌宠开关按钮图标、Tooltip 与主题样式"""
        if not hasattr(self, 'pet_toggle_btn') or not self.pet_toggle_btn:
            return
        d = getattr(self, 'is_dark', True)
        is_pet_on = self.config.get("pet", {}).get("enabled", self.config.get("pet_enabled", True))
        icon_color = ("#10b981" if is_pet_on else "#a1a1aa") if d else ("#059669" if is_pet_on else "#94a3b8")
        icon_name = "pet" if is_pet_on else "pet-off"
        try:
            from ui.chat_window import load_ui_icon
            self.pet_toggle_btn.setIcon(load_ui_icon(icon_name, icon_color, 14))
        except Exception:
            pass
        tip = "关闭桌宠 (当前已开启，点击隐藏并保存状态)" if is_pet_on else "开启桌宠 (当前已关闭，点击显示并保存状态)"
        self.pet_toggle_btn.setToolTip(tip)
        hover_bg = "#27272a" if d else "#e2e8f0"
        self.pet_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: {hover_bg};
            }}
        """)

    def update_sound_btn_state(self):
        """更新开发模式下声音开关按钮图标、Tooltip 与主题样式"""
        if not hasattr(self, 'sound_btn') or not self.sound_btn:
            return
        d = getattr(self, 'is_dark', True)
        is_sound_on = self.config.get("sound_enabled", True)
        icon_color = "#a1a1aa" if d else "#64748b"
        icon_name = "volume" if is_sound_on else "volume-off"
        try:
            from ui.chat_window import load_ui_icon
            self.sound_btn.setIcon(load_ui_icon(icon_name, icon_color, 13))
        except Exception:
            pass
        tip = "开启全局声音 (玩偶互动、番茄钟提醒与语音回复)" if not is_sound_on else "关闭全局声音 (静音模式)"
        self.sound_btn.setToolTip(tip)
        hover_bg = "#27272a" if d else "#e2e8f0"
        self.sound_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: {hover_bg};
            }}
        """)

    def set_status(self, msg: str):
        """更新开发模式底部状态栏文本"""
        if hasattr(self, 'status_lbl') and self.status_lbl:
            self.status_lbl.setText(f"● {msg}")
            QTimer.singleShot(4000, lambda: self.status_lbl.setText("🟢 智能体 就绪") if hasattr(self, 'status_lbl') and self.status_lbl else None)

    def apply_theme(self, is_dark: bool):
        """
        主题切换：把开发模式视图所有 widget 按 is_dark 刷新样式表。
        历史实现只刷新 4 个 widget（胶囊、tab 关闭、资源管理器底栏、状态栏），
        其余（编辑器、AI 聊天、控制台、菜单、tab 栏、交互终端…）全部写死深色，
        导致切到 light 模式时只有最顶上窗口 chrome 跟随系统，下面整片仍是深色。
        现逐个补齐：先刷新"有 apply_theme() 方法的子 widget"，再强制重写
        写死样式的关键 widget。
        """
        self.is_dark = is_dark

        # ── A. 有自己 apply_theme() 的子组件 ─────────────────
        # 1) 所有打开过的 CodeEditor（编辑器 tab + 内部欢迎页都存在 self.opened_editors）
        try:
            editors = list(getattr(self, 'opened_editors', {}).values())
        except Exception:
            editors = []
        for ed in editors:
            try:
                if hasattr(ed, 'apply_theme'):
                    ed.apply_theme(is_dark)
            except Exception:
                pass

        # 2) PlanDocumentViewerWidget（方案文档预览）
        plan_view = getattr(self, 'plan_viewer', None)
        if plan_view and hasattr(plan_view, 'apply_theme'):
            try:
                plan_view.apply_theme(is_dark)
            except Exception:
                pass

        # 3) 所有 AgentTrajectoryWidget（AI 助手回复卡片）——
        # 真实存储位置：逐一 `self.chat_v_layout.addWidget(turn_widget)`，没字典。
        # 用 findChildren 在 chat_container 里递归找，保证历史回复卡片一并刷新。
        container = getattr(self, 'chat_container', None)
        if container is not None:
            try:
                trajectory_widgets = container.findChildren(AgentTrajectoryWidget)
            except Exception:
                trajectory_widgets = []
            for tw in trajectory_widgets:
                if hasattr(tw, 'apply_theme'):
                    try:
                        tw.apply_theme(is_dark)
                    except Exception:
                        pass

        # ── B. 写死样式的关键 widget：逐个重设样式表 ──────────
        # 4) 开发模式胶囊按钮
        self._update_dev_mode_capsule_style()

        # 5) 资源管理器底栏
        if hasattr(self, 'explorer_bot_bar') and self.explorer_bot_bar:
            self.explorer_bot_bar.setStyleSheet(f"""
                QWidget {{
                    background-color: {'#1e1e1e' if is_dark else '#f1f5f9'};
                    border-top: 1px solid {'#2d2d2d' if is_dark else '#e2e8f0'};
                }}
            """)

        # 6) 状态栏标签
        if hasattr(self, 'status_lbl') and self.status_lbl:
            self.status_lbl.setStyleSheet(
                f"color:{'#a1a1aa' if is_dark else '#64748b'};"
                f"font-size:11px;font-family:'Microsoft YaHei UI';"
            )

        # 7) 桌宠按钮/声音按钮状态重画
        self.update_pet_btn_state()
        self.update_sound_btn_state()

        # 8) 编辑器 Tab 栏（深/浅主题重画）
        self._apply_editor_tab_theme(is_dark)

        # 10) 控制台面板（沙箱终端 + 模型日志）
        self._apply_console_panel_theme(is_dark)

        # 11) 交互终端（顶栏 + 终端控件）
        self._apply_interactive_terminal_theme(is_dark)

        # 12) 菜单栏 / 顶栏快速操作按钮
        self._apply_top_bar_theme(is_dark)

        # 13) AI 聊天底栏 / 输入框（如果存在）
        self._apply_chat_panel_theme(is_dark)

        # 14) 资源管理器（树 + 路径栏）
        self._apply_explorer_theme(is_dark)

        # 14.5) 方案文件顶部 nav_bar（已存在的实例按 is_dark 重新刷）
        d_nav_bg = '#1e2227' if is_dark else '#eff6ff'
        d_nav_border = '#2d333b' if is_dark else '#bfdbfe'
        d_tip_color = '#dcdfe4' if is_dark else '#1f2328'
        d_btn_blue_bg = '#094771' if is_dark else '#3b82f6'
        d_btn_blue_border = '#1f6feb' if is_dark else '#2563eb'
        d_btn_blue_hover = '#1f6feb' if is_dark else '#1d4ed8'
        d_btn_green_bg = '#2e7d32' if is_dark else '#16a34a'
        d_btn_green_hover = '#388e3c' if is_dark else '#15803d'
        for item in list(getattr(self, '_plan_nav_bars', []) or []):
            try:
                nb = item.get('nav_bar')
                if nb is not None:
                    nb.setStyleSheet(
                        f"background-color: {d_nav_bg}; border-bottom: 1px solid {d_nav_border}; padding: 0 8px;"
                    )
                    # QPalette 强制刷 QWidget 背景色（绕开 setStyleSheet 在 PyQt 失效的坑）
                    try:
                        from PyQt5.QtGui import QPalette
                        nb_palette = nb.palette()
                        nb_palette.setColor(QPalette.Window, QColor(d_nav_bg))
                        nb.setAutoFillBackground(True)
                        nb.setPalette(nb_palette)
                    except Exception:
                        pass
                tl = item.get('tip_lbl')
                if tl is not None:
                    tl.setStyleSheet(
                        f"color: {d_tip_color}; font-size: 11.5px;"
                        f" font-family: 'Segoe UI', 'Microsoft YaHei UI'; background: transparent;"
                    )
                br = item.get('btn_return')
                if br is not None:
                    br.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {d_btn_blue_bg}; color: #ffffff; border: 1px solid {d_btn_blue_border};
                            border-radius: 4px; padding: 2px 10px; font-size: 11px; font-weight: bold;
                        }}
                        QPushButton:hover {{ background-color: {d_btn_blue_hover}; }}
                    """)
                bs = item.get('btn_sync')
                if bs is not None:
                    bs.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {d_btn_green_bg}; color: white; border: none;
                            border-radius: 4px; padding: 2px 10px; font-size: 11px; font-weight: bold;
                        }}
                        QPushButton:hover {{ background-color: {d_btn_green_hover}; }}
                    """)
            except Exception:
                pass

        # 15) 主分割条与全局背景
        if hasattr(self, 'splitter') and self.splitter is not None:
            # QSS 无法直接给 QSplitter 上色，常用做法是给 handle 加色
            try:
                self.splitter.setStyleSheet(f"""
                    QSplitter::handle {{
                        background-color: {'#2d2d2d' if is_dark else '#e2e8f0'};
                    }}
                    QSplitter::handle:horizontal {{ width: 1px; }}
                    QSplitter::handle:vertical   {{ height: 1px; }}
                """)
            except Exception:
                pass

        # 16) 把中央 stack 背景也刷成主题色（避免白主题下还有一片深色）
        if hasattr(self, 'central_stack') and self.central_stack is not None:
            try:
                self.central_stack.setStyleSheet(
                    f"QStackedWidget {{ background-color: {'#1e1e1e' if is_dark else '#ffffff'}; }}"
                )
            except Exception:
                pass

        # 17) AI 助手使用的 PlanDocumentViewerWidget 已刷新；扩展/历史 reopen 的亦按上面 plan_view 处理

    # ── 主题刷新辅助方法（apply_theme 内调用） ──
    def _apply_editor_tab_theme(self, is_dark: bool):
        """重写 tab 栏的整套样式（被 apply_theme 复用）"""
        tabs = getattr(self, 'editor_tab_widget', None)
        if not tabs:
            return
        d = is_dark
        tab_bg        = '#1e1e1e' if d else '#ffffff'
        tab_inactive  = '#2d2d2d' if d else '#e2e8f0'
        tab_inactive_fg = '#969696' if d else '#475569'
        tab_active_fg = '#ffffff' if d else '#0f172a'
        tab_hover     = '#383838' if d else '#cbd5e1'
        border_color  = '#252526' if d else '#cbd5e1'
        accent        = '#007acc' if d else '#3b82f6'
        tool_bg       = '#1e1e1e' if d else '#ffffff'

        # close 按钮 SVG 仍沿用原素材（白色描边在浅色背景下有点淡，可以接受）
        p_close_norm = str((Path(__file__).parent.parent / "assets" / "icons" / "ui" / "tab_close.svg").resolve()).replace("\\", "/")
        p_close_hov  = str((Path(__file__).parent.parent / "assets" / "icons" / "ui" / "tab_close_hover.svg").resolve()).replace("\\", "/")

        tabs.setStyleSheet(f"""
            QTabWidget {{
                background-color: {tab_bg};
            }}
            QTabWidget::pane {{
                border: none;
                background-color: {tab_bg};
            }}
            QTabWidget::tab-bar {{
                left: 0px;
            }}
            QTabBar {{
                background-color: {tab_bg};
                border: none;
            }}
            QTabBar::tab {{
                background-color: {tab_inactive};
                color: {tab_inactive_fg};
                padding: 0px 8px 0px 10px;
                border: none;
                border-right: 1px solid {border_color};
                font-size: 12px;
                font-family: 'Segoe UI', 'Microsoft YaHei UI';
                height: 35px;
            }}
            QTabBar::tab:selected {{
                background-color: {tab_bg};
                color: {tab_active_fg};
                border-top: 2px solid {accent};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {tab_hover};
                color: {tab_active_fg};
            }}
            QTabBar::close-button {{
                image: url({p_close_norm});
                subcontrol-position: right;
                subcontrol-origin: padding;
                border-radius: 4px;
                padding: 3px;
            }}
            QTabBar::close-button:hover {{
                image: url({p_close_hov});
                background-color: rgba(255,255,255,0.15);
            }}
            QTabBar QToolButton {{
                background-color: {tool_bg};
                border: none;
                color: {tab_inactive_fg};
                border-radius: 3px;
                padding: 2px;
            }}
            QTabBar QToolButton:hover {{
                background-color: {tab_inactive};
                color: {tab_active_fg};
            }}
        """)


    def _apply_console_panel_theme(self, is_dark: bool):
        """刷新控制台面板：底栏按钮、终端输出、tab 按钮高亮"""
        d = is_dark
        bg_panel = '#181818' if d else '#f8fafc'
        bg_bar   = '#1f1f1f' if d else '#f1f5f9'
        border   = '#2d2d2d' if d else '#e2e8f0'
        fg       = '#ffffff' if d else '#0f172a'
        fg_dim   = '#a1a1aa' if d else '#64748b'
        bg_browser = '#0c0c0c' if d else '#ffffff'

        # 控制台 panel 整体样式（覆盖创建时的硬编码）
        for panel_attr in ('console_panel', 'console_widget'):
            p = getattr(self, panel_attr, None)
            if p is not None:
                try:
                    p.setStyleSheet(f"background-color: {bg_panel}; border-top: 1px solid {border};")
                except Exception:
                    pass

        # 控制台顶栏（创建时是局部变量 bar，找出来重新染色）
        try:
            panel = getattr(self, 'console_panel', None)
            if panel is not None:
                for w in panel.findChildren(QWidget):
                    if w is None or w.parent() is not panel:
                        # 仅 panel 直接子层（bar 是 panel 的直接子 widget）
                        continue
                    if w.metaObject().className() == 'QWidget' and w.layout() is not None and w != panel:
                        # 用 fixedHeight(30) 进一步判断这条是顶栏
                        if w.height() < 60 and w.layout() is not None:
                            try:
                                w.setStyleSheet(
                                    f"background-color: {bg_bar}; border-bottom: 1px solid {border};"
                                    f" padding: 0 8px;"
                                )
                            except Exception:
                                pass
                            break
        except Exception:
            pass

        # 两个 tab 按钮（模型与系统日志 + 交互终端）
        for btn_attr in ('console_tab_btn1', 'console_tab_btn2'):
            btn = getattr(self, btn_attr, None)
            if btn is not None:
                try:
                    btn.setStyleSheet(
                        f"color:{fg}; font-size:11.5px; font-weight:bold;"
                        f" background:transparent; border:none;"
                    )
                except Exception:
                    pass

        # 收起/清空按钮（原代码用局部变量 btn_clear/btn_collapse，没有 self 属性，
        # 这里从 console_panel.findChildren 反向找到所有 QPushButton 重设样式）
        try:
            panel = getattr(self, 'console_panel', None)
            if panel is not None:
                for b in panel.findChildren(QPushButton):
                    if b is None:
                        continue
                    text = b.text().strip()
                    if text in ('清空', '收起', ''):
                        try:
                            b.setStyleSheet(
                                f"color:{fg_dim}; border:1px solid {border}; border-radius:4px;"
                                f" padding:2px 10px; font-size:11px; background:transparent;"
                            )
                        except Exception:
                            pass
                    elif text in ('模型与系统日志', '交互终端'):
                        # 这些是 _create_console_panel 里 console_tab_btn1/2 的等价物；
                        # 真正的 console_tab_btn1/2 上面单独刷；这里跳过
                        pass
        except Exception:
            pass

        # 终端输出 QTextBrowser
        tb = getattr(self, 'terminal_output', None)
        if tb is not None:
            try:
                tb.setStyleSheet(
                    f"QTextBrowser {{ background-color: {bg_browser}; color: {fg};"
                    f" border: none; font-family: 'Cascadia Code', Consolas, monospace;"
                    f" font-size: 13px; padding: 4px 8px; }}"
                )
            except Exception:
                pass

        # 同步触发 tab 高亮（用现有 _switch_console_view / 内部状态）
        cur_idx = 0
        if hasattr(self, 'console_stack') and self.console_stack is not None:
            cur_idx = self.console_stack.currentIndex()
        if hasattr(self, '_switch_console_view'):
            try:
                self._switch_console_view(cur_idx)
            except Exception:
                pass

    def _apply_interactive_terminal_theme(self, is_dark: bool):
        """刷新交互终端：顶栏 + 终端控件 + 所有子 widget。"""
        term = getattr(self, 'interactive_terminal', None)
        if term is None:
            return
        d = is_dark
        bar_bg = '#161b22' if d else '#f1f5f9'
        border = '#2d2d2d' if d else '#e2e8f0'
        fg     = '#79c0ff' if d else '#1d4ed8'
        btn_fg = '#8b949e' if d else '#475569'
        btn_border = '#30363d' if d else '#cbd5e1'
        editor_bg = '#0c0c0c' if d else '#ffffff'
        editor_fg = '#cccccc' if d else '#0f172a'
        selection_bg = '#264f78' if d else '#3b82f6'
        btn_hover_bg = '#21262d' if d else '#e2e8f0'

        # 顶栏：先用 self 属性名找（如果有），否则用 findChildren 找顶栏
        bar = getattr(term, '_top_bar', None) or getattr(term, 'bar', None)
        if bar is None:
            # 兜底：找高度 < 60 的直接子 widget（顶栏特征）
            for w in term.findChildren(QWidget):
                if w.parent() is term and 0 < w.height() < 60 and w.layout() is not None:
                    bar = w
                    break
        if bar is not None:
            try:
                bar.setStyleSheet(
                    f"background-color: {bar_bg}; border-bottom: 1px solid {border};"
                )
            except Exception:
                pass

        # 路径标签
        path_lbl = getattr(term, 'path_lbl', None)
        if path_lbl is not None:
            try:
                path_lbl.setStyleSheet(
                    f"color: {fg}; font-size: 11px; background: transparent;"
                    f" font-family: 'Cascadia Code', Consolas, monospace;"
                )
            except Exception:
                pass

        # 清屏按钮
        btn = getattr(term, 'btn_clear_screen', None)
        if btn is not None:
            try:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent; color: {btn_fg};
                        border: 1px solid {btn_border}; border-radius: 4px;
                        padding: 2px 10px; font-size: 11px;
                    }}
                    QPushButton:hover {{
                        background-color: {btn_hover_bg};
                        color: {'#ffffff' if d else '#0f172a'};
                        border-color: {'#58a6ff' if d else '#3b82f6'};
                    }}
                """)
            except Exception:
                pass

        # 终端控件本身（TerminalEdit）+ 强制刷 viewport
        ed = getattr(term, 'terminal', None)
        if ed is not None:
            try:
                ed.setStyleSheet(f"""
                    QTextEdit {{
                        background-color: {editor_bg};
                        color: {editor_fg};
                        border: none;
                        font-family: 'Cascadia Code', Consolas, 'Courier New', monospace;
                        font-size: 13px;
                        padding: 8px 12px;
                        selection-background-color: {selection_bg};
                    }}
                """)
                # 关键：viewport 也要染色（QTextEdit setStyleSheet 不会穿透到 viewport）
                try:
                    vp = ed.viewport()
                    if vp is not None:
                        vp.setStyleSheet(
                            f"background-color: {editor_bg}; color: {editor_fg};"
                        )
                except Exception:
                    pass
            except Exception:
                pass

    def _apply_top_bar_theme(self, is_dark: bool):
        """顶栏按钮（文件/编辑/查看/终端/扩展）+ QMenu + 菜单弹出面板的主题化。"""
        d = is_dark
        bar_bg = '#1f1f1f' if d else '#f1f5f9'
        border = '#2d2d2d' if d else '#e2e8f0'
        fg     = '#ffffff' if d else '#0f172a'
        fg_dim = '#a1a1aa' if d else '#64748b'
        hover_bg = '#2d2d2d' if d else '#cbd5e1'
        menu_bg  = '#252526' if d else '#ffffff'

        btn_style = f"""
            QPushButton {{
                background: transparent;
                color: {fg};
                border: none;
                padding: 4px 10px;
                font-size: 12.5px;
                font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
                border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {hover_bg}; }}
        """

        # 五个菜单按钮
        for attr in ('file_menu_btn', 'edit_menu_btn', 'view_menu_btn',
                     'term_menu_btn', 'ext_menu_btn', 'test_menu_btn'):
            b = getattr(self, attr, None)
            if b is not None:
                try:
                    b.setStyleSheet(btn_style)
                except Exception:
                    pass

        # 五个 QMenu
        menu_style = f"""
            QMenu {{
                background-color: {menu_bg};
                color: {fg};
                border: 1px solid {border};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 5px 18px;
                border-radius: 3px;
            }}
            QMenu::item:selected {{
                background-color: {'#264f78' if d else '#bfdbfe'};
            }}
            QMenu::separator {{
                height: 1px;
                background: {border};
                margin: 4px 8px;
            }}
        """
        for attr in ('file_menu', 'edit_menu', 'view_menu', 'term_menu', 'ext_menu'):
            m = getattr(self, attr, None)
            if m is not None:
                try:
                    m.setStyleSheet(menu_style)
                except Exception:
                    pass

        # 顶栏 widget（持有菜单按钮的容器）—— 这是 _create_dev_menu_bar 创建的 bar，
        # 写死了 background-color: #1e1e1e，菜单按钮都 transparent 透出它的深色背景。
        # 之前列表里漏了 'menu_bar'，所以这条整条一直深色。
        for attr in ('menu_bar', 'dev_top_bar', 'top_bar', 'menu_bar_widget', 'menu_bar_container'):
            bar = getattr(self, attr, None)
            if bar is not None:
                try:
                    bar.setStyleSheet(
                        f"background-color: {bar_bg}; border-bottom: 1px solid {border};"
                    )
                except Exception:
                    pass
                break

        # QMenuBar（如存在——主菜单栏）
        mb = getattr(self, 'menuBar', None)
        if mb is not None:
            try:
                mb.setStyleSheet(f"""
                    QMenuBar {{
                        background-color: {bar_bg};
                        color: {fg};
                    }}
                    QMenuBar::item:selected {{
                        background-color: {hover_bg};
                    }}
                    QMenu {{
                        background-color: {menu_bg};
                        color: {fg};
                        border: 1px solid {border};
                    }}
                    QMenu::item:selected {{
                        background-color: {'#264f78' if d else '#bfdbfe'};
                    }}
                """)
            except Exception:
                pass

    def _apply_chat_panel_theme(self, is_dark: bool):
        """AI 助手面板按主题刷新：panel 外壳、滚动区、内容容器、顶栏胶囊、
        输入卡 + 输入框、底部按钮组、队列容器等。"""
        d = is_dark

        # === 主色板 ===
        panel_bg = '#1e1e1e' if d else '#ffffff'
        panel_border = '#2d2d2d' if d else '#e2e8f0'
        bar_bg = '#252526' if d else '#f8fafc'
        scroll_bg = '#1e1e1e' if d else '#ffffff'
        container_bg = '#1e1e1e' if d else '#ffffff'
        title_fg = '#ffffff' if d else '#0f172a'
        dim_fg = '#a1a1aa' if d else '#64748b'
        input_bg = '#1e1e1e' if d else '#ffffff'
        input_fg = '#cccccc' if d else '#0f172a'
        input_border = '#3c3c3c' if d else '#cbd5e1'
        accent = '#007acc' if d else '#3b82f6'
        queue_bg = '#16191f' if d else '#f1f5f9'
        queue_border = '#282d37' if d else '#cbd5e1'
        chip_bg = '#21262d' if d else '#e2e8f0'
        chip_fg = '#c9d1d9' if d else '#1f2328'
        chip_border = '#30363d' if d else '#cbd5e1'
        chip_hover = '#30363d' if d else '#cbd5e1'
        combo_bg = '#1f232a' if d else '#ffffff'
        combo_fg = '#61afef' if d else '#1d4ed8'
        combo_border = '#363c46' if d else '#cbd5e1'
        combo_drop_bg = '#252526' if d else '#ffffff'
        combo_sel = '#094771' if d else '#bfdbfe'

        # AI 助手 panel 顶栏
        ai_top_bar = getattr(self, 'ai_top_bar', None)
        if ai_top_bar is not None:
            try:
                ai_top_bar.setStyleSheet(
                    f"background-color: {bar_bg}; border-bottom: 1px solid {panel_border}; padding: 0 8px;"
                )
                try:
                    from PyQt5.QtGui import QPalette
                    ai_palette = ai_top_bar.palette()
                    ai_palette.setColor(QPalette.Window, QColor(bar_bg))
                    ai_top_bar.setAutoFillBackground(True)
                    ai_top_bar.setPalette(ai_palette)
                except Exception:
                    pass
                ai_top_bar.update()
            except Exception:
                pass

        # 单独的"AI 助手"标题
        ai_title = getattr(self, 'ai_panel_title', None)
        if ai_title is not None:
            try:
                ai_title.setStyleSheet(
                    f"color: {title_fg}; font-size: 12px; font-weight: bold; background: transparent; border: none;"
                )
            except Exception:
                pass

        # 角色胶囊
        p_combo = getattr(self, 'persona_combo', None)
        if p_combo is not None:
            try:
                p_combo.setStyleSheet(f"""
                    QComboBox {{
                        background: {'#1f232a' if d else '#ffffff'};
                        color: {'#61afef' if d else '#2563eb'};
                        border: 1px solid {'#363c46' if d else '#cbd5e1'};
                        border-radius: 4px;
                        padding: 0 6px;
                        font-size: 11px;
                        font-weight: bold;
                    }}
                    QComboBox:hover {{ border: 1px solid {accent}; }}
                    QComboBox::drop-down {{ border: none; background: transparent; }}
                    QComboBox QAbstractItemView {{
                        background: {combo_drop_bg};
                        color: {'#cccccc' if d else '#1f2328'};
                        selection-background-color: {combo_sel};
                    }}
                """)
            except Exception:
                pass

        # 模型下拉
        m_combo = getattr(self, 'model_combo', None)
        if m_combo is not None:
            try:
                m_combo.setStyleSheet(f"""
                    QComboBox {{
                        background: {combo_bg};
                        color: {'#cccccc' if d else '#1f2328'};
                        border: 1px solid {combo_border};
                        border-radius: 4px;
                        padding: 0 8px;
                        font-size: 11px;
                    }}
                    QComboBox:hover {{ border: 1px solid {accent}; }}
                    QComboBox::drop-down {{ border: none; background: transparent; }}
                    QComboBox QAbstractItemView {{
                        background: {combo_drop_bg};
                        color: {'#cccccc' if d else '#1f2328'};
                        selection-background-color: {combo_sel};
                    }}
                """)
            except Exception:
                pass

        # 扩展中心按钮
        ext_btn = getattr(self, 'ext_center_btn', None)
        if ext_btn is not None:
            try:
                ext_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {'#2b303c' if d else '#f0fdf4'};
                        color: {'#7ee787' if d else '#16a34a'};
                        border: 1px solid {'#3b4354' if d else '#bbf7d0'};
                        border-radius: 4px;
                        padding: 2px 7px;
                        font-size: 11px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background: {'#3b4354' if d else '#dcfce7'};
                        color: {'#a3f7ad' if d else '#15803d'};
                    }}
                """)
            except Exception:
                pass

        # + 新会话按钮
        btn_new_chat = getattr(self, 'btn_new_chat', None)
        if btn_new_chat is not None:
            try:
                btn_new_chat.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent; color: {'#858585' if d else '#64748b'};
                        border: none; font-size: 14px; font-weight: bold; border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        background-color: {'#333333' if d else '#e2e8f0'};
                        color: {'#ffffff' if d else '#0f172a'};
                    }}
                """)
            except Exception:
                pass

        # 历史会话按钮
        btn_hist = getattr(self, 'btn_history', None)
        if btn_hist is not None:
            try:
                btn_hist.setIcon(create_history_icon('#858585' if d else '#64748b', '#ffffff' if d else '#0f172a'))
                btn_hist.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent; border: none; border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        background-color: {'#333333' if d else '#e2e8f0'};
                    }}
                """)
            except Exception:
                pass

        # === 整个 AI 助手 panel ===
        ai_panel = getattr(self, 'ai_panel', None)
        if ai_panel is not None:
            try:
                ai_panel.setStyleSheet(
                    f"background-color: {panel_bg}; border-left: 1px solid {panel_border};"
                )
            except Exception:
                pass

        # === 滚动区 + 内容容器（让里面 trajectory widget 也接到对应容器底色）===
        chat_scroll = getattr(self, 'chat_scroll', None)
        if chat_scroll is not None:
            try:
                chat_scroll.setStyleSheet(f"""
                    QScrollArea {{
                        border: none;
                        background-color: {scroll_bg};
                    }}
                    QScrollBar:vertical {{
                        background: transparent; width: 8px; margin: 0px;
                    }}
                    QScrollBar::handle:vertical {{
                        background: {'#3e4451' if d else '#cbd5e1'};
                        border-radius: 4px; min-height: 30px;
                    }}
                    QScrollBar::handle:vertical:hover {{
                        background: {'#5c6370' if d else '#94a3b8'};
                    }}
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                        height: 0px; background: transparent;
                    }}
                    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                        background: transparent;
                    }}
                """)
            except Exception:
                pass

        chat_container = getattr(self, 'chat_container', None)
        if chat_container is not None:
            try:
                chat_container.setStyleSheet(f"background-color: {container_bg};")
            except Exception:
                pass

        # === 队列容器（待执行队列） ===
        for attr in ('queue_container',):
            qc = getattr(self, attr, None)
            if qc is not None:
                try:
                    qc.setStyleSheet(f"""
                        QFrame#{qc.objectName() or 'DevQueueContainer'} {{
                            background-color: {queue_bg};
                            border: 1px solid {queue_border};
                            border-radius: 8px;
                        }}
                    """)
                except Exception:
                    pass
        for attr, color in (
            ('queue_header_lbl', dim_fg),
            ('queue_hint_lbl', dim_fg),
        ):
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.setStyleSheet(
                        f"color: {color}; font-size: 11.5px; font-weight: 600;"
                        f" background: transparent; border: none; padding: 0;"
                    )
                except Exception:
                    pass

        # === DevInputCard（输入卡） + 输入框 ===
        if chat_container is not None:
            for card in chat_container.parent().findChildren(QWidget) if hasattr(chat_container.parent(), 'findChildren') else []:
                pass
        # 更直接：找所有名字为 DevInputCard 的 widget
        root = self
        if root is not None:
            try:
                input_cards = root.findChildren(QWidget, 'DevInputCard')
            except Exception:
                input_cards = []
            for c in input_cards:
                try:
                    c.setStyleSheet(f"""
                        QWidget#DevInputCard {{
                            background-color: {panel_bg};
                            border-top: 1px solid {panel_border};
                        }}
                    """)
                except Exception:
                    pass

        ie = getattr(self, 'input_edit', None)
        if ie is not None:
            try:
                ie.setStyleSheet(f"""
                    QPlainTextEdit {{
                        background-color: {input_bg};
                        color: {input_fg};
                        border: 1px solid {input_border};
                        border-radius: 6px;
                        padding: 6px;
                        font-size: 12px;
                        font-family: 'Segoe UI', 'Microsoft YaHei UI';
                    }}
                    QPlainTextEdit:focus {{ border: 1px solid {accent}; }}
                """)
                # QPalette 显式控制 placeholder 颜色（QSS 的 color 不影响 placeholder）
                try:
                    from PyQt5.QtGui import QPalette
                    placeholder_color = '#6b7280' if d else '#64748b'
                    ie_palette = ie.palette()
                    ie_palette.setColor(QPalette.PlaceholderText, QColor(placeholder_color))
                    ie.setPalette(ie_palette)
                except Exception:
                    pass
            except Exception:
                pass

        # === 顶栏 + 角色胶囊 + 模型下拉 + 扩展按钮 + 新对话按钮 + 历史按钮 ===
        for attr in ('persona_combo', 'model_combo'):
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.setStyleSheet(f"""
                        QComboBox {{
                            background: {combo_bg};
                            color: {'#cccccc' if d else '#1f2328'};
                            border: 1px solid {combo_border};
                            border-radius: 4px;
                            padding: 0 6px;
                            font-size: 11px;
                        }}
                        QComboBox QAbstractItemView {{
                            background: {combo_drop_bg};
                            color: {'#cccccc' if d else '#1f2328'};
                            selection-background-color: {combo_sel};
                        }}
                    """)
                except Exception:
                    pass

        ext_btn = getattr(self, 'ext_center_btn', None)
        if ext_btn is not None:
            try:
                ext_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {chip_bg};
                        color: {'#7ee787' if d else '#15803d'};
                        border: 1px solid {chip_border};
                        border-radius: 4px;
                        padding: 2px 7px;
                        font-size: 11px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background: {'#3b4354' if d else '#cbd5e1'};
                        color: {'#a3f7ad' if d else '#166534'};
                    }}
                """)
            except Exception:
                pass

        for attr in ('btn_new_chat', 'btn_history'):
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.setStyleSheet(f"""
                        QPushButton {{
                            background: transparent;
                            color: {dim_fg};
                            border: none;
                            font-size: 14px;
                            font-weight: bold;
                            border-radius: 4px;
                        }}
                        QPushButton:hover {{
                            background-color: {chip_hover};
                            color: {title_fg};
                        }}
                    """)
                except Exception:
                    pass

        # === 按钮 row：上传 / 制定方案 / 代码审查 / 运行测试 / 发送指令 ===
        for attr in ('upload_img_btn', 'btn_plan', 'btn_review', 'btn_test',
                     'btn_run_tests', 'send_btn', 'btn_send', 'send_command_btn',
                     'queue_clear_btn'):
            b = getattr(self, attr, None)
            if b is None:
                continue
            try:
                # 发送按钮保留蓝色实心
                if attr in ('send_btn', 'btn_send', 'send_command_btn'):
                    b.setStyleSheet(f"""
                        QPushButton {{
                            background: {accent};
                            color: white;
                            border: none;
                            border-radius: 6px;
                            padding: 6px 18px;
                            font-weight: bold;
                        }}
                        QPushButton:hover {{ background: {'#2563eb' if d else '#2563eb'}; }}
                    """)
                else:
                    b.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {chip_bg};
                            color: {chip_fg};
                            border: 1px solid {chip_border};
                            border-radius: 4px;
                            padding: 2px 8px;
                            font-size: 12px;
                            font-weight: bold;
                        }}
                        QPushButton:hover {{
                            background-color: {chip_hover};
                            color: {accent};
                            border-color: {accent};
                        }}
                    """)
            except Exception:
                pass

        # === 7) 刷新历史用户/AI 气泡（用户输入 + AI 流式输出卡片）===
        container = getattr(self, 'chat_container', None)
        user_boxes = list(getattr(self, '_user_bubbles', []) or [])
        if container is not None:
            try:
                for fb in container.findChildren(QFrame, "UserChatBubble"):
                    if fb not in user_boxes:
                        user_boxes.append(fb)
            except Exception:
                pass

        for b in user_boxes:
            try:
                self._refresh_user_bubble(b, d)
            except Exception:
                pass
        for b in list(getattr(self, '_ai_bubbles', []) or []):
            try:
                if d:
                    box_bg, box_border = '#252526', '#333842'
                    text_color = '#cccccc'
                else:
                    box_bg, box_border = '#f8fafc', '#cbd5e1'
                    text_color = '#1f2328'
                b.setStyleSheet(f"""
                    QFrame {{
                        background-color: {box_bg};
                        border: 1px solid {box_border};
                        border-radius: 8px;
                        padding: 8px 12px;
                    }}
                """)
                for child in b.findChildren(QLabel):
                    try:
                        child.setStyleSheet(
                            f"color: {text_color}; font-size: 12px;"
                            f" font-family: 'Segoe UI', 'Microsoft YaHei UI'; background: transparent; border: none;"
                        )
                    except Exception:
                        pass
            except Exception:
                pass

    def _apply_explorer_theme(self, is_dark: bool):
        """左侧资源管理器：树 + 路径栏。
        注意：实际 widget 是 QTreeView（QFileSystemModel 驱动），selector 必须用 QTreeView。"""
        d = is_dark
        tree_bg = '#1e1e1e' if d else '#ffffff'
        tree_fg = '#cccccc' if d else '#1f2328'
        border  = '#2d2d2d' if d else '#e2e8f0'
        hover   = '#2a2d2e' if d else '#e2e8f0'
        sel     = '#094771' if d else '#bfdbfe'
        sel_fg  = '#ffffff' if d else '#0f172a'

        # 资源管理器树
        tv = getattr(self, 'tree_view', None)
        if tv is not None:
            try:
                tv.setStyleSheet(f"""
                    QTreeView {{
                        background-color: {tree_bg};
                        color: {tree_fg};
                        border: none;
                        font-family: 'Microsoft YaHei UI', 'Consolas';
                        font-size: 12.5px;
                        alternate-background-color: {'#252526' if d else '#f8fafc'};
                    }}
                    QTreeView::item {{ padding: 3px 4px; }}
                    QTreeView::item:hover {{ background-color: {hover}; }}
                    QTreeView::item:selected {{ background-color: {sel}; color: {sel_fg}; }}
                    QHeaderView::section {{
                        background-color: {tree_bg};
                        color: {tree_fg};
                        border: 0px;
                        border-right: 1px solid {border};
                        padding: 4px;
                    }}
                """)
            except Exception:
                pass

        # 资源管理器 panel 整体（写死在 _create_explorer_panel 的 background-color: #252526）
        explorer_panel = getattr(self, 'explorer_panel', None)
        if explorer_panel is not None:
            try:
                explorer_panel.setStyleSheet(
                    f"background-color: {tree_bg}; border-right: 1px solid {border};"
                )
            except Exception:
                pass

        # 资源管理器顶栏与操作按钮
        header_bg = '#252526' if d else '#f8fafc'
        title_fg = '#bbbbbb' if d else '#0f172a'
        btn_fg = '#858585' if d else '#64748b'
        btn_hover_bg = '#333333' if d else '#e2e8f0'
        btn_hover_fg = '#ffffff' if d else '#0f172a'

        for attr in ('explorer_header', 'explorer_top_bar'):
            bar = getattr(self, attr, None)
            if bar is not None:
                try:
                    bar.setStyleSheet(
                        f"background-color: {header_bg}; border-bottom: 1px solid {border}; padding: 0 8px;"
                    )
                    try:
                        from PyQt5.QtGui import QPalette
                        palette = bar.palette()
                        palette.setColor(QPalette.Window, QColor(header_bg))
                        bar.setAutoFillBackground(True)
                        bar.setPalette(palette)
                    except Exception:
                        pass
                except Exception:
                    pass
                break

        title = getattr(self, 'explorer_title', None)
        if title is not None:
            try:
                title.setStyleSheet(
                    f"color: {title_fg}; font-size: 11px; font-weight: bold; background: transparent; border: none;"
                )
            except Exception:
                pass

        btn_qss = f"""
            QPushButton {{
                background: transparent; color: {btn_fg}; border: none;
                border-radius: 3px; font-size: 13px; font-weight: bold; padding: 0 4px;
            }}
            QPushButton:hover {{ background: {btn_hover_bg}; color: {btn_hover_fg}; }}
        """
        for b_name in ('explorer_btn_new', 'explorer_btn_refresh'):
            btn = getattr(self, b_name, None)
            if btn is not None:
                try:
                    btn.setStyleSheet(btn_qss)
                except Exception:
                    pass

        btn_open = getattr(self, 'explorer_btn_open', None)
        if btn_open is not None:
            try:
                btn_open.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent; color: {btn_fg}; border: none;
                        border-radius: 3px; font-size: 11px; padding: 2px 4px;
                    }}
                    QPushButton:hover {{ background: {btn_hover_bg}; color: {btn_hover_fg}; }}
                """)
            except Exception:
                pass

    # ══════════════════════════════════════════════════════════
    #  2. 左侧资源管理器 (Explorer)
    # ══════════════════════════════════════════════════════════
    def _create_explorer_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(0)
        panel.minimumSizeHint = lambda: QSize(0, 0)
        # 用 self.is_dark 参数化（之前写死深色导致 light 主题下整片深色）
        d = self.is_dark
        panel_bg = '#252526' if d else '#ffffff'
        border_c = '#2d2d2d' if d else '#cbd5e1'
        # 树视图配色（tree_view 也参数化）
        tree_bg = '#252526' if d else '#ffffff'
        tree_fg = '#cccccc' if d else '#1f2328'
        tree_hover = '#2a2d2e' if d else '#e2e8f0'
        tree_sel = '#094771' if d else '#bfdbfe'
        tree_sel_fg = '#ffffff' if d else '#0f172a'
        panel.setStyleSheet(f"background-color: {panel_bg}; border-right: 1px solid {border_c};")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 资源管理器顶条 (内嵌双模式切换胶囊与文件操作图标)
        header = QWidget()
        header.setFixedHeight(35)
        header.setMinimumWidth(0)
        header.minimumSizeHint = lambda: QSize(0, 0)
        # 顶栏也用主题色
        header_bg = '#252526' if d else '#f8fafc'
        header.setStyleSheet(f"background-color: {header_bg}; border-bottom: 1px solid {border_c}; padding: 0 8px;")
        self.explorer_header = header
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(8, 0, 8, 0)
        h_lay.setSpacing(4)

        title = QLabel("资源管理器")
        title_fg = '#bbbbbb' if d else '#0f172a'
        title.setStyleSheet(f"color: {title_fg}; font-size: 11px; font-weight: bold; background: transparent; border: none;")
        self.explorer_title = title
        h_lay.addWidget(title)
        h_lay.addStretch()

        # 顶部模式切换胶囊已常驻窗口全局 TopBar (NovaDesk v4.0 旁)，此处保持资源管理器标题栏清爽整洁
        self.back_work_btn = None

        btn_fg = '#858585' if d else '#64748b'
        btn_hover_bg = '#333333' if d else '#e2e8f0'
        btn_hover_fg = '#ffffff' if d else '#0f172a'
        btn_style = f"""
            QPushButton {{
                background: transparent; color: {btn_fg}; border: none;
                border-radius: 3px; font-size: 12px; padding: 2px 4px;
            }}
            QPushButton:hover {{ background: {btn_hover_bg}; color: {btn_hover_fg}; }}
        """
        btn_new_file = QPushButton("+")
        btn_new_file.setToolTip("新建文件")
        btn_new_file.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {btn_fg}; border: none;
                border-radius: 3px; font-size: 14px; font-weight: bold; padding: 0 4px;
            }}
            QPushButton:hover {{ background: {btn_hover_bg}; color: {btn_hover_fg}; }}
        """)
        btn_new_file.clicked.connect(self._action_new_file)
        self.explorer_btn_new = btn_new_file
        h_lay.addWidget(btn_new_file)

        btn_refresh = QPushButton("↻")
        btn_refresh.setToolTip("刷新目录")
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {btn_fg}; border: none;
                border-radius: 3px; font-size: 13px; font-weight: bold; padding: 0 4px;
            }}
            QPushButton:hover {{ background: {btn_hover_bg}; color: {btn_hover_fg}; }}
        """)
        btn_refresh.clicked.connect(self._refresh_explorer)
        self.explorer_btn_refresh = btn_refresh
        h_lay.addWidget(btn_refresh)

        btn_open = QPushButton("打开")
        btn_open.setToolTip("打开其他文件夹")
        btn_open.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {btn_fg}; border: none;
                border-radius: 3px; font-size: 11px; padding: 2px 4px;
            }}
            QPushButton:hover {{ background: {btn_hover_bg}; color: {btn_hover_fg}; }}
        """)
        btn_open.clicked.connect(self._action_open_folder)
        self.explorer_btn_open = btn_open
        h_lay.addWidget(btn_open)

        lay.addWidget(header)

        # 树形视图
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(self.workspace_root)
        self.file_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)

        self.tree_view = QTreeView()
        self.tree_view.setMinimumWidth(0)
        self.tree_view.minimumSizeHint = lambda: QSize(0, 0)
        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(self.workspace_root))
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(16)
        self.tree_view.hideColumn(1)
        self.tree_view.hideColumn(2)
        self.tree_view.hideColumn(3)

        self.tree_view.setStyleSheet(f"""
            QTreeView {{
                background-color: {tree_bg};
                color: {tree_fg};
                border: none;
                font-family: 'Segoe UI', 'Microsoft YaHei UI';
                font-size: 12.5px;
            }}
            QTreeView::item {{
                padding: 3px 0;
            }}
            QTreeView::item:hover {{
                background-color: {tree_hover};
            }}
            QTreeView::item:selected {{
                background-color: {tree_sel};
                color: {tree_sel_fg};
            }}
        """)
        # QTreeView 的 background 在某些 PyQt 版本不响应 QSS——用 QPalette 强制
        try:
            from PyQt5.QtGui import QPalette
            tv_palette = self.tree_view.palette()
            tv_palette.setColor(QPalette.Base, QColor(tree_bg))
            tv_palette.setColor(QPalette.Text, QColor(tree_fg))
            self.tree_view.setPalette(tv_palette)
        except Exception:
            pass
        self.tree_view.doubleClicked.connect(self._on_tree_item_double_clicked)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._on_tree_context_menu)
        # 默认展开根节点
        root_idx = self.file_model.index(self.workspace_root)
        self.tree_view.expand(root_idx)
        lay.addWidget(self.tree_view, 1)

        # 智能空状态提示卡片 (当所选工作空间目录为空时呈现友好提示与打开入口)
        self.empty_explorer_hint = QWidget()
        eh_lay = QVBoxLayout(self.empty_explorer_hint)
        eh_lay.setContentsMargins(14, 28, 14, 20)
        eh_lay.setSpacing(8)
        eh_lbl = QLabel("📁 当前工作空间为空")
        eh_lbl.setStyleSheet("color: #8b949e; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        eh_lbl.setAlignment(Qt.AlignCenter)
        eh_sub = QLabel("点击上方 ＋ 新建代码文件\n或选择其他包含工程代码的文件夹")
        eh_sub.setStyleSheet("color: #6e7681; font-size: 11px; background: transparent; border: none;")
        eh_sub.setAlignment(Qt.AlignCenter)
        btn_open_ws = QPushButton("📂 打开已有工程文件夹")
        btn_open_ws.setCursor(Qt.PointingHandCursor)
        btn_open_ws.setStyleSheet("""
            QPushButton {
                background-color: #21262d; color: #58a6ff; border: 1px solid #30363d;
                border-radius: 4px; padding: 5px 12px; font-size: 11.5px;
            }
            QPushButton:hover { background-color: #30363d; border-color: #388bfd; }
        """)
        btn_open_ws.clicked.connect(self._action_open_folder)
        eh_lay.addWidget(eh_lbl)
        eh_lay.addWidget(eh_sub)
        eh_lay.addWidget(btn_open_ws, 0, Qt.AlignCenter)
        eh_lay.addStretch()
        self.empty_explorer_hint.setVisible(False)
        lay.addWidget(self.empty_explorer_hint, 1)

        # 底部状态信息与全局开关 (状态提示 / 桌宠开关 / 声音静音开关)
        # 1:1 对齐办公模式侧边栏底栏 (相同视觉规范、22x22 紧凑尺寸、完全状态双向联动)
        bot_bar = QWidget()
        bot_bar.setFixedHeight(30)
        bot_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {'#1e1e1e' if self.is_dark else '#f1f5f9'};
                border-top: 1px solid {'#2d2d2d' if self.is_dark else '#e2e8f0'};
            }}
        """)
        self.explorer_bot_bar = bot_bar
        bot_lay = QHBoxLayout(bot_bar)
        bot_lay.setContentsMargins(8, 2, 8, 2)
        bot_lay.setSpacing(4)

        self.status_lbl = QLabel("🟢 智能体 就绪")
        self.status_lbl.setStyleSheet(f"color:{'#a1a1aa' if self.is_dark else '#64748b'};font-size:11px;font-family:'Microsoft YaHei UI';")
        bot_lay.addWidget(self.status_lbl)
        bot_lay.addStretch()

        # 桌宠显示/隐藏开关 (位置：声音开关左侧，持久化记录状态，与办公模式完全同步)
        self.pet_toggle_btn = QPushButton()
        self.pet_toggle_btn.setFixedSize(22, 22)
        self.pet_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.pet_toggle_btn.setIconSize(QSize(14, 14))
        self.pet_toggle_btn.clicked.connect(self._on_dev_pet_toggle)
        bot_lay.addWidget(self.pet_toggle_btn)
        bot_lay.addSpacing(2)

        # 声音控制开关 (与办公模式完全同步)
        self.sound_btn = QPushButton()
        self.sound_btn.setFixedSize(22, 22)
        self.sound_btn.setCursor(Qt.PointingHandCursor)
        self.sound_btn.setIconSize(QSize(13, 13))
        self.sound_btn.clicked.connect(self._on_dev_sound_toggle)
        bot_lay.addWidget(self.sound_btn)

        self.update_pet_btn_state()
        self.update_sound_btn_state()
        lay.addWidget(bot_bar)

        return panel

    # ══════════════════════════════════════════════════════════
    #  3. 中间多标签代码编辑器
    # ══════════════════════════════════════════════════════════
    def _create_editor_tabs(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.setTabsClosable(True)
        tabs.setMovable(True)
        tabs.setDocumentMode(True)
        tabs.tabCloseRequested.connect(self._close_editor_tab)
        tabs.currentChanged.connect(self._on_tab_changed)

        # 中键点击 Tab 关闭——通过 eventFilter 监听 tabBar
        self._editor_tab_bar = tabs.tabBar()
        self._editor_tab_bar.installEventFilter(self)

        p_close_norm = str((Path(__file__).parent.parent / "assets" / "icons" / "ui" / "tab_close.svg").resolve()).replace("\\", "/")
        p_close_hov  = str((Path(__file__).parent.parent / "assets" / "icons" / "ui" / "tab_close_hover.svg").resolve()).replace("\\", "/")

        tabs.setStyleSheet(f"""
            QTabWidget {{
                background-color: #1e1e1e;
            }}
            QTabWidget::pane {{
                border: none;
                background-color: #1e1e1e;
            }}
            QTabWidget::tab-bar {{
                left: 0px;
            }}
            QTabBar {{
                background-color: #1e1e1e;
                border: none;
            }}
            QTabBar::tab {{
                background-color: #2d2d2d;
                color: #969696;
                padding: 0px 8px 0px 10px;
                border: none;
                border-right: 1px solid #252526;
                font-size: 12px;
                font-family: 'Segoe UI', 'Microsoft YaHei UI';
                height: 35px;
            }}
            QTabBar::tab:selected {{
                background-color: #1e1e1e;
                color: #ffffff;
                border-top: 2px solid #007acc;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: #2a2d2e;
                color: #cccccc;
            }}
            QTabBar::close-button {{
                image: url({p_close_norm});
                subcontrol-position: right;
                subcontrol-origin: padding;
                border-radius: 4px;
                padding: 3px;
            }}
            QTabBar::close-button:hover {{
                image: url({p_close_hov});
                background-color: rgba(255,255,255,0.15);
            }}
            QTabBar QToolButton {{
                background-color: #1e1e1e;
                border: none;
                color: #969696;
                border-radius: 3px;
                padding: 2px;
            }}
            QTabBar QToolButton:hover {{
                background-color: #2d2d2d;
                color: #ffffff;
            }}
        """)

        return tabs

    def _open_welcome_tab(self):
        welcome_ed = CodeEditor(self, is_dark=getattr(self, 'is_dark', True), show_minimap=getattr(self, '_show_minimap', False))
        welcome_text = (
            "# =========================================================\n"
            "#  DeskAI 代码开发工作台 (Dev Agentic IDE)\n"
            "# =========================================================\n"
            "# - 双击左侧资源管理器中的代码或文件即可在此编辑查看\n"
            "# - 支持 Python 语法高亮、行号显示与 Tab 缩进\n"
            "# - 按 Ctrl+S 保存文件，按 F5 一键在底部沙箱运行当前脚本\n"
            "# - 右侧为 AI 智能助手，输入需求自动分析、生成与落地代码\n"
            "# =========================================================\n\n"
            "def hello_developer():\n"
            "    print('欢迎进入现代 Agentic 代码开发模式！')\n"
            "    print('准备好开始构建你的 Python 桌面应用了吗？')\n\n"
            "if __name__ == '__main__':\n"
            "    hello_developer()\n"
        )
        welcome_ed.setPlainText(welcome_text)
        welcome_ed.current_file_path = "welcome.py"
        _ic = get_dev_file_icon("welcome.py", getattr(self, 'is_dark', True))
        self.editor_tab_widget.addTab(welcome_ed, _ic, "welcome.py")
        self.opened_editors["welcome.py"] = welcome_ed

    # ══════════════════════════════════════════════════════════
    #  4. 中间下方抽屉控制台 (沙箱终端 + 模型运行日志)
    # ══════════════════════════════════════════════════════════
    def _create_console_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background-color: #181818; border-top: 1px solid #2d2d2d;")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 控制台顶栏 (只有模型与系统日志 + 交互终端 两页，沙箱终端已合并到日志面板)
        bar = QWidget()
        bar.setFixedHeight(30)
        bar.setStyleSheet("background-color: #1f1f1f; border-bottom: 1px solid #2d2d2d; padding: 0 8px;")
        b_lay = QHBoxLayout(bar)
        b_lay.setContentsMargins(8, 0, 8, 0)
        b_lay.setSpacing(8)

        self.console_tab_btn1 = QPushButton("模型与系统日志")
        self.console_tab_btn1.setCursor(Qt.PointingHandCursor)
        self.console_tab_btn1.setStyleSheet("color:#ffffff; font-size:11.5px; font-weight:bold; background:transparent; border:none;")
        self.console_tab_btn1.clicked.connect(lambda: self._switch_console_view(0))
        b_lay.addWidget(self.console_tab_btn1)

        self.console_tab_btn2 = QPushButton("交互终端")
        self.console_tab_btn2.setCursor(Qt.PointingHandCursor)
        self.console_tab_btn2.setStyleSheet("color:#858585; font-size:11.5px; background:transparent; border:none;")
        self.console_tab_btn2.clicked.connect(lambda: self._switch_console_view(1))
        b_lay.addWidget(self.console_tab_btn2)

        b_lay.addStretch()

        btn_style = """
            QPushButton {
                background: transparent; color: #858585; border: none;
                border-radius: 3px; font-size: 11px; padding: 2px 6px;
            }
            QPushButton:hover { background: #333333; color: #ffffff; }
        """
        btn_clear = QPushButton("清空")
        btn_clear.setStyleSheet(btn_style)
        btn_clear.clicked.connect(self._clear_terminal)
        b_lay.addWidget(btn_clear)

        btn_collapse = QPushButton("收起")
        btn_collapse.setStyleSheet(btn_style)
        btn_collapse.clicked.connect(self._toggle_console)
        b_lay.addWidget(btn_collapse)

        lay.addWidget(bar)

        # 用 QStackedWidget 承载两个面板（沙箱终端已并入日志面板，所以无需单独 widget）
        self.console_stack = QStackedWidget()
        lay.addWidget(self.console_stack, 1)

        # 唯一的输出面板：模型与系统日志 + 沙箱终端（合并显示）
        # 让 self.terminal_output 与 self.log_output 指向同一个 QTextBrowser，
        # 这样全项目 ~50 处 self.terminal_output.append(...) 调用无需修改，
        # 内容会自然落到这一页；切到「模型与系统日志」即可看到一切日志。
        self.terminal_output = QTextBrowser()
        self.terminal_output.setStyleSheet("""
            QTextBrowser {
                background-color: #141414;
                color: #cccccc;
                border: none;
                font-family: 'Cascadia Code', Consolas, 'Courier New', monospace;
                font-size: 12px;
                padding: 8px;
            }
        """)
        self.terminal_output.append("<span style='color:#61afef'>[模型与系统日志 Ready]</span> 沙箱终端输出、模型调用、文件变动、AI 推理等日志均在此处实时滚动。")
        self.log_output = self.terminal_output  # 别名，保持向后兼容
        self.console_stack.addWidget(self.terminal_output)

        # 交互终端 (用户可输入命令)
        self.interactive_terminal = InteractiveTerminalWidget(self.workspace_root, parent=self)
        self.console_stack.addWidget(self.interactive_terminal)

        return panel

    def _switch_console_view(self, index: int):
        if not hasattr(self, 'console_stack'):
            return
        self.console_stack.setCurrentIndex(index)
        active_style = "color:#ffffff; font-size:11.5px; font-weight:bold; background:transparent; border:none;"
        inactive_style = "color:#858585; font-size:11.5px; background:transparent; border:none;"
        btns = [getattr(self, 'console_tab_btn1', None), getattr(self, 'console_tab_btn2', None)]
        for idx, btn in enumerate(btns):
            if btn is None:
                continue
            if idx == index:
                btn.setStyleSheet(active_style)
            else:
                btn.setStyleSheet(inactive_style)
        # 切换到交互终端时自动获取焦点
        if index == 1 and hasattr(self, 'interactive_terminal'):
            self.interactive_terminal.focus_terminal()

    # ══════════════════════════════════════════════════════════
    #  5. 最右侧 AI 助手面板 (Agent Workspace)
    # ══════════════════════════════════════════════════════════
    def _create_ai_agent_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background-color: #1e1e1e; border-left: 1px solid #2d2d2d;")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # AI 助手顶栏
        bar = QWidget()
        bar.setObjectName("DevAiTopBar")  # 让主题切换时能找到
        bar.setFixedHeight(35)
        # 用 self.is_dark 参数化：之前写死深色导致 apply_theme 没把它刷过来
        d = self.is_dark
        bar_bg = '#252526' if d else '#f8fafc'
        bar_border = '#2d2d2d' if d else '#cbd5e1'
        bar.setStyleSheet(f"background-color: {bar_bg}; border-bottom: 1px solid {bar_border}; padding: 0 8px;")
        # QWidget 背景在某些 PyQt 版本不响应 QSS——用 QPalette 强制（首启就对）
        from PyQt5.QtGui import QPalette
        bar_palette = bar.palette()
        bar_palette.setColor(QPalette.Window, QColor(bar_bg))
        bar.setAutoFillBackground(True)
        bar.setPalette(bar_palette)
        self.ai_top_bar = bar
        b_lay = QHBoxLayout(bar)
        b_lay.setContentsMargins(8, 0, 8, 0)
        b_lay.setSpacing(6)

        title = QLabel("AI 助手")
        title.setObjectName("DevAiPanelTitle")  # 让主题切换时能找到
        title.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold;")
        self.ai_panel_title = title
        b_lay.addWidget(title)

        # 开发者身份下拉胶囊选择器 (对齐需求：不同的真实生效开发者身份)
        self.persona_combo = QComboBox()
        self.persona_combo.setFixedHeight(24)
        self.persona_combo.setToolTip("切换大模型开发者身份 (不同身份注入专属架构思维、代码风格与评审规范)")
        self.persona_combo.setStyleSheet("""
            QComboBox {
                background: #1f232a; color: #61afef; border: 1px solid #363c46;
                border-radius: 4px; padding: 0 6px; font-size: 11px; font-weight: bold;
            }
            QComboBox QAbstractItemView {
                background: #252526; color: #cccccc; selection-background-color: #094771;
            }
        """)
        self._refresh_persona_combo()
        self.persona_combo.currentIndexChanged.connect(self._on_persona_changed)
        b_lay.addWidget(self.persona_combo)

        # 扩展中心按钮 (MCP & Skill 统一管理与真实添加)
        self.ext_center_btn = QPushButton("扩展")
        self.ext_center_btn.setToolTip("打开 MCP 连接器与 Skill 技能管理中心")
        self.ext_center_btn.setFixedHeight(24)
        self.ext_center_btn.setStyleSheet("""
            QPushButton {
                background: #2b303c; color: #7ee787; border: 1px solid #3b4354;
                border-radius: 4px; padding: 2px 7px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background: #3b4354; color: #a3f7ad; }
        """)
        self.ext_center_btn.clicked.connect(self._open_extension_manager)
        b_lay.addWidget(self.ext_center_btn)

        b_lay.addStretch()

        # 模型选择器 (严格与系统 models_list 同步)
        self.model_combo = QComboBox()
        self.model_combo.setFixedHeight(24)
        self.model_combo.setStyleSheet("""
            QComboBox {
                background: #333333; color: #cccccc; border: 1px solid #444444;
                border-radius: 4px; padding: 0 8px; font-size: 11px;
            }
            QComboBox QAbstractItemView {
                background: #252526; color: #cccccc; selection-background-color: #094771;
            }
        """)
        self.refresh_models_list()
        self.model_combo.currentIndexChanged.connect(self._on_model_selection_changed)
        b_lay.addWidget(self.model_combo)

        self.btn_new_chat = QPushButton("+")
        self.btn_new_chat.setToolTip("新任务 (New Conversation)")
        self.btn_new_chat.setFixedSize(24, 24)
        self.btn_new_chat.setCursor(Qt.PointingHandCursor)
        self.btn_new_chat.setStyleSheet("""
            QPushButton {
                background: transparent; color: #858585; border: none; font-size: 14px; font-weight: bold; border-radius: 4px;
            }
            QPushButton:hover { background-color: #333333; color: #ffffff; }
        """)
        self.btn_new_chat.clicked.connect(self._action_new_conversation)
        b_lay.addWidget(self.btn_new_chat)

        self.btn_history = QPushButton()
        self.btn_history.setToolTip("Past Conversations (会话历史)")
        self.btn_history.setFixedSize(24, 24)
        self.btn_history.setCursor(Qt.PointingHandCursor)
        self.btn_history.setIcon(create_history_icon("#858585", "#ffffff"))
        self.btn_history.setIconSize(QSize(15, 15))
        self.btn_history.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; border-radius: 4px;
            }
            QPushButton:hover { background-color: #333333; }
        """)
        self.btn_history.clicked.connect(self._open_past_conversations_dialog)
        b_lay.addWidget(self.btn_history)

        lay.addWidget(bar)

        # 消息流展示滚动区
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #3e4451;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5c6370;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: #1e1e1e;")
        self.chat_v_layout = QVBoxLayout(self.chat_container)
        self.chat_v_layout.setContentsMargins(12, 12, 12, 12)
        self.chat_v_layout.setSpacing(10)
        self.chat_v_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_container)
        lay.addWidget(self.chat_scroll, 1)


        # 固底输入框卡片
        input_card = QWidget()
        input_card.setObjectName("DevInputCard")
        input_card.setStyleSheet("""
            QWidget#DevInputCard {
                background-color: #1e1e1e;
                border-top: 1px solid #2d2d2d;
            }
        """)
        ic_lay = QVBoxLayout(input_card)
        ic_lay.setContentsMargins(10, 8, 10, 8)
        ic_lay.setSpacing(6)

        # 排队队列展示容器卡片 (对齐用户需求：新对话在输入框前面排队，等第一个对话处理完了自动发送)
        self.queue_container = QFrame()
        self.queue_container.setObjectName("DevQueueContainer")
        self.queue_container.setStyleSheet("""
            QFrame#DevQueueContainer {
                background-color: #16191f;
                border: 1px solid #282d37;
                border-radius: 8px;
            }
        """)
        self.queue_container_lay = QVBoxLayout(self.queue_container)
        self.queue_container_lay.setContentsMargins(10, 8, 10, 8)
        self.queue_container_lay.setSpacing(6)

        # 排队队列顶栏：标题 + 数量徽章 + 自动流转说明 + 清空按钮
        q_top_row = QHBoxLayout()
        q_top_row.setContentsMargins(0, 0, 0, 0)
        q_top_row.setSpacing(6)

        self.queue_header_lbl = QLabel("待执行队列")
        self.queue_header_lbl.setStyleSheet("""
            QLabel {
                color: #e2e8f0;
                font-size: 11.5px;
                font-weight: 600;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        q_top_row.addWidget(self.queue_header_lbl)

        self.queue_badge_lbl = QLabel("0 条等待中")
        self.queue_badge_lbl.setStyleSheet("""
            QLabel {
                background-color: rgba(56, 139, 253, 0.15);
                color: #58a6ff;
                border: 1px solid rgba(56, 139, 253, 0.3);
                border-radius: 9px;
                padding: 1px 7px;
                font-size: 10px;
                font-weight: 600;
                font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
            }
        """)
        q_top_row.addWidget(self.queue_badge_lbl)

        self.queue_hint_lbl = QLabel("（前序任务完成后将自动连续执行）")
        self.queue_hint_lbl.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 10.5px;
                font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        q_top_row.addWidget(self.queue_hint_lbl)

        q_top_row.addStretch()

        self.queue_clear_btn = QPushButton("清空队列")
        self.queue_clear_btn.setCursor(Qt.PointingHandCursor)
        self.queue_clear_btn.setToolTip("清空所有正在排队的等待需求")
        self.queue_clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8b949e;
                border: 1px solid #30363d;
                border-radius: 4px;
                font-size: 10.5px;
                padding: 2px 8px;
                font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(248, 81, 73, 0.15);
                color: #f85149;
                border-color: rgba(248, 81, 73, 0.35);
            }
        """)
        self.queue_clear_btn.clicked.connect(self._clear_queued_prompts)
        q_top_row.addWidget(self.queue_clear_btn)
        self.queue_container_lay.addLayout(q_top_row)

        # 排队条目列表容器 (可纵向滚动，高度限制最大 96px 防止占满界面)
        self.queue_scroll = QScrollArea()
        self.queue_scroll.setWidgetResizable(True)
        self.queue_scroll.setMaximumHeight(96)
        self.queue_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                border-radius: 2px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #58a6ff;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.queue_items_widget = QWidget()
        self.queue_items_widget.setStyleSheet("background: transparent;")
        self.queue_items_layout = QVBoxLayout(self.queue_items_widget)
        self.queue_items_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_items_layout.setSpacing(4)
        self.queue_scroll.setWidget(self.queue_items_widget)

        self.queue_container_lay.addWidget(self.queue_scroll)
        self.queue_container.setVisible(False)
        ic_lay.addWidget(self.queue_container)

        # 图片附件预览条 (置于输入框上方，支持粘贴、拖拽、上传图片文件)
        self.image_preview_bar = QFrame()
        self.image_preview_bar.setFixedHeight(42)
        self.image_preview_bar.setStyleSheet("""
            QFrame {
                background-color: #1a222d;
                border: 1px solid #1f3a5f;
                border-radius: 6px;
            }
        """)
        img_bar_lay = QHBoxLayout(self.image_preview_bar)
        img_bar_lay.setContentsMargins(8, 3, 8, 3)
        img_bar_lay.setSpacing(8)

        self.img_thumb_lbl = QLabel()
        self.img_thumb_lbl.setFixedSize(34, 34)
        self.img_thumb_lbl.setStyleSheet("border-radius: 4px; background: #161b22; border: 1px solid #30363d;")
        self.img_thumb_lbl.setScaledContents(True)
        img_bar_lay.addWidget(self.img_thumb_lbl)

        self.img_info_lbl = QLabel("未选择图片")
        self.img_info_lbl.setStyleSheet("color: #58a6ff; font-size: 11.5px; font-weight: 500;")
        img_bar_lay.addWidget(self.img_info_lbl, 1)

        self.remove_img_btn = QPushButton("✕ 移除")
        self.remove_img_btn.setCursor(Qt.PointingHandCursor)
        self.remove_img_btn.setStyleSheet("""
            QPushButton {
                background: rgba(248, 81, 73, 0.15);
                color: #ff7b72;
                border: 1px solid rgba(248, 81, 73, 0.3);
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(248, 81, 73, 0.3);
                color: #ffffff;
            }
        """)
        self.remove_img_btn.clicked.connect(self._clear_attached_image)
        img_bar_lay.addWidget(self.remove_img_btn)

        self.image_preview_bar.setVisible(False)
        ic_lay.addWidget(self.image_preview_bar)

        self.input_edit = QPlainTextEdit()
        self.input_edit.setPlaceholderText("向 AI 智能体提出需求（支持直接 Ctrl+V 粘贴图片、拖拽图片或点击下方上传）...")
        self.input_edit.setFixedHeight(70)
        self.input_edit.setAcceptDrops(True)
        # 用 self.is_dark 参数化（之前写死 dark 样式导致 light 主题下背景深字浅——反了；
        # placeholder 颜色通过 QPalette 设置，因为 QSS 的 color 不影响 placeholder）
        d = self.is_dark
        ie_bg = '#1e1e1e' if d else '#ffffff'
        ie_fg = '#cccccc' if d else '#0f172a'
        ie_border = '#3c3c3c' if d else '#cbd5e1'
        ie_focus = '#007acc' if d else '#3b82f6'
        ie_placeholder = '#6b7280' if d else '#64748b'
        self.input_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {ie_bg};
                color: {ie_fg};
                border: 1px solid {ie_border};
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
                font-family: 'Segoe UI', 'Microsoft YaHei UI';
            }}
            QPlainTextEdit:focus {{
                border: 1px solid {ie_focus};
            }}
        """)
        # QPalette 显式控制 placeholder 颜色（绕开 setStyleSheet 限制）
        from PyQt5.QtGui import QPalette
        ie_palette = self.input_edit.palette()
        ie_palette.setColor(QPalette.PlaceholderText, QColor(ie_placeholder))
        self.input_edit.setPalette(ie_palette)
        ic_lay.addWidget(self.input_edit)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(6)

        self.upload_img_btn = QPushButton("＋")
        self.upload_img_btn.setCursor(Qt.PointingHandCursor)
        self.upload_img_btn.setToolTip("添加文件或图片（支持代码、文档、图片）")
        self.upload_img_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #58a6ff;
                border-color: #58a6ff;
            }
        """)
        self.upload_img_btn.clicked.connect(self._select_attachment_dialog)
        btn_row.addWidget(self.upload_img_btn)

        # 快捷功能按钮：[制定方案]、[代码审查]、[运行测试]
        chip_btn_style = """
            QPushButton {
                background-color: #21262d;
                color: #8b949e;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #58a6ff;
                border-color: #388bfd;
            }
            QPushButton:pressed {
                background-color: #161b22;
            }
        """
        self.btn_plan = QPushButton("制定方案")
        self.btn_plan.setCursor(Qt.PointingHandCursor)
        self.btn_plan.setToolTip("组织架构设计并触发 AI 规划落地实施方案 (/plan)")
        self.btn_plan.setStyleSheet(chip_btn_style)
        self.btn_plan.clicked.connect(self._action_plan)
        btn_row.addWidget(self.btn_plan)

        self.btn_review = QPushButton("代码审查")
        self.btn_review.setCursor(Qt.PointingHandCursor)
        self.btn_review.setToolTip("对当前代码执行企业级 5 维度深度审查 (/review)")
        self.btn_review.setStyleSheet(chip_btn_style)
        self.btn_review.clicked.connect(self._action_review)
        btn_row.addWidget(self.btn_review)

        self.btn_run_tests = QPushButton("运行测试")
        self.btn_run_tests.setCursor(Qt.PointingHandCursor)
        self.btn_run_tests.setToolTip("运行当前代码或测试套件，并智能诊断排查报错")
        self.btn_run_tests.setStyleSheet(chip_btn_style)
        self.btn_run_tests.clicked.connect(self._action_run_tests)
        btn_row.addWidget(self.btn_run_tests)

        btn_row.addStretch()

        hint_lbl = QLabel("按 Enter 发送 / Shift+Enter 换行")
        hint_lbl.setStyleSheet("color: #666666; font-size: 10.5px;")
        btn_row.addWidget(hint_lbl)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setVisible(False)
        self.stop_btn.setToolTip("停止当前正在执行的 AI 任务")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d333b; color: #f85149; border: 1px solid #da3633;
                border-radius: 4px; padding: 4px 12px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(248, 81, 73, 0.2); color: #ff7b72; }
        """)
        self.stop_btn.clicked.connect(self._stop_ai_generation)
        btn_row.addWidget(self.stop_btn)

        self.send_btn = QPushButton("发送指令")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c; color: white; border: none;
                border-radius: 4px; padding: 4px 16px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1177bb; }
        """)
        self.send_btn.clicked.connect(self._send_ai_prompt)
        btn_row.addWidget(self.send_btn)

        ic_lay.addLayout(btn_row)
        lay.addWidget(input_card)

        # 绑定事件过滤器（拦截回车发送、Ctrl+V 图片粘贴、拖拽图片）
        self.input_edit.installEventFilter(self)

        return panel

    def eventFilter(self, obj, event):
        # 中键点击 Tab 关闭
        if obj is getattr(self, '_editor_tab_bar', None):
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.MiddleButton:
                idx = obj.tabAt(event.pos())
                if idx >= 0:
                    self._close_editor_tab(idx)
                    return True
        if obj == getattr(self, 'input_edit', None):
            # 1. 拦截键盘事件
            if event.type() == QEvent.KeyPress:
                # 检查回车发送
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    if event.modifiers() & Qt.ShiftModifier:
                        return False  # Shift+Enter 换行
                    else:
                        self._send_ai_prompt()
                        return True
                # 检查粘贴快捷键 (Ctrl+V / Shift+Insert)
                elif event.matches(QKeySequence.Paste) or (event.key() == Qt.Key_V and (event.modifiers() & Qt.ControlModifier)):
                    clipboard = QApplication.clipboard()
                    mime_data = clipboard.mimeData() if clipboard else None
                    if mime_data:
                        # 情况 A: 剪贴板中直接是图片数据 (截图或复制图片)
                        if mime_data.hasImage():
                            img = clipboard.image()
                            if not img.isNull():
                                self._save_and_attach_clipboard_image(img)
                                return True
                        # 情况 B: 剪贴板复制的是本地文件列表
                        elif mime_data.hasUrls():
                            for url in mime_data.urls():
                                l_path = url.toLocalFile()
                                if l_path and Path(l_path).suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'):
                                    self._attach_image(l_path)
                                    return True

            # 2. 拦截拖拽图片进入与释放
            elif event.type() == QEvent.DragEnter:
                mime_data = event.mimeData()
                if mime_data and mime_data.hasUrls():
                    for url in mime_data.urls():
                        l_path = url.toLocalFile()
                        if l_path and Path(l_path).suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'):
                            event.acceptProposedAction()
                            return True
            elif event.type() == QEvent.Drop:
                mime_data = event.mimeData()
                if mime_data and mime_data.hasUrls():
                    for url in mime_data.urls():
                        l_path = url.toLocalFile()
                        if l_path and Path(l_path).suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'):
                            self._attach_image(l_path)
                            event.acceptProposedAction()
                            return True

        return super().eventFilter(obj, event)

    def _save_and_attach_clipboard_image(self, qimage: QImage):
        """将剪贴板捕获的位图暂存至工作空间缓存目录并附加到当前对话"""
        try:
            cache_dir = Path(self.workspace_root) / ".desk_cache" / "uploads"
            cache_dir.mkdir(parents=True, exist_ok=True)
            fname = f"paste_{int(time.time()*1000)}.png"
            target_path = cache_dir / fname
            qimage.save(str(target_path), "PNG")
            self._attach_image(str(target_path))
            self.terminal_output.append(
                f"<span style='color:#58a6ff'>📷 <b>[已粘贴图片]</b> 成功从剪贴板捕获并暂存: <code>{fname}</code></span>"
            )
        except Exception as e:
            self.terminal_output.append(f"<span style='color:#e06c75'>❌ 保存剪贴板图片异常: {e}</span>")

    def _attach_image(self, file_path: str):
        """挂载图片并刷新输入框上方预览栏"""
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return
        self._attached_image_path = str(p)
        
        pix = QPixmap(str(p))
        if not pix.isNull():
            self.img_thumb_lbl.setPixmap(pix.scaled(34, 34, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        
        sz_bytes = p.stat().st_size
        sz_str = f"{sz_bytes / 1024:.1f} KB" if sz_bytes >= 1024 else f"{sz_bytes} B"
        self.img_info_lbl.setText(f"🖼️ {p.name} ({sz_str})")
        self.image_preview_bar.setVisible(True)

    def _clear_attached_image(self):
        """清空当前挂载的图片或文件附件"""
        self._attached_image_path = None
        self._attached_file_path = None
        if hasattr(self, 'image_preview_bar'):
            self.image_preview_bar.setVisible(False)

    def _select_attachment_dialog(self):
        """打开文件选择器添加文件或图片（支持代码、文档、图片）"""
        fpath, _ = QFileDialog.getOpenFileName(
            self, "选择要添加的文件或图片", self.workspace_root,
            "所有支持文件 (*.py *.js *.ts *.html *.css *.json *.md *.txt *.png *.jpg *.jpeg *.webp);;代码与文本文件 (*.py *.js *.ts *.html *.css *.json *.md *.txt *.yml *.yaml *.sql);;图片文件 (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;所有文件 (*.*)"
        )
        if not fpath:
            return
        p = Path(fpath)
        ext = p.suffix.lower()
        if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]:
            self._attach_image(fpath)
        else:
            self._attach_file(fpath)

    def _attach_file(self, file_path: str):
        """挂载代码或文本文件附件，并在输入框上方展示附件条，同时联动打开文件"""
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return
        self._attached_file_path = str(p.resolve())
        self._attached_image_path = None

        try:
            rel = str(p.resolve().relative_to(Path(self.workspace_root).resolve()))
        except Exception:
            rel = p.name

        sz_bytes = p.stat().st_size
        sz_str = f"{sz_bytes / 1024:.1f} KB" if sz_bytes >= 1024 else f"{sz_bytes} B"

        self.img_thumb_lbl.setText("📄")
        self.img_thumb_lbl.setStyleSheet("border-radius: 4px; background: #161b22; border: 1px solid #30363d; font-size: 16px; color: #58a6ff;")
        self.img_info_lbl.setText(f"📄 {p.name} <span style='color:#8b949e;'>({rel}, {sz_str})</span>")
        self.image_preview_bar.setVisible(True)

        # 智能在输入框追加 @rel 引用
        cur_text = self.input_edit.toPlainText().strip()
        ref_tag = f"@{rel}"
        if ref_tag not in cur_text:
            new_text = f"{cur_text} {ref_tag}".strip() if cur_text else f"{ref_tag} "
            self.input_edit.setPlainText(new_text)

        # 联动在中间编辑器打开该文件
        self.open_file_in_editor(file_path)
        self.terminal_output.append(f"<span style='color:#58a6ff'>📄 <b>[已添加文件]</b> 成功将 <code>{rel}</code> 添加至上下文并打开</span>")

    def _select_image_dialog(self):
        """兼容旧调用，转发至统一的添加文件/图片选择器"""
        self._select_attachment_dialog()

    # ══════════════════════════════════════════════════════════
    #  业务逻辑：文件打开、编辑与保存
    # ══════════════════════════════════════════════════════════
    def open_file_in_editor(self, file_path: str, line_no: int = 1):
        target_line = int(line_no) if line_no else 1
        # 支持 path:line 形式的字符串 (例如从探索分析点击发来的 "ui/code_editor.py:1800")
        if ":" in file_path:
            parts = file_path.rsplit(":", 1)
            if len(parts) == 2 and parts[1].isdigit():
                file_path = parts[0]
                target_line = int(parts[1])

        p = Path(file_path)
        if not p.is_absolute():
            p = (Path(self.workspace_root) / p).resolve()
        else:
            p = p.resolve()

        if not p.exists() or not p.is_file():
            return

        # 智能工作空间跟随：如果当前工作空间为空，而打开的文件在包含代码的工程文件夹中，自动将资源管理器切换到该文件夹
        p_parent = p.parent
        p_parent_has_files = False
        try:
            p_parent_has_files = any(not it.name.startswith(".") for it in p_parent.iterdir())
        except Exception:
            pass
            
        cur_ws_has_files = False
        try:
            cur_ws_has_files = any(not it.name.startswith(".") for it in Path(self.workspace_root).iterdir())
        except Exception:
            pass

        if (not cur_ws_has_files) and p_parent_has_files:
            self.set_workspace_root(str(p_parent), save_state=False)

        # 若已打开，直接切换到对应的 Tab 并平滑定位到指定行
        p_str = str(p)
        if p_str in self.opened_editors:
            for idx in range(self.editor_tab_widget.count()):
                w = self.editor_tab_widget.widget(idx)
                if (hasattr(w, 'current_file_path') and w.current_file_path == p_str) or (getattr(w, '_wrapped_file_path', '') == p_str):
                    self.editor_tab_widget.setCurrentIndex(idx)
                    ed = getattr(w, '_inner_editor', w)
                    if target_line > 1 and hasattr(ed, 'jump_to_line'):
                        ed.jump_to_line(target_line)
                    if not getattr(self, '_is_restoring_session', False):
                        self._save_dev_workspace_session_state()
                    return

        # 读取内容并新建编辑器
        try:
            content = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = p.read_text(encoding="gbk", errors="ignore")
            except Exception as e:
                self.terminal_output.append(f"❌ 读取文件失败: {e}")
                return

        editor = CodeEditor(self, is_dark=getattr(self, 'is_dark', True), show_minimap=getattr(self, '_show_minimap', False))
        editor.setPlainText(content)
        editor.current_file_path = p_str
        editor.is_modified = False

        tab_title = p.name

        # 特别优化：若打开的是方案文件（implementation_plan.md 或 plan_*.md），注入顶部返回横幅
        import fnmatch
        _is_plan_file = (p.name == "implementation_plan.md" or fnmatch.fnmatch(p.name, "plan_*.md"))
        if _is_plan_file:
            container = QWidget()
            c_lay = QVBoxLayout(container)
            c_lay.setContentsMargins(0, 0, 0, 0)
            c_lay.setSpacing(0)

            # 顶部快捷导航栏（用 self.is_dark 参数化：之前写死深色导致 light 主题下仍是深色）
            d = self.is_dark
            nav_bg = '#1e2227' if d else '#eff6ff'
            nav_border = '#2d333b' if d else '#bfdbfe'
            tip_color = '#dcdfe4' if d else '#1f2328'
            btn_blue_bg = '#094771' if d else '#3b82f6'
            btn_blue_border = '#1f6feb' if d else '#2563eb'
            btn_blue_hover = '#1f6feb' if d else '#1d4ed8'
            btn_green_bg = '#2e7d32' if d else '#16a34a'
            btn_green_hover = '#388e3c' if d else '#15803d'

            nav_bar = QFrame()
            nav_bar.setFixedHeight(34)
            nav_bar.setStyleSheet(f"background-color: {nav_bg}; border-bottom: 1px solid {nav_border}; padding: 0 8px;")
            n_lay = QHBoxLayout(nav_bar)
            n_lay.setContentsMargins(8, 0, 8, 0)
            n_lay.setSpacing(10)

            tip_lbl = QLabel(f"📋 <b>{p.name}</b> 实施方案源码编辑模式")
            tip_lbl.setStyleSheet(f"color: {tip_color}; font-size: 11.5px; font-family: 'Segoe UI', 'Microsoft YaHei UI'; background: transparent;")
            n_lay.addWidget(tip_lbl)
            n_lay.addStretch()

            btn_return_plan = QPushButton("👁️ 返回方案渲染视图")
            btn_return_plan.setCursor(Qt.PointingHandCursor)
            btn_return_plan.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_blue_bg}; color: #ffffff; border: 1px solid {btn_blue_border};
                    border-radius: 4px; padding: 2px 10px; font-size: 11px; font-weight: bold;
                }}
                QPushButton:hover {{ background-color: {btn_blue_hover}; }}
            """)
            btn_return_plan.clicked.connect(lambda: self._switch_to_plan_preview_tab(editor))
            n_lay.addWidget(btn_return_plan)

            btn_sync_save = QPushButton("💾 保存并同步方案")
            btn_sync_save.setCursor(Qt.PointingHandCursor)
            btn_sync_save.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_green_bg}; color: white; border: none;
                    border-radius: 4px; padding: 2px 10px; font-size: 11px; font-weight: bold;
                }}
                QPushButton:hover {{ background-color: {btn_green_hover}; }}
            """)
            def _on_sync_save():
                try:
                    p.write_text(editor.toPlainText(), encoding="utf-8")
                    editor.is_modified = False
                    self._switch_to_plan_preview_tab(editor)
                    self.terminal_output.append("💾 方案内容已保存并同步至渲染视图！")
                except Exception as ex:
                    self.terminal_output.append(f"⚠️ 保存方案异常: {ex}")
            btn_sync_save.clicked.connect(_on_sync_save)
            n_lay.addWidget(btn_sync_save)

            # 把 nav_bar 各 widget 存到 self，让 apply_theme 在运行时主题切换时也能统一刷
            if not hasattr(self, '_plan_nav_bars') or self._plan_nav_bars is None:
                self._plan_nav_bars = []
            self._plan_nav_bars.append({
                'nav_bar': nav_bar, 'tip_lbl': tip_lbl,
                'btn_return': btn_return_plan, 'btn_sync': btn_sync_save,
            })

            c_lay.addWidget(nav_bar)
            c_lay.addWidget(editor, 1)

            container._inner_editor = editor
            container._wrapped_file_path = p_str
            container.current_file_path = p_str

            _ic = get_dev_file_icon(p_str, getattr(self, 'is_dark', True))
            idx = self.editor_tab_widget.addTab(container, _ic, tab_title)
            self.editor_tab_widget.setCurrentIndex(idx)
            self.opened_editors[p_str] = editor
        else:
            _ic = get_dev_file_icon(p_str, getattr(self, 'is_dark', True))
            idx = self.editor_tab_widget.addTab(editor, _ic, tab_title)
            self.editor_tab_widget.setCurrentIndex(idx)
            self.opened_editors[p_str] = editor

        if target_line > 1 and hasattr(editor, 'jump_to_line'):
            editor.jump_to_line(target_line)
        self.terminal_output.append(f"📄 已在编辑器中打开: {p.name}")
        if not getattr(self, '_is_restoring_session', False):
            self._save_dev_workspace_session_state()

    def _switch_to_plan_preview_tab(self, editor=None):
        """从方案代码编辑模式平滑切回方案渲染视图 Tab"""
        updated_content = editor.toPlainText() if editor else ""
        current_ed_path = getattr(editor, 'current_file_path', '') if editor else ""
        plan_tab_idx = -1
        plan_widget = None
        for idx in range(self.editor_tab_widget.count()):
            w = self.editor_tab_widget.widget(idx)
            if isinstance(w, PlanDocumentViewerWidget):
                if current_ed_path and getattr(w, 'plan_file_path', '') == current_ed_path:
                    plan_tab_idx = idx
                    plan_widget = w
                    break
                elif plan_tab_idx < 0:
                    plan_tab_idx = idx
                    plan_widget = w

        if plan_widget and plan_tab_idx >= 0:
            if updated_content:
                plan_widget.set_plan_content(updated_content)
            self.editor_tab_widget.setCurrentIndex(plan_tab_idx)
        else:
            plan_path = current_ed_path or getattr(self, '_current_plan_file_path', '') or str(Path(self.workspace_root) / "implementation_plan.md")
            if not updated_content and Path(plan_path).exists():
                try:
                    updated_content = Path(plan_path).read_text(encoding="utf-8")
                except Exception:
                    pass
            self.open_plan_preview(updated_content, plan_path)

    def open_diff_viewer(self, file_path: str):
        """在中间多标签主屏幕打开红绿代码差异比对视图 (Diff Viewer) 并自动平滑定位跳转到变更行"""
        p = Path(file_path)
        from core.file_diff_tracker import FileDiffTracker
        tracker = FileDiffTracker.get_instance()

        rec = None
        if p.is_absolute():
            rec = tracker.get_record(str(p.resolve()))

        if not rec:
            for r in tracker.get_recent_records(50):
                if r.rel_path == file_path or Path(r.abs_path).resolve() == p.resolve() or Path(r.rel_path).name == p.name:
                    rec = r
                    p = Path(r.abs_path)
                    break

        if not rec:
            if not p.is_absolute():
                p = (Path(self.workspace_root) / p).resolve()
            rec = tracker.get_record(str(p))

        if not rec and p.exists():
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
                rec = tracker.record_change(
                    rel_path=p.name,
                    abs_path=str(p.resolve()),
                    before_content="",
                    after_content=content,
                    session_id=self._current_session_id or ""
                )
            except Exception as e:
                print(f"[open_diff_viewer] synthesize record failed: {e}")

        # 防御性刷新：如果文件在记录生成后被外部/其他流程修改过，
        # 重新从磁盘读取当前真实内容，避免 Diff 视图显示过旧或转义残留文本。
        if rec and p.exists():
            try:
                current_content = p.read_text(encoding="utf-8", errors="replace")
                if current_content != rec.after_content:
                    rec = tracker.record_change(
                        rel_path=rec.rel_path,
                        abs_path=str(p.resolve()),
                        before_content="",
                        after_content=current_content,
                        session_id=self._current_session_id or ""
                    )
            except Exception:
                pass

        tab_title = f"Diff: {p.name}"
        # 检查是否已打开相同对比 Tab
        for idx in range(self.editor_tab_widget.count()):
            w = self.editor_tab_widget.widget(idx)
            if isinstance(w, DiffViewerWidget) and (getattr(w, 'file_path', '') == str(p) or (rec and w.rec and w.rec.abs_path == rec.abs_path)):
                self.editor_tab_widget.setCurrentIndex(idx)
                w.rec = rec or w.rec
                w._render_diff()
                self._sync_editor_jump(p, rec)
                return

        diff_w = DiffViewerWidget(rec=rec, file_path=str(p), dev_view=self)
        idx = self.editor_tab_widget.addTab(diff_w, tab_title)
        self.editor_tab_widget.setCurrentIndex(idx)
        self.terminal_output.append(f"🔍 已在主屏幕呈现代码变动详细 Diff 对比并定位: <code>{p.name}</code>")
        self._sync_editor_jump(p, rec)

    def _sync_editor_jump(self, p: Path, rec):
        """如果该文件同时在代码编辑器打开，同步跳转光标并高亮定位到变更行"""
        p_str = str(p)
        if p_str in self.opened_editors and rec:
            try:
                first_lineno = 1
                for b in rec.get_diff_blocks():
                    if b.get("type") in ["add", "del"]:
                        first_lineno = int(b.get("new_no") or b.get("old_no") or 1)
                        break
                self.opened_editors[p_str].jump_to_line(first_lineno)
            except Exception:
                pass

    def _get_plans_dir(self) -> Path:
        """获取当前工作空间下的方案独立存储目录 (plans/)，确保目录存在"""
        plans_dir = Path(self.workspace_root) / "plans"
        try:
            plans_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[DevModeView] 创建方案存储目录失败: {e}")
        return plans_dir

    def _organize_and_cleanup_plans(self, days: Optional[int] = None):
        """
        方案文件整理与过期历史清理引擎：
        1. 确保 plans/ 独立方案文件夹存在；
        2. 将散落在工作空间根目录下的历史 plan_*.md（以及旧 implementation_plan.md）自动整理迁移归拢至 plans/ 文件夹；
        3. 扫描 plans/ 目录（及根目录），物理删除超过指定天数（默认 25 天）的过期方案文件；
        4. 联动 MemoryManager 自动清理超过 25 天的过期会话与消息历史记录。
        """
        if days is None:
            days = self.config.get("behavior", {}).get("history_retention_days") or self.config.get("history_retention_days", 25)
        try:
            days = int(days)
        except Exception:
            days = 25

        cutoff_sec = time.time() - (days * 86400)
        plans_dir = self._get_plans_dir()
        ws_root = Path(self.workspace_root)

        moved_count = 0
        cleaned_files_count = 0

        # 1. 扫描根目录下的 plan_*.md 和 implementation_plan.md
        try:
            for p in list(ws_root.glob("plan_*.md")):
                if not p.is_file():
                    continue
                # 若已超过指定保留天数，直接清理
                try:
                    if p.stat().st_mtime < cutoff_sec:
                        p.unlink()
                        cleaned_files_count += 1
                        continue
                except Exception:
                    pass
                # 未过期，迁移归类至 plans/ 独立目录
                try:
                    target = plans_dir / p.name
                    if target.resolve() != p.resolve():
                        if target.exists():
                            if p.stat().st_mtime > target.stat().st_mtime:
                                shutil.move(str(p), str(target))
                            else:
                                p.unlink()
                        else:
                            shutil.move(str(p), str(target))
                        moved_count += 1
                except Exception as e:
                    print(f"[DevModeView] 迁移方案文件 {p.name} 失败: {e}")

            # 根目录下若有旧 implementation_plan.md 也进行归纳迁移或清理
            root_impl = ws_root / "implementation_plan.md"
            if root_impl.is_file():
                try:
                    if root_impl.stat().st_mtime < cutoff_sec:
                        root_impl.unlink()
                        cleaned_files_count += 1
                    else:
                        target_impl = plans_dir / "implementation_plan.md"
                        if not target_impl.exists():
                            shutil.move(str(root_impl), str(target_impl))
                            moved_count += 1
                except Exception:
                    pass
        except Exception as e:
            print(f"[DevModeView] 整理根目录方案文件异常: {e}")

        # 2. 扫描 plans/ 目录下的过期方案文件
        try:
            if plans_dir.exists():
                for p in list(plans_dir.glob("plan_*.md")):
                    if not p.is_file():
                        continue
                    try:
                        if p.stat().st_mtime < cutoff_sec:
                            p.unlink()
                            cleaned_files_count += 1
                    except Exception:
                        pass
                target_impl = plans_dir / "implementation_plan.md"
                if target_impl.is_file():
                    try:
                        if target_impl.stat().st_mtime < cutoff_sec:
                            target_impl.unlink()
                            cleaned_files_count += 1
                    except Exception:
                        pass
        except Exception as e:
            print(f"[DevModeView] 清理过期方案文档异常: {e}")

        # 3. 联动 MemoryManager 清理超过 25 天的历史会话与消息
        db_clean = {}
        if getattr(self, "memory", None) and hasattr(self.memory, "cleanup_expired_history"):
            try:
                db_clean = self.memory.cleanup_expired_history(days=days)
            except Exception as e:
                print(f"[DevModeView] 清理过期历史会话异常: {e}")

        # 4. 若有移动或清理，刷新文件树
        if moved_count > 0 or cleaned_files_count > 0:
            try:
                self._refresh_explorer()
            except Exception:
                pass

        msg_parts = []
        if moved_count > 0:
            msg_parts.append(f"已自动归类 {moved_count} 份历史方案至 plans/ 独立目录")
        if cleaned_files_count > 0:
            msg_parts.append(f"已自动清理 {cleaned_files_count} 份超过 {days} 天的过期方案文档")
        if db_clean.get("deleted_sessions", 0) > 0:
            msg_parts.append(f"已清理 {db_clean['deleted_sessions']} 个超过 {days} 天的历史会话")

        if msg_parts and hasattr(self, "terminal_output") and self.terminal_output:
            self.terminal_output.append(
                f"<span style='color: #79c0ff;'>🧹 <b>[生命周期整理]</b> {'，'.join(msg_parts)}。</span>"
            )

    def open_plan_preview(self, plan_content: str = "", plan_file_path: Optional[str] = None):
        """在中间多标签主屏幕打开并预览技术落地实施方案文档 (支持多方案互不覆盖，统一部署在 plans/ 独立目录下)"""
        if not plan_file_path:
            plan_file_path = getattr(self, '_current_plan_file_path', '') or str(self._get_plans_dir() / "implementation_plan.md")

        plan_content = sanitize_tool_json_artifacts(strip_emojis(plan_content))

        # 若传入内容，先落盘物理文件以便用户随时查阅
        if plan_content and plan_content.strip():
            try:
                p_obj = Path(plan_file_path)
                p_obj.parent.mkdir(parents=True, exist_ok=True)
                p_obj.write_text(plan_content, encoding="utf-8")
                # 同步记录至 FileDiffTracker
                try:
                    from core.file_diff_tracker import FileDiffTracker
                    tracker = FileDiffTracker.get_instance()
                    abs_p = str(p_obj.resolve())
                    if not tracker.get_record(abs_p):
                        try:
                            rel_p = str(p_obj.relative_to(Path(self.workspace_root))).replace("\\", "/")
                        except Exception:
                            rel_p = p_obj.name
                        tracker.record_change(
                            rel_path=rel_p,
                            abs_path=abs_p,
                            before_content="",
                            after_content=plan_content,
                            session_id=self._current_session_id or ""
                        )
                except Exception:
                    pass
            except Exception as e:
                print(f"[DevModeView] 保存方案文档 {Path(plan_file_path).name} 失败: {e}")
        elif Path(plan_file_path).exists():
            try:
                plan_content = sanitize_tool_json_artifacts(strip_emojis(Path(plan_file_path).read_text(encoding="utf-8", errors="replace")))
            except Exception:
                pass

        tab_title = f"方案: {Path(plan_file_path).name}"
        # 检查是否已打开相同 Plan Tab，若已存在则刷新内容并切到该页
        for idx in range(self.editor_tab_widget.count()):
            w = self.editor_tab_widget.widget(idx)
            if isinstance(w, PlanDocumentViewerWidget) and getattr(w, 'plan_file_path', None) == plan_file_path:
                self.editor_tab_widget.setCurrentIndex(idx)
                w.set_plan_content(plan_content, plan_file_path)
                self.editor_tab_widget.setTabText(idx, tab_title)
                self.terminal_output.append(f"📋 已在中间主屏幕切换至【{Path(plan_file_path).name}】方案文档预览")
                return

        plan_w = PlanDocumentViewerWidget(plan_content=plan_content, plan_file_path=plan_file_path, dev_view=self)
        idx = self.editor_tab_widget.addTab(plan_w, tab_title)
        self.editor_tab_widget.setCurrentIndex(idx)
        self.terminal_output.append(f"📋 已在中间主屏幕呈现【{Path(plan_file_path).name}】方案文档预览")

    def _close_editor_tab(self, index: int):
        w = self.editor_tab_widget.widget(index)
        if hasattr(w, 'current_file_path'):
            self.opened_editors.pop(w.current_file_path, None)
        elif hasattr(w, '_wrapped_file_path'):
            self.opened_editors.pop(w._wrapped_file_path, None)
        elif hasattr(w, 'file_path'):
            self.opened_editors.pop(w.file_path, None)
        # 关闭方案文档视图时，自动解除审批门控并恢复队列
        if isinstance(w, PlanDocumentViewerWidget):
            self._pending_plan_approval = False
            if self._dev_message_queue and not self._is_generating:
                QTimer.singleShot(120, self._dequeue_and_run)
        self.editor_tab_widget.removeTab(index)
        if not getattr(self, '_is_restoring_session', False):
            self._save_dev_workspace_session_state()

    def _on_tab_changed(self, idx: int):
        if not getattr(self, '_is_restoring_session', False):
            self._save_dev_workspace_session_state()

    def _dequeue_and_run(self):
        """小工具方法：当方案关闭或门控解除时，从队列取出下一条任务执行"""
        if not self._dev_message_queue or self._is_generating:
            return
        next_item = self._dev_message_queue.pop(0)
        if isinstance(next_item, tuple):
            if len(next_item) == 3:
                next_text, next_img, next_file = next_item
            elif len(next_item) == 2:
                next_text, next_img = next_item
                next_file = None
            else:
                next_text, next_img, next_file = next_item[0], None, None
        else:
            next_text, next_img, next_file = next_item, None, None
        self._update_queue_ui()
        q_rem = len(self._dev_message_queue)
        self.terminal_output.append(
            f"<span style='color:#98c379'><b>[队列恢复]</b> 方案已处理，自动启动排队的下一条指令（队列剩余 {q_rem} 条）</span>"
        )
        self._execute_ai_prompt(next_text, image_path=next_img, file_path=next_file)

    def _get_current_editor(self) -> Optional[CodeEditor]:
        w = self.editor_tab_widget.currentWidget()
        if isinstance(w, CodeEditor):
            return w
        return getattr(w, '_inner_editor', None)

    def _action_save_current(self):
        ed = self._get_current_editor()
        if not ed or not ed.current_file_path:
            return
        try:
            p = Path(ed.current_file_path)
            p.write_text(ed.toPlainText(), encoding="utf-8")
            ed.is_modified = False
            self.terminal_output.append(f"💾 文件保存成功: {p.name}")
            if not getattr(self, '_is_restoring_session', False):
                self._save_dev_workspace_session_state()
        except Exception as e:
            self.terminal_output.append(f"❌ 保存失败: {e}")

    def _action_close_current_tab(self):
        idx = self.editor_tab_widget.currentIndex()
        if idx >= 0:
            self._close_editor_tab(idx)

    def _action_new_file(self):
        file_name, ok = QFileDialog.getSaveFileName(self, "新建文件", self.workspace_root, "All Files (*)")
        if ok and file_name:
            Path(file_name).touch()
            self._refresh_explorer()
            self.open_file_in_editor(file_name)

    def _action_open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "打开文件", self.workspace_root, "All Files (*)")
        if file_path:
            self.open_file_in_editor(file_path)

    def _action_open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "打开文件夹", self.workspace_root)
        if folder_path:
            self.set_workspace_root(folder_path, save_state=True)

    def set_workspace_root(self, folder_path: str, save_state: bool = True):
        self.workspace_root = str(Path(folder_path).resolve())
        self.file_model.setRootPath(self.workspace_root)
        root_idx = self.file_model.index(self.workspace_root)
        self.tree_view.setRootIndex(root_idx)
        self.tree_view.expand(root_idx)
        if hasattr(self, 'ws_path_lbl') and self.ws_path_lbl:
            self.ws_path_lbl.setText(f"{Path(self.workspace_root).name}")
            self.ws_path_lbl.setToolTip(self.workspace_root)
        if hasattr(self, 'terminal_output') and self.terminal_output:
            self.terminal_output.append(f"📂 工作空间已切换为: {self.workspace_root}")
        self._update_explorer_empty_hint()
        if save_state and not getattr(self, '_is_restoring_session', False):
            self._save_dev_workspace_session_state()
        self._organize_and_cleanup_plans()

    def _refresh_explorer(self):
        self.file_model.setRootPath(self.workspace_root)
        root_idx = self.file_model.index(self.workspace_root)
        self.tree_view.setRootIndex(root_idx)
        self.tree_view.expand(root_idx)
        self._update_explorer_empty_hint()

    def _update_explorer_empty_hint(self):
        """如果当前工作空间为空，在树形区展示友好空状态提示卡片，杜绝纯黑死寂"""
        if not hasattr(self, 'empty_explorer_hint') or not hasattr(self, 'tree_view'):
            return
        p = Path(self.workspace_root)
        has_items = False
        if p.exists() and p.is_dir():
            try:
                has_items = any(not it.name.startswith(".") for it in p.iterdir())
            except Exception:
                has_items = True
        self.empty_explorer_hint.setVisible(not has_items)
        self.tree_view.setVisible(has_items)

    def _save_dev_workspace_session_state(self):
        """持久化保存当前工作空间目录、已打开的全部文件标签及活跃焦点至本地会话与全局配置中"""
        try:
            opened_files = []
            cursor_positions = {}
            for idx in range(self.editor_tab_widget.count()):
                w = self.editor_tab_widget.widget(idx)
                fp = getattr(w, 'current_file_path', None) or getattr(w, '_wrapped_file_path', None)
                if fp and fp != "welcome.py" and Path(fp).exists():
                    p_res = str(Path(fp).resolve())
                    if p_res not in opened_files:
                        opened_files.append(p_res)
                    ed = getattr(w, '_inner_editor', w)
                    if hasattr(ed, 'textCursor'):
                        cursor_positions[p_res] = ed.textCursor().blockNumber() + 1

            active_file = None
            cur_w = self.editor_tab_widget.currentWidget()
            if cur_w:
                fp = getattr(cur_w, 'current_file_path', None) or getattr(cur_w, '_wrapped_file_path', None)
                if fp and fp != "welcome.py" and Path(fp).exists():
                    active_file = str(Path(fp).resolve())

            state = {
                "workspace_dir": str(Path(self.workspace_root).resolve()),
                "opened_files": opened_files,
                "active_file": active_file,
                "cursor_positions": cursor_positions,
                "timestamp": time.time()
            }

            # 1. 保存到独立会话文件 data/dev_session_state.json
            state_file = Path("data/dev_session_state.json")
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

            # 2. 同步写入 self.config
            self.config["workspace_dir"] = state["workspace_dir"]
            self.config["dev_session_state"] = state
            ws_name = Path(state["workspace_dir"]).name
            self.config["current_workspace_name"] = ws_name
            if callable(self.save_config_fn):
                try:
                    self.save_config_fn(self.config)
                except Exception:
                    pass
        except Exception as e:
            print(f"[DevModeView] 保存工作空间与文件会话状态异常: {e}")

    def _restore_dev_workspace_session_state(self):
        """启动时自动恢复上次关闭时的真实工作空间目录、所有已打开文件标签及光标焦点"""
        self._is_restoring_session = True
        try:
            saved_state = None
            state_file = Path("data/dev_session_state.json")
            if state_file.exists():
                try:
                    saved_state = json.loads(state_file.read_text(encoding="utf-8"))
                except Exception as e:
                    print(f"[DevModeView] 读取会话状态文件异常: {e}")

            if not saved_state:
                saved_state = self.config.get("dev_session_state", {})

            def _dir_has_files(d_path):
                if not d_path:
                    return False
                p = Path(d_path)
                if not p.exists() or not p.is_dir():
                    return False
                try:
                    return any(not it.name.startswith(".") for it in p.iterdir())
                except Exception:
                    return False

            # 1. 确定工作空间目录 (带智能防空与回退兜底)
            target_ws = saved_state.get("workspace_dir") if saved_state else None
            if not target_ws or not Path(target_ws).exists():
                target_ws = self.config.get("workspace_dir")

            if not _dir_has_files(target_ws):
                # 优先从历史打开的文件列表中寻找工程目录
                cand_files = saved_state.get("opened_files", []) if saved_state else []
                for cf in cand_files:
                    if Path(cf).exists() and _dir_has_files(Path(cf).parent):
                        target_ws = str(Path(cf).parent.resolve())
                        break

                # 其次从全局配置的 workspaces 列表中寻找真实包含文件的工程
                if not _dir_has_files(target_ws):
                    for ws in self.config.get("workspaces", []):
                        ws_p = ws.get("path")
                        if _dir_has_files(ws_p):
                            target_ws = str(Path(ws_p).resolve())
                            break

                # 最后兜底回退至程序运行目录
                if not _dir_has_files(target_ws):
                    if _dir_has_files(Path.cwd()):
                        target_ws = str(Path.cwd().resolve())

            if target_ws and Path(target_ws).exists():
                self.set_workspace_root(target_ws, save_state=False)

            # 2. 恢复已打开文件
            opened_files = saved_state.get("opened_files", []) if saved_state else []
            active_file = saved_state.get("active_file") if saved_state else None
            cursor_pos = saved_state.get("cursor_positions", {}) if saved_state else {}

            # 若未记录打开文件，但工作空间内存在 implementation_plan.md 或核心代码文件，自动载入
            if not opened_files and target_ws and Path(target_ws).exists():
                plan_f = Path(target_ws) / "implementation_plan.md"
                if plan_f.exists():
                    opened_files.append(str(plan_f.resolve()))
                else:
                    py_files = [str(f.resolve()) for f in Path(target_ws).glob("*.py")]
                    if py_files:
                        opened_files.append(py_files[0])

            restored_count = 0
            for fp in opened_files:
                if Path(fp).exists() and Path(fp).is_file():
                    line = cursor_pos.get(fp, 1)
                    self.open_file_in_editor(fp, line_no=line)
                    restored_count += 1

            # 3. 聚焦活跃文件标签页
            if active_file:
                for idx in range(self.editor_tab_widget.count()):
                    w = self.editor_tab_widget.widget(idx)
                    f = getattr(w, 'current_file_path', None) or getattr(w, '_wrapped_file_path', None)
                    if f and str(Path(f).resolve()) == str(Path(active_file).resolve()):
                        self.editor_tab_widget.setCurrentIndex(idx)
                        break

            # 4. 若最终没有任何有效文件恢复，展示默认欢迎页
            if restored_count == 0:
                self._open_welcome_tab()
        finally:
            self._is_restoring_session = False
            self._save_dev_workspace_session_state()

    def closeEvent(self, event):
        self._save_dev_workspace_session_state()
        super().closeEvent(event)

    def _on_tree_item_double_clicked(self, index):
        file_path = self.file_model.filePath(index)
        p = Path(file_path)
        if p.is_file():
            # 图片文件直接在中间 tab 中预览，不占用代码编辑器
            if ImageViewerWidget.is_image_file(file_path):
                ImageViewerWidget.open_in_editor_tab(self, str(p.resolve()))
                return
            self.open_file_in_editor(file_path)

    # ══════════════════════════════════════════════════════════
    #  资源管理器右键菜单：重命名 / 删除 / 多格式复制 / 在系统资源管理器中显示
    # ══════════════════════════════════════════════════════════
    def _on_tree_context_menu(self, pos):
        index = self.tree_view.indexAt(pos)
        menu = QMenu(self.tree_view)
        menu.setStyleSheet("""
            QMenu {
                background-color: #252526;
                color: #cccccc;
                border: 1px solid #3e4451;
                padding: 4px 0;
            }
            QMenu::item { padding: 5px 24px; font-size: 12px; }
            QMenu::item:selected { background-color: #094771; color: #ffffff; }
            QMenu::separator {
                height: 1px; background: #3e4451; margin: 4px 8px;
            }
        """)

        # 右键空白区域：只提供「新建文件」「新建文件夹」「在文件管理器中打开根目录」
        if not index.isValid():
            act_new_file = QAction("新建文件", self)
            act_new_file.triggered.connect(lambda: self._tree_create_at_root("file"))
            menu.addAction(act_new_file)
            act_new_dir = QAction("新建文件夹", self)
            act_new_dir.triggered.connect(lambda: self._tree_create_at_root("dir"))
            menu.addAction(act_new_dir)
            menu.addSeparator()
            act_reveal_root = QAction("在文件管理器中打开工作空间", self)
            act_reveal_root.triggered.connect(lambda: self._tree_reveal_in_explorer(self.workspace_root))
            menu.addAction(act_reveal_root)
            menu.exec_(self.tree_view.viewport().mapToGlobal(pos))
            return

        file_path = self.file_model.filePath(index)
        p = Path(file_path)
        is_dir = p.is_dir()
        is_root = (str(p.resolve()) == str(Path(self.workspace_root).resolve()))

        # 打开 / 重命名 / 删除（根目录与外部节点不可重命名/删除）
        if not is_dir and not is_root:
            act_open = QAction("打开", self)
            act_open.triggered.connect(lambda: self.open_file_in_editor(file_path))
            menu.addAction(act_open)
            menu.addSeparator()

        if not is_root:
            act_rename = QAction("重命名", self)
            act_rename.triggered.connect(lambda: self._tree_rename(file_path))
            menu.addAction(act_rename)

        act_delete = QAction("删除", self)
        act_delete.triggered.connect(lambda: self._tree_delete(file_path))
        menu.addAction(act_delete)

        menu.addSeparator()

        # 复制路径相关（多格式）
        copy_menu = menu.addMenu("复制")
        act_copy_abs = QAction("Windows 原生完整路径", self)
        act_copy_abs.triggered.connect(lambda: self._tree_copy_text(str(p)))
        copy_menu.addAction(act_copy_abs)

        act_copy_posix = QAction("POSIX 正斜杠路径", self)
        act_copy_posix.triggered.connect(lambda: self._tree_copy_text(str(p).replace("\\", "/")))
        copy_menu.addAction(act_copy_posix)

        # 计算工作空间相对路径
        try:
            rel_path = p.resolve().relative_to(Path(self.workspace_root).resolve()).as_posix()
        except Exception:
            rel_path = p.name

        act_copy_rel = QAction("相对工作空间路径", self)
        act_copy_rel.triggered.connect(lambda: self._tree_copy_text(rel_path))
        copy_menu.addAction(act_copy_rel)

        name_with_ext = p.name
        name_without_ext = p.stem if p.suffix else p.name
        act_copy_name_ext = QAction("文件名（含扩展名）", self)
        act_copy_name_ext.triggered.connect(lambda: self._tree_copy_text(name_with_ext))
        copy_menu.addAction(act_copy_name_ext)
        act_copy_name = QAction("文件名（不含扩展名）", self)
        act_copy_name.triggered.connect(lambda: self._tree_copy_text(name_without_ext))
        copy_menu.addAction(act_copy_name)

        if not is_dir:
            copy_menu.addSeparator()
            act_copy_file = QAction("复制文件本体", self)
            act_copy_file.triggered.connect(lambda: self._tree_copy_file_binary(file_path))
            copy_menu.addAction(act_copy_file)

            act_copy_content = QAction("复制文件内容（文本）", self)
            act_copy_content.triggered.connect(lambda: self._tree_copy_text_file(file_path))
            copy_menu.addAction(act_copy_content)

        menu.addSeparator()

        act_reveal = QAction("在文件管理器中显示", self)
        act_reveal.triggered.connect(lambda: self._tree_reveal_in_explorer(file_path))
        menu.addAction(act_reveal)

        menu.exec_(self.tree_view.viewport().mapToGlobal(pos))

    def _tree_copy_text(self, text: str):
        QApplication.clipboard().setText(text or "")
        self.set_status(f"已复制到剪贴板：{(text or '')[:80]}")

    def _tree_copy_text_file(self, file_path: str):
        try:
            text = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            self.set_status(f"读取文件失败：{e}")
            return
        QApplication.clipboard().setText(text)
        self.set_status(f"已复制文件文本内容：{Path(file_path).name}")

    def _tree_copy_file_binary(self, file_path: str):
        """把文件本体以二进制形式塞入剪贴板，像 Windows 资源管理器那样粘贴时可直接落盘"""
        from PyQt5.QtCore import QMimeData, QUrl
        from PyQt5.QtGui import QDrag
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            self.set_status("复制失败：文件不存在")
            return
        try:
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(p.resolve()))])
            QApplication.clipboard().setMimeData(mime)
            self.set_status(f"已复制文件本体：{p.name}（粘贴时可直接落盘）")
        except Exception as e:
            self.set_status(f"复制文件失败：{e}")

    def _tree_rename(self, file_path: str):
        p = Path(file_path)
        parent_layout = None
        try:
            from PyQt5.QtWidgets import QInputDialog
            new_name, ok = QInputDialog.getText(
                self, "重命名", f"将 {p.name} 重命名为：", text=p.name
            )
        except Exception:
            new_name, ok = "", False
        if not ok or not new_name.strip() or new_name.strip() == p.name:
            return
        new_name = new_name.strip()
        target = p.parent / new_name
        if target.exists():
            QMessageBox.warning(self, "重命名失败", f"目标已存在：{target.name}")
            return
        try:
            p.rename(target)
            self.set_status(f"已重命名：{p.name} → {new_name}")
        except Exception as e:
            QMessageBox.critical(self, "重命名失败", str(e))

    def _tree_delete(self, file_path: str):
        p = Path(file_path)
        is_dir = p.is_dir()
        kind = "文件夹" if is_dir else "文件"
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除{kind}「{p.name}」吗？\n\n路径：{file_path}\n\n删除后不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            import shutil
            if is_dir:
                shutil.rmtree(p)
            else:
                p.unlink()
            self.set_status(f"已删除{kind}：{p.name}")
        except Exception as e:
            QMessageBox.critical(self, "删除失败", str(e))

    def _tree_create_at_root(self, kind: str):
        """在工作空间根目录新建文件/文件夹"""
        try:
            from PyQt5.QtWidgets import QInputDialog
        except Exception:
            return
        label = "新建文件名：" if kind == "file" else "新建文件夹名："
        name, ok = QInputDialog.getText(self, "新建" + ("文件" if kind == "file" else "文件夹"), label)
        if not ok or not name.strip():
            return
        name = name.strip()
        target = Path(self.workspace_root) / name
        if target.exists():
            QMessageBox.warning(self, "新建失败", f"已存在同名{name}：{name}")
            return
        try:
            if kind == "file":
                target.write_text("", encoding="utf-8")
            else:
                target.mkdir(parents=False, exist_ok=False)
            self.set_status(f"已新建：{name}")
        except Exception as e:
            QMessageBox.critical(self, "新建失败", str(e))

    def _tree_reveal_in_explorer(self, file_path: str):
        """在系统资源管理器中显示并选中文件/目录"""
        p = Path(file_path)
        try:
            if not p.exists():
                self.set_status("路径不存在，无法在文件管理器中显示")
                return
            if sys.platform.startswith("win"):
                if p.is_dir():
                    os.startfile(str(p))  # noqa: S606
                else:
                    # 选中文件：使用 explorer /select,
                    subprocess.run(
                        ["explorer", f"/select,{p.resolve()}"],
                        shell=False,
                        check=False,
                    )
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", str(p)], check=False)
            else:
                subprocess.run(["xdg-open", str(p.parent if p.is_file() else p)], check=False)
        except Exception as e:
            self.set_status(f"打开文件管理器失败：{e}")

    # ══════════════════════════════════════════════════════════
    #  终端控制与运行当前 Python 脚本
    # ══════════════════════════════════════════════════════════
    # ══════════════════════════════════════════════════════════
    #  核心功能组件：[制定方案]、[代码审查]、[运行测试]
    # ══════════════════════════════════════════════════════════
    def _action_plan(self):
        """[制定方案] 交互触发：结合当前活跃文件或需求自动组织架构设计任务并即刻驱动 AI 制定"""
        ed = self._get_current_editor()
        current_input = self.input_edit.toPlainText().strip()
        self._is_plan_mode = True

        # 若输入框中已有用户输入，智能组织需求并即刻触发 AI 规划
        if current_input:
            if not current_input.startswith("【制定方案】"):
                prompt = f"【制定方案】：{current_input}"
            else:
                prompt = current_input
            self.input_edit.setPlainText(prompt)
            self._send_ai_prompt()
            return

        if ed and ed.current_file_path:
            try:
                rel_name = Path(ed.current_file_path).name
                total_lines = len(ed.toPlainText().splitlines())
                sel = ed.textCursor().selectedText().strip()
                if sel:
                    sel_lines = len(sel.splitlines())
                    draft = f"请针对文件【{rel_name}】选中的核心代码片段（共 {sel_lines} 行）制定技术落地与架构重构实施方案"
                else:
                    draft = f"请针对当前文件【{rel_name}】（共 {total_lines} 行）进行深入需求分析，制定系统的代码落地与实现架构方案"
            except Exception:
                draft = "请为当前项目需求制定详细的代码落地与系统架构方案"
        else:
            ws_name = Path(self.workspace_root).name
            draft = f"请对当前工作空间【{ws_name}】的核心业务逻辑制定详细的技术架构与分步落地实施方案"

        self.input_edit.setPlainText(draft)
        # 真实触发大模型生成方案，绝非仅填充文本框的空架子
        self._send_ai_prompt()

    def _action_review(self):
        """[代码审查] 交互触发：自动捕获当前文件或工作空间核心模块，立即触发 5 维度深度代码质量审查"""
        ed = self._get_current_editor()
        current_input = self.input_edit.toPlainText().strip()
        self._is_review_mode = True

        # 若输入框中已有用户需求，直接发送进行深度审查
        if current_input:
            if not current_input.startswith("【代码审查】"):
                prompt = f"【代码审查】：{current_input}"
            else:
                prompt = current_input
            self.input_edit.setPlainText(prompt)
            self._send_ai_prompt()
            return

        target_file = None
        if ed and ed.current_file_path:
            target_file = ed.current_file_path
        else:
            # 自动探测工作空间最近修改的核心 Python 文件并打开
            try:
                ws = Path(self.workspace_root)
                candidates = [p for p in ws.rglob("*.py") if not p.name.startswith(".") and not any(part.startswith(".") for part in p.parts)]
                if candidates:
                    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    target_file = str(candidates[0])
                    self.open_file_in_editor(target_file)
            except Exception:
                pass

        if target_file:
            rel_name = Path(target_file).name
            try:
                total_lines = len(Path(target_file).read_text(encoding="utf-8", errors="replace").splitlines())
            except Exception:
                total_lines = 0
            cur_ed = self._get_current_editor()
            sel = cur_ed.textCursor().selectedText().strip() if cur_ed else ""
            if sel:
                sel_lines = len(sel.splitlines())
                draft = f"请对当前文件【{rel_name}】选中的代码片段（共 {sel_lines} 行）执行 5 维度企业级深度代码审查"
            else:
                draft = f"请对当前核心代码文件【{rel_name}】（共 {total_lines} 行完整代码）执行 5 维度企业级深度代码审查"
        else:
            ws_name = Path(self.workspace_root).name
            draft = f"请对当前工作空间【{ws_name}】的代码工程结构与核心逻辑执行全面的代码质量体检与安全审查"

        self.input_edit.setPlainText(draft)
        # 真实触发大模型代码审查
        self._send_ai_prompt()

    def _discover_test_target(self) -> tuple[Optional[str], str]:
        """
        智能测试目标发现引擎:
        返回 (test_file_path, description)
        """
        ed = self._get_current_editor()
        cur_file = ed.current_file_path if (ed and ed.current_file_path) else None

        # 1. 当前文件本身就是测试文件
        if cur_file and (Path(cur_file).name.startswith("test_") or Path(cur_file).name.endswith("_test.py")):
            return cur_file, "当前编辑器激活的单元测试文件"

        # 2. 当前文件是业务模块，寻找其关联的测试文件
        if cur_file:
            stem = Path(cur_file).stem
            candidates = [
                Path(self.workspace_root) / f"test_{stem}.py",
                Path(self.workspace_root) / "tests" / f"test_{stem}.py",
                Path(self.workspace_root) / "scratch" / f"test_{stem}.py",
                Path(cur_file).parent / f"test_{stem}.py"
            ]
            for cand in candidates:
                if cand.is_file():
                    return str(cand), f"匹配模块【{stem}.py】的对应测试用例"

        # 3. 扫描 workspace 下常见的测试目录与文件 (scratch/test_*.py, tests/test_*.py, test_*.py)
        test_files = []
        try:
            ws = Path(self.workspace_root)
            for sub in ["tests", "scratch", "."]:
                dir_p = ws / sub if sub != "." else ws
                if dir_p.is_dir():
                    for f in dir_p.glob("test_*.py"):
                        if f.is_file():
                            test_files.append(f)
        except Exception:
            pass

        if test_files:
            # 优先选择最近修改的测试文件
            test_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return str(test_files[0]), f"工作空间最新测试文件 (共发现 {len(test_files)} 个单测)"

        # 4. 兜底：如果当前有打开的 py 文件，直接作为执行脚本
        if cur_file and cur_file.endswith(".py"):
            return cur_file, "当前编辑器活跃的 Python 脚本"

        return None, ""

    def _action_run_tests(self):
        """[运行测试] 智能测试引擎 (非阻塞沙箱线程执行 + 结果诊断 + 聊天卡片实时呈现 + 报错一键自愈)"""
        # 1. 确保沙箱控制台处于显示状态，并切到终端标签页
        if not self.console_panel.isVisible():
            self.console_panel.setVisible(True)
        self._switch_console_view(0)

        # 2. 智能识别测试目标
        target_file, target_desc = self._discover_test_target()
        if not target_file:
            msg = "⚠️ 未在当前工作空间或打开的编辑器中发现 Python 脚本或测试用例 (test_*.py)。请先在编辑器打开脚本或编写单测后重试。"
            self.terminal_output.append(f"<div style='color:#e5c07b;margin:4px 0;'>{msg}</div>")
            
            # 在 AI 聊天流中同步反馈
            notice_card = QFrame()
            notice_card.setStyleSheet("background-color: #2c2214; border: 1px solid #734e18; border-radius: 6px; padding: 8px 12px; margin: 4px 0;")
            n_lay = QHBoxLayout(notice_card)
            n_lay.setContentsMargins(0, 0, 0, 0)
            n_lbl = QLabel(f"⚠️ <b>[测试目标未找到]</b>: 请先在代码编辑器中打开脚本或在 scratch/ 编写单测。")
            n_lbl.setStyleSheet("color: #e5c07b; font-size: 12px; background: transparent; border: none;")
            n_lay.addWidget(n_lbl)
            self.chat_v_layout.insertWidget(self.chat_v_layout.count() - 1, notice_card)
            self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
            return

        # 3. 运行前自动保存当前编辑器文件
        self._action_save_current()

        # 4. 打印启动横幅并向 AI 聊天流投递运行状态卡片
        target_name = Path(target_file).name
        try:
            rel_target = str(Path(target_file).relative_to(self.workspace_root))
        except Exception:
            rel_target = target_name

        self.terminal_output.append(
            f"<div style='color:#61afef;font-weight:bold;margin:8px 0 4px 0;'>"
            f"══════════════════════════════════════════════════════════<br>"
            f"🚀 <b>[DeskAI 自动化测试引擎]</b> 启动测试任务<br>"
            f"🎯 <b>测试目标</b>: {rel_target} ({target_desc})<br>"
            f"📂 <b>沙箱工作目录</b>: {self.workspace_root}<br>"
            f"══════════════════════════════════════════════════════════"
            f"</div>"
        )

        start_card = QFrame()
        start_card.setStyleSheet("background-color: #1a2332; border: 1px solid #1f6feb; border-radius: 6px; padding: 8px 12px; margin: 4px 0;")
        s_lay = QHBoxLayout(start_card)
        s_lay.setContentsMargins(0, 0, 0, 0)
        s_lbl = QLabel(f"🚀 <b>[自动化测试启动]</b>: 正在沙箱中执行 <code>{rel_target}</code> ({target_desc})...")
        s_lbl.setStyleSheet("color: #79c0ff; font-size: 12px; background: transparent; border: none;")
        s_lay.addWidget(s_lbl)
        self.chat_v_layout.insertWidget(self.chat_v_layout.count() - 1, start_card)
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

        # 5. 异步在独立线程中执行，绝不阻塞 UI 界面
        threading.Thread(
            target=self._run_test_worker,
            args=(str(target_file), rel_target),
            daemon=True
        ).start()

    def _run_test_worker(self, target_file: str, rel_target: str):
        t0 = time.time()
        try:
            res = subprocess.run(
                [sys.executable, target_file],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=45
            )
            elapsed = time.time() - t0
            self.test_finished_signal.emit(res.returncode, res.stdout or "", res.stderr or "", elapsed, rel_target)
        except subprocess.TimeoutExpired as e:
            elapsed = time.time() - t0
            self.test_finished_signal.emit(-1, e.stdout or "", "⚠️ 测试执行超时 (超过 45 秒已自动终止)", elapsed, rel_target)
        except Exception as e:
            elapsed = time.time() - t0
            self.test_finished_signal.emit(-2, "", f"❌ 启动测试子进程异常: {e}", elapsed, rel_target)

    def _on_test_finished(self, returncode: int, stdout: str, stderr: str, elapsed: float, rel_target: str):
        """测试运行完成回调 (主 GUI 线程执行，终端与 AI 助手流双向联动)"""
        if stdout and stdout.strip():
            safe_out = html.escape(stdout.strip())
            self.terminal_output.append(f"<pre style='color:#abb2bf;font-family:monospace;margin:4px 0;'>{safe_out}</pre>")
        if stderr and stderr.strip():
            safe_err = html.escape(stderr.strip())
            self.terminal_output.append(f"<pre style='color:#e06c75;font-family:monospace;margin:4px 0;'>{safe_err}</pre>")

        if returncode == 0:
            self.terminal_output.append(
                f"<div style='color:#98c379;font-weight:bold;margin:6px 0;'>"
                f"✔ [TEST PASSED] 测试用例全部通过！(耗时: {elapsed:.2f}s, 退出码: 0)<br>"
                f"🎉 目标模块运行稳定，各项断言与执行逻辑均验证正常。"
                f"</div>"
            )
        else:
            self.terminal_output.append(
                f"<div style='color:#e06c75;font-weight:bold;margin:6px 0;'>"
                f"✖ [TEST FAILED] 测试运行异常或未通过！(耗时: {elapsed:.2f}s, 退出码: {returncode})"
                f"</div>"
            )

        # 在 AI 助手聊天流中追加结构化测试报告与一键自愈互动卡片
        res_card = QFrame()
        res_card.setStyleSheet(f"""
            QFrame {{
                background-color: {'#162a1e' if returncode == 0 else '#2c191a'};
                border: 1px solid {'#238636' if returncode == 0 else '#da3633'};
                border-radius: 8px;
                padding: 12px 14px;
                margin: 6px 0;
            }}
        """)
        r_lay = QVBoxLayout(res_card)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(8)

        st_title = f"✔ [测试全部通过] {rel_target} (耗时 {elapsed:.2f}s, Exit Code 0)" if returncode == 0 else f"✖ [测试未通过] {rel_target} (耗时 {elapsed:.2f}s, Exit Code {returncode})"
        st_color = "#3fb950" if returncode == 0 else "#f85149"
        hdr = QLabel(f"<b>{st_title}</b>")
        hdr.setStyleSheet(f"color: {st_color}; font-size: 13px; background: transparent; border: none;")
        r_lay.addWidget(hdr)

        if returncode == 0:
            msg = QLabel("🎉 目标模块各项断言与执行逻辑均验证正常，代码运行稳定无异常。")
            msg.setStyleSheet("color: #7ee787; font-size: 12px; background: transparent; border: none;")
            r_lay.addWidget(msg)
        else:
            err_text = stderr.strip() if (stderr and stderr.strip()) else stdout.strip()
            err_lines = err_text.splitlines()[-20:]
            err_snippet = "\n".join(err_lines)
            err_lbl = QLabel(f"<pre style='color:#ff7b72; font-family:Consolas,monospace; font-size:11px; background:#1e1415; padding:6px; border-radius:4px;'>{html.escape(err_snippet)}</pre>")
            err_lbl.setWordWrap(True)
            r_lay.addWidget(err_lbl)

            heal_cmd = (
                f"运行测试【{rel_target}】失败 (Exit Code {returncode})。请根据以下报错堆栈排查根本原因，调用 write_workspace_file 修复代码，并调用 run_workspace_command 重新测试直到通过：\n"
                f"```text\n{err_snippet}\n```"
            )

            # 一键 AI 自愈修复按钮
            btn_heal = QPushButton("⚡ 一键调用 AI 自动自愈修复 (Auto-Heal)")
            btn_heal.setStyleSheet("""
                QPushButton {
                    background-color: #238636;
                    color: #ffffff;
                    font-weight: bold;
                    border: none;
                    border-radius: 6px;
                    padding: 7px 14px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #2ea043;
                }
            """)
            btn_heal.clicked.connect(lambda checked, cmd=heal_cmd: self._trigger_heal(cmd))
            r_lay.addWidget(btn_heal)

            # 同步更新输入框草稿
            self.input_edit.setPlainText(heal_cmd)

        self.chat_v_layout.insertWidget(self.chat_v_layout.count() - 1, res_card)
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

    def _trigger_heal(self, heal_cmd: str):
        """一键触发 AI 自愈修复"""
        self.input_edit.setPlainText(heal_cmd)
        self._send_ai_prompt()

    def _execute_plan_proceed(self):
        """用户确认实施方案：解除审批门控并启动分步执行与代码写入验证闭环。
        若 AI 正在执行其他任务，将 proceed 插入队列首位而不是直接中断。"""
        # 解除审批门控
        self._pending_plan_approval = False

        # 优先使用当前活跃方案文件路径，如无则查找 plans/ 目录下最新的方案文件
        plan_path_str = getattr(self, '_current_plan_file_path', '')
        if not plan_path_str or not Path(plan_path_str).exists():
            plans_dir = self._get_plans_dir()
            plan_files = sorted(plans_dir.glob("plan_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
            if plan_files:
                plan_path_str = str(plan_files[0])
            elif (plans_dir / "implementation_plan.md").exists():
                plan_path_str = str(plans_dir / "implementation_plan.md")
            elif (Path(self.workspace_root) / "implementation_plan.md").exists():
                plan_path_str = str(Path(self.workspace_root) / "implementation_plan.md")
            else:
                plan_path_str = str(plans_dir / "implementation_plan.md")
        plan_path = Path(plan_path_str)
        plan_details = ""
        if plan_path.exists():
            try:
                plan_details = plan_path.read_text(encoding="utf-8", errors="replace").strip()
            except Exception:
                pass

        plan_fname = plan_path.name
        if plan_details:
            proceed_prompt = (
                f"我已审阅并正式批准《技术实施方案 ({plan_fname})》。\n\n"
                f"【批准执行的方案全文如下】：\n```markdown\n{plan_details}\n```\n\n"
                f"请你严格按照上述已批准方案中的【架构设计】与【分步执行步骤】：\n"
                f"1. 按步骤使用 write_workspace_file 编写并落盘各模块源码；\n"
                f"2. 使用 run_workspace_command 运行自动化测试与验证；\n"
                f"3. 遇到问题自动排查修复，直至完全达成方案目标！请开始第一步执行。"
            )
        else:
            proceed_prompt = "已仔细审阅并批准技术落地实施方案。请立即按照规划好的分步路线图，调用 write_workspace_file 编写各模块源码，并运行测试验证！"

        # 如果 AI 正在执行其他任务，将 proceed 插入队列首位，任务完成后立即执行
        if self._is_generating:
            self._dev_message_queue.insert(0, (proceed_prompt, None, None))
            self._update_queue_ui()
            self.terminal_output.append(
                "<span style='color:#e5c07b'><b>[方案已入队]</b> 当前 AI 尚在执行其他任务，方案已插入执行队列首位，将在当前任务完成后立即启动。</span>"
            )
            return

        # AI 空闲，直接执行
        self.input_edit.setPlainText(proceed_prompt)
        self._send_ai_prompt()

    def _run_current_file(self):
        """兼容菜单与快捷键 F5 入口，统一转发至智能测试运行引擎"""
        self._action_run_tests()

    def _clear_terminal(self):
        # terminal_output 与 log_output 是同一对象，清一次即可
        self.terminal_output.clear()
        self.terminal_output.append("<span style='color:#61afef'>[模型与系统日志已清空]</span>")
        # 同步：清空交互终端（向 PTY 发送 cls 清屏）
        if hasattr(self, 'interactive_terminal') and self.interactive_terminal:
            try:
                self.interactive_terminal._clear_screen()
            except Exception:
                pass

    def _on_h_splitter_moved(self, pos: int, index: int):
        """当拖动中间窗口向左覆盖资源管理器时，支持一直移动至完全覆盖隐藏；向右拖出时恢复显示"""
        if index == 1:
            if pos <= 20:
                cur_sizes = self.h_splitter.sizes()
                if cur_sizes[0] != 0:
                    total_left = cur_sizes[0] + cur_sizes[1]
                    self.h_splitter.setSizes([0, total_left, cur_sizes[2] if len(cur_sizes) > 2 else 380])

    def _toggle_explorer(self):
        sizes = self.h_splitter.sizes()
        if sizes[0] == 0 or not self.explorer_panel.isVisible():
            self.explorer_panel.setVisible(True)
            total = sizes[0] + sizes[1]
            self.h_splitter.setSizes([220, max(150, total - 220), sizes[2] if len(sizes) > 2 else 380])
        else:
            total = sizes[0] + sizes[1]
            self.h_splitter.setSizes([0, total, sizes[2] if len(sizes) > 2 else 380])

    def _toggle_console(self):
        self.console_panel.setVisible(not self.console_panel.isVisible())

    def _open_interactive_terminal(self):
        """
        显示底部控制台并切到"交互终端" tab（用于「终端 (T) ▾」菜单新加的入口）。
        - 如果 console_panel 当前隐藏，先 setVisible(True)
        - 然后 _switch_console_view(1) 切到 console_stack 的第 1 页（交互终端）
        - _switch_console_view 内部会调 interactive_terminal.focus_terminal() 把焦点交给输入区
        """
        if not hasattr(self, 'console_panel') or self.console_panel is None:
            return
        if not self.console_panel.isVisible():
            self.console_panel.setVisible(True)
        self._switch_console_view(1)

    def _toggle_ai_panel(self):
        self.ai_panel.setVisible(not self.ai_panel.isVisible())

    def _toggle_minimap(self, checked: bool):
        self._show_minimap = checked
        if hasattr(self, 'editor_tab_widget'):
            for i in range(self.editor_tab_widget.count()):
                w = self.editor_tab_widget.widget(i)
                if hasattr(w, 'set_show_minimap'):
                    w.set_show_minimap(checked)

    # ══════════════════════════════════════════════════════════
    #  模型动态同步与切换逻辑 (严格与系统 models_list 同步，绝无假数据)
    # ══════════════════════════════════════════════════════════
    def refresh_models_list(self):
        """从应用配置动态加载真实模型列表并同步当前激活模型"""
        self.model_combo.blockSignals(True)
        self.model_combo.clear()

        models_list = self.config.get("models_list", [])
        active_id = self.config.get("active_model_id", "")
        active_name = self.config.get("active_model_name", "")
        cur_idx = 0

        if not models_list:
            # 兜底从 ai_engine 读取当前活跃模型
            cur_name = getattr(self.ai_engine, "model_name", "默认模型")
            self.model_combo.addItem(cur_name, {"id": "default", "name": cur_name, "model_name": cur_name})
        else:
            for idx, m in enumerate(models_list):
                if isinstance(m, str):
                    m = {"id": m, "name": m, "model_name": m}
                m_id = m.get("id", "")
                m_name = m.get("name") or m.get("model_name") or m_id
                self.model_combo.addItem(m_name, m)
                if m_id == active_id or m_name == active_name or m.get("model_name") == getattr(self.ai_engine, "model_name", ""):
                    cur_idx = idx

        self.model_combo.setCurrentIndex(cur_idx)
        self.model_combo.blockSignals(False)

    def _on_model_selection_changed(self, index: int):
        if index < 0:
            return
        m_data = self.model_combo.itemData(index)
        if not m_data or not isinstance(m_data, dict):
            return

        # 真正热切换大模型连接端点 (100% 内存即时替换)
        if hasattr(self.ai_engine, 'set_active_model'):
            self.ai_engine.set_active_model(m_data)

        m_id = m_data.get("id", "")
        m_name = m_data.get("name") or m_data.get("model_name") or m_id
        self.config["active_model_id"] = m_id
        self.config["active_model_name"] = m_name

        # 持久化落盘配置
        if hasattr(self, 'save_config_fn') and self.save_config_fn:
            try:
                self.save_config_fn(self.config)
            except Exception as e:
                print(f"[DevModeView] 保存配置异常: {e}")

        provider_str = m_data.get('provider', '')
        self.terminal_output.append(f"<span style='color:#61afef'>🔄 [大模型切换] 已实时切换为: <b>{m_name}</b> ({provider_str})</span>")

    # ══════════════════════════════════════════════════════════
    #  开发者身份与 MCP/Skill 扩展中心联动逻辑
    # ══════════════════════════════════════════════════════════
    def _refresh_persona_combo(self):
        """从配置中加载 7 种专业开发者身份与用户自定义身份，并同步当前活跃身份"""
        if not hasattr(self, "persona_combo"):
            return
        self.persona_combo.blockSignals(True)
        self.persona_combo.clear()

        custom_personas = self.config.get("dev_custom_personas", {})
        all_personas = dict(DEFAULT_DEV_PERSONAS)
        all_personas.update(custom_personas)

        active_p_id = self.config.get("dev_active_persona", "fullstack_architect")
        if active_p_id == "fullstack":
            active_p_id = "fullstack_architect"
        cur_idx = 0

        for idx, (p_id, p_info) in enumerate(all_personas.items()):
            icon = p_info.get("icon", "👨‍💻")
            name = p_info.get("name", p_id)
            self.persona_combo.addItem(f"{icon} {name}", p_id)
            if p_id == active_p_id:
                cur_idx = idx

        self.persona_combo.setCurrentIndex(cur_idx)
        self.persona_combo.blockSignals(False)

    def _on_persona_changed(self, index: int):
        """用户切换开发者身份 (持久化落盘并动态更新大模型系统 Prompt)"""
        if index < 0:
            return
        p_id = self.persona_combo.itemData(index)
        if not p_id:
            return

        self.config["dev_active_persona"] = p_id
        if hasattr(self, "save_config_fn") and self.save_config_fn:
            try:
                self.save_config_fn(self.config)
            except Exception as e:
                print(f"[DevModeView] 保存开发者身份配置异常: {e}")

        custom_personas = self.config.get("dev_custom_personas", {})
        all_personas = dict(DEFAULT_DEV_PERSONAS)
        all_personas.update(custom_personas)
        p_info = all_personas.get(p_id, {})
        p_name = p_info.get("name", p_id)
        icon = p_info.get("icon") or (p_info.get("title", "").split()[0] if p_info.get("title") else "👨‍💻")
        desc = p_info.get("desc") or p_info.get("description", "")

        self.terminal_output.append(
            f"<span style='color:#61afef'>🎭 [身份切换] 当前大模型开发者身份已实时切换为: <b>{icon} {p_name}</b></span>\n"
            f"<span style='color:#858585'>   角色职责与思维模型: {desc}</span>"
        )

    def _open_extension_manager(self):
        """打开专业的 MCP 服务与 Skill 扩展管理中心对话框"""
        dlg = DevExtensionManagerDialog(self.config, self.save_config_fn, getattr(self, "is_dark", True), self)
        dlg.extensions_changed.connect(self._on_extension_changed)
        dlg.exec_()

    def _on_extension_changed(self):
        """扩展中心保存后即时热重载 MCP 工具与身份配置"""
        self._refresh_persona_combo()
        try:
            MCPToolBridge.get_instance().mount_all_mcp_tools()
        except Exception as e:
            print(f"[DevModeView] 热重载 MCP 工具异常: {e}")
        self.terminal_output.append(
            "<span style='color:#98c379'>🧩 [扩展中心同步] MCP 服务与 Skill 技能已更新并即时热加载就绪！</span>"
        )

    # ══════════════════════════════════════════════════════════
    #  AI 智能交互逻辑 (真实异步流式生成 + 工具调用真实写文件 + 编辑器自动打开)
    # ══════════════════════════════════════════════════════════
    def _connect_ai_signals(self):
        self.ai_chunk_signal.connect(self._on_ai_chunk)
        self.ai_done_signal.connect(self._on_ai_done)
        self.ai_error_signal.connect(self._on_ai_error)

    def _on_tracker_file_changed(self, rec):
        """后台文件变动安全转发至主线程"""
        try:
            self.file_diff_recorded_signal.emit(rec)
        except Exception:
            pass

    def _handle_file_diff_record(self, rec):
        """主线程响应实际文件创建/修改事件 (底层总线保证 100% 捕获变更)"""
        if not rec:
            return
        abs_p = str(Path(rec.abs_path).resolve())
        rel_p = rec.rel_path
        status_name = "新建文件" if rec.status == "created" else "修改文件"

        if abs_p not in self._generated_files:
            self._generated_files.append(abs_p)

        if self._current_traj:
            self._current_traj.add_file_change(rel_p, status_name, rec.added_lines, rec.removed_lines, abs_p)

        self.terminal_output.append(
            f"📝 <span style='color:#61afef'><b>[文件变动捕捉]</b> 已{status_name}: <code>{rel_p}</code> (+{rec.added_lines} -{rec.removed_lines} 行)</span>"
        )

    def _on_single_accept(self, rel_path: str):
        """单文件接纳"""
        try:
            from core.file_diff_tracker import FileDiffTracker
            tracker = FileDiffTracker.get_instance()
            p = Path(rel_path)
            target = p if p.is_absolute() else (Path(self.workspace_root) / p)
            abs_p = str(target.resolve())
            tracker.accept_change(abs_p)
            # 若文件在编辑器打开，确保内容同步
            if abs_p in self.opened_editors and target.exists():
                try:
                    self.opened_editors[abs_p].setPlainText(target.read_text(encoding="utf-8"))
                    self.opened_editors[abs_p].is_modified = False
                except Exception:
                    pass
            self.terminal_output.append(f"<span style='color:#98c379'>✅ 已确认接纳单个文件变动: <code>{target.name}</code></span>")
        except Exception as e:
            self.terminal_output.append(f"⚠️ 接纳文件异常: {e}")

    def _on_single_reject(self, rel_path: str):
        """单文件撤回/还原"""
        try:
            from core.file_diff_tracker import FileDiffTracker
            tracker = FileDiffTracker.get_instance()
            p = Path(rel_path)
            target = p if p.is_absolute() else (Path(self.workspace_root) / p)
            abs_p = str(target.resolve())
            tracker.revert_change(abs_p)

            # 若编辑器打开了该文件：新建文件被删则关闭tab，修改文件则刷新为旧版
            if abs_p in self.opened_editors:
                if not target.exists():
                    for idx in range(self.editor_tab_widget.count()):
                        w = self.editor_tab_widget.widget(idx)
                        if hasattr(w, 'current_file_path') and w.current_file_path == abs_p:
                            self.editor_tab_widget.removeTab(idx)
                            break
                    self.opened_editors.pop(abs_p, None)
                else:
                    try:
                        self.opened_editors[abs_p].setPlainText(target.read_text(encoding="utf-8"))
                        self.opened_editors[abs_p].is_modified = False
                    except Exception:
                        pass
            self._refresh_explorer()
            self.terminal_output.append(f"<span style='color:#e06c75'>❌ 已放弃并物理还原文件: <code>{target.name}</code></span>")
        except Exception as e:
            self.terminal_output.append(f"⚠️ 还原文件异常: {e}")

    def _on_accept_trajectory_changes(self, file_str: str):
        """用户点击【全部接收 (Accept)】或【重新接纳 (Re-apply)】"""
        try:
            from core.file_diff_tracker import FileDiffTracker
            tracker = FileDiffTracker.get_instance()
            files = [f.strip() for f in file_str.split(",") if f.strip()]
            for f in files:
                p = Path(f)
                target = p if p.is_absolute() else (Path(self.workspace_root) / p)
                abs_p = str(target.resolve())
                tracker.accept_change(abs_p)
                # 重新写入或确认落地后，同步编辑器
                if abs_p in self.opened_editors and target.exists():
                    try:
                        self.opened_editors[abs_p].setPlainText(target.read_text(encoding="utf-8"))
                        self.opened_editors[abs_p].is_modified = False
                    except Exception:
                        pass
            self._refresh_explorer()
            self.terminal_output.append(
                f"<span style='color:#98c379'>✅ 已确认接收全部 {len(files)} 个文件变更！"
                f"（代码已落地就绪，随时支持点击卡片上的【↩️ 撤回本次变更】物理回滚）</span>"
            )
        except Exception as e:
            self.terminal_output.append(f"⚠️ 接收变更异常: {e}")

    def _on_reject_trajectory_changes(self, file_str: str):
        """用户点击【放弃 (Reject)】或【撤回 (Revert)】：物理还原代码并关闭/刷新 Tab"""
        try:
            from core.file_diff_tracker import FileDiffTracker
            tracker = FileDiffTracker.get_instance()
            files = [f.strip() for f in file_str.split(",") if f.strip()]
            for f in files:
                p = Path(f)
                target = p if p.is_absolute() else (Path(self.workspace_root) / p)
                abs_p = str(target.resolve())
                tracker.revert_change(abs_p)
                # 若编辑器打开了该文件，新建文件自动关闭 Tab，修改文件刷新为还原前内容
                if abs_p in self.opened_editors:
                    if not target.exists():
                        for idx in range(self.editor_tab_widget.count()):
                            w = self.editor_tab_widget.widget(idx)
                            if hasattr(w, 'current_file_path') and w.current_file_path == abs_p:
                                self.editor_tab_widget.removeTab(idx)
                                break
                        self.opened_editors.pop(abs_p, None)
                    else:
                        try:
                            self.opened_editors[abs_p].setPlainText(target.read_text(encoding="utf-8"))
                            self.opened_editors[abs_p].is_modified = False
                        except Exception:
                            pass
            self._refresh_explorer()
            self.terminal_output.append(
                f"<span style='color:#e06c75'>❌ 已放弃/撤销全部 {len(files)} 个文件变动！"
                f"（代码已物理回退，随时支持点击卡片上的【↩️ 重新接纳】恢复）</span>"
            )
        except Exception as e:
            self.terminal_output.append(f"⚠️ 还原变更异常: {e}")

    def _filter_dumped_code_blocks(self, text: str) -> str:
        """
        智能清洗大模型在聊天框中倾倒的长篇全量代码块 (对齐用户需求：只保留精炼的方案总结与要点说明)
        - 将超过 8 行的长篇源码块替换为已落盘文件卡片提示
        - 保留短命令、测试调用示例或 <= 8 行的关键代码片段
        - 完整保留所有结构化排版、说明与小结
        """
        import re
        def _replace_block(match):
            lang = match.group(1) or ""
            code = match.group(2) or ""
            lines = [ln for ln in code.strip().splitlines() if ln.strip()]

            # 如果是短代码（比如命令行命令、简短调用示例，<= 8 行），正常保留
            if len(lines) <= 8:
                return match.group(0)

            # 提取文件提示
            hint = ""
            m_file = re.search(r'#\s*(?:file|文件名)?\s*[:：]?\s*([a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9]+)', code)
            if m_file:
                hint = f" <code>{m_file.group(1)}</code>"
            elif "class " in code:
                m_cls = re.search(r'class\s+([A-Za-z0-9_]+)', code)
                if m_cls:
                    hint = f" (定义 <code>class {m_cls.group(1)}</code>)"

            return (
                f"\n> **[代码已自动写入磁盘文件并在主屏幕编辑器中打开]**{hint}\n"
                f"> *（共 {len(lines)} 行源码已落地就绪，无需在聊天框滚动阅读，请直接在左侧/中间主屏幕代码视图中查看、编辑与调试）*\n"
            )

        cleaned = re.sub(r'```([a-zA-Z0-9_\-#\+]*)\n(.*?)```', _replace_block, text, flags=re.DOTALL)
        return clean_markdown_tables(strip_emojis(cleaned))

    # ══════════════════════════════════════════════════════════
    #  消息排队队列管理 (对齐需求：支持连续发送多个对话，在输入框前面排队并自动流转)
    # ══════════════════════════════════════════════════════════
    def _update_queue_ui(self):
        """动态刷新输入框上方的待处理消息排队列表"""
        if not hasattr(self, 'queue_items_layout') or not hasattr(self, 'queue_container'):
            return

        while self.queue_items_layout.count():
            item = self.queue_items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        q_len = len(self._dev_message_queue)
        if q_len == 0:
            self.queue_container.setVisible(False)
            self.send_btn.setText("发送指令")
            self.send_btn.setEnabled(True)
            self.input_edit.setPlaceholderText("向 AI 智能体提出需求（例如：'在工作空间创建 calc_tool.py 实现计算器'）...")
            if not self._is_generating:
                self.send_btn.setToolTip("")
            else:
                self.send_btn.setToolTip("当前任务正在处理中，发送新需求将自动加入排队序列顺延执行")
            return

        self.queue_container.setVisible(True)
        self.queue_header_lbl.setText("待执行队列")
        if hasattr(self, 'queue_badge_lbl'):
            self.queue_badge_lbl.setText(f"{q_len} 条等待中")

        for idx, item in enumerate(self._dev_message_queue):
            if isinstance(item, tuple):
                if len(item) >= 3:
                    q_text, q_img, q_file = item[0], item[1], item[2]
                elif len(item) == 2:
                    q_text, q_img = item
                    q_file = None
                else:
                    q_text, q_img, q_file = item[0], None, None
            else:
                q_text, q_img, q_file = item, None, None

            row = QFrame()
            row.setFixedHeight(30)
            row.setStyleSheet("""
                QFrame {
                    background-color: #1c2128;
                    border: 1px solid #2d333b;
                    border-radius: 6px;
                }
                QFrame:hover {
                    background-color: #22272e;
                    border-color: #388bfd;
                }
            """)
            r_lay = QHBoxLayout(row)
            r_lay.setContentsMargins(8, 2, 8, 2)
            r_lay.setSpacing(8)

            badge = QLabel(f"#{idx + 1}")
            badge.setStyleSheet("""
                QLabel {
                    background-color: #232a35;
                    color: #58a6ff;
                    font-weight: bold;
                    font-size: 10px;
                    font-family: 'Cascadia Code', Consolas, monospace;
                    border-radius: 3px;
                    padding: 2px 6px;
                }
            """)
            r_lay.addWidget(badge)

            preview = q_text.replace("\n", " ").strip()
            if q_img:
                preview = f"🖼️ {preview}"
            if len(preview) > 65:
                preview = preview[:63] + "..."
            txt_lbl = QLabel(preview)
            txt_lbl.setToolTip(f"{'[附带图片] ' if q_img else ''}{q_text}")
            txt_lbl.setStyleSheet("""
                QLabel {
                    color: #c9d1d9;
                    font-size: 11.5px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
                    background: transparent;
                    border: none;
                }
            """)
            r_lay.addWidget(txt_lbl, 1)

            del_btn = QPushButton("✕")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setToolTip("取消并移除该排队任务")
            del_btn.setFixedSize(20, 20)
            del_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #768390;
                    border: none;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(248, 81, 73, 0.2);
                    color: #ff7b72;
                }
            """)
            del_btn.clicked.connect(lambda checked, i=idx: self._remove_queued_prompt(i))
            r_lay.addWidget(del_btn)

            self.queue_items_layout.addWidget(row)

        self.send_btn.setText(f"排队发送 ({q_len})" if q_len > 1 else "排队发送")
        self.send_btn.setEnabled(True)
        self.send_btn.setToolTip(f"当前任务处理中，已有 {q_len} 条在排队，发送将继续追加至队尾")
        self.input_edit.setPlaceholderText(f"当前任务正在处理中（已排队 {q_len} 条）... 继续输入新需求追加排队")

    def _remove_queued_prompt(self, idx: int):
        """移除排队中的指定指令"""
        if 0 <= idx < len(self._dev_message_queue):
            removed = self._dev_message_queue.pop(idx)
            self._update_queue_ui()
            raw_t = removed[0] if isinstance(removed, tuple) else removed
            short_txt = raw_t[:30] + ("..." if len(raw_t) > 30 else "")
            self.terminal_output.append(
                f"<span style='color:#858585'>已从排队队列中移除需求: <code>{short_txt}</code></span>"
            )

    def _clear_queued_prompts(self, *args):
        """清空所有排队等待的指令"""
        if self._dev_message_queue:
            cnt = len(self._dev_message_queue)
            self._dev_message_queue.clear()
            self._update_queue_ui()
            self.send_btn.setText("发送指令")
            self.input_edit.setPlaceholderText("向 AI 智能体提出需求（支持直接 Ctrl+V 粘贴图片、拖拽图片或点击下方上传）...")
            self.terminal_output.append(
                f"<span style='color:#858585'>已清空待处理排队队列（共移除 {cnt} 条排队指令）</span>"
            )

    def _stop_ai_generation(self, *args):
        """停止当前正在执行的 AI 任务并恢复就绪状态"""
        self._stop_requested = True
        self._is_generating = False
        if hasattr(self, 'stop_btn'):
            self.stop_btn.setVisible(False)
        self.send_btn.setText("发送指令")
        self.send_btn.setEnabled(True)
        self.input_edit.setPlaceholderText("向 AI 智能体提出需求（支持直接 Ctrl+V 粘贴图片、拖拽图片或点击下方上传）...")
        if self._current_traj:
            self._current_traj.set_summary_text("[已停止] 任务已由用户手动中止")
            self._current_traj.set_status("done")
            self._current_traj.add_log("SYSTEM", "用户点击停止，已中止当前生成任务")
        self.terminal_output.append("<span style='color:#e5c07b'><b>[已停止]</b> 任务生成已由用户手动中止。</span>")
        self._update_queue_ui()

    def _send_ai_prompt(self):
        """
        发送或排队 AI 提示词：
        - 若当前模型正在处理中，则自动放入排队队列并在输入框上方卡片展示
        - 若当前空闲，则立即触发流式执行
        """
        text = self.input_edit.toPlainText().strip()
        attached_img = self._attached_image_path
        attached_file = getattr(self, '_attached_file_path', None)
        if not text and not attached_img and not attached_file:
            return

        if not text and attached_img:
            text = "请详细分析识别这张图片中的视觉细节与关键信息。"
        elif not text and attached_file:
            text = f"请详细分析并处理附带的文件【{Path(attached_file).name}】代码实现与架构逻辑。"

        if self._is_generating:
            self._dev_message_queue.append((text, attached_img, attached_file))
            self.input_edit.clear()
            self._clear_attached_image()
            self._update_queue_ui()
            q_len = len(self._dev_message_queue)
            hint_parts = []
            if attached_img:
                hint_parts.append(f"图片 {Path(attached_img).name}")
            if attached_file:
                hint_parts.append(f"文件 {Path(attached_file).name}")
            img_hint = f" [已附带{'、'.join(hint_parts)}]" if hint_parts else ""
            self.terminal_output.append(
                f"<span style='color:#61afef'><b>[指令已排队]</b> 需求{img_hint}已进入等待队列（前方排队 {q_len} 条），当前任务完成后将自动触发执行。</span>"
            )
            return

        self.input_edit.clear()
        self._clear_attached_image()
        self._execute_ai_prompt(text, image_path=attached_img, file_path=attached_file)

    def _execute_ai_prompt(self, text: str, image_path: Optional[str] = None, file_path: Optional[str] = None):
        """真正启动单轮对话的大模型流式推理与工具执行"""
        self._is_generating = True
        self._stop_requested = False
        if hasattr(self, 'stop_btn'):
            self.stop_btn.setVisible(True)
        self._update_queue_ui()
        self._add_user_chat_bubble(text, image_path=image_path, file_path=file_path)

        # 1. 会话生命周期管理：若当前无活跃会话，则自动在 SQLite 中创建新会话
        if not self._current_session_id and self.memory:
            clean_first_line = text.strip().splitlines()[0].strip()
            for prefix in ["/plan", "/review", "请", "帮我", "在工作空间"]:
                if clean_first_line.startswith(prefix):
                    clean_first_line = clean_first_line[len(prefix):].strip()
            auto_title = clean_first_line[:32].strip() or "代码开发任务"
            self._current_session_id = self.memory.create_session(
                title=auto_title,
                workspace_name=self.workspace_root
            )

        # 2. 记录用户本次提问到 SQLite
        if self.memory and self._current_session_id:
            try:
                record_txt = f"[图片附件: {Path(image_path).name}]\n{text}" if image_path else text
                self.memory.add_message(self._current_session_id, "user", record_txt)
            except Exception as e:
                print(f"[DevModeView] 保存用户提问异常: {e}")

        # 3. 提取多轮历史会话记忆并注入 Prompt
        context_memory_section = ""
        if self.memory and self._current_session_id:
            try:
                past_msgs = self.memory.get_session_messages(self._current_session_id)
                prior_msgs = [m for m in past_msgs[:-1] if m.get("content")]
                if prior_msgs:
                    import re
                    recent_history = prior_msgs[-6:]
                    mem_lines = []
                    for hm in recent_history:
                        role_tag = "开发者用户" if hm.get("role") in ("user", "human") else "AI 助手（你）"
                        raw_c = hm.get("content", "")
                        clean_c = re.sub(r':::tool_call:[^:\n]+:[^:\n]+(?::[^:\n]+)?:::', '', raw_c)
                        clean_c = re.sub(r'\[\[WORKSPACE_DIFF:[^\]]+\]\]', '', clean_c)
                        clean_c = re.sub(r'\[\[WORKSPACE_EXPLORE:[^\]]+\]\]', '', clean_c)
                        clean_c = re.sub(r'\[\[WORKSPACE_CMD:[^\]]+\]\]', '', clean_c).strip()
                        if len(clean_c) > 260:
                            clean_c = clean_c[:260] + "..."
                        mem_lines.append(f"- {role_tag}: {clean_c}")

                    if mem_lines:
                        context_memory_section = (
                            f"\n【当前会话多轮历史记忆与前序任务上下文】：\n"
                            + "\n".join(mem_lines) + "\n"
                            f"请在当前回复中保持与上述历史上下文的一致性与连续性，结合前序结论继续推进！\n"
                        )
            except Exception as e:
                print(f"[DevModeView] 提取会话记忆异常: {e}")

        self._req_start_time = time.time()
        self._generated_files = []
        self._tracked_explores = set()
        self._tracked_cmds = set()
        self._tracked_diffs = set()

        # 创建一体化 Antigravity 风格的 AI 回复卡片 (内嵌执行轨迹 + 总结文本 + 底部Review审查胶囊)
        turn_widget = AgentTrajectoryWidget(self, is_dark=getattr(self, 'is_dark', True))
        turn_widget.accept_changes_signal.connect(self._on_accept_trajectory_changes)
        turn_widget.reject_changes_signal.connect(self._on_reject_trajectory_changes)
        turn_widget.open_file_signal.connect(self.open_file_in_editor)
        turn_widget.open_diff_signal.connect(self.open_diff_viewer)
        turn_widget.single_accept_signal.connect(self._on_single_accept)
        turn_widget.single_reject_signal.connect(self._on_single_reject)

        self.chat_v_layout.insertWidget(self.chat_v_layout.count() - 1, turn_widget)
        # 立即按当前主题刷一次：__init__ 内部 setStyleSheet 都是深色，
        # 必须在所有子 widget 创建完之后再覆盖一次。
        try:
            turn_widget.apply_theme(getattr(self, 'is_dark', True))
        except Exception:
            pass

        self._current_traj = turn_widget
        self._current_ai_lbl = turn_widget

        # 判断是否为日常问候或测试打招呼
        raw_stripped = text.strip()
        is_greeting = raw_stripped.lower() in [
            "你好", "您好", "hi", "hello", "在吗", "在不在", "早上好", "下午好", "晚上好",
            "hey", "嗨", "你好呀", "打扰了", "test", "测试", "在?", "在？", "哈喽", "hello world"
        ]
        self._is_greeting_turn = is_greeting

        # 判断是否为 Planning Mode (方案制定) 或 Review Mode (代码审查)
        # 注意：日常问候绝对不能进入方案模式；计划触发词必须是明确要求制定方案的指令
        plan_triggers = [
            "/plan", "制定方案", "实施方案", "架构方案", "计划书",
            "先写方案", "先出方案", "先做方案", "等我同意", "等我确认", "先出计划",
            "先写好计划", "编写好计划", "先设计方案", "先写计划", "先做计划", "先制定计划"
        ]
        is_plan_mode = (
            not is_greeting
            and any(k in text for k in plan_triggers)
            and not text.strip().startswith("我已审阅并正式批准")
        )
        self._is_plan_mode = is_plan_mode
        is_review_mode = not is_greeting and (text.strip().startswith("/review") or "代码审查" in text or "代码评审" in text)

        # 获取当前选中的专业开发者身份设定
        active_persona_id = self.config.get("dev_active_persona", "fullstack_architect")
        if active_persona_id == "fullstack":
            active_persona_id = "fullstack_architect"
        custom_personas = self.config.get("dev_custom_personas", {})
        all_personas = dict(DEFAULT_DEV_PERSONAS)
        all_personas.update(custom_personas)
        persona_info = all_personas.get(active_persona_id) or DEFAULT_DEV_PERSONAS.get("fullstack_architect", {})
        persona_sys_prompt = persona_info.get("prompt") or persona_info.get("system_prompt", "")
        p_name = persona_info.get("name", "全栈架构师")

        # 初始化真实执行日志与状态（绝不使用虚假模板）
        m_name = getattr(self.ai_engine, "model_name", "") or self.config.get("active_model_name", "默认模型")
        if image_path:
            turn_widget.add_log("USER", f"开发需求 [附图片 {Path(image_path).name}]: {text[:50]}")
        else:
            turn_widget.add_log("USER", f"开发需求: {text[:60]}")
        turn_widget.add_log("INFO", f"连接模型 [{m_name}]，激活开发者身份: {p_name}")

        self._seen_first_chunk = False
        self._seen_think_start = False
        self._seen_think_end = False
        self._tracked_running_tools = set()
        self._tracked_done_tools = set()

        if is_plan_mode:
            turn_widget.set_working_status("正在请求大模型生成实施方案 (Planning Mode)...")
        elif is_review_mode:
            turn_widget.set_working_status("正在请求大模型进行代码审查 (Code Review Mode)...")
        else:
            turn_widget.set_working_status("正在连接大模型并发送请求...")

        # 继承办公模式核心红线与用户档案记忆
        user_rules = (self.config.get("user_rules") or self.config.get("custom_rules") or "").strip()
        user_name = (self.config.get("user_name") or "").strip()
        user_memo = (self.config.get("user_memo") or "").strip()

        rules_section = ""
        if user_rules:
            rules_section = (
                f"\n【继承办公模式核心准则与不可逾越红线（最高约束力）】：\n"
                f"{user_rules}\n"
            )
        user_section = ""
        if user_name or user_memo:
            user_section = f"\n【开发者用户偏好与档案】：昵称「{user_name}」，偏好「{user_memo}」\n"

        image_notice = ""
        if image_path:
            image_notice = (
                f"\n【用户上传图片说明】：用户在本次需求中附带了一张本地图片（文件: `{Path(image_path).name}`，完整路径: `{image_path}`）。\n"
                f"图片内容已编码为多模态视觉数据传输给模型进行识别。\n"
            )

        file_notice = ""
        if file_path:
            try:
                af_p = Path(file_path)
                if af_p.exists() and af_p.is_file():
                    try:
                        af_rel = str(af_p.resolve().relative_to(Path(self.workspace_root).resolve()))
                    except Exception:
                        af_rel = af_p.name
                    af_content = af_p.read_text(encoding="utf-8", errors="replace")
                    lines = af_content.splitlines()
                    if len(lines) > 600:
                        af_content = "\n".join(lines[:600]) + f"\n... (已自动截取前 600 行，共 {len(lines)} 行)"
                    file_notice = (
                        f"\n【用户通过 ＋ 按钮附带的文件代码上下文】：\n"
                        f"文件路径: `{af_rel}`\n"
                        f"文件内容:\n```{af_p.suffix.lstrip('.')}\n{af_content}\n```\n"
                    )
            except Exception as e:
                print(f"[DevModeView] 读取附带文件异常: {e}")

        mode_directives = ""
        if is_greeting:
            mode_directives = (
                "\n【当前交互为日常问候/寒暄 (Greeting)】：\n"
                "用户当前仅发送了日常问候或打招呼（如「你好」）。\n"
                "你的职责是：以专业、亲切、简明的全栈开发工程师口吻简要回应（控制在 2~3 句话以内），简要说明你可以提供代码编写、架构设计、Bug 排查及测试验证等开发协助，请用户直接提出具体的工程或代码需求。\n"
                "【严格禁令】：\n"
                "1. 绝对严禁输出任何长篇大论、严禁列出长列表、严禁强行设计实施方案！\n"
                "2. 绝对严禁调用任何工具或生成任何文件！保持简明自然的问答交流即可。\n"
            )
        elif is_plan_mode:
            mode_directives = (
                "\n【当前任务处于专业架构方案制定模式 (Planning Mode)】：\n"
                "用户明确要求：「先编写好计划/方案，等我同意后再执行」！\n"
                "你当前的核心职责是为该需求设计一份严谨、详尽、逻辑闭环的技术落地实施方案（技术设计文档）。\n"
                "【方案制定阶段严禁执行落地与文件写入（最高铁律）】：\n"
                "1. 绝对严禁调用 write_workspace_file 或 modify_workspace_file 创建或修改任何代码文件！\n"
                "2. 绝对严禁调用 run_workspace_command 编译、运行测试或执行任何终端命令！\n"
                "3. 你仅允许使用 read_workspace_file 或 list_workspace_files 进行项目现状调研；\n"
                "4. 你的全部产出必须是当前回复中的技术落地方案 Markdown 文本，系统会自动将其提取并在中间主屏幕渲染为独立方案文档！\n"
                "5. 真正的工程代码文件落地与运行测试，必须且只能等待用户在界面审阅方案并点击【批准并执行 (Process)】后的下一轮对话中进行！\n"
                "请严格遵守以下核心工程规范：\n"
                "1. 【代码语言与格式规范（最高红线）】：\n"
                "   - 严禁使用 ```text 标签倾倒伪代码！严禁使用带有中文冒号、中英文混杂的非可执行伪逻辑！\n"
                "   - 方案中涉及的具体代码块必须严格标注对应的真实语言标识符（如 ```c, ```java, ```python, ```bash 等）；\n"
                "   - 代码块内部必须是语法完备、缩进工整、符合该语言编译标准的真实代码实现，用户直接复制下来即可直接编译/运行！\n"
                "2. 【纯净工程无 Emoji 规范】：\n"
                "   - 全文绝对严禁包含任何 Emoji 图标符号（包括但不限于 🚀、🎨、✨、💡 等），所有标题、阶段与状态必须保持纯文本专业工程风格。\n"
                "3. 【方案详略度自适应原则（严禁过度设计与无端繁琐化）】：\n"
                "   - 若用户需求为简单任务（如单一算法实现、小函数、单个类示例、简单脚本、单点代码修改）：\n"
                "     * 方案必须精炼聚焦！严禁过度设计！\n"
                "     * 严禁无端膨胀设计为 4~5 个多余文件（严禁为了写个简单算法就强行单独建 Demo、Test、bat 脚本、README 文档等一整套庞大工程矩阵）！通常仅需 1 个主源文件即可；\n"
                "     * 方案只需结构清晰简短：① 目标与文件路径；② 核心算法思路与接口骨架（代码块严格 <=20 行）；③ 运行或测试验证方法。\n"
                "   - 只有在多模块系统、大型功能重构等确实复杂的工程场景下，才展开完整的文件变更矩阵与多阶段详细路线图。\n"
                "4. 【代码块规范 - 核心红线】：\n"
                "   - 方案文档中代码块只展示关键接口签名与核心算法骨架（<=20行），严禁倾倒完整超长实现（完整实现留待用户批准后落地阶段生成）；\n"
                "   - 代码块严禁夹带无意义的中间文本，语言标识符（如 ```java）必须紧跟三个反引号。\n"
            )
        elif is_review_mode:
            ed = self._get_current_editor()
            code_ctx = ""
            if ed and ed.current_file_path:
                cur_fname = Path(ed.current_file_path).name
                cursor = ed.textCursor()
                sel = cursor.selectedText().strip()
                if sel:
                    code_ctx = f"\n【待审查文件选中的关键代码片段（文件: {cur_fname}）】：\n```python\n{sel}\n```\n"
                else:
                    raw_code = ed.toPlainText()
                    lines = raw_code.splitlines()
                    if len(lines) > 800:
                        raw_code = "\n".join(lines[:800]) + f"\n... [已自动截取前 800 行，共 {len(lines)} 行]"
                    code_ctx = f"\n【待审查目标文件真实源码（文件: {cur_fname}，共 {len(lines)} 行）】：\n```python\n{raw_code}\n```\n"

            mode_directives = (
                "\n【当前任务处于企业级深度代码审查模式 (Code Review Mode)】：\n"
                f"{code_ctx}"
                "请根据待审查源码，按照以下标准专业结构输出代码体检与审查报告（严禁包含任何 Emoji 图标符号）：\n"
                "1. 【综合健康度评分 (Code Health Score: 0 - 100 分)】：\n"
                "   - 综合评分与核心总评\n"
                "   - 五维雷达得分：规范性 (20分) | 健壮性 (20分) | 性能 (20分) | 安全性 (20分) | 可维护性 (20分)\n"
                "2. 【严重缺陷与 Bug 预警 (Defects & Vulnerabilities)】：\n"
                "   - 按级别标明 `[CRITICAL]` / `[HIGH]` / `[MEDIUM]` / `[LOW]`，明确指出具体行号与潜在危害；\n"
                "3. 【性能瓶颈与算法优化建议 (Performance Bottlenecks)】：\n"
                "   - 指出低效算法或 I/O，给出复杂度改善预期 (如 O(N²) -> O(N))；\n"
                "4. 【边界防御与异常处理漏洞 (Edge Cases & Resilience)】：\n"
                "   - 指出缺失的空指针防御、资源未关闭或异常吞没问题；\n"
                "5. 【重构参考代码与对比 (Refactored Diff)】：\n"
                "   - 提供优雅、规范的重构对比代码（Before vs After 或 Markdown diff 形式）。\n"
            )

        if is_greeting:
            dialogue_rule = "   - 热情简短问候，询问具体编程需求，控制在 3 句话以内，禁止长篇大论与列清单；\n"
        else:
            dialogue_rule = "   - 对话框中只输出精炼专业的【方案总结与架构说明】：包括处理了哪些文件、做了什么修改、设计亮点与测试建议；\n"

        # 构造专业代码开发 Prompt (强力红线禁止长代码倾倒与 Emoji 污染)
        dev_instruction = (
            f"【专业 IDE 代码开发环境提示】：\n"
            f"你当前正在由开发者使用的专业 IDE 代码开发模式下协助编程，当前绑定的项目工作空间物理路径为: `{self.workspace_root}`。\n"
            f"当前你被激活的专业开发者身份为：【{p_name}】。\n"
            f"{rules_section}"
            f"{user_section}"
            f"{context_memory_section}"
            f"{image_notice}"
            f"{file_notice}"
            f"{mode_directives}\n"
            f"【绝对红线规则 - 违者扣除权限】：\n"
            f"1. 【代码写入与落盘规范】：\n"
            f"   - （方案制定 Planning Mode 期间严禁调用任何写入与执行工具）在用户批准执行的落地阶段，任何代码文件的编写与重构必须调用 `write_workspace_file` 工具真实写入工作空间物理文件！\n"
            f"   - 严禁在回答文本中直接粘贴长达几十上百行的全量源码（写入文件后系统会自动在中间主屏幕打开代码视图供开发者调试）。\n"
            f"2. 【工具调用要求】：\n"
            f"   - 深度分析代码使用 `read_workspace_file` (支持 start_line 与 end_line 切片)；\n"
            f"   - 探索项目结构使用 `list_workspace_files`；\n"
            f"   - 在执行落地阶段，编写或修改文件输出标准工具调用：\n"
            f"     ````tool\n"
            f"     {{\"name\": \"write_workspace_file\", \"args\": {{\"file_path\": \"相对路径\", \"content\": \"完整代码\"}}}}\n"
            f"     ````\n"
            f"   - 测试运行命令调用 `run_workspace_command`，例如 `python -m py_compile 文件` 或 `python 测试脚本`；\n"
            f"3. 【对话回复内容要求】：\n"
            f"{dialogue_rule}"
            f"   - 保持语言简练、结构清晰，全部使用中文。\n"
            f"4. 【格式排版红线 - 严禁使用任何 Emoji / 表情图标】：\n"
            f"   - 严禁在标题、小节、列表清单、表格或正文中使用任何 Emoji、彩色图标或图形符号（严禁使用 🎯、📋、🚀、⚠️、🧪、📊、🚨、⚡、🛡️、✨、📌、📐、💡、✅、✔、❌、⏸️ 等任何非文字图标符号）；\n"
            f"   - 所有章节与列表清单仅允许使用标准纯文本、数字标号 (1, 2, 3...)、字母或破折号 (-)，保持专业严肃、严谨规范的企业级工程技术风格！\n\n"
            f"【用户需求】：\n{text}"
        )

        threading.Thread(target=self._ai_stream_worker, args=(dev_instruction, persona_sys_prompt, image_path), daemon=True).start()

    def _ai_stream_worker(self, prompt: str, persona_prompt: str = "", image_path: Optional[str] = None):
        full_text = ""
        loop = None
        last_emit_time = 0.0
        session_tag = f"dev_session_{self._current_session_id}" if self._current_session_id else "dev_ide_task"
        try:
            try:
                from core.security_guard import SecurityGuard
                SecurityGuard.get_instance().set_workspace_root(self.workspace_root)
            except Exception:
                pass

            async def _run():
                nonlocal full_text, last_emit_time
                import time
                async for chunk in self.ai_engine.chat_stream(
                    prompt, session_id=session_tag, persona_prompt=persona_prompt, image_path=image_path
                ):
                    if getattr(self, '_stop_requested', False):
                        break
                    full_text += chunk

                    # 核心性能优化：50ms 流式节流自适应批处理（约 20 FPS），关键标记即刻强刷
                    now = time.time()
                    is_special = any(k in chunk for k in [":::tool_call:", "[[WORKSPACE_", "<think>", "</think>"])
                    if is_special or (now - last_emit_time >= 0.05):
                        last_emit_time = now
                        try:
                            self.ai_chunk_signal.emit(full_text)
                        except RuntimeError:
                            break

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_run())
            if not getattr(self, '_stop_requested', False):
                try:
                    self.ai_done_signal.emit(full_text)
                except RuntimeError:
                    pass
        except Exception as e:
            if not getattr(self, '_stop_requested', False):
                try:
                    self.ai_error_signal.emit(str(e))
                except RuntimeError:
                    pass
        finally:
            if loop:
                try:
                    loop.close()
                except Exception:
                    pass

    def _on_ai_chunk(self, full_text: str):
        if not self._current_traj:
            return

        import re
        import base64

        # 记录首包响应日志 (TTFT)
        if not getattr(self, '_seen_first_chunk', False):
            self._seen_first_chunk = True
            self._current_traj.add_log("RUN", "模型开始流式响应")

        # 0. 实时捕获并更新大模型真实思考过程 (<think>...</think>)
        thought_text = ""
        summary_source = full_text
        if "<think>" in full_text:
            if not getattr(self, '_seen_think_start', False):
                self._seen_think_start = True
                self._current_traj.set_working_status("大模型正在深度思考推理中...")
                self._current_traj.add_log("THINK", "大模型进入思维链深度推理状态")

            if "</think>" in full_text:
                m_th = re.search(r'<think>(.*?)</think>', full_text, flags=re.DOTALL)
                if m_th:
                    thought_text = m_th.group(1).strip()
                summary_source = re.sub(r'<think>.*?</think>', '', full_text, flags=re.DOTALL)
                if not getattr(self, '_seen_think_end', False):
                    self._seen_think_end = True
                    self._current_traj.set_working_status("大模型思考完成，正在生成实施方案与代码...")
                    self._current_traj.add_log("THINK", "大模型思维链推理完成")
                    if hasattr(self._current_traj, 'thought_badge'):
                        self._current_traj.thought_badge.setText("思考完成")
                        self._current_traj.thought_badge.setStyleSheet("background-color: rgba(63, 185, 80, 0.15); color: #3fb950; border-radius: 8px; padding: 1px 6px; font-size: 10px; font-weight: bold;")
            else:
                parts = full_text.split("<think>", 1)
                thought_text = parts[1].strip()
                summary_source = parts[0]

        if thought_text and self._current_traj:
            self._current_traj.set_thought_content(thought_text)

        # 1. 捕获工具调用进度与状态
        if ":::tool_call:running:" in full_text:
            if not hasattr(self, '_tracked_running_tools'):
                self._tracked_running_tools = set()
            for m in re.finditer(r':::tool_call:running:([^:\n]+):([^:\n]+):::', full_text):
                t_name, t_desc = m.groups()
                if (t_name, t_desc) not in self._tracked_running_tools:
                    self._tracked_running_tools.add((t_name, t_desc))
                    if t_name in ["read_workspace_file", "list_workspace_files"]:
                        self._current_traj.set_working_status(f"正在探索工作空间文件: {t_desc}...")
                    elif t_name == "run_workspace_command":
                        self._current_traj.set_working_status("正在执行沙箱终端命令...")
                    else:
                        self._current_traj.set_working_status(f"正在执行工具: {t_desc}...")
                    self._current_traj.add_log("TOOL", f"调用工具 [{t_name}]: {t_desc}")

        if ":::tool_call:done:" in full_text:
            if not hasattr(self, '_tracked_done_tools'):
                self._tracked_done_tools = set()
            for m in re.finditer(r':::tool_call:done:([^:\n]+):([^:\n]+):::', full_text):
                t_name, t_desc = m.groups()
                if (t_name, t_desc) not in self._tracked_done_tools:
                    self._tracked_done_tools.add((t_name, t_desc))
                    self._current_traj.set_working_status(f"工具 [{t_desc}] 执行完成，正在整合结果...")
                    self._current_traj.add_log("TOOL", f"工具 [{t_name}] 数据返回就绪")

        # 2. 捕获文件/目录探索标记 (对齐截图 1、2: Explored 1 file, 1 folder > / Analyzed 🐍 ...)
        if not hasattr(self, '_tracked_explores'):
            self._tracked_explores = set()
        for idx, m in enumerate(re.finditer(r'\[\[WORKSPACE_EXPLORE:([^|]+)\|([^|]*)\|([^\]]+)\]\]', full_text)):
            rel_p, line_range, item_type = m.groups()
            key = (idx, rel_p, line_range, item_type)
            if key not in self._tracked_explores:
                self._tracked_explores.add(key)
                self._current_traj.add_explore_item(rel_p, line_range, item_type)

        # 3. 捕获终端命令执行 (对齐截图 1、2、3: Ran & "python.exe" ... ▾)
        # 支持三段式 cmd|code|out_b64 与二段式 cmd|code
        if not hasattr(self, '_tracked_cmds'):
            self._tracked_cmds = set()
        for idx, m in enumerate(re.finditer(r'\[\[WORKSPACE_CMD:([^|]+)\|([^|]+)\|([^\]]+)\]\]', full_text)):
            cmd_str, code_str, out_b64 = m.groups()
            key = ("3", idx, cmd_str, code_str, out_b64)
            if key not in self._tracked_cmds:
                self._tracked_cmds.add(key)
                try:
                    out_text = base64.b64decode(out_b64).decode("utf-8", errors="replace")
                except Exception:
                    out_text = ""
                exit_c = int(code_str) if (code_str.lstrip("-").isdigit()) else 0
                self._current_traj.add_command_step(cmd_str, out_text, exit_c)

        for idx, m in enumerate(re.finditer(r'\[\[WORKSPACE_CMD:([^|]+)\|([^|\]]+)\]\]', full_text)):
            cmd_str, code_str = m.groups()
            key = ("2", idx, cmd_str, code_str)
            if key not in self._tracked_cmds:
                self._tracked_cmds.add(key)
                exit_c = int(code_str) if (code_str.lstrip("-").isdigit()) else 0
                self._current_traj.add_command_step(cmd_str, f".../Demo/desk_tools > {cmd_str}\n(退出码: {exit_c})", exit_c)

        # 4. 捕获代码落盘差异 (对齐截图 1、2: Edited 🐍 filename +add -del [Open Diff])
        if not hasattr(self, '_tracked_diffs'):
            self._tracked_diffs = set()
        for idx, m in enumerate(re.finditer(r'\[\[WORKSPACE_DIFF:([^|]+)\|([^|]+)\|([^|]+)\|\+([0-9]+)\|-\s*([0-9]+)\]\]', full_text)):
            rel_p, abs_p, status, added, removed = m.groups()
            key = (idx, rel_p, abs_p, status, added, removed)
            if key not in self._tracked_diffs:
                self._tracked_diffs.add(key)
                if abs_p not in self._generated_files:
                    self._generated_files.append(abs_p)
                self._current_traj.add_file_change(rel_p, status, int(added), int(removed), abs_p)

        # 5. 过滤内部协议标记与长代码块，实时流式更新总结文本
        clean_text = re.sub(r':::tool_call:[^:\n]+:[^:\n]+(?::[^:\n]+)?:::', '', summary_source)
        clean_text = re.sub(r'\[\[WORKSPACE_DIFF:[^\]]+\]\]', '', clean_text)
        clean_text = re.sub(r'\[\[WORKSPACE_EXPLORE:[^\]]+\]\]', '', clean_text)
        clean_text = re.sub(r'\[\[WORKSPACE_CMD:[^\]]+\]\]', '', clean_text).strip()

        if clean_text:
            filtered_summary = self._filter_dumped_code_blocks(clean_text)
            self._current_traj.set_summary_text(filtered_summary)
            self._seen_thinking_transition = False  # 正文已恢复，清除过渡标记
        elif getattr(self, '_seen_think_end', False) and not getattr(self, '_seen_thinking_transition', False):
            # 思考已完成但正文尚未到达，显示过渡状态避免用户感知为"卡住"
            self._seen_thinking_transition = True
            self._current_traj.set_summary_text("（大模型正在整理输出...）")

        # 自动滚动到底部
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

    def _on_ai_done(self, full_text: str):
        if getattr(self, '_stop_requested', False):
            self._stop_requested = False
            return

        # 记录思考与推理耗时，顶部折叠为 'Worked for Xs ›' (对齐截图 3)
        cost = max(1.0, time.time() - getattr(self, '_req_start_time', time.time()))

        # 最终清洗总结与思考提取（思考过程绝对隔离，禁止污染正文）
        import re
        clean_content, thought_text = extract_thought_process(full_text)
        if thought_text and self._current_traj:
            self._current_traj.set_thought_content(thought_text)

        clean_text = re.sub(r':::tool_call:[^:\n]+:[^:\n]+(?::[^:\n]+)?:::', '', clean_content)
        clean_text = re.sub(r'\[\[WORKSPACE_DIFF:[^\]]+\]\]', '', clean_text)
        clean_text = re.sub(r'\[\[WORKSPACE_EXPLORE:[^\]]+\]\]', '', clean_text)
        clean_text = re.sub(r'\[\[WORKSPACE_CMD:[^\]]+\]\]', '', clean_text).strip()

        # 兜底保障机制：若去标记后正文为空，根据是否生成文件给出明确状态（绝对不倾倒内部思考）
        if not clean_text:
            if self._generated_files:
                clean_text = f"已成功分析并生成 {len(self._generated_files)} 个代码文件，已在主屏幕编辑器中打开就绪。"
            else:
                clean_text = "（大模型已执行完毕）"

        if self._current_traj:
            # 任务完毕后自动折叠思考面板，只保留顶部消耗时间 Worked for Xs
            self._current_traj.set_thought_time(cost)
            # 方案模式严格判定：
            # 1. 若为日常打招呼/问候轮次，绝对严禁作为方案处理
            # 2. 用户明确发起方案规划模式 (self._is_plan_mode 为 True) 且生成了有效内容
            # 3. 或回复内容极其严格地命中了技术实施方案核心结构
            is_plan = False
            if not getattr(self, '_is_greeting_turn', False):
                if getattr(self, '_is_plan_mode', False):
                    is_plan = True
                elif _is_plan_document(clean_text):
                    is_plan = True
            if is_plan:
                from datetime import datetime as _dt
                _plan_ts = _dt.now().strftime("%Y%m%d_%H%M%S")
                _plan_fname = f"plan_{_plan_ts}.md"
                plans_dir = self._get_plans_dir()
                plan_file_path = str(plans_dir / _plan_fname)
                self._current_plan_file_path = plan_file_path

                # 规划模式核心红线：AI 聊天框只呈现精简的执行步骤与流程总结，完整详细设计文档写入 plans/plan_*.md 并在主屏幕渲染展示
                chat_summary = _generate_plan_chat_summary(clean_text, _plan_fname)
                self._current_traj.set_summary_text(chat_summary)

                # 保存并打开完整的方案文档，使用带时间戳的唯一文件名避免多方案互相覆盖
                clean_full_plan = clean_markdown_tables(strip_emojis(clean_text))
                try:
                    Path(plan_file_path).write_text(clean_full_plan, encoding="utf-8")
                except Exception as e:
                    print(f"[DevModeView] 保存方案文档 {_plan_fname} 失败: {e}")

                self.open_plan_preview(clean_full_plan, plan_file_path)
                self._current_traj.add_plan_proceed_card(
                    on_proceed_fn=lambda: self._execute_plan_proceed(),
                    on_preview_fn=lambda: self.open_plan_preview(clean_full_plan, plan_file_path),
                    plan_file_name=_plan_fname
                )
                # 方案审批门控：暂停队列自动流转，等待用户确认
                self._pending_plan_approval = True
                # 自动执行一次方案文件归类整理与 25 天历史生命周期清理
                try:
                    self._organize_and_cleanup_plans()
                except Exception:
                    pass
            else:
                filtered_summary = clean_markdown_tables(strip_emojis(self._filter_dumped_code_blocks(clean_text)))
                self._current_traj.set_summary_text(filtered_summary)

        # 兜底保障机制：仅在非方案规划模式下，若 _generated_files 为空才扫描本次请求触发期间工作空间生成或更新的代码文件
        if not is_plan and not self._generated_files and hasattr(self, '_req_start_time'):
            try:
                ws = Path(self.workspace_root)
                if ws.exists():
                    for p in ws.rglob("*"):
                        if p.is_file() and not p.name.startswith(".") and not any(part.startswith(".") for part in p.parts):
                            try:
                                if p.stat().st_mtime >= self._req_start_time - 1.5:
                                    abs_str = str(p.resolve())
                                    rel_str = p.relative_to(ws).as_posix()
                                    if abs_str not in self._generated_files:
                                        self._generated_files.append(abs_str)
                                        if self._current_traj:
                                            line_cnt = len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
                                            self._current_traj.add_file_change(rel_str, "新建文件", line_cnt, 0, abs_str)
                            except Exception:
                                pass
            except Exception:
                pass

        # 刷新资源管理器树
        self._refresh_explorer()

        # 仅在非方案规划模式下，如果生成了代码文件，自动在中间编辑器打开并呈现高亮源码
        if not is_plan and self._generated_files:
            for f_path in self._generated_files:
                if Path(f_path).exists() and Path(f_path).is_file():
                    self.open_file_in_editor(f_path)
                    self.terminal_output.append(
                        f"<span style='color:#98c379'><b>[代码实时生成]</b> 文件已落盘并在中间主屏幕编辑器打开: <code>{Path(f_path).name}</code></span>\n"
                        f"可以直接在上方主屏幕编辑修改该代码，或按 <b>F5</b> 立即在下方终端执行！"
                    )

        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

        # 保存本次大模型完整回复至 SQLite 会话持久化库
        if self.memory and self._current_session_id and full_text.strip():
            try:
                self.memory.add_message(self._current_session_id, "assistant", full_text)
            except Exception as e:
                print(f"[DevModeView] 保存助手回复异常: {e}")

        # 核心：检查代码开发模式排队队列是否有等待中的下一条任务，自动流转发送！
        # 方案审批门控：若当前有方案文档待用户批准，等前督查队列首位是否是 proceed 指令
        if getattr(self, '_pending_plan_approval', False):
            # 首位是 proceed 指令（用户已在 AI 忙时点了 Process）→ 放行：清除门控使其在下方正常入队逻辑执行
            _q_front_is_proceed = False
            if self._dev_message_queue:
                _peek = self._dev_message_queue[0]
                _peek_text = _peek[0] if isinstance(_peek, tuple) else _peek
                if isinstance(_peek_text, str) and _peek_text.startswith("我已审阅并正式批准"):
                    _q_front_is_proceed = True
            if not _q_front_is_proceed:
                # 非 proceed 队列项——普通门控逻辑：暂停自动流转
                self._is_generating = False
                if hasattr(self, 'stop_btn'):
                    self.stop_btn.setVisible(False)
                self.send_btn.setEnabled(True)
                self.send_btn.setText("发送指令")
                if self._dev_message_queue:
                    cnt = len(self._dev_message_queue)
                    self.terminal_output.append(
                        f"<span style='color:#e5c07b'><b>[队列已暂停]</b> 方案文档待您审批，批准或关闭方案后将自动执行剩余 {cnt} 条排队指令。</span>"
                    )
                self._update_queue_ui()
                return
            # 队首是 proceed：先清除门控再正常进入队列处理逻辑
            self._pending_plan_approval = False

        if self._dev_message_queue:
            next_item = self._dev_message_queue.pop(0)
            if isinstance(next_item, tuple):
                if len(next_item) == 3:
                    next_text, next_img, next_file = next_item
                elif len(next_item) == 2:
                    next_text, next_img = next_item
                    next_file = None
                else:
                    next_text, next_img, next_file = next_item[0], None, None
            else:
                next_text, next_img, next_file = next_item, None, None
            self._update_queue_ui()
            q_rem = len(self._dev_message_queue)
            self.terminal_output.append(
                f"<span style='color:#98c379'><b>[队列自动流转]</b> 上一任务已完成，自动发送并开始处理排队的下一条指令（队列剩余 {q_rem} 条）</span>"
            )
            QTimer.singleShot(150, lambda: self._execute_ai_prompt(next_text, image_path=next_img, file_path=next_file))
        else:
            self._is_generating = False
            if hasattr(self, 'stop_btn'):
                self.stop_btn.setVisible(False)
            self.send_btn.setEnabled(True)
            self.send_btn.setText("发送指令")
            self.input_edit.setPlaceholderText("向 AI 智能体提出需求（点击 ＋ 添加文件或图片、支持 Ctrl+V 粘贴与拖拽）...")
            self._update_queue_ui()

    def _on_ai_error(self, err: str):
        if getattr(self, '_stop_requested', False):
            self._stop_requested = False
            return

        if self._current_traj:
            self._current_traj.add_log("ERROR", f"调用异常: {err}")
            self._current_traj.set_working_status("生成异常中断")
            self._current_traj.set_summary_text(f"[大模型推理异常] {err}")
        self.terminal_output.append(f"<span style='color:#e06c75'>[AI 生成异常] {err}</span>")

        # 遇到错误时，若队列中仍有排队消息，继续自动流转处理下一条
        if self._dev_message_queue:
            next_item = self._dev_message_queue.pop(0)
            if isinstance(next_item, tuple):
                if len(next_item) == 3:
                    next_text, next_img, next_file = next_item
                elif len(next_item) == 2:
                    next_text, next_img = next_item
                    next_file = None
                else:
                    next_text, next_img, next_file = next_item[0], None, None
            else:
                next_text, next_img, next_file = next_item, None, None
            self._update_queue_ui()
            q_rem = len(self._dev_message_queue)
            self.terminal_output.append(
                f"<span style='color:#e5c07b'><b>[异常流转]</b> 上一任务发生异常，自动流转至排队的下一条指令（队列剩余 {q_rem} 条）</span>"
            )
            QTimer.singleShot(150, lambda: self._execute_ai_prompt(next_text, image_path=next_img, file_path=next_file))
        else:
            self._is_generating = False
            if hasattr(self, 'stop_btn'):
                self.stop_btn.setVisible(False)
            self.send_btn.setEnabled(True)
            self.send_btn.setText("发送指令")
            self.input_edit.setPlaceholderText("向 AI 智能体提出需求（点击 ＋ 添加文件或图片、支持 Ctrl+V 粘贴与拖拽）...")
            self._update_queue_ui()


    def _add_user_chat_bubble(self, text: str, image_path: Optional[str] = None, file_path: Optional[str] = None):
        box = QFrame()
        box.setObjectName("UserChatBubble")
        # 用 self.is_dark 参数化：light 主题下白底深字，dark 主题下深底亮字
        d = self.is_dark
        if d:
            box_bg, box_border = '#262626', '#333333'
            text_color = '#f0f6fc'
            fcard_bg, fcard_border = '#1a1e24', '#283344'
            img_bg, img_border = '#1a1a1a', '#3d3d3d'
        else:
            box_bg, box_border = '#f1f5f9', '#cbd5e1'
            text_color = '#1f2328'
            fcard_bg, fcard_border = '#eff6ff', '#bfdbfe'
            img_bg, img_border = '#f8fafc', '#cbd5e1'
        box.setStyleSheet(f"""
            QFrame {{
                background-color: {box_bg};
                border: 1px solid {box_border};
                border-radius: 6px;
                padding: 10px 14px;
                margin: 4px 0;
            }}
        """)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        if file_path and Path(file_path).exists():
            fp_ = Path(file_path)
            f_card = QFrame()
            f_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {fcard_bg};
                    border: 1px solid {fcard_border};
                    border-radius: 6px;
                }}
            """)
            fc_lay = QHBoxLayout(f_card)
            fc_lay.setContentsMargins(10, 6, 10, 6)
            fc_lay.setSpacing(8)

            f_icon = QLabel("📄")
            f_icon.setStyleSheet("font-size: 14px; background: transparent; border: none;")
            fc_lay.addWidget(f_icon)

            sz_b = fp_.stat().st_size
            sz_t = f"{sz_b / 1024:.1f} KB" if sz_b >= 1024 else f"{sz_b} B"
            meta_lbl = QLabel(f"<b>{fp_.name}</b> <span style='color:{'#8b949e' if d else '#64748b'}; font-size:11px;'>({sz_t})</span>")
            meta_lbl.setStyleSheet(f"color: {'#79c0ff' if d else '#1d4ed8'}; font-size: 12px; background: transparent; border: none;")
            fc_lay.addWidget(meta_lbl, 1)

            btn_open = QPushButton("查看 ›")
            btn_open.setCursor(Qt.PointingHandCursor)
            btn_open.setStyleSheet(f"background: transparent; color: {'#58a6ff' if d else '#1d4ed8'}; border: none; font-size: 11px;")
            btn_open.clicked.connect(lambda checked, p=file_path: self.open_file_in_editor(p))
            fc_lay.addWidget(btn_open)

            lay.addWidget(f_card)
            box._f_card = f_card
            box._btn_open = btn_open

        if image_path and Path(image_path).exists():
            img_card = QFrame()
            img_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {img_bg};
                    border: 1px solid {img_border};
                    border-radius: 6px;
                }}
            """)
            ic_lay = QHBoxLayout(img_card)
            ic_lay.setContentsMargins(6, 6, 6, 6)
            ic_lay.setSpacing(10)

            img_lbl = QLabel()
            pix = QPixmap(str(image_path))
            if not pix.isNull():
                if pix.width() > 240 or pix.height() > 180:
                    pix = pix.scaled(240, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_lbl.setPixmap(pix)
            ic_lay.addWidget(img_lbl)

            p = Path(image_path)
            sz_b = p.stat().st_size
            sz_t = f"{sz_b / 1024:.1f} KB" if sz_b >= 1024 else f"{sz_b} B"
            meta_lbl = QLabel(f"<b>🖼️ {p.name}</b><br><span style='color:{'#8b949e' if d else '#64748b'}; font-size:11px;'>文件大小: {sz_t}</span>")
            meta_lbl.setStyleSheet(f"color: {'#e6edf3' if d else '#1f2328'}; font-size: 12px; background: transparent; border: none;")
            ic_lay.addWidget(meta_lbl, 1)

            lay.addWidget(img_card)
            box._img_card = img_card

        if text:
            lbl = QLabel(text)
            lbl.setObjectName("UserChatText")
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lbl.setStyleSheet(f"""
                color: {text_color};
                font-size: 12.5px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.45;
                background: transparent;
                border: none;
            """)
            lay.addWidget(lbl)
            box._text_lbl = lbl

        self.chat_v_layout.insertWidget(self.chat_v_layout.count() - 1, box)
        # 保存 box 引用：apply_theme 时刷新所有用户气泡
        if not hasattr(self, '_user_bubbles') or self._user_bubbles is None:
            self._user_bubbles = []
        self._user_bubbles.append(box)
        # 立即刷一次（确保正确颜色）
        try:
            self._refresh_user_bubble(box, d)
        except Exception:
            pass

    def _refresh_user_bubble(self, box, d: bool):
        """根据 d 重新设 box 样式及文字颜色（用于 apply_theme 统一刷新所有用户气泡）"""
        if d:
            box_bg, box_border = '#262626', '#333333'
            text_color = '#f0f6fc'  # 纯净亮白，在深色背景上极其清晰醒目
            fcard_bg, fcard_border = '#1a1e24', '#283344'
            fcard_text = '#79c0ff'
            fcard_btn = '#58a6ff'
            img_bg, img_border = '#1a1a1a', '#3d3d3d'
            img_text = '#e6edf3'
        else:
            box_bg, box_border = '#f1f5f9', '#cbd5e1'
            text_color = '#1f2328'  # 深灰黑，在浅色背景上清晰锐利
            fcard_bg, fcard_border = '#eff6ff', '#bfdbfe'
            fcard_text = '#1d4ed8'
            fcard_btn = '#1d4ed8'
            img_bg, img_border = '#f8fafc', '#cbd5e1'
            img_text = '#1f2328'

        try:
            box.setStyleSheet(f"""
                QFrame {{
                    background-color: {box_bg};
                    border: 1px solid {box_border};
                    border-radius: 6px;
                    padding: 10px 14px;
                    margin: 4px 0;
                }}
            """)
        except Exception:
            pass

        # 1. 刷新文本标签
        text_lbl = getattr(box, '_text_lbl', None)
        if text_lbl is not None:
            try:
                text_lbl.setStyleSheet(f"""
                    color: {text_color};
                    font-size: 12.5px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    line-height: 1.45;
                    background: transparent;
                    border: none;
                """)
            except Exception:
                pass

        # 2. 遍历 box 中所有 QLabel（确保不论何时创建的文本标签均同步更新）
        try:
            for child in box.findChildren(QLabel):
                if child is text_lbl:
                    continue
                txt = child.text() or ""
                # 排除纯 emoji 图标与图片展示控件
                if txt in ("📄", "🖼️") or child.pixmap() is not None:
                    continue
                # 区分附件 meta 与正文
                if "🖼️" in txt:
                    child.setStyleSheet(f"color: {img_text}; font-size: 12px; background: transparent; border: none;")
                elif "<b>" in txt:
                    child.setStyleSheet(f"color: {fcard_text}; font-size: 12px; background: transparent; border: none;")
                else:
                    child.setStyleSheet(f"""
                        color: {text_color};
                        font-size: 12.5px;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                        line-height: 1.45;
                        background: transparent;
                        border: none;
                    """)
        except Exception:
            pass

        # 3. 刷新文件/图片附件卡片 QFrame 与按钮
        f_card = getattr(box, '_f_card', None)
        if f_card is not None:
            try:
                f_card.setStyleSheet(f"background-color: {fcard_bg}; border: 1px solid {fcard_border}; border-radius: 6px;")
            except Exception:
                pass
        btn_open = getattr(box, '_btn_open', None)
        if btn_open is not None:
            try:
                btn_open.setStyleSheet(f"background: transparent; color: {fcard_btn}; border: none; font-size: 11px;")
            except Exception:
                pass
        img_card = getattr(box, '_img_card', None)
        if img_card is not None:
            try:
                img_card.setStyleSheet(f"background-color: {img_bg}; border: 1px solid {img_border}; border-radius: 6px;")
            except Exception:
                pass

    def _add_ai_chat_bubble(self, text: str) -> QLabel:
        box = QFrame()
        d = self.is_dark
        if d:
            box_bg, box_border = '#252526', '#333842'
            text_color = '#cccccc'
        else:
            box_bg, box_border = '#f8fafc', '#cbd5e1'
            text_color = '#1f2328'
        box.setStyleSheet(f"""
            QFrame {{
                background-color: {box_bg};
                border: 1px solid {box_border};
                border-radius: 8px;
                padding: 8px 12px;
            }}
        """)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl.setStyleSheet(f"color: {text_color}; font-size: 12px; font-family: 'Segoe UI', 'Microsoft YaHei UI';")
        lay.addWidget(lbl)
        self.chat_v_layout.insertWidget(self.chat_v_layout.count() - 1, box)
        # 保存 box 引用：apply_theme 时刷新所有 AI 气泡
        if not hasattr(self, '_ai_bubbles') or self._ai_bubbles is None:
            self._ai_bubbles = []
        self._ai_bubbles.append(box)
        return lbl

    def _clear_ai_chat(self):
        """兼容旧调用：触发新建任务会话"""
        self._action_new_conversation()

    def _init_session_state(self):
        """启动时自动载入当前工作空间最近的历史会话（若有）"""
        if not self.memory:
            return
        try:
            sessions = self.memory.get_all_sessions()
            matched = [s for s in sessions if s.get("workspace_name") == self.workspace_root]
            target = matched[0] if matched else (sessions[0] if sessions else None)
            if target:
                self._load_session(target["id"], initial_load=True)
        except Exception as e:
            print(f"[DevModeView] 初始化会话状态异常: {e}")

    def _action_new_conversation(self):
        """开启全新会话任务，旧会话安全保存在 SQLite 数据库中"""
        self._dev_message_queue.clear()
        self._update_queue_ui()
        self._current_session_id = None
        self._clear_ai_chat_ui_only()
        self.input_edit.clear()
        self.terminal_output.append(
            "<span style='color:#79c0ff'><b>[新建任务会话]</b> 已开启全新对话任务。历史会话已自动归档至「会话历史」中，点击上方时钟图标即可随时查阅与切换。</span>"
        )

    def _clear_ai_chat_ui_only(self):
        """仅清空界面上的消息卡片控件，不改变会话 ID"""
        self._user_bubbles = []
        self._ai_bubbles = []
        while self.chat_v_layout.count() > 1:
            item = self.chat_v_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _load_session(self, session_id: int, initial_load: bool = False):
        """载入并恢复历史会话的所有对话与轨迹记录"""
        if not self.memory:
            return

        if self._current_session_id == session_id and not initial_load:
            return

        sess = self.memory.get_session(session_id)
        if not sess:
            return

        self._current_session_id = session_id
        messages = self.memory.get_session_messages(session_id)

        # 核心性能优化：冻结滚动区域重绘，批量清理与恢复完成后统一刷新，彻底杜绝切换卡顿
        self.chat_scroll.setUpdatesEnabled(False)
        try:
            # 清空当前界面卡片
            self._clear_ai_chat_ui_only()

            # 逐一恢复对话记录
            if messages:
                for m in messages:
                    role = m.get("role", "")
                    content = m.get("content", "")
                    if role in ("user", "human"):
                        self._add_user_chat_bubble(content)
                    elif role in ("assistant", "ai"):
                        self._restore_assistant_turn(content)

                # 同步大模型的多轮上下文隔离记忆
                if self.ai_engine:
                    sid_key = f"dev_session_{session_id}"
                    hist_records = [
                        {"role": ("user" if m.get("role") in ("user", "human") else "assistant"),
                         "content": m.get("content", "")}
                        for m in messages
                    ]
                    if hasattr(self.ai_engine, "session_histories"):
                        self.ai_engine.session_histories[sid_key] = hist_records
                    if hasattr(self.ai_engine, "conversation_history"):
                        self.ai_engine.conversation_history = list(hist_records)
        finally:
            self.chat_scroll.setUpdatesEnabled(True)

        # 滚动到底部
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

        title = sess.get("title", "未命名会话")
        if not initial_load:
            self.terminal_output.append(
                f"<span style='color:#61afef'><b>[会话历史恢复]</b> 已载入会话「{title}」（共 {len(messages)} 条对话记录）</span>"
            )

    def _restore_assistant_turn(self, content: str):
        """从持久化存储的助手消息中完整恢复 AgentTrajectoryWidget 轨迹与卡片"""
        import re
        import base64

        turn_widget = AgentTrajectoryWidget(self, is_dark=getattr(self, 'is_dark', True))
        turn_widget.accept_changes_signal.connect(self._on_accept_trajectory_changes)
        turn_widget.reject_changes_signal.connect(self._on_reject_trajectory_changes)
        turn_widget.open_file_signal.connect(self.open_file_in_editor)
        turn_widget.open_diff_signal.connect(self.open_diff_viewer)
        turn_widget.single_accept_signal.connect(self._on_single_accept)
        turn_widget.single_reject_signal.connect(self._on_single_reject)

        # 1. 恢复探索与文件分析
        for m in re.finditer(r'\[\[WORKSPACE_EXPLORE:([^|]+)\|([^|]*)\|([^\]]+)\]\]', content):
            rel_p, line_range, item_type = m.groups()
            turn_widget.add_explore_item(rel_p, line_range, item_type)

        # 2. 恢复终端命令执行
        for m in re.finditer(r'\[\[WORKSPACE_CMD:([^|]+)\|([^|]+)\|([^\]]+)\]\]', content):
            cmd_str, code_str, out_b64 = m.groups()
            try:
                out_text = base64.b64decode(out_b64).decode("utf-8", errors="replace")
            except Exception:
                out_text = ""
            exit_c = int(code_str) if (code_str.lstrip("-").isdigit()) else 0
            turn_widget.add_command_step(cmd_str, out_text, exit_c)

        for m in re.finditer(r'\[\[WORKSPACE_CMD:([^|]+)\|([^|\]]+)\]\]', content):
            cmd_str, code_str = m.groups()
            exit_c = int(code_str) if (code_str.lstrip("-").isdigit()) else 0
            turn_widget.add_command_step(cmd_str, f".../Demo/desk_tools > {cmd_str}\n(退出码: {exit_c})", exit_c)

        # 3. 恢复代码落盘差异
        for m in re.finditer(r'\[\[WORKSPACE_DIFF:([^|]+)\|([^|]+)\|([^|]+)\|\+([0-9]+)\|-\s*([0-9]+)\]\]', content):
            rel_p, abs_p, status, added, removed = m.groups()
            turn_widget.add_file_change(rel_p, status, int(added), int(removed), abs_p)

        # 4. 恢复方案总结（深度提取并隔离思考过程，杜绝思考链污染主回复与表格）
        clean_content, thought_text = extract_thought_process(content)
        if thought_text:
            turn_widget.set_thought_content(thought_text)

        clean_text = re.sub(r':::tool_call:[^:\n]+:[^:\n]+(?::[^:\n]+)?:::', '', clean_content)
        clean_text = re.sub(r'\[\[WORKSPACE_DIFF:[^\]]+\]\]', '', clean_text)
        clean_text = re.sub(r'\[\[WORKSPACE_EXPLORE:[^\]]+\]\]', '', clean_text)
        clean_text = re.sub(r'\[\[WORKSPACE_CMD:[^\]]+\]\]', '', clean_text).strip()
        clean_text = clean_markdown_tables(clean_text)

        if clean_text:
            if _is_plan_document(clean_text):
                # 方案规划记录恢复：使用方案精炼概要 + 方案就绪卡片，绝对不倾倒全量文档
                matched_fname = "implementation_plan.md"
                try:
                    ws_plans = sorted(Path(self.workspace_root).glob("plan_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
                    if ws_plans:
                        matched_fname = ws_plans[0].name
                except Exception:
                    pass
                plan_file_path = str(Path(self.workspace_root) / matched_fname)
                chat_summary = _generate_plan_chat_summary(clean_text, matched_fname)
                turn_widget.set_summary_text(chat_summary)
                turn_widget.add_plan_proceed_card(
                    on_proceed_fn=lambda: self._execute_plan_proceed(),
                    on_preview_fn=lambda: self.open_plan_preview(clean_text, plan_file_path),
                    plan_file_name=matched_fname
                )
            else:
                filtered_summary = clean_markdown_tables(strip_emojis(self._filter_dumped_code_blocks(clean_text)))
                turn_widget.set_summary_text(filtered_summary)

        # 历史记录完成状态自动折叠思考面板，绝不暴露思考过程
        turn_widget.set_thought_time(12.5)

        self.chat_v_layout.insertWidget(self.chat_v_layout.count() - 1, turn_widget)
        # 立即按当前主题刷一次：__init__ 内部 setStyleSheet 都是深色，
        # 必须在所有子 widget 创建完之后再覆盖一次。
        try:
            turn_widget.apply_theme(getattr(self, 'is_dark', True))
        except Exception:
            pass

    def _open_past_conversations_dialog(self):
        """弹出 Antigravity IDE 风格的 Past Conversations 历史会话对话框"""
        if not self.memory:
            return
        dlg = PastConversationsDialog(
            memory_manager=self.memory,
            current_session_id=self._current_session_id,
            workspace_root=self.workspace_root,
            parent=self
        )
        dlg.session_selected.connect(self._load_session)
        dlg.session_deleted.connect(self._on_session_deleted)

        # 精确计算弹出位置：贴合 self.btn_history 按钮下方
        btn_pos = self.btn_history.mapToGlobal(QPoint(0, 0))
        btn_rect = self.btn_history.rect()

        popup_x = btn_pos.x() + btn_rect.width() - dlg.width()
        popup_y = btn_pos.y() + btn_rect.height() + 4

        screen_geom = QApplication.desktop().availableGeometry(self.btn_history)
        if popup_x < screen_geom.left() + 10:
            popup_x = screen_geom.left() + 10
        if popup_x + dlg.width() > screen_geom.right() - 10:
            popup_x = screen_geom.right() - 10 - dlg.width()
        if popup_y + dlg.height() > screen_geom.bottom() - 10:
            popup_y = btn_pos.y() - dlg.height() - 4

        dlg.move(popup_x, popup_y)
        dlg.exec_()

    def _on_session_deleted(self, session_id: int):
        """会话被删除时的回调处理"""
        if session_id == self._current_session_id:
            self._action_new_conversation()
