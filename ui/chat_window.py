# -*- coding: utf-8 -*-
"""
NovaDesk v3.0 - 全功能桌面 AI 工作台 (WorkBuddy 级像素复刻)
- 聊天主页：空态悬浮居中输入框 vs 对话态底部固定输入框双态无缝切换
- 消息展示：纯净 Markdown 优雅排版 + 底部快捷工具条 (复制/点赞/点踩/朗读/重试/Token统计)
- 技能与专家大厅：分类胶囊、专家卡片一键召唤、技能卡片
- 「我安装的」专属管理页：带面包屑返回、开关 Switch、搜索与管理
- 工作空间管理器：支持多空间搜索、切换、新建与本地文件夹关联，侧边栏空间联动
- 自动化流：真实 PetScheduler 定时任务集成与运行记录
- 模型与设置：与 config.models_list 真实同步，测试连接，增删改查
- 侧边栏：历史会话点击即入、重命名、导出、删除、任务数量动态更新
"""
import sys
import os
import re
import json
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
        QLineEdit, QTextEdit, QScrollArea, QFrame, QApplication, QStackedWidget,
        QSplitter, QTableWidget, QTableWidgetItem, QComboBox, QFormLayout,
        QListWidget, QListWidgetItem, QHeaderView, QMessageBox, QFileDialog,
        QSizePolicy, QDialog, QGraphicsDropShadowEffect, QMenu, QAction,
        QInputDialog, QCheckBox, QSpinBox, QTimeEdit, QDateEdit, QDialogButtonBox,
        QTabWidget, QScrollBar, QToolButton, QGraphicsOpacityEffect
    )
    from PyQt5.QtCore import (
        Qt, pyqtSignal, QPoint, QPointF, QRectF, QTimer, QSize, QRect, QTime, QDate,
        QPropertyAnimation, QEasingCurve, pyqtProperty
    )
    from PyQt5.QtGui import (
        QFont, QColor, QIcon, QPainter, QPainterPath, QPen, QBrush, QPixmap,
        QCursor, QTextCursor, QFontMetrics, QLinearGradient
    )
except ImportError:
    pass

ROOT_DIR = Path(__file__).parent.parent
ICON_PATH = ROOT_DIR / "assets" / "icons" / "pet_icon.png"
MCP_CONFIG_PATH = ROOT_DIR / "mcp_config.json"
SKILLS_DIR = ROOT_DIR / "skills"
AUTO_LOG_PATH = ROOT_DIR / "data" / "auto_run_log.json"


# ─────────────────────────── 工具函数 ───────────────────────────

def format_relative_time(dt_str: str) -> str:
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


def load_skills_from_dir() -> List[Dict]:
    """读取 skills/ 目录下所有技能的 SKILL.md frontmatter"""
    result = []
    if not SKILLS_DIR.exists():
        return result
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            try:
                text = skill_md.read_text(encoding="utf-8")
                meta = _parse_frontmatter(text)
                result.append({
                    "id": skill_dir.name,
                    "name": meta.get("name", skill_dir.name),
                    "description": meta.get("description", ""),
                    "version": meta.get("version", "1.0"),
                    "tools": meta.get("tools", []),
                    "path": str(skill_dir),
                })
            except Exception:
                pass
    return result


def _parse_frontmatter(text: str) -> Dict:
    meta = {}
    if not text.startswith("---"):
        return meta
    end = text.find("---", 3)
    if end == -1:
        return meta
    block = text[3:end].strip()
    for line in block.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k == "tools":
                continue
            meta[k] = v
    tools = []
    in_tools = False
    for line in block.splitlines():
        if line.strip().startswith("tools:"):
            in_tools = True
            continue
        if in_tools:
            stripped = line.strip()
            if stripped.startswith("- "):
                tools.append(stripped[2:])
            elif stripped and not stripped.startswith(" "):
                in_tools = False
    if tools:
        meta["tools"] = tools
    return meta


def load_auto_log() -> List[Dict]:
    try:
        if AUTO_LOG_PATH.exists():
            with open(AUTO_LOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def save_auto_log(log: List[Dict]):
    try:
        AUTO_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(AUTO_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log[-200:], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[AutoLog] save error: {e}")


# ─────────────────────────── 现代化开关组件 (Switch) ───────────────────────────

class ToggleSwitch(QWidget):
    """精美平滑过渡开关"""
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedSize(42, 22)
        self.setCursor(Qt.PointingHandCursor)
        self._checked = checked
        self._thumb_position = 20 if checked else 2

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self._thumb_position = 20 if checked else 2
            self.update()
            self.toggled.emit(self._checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景底轨
        track_color = QColor("#10b981") if self._checked else QColor("#cbd5e1")
        painter.setBrush(QBrush(track_color))
        painter.setPen(Qt.NoPen)
        rect = QRectF(0, 0, self.width(), self.height())
        painter.drawRoundedRect(rect, self.height() / 2, self.height() / 2)

        # 白色滑块
        painter.setBrush(QBrush(QColor("#ffffff")))
        thumb_size = self.height() - 4
        thumb_x = 22 if self._checked else 2
        painter.drawEllipse(QRectF(thumb_x, 2, thumb_size, thumb_size))


# ─────────────────────────── 可拖拽标题栏 ───────────────────────────

class DraggableTopBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            win = self.window()
            if win and not getattr(win, '_is_maximized', False):
                self._drag_pos = event.globalPos() - win.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and (event.buttons() & Qt.LeftButton):
            win = self.window()
            if win and not getattr(win, '_is_maximized', False):
                win.move(event.globalPos() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


# ─────────────────────────── 聊天输入框 ───────────────────────────

class ChatTextEdit(QTextEdit):
    return_pressed = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.return_pressed.emit()
                event.accept()
        else:
            super().keyPressEvent(event)


# ─────────────────────────── 工作空间选择与管理浮窗 ───────────────────────────

class WorkspaceSelectorPopup(QWidget):
    workspace_selected = pyqtSignal(dict)
    create_new_requested = pyqtSignal()
    open_folder_requested = pyqtSignal()

    def __init__(self, workspaces: List[dict], current_name: str = "", is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.workspaces = workspaces
        self.current_name = current_name
        self.is_dark = is_dark
        self.setFixedWidth(280)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        card = QFrame(self)
        card.setObjectName("WsPopupCard")
        bg_color = "rgba(15,23,42,0.97)" if self.is_dark else "rgba(255,255,255,0.98)"
        border_color = "#334155" if self.is_dark else "#e2e8f0"
        card.setStyleSheet(f"""
            QFrame#WsPopupCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 14px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 6)
        card.setGraphicsEffect(shadow)

        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(10, 10, 10, 10)
        c_lay.setSpacing(6)

        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 搜索工作空间")
        self.search_edit.setFixedHeight(32)
        inp_bg = "#1e293b" if self.is_dark else "#f8fafc"
        fg = "#e2e8f0" if self.is_dark else "#0f172a"
        self.search_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {inp_bg};
                color: {fg};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
        """)
        self.search_edit.textChanged.connect(self._filter_list)
        c_lay.addWidget(self.search_edit)

        # 列表区域
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(2)
        c_lay.addWidget(self.list_container)

        self._render_items(self.workspaces)

        # 分割线
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(0,0,0,0.06); min-height: 1px; max-height: 1px; margin: 4px 0;")
        c_lay.addWidget(sep)

        # 底部操作按钮
        btn_style = f"""
            QPushButton {{
                background: transparent;
                color: {fg};
                border: none;
                border-radius: 8px;
                padding: 7px 10px;
                text-align: left;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{
                background: {'#1e293b' if self.is_dark else '#f1f5f9'};
            }}
        """

        add_btn = QPushButton("＋  新建工作空间")
        add_btn.setStyleSheet(btn_style)
        add_btn.clicked.connect(self._on_create_new)
        c_lay.addWidget(add_btn)

        open_btn = QPushButton("📁  打开本地文件夹")
        open_btn.setStyleSheet(btn_style)
        open_btn.clicked.connect(self._on_open_folder)
        c_lay.addWidget(open_btn)

        layout.addWidget(card)

    def _render_items(self, items: List[dict]):
        for i in reversed(range(self.list_layout.count())):
            w = self.list_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        fg = "#e2e8f0" if self.is_dark else "#0f172a"
        for ws in items:
            name = ws.get("name", "未命名")
            is_current = (name == self.current_name)
            btn = QPushButton(f"📁  {name}")
            btn.setFixedHeight(32)
            bg = "#1e293b" if (self.is_dark and is_current) else ("#eff6ff" if is_current else "transparent")
            text_c = "#6366f1" if is_current else fg
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    color: {text_c};
                    border: none;
                    border-radius: 8px;
                    padding: 0 10px;
                    text-align: left;
                    font-size: 12.5px;
                    font-weight: {'bold' if is_current else 'normal'};
                    font-family: 'Microsoft YaHei UI';
                }}
                QPushButton:hover {{
                    background-color: {'#334155' if self.is_dark else '#f1f5f9'};
                }}
            """)
            btn.clicked.connect(lambda ch, w_=ws: self._select_workspace(w_))
            self.list_layout.addWidget(btn)

    def _filter_list(self, text: str):
        kw = text.strip().lower()
        filtered = [ws for ws in self.workspaces if kw in ws.get("name", "").lower()]
        self._render_items(filtered)

    def _select_workspace(self, ws: dict):
        self.workspace_selected.emit(ws)
        self.close()

    def _on_create_new(self):
        self.create_new_requested.emit()
        self.close()

    def _on_open_folder(self):
        self.open_folder_requested.emit()
        self.close()


# ─────────────────────────── 安全权限切换弹窗 ───────────────────────────

class PermissionPopupCard(QWidget):
    permission_changed = pyqtSignal(str)

    def __init__(self, current_perm: str = "standard", is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.current_perm = current_perm
        self.is_dark = is_dark
        self.setFixedWidth(290)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        card = QFrame(self)
        card.setObjectName("PermCard")
        bg_color = "rgba(15,23,42,0.97)" if self.is_dark else "rgba(255,255,255,0.98)"
        border_color = "#334155" if self.is_dark else "#e2e8f0"
        text_main = "#e2e8f0" if self.is_dark else "#0f172a"
        text_sub = "#94a3b8" if self.is_dark else "#64748b"
        card.setStyleSheet(f"""
            QFrame#PermCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 14px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 90))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(16, 14, 16, 14)
        c_layout.setSpacing(10)

        title_lbl = QLabel("🛡️ 安全权限管理")
        title_lbl.setStyleSheet(f"color: {text_main}; font-size: 13px; font-weight: bold; font-family: 'Microsoft YaHei UI';")
        c_layout.addWidget(title_lbl)

        self.desc_lbl = QLabel()
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet(f"color: {text_sub}; font-size: 11.5px; line-height: 1.5; font-family: 'Microsoft YaHei UI';")
        c_layout.addWidget(self.desc_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(0,0,0,0.08); min-height: 1px; max-height: 1px;")
        c_layout.addWidget(sep)

        row = QHBoxLayout()
        row_lbl = QLabel("允许完全访问")
        row_lbl.setStyleSheet(f"color: {text_main}; font-size: 12px; font-weight: 500;")
        row.addWidget(row_lbl)
        row.addStretch()

        self.toggle_btn = QPushButton()
        self.toggle_btn.setFixedSize(54, 24)
        self.toggle_btn.clicked.connect(self._on_toggle)
        row.addWidget(self.toggle_btn)
        c_layout.addLayout(row)

        self._update_state()
        layout.addWidget(card)

    def _update_state(self):
        is_full = (self.current_perm == "full_auto")
        if is_full:
            self.desc_lbl.setText("当前为【完全访问】模式：AI 智能体可在全盘任意路径操作文件与执行系统命令。")
            self.toggle_btn.setText("开启")
            self.toggle_btn.setStyleSheet(
                "QPushButton { background-color: #10b981; color: #ffffff; border: none; border-radius: 12px; font-size: 11px; font-weight: bold; }"
            )
        else:
            self.desc_lbl.setText("当前为默认权限，所有操作在安全沙箱内进行，超出范围会先请求允许。")
            self.toggle_btn.setText("关闭")
            self.toggle_btn.setStyleSheet(
                "QPushButton { background-color: #e2e8f0; color: #64748b; border: 1px solid #cbd5e1; border-radius: 12px; font-size: 11px; font-weight: bold; }"
            )

    def _on_toggle(self):
        self.current_perm = "standard" if self.current_perm == "full_auto" else "full_auto"
        self._update_state()
        self.permission_changed.emit(self.current_perm)


# ─────────────────────────── 模型切换弹窗 ───────────────────────────

class ModelSelectorPopupCard(QWidget):
    model_selected = pyqtSignal(dict)

    def __init__(self, models: List[dict], active_model_id: str, is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.models = models
        self.active_model_id = active_model_id
        self.is_dark = is_dark
        self.setFixedWidth(300)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        card = QFrame(self)
        card.setObjectName("ModelCard")
        bg_color = "rgba(15,23,42,0.97)" if self.is_dark else "rgba(255,255,255,0.98)"
        border_color = "#334155" if self.is_dark else "#e2e8f0"
        text_main = "#e2e8f0" if self.is_dark else "#0f172a"
        card.setStyleSheet(f"""
            QFrame#ModelCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 14px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 90))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(10, 10, 10, 10)
        c_layout.setSpacing(4)

        header = QLabel("🤖 切换模型")
        header.setStyleSheet(f"color: {text_main}; font-size: 12px; font-weight: bold; padding: 4px 6px;")
        c_layout.addWidget(header)

        for m in self.models:
            mid = m.get("id", "")
            name = m.get("name", "未命名模型")
            is_active = (mid == self.active_model_id)
            indicator = "✓ " if is_active else "   "
            btn = QPushButton(f"{indicator}{name}")
            hover_bg = '#334155' if self.is_dark else '#f1f5f9'
            active_bg = '#1e293b' if self.is_dark else '#eff6ff'
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {active_bg if is_active else 'transparent'};
                    color: {'#6366f1' if is_active else text_main};
                    border: none;
                    border-radius: 8px;
                    padding: 8px 12px;
                    text-align: left;
                    font-size: 12px;
                    font-family: 'Microsoft YaHei UI';
                    font-weight: {'bold' if is_active else 'normal'};
                }}
                QPushButton:hover {{ background-color: {hover_bg}; }}
            """)
            btn.clicked.connect(lambda checked, mod=m: self._select_model(mod))
            c_layout.addWidget(btn)
        layout.addWidget(card)

    def _select_model(self, model: dict):
        self.model_selected.emit(model)
        self.close()


# ─────────────────────────── 全局任务搜索浮窗 (复刻截图 4) ───────────────────────────

class GlobalTaskSearchPopup(QWidget):
    session_selected = pyqtSignal(int)

    def __init__(self, sessions: List[dict], current_ws: str = "Study笔记", is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.sessions = sessions
        self.current_ws = current_ws
        self.is_dark = is_dark
        self.setFixedSize(360, 420)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        card = QFrame(self)
        card.setObjectName("SearchCard")
        bg_color = "rgba(15,23,42,0.98)" if self.is_dark else "rgba(255,255,255,0.99)"
        border_color = "#334155" if self.is_dark else "#e2e8f0"
        card.setStyleSheet(f"""
            QFrame#SearchCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 16px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 6)
        card.setGraphicsEffect(shadow)

        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(14, 14, 14, 14)
        c_lay.setSpacing(10)

        # 搜索输入行
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 搜索任务")
        self.search_edit.setFixedHeight(36)
        inp_bg = "#1e293b" if self.is_dark else "#f8fafc"
        fg = "#e2e8f0" if self.is_dark else "#0f172a"
        self.search_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {inp_bg};
                color: {fg};
                border: 1px solid {border_color};
                border-radius: 10px;
                padding: 0 12px;
                font-size: 13px;
                font-family: 'Microsoft YaHei UI';
            }}
        """)
        self.search_edit.textChanged.connect(self._filter_sessions)
        top_row.addWidget(self.search_edit, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("background: transparent; color: #94a3b8; border: none; font-size: 13px;")
        close_btn.clicked.connect(self.close)
        top_row.addWidget(close_btn)
        c_lay.addLayout(top_row)

        sec_lbl = QLabel("最近任务")
        sec_lbl.setStyleSheet("color: #64748b; font-size: 11.5px; font-weight: bold; font-family: 'Microsoft YaHei UI';")
        c_lay.addWidget(sec_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        self.list_container = QWidget()
        self.list_lay = QVBoxLayout(self.list_container)
        self.list_lay.setContentsMargins(0, 0, 0, 0)
        self.list_lay.setSpacing(4)
        self.list_lay.addStretch()

        scroll.setWidget(self.list_container)
        c_lay.addWidget(scroll, 1)

        self._render_items(self.sessions)
        layout.addWidget(card)

    def _render_items(self, items: List[dict]):
        for i in reversed(range(self.list_lay.count() - 1)):
            w = self.list_lay.itemAt(i).widget()
            if w: w.setParent(None)

        fg = "#e2e8f0" if self.is_dark else "#1e293b"
        for s in items[:15]:
            sid = s.get("id")
            title = str(s.get("title", "未命名")).strip()
            btn = QPushButton()
            btn.setFixedHeight(38)
            btn.setCursor(Qt.PointingHandCursor)
            hover_bg = '#334155' if self.is_dark else '#f1f5f9'
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    border-radius: 8px;
                    padding: 0 10px;
                }}
                QPushButton:hover {{ background-color: {hover_bg}; }}
            """)

            b_lay = QHBoxLayout(btn)
            b_lay.setContentsMargins(4, 0, 4, 0)
            t_lbl = QLabel(title if len(title) <= 16 else title[:15] + "...")
            t_lbl.setStyleSheet(f"color: {fg}; font-size: 12.5px; font-weight: 500; font-family: 'Microsoft YaHei UI';")
            b_lay.addWidget(t_lbl, 1)

            ws_lbl = QLabel(f"📁 {self.current_ws}")
            ws_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-family: 'Microsoft YaHei UI';")
            b_lay.addWidget(ws_lbl)

            btn.clicked.connect(lambda ch, s_id=sid: self._on_select(s_id))
            self.list_lay.insertWidget(self.list_lay.count() - 1, btn)

    def _filter_sessions(self, text: str):
        kw = text.strip().lower()
        filtered = [s for s in self.sessions if kw in str(s.get("title", "")).lower()]
        self._render_items(filtered)

    def _on_select(self, sid: int):
        self.session_selected.emit(sid)
        self.close()


# ─────────────────────────── 任务状态与时间筛选浮窗 (复刻截图 5) ───────────────────────────

class TaskFilterPopup(QWidget):
    filter_applied = pyqtSignal(str, str)

    def __init__(self, current_status: str = "全部状态", current_time: str = "全部时间", is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.current_status = current_status
        self.current_time = current_time
        self.is_dark = is_dark
        self.setFixedWidth(240)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        card = QFrame(self)
        card.setObjectName("FilterCard")
        bg_color = "rgba(15,23,42,0.98)" if self.is_dark else "rgba(255,255,255,0.99)"
        border_color = "#334155" if self.is_dark else "#e2e8f0"
        card.setStyleSheet(f"""
            QFrame#FilterCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 14px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(10, 10, 10, 10)
        c_lay.setSpacing(3)

        fg = "#e2e8f0" if self.is_dark else "#0f172a"

        # 1. 筛选状态
        s_lbl = QLabel("筛选状态")
        s_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; padding-left: 6px;")
        c_lay.addWidget(s_lbl)

        statuses = ["全部状态", "进行中", "已完成", "失败", "待处理", "规划中"]
        for st in statuses:
            btn = self._build_filter_btn(st, is_active=(st == self.current_status), is_status=True)
            c_lay.addWidget(btn)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("background: rgba(0,0,0,0.06); min-height: 1px; max-height: 1px; margin: 4px 0;")
        c_lay.addWidget(sep1)

        # 2. 筛选时间
        t_lbl = QLabel("筛选时间")
        t_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; padding-left: 6px;")
        c_lay.addWidget(t_lbl)

        times = ["全部时间", "今天", "最近 7 天", "最近 30 天"]
        for tm in times:
            btn = self._build_filter_btn(tm, is_active=(tm == self.current_time), is_status=False)
            c_lay.addWidget(btn)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background: rgba(0,0,0,0.06); min-height: 1px; max-height: 1px; margin: 4px 0;")
        c_lay.addWidget(sep2)

        reset_btn = QPushButton("重置筛选条件")
        reset_btn.setFixedHeight(30)
        reset_btn.setStyleSheet("background: transparent; color: #94a3b8; border: none; font-size: 11.5px; text-align: left; padding-left: 8px;")
        reset_btn.clicked.connect(self._reset_filters)
        c_lay.addWidget(reset_btn)

        layout.addWidget(card)

    def _build_filter_btn(self, name: str, is_active: bool, is_status: bool) -> QPushButton:
        btn = QPushButton()
        btn.setFixedHeight(30)
        btn.setCursor(Qt.PointingHandCursor)
        hover_bg = '#334155' if self.is_dark else '#f1f5f9'
        active_bg = '#1e293b' if self.is_dark else '#f1f5f9'
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {active_bg if is_active else 'transparent'};
                border: none;
                border-radius: 6px;
                padding: 0 6px;
            }}
            QPushButton:hover {{ background-color: {hover_bg}; }}
        """)

        b_lay = QHBoxLayout(btn)
        b_lay.setContentsMargins(4, 0, 4, 0)
        lbl = QLabel(name)
        fg = "#e2e8f0" if self.is_dark else "#0f172a"
        lbl.setStyleSheet(f"color: {fg}; font-size: 12px; font-weight: {'bold' if is_active else 'normal'}; font-family: 'Microsoft YaHei UI';")
        b_lay.addWidget(lbl, 1)

        if is_active:
            check_icon = QLabel("✓")
            check_icon.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
            b_lay.addWidget(check_icon)

        if is_status:
            btn.clicked.connect(lambda ch, s=name: self._on_status_chosen(s))
        else:
            btn.clicked.connect(lambda ch, t=name: self._on_time_chosen(t))
        return btn

    def _on_status_chosen(self, s: str):
        self.current_status = s
        self.filter_applied.emit(self.current_status, self.current_time)
        self.close()

    def _on_time_chosen(self, t: str):
        self.current_time = t
        self.filter_applied.emit(self.current_status, self.current_time)
        self.close()

    def _reset_filters(self):
        self.current_status = "全部状态"
        self.current_time = "全部时间"
        self.filter_applied.emit("全部状态", "全部时间")
        self.close()


# ─────────────────────────── 自动化提示词：技能选择浮窗 (复刻截图 3) ───────────────────────────

class AutoSkillSelectPopup(QWidget):
    skill_selected = pyqtSignal(str, str)
    import_requested = pyqtSignal()

    def __init__(self, skills: List[dict], is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.skills = skills
        self.is_dark = is_dark
        self.setFixedSize(300, 360)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        card = QFrame(self)
        card.setObjectName("SkillPopupCard")
        bg_color = "rgba(15,23,42,0.98)" if self.is_dark else "rgba(255,255,255,0.99)"
        border_color = "#334155" if self.is_dark else "#e2e8f0"
        card.setStyleSheet(f"""
            QFrame#SkillPopupCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 14px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(10, 10, 10, 10)
        c_lay.setSpacing(8)

        # 搜索技能输入框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 搜索技能")
        self.search_edit.setFixedHeight(34)
        inp_bg = "#1e293b" if self.is_dark else "#f8fafc"
        fg = "#e2e8f0" if self.is_dark else "#0f172a"
        self.search_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {inp_bg};
                color: {fg};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 12.5px;
                font-family: 'Microsoft YaHei UI';
            }}
        """)
        self.search_edit.textChanged.connect(self._filter_skills)
        c_lay.addWidget(self.search_edit)

        # 技能列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        self.list_w = QWidget()
        self.list_lay = QVBoxLayout(self.list_w)
        self.list_lay.setContentsMargins(0, 0, 0, 0)
        self.list_lay.setSpacing(4)
        self.list_lay.addStretch()

        scroll.setWidget(self.list_w)
        c_lay.addWidget(scroll, 1)

        # 底部导入技能
        import_btn = QPushButton("📁 导入技能")
        import_btn.setFixedHeight(32)
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #475569; border: none;
                border-top: 1px solid #f1f5f9; text-align: left; padding-left: 8px;
                font-size: 12px; font-family: 'Microsoft YaHei UI';
            }
            QPushButton:hover { color: #6366f1; }
        """)
        import_btn.clicked.connect(self._on_import)
        c_lay.addWidget(import_btn)

        self._render_skills(self.skills)
        layout.addWidget(card)

    def _render_skills(self, items: List[dict]):
        for i in reversed(range(self.list_lay.count() - 1)):
            w = self.list_lay.itemAt(i).widget()
            if w: w.setParent(None)

        COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4"]
        for idx, s in enumerate(items[:20]):
            name = s.get("name", "技能")
            desc = s.get("description", s.get("desc", ""))
            char = s.get("char", name[:1])
            col = s.get("color", COLORS[idx % len(COLORS)])

            btn = QPushButton()
            btn.setFixedHeight(46)
            btn.setCursor(Qt.PointingHandCursor)
            hover_bg = '#334155' if self.is_dark else '#f8fafc'
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: none; border-radius: 8px; padding: 4px;
                }}
                QPushButton:hover {{ background: {hover_bg}; }}
            """)

            b_lay = QHBoxLayout(btn)
            b_lay.setContentsMargins(4, 2, 4, 2)
            b_lay.setSpacing(8)

            badge = QLabel(char)
            badge.setFixedSize(24, 24)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(f"background: {col}; color: #fff; border-radius: 5px; font-weight: bold; font-size: 11px;")
            b_lay.addWidget(badge)

            v = QVBoxLayout(); v.setSpacing(1)
            nl = QLabel(name)
            nl.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {'#e2e8f0' if self.is_dark else '#0f172a'};")
            dl = QLabel(desc[:26] + "..." if len(desc) > 26 else desc)
            dl.setStyleSheet("font-size: 10.5px; color: #94a3b8;")
            v.addWidget(nl); v.addWidget(dl)
            b_lay.addLayout(v, 1)

            btn.clicked.connect(lambda ch, n=name, p=s.get("prompt", name): self._on_select(n, p))
            self.list_lay.insertWidget(self.list_lay.count() - 1, btn)

    def _filter_skills(self, text: str):
        kw = text.strip().lower()
        filtered = [s for s in self.skills if kw in s.get("name", "").lower() or kw in s.get("description", "").lower()]
        self._render_skills(filtered)

    def _on_select(self, name: str, prompt: str):
        self.skill_selected.emit(name, prompt)
        self.close()

    def _on_import(self):
        self.import_requested.emit()
        self.close()


# ─────────────────────────── 自动化提示词：专家选择浮窗 (复刻截图 4) ───────────────────────────

class AutoExpertSelectPopup(QWidget):
    expert_selected = pyqtSignal(str, str)
    more_requested = pyqtSignal()

    def __init__(self, experts: List[dict] = None, is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.is_dark = is_dark
        self.experts = experts or [
            {"name": "前端开发工程师", "role": "像素匠", "char": "端", "color": "#3b82f6", "prompt": "作为前端开发工程师，请帮我审查并实现..."},
            {"name": "全栈架构师", "role": "系统设计", "char": "栈", "color": "#10b981", "prompt": "作为全栈架构师，请评估系统架构方案..."},
            {"name": "量化投研专家", "role": "策略研究", "char": "量", "color": "#ef4444", "prompt": "作为量化投研专家，请分析当前市场走势..."},
            {"name": "法律顾问", "role": "合规审查", "char": "法", "color": "#8b5cf6", "prompt": "作为资深企业法律顾问，请起草或审查合同..."},
            {"name": "新媒体主编", "role": "内容爆款", "char": "文", "color": "#f59e0b", "prompt": "作为新媒体爆款主编，请润色并优化推文标题与结构..."},
        ]
        self.setFixedSize(260, 260)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        card = QFrame(self)
        card.setObjectName("ExpertPopupCard")
        bg_color = "rgba(15,23,42,0.98)" if self.is_dark else "rgba(255,255,255,0.99)"
        border_color = "#334155" if self.is_dark else "#e2e8f0"
        card.setStyleSheet(f"""
            QFrame#ExpertPopupCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 14px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(10, 10, 10, 10)
        c_lay.setSpacing(6)

        sec_lbl = QLabel("最近召唤")
        sec_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; padding-left: 4px;")
        c_lay.addWidget(sec_lbl)

        for exp in self.experts[:3]:
            btn = QPushButton()
            btn.setFixedHeight(44)
            btn.setCursor(Qt.PointingHandCursor)
            hover_bg = '#334155' if self.is_dark else '#f8fafc'
            btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; border: none; border-radius: 8px; }}
                QPushButton:hover {{ background: {hover_bg}; }}
            """)

            b_lay = QHBoxLayout(btn)
            b_lay.setContentsMargins(4, 2, 4, 2)
            b_lay.setSpacing(8)

            avatar = QLabel(exp["char"])
            avatar.setFixedSize(28, 28)
            avatar.setAlignment(Qt.AlignCenter)
            avatar.setStyleSheet(f"background: {exp['color']}; color: #fff; border-radius: 14px; font-weight: bold; font-size: 12px;")
            b_lay.addWidget(avatar)

            v = QVBoxLayout(); v.setSpacing(1)
            nl = QLabel(exp["name"])
            nl.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {'#e2e8f0' if self.is_dark else '#0f172a'};")
            rl = QLabel(exp["role"])
            rl.setStyleSheet("font-size: 10.5px; color: #94a3b8;")
            v.addWidget(nl); v.addWidget(rl)
            b_lay.addLayout(v, 1)

            btn.clicked.connect(lambda ch, e=exp: self._on_select(e["name"], e["prompt"]))
            c_lay.addWidget(btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(0,0,0,0.06); min-height: 1px; max-height: 1px; margin: 4px 0;")
        c_lay.addWidget(sep)

        more_btn = QPushButton("🎓 召唤其它专家")
        more_btn.setFixedHeight(30)
        more_btn.setCursor(Qt.PointingHandCursor)
        more_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #6366f1; border: none;
                text-align: left; padding-left: 6px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { color: #4f46e5; }
        """)
        more_btn.clicked.connect(self._on_more)
        c_lay.addWidget(more_btn)

        layout.addWidget(card)

    def _on_select(self, name: str, prompt: str):
        self.expert_selected.emit(name, prompt)
        self.close()

    def _on_more(self):
        self.more_requested.emit()
        self.close()


# ─────────────────────────── 自动化权限选择浮窗 (复刻截图 5) ───────────────────────────

class AutoPermissionSelectPopup(QWidget):
    permission_chosen = pyqtSignal(str)

    def __init__(self, current_perm: str = "full", is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.current_perm = current_perm
        self.is_dark = is_dark
        self.setFixedSize(360, 230)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        card = QFrame(self)
        card.setObjectName("PermPopupCard")
        bg_color = "rgba(24,24,27,0.98)" if self.is_dark else "rgba(255,255,255,0.99)"
        border_color = "#3f3f46" if self.is_dark else "#e2e8f0"
        card.setStyleSheet(f"""
            QFrame#PermPopupCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 14px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(10, 10, 10, 10)
        c_lay.setSpacing(8)

        # 选项 1：完全访问权限 (推荐)
        is_full = (self.current_perm == "full")
        btn_full = self._build_perm_card(
            title="⚠️ 完全访问权限 (推荐)",
            desc="自动化任务会在本地客户端无人值守执行，并可能自动执行敏感操作或修改文件。执行期间请勿关闭电脑或退出客户端，且仅应在信任任务时使用该模式。",
            is_active=is_full,
            mode="full"
        )
        c_lay.addWidget(btn_full)

        # 选项 2：默认权限
        btn_std = self._build_perm_card(
            title="🛡️ 默认权限",
            desc="敏感操作需用户确认。如果你离开屏幕，任务会停在等待状态。仅推荐在本地调试 / 手动监管时使用。",
            is_active=not is_full,
            mode="standard"
        )
        c_lay.addWidget(btn_std)

        layout.addWidget(card)

    def _build_perm_card(self, title: str, desc: str, is_active: bool, mode: str) -> QPushButton:
        btn = QPushButton()
        btn.setFixedHeight(95)
        btn.setCursor(Qt.PointingHandCursor)
        if self.is_dark:
            bg = "#27272a" if is_active else "transparent"
            border = "#3f3f46" if is_active else "transparent"
            hover_bg = "#27272a"
        else:
            bg = "#f1f5f9" if is_active else "transparent"
            border = "#e2e8f0" if is_active else "transparent"
            hover_bg = "#f1f5f9"
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 10px;
                text-align: left;
                padding: 8px;
            }}
            QPushButton:hover {{ background-color: {hover_bg}; }}
        """)

        b_lay = QVBoxLayout(btn)
        b_lay.setContentsMargins(6, 4, 6, 4)
        b_lay.setSpacing(3)

        top_row = QHBoxLayout()
        if is_active:
            chk = QLabel("✓")
            chk.setStyleSheet(f"color: {'#ffffff' if self.is_dark else '#0f172a'}; font-weight: bold; font-size: 13px;")
            top_row.addWidget(chk)

        tl = QLabel(title)
        tl.setStyleSheet(f"font-size: 12.5px; font-weight: bold; color: {'#f4f4f5' if self.is_dark else '#0f172a'}; font-family: 'Microsoft YaHei UI';")
        top_row.addWidget(tl, 1)
        b_lay.addLayout(top_row)

        dl = QLabel(desc)
        dl.setWordWrap(True)
        dl.setStyleSheet(f"font-size: 11px; color: {'#a1a1aa' if self.is_dark else '#64748b'}; font-family: 'Microsoft YaHei UI'; line-height: 1.35;")
        b_lay.addWidget(dl)

        btn.clicked.connect(lambda ch, m=mode: self._on_choose(m))
        return btn

class SidebarWorkspaceHeaderWidget(QWidget):
    """1:1 复刻截图：工作空间卡片头部 [📁 空间名称 ∨]  右侧 [更多 ...][新建任务 ➕]"""
    clicked = pyqtSignal(str, str)             # ws_name, ws_path
    add_task_clicked = pyqtSignal(str, str)    # ws_name, ws_path
    open_folder_requested = pyqtSignal(str)   # ws_path
    remove_requested = pyqtSignal(str)        # ws_name

    def __init__(self, name: str, path: str, is_active: bool = False, is_collapsed: bool = False, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self.ws_name = name
        self.ws_path = path
        self.is_active = is_active
        self.is_collapsed = is_collapsed
        self.is_dark = is_dark
        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()

    def _init_ui(self):
        d = self.is_dark
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 2, 8, 2)
        lay.setSpacing(6)

        arrow = "∨" if not self.is_collapsed else "∧"
        self.title_lbl = QLabel(f"📁  {self.ws_name}  {arrow}")
        self.title_lbl.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold if self.is_active else QFont.Normal))
        self.title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        text_color = "#ffffff" if self.is_active else ("#e4e4e7" if d else "#0f172a")
        self.title_lbl.setStyleSheet(f"color: {text_color}; background: transparent;")
        lay.addWidget(self.title_lbl, 1)

        self.actions_widget = QWidget(self)
        a_lay = QHBoxLayout(self.actions_widget)
        a_lay.setContentsMargins(0, 0, 0, 0)
        a_lay.setSpacing(2)

        icon_btn_style = f"""
            QPushButton {{
                background: transparent;
                color: {'#a1a1aa' if d else '#64748b'};
                border: none;
                border-radius: 4px;
                padding: 1px 3px;
                font-size: 11.5px;
            }}
            QPushButton:hover {{
                background: {'#2e2e32' if d else '#e2e8f0'};
                color: {'#ffffff' if d else '#0f172a'};
            }}
        """

        self.btn_more = QPushButton("⋯")
        self.btn_more.setFixedSize(18, 20)
        self.btn_more.setToolTip("工作空间操作")
        self.btn_more.setStyleSheet(icon_btn_style)
        self.btn_more.clicked.connect(self._show_more_menu)
        a_lay.addWidget(self.btn_more)

        self.btn_add = QPushButton("💬+")
        self.btn_add.setFixedSize(22, 20)
        self.btn_add.setToolTip("在该空间新建任务")
        self.btn_add.setStyleSheet(icon_btn_style)
        self.btn_add.clicked.connect(lambda: self.add_task_clicked.emit(self.ws_name, self.ws_path))
        a_lay.addWidget(self.btn_add)

        lay.addWidget(self.actions_widget)
        if not self.is_active:
            self.actions_widget.hide()

    def enterEvent(self, event):
        self.actions_widget.show()
        if not self.is_active:
            bg = "#232326" if self.is_dark else "#f1f5f9"
            self.setStyleSheet(f"background-color: {bg}; border-radius: 8px;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.is_active:
            self.actions_widget.hide()
            self.setStyleSheet("background-color: transparent;")
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.ws_name, self.ws_path)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.ws_name, self.ws_path)
        super().mouseDoubleClickEvent(event)

    def _show_more_menu(self):
        menu = QMenu(self)
        d = self.is_dark
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {'#1e1e1e' if d else '#ffffff'};
                color: {'#f4f4f5' if d else '#0f172a'};
                border: 1px solid {'#2e2e2e' if d else '#e2e8f0'};
                border-radius: 10px;
                padding: 4px;
                font-family: 'Microsoft YaHei UI';
                font-size: 12px;
            }}
            QMenu::item {{
                padding: 6px 18px;
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: {'#27272a' if d else '#f1f5f9'};
            }}
        """)
        act_open = menu.addAction("📁 打开文件夹")
        menu.addSeparator()
        act_remove = menu.addAction("🗑 从列表中移除")
        act = menu.exec_(self.btn_more.mapToGlobal(QPoint(0, self.btn_more.height())))
        if act == act_open:
            self.open_folder_requested.emit(self.ws_path)
        elif act == act_remove:
            self.remove_requested.emit(self.ws_name)


# ─────────────────────────── 侧边栏任务项小部件 (Hover 悬浮显示操作图标) ───────────────────────────

class SidebarTaskItemWidget(QWidget):
    """复刻截图：鼠标 Hover 时右侧时间变为 [更多 ...][归档 🗄️][置顶 📌]"""
    clicked = pyqtSignal(int)
    rename_requested = pyqtSignal(int, str)
    delete_requested = pyqtSignal(int)
    archive_requested = pyqtSignal(int)
    pin_toggled = pyqtSignal(int, bool)
    save_to_ws_requested = pyqtSignal(int, str)
    export_requested = pyqtSignal(int, str)

    def __init__(self, session_id: int, title: str, time_str: str, is_pinned: bool = False, is_active: bool = False, is_dark: bool = False, is_sub_item: bool = False, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.title = title
        self.time_str = time_str
        self.is_pinned = is_pinned
        self.is_active = is_active
        self.is_dark = is_dark
        self.is_sub_item = is_sub_item
        self.setFixedHeight(34)
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()

    def _init_ui(self):
        lay = QHBoxLayout(self)
        left_margin = 22 if self.is_sub_item else 8
        lay.setContentsMargins(left_margin, 2, 8, 2)
        lay.setSpacing(6)

        # 标题 (如果是工作空间下属子任务，显示层次指示符 ↳)
        prefix = "↳ " if self.is_sub_item else ""
        self.title_lbl = QLabel(f"{prefix}{self.title}")
        self.title_lbl.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold if self.is_active else QFont.Normal))
        if self.is_active:
            text_color = "#ffffff" if self.is_dark else "#6366f1"
        else:
            text_color = ("#cbd5e1" if self.is_sub_item else "#e4e4e7") if self.is_dark else ("#475569" if self.is_sub_item else "#0f172a")
        self.title_lbl.setStyleSheet(f"color: {text_color}; background: transparent;")
        self.title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(self.title_lbl, 1)

        # 时间标签 (默认展示)
        self.time_lbl = QLabel(self.time_str)
        self.time_lbl.setStyleSheet(f"color: {'#71717a' if self.is_dark else '#94a3b8'}; font-size: 11px; background: transparent;")
        self.time_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(self.time_lbl)

        # 操作小图标容器 (Hover 时展示)
        self.actions_widget = QWidget(self)
        a_lay = QHBoxLayout(self.actions_widget)
        a_lay.setContentsMargins(0, 0, 0, 0)
        a_lay.setSpacing(2)

        icon_btn_style = f"""
            QPushButton {{
                background: transparent;
                color: {'#a1a1aa' if self.is_dark else '#64748b'};
                border: none;
                border-radius: 4px;
                padding: 1px 2px;
                font-size: 11px;
                font-family: 'Segoe UI Symbol', 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{
                background: {'#2e2e32' if self.is_dark else '#e2e8f0'};
                color: {'#ffffff' if self.is_dark else '#0f172a'};
            }}
        """

        # 1. 更多 ...
        self.btn_more = QPushButton("⋯")
        self.btn_more.setFixedSize(18, 20)
        self.btn_more.setToolTip("更多")
        self.btn_more.setStyleSheet(icon_btn_style)
        self.btn_more.clicked.connect(self._show_more_menu)
        a_lay.addWidget(self.btn_more)

        # 2. 归档 (极简单色盒子 ⌸)
        self.btn_archive = QPushButton("⌸")
        self.btn_archive.setFixedSize(18, 20)
        self.btn_archive.setToolTip("归档任务")
        self.btn_archive.setStyleSheet(icon_btn_style)
        self.btn_archive.clicked.connect(lambda: self.archive_requested.emit(self.session_id))
        a_lay.addWidget(self.btn_archive)

        # 3. 置顶 (极简单色星标/微标 ✦ / ✧)
        pin_icon = "✦" if self.is_pinned else "✧"
        pin_tip = "取消置顶" if self.is_pinned else "置顶任务"
        self.btn_pin = QPushButton(pin_icon)
        self.btn_pin.setFixedSize(18, 20)
        self.btn_pin.setToolTip(pin_tip)
        pin_style = icon_btn_style
        if self.is_pinned:
            pin_style = f"""
                QPushButton {{
                    background: transparent;
                    color: {'#818cf8' if self.is_dark else '#6366f1'};
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    font-family: 'Segoe UI Symbol', 'Microsoft YaHei UI';
                }}
                QPushButton:hover {{
                    background: {'#2e2e32' if self.is_dark else '#e2e8f0'};
                    color: #ffffff;
                }}
            """
        self.btn_pin.setStyleSheet(pin_style)
        self.btn_pin.clicked.connect(lambda: self.pin_toggled.emit(self.session_id, not self.is_pinned))
        a_lay.addWidget(self.btn_pin)

        self.actions_widget.hide()
        lay.addWidget(self.actions_widget)

    def enterEvent(self, event):
        self.time_lbl.hide()
        self.actions_widget.show()
        if not self.is_active:
            bg = "#232326" if self.is_dark else "#f1f5f9"
            self.setStyleSheet(f"background-color: {bg}; border-radius: 8px;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.actions_widget.hide()
        self.time_lbl.show()
        if not self.is_active:
            self.setStyleSheet("background-color: transparent;")
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.session_id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.session_id)
        super().mouseDoubleClickEvent(event)

    def _show_more_menu(self):
        menu = QMenu(self)
        d = self.is_dark
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {'#1e1e20' if d else '#ffffff'};
                color: {'#f4f4f5' if d else '#0f172a'};
                border: 1px solid {'#2e2e32' if d else '#e2e8f0'};
                border-radius: 12px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 6px 16px;
                border-radius: 6px;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
            QMenu::item:selected {{
                background-color: {'#2a2a2d' if d else '#f1f5f9'};
                color: {'#ffffff' if d else '#0f172a'};
            }}
        """)

        act_batch   = menu.addAction("📑 批量操作")
        act_folder  = menu.addAction("📁 打开会话所在文件夹")
        menu.addSeparator()
        act_rename  = menu.addAction("✎ 重命名")
        act_ws      = menu.addAction("💾 保存到工作空间...")
        act_export  = menu.addAction("📤 导出为 Markdown")
        act_share   = menu.addAction("🔗 分享会话")
        menu.addSeparator()
        act_delete  = menu.addAction("🗑️ 删除任务")

        action = menu.exec_(QCursor.pos())
        if action == act_rename:
            new_title, ok = QInputDialog.getText(self, "重命名任务", "请输入新名称：", text=self.title)
            if ok and new_title.strip():
                self.rename_requested.emit(self.session_id, new_title.strip())
        elif action == act_delete:
            reply = QMessageBox.question(
                self, "确认删除", f"确定要删除任务「{self.title}」吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.delete_requested.emit(self.session_id)
        elif action == act_ws:
            self.save_to_ws_requested.emit(self.session_id, self.title)
        elif action == act_export:
            self.export_requested.emit(self.session_id, self.title)
        elif action == act_batch:
            QMessageBox.information(self, "批量操作", "已进入多选管理模式")
        elif action == act_folder:
            import os
            os.system(f'explorer "{ROOT_DIR}"')
        elif action == act_share:
            QApplication.clipboard().setText(f"NovaDesk 任务分享：{self.title}")
            QMessageBox.information(self, "分享成功", "任务分享文案已复制到剪贴板！")


# ─────────────────────────── 精美纯净对话消息块 (MessageBlock) ───────────────────────────

class MessageBlock(QWidget):
    """WorkBuddy 风格纯净排版消息展示，带底部操作栏"""
    retry_requested = pyqtSignal(str)

    def __init__(self, sender: str, text: str, timestamp: str = "", model_name: str = "DeepSeek", is_dark: bool = False, parent=None):
        super().__init__(parent)
        self.sender = sender
        self.raw_text = text
        self.timestamp = timestamp or datetime.now().strftime("%H:%M")
        self.model_name = model_name
        self.is_dark = is_dark
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 12)
        main_layout.setSpacing(6)

        if self.sender == "user":
            # 用户消息：优雅深色右侧轻胶囊
            row = QHBoxLayout()
            row.addStretch()
            self.lbl_text = QLabel(self.raw_text)
            self.lbl_text.setWordWrap(True)
            self.lbl_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.lbl_text.setFont(QFont("Microsoft YaHei UI", 10))
            self._apply_user_text_style()
            row.addWidget(self.lbl_text)
            main_layout.addLayout(row)
        else:
            # AI 消息：通透纯净白底/深底排版 (无任何粗笨外框)
            self.lbl_text = QLabel(self.raw_text)
            self.lbl_text.setWordWrap(True)
            self.lbl_text.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
            self.lbl_text.setFont(QFont("Microsoft YaHei UI", 10))
            self._apply_ai_text_style()
            main_layout.addWidget(self.lbl_text)

            # 底部精致操作工具条
            self.toolbar = QHBoxLayout()
            self.toolbar.setContentsMargins(4, 2, 4, 0)
            self.toolbar.setSpacing(6)

            d = self.is_dark
            tool_btn_style = f"""
                QPushButton {{
                    background: transparent;
                    color: {'#a1a1aa' if d else '#64748b'};
                    border: none;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 11px;
                    font-family: 'Microsoft YaHei UI';
                }}
                QPushButton:hover {{
                    color: {'#ffffff' if d else '#0f172a'};
                    background: {'#27272a' if d else '#f1f5f9'};
                }}
            """

            # 1. 真实复制按钮（带成功反馈）
            self.copy_btn = QPushButton("📋 复制")
            self.copy_btn.setCursor(Qt.PointingHandCursor)
            self.copy_btn.setStyleSheet(tool_btn_style)
            self.copy_btn.clicked.connect(self._do_copy)
            self.toolbar.addWidget(self.copy_btn)

            # 2. 真实点赞状态切换
            self.is_liked = False
            self.like_btn = QPushButton("👍")
            self.like_btn.setCursor(Qt.PointingHandCursor)
            self.like_btn.setStyleSheet(tool_btn_style)
            self.like_btn.setToolTip("觉得很棒")
            self.like_btn.clicked.connect(self._toggle_like)
            self.toolbar.addWidget(self.like_btn)

            # 3. 真实点踩状态切换
            self.is_disliked = False
            self.dislike_btn = QPushButton("👎")
            self.dislike_btn.setCursor(Qt.PointingHandCursor)
            self.dislike_btn.setStyleSheet(tool_btn_style)
            self.dislike_btn.setToolTip("内容有待改进")
            self.dislike_btn.clicked.connect(self._toggle_dislike)
            self.toolbar.addWidget(self.dislike_btn)

            # 4. 真实重试按钮
            self.retry_btn = QPushButton("🔄 重试")
            self.retry_btn.setCursor(Qt.PointingHandCursor)
            self.retry_btn.setStyleSheet(tool_btn_style)
            self.retry_btn.setToolTip("重新生成此回答")
            self.retry_btn.clicked.connect(lambda: self.retry_requested.emit(self.raw_text))
            self.toolbar.addWidget(self.retry_btn)

            self.toolbar.addSpacing(10)
            
            # 5. 真实动态 Token 统计计算
            self.stats_lbl = QLabel(self._calc_real_token_stat())
            self.stats_lbl.setStyleSheet(f"color: {'#71717a' if d else '#94a3b8'}; font-size: 11px; font-family: 'Microsoft YaHei UI';")
            self.toolbar.addWidget(self.stats_lbl)

            self.toolbar.addStretch()
            main_layout.addLayout(self.toolbar)

    def _calc_real_token_stat(self) -> str:
        txt = self.raw_text.strip()
        if not txt or txt == "⏳ 正在思考...":
            return f"⚡ 0 Tokens · {self.model_name}"
        import re
        # 汉字统计 (1汉字 ≈ 1.5 token)
        chinese_cnt = len(re.findall(r'[\u4e00-\u9fa5]', txt))
        other_cnt = max(0, len(txt) - chinese_cnt)
        # 英文/标点/代码符号约 0.35 token/字符
        est_tokens = max(1, int(chinese_cnt * 1.45 + other_cnt * 0.35))
        return f"⚡ 共消耗 ≈ {est_tokens} Tokens · {self.model_name}"

    def _do_copy(self):
        txt = self.raw_text.strip()
        if txt and txt != "⏳ 正在思考...":
            QApplication.clipboard().setText(txt)
            self.copy_btn.setText("✓ 已复制")
            self.copy_btn.setStyleSheet("color: #10b981; font-weight: bold; border: none; font-size: 11px;")
            QTimer.singleShot(1500, self._reset_copy_btn)

    def _reset_copy_btn(self):
        d = self.is_dark
        self.copy_btn.setText("📋 复制")
        self.copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {'#a1a1aa' if d else '#64748b'};
                border: none; border-radius: 4px; padding: 2px 6px; font-size: 11px;
            }}
            QPushButton:hover {{
                color: {'#ffffff' if d else '#0f172a'};
                background: {'#27272a' if d else '#f1f5f9'};
            }}
        """)

    def _toggle_like(self):
        self.is_liked = not self.is_liked
        if self.is_liked:
            self.is_disliked = False
            self.dislike_btn.setText("👎")
            self.dislike_btn.setStyleSheet("color: #94a3b8; border: none;")
            self.like_btn.setText("👍 已赞")
            self.like_btn.setStyleSheet("color: #6366f1; font-weight: bold; border: none; font-size: 11px;")
        else:
            self.like_btn.setText("👍")
            self._reset_copy_btn()

    def _toggle_dislike(self):
        self.is_disliked = not self.is_disliked
        if self.is_disliked:
            self.is_liked = False
            self.like_btn.setText("👍")
            self.like_btn.setStyleSheet("color: #94a3b8; border: none;")
            self.dislike_btn.setText("👎 已反馈")
            self.dislike_btn.setStyleSheet("color: #ef4444; font-weight: bold; border: none; font-size: 11px;")
        else:
            self.dislike_btn.setText("👎")
            self._reset_copy_btn()

    def _apply_user_text_style(self):
        user_bg = "#27272a" if self.is_dark else "#18181b"
        self.lbl_text.setStyleSheet(f"""
            QLabel {{
                background-color: {user_bg};
                color: #ffffff;
                border-radius: 16px;
                border-bottom-right-radius: 4px;
                padding: 10px 18px;
                font-size: 13.5px;
                line-height: 1.5;
                font-family: 'Microsoft YaHei UI', -apple-system, sans-serif;
            }}
        """)

    def _apply_ai_text_style(self):
        text_color = "#f8fafc" if self.is_dark else "#0f172a"
        self.lbl_text.setStyleSheet(f"""
            QLabel {{
                background-color: transparent;
                color: {text_color};
                padding: 4px 6px;
                font-size: 14px;
                line-height: 1.7;
                font-family: 'Microsoft YaHei UI', -apple-system, sans-serif;
            }}
        """)

    def set_text(self, text: str):
        self.raw_text = text
        if hasattr(self, 'lbl_text'):
            self.lbl_text.setText(text)
        if hasattr(self, 'stats_lbl'):
            self.stats_lbl.setText(self._calc_real_token_stat())

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        if self.sender == "user":
            self._apply_user_text_style()
        else:
            self._apply_ai_text_style()
            d = self.is_dark
            tool_btn_style = f"""
                QPushButton {{
                    background: transparent;
                    color: {'#a1a1aa' if d else '#64748b'};
                    border: none;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 11px;
                    font-family: 'Microsoft YaHei UI';
                }}
                QPushButton:hover {{
                    color: {'#ffffff' if d else '#0f172a'};
                    background: {'#27272a' if d else '#f1f5f9'};
                }}
            """
            if hasattr(self, 'copy_btn'): self.copy_btn.setStyleSheet(tool_btn_style)
            if hasattr(self, 'like_btn') and not self.is_liked: self.like_btn.setStyleSheet(tool_btn_style)
            if hasattr(self, 'dislike_btn') and not self.is_disliked: self.dislike_btn.setStyleSheet(tool_btn_style)
            if hasattr(self, 'retry_btn'): self.retry_btn.setStyleSheet(tool_btn_style)
            if hasattr(self, 'stats_lbl'):
                self.stats_lbl.setStyleSheet(f"color: {'#71717a' if d else '#94a3b8'}; font-size: 11px; font-family: 'Microsoft YaHei UI';")


# ─────────────────────────── 添加自动化对话框 ───────────────────────────

class AddAutomationDialog(QDialog):
    def __init__(self, parent=None, is_dark: bool = False):
        super().__init__(parent)
        self.is_dark = is_dark
        self.setWindowTitle("添加自动化任务")
        self.setFixedSize(480, 340)
        self.setModal(True)
        self._result_data = None
        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("➕ 新建自动化任务")
        title.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例：每日 AI 新闻推送")
        self.name_edit.setFixedHeight(34)
        form.addRow("任务名称：", self.name_edit)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("输入 AI 执行的指令，例：查全网热搜新闻与最新科技动态")
        self.prompt_edit.setFixedHeight(70)
        form.addRow("执行指令：", self.prompt_edit)

        self.trigger_combo = QComboBox()
        self.trigger_combo.addItems(["固定时间触发", "延迟分钟数触发"])
        self.trigger_combo.currentIndexChanged.connect(self._on_trigger_type_change)
        form.addRow("触发方式：", self.trigger_combo)

        self.time_stack = QStackedWidget()
        time_w = QWidget()
        time_l = QHBoxLayout(time_w)
        time_l.setContentsMargins(0, 0, 0, 0)
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(8, 0))
        self.time_edit.setFixedHeight(34)
        time_l.addWidget(self.time_edit)
        self.repeat_check = QCheckBox("每日重复")
        self.repeat_check.setChecked(True)
        time_l.addWidget(self.repeat_check)
        time_l.addStretch()
        self.time_stack.addWidget(time_w)

        delay_w = QWidget()
        delay_l = QHBoxLayout(delay_w)
        delay_l.setContentsMargins(0, 0, 0, 0)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 1440)
        self.delay_spin.setValue(30)
        self.delay_spin.setFixedHeight(34)
        delay_l.addWidget(self.delay_spin)
        delay_l.addWidget(QLabel("分钟后触发"))
        delay_l.addStretch()
        self.time_stack.addWidget(delay_w)
        form.addRow("触发时间：", self.time_stack)
        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(80, 34)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        ok_btn = QPushButton("✓ 创建任务")
        ok_btn.setFixedSize(100, 34)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok)
        btn_box.addWidget(ok_btn)
        layout.addLayout(btn_box)

    def _on_trigger_type_change(self, idx):
        self.time_stack.setCurrentIndex(idx)

    def _on_ok(self):
        name = self.name_edit.text().strip()
        prompt = self.prompt_edit.toPlainText().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请填写任务名称")
            return
        if not prompt:
            QMessageBox.warning(self, "提示", "请填写执行指令")
            return
        trig_type = self.trigger_combo.currentIndex()
        if trig_type == 0:
            t = self.time_edit.time()
            time_str = f"{t.hour():02d}:{t.minute():02d}"
            repeat = self.repeat_check.isChecked()
            self._result_data = {
                "name": name,
                "prompt": prompt,
                "trigger_type": "fixed_time",
                "time_str": time_str,
                "repeat_daily": repeat,
            }
        else:
            minutes = self.delay_spin.value()
            self._result_data = {
                "name": name,
                "prompt": prompt,
                "trigger_type": "delay",
                "minutes": minutes,
                "repeat_daily": False,
            }
        self.accept()

    def _apply_style(self):
        bg = "#0f172a" if self.is_dark else "#ffffff"
        fg = "#e2e8f0" if self.is_dark else "#0f172a"
        border = "#334155" if self.is_dark else "#e2e8f0"
        inp_bg = "#1e293b" if self.is_dark else "#f8fafc"
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; color: {fg}; font-family: 'Microsoft YaHei UI'; }}
            QLabel {{ color: {fg}; font-size: 12px; }}
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QTimeEdit {{
                background-color: {inp_bg}; color: {fg}; border: 1px solid {border};
                border-radius: 6px; padding: 4px 8px; font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton {{
                background-color: {inp_bg}; color: {fg}; border: 1px solid {border};
                border-radius: 6px; font-size: 12px; padding: 0 10px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:default {{
                background-color: #6366f1; color: #ffffff; border: none;
                font-weight: bold;
            }}
            QPushButton:default:hover {{ background-color: #4f46e5; }}
            QCheckBox {{ color: {fg}; }}
        """)

    def get_result(self):
        return self._result_data


# ─────────────────────────── 添加/编辑模型对话框 ───────────────────────────

class AddModelDialog(QDialog):
    def __init__(self, parent=None, is_dark: bool = False, model_data: dict = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.model_data = model_data or {}
        is_edit = bool(model_data)
        self.setWindowTitle("编辑模型" if is_edit else "添加新模型")
        self.setFixedSize(500, 400)
        self.setModal(True)
        self._result_data = None
        self._init_ui(is_edit)
        self._apply_style()

    def _init_ui(self, is_edit: bool):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("✏️ 编辑模型配置" if is_edit else "➕ 添加新 AI 模型")
        title.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_edit = QLineEdit(self.model_data.get("name", ""))
        self.name_edit.setPlaceholderText("例：GPT-4o-mini")
        self.name_edit.setFixedHeight(34)
        form.addRow("显示名称：", self.name_edit)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["openai_compatible", "ollama", "custom"])
        prov = self.model_data.get("provider", "openai_compatible")
        idx = self.provider_combo.findText(prov)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        form.addRow("提供商：", self.provider_combo)

        self.model_name_edit = QLineEdit(self.model_data.get("model_name", ""))
        self.model_name_edit.setPlaceholderText("例：gpt-4o-mini")
        self.model_name_edit.setFixedHeight(34)
        form.addRow("模型 ID：", self.model_name_edit)

        self.api_url_edit = QLineEdit(self.model_data.get("api_base_url", ""))
        self.api_url_edit.setPlaceholderText("例：https://api.openai.com/v1")
        self.api_url_edit.setFixedHeight(34)
        form.addRow("API Base URL：", self.api_url_edit)

        self.api_key_edit = QLineEdit(self.model_data.get("api_key", ""))
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("输入 API Key（无需则留空）")
        self.api_key_edit.setFixedHeight(34)
        form.addRow("API Key：", self.api_key_edit)

        self.system_prompt_edit = QTextEdit()
        self.system_prompt_edit.setPlainText(
            self.model_data.get("system_prompt", "你是一个全能的桌面 AI 智能体助理。")
        )
        self.system_prompt_edit.setFixedHeight(60)
        form.addRow("系统提示词：", self.system_prompt_edit)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(80, 34)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        ok_btn = QPushButton("✓ 保存模型")
        ok_btn.setFixedSize(100, 34)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok)
        btn_box.addWidget(ok_btn)
        layout.addLayout(btn_box)

    def _on_ok(self):
        name = self.name_edit.text().strip()
        model_name = self.model_name_edit.text().strip()
        api_url = self.api_url_edit.text().strip()
        if not name or not model_name:
            QMessageBox.warning(self, "提示", "请填写显示名称和模型 ID")
            return
        import uuid
        self._result_data = {
            "id": self.model_data.get("id") or f"model_{uuid.uuid4().hex[:8]}",
            "name": name,
            "provider": self.provider_combo.currentText(),
            "model_name": model_name,
            "api_base_url": api_url,
            "api_key": self.api_key_edit.text().strip(),
            "system_prompt": self.system_prompt_edit.toPlainText().strip()
            or "你是一个全能的桌面 AI 智能体助理。",
        }
        self.accept()

    def _apply_style(self):
        bg = "#0f172a" if self.is_dark else "#ffffff"
        fg = "#e2e8f0" if self.is_dark else "#0f172a"
        border = "#334155" if self.is_dark else "#e2e8f0"
        inp_bg = "#1e293b" if self.is_dark else "#f8fafc"
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; color: {fg}; font-family: 'Microsoft YaHei UI'; }}
            QLabel {{ color: {fg}; font-size: 12px; }}
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {inp_bg}; color: {fg}; border: 1px solid {border};
                border-radius: 6px; padding: 4px 8px; font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton {{
                background-color: {inp_bg}; color: {fg}; border: 1px solid {border};
                border-radius: 6px; font-size: 12px; padding: 0 10px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:default {{
                background-color: #6366f1; color: #ffffff; border: none; font-weight: bold;
            }}
            QPushButton:default:hover {{ background-color: #4f46e5; }}
        """)

    def get_result(self):
        return self._result_data


# ─────────────────────────── 浮窗卡片组件 ───────────────────────────

class ModelSelectorPopupCard(QFrame):
    """模型选择浮窗卡片"""
    model_selected = pyqtSignal(dict)

    def __init__(self, models: List[dict], active_model_id: str = "", is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.models = models
        self.active_id = active_model_id
        self.is_dark = is_dark
        self.setFixedWidth(280)
        self._init_ui()

    def _init_ui(self):
        d = self.is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        border = "#2e2e2e" if d else "#e2e8f0"
        fg = "#f4f4f5" if d else "#0f172a"
        sub_fg = "#a1a1aa" if d else "#64748b"
        hover = "#27272a" if d else "#f1f5f9"

        self.setStyleSheet(f"""
            QFrame#Inner {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)
        outer_lay = QVBoxLayout(self)
        outer_lay.setContentsMargins(6, 6, 6, 6)

        inner = QFrame()
        inner.setObjectName("Inner")
        shadow = QGraphicsDropShadowEffect(inner)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80 if d else 30))
        shadow.setOffset(0, 4)
        inner.setGraphicsEffect(shadow)

        lay = QVBoxLayout(inner)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(4)

        head_lbl = QLabel("选择切换大模型")
        head_lbl.setStyleSheet(f"font-size: 11.5px; font-weight: bold; color: {sub_fg}; font-family: 'Microsoft YaHei UI'; padding: 2px 6px;")
        lay.addWidget(head_lbl)

        for m in self.models:
            mid = m.get("id", "")
            m_name = m.get("name", "未命名模型")
            m_prov = m.get("provider", "custom")
            is_active = (mid == self.active_id)

            btn = QPushButton()
            btn.setFixedHeight(38)
            btn.setCursor(Qt.PointingHandCursor)
            active_bg = "#27272a" if d else "#e0e7ff"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {active_bg if is_active else 'transparent'};
                    border: none;
                    border-radius: 8px;
                    padding: 0 8px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {hover};
                }}
            """)
            btn_l = QHBoxLayout(btn)
            btn_l.setContentsMargins(4, 0, 4, 0)
            btn_l.setSpacing(8)

            icon_lbl = QLabel("⚡" if m_prov == "ollama" else "🤖")
            icon_lbl.setFont(QFont("Segoe UI Emoji", 11))
            btn_l.addWidget(icon_lbl)

            name_lbl = QLabel(m_name)
            name_lbl.setStyleSheet(f"font-size: 12px; font-weight: {'bold' if is_active else 'normal'}; color: {'#818cf8' if is_active and d else ('#4f46e5' if is_active else fg)}; font-family: 'Microsoft YaHei UI';")
            btn_l.addWidget(name_lbl, 1)

            if is_active:
                chk = QLabel("✓")
                chk.setStyleSheet(f"color: {'#818cf8' if d else '#4f46e5'}; font-weight: bold; font-size: 12px;")
                btn_l.addWidget(chk)

            btn.clicked.connect(lambda ch, mod=m: self._on_select(mod))
            lay.addWidget(btn)

        outer_lay.addWidget(inner)

    def _on_select(self, model: dict):
        self.model_selected.emit(model)
        self.close()


class WorkspaceSelectorPopup(QFrame):
    """工作空间选择与管理浮窗"""
    workspace_selected = pyqtSignal(dict)
    create_new_requested = pyqtSignal()
    open_folder_requested = pyqtSignal()

    def __init__(self, workspaces: List[dict], current_name: str = "", is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.workspaces = workspaces
        self.current_name = current_name
        self.is_dark = is_dark
        self.setFixedWidth(280)
        self._init_ui()

    def _init_ui(self):
        d = self.is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        border = "#2e2e2e" if d else "#e2e8f0"
        fg = "#f4f4f5" if d else "#0f172a"
        sub_fg = "#a1a1aa" if d else "#64748b"
        hover = "#27272a" if d else "#f1f5f9"

        self.setStyleSheet(f"""
            QFrame#Inner {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)
        outer_lay = QVBoxLayout(self)
        outer_lay.setContentsMargins(6, 6, 6, 6)

        inner = QFrame()
        inner.setObjectName("Inner")
        shadow = QGraphicsDropShadowEffect(inner)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80 if d else 30))
        shadow.setOffset(0, 4)
        inner.setGraphicsEffect(shadow)

        lay = QVBoxLayout(inner)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(4)

        head_lbl = QLabel("切换工作空间")
        head_lbl.setStyleSheet(f"font-size: 11.5px; font-weight: bold; color: {sub_fg}; font-family: 'Microsoft YaHei UI'; padding: 2px 6px;")
        lay.addWidget(head_lbl)

        for ws in self.workspaces:
            name = ws.get("name", "未命名空间")
            path = ws.get("path", "")
            is_active = (name == self.current_name)

            btn = QPushButton()
            btn.setFixedHeight(38)
            btn.setCursor(Qt.PointingHandCursor)
            active_bg = "#27272a" if d else "#e0e7ff"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {active_bg if is_active else 'transparent'};
                    border: none;
                    border-radius: 8px;
                    padding: 0 8px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {hover};
                }}
            """)
            btn_l = QHBoxLayout(btn)
            btn_l.setContentsMargins(4, 0, 4, 0)
            btn_l.setSpacing(8)

            icon_lbl = QLabel("📁")
            icon_lbl.setFont(QFont("Segoe UI Emoji", 11))
            btn_l.addWidget(icon_lbl)

            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(f"font-size: 12px; font-weight: {'bold' if is_active else 'normal'}; color: {'#818cf8' if is_active and d else ('#4f46e5' if is_active else fg)}; font-family: 'Microsoft YaHei UI';")
            btn_l.addWidget(name_lbl, 1)

            if is_active:
                chk = QLabel("✓")
                chk.setStyleSheet(f"color: {'#818cf8' if d else '#4f46e5'}; font-weight: bold; font-size: 12px;")
                btn_l.addWidget(chk)

            btn.clicked.connect(lambda ch, w=ws: self._on_select(w))
            lay.addWidget(btn)

        lay.addSpacing(4)
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {border};")
        lay.addWidget(div)

        # 底部操作行
        bot_btn_l = QHBoxLayout()
        bot_btn_l.setSpacing(6)

        new_btn = QPushButton("＋ 新建空间")
        new_btn.setFixedHeight(30)
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{fg};border:none;border-radius:6px;font-size:11.5px;font-weight:bold;font-family:'Microsoft YaHei UI';}} QPushButton:hover{{background:{hover};}}")
        new_btn.clicked.connect(self._on_create_new)
        bot_btn_l.addWidget(new_btn)

        folder_btn = QPushButton("📂 本地目录")
        folder_btn.setFixedHeight(30)
        folder_btn.setCursor(Qt.PointingHandCursor)
        folder_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{sub_fg};border:none;border-radius:6px;font-size:11.5px;font-family:'Microsoft YaHei UI';}} QPushButton:hover{{background:{hover};color:{fg};}}")
        folder_btn.clicked.connect(self._on_open_folder)
        bot_btn_l.addWidget(folder_btn)

        lay.addLayout(bot_btn_l)
        outer_lay.addWidget(inner)

    def _on_select(self, ws: dict):
        self.workspace_selected.emit(ws)
        self.close()

    def _on_create_new(self):
        self.create_new_requested.emit()
        self.close()

    def _on_open_folder(self):
        self.open_folder_requested.emit()
        self.close()


class PermissionPopupCard(QFrame):
    """权限模式切换浮窗"""
    permission_changed = pyqtSignal(str)

    def __init__(self, current_perm: str = "standard", is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.current_perm = current_perm
        self.is_dark = is_dark
        self.setFixedWidth(260)
        self._init_ui()

    def _init_ui(self):
        d = self.is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        border = "#2e2e2e" if d else "#e2e8f0"
        fg = "#f4f4f5" if d else "#0f172a"
        sub_fg = "#a1a1aa" if d else "#64748b"
        hover = "#27272a" if d else "#f1f5f9"

        self.setStyleSheet(f"QFrame#Inner {{ background-color: {bg}; border: 1px solid {border}; border-radius: 12px; }}")
        outer_lay = QVBoxLayout(self)
        outer_lay.setContentsMargins(6, 6, 6, 6)

        inner = QFrame()
        inner.setObjectName("Inner")
        shadow = QGraphicsDropShadowEffect(inner)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80 if d else 30))
        shadow.setOffset(0, 4)
        inner.setGraphicsEffect(shadow)

        lay = QVBoxLayout(inner)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(4)

        head_lbl = QLabel("安全与执行权限")
        head_lbl.setStyleSheet(f"font-size: 11.5px; font-weight: bold; color: {sub_fg}; font-family: 'Microsoft YaHei UI'; padding: 2px 6px;")
        lay.addWidget(head_lbl)

        options = [
            ("standard", "🛡️ 默认权限", "敏感操作（写入/删除/终端）需确认"),
            ("full", "🚀 完全访问", "全自动免确认执行"),
        ]

        for p_val, p_title, p_desc in options:
            is_active = (self.current_perm == p_val)
            btn = QPushButton()
            btn.setFixedHeight(46)
            btn.setCursor(Qt.PointingHandCursor)
            active_bg = "#27272a" if d else "#e0e7ff"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {active_bg if is_active else 'transparent'};
                    border: none;
                    border-radius: 8px;
                    padding: 4px 8px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {hover};
                }}
            """)
            btn_l = QVBoxLayout(btn)
            btn_l.setContentsMargins(2, 2, 2, 2)
            btn_l.setSpacing(1)

            t_lbl = QLabel(p_title)
            t_lbl.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {'#818cf8' if is_active and d else ('#4f46e5' if is_active else fg)};")
            btn_l.addWidget(t_lbl)

            d_lbl = QLabel(p_desc)
            d_lbl.setStyleSheet(f"font-size: 10px; color: {sub_fg};")
            btn_l.addWidget(d_lbl)

            btn.clicked.connect(lambda ch, val=p_val: self._on_select(val))
            lay.addWidget(btn)

        outer_lay.addWidget(inner)

    def _on_select(self, perm: str):
        self.permission_changed.emit(perm)
        self.close()


class GlobalTaskSearchPopup(QFrame):
    """全局任务搜索浮窗"""
    session_selected = pyqtSignal(int)

    def __init__(self, sessions: List[dict], current_ws: str = "", is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.sessions = sessions
        self.is_dark = is_dark
        self.setFixedSize(340, 380)
        self._init_ui()

    def _init_ui(self):
        d = self.is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        border = "#2e2e2e" if d else "#e2e8f0"
        fg = "#f4f4f5" if d else "#0f172a"
        sub_fg = "#a1a1aa" if d else "#64748b"

        self.setStyleSheet(f"QFrame#Inner {{ background-color: {bg}; border: 1px solid {border}; border-radius: 12px; }}")
        outer_lay = QVBoxLayout(self)
        outer_lay.setContentsMargins(6, 6, 6, 6)

        inner = QFrame()
        inner.setObjectName("Inner")
        shadow = QGraphicsDropShadowEffect(inner)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80 if d else 30))
        shadow.setOffset(0, 4)
        inner.setGraphicsEffect(shadow)

        lay = QVBoxLayout(inner)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索任务名称或内容...")
        self.search_input.setFixedHeight(34)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {'#27272a' if d else '#f1f5f9'};
                color: {fg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
        """)
        self.search_input.textChanged.connect(self._on_search)
        lay.addWidget(self.search_input)

        self.list_w = QListWidget()
        self.list_w.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                color: {fg};
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-radius: 6px;
            }}
            QListWidget::item:hover {{
                background: {'#27272a' if d else '#f1f5f9'};
            }}
        """)
        self.list_w.itemClicked.connect(self._on_item_clicked)
        lay.addWidget(self.list_w, 1)

        self._populate_list(self.sessions)
        outer_lay.addWidget(inner)

    def _populate_list(self, sessions: List[dict]):
        self.list_w.clear()
        for s in sessions:
            title = s.get("title", "未命名会话")
            sid = s.get("id")
            item = QListWidgetItem(f"💬  {title}")
            item.setData(Qt.UserRole, sid)
            self.list_w.addItem(item)

    def _on_search(self, kw: str):
        kw = kw.strip().lower()
        if not kw:
            self._populate_list(self.sessions)
            return
        filtered = [s for s in self.sessions if kw in s.get("title", "").lower()]
        self._populate_list(filtered)

    def _on_item_clicked(self, item):
        sid = item.data(Qt.UserRole)
        if sid:
            self.session_selected.emit(sid)
            self.close()


class TaskFilterPopup(QFrame):
    """任务筛选浮窗"""
    filter_applied = pyqtSignal(str, str)

    def __init__(self, current_status: str = "全部状态", current_time: str = "全部时间", is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.current_status = current_status
        self.current_time = current_time
        self.is_dark = is_dark
        self.setFixedWidth(240)
        self._init_ui()

    def _init_ui(self):
        d = self.is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        border = "#2e2e2e" if d else "#e2e8f0"
        fg = "#f4f4f5" if d else "#0f172a"
        sub_fg = "#a1a1aa" if d else "#64748b"

        self.setStyleSheet(f"QFrame#Inner {{ background-color: {bg}; border: 1px solid {border}; border-radius: 12px; }}")
        outer_lay = QVBoxLayout(self)
        outer_lay.setContentsMargins(6, 6, 6, 6)

        inner = QFrame()
        inner.setObjectName("Inner")
        shadow = QGraphicsDropShadowEffect(inner)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80 if d else 30))
        shadow.setOffset(0, 4)
        inner.setGraphicsEffect(shadow)

        lay = QVBoxLayout(inner)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        head_lbl = QLabel("时间范围筛选")
        head_lbl.setStyleSheet(f"font-size: 11.5px; font-weight: bold; color: {sub_fg};")
        lay.addWidget(head_lbl)

        time_options = ["全部时间", "今天", "最近 7 天", "最近 30 天"]
        for opt in time_options:
            btn = QPushButton(f"{'● ' if self.current_time == opt else '○ '}{opt}")
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {'#818cf8' if self.current_time == opt and d else ('#4f46e5' if self.current_time == opt else fg)};
                    border: none;
                    border-radius: 6px;
                    text-align: left;
                    padding: 0 6px;
                    font-size: 12px;
                    font-weight: {'bold' if self.current_time == opt else 'normal'};
                }}
                QPushButton:hover {{
                    background: {'#27272a' if d else '#f1f5f9'};
                }}
            """)
            btn.clicked.connect(lambda ch, o=opt: self._on_time_selected(o))
            lay.addWidget(btn)

        outer_lay.addWidget(inner)

    def _on_time_selected(self, t_opt: str):
        self.filter_applied.emit(self.current_status, t_opt)
        self.close()


class AutoSkillSelectPopup(QFrame):
    """自动化页面技能选择浮窗"""
    skill_selected = pyqtSignal(str, str)
    import_requested = pyqtSignal()

    def __init__(self, skills: List[dict], is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.skills = skills
        self.is_dark = is_dark
        self.setFixedSize(300, 360)
        self._init_ui()

    def _init_ui(self):
        d = self.is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        border = "#2e2e2e" if d else "#e2e8f0"
        fg = "#f4f4f5" if d else "#0f172a"
        sub_fg = "#a1a1aa" if d else "#64748b"
        hover = "#27272a" if d else "#f1f5f9"

        self.setStyleSheet(f"QFrame#Inner {{ background-color: {bg}; border: 1px solid {border}; border-radius: 12px; }}")
        outer_lay = QVBoxLayout(self)
        outer_lay.setContentsMargins(6, 6, 6, 6)

        inner = QFrame()
        inner.setObjectName("Inner")
        shadow = QGraphicsDropShadowEffect(inner)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80 if d else 30))
        shadow.setOffset(0, 4)
        inner.setGraphicsEffect(shadow)

        lay = QVBoxLayout(inner)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        head_lbl = QLabel("🪄 选择引入技能")
        head_lbl.setStyleSheet(f"font-size: 11.5px; font-weight: bold; color: {sub_fg}; font-family: 'Microsoft YaHei UI';")
        lay.addWidget(head_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        content = QWidget()
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(4)

        for s in self.skills:
            name = s.get("name", "技能")
            prompt = s.get("prompt", f"使用{name}技能")
            btn = QPushButton(f"⚡ {name}")
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {fg}; border: none; border-radius: 6px;
                    text-align: left; padding: 0 8px; font-size: 12px; font-family: 'Microsoft YaHei UI';
                }}
                QPushButton:hover {{ background: {hover}; }}
            """)
            btn.clicked.connect(lambda ch, n=name, p=prompt: self._on_choose(n, p))
            c_lay.addWidget(btn)

        c_lay.addStretch()
        scroll.setWidget(content)
        lay.addWidget(scroll, 1)

        outer_lay.addWidget(inner)

    def _on_choose(self, name: str, prompt: str):
        self.skill_selected.emit(name, prompt)
        self.close()


class AutoExpertSelectPopup(QFrame):
    """自动化页面专家选择浮窗"""
    expert_selected = pyqtSignal(str, str)
    more_requested = pyqtSignal()

    def __init__(self, is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.is_dark = is_dark
        self.setFixedSize(300, 360)
        self._init_ui()

    def _init_ui(self):
        d = self.is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        border = "#2e2e2e" if d else "#e2e8f0"
        fg = "#f4f4f5" if d else "#0f172a"
        sub_fg = "#a1a1aa" if d else "#64748b"
        hover = "#27272a" if d else "#f1f5f9"

        self.setStyleSheet(f"QFrame#Inner {{ background-color: {bg}; border: 1px solid {border}; border-radius: 12px; }}")
        outer_lay = QVBoxLayout(self)
        outer_lay.setContentsMargins(6, 6, 6, 6)

        inner = QFrame()
        inner.setObjectName("Inner")
        shadow = QGraphicsDropShadowEffect(inner)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80 if d else 30))
        shadow.setOffset(0, 4)
        inner.setGraphicsEffect(shadow)

        lay = QVBoxLayout(inner)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        head_lbl = QLabel("🎓 召唤行业专家")
        head_lbl.setStyleSheet(f"font-size: 11.5px; font-weight: bold; color: {sub_fg}; font-family: 'Microsoft YaHei UI';")
        lay.addWidget(head_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        content = QWidget()
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(4)

        try:
            from core.ai_engine import EXPERTS_MAP
            experts = EXPERTS_MAP.values()
        except Exception:
            experts = []

        for exp in experts:
            name = exp.get("name", "专家")
            role = exp.get("role", "")
            btn = QPushButton(f"👤 {name}  ·  {role}")
            btn.setFixedHeight(34)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {fg}; border: none; border-radius: 6px;
                    text-align: left; padding: 0 8px; font-size: 11.5px; font-family: 'Microsoft YaHei UI';
                }}
                QPushButton:hover {{ background: {hover}; }}
            """)
            btn.clicked.connect(lambda ch, n=name, p=exp.get("system_prompt",""): self._on_choose(n, p))
            c_lay.addWidget(btn)

        c_lay.addStretch()
        scroll.setWidget(content)
        lay.addWidget(scroll, 1)

        outer_lay.addWidget(inner)

    def _on_choose(self, name: str, prompt: str):
        self.expert_selected.emit(name, prompt)
        self.close()


class AutoPermissionSelectPopup(QFrame):
    """自动化页面权限选择浮窗"""
    permission_chosen = pyqtSignal(str)

    def __init__(self, current_perm: str = "standard", is_dark: bool = False, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.current_perm = current_perm
        self.is_dark = is_dark
        self.setFixedWidth(260)
        self._init_ui()

    def _init_ui(self):
        d = self.is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        border = "#2e2e2e" if d else "#e2e8f0"
        fg = "#f4f4f5" if d else "#0f172a"
        sub_fg = "#a1a1aa" if d else "#64748b"
        hover = "#27272a" if d else "#f1f5f9"

        self.setStyleSheet(f"QFrame#Inner {{ background-color: {bg}; border: 1px solid {border}; border-radius: 12px; }}")
        outer_lay = QVBoxLayout(self)
        outer_lay.setContentsMargins(6, 6, 6, 6)

        inner = QFrame()
        inner.setObjectName("Inner")
        shadow = QGraphicsDropShadowEffect(inner)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80 if d else 30))
        shadow.setOffset(0, 4)
        inner.setGraphicsEffect(shadow)

        lay = QVBoxLayout(inner)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(4)

        head_lbl = QLabel("任务执行权限")
        head_lbl.setStyleSheet(f"font-size: 11.5px; font-weight: bold; color: {sub_fg}; font-family: 'Microsoft YaHei UI'; padding: 2px 6px;")
        lay.addWidget(head_lbl)

        options = [
            ("standard", "🛡️ 默认权限", "敏感文件与终端执行需确认"),
            ("full", "⚠️ 完全访问权限", "自动化后台免确认全自动执行"),
        ]

        for p_val, p_title, p_desc in options:
            is_active = (self.current_perm == p_val)
            btn = QPushButton()
            btn.setFixedHeight(46)
            btn.setCursor(Qt.PointingHandCursor)
            active_bg = "#27272a" if d else "#e0e7ff"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {active_bg if is_active else 'transparent'};
                    border: none; border-radius: 8px; padding: 4px 8px; text-align: left;
                }}
                QPushButton:hover {{ background: {hover}; }}
            """)
            btn_l = QVBoxLayout(btn)
            btn_l.setContentsMargins(2, 2, 2, 2)
            btn_l.setSpacing(1)

            t_lbl = QLabel(p_title)
            t_lbl.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {'#818cf8' if is_active and d else ('#4f46e5' if is_active else fg)};")
            btn_l.addWidget(t_lbl)

            d_lbl = QLabel(p_desc)
            d_lbl.setStyleSheet(f"font-size: 10px; color: {sub_fg};")
            btn_l.addWidget(d_lbl)

            btn.clicked.connect(lambda ch, val=p_val: self._on_choose(val))
            lay.addWidget(btn)

        outer_lay.addWidget(inner)

    def _on_choose(self, perm: str):
        self.permission_chosen.emit(perm)
        self.close()


# ═══════════════════════════════════════════════════════════════
#  ChatWindow  —  主窗口
# ═══════════════════════════════════════════════════════════════

class ChatWindow(QWidget):
    """NovaDesk v4.0 主工作台 (WorkBuddy 复刻)"""
    message_chunk_signal = pyqtSignal(int, str)
    message_done_signal  = pyqtSignal(int, str)
    message_error_signal = pyqtSignal(int, str)
    test_done_signal     = pyqtSignal(bool, str)

    def __init__(self, config: dict, ai_engine,
                 voice_input=None, voice_output=None,
                 pet_window=None, save_config_fn=None):
        super().__init__()
        self.config          = config
        self.ai_engine       = ai_engine
        self.pet_window      = pet_window
        self.save_config_fn  = save_config_fn
        self.memory          = getattr(ai_engine, "memory", None)

        self._is_dark        = (config.get("ui_theme", "light") == "dark")
        self._is_generating  = False
        self._is_maximized   = False
        self._normal_geometry = None
        self._current_ai_block = None
        self._current_session_id = None
        self._stream_id      = 0
        self._message_blocks: List[MessageBlock] = []
        self._session_collapsed = False
        self._ws_collapsed   = False
        self._installed_skills = set(config.get("plugins", {}).get("enabled", []))

        # 工作空间列表初始化
        self.workspaces = config.get("workspaces", [
            {"name": "Study笔记", "path": str(ROOT_DIR / "Study笔记")},
            {"name": "Agent开发", "path": str(ROOT_DIR / "Agent开发")},
            {"name": "langchain_demo", "path": str(ROOT_DIR / "langchain_demo")},
            {"name": "tjxt", "path": str(ROOT_DIR / "tjxt")},
            {"name": "Spring_AI_MCP", "path": str(ROOT_DIR / "Spring_AI_MCP")},
        ])
        self.current_workspace_name = config.get("current_workspace_name", "Study笔记")
        self.current_workspace_path = config.get("workspace_dir", str(ROOT_DIR))
        self.current_permission     = config.get("permission_mode", "standard")

        self.setWindowTitle("NovaDesk v3.0")
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self._init_window()
        self._build_ui()
        self._connect_signals()
        self._init_or_load_latest_session()

    def _init_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Window |
            Qt.WindowMinimizeButtonHint | Qt.WindowSystemMenuHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1120, 780)
        self.setMinimumSize(900, 640)

    def show_animated(self, target_pos: Optional[QPoint] = None):
        """带有高级平滑淡入透明度与缓动过渡效果的窗口展示"""
        if target_pos:
            self.move(target_pos)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.activateWindow()

        if hasattr(self, '_fade_anim') and self._fade_anim:
            self._fade_anim.stop()
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(220)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.start()

    def showEvent(self, event):
        super().showEvent(event)
        if self.windowOpacity() < 0.95:
            if hasattr(self, '_fade_anim') and self._fade_anim:
                self._fade_anim.stop()
            self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
            self._fade_anim.setDuration(200)
            self._fade_anim.setStartValue(self.windowOpacity())
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._fade_anim.start()

    def _connect_signals(self):
        self.message_chunk_signal.connect(self._on_chunk)
        self.message_done_signal.connect(self._on_done)
        self.message_error_signal.connect(self._on_error)
        self.test_done_signal.connect(self._on_test_result)
        try:
            from core.pet_scheduler import PetScheduler
            sched = PetScheduler.get_instance()
            sched.reminder_triggered.connect(self._on_scheduler_reminder_triggered)
        except Exception:
            pass

    def _on_scheduler_reminder_triggered(self, rid: int, title: str, content: str, motion: str):
        self._log_auto_run(title, content, "自动触发执行", "success")
        self._refresh_task_list()
        self._show_status(f"⏰ 自动化任务已执行：{title}")

    def _build_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(8, 8, 8, 8)
        self.root_layout.setSpacing(0)

        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("MainFrame")
        self.main_frame_shadow = QGraphicsDropShadowEffect(self.main_frame)
        self.main_frame_shadow.setBlurRadius(28)
        self.main_frame_shadow.setColor(QColor(0, 0, 0, 80))
        self.main_frame_shadow.setOffset(0, 6)
        self.main_frame.setGraphicsEffect(self.main_frame_shadow)

        fl = QVBoxLayout(self.main_frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)

        self.topbar = self._create_topbar()
        fl.addWidget(self.topbar)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)

        self.sidebar = self._create_sidebar()
        self.splitter.addWidget(self.sidebar)

        self.main_stack = QStackedWidget()
        self.page_chat     = self._create_chat_page()
        self.page_hub      = self._create_hub_page()
        self.page_auto     = self._create_automation_page()
        self.page_settings = self._create_settings_page()

        for p in [self.page_chat, self.page_hub, self.page_auto, self.page_settings]:
            self.main_stack.addWidget(p)

        self.splitter.addWidget(self.main_stack)
        self.splitter.setSizes([230, 890])
        fl.addWidget(self.splitter, 1)

        self.root_layout.addWidget(self.main_frame)
        self._apply_theme()

    # ══════════════════════════════════════════════════════════
    #  顶部标题栏 (移除 ready 徽章，极简纯净 1:1 对齐)
    # ══════════════════════════════════════════════════════════
    def _create_topbar(self) -> QWidget:
        bar = DraggableTopBar(self)
        bar.setFixedHeight(46)
        bar.setObjectName("TopBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 10, 0)
        lay.setSpacing(8)

        dot_r = QLabel("●"); dot_r.setStyleSheet("color:#ef4444;font-size:10px;")
        dot_y = QLabel("●"); dot_y.setStyleSheet("color:#f59e0b;font-size:10px;")
        dot_g = QLabel("●"); dot_g.setStyleSheet("color:#10b981;font-size:10px;")
        for d in [dot_r, dot_y, dot_g]:
            lay.addWidget(d)

        lay.addSpacing(6)
        self.expand_sb_btn = QPushButton("◫ 展开侧边栏")
        self.expand_sb_btn.setFixedHeight(28)
        self.expand_sb_btn.setCursor(Qt.PointingHandCursor)
        self.expand_sb_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0;
                border-radius: 6px; padding: 0 10px; font-size: 11.5px; font-family: 'Microsoft YaHei UI';
            }
            QPushButton:hover { background: #e2e8f0; color: #0f172a; }
        """)
        self.expand_sb_btn.clicked.connect(self._toggle_sidebar_collapse)
        self.expand_sb_btn.hide()
        lay.addWidget(self.expand_sb_btn)

        self.title_lbl = QLabel("NovaDesk v3.0")
        self.title_lbl.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        lay.addWidget(self.title_lbl)
        lay.addStretch()

        self.theme_btn = QPushButton("🌙" if self._is_dark else "☀️")
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.clicked.connect(self._toggle_theme)
        lay.addWidget(self.theme_btn)

        self.min_btn = QPushButton("─")
        self.min_btn.setFixedSize(32, 32)
        self.min_btn.clicked.connect(self.showMinimized)
        lay.addWidget(self.min_btn)

        self.max_btn = QPushButton("▢")
        self.max_btn.setFixedSize(32, 32)
        self.max_btn.clicked.connect(self._toggle_maximize)
        lay.addWidget(self.max_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.clicked.connect(self.hide)
        lay.addWidget(self.close_btn)
        return bar

    # ══════════════════════════════════════════════════════════
    #  侧边栏 (任务 + 空间联动)
    # ══════════════════════════════════════════════════════════
    def _create_sidebar(self) -> QWidget:
        sb = QWidget()
        sb.setObjectName("SideBar")
        sb.setFixedWidth(230)
        lay = QVBoxLayout(sb)
        lay.setContentsMargins(8, 12, 8, 10)
        lay.setSpacing(6)

        # 头部工作台信息与快捷操作 (复刻截图：WorkBuddy + [收起侧边栏][搜索][筛选])
        top_info = QHBoxLayout()
        top_info.setSpacing(6)
        
        info_v = QVBoxLayout()
        info_v.setSpacing(0)
        self.work_lbl = QLabel("NovaDesk")
        self.work_lbl.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        self.ver_lbl = QLabel("v3.0")
        self.ver_lbl.setStyleSheet("color: #94a3b8; font-size: 10px;")
        info_v.addWidget(self.work_lbl)
        info_v.addWidget(self.ver_lbl)
        top_info.addLayout(info_v)
        top_info.addStretch()

        top_icon_btn_style = """
            QPushButton {
                background: transparent;
                color: #64748b;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                padding: 3px;
            }
            QPushButton:hover {
                background: #e2e8f0;
                color: #0f172a;
            }
        """

        # 1. 收起侧边栏
        self.btn_collapse_sb = QPushButton("◫")
        self.btn_collapse_sb.setFixedSize(26, 26)
        self.btn_collapse_sb.setToolTip("收起侧边栏")
        self.btn_collapse_sb.setStyleSheet(top_icon_btn_style)
        self.btn_collapse_sb.clicked.connect(self._toggle_sidebar_collapse)
        top_info.addWidget(self.btn_collapse_sb)

        # 2. 搜索
        self.btn_search_tasks = QPushButton("🔍")
        self.btn_search_tasks.setFixedSize(26, 26)
        self.btn_search_tasks.setToolTip("搜索")
        self.btn_search_tasks.setStyleSheet(top_icon_btn_style)
        self.btn_search_tasks.clicked.connect(self._open_global_task_search_popup)
        top_info.addWidget(self.btn_search_tasks)

        # 3. 筛选
        self.btn_filter_tasks = QPushButton("🌪️")
        self.btn_filter_tasks.setFixedSize(26, 26)
        self.btn_filter_tasks.setToolTip("筛选")
        self.btn_filter_tasks.setStyleSheet(top_icon_btn_style)
        self.btn_filter_tasks.clicked.connect(self._open_task_filter_popup)
        top_info.addWidget(self.btn_filter_tasks)

        lay.addLayout(top_info)
        lay.addSpacing(4)

        # + 新建任务
        self.new_task_btn = QPushButton("＋  新建任务")
        self.new_task_btn.setFixedHeight(36)
        self.new_task_btn.clicked.connect(self._create_new_session_action)
        lay.addWidget(self.new_task_btn)
        lay.addSpacing(4)

        # 主导航
        self.nav_btns = []
        nav_items = [
            ("💬", "助理", 0),
            ("🧩", "专家·技能·连接器", 1),
            ("⚡", "自动化", 2),
            ("⚙️", "设置与模型", 3),
        ]
        for icon, label, idx in nav_items:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setFixedHeight(34)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self._switch_nav(i))
            lay.addWidget(btn)
            self.nav_btns.append(btn)
        self.nav_btns[0].setChecked(True)

        lay.addSpacing(6)

        # ── 1. 任务独立滑动区 (独立的滑动视口，自适应并带独立滚动条)
        self.task_box = QWidget()
        self.task_box.setStyleSheet("background: transparent;")
        tb_lay = QVBoxLayout(self.task_box)
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.setSpacing(4)

        task_header = QHBoxLayout()
        self.task_head = QLabel("任务 (0) ∨")
        self.task_head.setStyleSheet("color:#94a3b8;font-size:11px;font-weight:bold;")
        self.task_head.setCursor(Qt.PointingHandCursor)
        self.task_head.mousePressEvent = lambda e: self._toggle_session_list()
        task_header.addWidget(self.task_head)
        task_header.addStretch()
        tb_lay.addLayout(task_header)

        self.session_list = QListWidget()
        self.session_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.session_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.session_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.session_list.customContextMenuRequested.connect(self._show_session_context_menu)
        self.session_list.itemClicked.connect(self._on_session_item_clicked)
        self.session_list.itemDoubleClicked.connect(self._on_session_item_clicked)
        tb_lay.addWidget(self.session_list, 1)

        lay.addWidget(self.task_box, 3)

        lay.addSpacing(6)

        # ── 2. 空间独立滑动区 (独立的滑动视口，无论任务多少，空间永远在此独立展示与滑动)
        self.ws_box = QWidget()
        self.ws_box.setStyleSheet("background: transparent;")
        wb_lay = QVBoxLayout(self.ws_box)
        wb_lay.setContentsMargins(0, 0, 0, 0)
        wb_lay.setSpacing(4)

        ws_header = QHBoxLayout()
        self.ws_head = QLabel(f"空间 ({len(self.workspaces)}) ∨")
        self.ws_head.setStyleSheet("color:#94a3b8;font-size:11px;font-weight:bold;")
        self.ws_head.setCursor(Qt.PointingHandCursor)
        self.ws_head.mousePressEvent = lambda e: self._toggle_workspace_area()
        ws_header.addWidget(self.ws_head)
        ws_header.addStretch()
        wb_lay.addLayout(ws_header)

        self.ws_list = QListWidget()
        self.ws_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ws_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.ws_list.itemClicked.connect(self._on_ws_list_item_clicked)
        self.ws_list.itemDoubleClicked.connect(self._on_ws_list_item_clicked)
        wb_lay.addWidget(self.ws_list, 1)
        self._refresh_sidebar_workspaces()

        lay.addWidget(self.ws_box, 2)

        # 底部状态与全局声音喇叭 (开启/关闭所有互动声音、番茄钟/定时任务到点声音与语音)
        bot = QHBoxLayout()
        bot.setContentsMargins(4, 4, 4, 0)
        self.status_lbl = QLabel("🟢 智能体 就绪")
        self.status_lbl.setStyleSheet("color:#64748b;font-size:11px;")
        bot.addWidget(self.status_lbl)
        bot.addStretch()

        is_sound_on = self.config.get("sound_enabled", True)
        self.sound_btn = QPushButton("🔊" if is_sound_on else "🔇")
        self.sound_btn.setFixedSize(28, 28)
        self.sound_btn.setCursor(Qt.PointingHandCursor)
        self.sound_btn.setToolTip("开启/关闭全局声音 (玩偶互动、番茄钟提醒与语音回复)")
        self.sound_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                padding: 2px;
            }
            QPushButton:hover {
                background: #27272a;
            }
        """)
        self.sound_btn.clicked.connect(self._toggle_sound_muted)
        bot.addWidget(self.sound_btn)
        lay.addLayout(bot)
        return sb

    def _toggle_sound_muted(self):
        curr = self.config.get("sound_enabled", True)
        new_val = not curr
        self.config["sound_enabled"] = new_val
        self.config.setdefault("behavior", {})["sound_enabled"] = new_val
        if self.pet_window and hasattr(self.pet_window, "set_sound_enabled"):
            self.pet_window.set_sound_enabled(new_val)
        if self.save_config_fn:
            self.save_config_fn(self.config)
        self.sound_btn.setText("🔊" if new_val else "🔇")
        self._show_status("🔊 全局声音已开启" if new_val else "🔇 全局已静音 (所有声音关闭)")

    # ══════════════════════════════════════════════════════════
    #  聊天页 (居中悬浮模式 vs 对话模式)
    # ══════════════════════════════════════════════════════════
    def _create_chat_page(self) -> QWidget:
        page = QWidget()
        self.chat_page_stack = QStackedWidget(page)
        p_lay = QVBoxLayout(page)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.addWidget(self.chat_page_stack)

        # ── 模式 1：居中悬浮卡片态 (Hero Empty Mode)
        self.view_hero = QWidget()
        vh_lay = QVBoxLayout(self.view_hero)
        vh_lay.setContentsMargins(20, 20, 20, 20)

        vh_lay.addStretch(1)

        # 居中核心容器 (限制最大宽度，非常高级)
        center_box = QWidget()
        center_box.setFixedWidth(780)
        cb_lay = QVBoxLayout(center_box)
        cb_lay.setContentsMargins(0, 0, 0, 0)
        cb_lay.setSpacing(14)
        cb_lay.setAlignment(Qt.AlignCenter)

        # 顶部大标题与活动徽章
        header_row = QHBoxLayout()
        header_row.setAlignment(Qt.AlignCenter)
        self.h_title = QLabel("NovaDesk, 我帮你")
        self.h_title.setFont(QFont("Microsoft YaHei UI", 24, QFont.Bold))
        header_row.addWidget(self.h_title)
        cb_lay.addLayout(header_row)

        # 场景芯片分类行 1
        self.chip_buttons = []
        r1 = QHBoxLayout(); r1.setAlignment(Qt.AlignCenter); r1.setSpacing(10)
        items1 = [("☕", "日常办公"), ("💻", "代码开发"), ("🎨", "设计创意"), ("📊", "数据分析")]
        for icon, name in items1:
            b = QPushButton(f"{icon}  {name}")
            b.setFixedHeight(32)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda c, n=name: self._on_scenario_chip(n))
            r1.addWidget(b)
            self.chip_buttons.append(b)
        cb_lay.addLayout(r1)

        # 细分工具胶囊行 2
        r2 = QHBoxLayout(); r2.setAlignment(Qt.AlignCenter); r2.setSpacing(8)
        items2 = [
            ("📄", "文档处理"), ("💳", "金融服务"),
            ("🪪", "个人工作台"), ("🖥️", "幻灯片"), ("🔍", "深度研究"), ("🎬", "视频生成")
        ]
        for icon, name in items2:
            b = QPushButton(f"{icon} {name}")
            b.setFixedHeight(28)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda c, n=name: self._on_scenario_chip(n))
            r2.addWidget(b)
            self.chip_buttons.append(b)
        cb_lay.addLayout(r2)

        cb_lay.addSpacing(6)

        # 悬浮居中大输入卡片
        self.hero_dock_card = QFrame()
        self.hero_dock_card.setObjectName("HeroDockCard")
        h_dock_l = QVBoxLayout(self.hero_dock_card)
        h_dock_l.setContentsMargins(18, 14, 18, 12)
        h_dock_l.setSpacing(8)

        self.hero_input_edit = ChatTextEdit()
        self.hero_input_edit.setFixedHeight(68)
        self.hero_input_edit.setPlaceholderText(
            "今天帮你做些什么？ @ 引用对话文件，/ 调用技能与指令"
        )
        self.hero_input_edit.return_pressed.connect(self._send_hero_message)
        h_dock_l.addWidget(self.hero_input_edit)

        h_dock_bot = QHBoxLayout(); h_dock_bot.setSpacing(8)
        self.hero_plus_btn = QPushButton("＋")
        self.hero_plus_btn.setFixedSize(28, 28)
        self.hero_plus_btn.setToolTip("添加/引用本地项目文件与文档")
        self.hero_plus_btn.clicked.connect(self._on_plus_attach_file_clicked)
        h_dock_bot.addWidget(self.hero_plus_btn)
        h_dock_bot.addStretch()

        self.hero_model_pill = QPushButton(f"🤖 {self._get_active_model_display()} ∨")
        self.hero_model_pill.setFixedHeight(30)
        self.hero_model_pill.clicked.connect(self._open_model_selector_popup)
        h_dock_bot.addWidget(self.hero_model_pill)

        self.hero_send_btn = QPushButton("▲")
        self.hero_send_btn.setFixedSize(30, 30)
        self.hero_send_btn.setCursor(Qt.PointingHandCursor)
        self.hero_send_btn.clicked.connect(self._send_hero_message)
        h_dock_bot.addWidget(self.hero_send_btn)

        h_dock_l.addLayout(h_dock_bot)
        cb_lay.addWidget(self.hero_dock_card)

        # 卡片下方药丸行 (选择工作空间 / 默认权限)
        h_sub = QHBoxLayout(); h_sub.setContentsMargins(6, 0, 6, 0); h_sub.setSpacing(12)
        ws_init_txt = f"📁 {self.current_workspace_name} ∨" if self.current_workspace_name else "📁 选择工作空间 ∨"
        self.hero_ws_pill = QPushButton(ws_init_txt)
        self.hero_ws_pill.clicked.connect(self._open_workspace_selector_popup)
        h_sub.addWidget(self.hero_ws_pill)

        self.hero_perm_pill = QPushButton(
            "🛡️ 默认权限 ∨" if self.current_permission == "standard" else "🚀 完全访问 ∨"
        )
        self.hero_perm_pill.clicked.connect(self._open_permission_popup)
        h_sub.addWidget(self.hero_perm_pill)
        h_sub.addStretch()
        cb_lay.addLayout(h_sub)

        vh_lay.addWidget(center_box, 0, Qt.AlignCenter)
        vh_lay.addStretch(2)

        self.chat_page_stack.addWidget(self.view_hero)

        # ── 模式 2：对话模式态 (Active Chat Mode)
        self.view_active = QWidget()
        va_lay = QVBoxLayout(self.view_active)
        va_lay.setContentsMargins(20, 10, 20, 14)
        va_lay.setSpacing(8)

        # 对话顶部标题栏
        self.chat_header = QHBoxLayout()
        self.chat_title_lbl = QLabel("新任务会话")
        self.chat_title_lbl.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        self.chat_header.addWidget(self.chat_title_lbl)
        self.chat_header.addStretch()

        self.search_chat_btn = QPushButton("🔍")
        self.search_chat_btn.setFixedSize(28, 28)
        self.search_chat_btn.clicked.connect(self._open_global_task_search_popup)
        self.chat_header.addWidget(self.search_chat_btn)

        self.export_chat_btn = QPushButton("↗ 导出")
        self.export_chat_btn.setFixedHeight(28)
        self.export_chat_btn.clicked.connect(lambda: self._export_session_markdown(self._current_session_id, self.chat_title_lbl.text()))
        self.chat_header.addWidget(self.export_chat_btn)

        va_lay.addLayout(self.chat_header)

        # 滚动消息区
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{width:5px;background:transparent;border-radius:3px;}"
            "QScrollBar::handle:vertical{background:#cbd5e1;border-radius:3px;min-height:20px;}"
        )

        self.chat_content = QWidget()
        self.chat_layout  = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch()

        self.scroll_area.setWidget(self.chat_content)
        va_lay.addWidget(self.scroll_area, 1)

        # 固底输入卡片
        self.dock_card = QFrame()
        self.dock_card.setObjectName("DockCard")
        dock_l = QVBoxLayout(self.dock_card)
        dock_l.setContentsMargins(16, 12, 16, 10)
        dock_l.setSpacing(8)

        self.input_edit = ChatTextEdit()
        self.input_edit.setFixedHeight(54)
        self.input_edit.setPlaceholderText(
            "今天帮你做些什么？ @ 引用对话文件，/ 调用技能与指令"
        )
        self.input_edit.return_pressed.connect(self._send_active_message)
        dock_l.addWidget(self.input_edit)

        dock_bot = QHBoxLayout(); dock_bot.setSpacing(8)
        self.plus_btn = QPushButton("＋")
        self.plus_btn.setFixedSize(26, 26)
        self.plus_btn.setToolTip("添加/引用本地项目文件与文档")
        self.plus_btn.clicked.connect(self._on_plus_attach_file_clicked)
        dock_bot.addWidget(self.plus_btn)
        dock_bot.addStretch()

        self.model_pill = QPushButton(f"🤖 {self._get_active_model_display()} ∨")
        self.model_pill.setFixedHeight(30)
        self.model_pill.clicked.connect(self._open_model_selector_popup)
        dock_bot.addWidget(self.model_pill)

        self.send_btn = QPushButton("▲")
        self.send_btn.setFixedSize(30, 30)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self._send_active_message)
        dock_bot.addWidget(self.send_btn)
        dock_l.addLayout(dock_bot)
        va_lay.addWidget(self.dock_card)

        # 底部工作区与权限胶囊
        sub = QHBoxLayout(); sub.setContentsMargins(4, 0, 4, 0); sub.setSpacing(10)
        self.ws_pill = QPushButton(ws_init_txt)
        self.ws_pill.clicked.connect(self._open_workspace_selector_popup)
        sub.addWidget(self.ws_pill)

        self.perm_pill = QPushButton(
            "🛡️ 默认权限 ∨" if self.current_permission == "standard" else "🚀 完全访问 ∨"
        )
        self.perm_pill.clicked.connect(self._open_permission_popup)
        sub.addWidget(self.perm_pill)
        sub.addStretch()

        footer_hint = QLabel("内容由 AI 生成，请核实重要信息")
        footer_hint.setStyleSheet("color: #94a3b8; font-size: 11px;")
        sub.addWidget(footer_hint)
        va_lay.addLayout(sub)

        self.chat_page_stack.addWidget(self.view_active)
        self.chat_page_stack.setCurrentIndex(0)
        return page

    # ══════════════════════════════════════════════════════════
    #  技能 Hub 与「我安装的」专属页
    # ══════════════════════════════════════════════════════════
    def _create_hub_page(self) -> QWidget:
        page = QWidget()
        self.hub_main_stack = QStackedWidget(page)
        p_lay = QVBoxLayout(page)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.addWidget(self.hub_main_stack)

        # ── 视图 1：技能与专家大厅
        hub_hall = QWidget()
        ml = QVBoxLayout(hub_hall)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        # 顶部导航条
        top_bar = QWidget()
        top_bar.setObjectName("HubTopBar")
        top_bar.setFixedHeight(52)
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(20, 8, 20, 8)
        tb_lay.setSpacing(8)

        self.hub_tab_expert = QPushButton("🧩 专家")
        self.hub_tab_skill  = QPushButton("🪄 技能")
        self.hub_tab_conn   = QPushButton("🔗 连接器")
        for t in [self.hub_tab_expert, self.hub_tab_skill, self.hub_tab_conn]:
            t.setFixedHeight(32)
            t.setCheckable(True)
        self.hub_tab_expert.clicked.connect(lambda: self._switch_hub_tab(0))
        self.hub_tab_skill.clicked.connect(lambda:  self._switch_hub_tab(1))
        self.hub_tab_conn.clicked.connect(lambda:   self._switch_hub_tab(2))
        tb_lay.addWidget(self.hub_tab_expert)
        tb_lay.addWidget(self.hub_tab_skill)
        tb_lay.addWidget(self.hub_tab_conn)
        tb_lay.addStretch()

        self.hub_search = QLineEdit()
        self.hub_search.setPlaceholderText("🔍 搜索...")
        self.hub_search.setFixedSize(200, 32)
        self.hub_search.textChanged.connect(self._on_hub_search)
        tb_lay.addWidget(self.hub_search)

        self.custom_conn_btn = QPushButton("⚙ 自定义连接器")
        self.custom_conn_btn.setFixedHeight(32)
        self.custom_conn_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0;
                border-radius: 8px; padding: 0 12px; font-size: 11.5px;
                font-family: 'Microsoft YaHei UI';
            }
            QPushButton:hover { background: #e2e8f0; }
        """)
        self.custom_conn_btn.clicked.connect(self._on_custom_connector_dialog)
        tb_lay.addWidget(self.custom_conn_btn)

        self.my_installed_btn = QPushButton(f"📦 我安装的 ({len(self._installed_skills)})")
        self.my_installed_btn.setFixedHeight(32)
        self.my_installed_btn.clicked.connect(self._open_my_installed_page)
        tb_lay.addWidget(self.my_installed_btn)

        ml.addWidget(top_bar)

        self.hub_stack = QStackedWidget()
        self.hub_stack.addWidget(self._create_experts_tab())
        self.hub_stack.addWidget(self._create_skills_tab())
        self.hub_stack.addWidget(self._create_connectors_tab())
        ml.addWidget(self.hub_stack, 1)

        self.hub_main_stack.addWidget(hub_hall)

        # ── 视图 2：「我安装的」管理专区 (复刻截图 3)
        self.view_installed = self._create_my_installed_view()
        self.hub_main_stack.addWidget(self.view_installed)

        self._switch_hub_tab(1)
        return page

    def _create_my_installed_view(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(14)

        # 顶部返回行
        back_btn = QPushButton("‹ 全部技能")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748b;
                border: none;
                font-size: 13px;
                font-family: 'Microsoft YaHei UI';
            }
            QPushButton:hover { color: #6366f1; }
        """)
        back_btn.clicked.connect(lambda: self.hub_main_stack.setCurrentIndex(0))
        lay.addWidget(back_btn, 0, Qt.AlignLeft)

        # 标题与搜索行
        header_row = QHBoxLayout()
        self.installed_title_lbl = QLabel(f"我安装的  ({len(self._installed_skills)})")
        self.installed_title_lbl.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        header_row.addWidget(self.installed_title_lbl)
        header_row.addStretch()

        batch_btn = QPushButton("批量管理 ⚙")
        batch_btn.setFixedHeight(32)
        batch_btn.setStyleSheet("""
            QPushButton {
                background: #f1f5f9;
                color: #475569;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }
            QPushButton:hover { background: #e2e8f0; }
        """)
        header_row.addWidget(batch_btn)

        self.installed_search = QLineEdit()
        self.installed_search.setPlaceholderText("🔍 搜索已安装的技能")
        self.installed_search.setFixedSize(220, 32)
        self.installed_search.textChanged.connect(self._filter_my_installed_cards)
        header_row.addWidget(self.installed_search)
        lay.addLayout(header_row)

        # 卡片滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        self.installed_cards_container = QWidget()
        self.installed_cards_grid = QGridLayout(self.installed_cards_container)
        self.installed_cards_grid.setSpacing(14)
        self.installed_cards_grid.setAlignment(Qt.AlignTop)

        scroll.setWidget(self.installed_cards_container)
        lay.addWidget(scroll, 1)
        return w

    def _open_my_installed_page(self):
        self._refresh_my_installed_cards()
        self.hub_main_stack.setCurrentIndex(1)

    def _refresh_my_installed_cards(self, filter_kw: str = ""):
        for i in reversed(range(self.installed_cards_grid.count())):
            w = self.installed_cards_grid.itemAt(i).widget()
            if w:
                w.setParent(None)

        all_skills = self._get_skills_data()
        installed_list = [s for s in all_skills if s["id"] in self._installed_skills]
        self.installed_title_lbl.setText(f"我安装的  ({len(installed_list)})")
        self.my_installed_btn.setText(f"📦 我安装的 ({len(installed_list)})")

        kw = filter_kw.strip().lower()
        col = 0; row = 0
        for s in installed_list:
            name = s.get("name", "")
            desc = s.get("description", "")
            if kw and kw not in name.lower() and kw not in desc.lower():
                continue

            card = self._build_installed_manage_card(s)
            self.installed_cards_grid.addWidget(card, row, col)
            col += 1
            if col >= 2:
                col = 0; row += 1

    def _build_installed_manage_card(self, s: dict) -> QFrame:
        card = QFrame()
        card.setFixedHeight(120)
        bg = "#1e293b" if self._is_dark else "#ffffff"
        border = "#334155" if self._is_dark else "#e2e8f0"
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
            QFrame:hover {{
                border-color: #6366f1;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        # 头部：图标 + 标题 + 徽章 + Switch
        top = QHBoxLayout()
        top.setSpacing(10)

        icon_lbl = QLabel(s.get("name", "技")[:1])
        icon_lbl.setFixedSize(32, 32)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        icon_lbl.setStyleSheet(f"background: {s.get('color', '#6366f1')}; color: #ffffff; border-radius: 8px;")
        top.addWidget(icon_lbl)

        title_lbl = QLabel(s.get("name", "未命名"))
        title_lbl.setStyleSheet("font-size: 13.5px; font-weight: bold; color: #0f172a; font-family: 'Microsoft YaHei UI';")
        top.addWidget(title_lbl)

        badge = QLabel("套件")
        badge.setStyleSheet("""
            QLabel {
                background: #f3e8ff;
                color: #9333ea;
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10.5px;
                font-family: 'Microsoft YaHei UI';
            }
        """)
        top.addWidget(badge)
        top.addStretch()

        switch = ToggleSwitch(checked=True)
        switch.toggled.connect(lambda ch, s_=s: self._on_installed_switch_toggled(s_, ch))
        top.addWidget(switch)
        lay.addLayout(top)

        desc_lbl = QLabel(s.get("description", ""))
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 11.5px; color: #64748b; font-family: 'Microsoft YaHei UI'; line-height: 1.4;")
        lay.addWidget(desc_lbl)

        return card

    def _on_installed_switch_toggled(self, s: dict, checked: bool):
        sid = s.get("id", "")
        if checked:
            self._installed_skills.add(sid)
            self._show_status(f"已启用技能：{s.get('name')}")
        else:
            self._installed_skills.discard(sid)
            self._show_status(f"已停用技能：{s.get('name')}")

        self.config.setdefault("plugins", {})["enabled"] = list(self._installed_skills)
        if self.save_config_fn:
            self.save_config_fn(self.config)
        self._rebuild_skills_grid()

    def _filter_my_installed_cards(self, text: str):
        self._refresh_my_installed_cards(filter_kw=text)

    # ── 专家 Tab ──────────────────────────────────────────────
    def _create_experts_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(12)

        head = QLabel("精选场景专家")
        head.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        head.setStyleSheet(f"color: {'#f4f4f5' if self._is_dark else '#0f172a'}; font-family: 'Microsoft YaHei UI';")
        lay.addWidget(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;} QScrollArea > QWidget > QWidget{background:transparent;}")
        scroll.viewport().setStyleSheet("background: transparent; border: none;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.experts_grid = QGridLayout(content)
        self.experts_grid.setSpacing(12)
        self._rebuild_expert_cards()

        scroll.setWidget(content)
        lay.addWidget(scroll, 1)
        return w

    def _rebuild_expert_cards(self, filter_kw: str = ""):
        for i in reversed(range(self.experts_grid.count())):
            w = self.experts_grid.itemAt(i).widget()
            if w:
                w.setParent(None)

        try:
            from core.ai_engine import EXPERTS_MAP
            experts_map = EXPERTS_MAP
        except Exception:
            experts_map = {}

        # 按照场景分组
        SCENARIO_GROUPS = [
            {
                "title": "内容创作",
                "bg_gradient": "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #eef2ff,stop:1 #ffffff)",
                "icon": "✍️",
                "items": [
                    {"id": "content_creator_team", "name": "内容创作专家团", "char": "团", "color": "#ec4899", "desc": "全平台爆款内容创意与分发", "prompt": "请帮我制定一份全平台内容创作与引流策略", "system_prompt": "你是一个顶尖跨平台内容创作与矩阵运营专家。"},
                    {"id": "content_creator", "name": "内容创作专家", "char": "文", "color": "#8b5cf6", "desc": "擅长创作引人入胜的深度内容", "prompt": "请为我们的产品撰写一篇具有病毒式传播力的全网推广软文", "system_prompt": experts_map.get("content_creator", {}).get("system_prompt", "")},
                    {"id": "xhs_publisher", "name": "小红书运营专家", "char": "红", "color": "#ef4444", "desc": "小红书爆款图文与种草方案", "prompt": "请在当前工作目录下帮我编写一套高点赞小红书爆款图文笔记", "system_prompt": experts_map.get("xhs_publisher", {}).get("system_prompt", "")},
                ]
            },
            {
                "title": "投资分析",
                "bg_gradient": "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #f0fdf4,stop:1 #ffffff)",
                "icon": "📈",
                "items": [
                    {"id": "trade_team", "name": "交易分析团队", "char": "析", "color": "#06b6d4", "desc": "多维度盘面与量化交易信号拆解", "prompt": "请帮我分析当前科技板块的宏观走势与量价结构", "system_prompt": "你是一个资深量化交易与盘面技术分析团队。"},
                    {"id": "stock_researcher", "name": "股票研究专家", "char": "研", "color": "#10b981", "desc": "财报分析、DCF估值与首次覆盖报告", "prompt": "请基于最新财报数据做一次基本面与 DCF 估值分析", "system_prompt": experts_map.get("stock_researcher", {}).get("system_prompt", "")},
                    {"id": "tx_stock", "name": "腾讯自选股股票投研专家团", "char": "投", "color": "#ef4444", "desc": "智能选股与行业研报深度对比", "prompt": "请为我梳理当前A股和港股热门标的的研报核心逻辑", "system_prompt": "你是一个专业的股票投研智囊团。"},
                ]
            },
            {
                "title": "法律咨询",
                "bg_gradient": "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #faf5ff,stop:1 #ffffff)",
                "icon": "⚖️",
                "items": [
                    {"id": "legal_search", "name": "法律检索专家", "char": "检", "color": "#475569", "desc": "民商事法条检索与裁判文书类案分析", "prompt": "请帮我检索关于竞业限制协议效力的最新裁判要旨", "system_prompt": "你是一名资深法律文献与类案检索专家。"},
                    {"id": "legal_expert", "name": "资深合同法务专家", "char": "法", "color": "#0284c7", "desc": "合同起草、合规审查与知识产权保护", "prompt": "请帮我起草一份软件开发技术服务合同，重点规避交付争议风险", "system_prompt": experts_map.get("legal_expert", {}).get("system_prompt", "")},
                    {"id": "tax_compliance", "name": "财税合规专家团", "char": "税", "color": "#059669", "desc": "企业合规架构设计与税优方案", "prompt": "请帮我分析小微企业技术服务收入的税务合规与抵扣策略", "system_prompt": "你是一个资深注册会计师与财税合规智囊团。"},
                ]
            },
            {
                "title": "小微企业",
                "bg_gradient": "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #fffbeb,stop:1 #ffffff)",
                "icon": "💼",
                "items": [
                    {"id": "sales_coach", "name": "销售教练", "char": "销", "color": "#d97706", "desc": "大客户打法、销售话术与漏斗跟进", "prompt": "请帮我为新产品设计一套针对企业客户的电话开拓销售话术", "system_prompt": "你是一名资深 B2B 销售总监与谈判教练。"},
                    {"id": "wechat_op", "name": "微信公众号运营专家", "char": "微", "color": "#10b981", "desc": "微信生态闭环、私域裂变与长文排版", "prompt": "请帮我策划一篇微信公众号爆款干货长文与私域引流钩子", "system_prompt": "你是一名微信公众号百万阅读操盘手。"},
                    {"id": "startup_partner", "name": "创业伙伴", "char": "创", "color": "#6366f1", "desc": "0-1 商业闭环验证与极简成本控制", "prompt": "我想开启一个一人 AI 工具公司的创业项目，请帮我梳理第一阶段的核心商业闭环", "system_prompt": experts_map.get("startup_partner", {}).get("system_prompt", "")},
                ]
            },
            {
                "title": "电商运营",
                "bg_gradient": "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #fff1f2,stop:1 #ffffff)",
                "icon": "🛒",
                "items": [
                    {"id": "cn_ecommerce", "name": "中国电商运营专家", "char": "淘", "color": "#ef4444", "desc": "淘系/抖音/京东店铺运营与直通车打法", "prompt": "请帮我分析夏季服饰新品在抖音电商的冷启动起量策略", "system_prompt": "你是一名资深国内主流电商平台操盘总监。"},
                    {"id": "cross_border", "name": "跨境电商专家", "char": "跨", "color": "#0284c7", "desc": "亚马逊/TikTok Shop 选品与独立站运营", "prompt": "请帮我制定一份 TikTok Shop 美区小店的爆款选品分析报告", "system_prompt": "你是一名拥有多年出海经验的跨境电商专家。"},
                    {"id": "monetization", "name": "内容变现商业化专家团", "char": "商", "color": "#b45309", "desc": "知识付费、高客单转化与私域变现闭环", "prompt": "请帮我设计一套基于 AI 技能训练营的高客单转化商业闭环", "system_prompt": "你是一名资深商业化变现与知识付费操盘顾问。"},
                ]
            },
            {
                "title": "开学季与学术",
                "bg_gradient": "qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #f0fdfa,stop:1 #ffffff)",
                "icon": "🎓",
                "items": [
                    {"id": "campus_job_coach", "name": "校园求职教练", "char": "求", "color": "#6366f1", "desc": "应届生简历 STAR 优化与名企面试真题训练", "prompt": "我想从零制作一份应届生简历，请根据我的经历帮我生成可投递版本", "system_prompt": experts_map.get("campus_job_coach", {}).get("system_prompt", "")},
                    {"id": "thesis_advisor", "name": "论文写作导师", "char": "论", "color": "#8b5cf6", "desc": "开题报告、论文选题、文献综述框架整理", "prompt": "请帮我为人工智能方向拟定3个具有前沿创新性的毕业论文选题", "system_prompt": experts_map.get("thesis_advisor", {}).get("system_prompt", "")},
                    {"id": "campus_event_planner", "name": "校园活动策划顾问", "char": "策", "color": "#f59e0b", "desc": "迎新晚会、学术讲座与社团全案策划", "prompt": "请帮我们社团策划一份为期两天的秋季迎新纳新游园会活动全案", "system_prompt": experts_map.get("campus_event_planner", {}).get("system_prompt", "")},
                ]
            },
        ]

        kw = filter_kw.strip().lower()
        col = 0; row = 0
        for group in SCENARIO_GROUPS:
            # 过滤逻辑
            if kw:
                matched_items = [
                    it for it in group["items"]
                    if kw in it["name"].lower() or kw in it.get("desc", "").lower() or kw in group["title"].lower()
                ]
                if not matched_items:
                    continue
                display_group = dict(group)
                display_group["items"] = matched_items
            else:
                display_group = group

            card = self._build_scenario_group_card(display_group)
            self.experts_grid.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0; row += 1

    def _build_scenario_group_card(self, group: dict) -> QFrame:
        """构建复刻截图的场景大卡片组件，内含带 Hover 阴影与背景高亮的专家列表项"""
        card = QFrame()
        card.setFixedHeight(230)
        card.setMinimumWidth(260)
        d = self._is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        border = "#2a2a2a" if d else "#e2e8f0"
        title_fg = "#f4f4f5" if d else "#0f172a"
        item_fg = "#f4f4f5" if d else "#1e293b"
        hover_bg = "#27272a" if d else "#f1f5f9"
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 16px;
            }}
            QFrame:hover {{
                border-color: {'#404040' if d else '#6366f1'};
            }}
        """)

        # 细腻投影
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 60 if d else 30))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(16, 16, 16, 14)
        c_lay.setSpacing(8)

        # 头部标题行
        header_row = QHBoxLayout()
        title_lbl = QLabel(group.get("title", "场景"))
        title_lbl.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {title_fg}; font-family: 'Microsoft YaHei UI';")
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        icon_lbl = QLabel(group.get("icon", "✨"))
        icon_lbl.setFont(QFont("Segoe UI Emoji", 14))
        header_row.addWidget(icon_lbl)
        c_lay.addLayout(header_row)

        c_lay.addSpacing(2)

        # 专家列表小项 (每一个都可以 Hover 高亮和点击激活)
        for item in group.get("items", []):
            item_btn = QPushButton()
            item_btn.setFixedHeight(40)
            item_btn.setCursor(Qt.PointingHandCursor)
            item_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 10px;
                    padding: 0 8px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {hover_bg};
                }}
            """)

            btn_l = QHBoxLayout(item_btn)
            btn_l.setContentsMargins(4, 0, 4, 0)
            btn_l.setSpacing(10)

            # 圆形小头像
            avatar = QLabel(item.get("char", "专"))
            avatar.setFixedSize(26, 26)
            avatar.setAlignment(Qt.AlignCenter)
            avatar.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
            avatar.setStyleSheet(f"""
                background-color: {item.get('color', '#6366f1')};
                color: #ffffff;
                border-radius: 13px;
            """)
            btn_l.addWidget(avatar)

            # 专家名称
            name_lbl = QLabel(item.get("name", "未命名"))
            name_lbl.setStyleSheet(f"font-size: 12.5px; font-weight: 600; color: {item_fg}; font-family: 'Microsoft YaHei UI';")
            btn_l.addWidget(name_lbl, 1)

            # 点击事件绑定
            p = item.get("prompt", f"请以{item.get('name')}身份帮我")
            sp = item.get("system_prompt", "")
            item_btn.clicked.connect(lambda ch, prompt=p, sys_prompt=sp: self._activate_expert(prompt, sys_prompt))

            c_lay.addWidget(item_btn)

        c_lay.addStretch()
        return card


    def _activate_expert(self, prompt: str, system_prompt: str = ""):
        if system_prompt and self.ai_engine:
            self.ai_engine.system_prompt = system_prompt
        self._switch_nav(0)
        self._enter_active_chat_mode()
        self.input_edit.setText(prompt)
        self._send_active_message()

    # ── 技能 Tab ──────────────────────────────────────────────
    def _create_skills_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(12)
        d = self._is_dark

        top_row = QHBoxLayout()
        head = QLabel("精选技能")
        head.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        head.setStyleSheet(f"color: {'#f4f4f5' if d else '#0f172a'}; font-family: 'Microsoft YaHei UI';")
        top_row.addWidget(head)
        top_row.addStretch()

        self.skill_refresh_btn = QPushButton("↻ 刷新")
        self.skill_refresh_btn.setFixedHeight(28)
        self.skill_refresh_btn.setCursor(Qt.PointingHandCursor)
        self.skill_refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {'#27272a' if d else '#f1f5f9'};
                color: {'#a1a1aa' if d else '#64748b'};
                border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                border-radius: 6px; padding: 0 10px; font-size: 11.5px;
            }}
            QPushButton:hover {{
                background: {'#3f3f46' if d else '#e2e8f0'};
                color: {'#ffffff' if d else '#0f172a'};
            }}
        """)
        self.skill_refresh_btn.clicked.connect(self._rebuild_skills_grid)
        top_row.addWidget(self.skill_refresh_btn)
        lay.addLayout(top_row)

        self.skill_cat_row = QHBoxLayout()
        self.skill_cat_row.setSpacing(6)
        self.skill_cat_buttons = []
        categories = ["全部","办公协同","开发工具","投资理财","效率工具","内容创作","信息资讯","生活服务"]
        for cat in categories:
            b = QPushButton(cat)
            b.setCheckable(True)
            b.setFixedHeight(28)
            b.setCursor(Qt.PointingHandCursor)
            if cat == "全部": b.setChecked(True)
            self._apply_cat_btn_style(b, b.isChecked())
            b.clicked.connect(lambda c, cc=cat, btn=b: self._on_skill_cat_clicked(cc, btn))
            self.skill_cat_row.addWidget(b)
            self.skill_cat_buttons.append(b)
        self.skill_cat_row.addStretch()
        lay.addLayout(self.skill_cat_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;} QScrollArea > QWidget > QWidget{background:transparent;}")
        scroll.viewport().setStyleSheet("background: transparent; border: none;")

        self._skills_scroll_content = QWidget()
        self._skills_scroll_content.setStyleSheet("background: transparent;")
        self.skills_grid = QGridLayout(self._skills_scroll_content)
        self.skills_grid.setSpacing(10)
        self._rebuild_skills_grid()

        scroll.setWidget(self._skills_scroll_content)
        lay.addWidget(scroll, 1)
        return w

    def _apply_cat_btn_style(self, btn: QPushButton, checked: bool):
        d = self._is_dark
        if checked:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: #6366f1;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 0 12px;
                    font-size: 11.5px;
                    font-weight: bold;
                    font-family: 'Microsoft YaHei UI';
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#27272a' if d else '#ffffff'};
                    color: {'#d4d4d8' if d else '#475569'};
                    border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                    border-radius: 6px;
                    padding: 0 12px;
                    font-size: 11.5px;
                    font-family: 'Microsoft YaHei UI';
                }}
                QPushButton:hover {{
                    background: {'#3f3f46' if d else '#f1f5f9'};
                    color: {'#ffffff' if d else '#0f172a'};
                }}
            """)

    def _on_skill_cat_clicked(self, cat: str, clicked_btn: QPushButton):
        for b in self.skill_cat_buttons:
            b.setChecked(b == clicked_btn)
            self._apply_cat_btn_style(b, b == clicked_btn)
        self._filter_skill_cat(cat)

    def _filter_skill_cat(self, cat: str):
        self._current_skill_cat = cat
        kw = self.hub_search.text().strip() if hasattr(self, 'hub_search') else ""
        self._rebuild_skills_grid(filter_cat=cat, filter_kw=kw)

    def _get_skills_data(self) -> List[Dict]:
        local = load_skills_from_dir()
        builtin = [
            {"id":"web_search_news","name":"全网热搜搜索","description":"实时检索全网新闻热榜与资讯","cat":"信息资讯","char":"搜","color":"#ef4444","prompt":"帮我搜索今日全网科技热搜新闻"},
            {"id":"amap_lbs","name":"高德地图导航","description":"路线规划、天气查询与LBS生活服务","cat":"生活服务","char":"图","color":"#10b981","prompt":"帮我规划从北京到上海的最优驾车路线"},
            {"id":"markdownify","name":"Markdownify 文档转换","description":"PDF/Word/网页转 Markdown 文本提取","cat":"效率工具","char":"文","color":"#6366f1","prompt":"帮我把这个 PDF 文件转为 Markdown 格式"},
            {"id":"github_tools","name":"GitHub 代码管理","description":"搜索仓库、管理 Issue 与 PR","cat":"开发工具","char":"G","color":"#0f172a","prompt":"帮我搜索最近热门的 AI 桌面应用 GitHub 项目"},
            {"id":"ppt_tools","name":"PPT 生成大师","description":"根据主题和大纲一键生成商务 PPT","cat":"办公协同","char":"P","color":"#f59e0b","prompt":"帮我生成一份关于 AI 趋势的 20 页商务演示文稿"},
            {"id":"kuaidi100_tools","name":"快递100 物流查询","description":"全球快递公司单号追踪与运费预估","cat":"生活服务","char":"快","color":"#06b6d4","prompt":"帮我查询这个快递单号的实时物流状态"},
            {"id":"health_calculator_tools","name":"健康指标计算器","description":"BMI、体脂率、BMR 等健康参数计算","cat":"生活服务","char":"健","color":"#10b981","prompt":"帮我计算我的 BMI 和基础代谢率"},
            {"id":"firecrawl_tools","name":"Firecrawl 网页爬虫","description":"智能网络爬虫与结构化数据提取","cat":"开发工具","char":"爬","color":"#ef4444","prompt":"帮我爬取并分析这个网页的核心内容"},
            {"id":"ticket_12306_tools","name":"12306 火车票查询","description":"查询高铁余票、时刻表与票价信息","cat":"生活服务","char":"火","color":"#f59e0b","prompt":"查询明天北京到上海的高铁余票"},
            {"id":"file_tools","name":"文档处理大师","description":"Word/PDF 智能读取、修改与生成","cat":"办公协同","char":"档","color":"#8b5cf6","prompt":"帮我分析这份 PDF 文件并提取关键信息"},
            {"id":"knowledge_base_tools","name":"本地知识库 RAG","description":"查询本地向量知识库与文档问答","cat":"效率工具","char":"库","color":"#0284c7","prompt":"在我的本地知识库中查询相关内容"},
            {"id":"computer_control","name":"桌面自动化控制","description":"截图分析、应用操作与 Shell 执行","cat":"开发工具","char":"控","color":"#475569","prompt":"帮我截取当前屏幕并分析内容"},
        ]
        local_ids = {s["id"] for s in local}
        for s in local:
            s.setdefault("cat", "效率工具")
            s.setdefault("char", s["name"][:1])
            PALETTE = ["#6366f1","#8b5cf6","#06b6d4","#10b981","#f59e0b","#ef4444"]
            import hashlib
            s.setdefault("color", PALETTE[int(hashlib.md5(s["id"].encode()).hexdigest(),16) % len(PALETTE)])
            s.setdefault("prompt", f"使用 {s['name']} 技能帮我完成任务")
        for b in builtin:
            if b["id"] not in local_ids:
                local.append(b)
        return local

    def _rebuild_skills_grid(self, filter_cat: str = "全部", filter_kw: str = ""):
        for i in reversed(range(self.skills_grid.count())):
            w = self.skills_grid.itemAt(i).widget()
            if w: w.setParent(None)

        skills = self._get_skills_data()
        kw = filter_kw.strip().lower()
        col = 0; row = 0
        for s in skills:
            cat = s.get("cat", "")
            name = s.get("name", "")
            desc = s.get("description", "")
            if filter_cat != "全部" and cat != filter_cat:
                continue
            if kw and kw not in name.lower() and kw not in desc.lower():
                continue

            card = self._build_skill_card(s)
            self.skills_grid.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0; row += 1

    def _build_skill_card(self, s: Dict) -> QFrame:
        sid = s.get("id", "")
        name = s.get("name", "技能")
        desc = s.get("description", "")
        char = s.get("char", name[:1])
        color = s.get("color", "#6366f1")
        prompt = s.get("prompt", f"使用{name}技能")
        installed = sid in self._installed_skills

        card = QFrame()
        card.setFixedHeight(110)
        d = self._is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        border = "#2a2a2a" if d else "#e2e8f0"
        title_fg = "#f4f4f5" if d else "#0f172a"
        desc_fg = "#a1a1aa" if d else "#64748b"
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border-color: {'#404040' if d else '#6366f1'};
            }}
        """)

        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(12, 10, 12, 10)
        c_lay.setSpacing(6)

        top = QHBoxLayout(); top.setSpacing(8)
        badge = QLabel(char)
        badge.setFixedSize(30, 30)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        badge.setStyleSheet(f"background:{color};color:#fff;border-radius:15px;")
        top.addWidget(badge)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"font-size:12.5px;font-weight:bold;color:{title_fg};font-family:'Microsoft YaHei UI';")
        top.addWidget(name_lbl, 1)

        action_btn = QPushButton("✓ 已安装" if installed else "+ 添加")
        action_btn.setFixedSize(66, 24)
        if installed:
            action_btn.setStyleSheet(f"QPushButton{{background:{'#064e3b' if d else '#dcfce7'};color:{'#34d399' if d else '#15803d'};border:none;border-radius:6px;font-size:11px;font-weight:bold;}}")
        else:
            action_btn.setStyleSheet(f"QPushButton{{background:{'#27272a' if d else '#f1f5f9'};color:{'#f4f4f5' if d else '#475569'};border:1px solid {'#3f3f46' if d else '#e2e8f0'};border-radius:6px;font-size:11px;font-weight:bold;}} QPushButton:hover{{background:{'#3f3f46' if d else '#6366f1'};color:#fff;border:none;}}")
        action_btn.clicked.connect(lambda c, s_=s, b=action_btn: self._toggle_skill_install(s_, b))
        top.addWidget(action_btn)
        c_lay.addLayout(top)

        d_lbl = QLabel(desc)
        d_lbl.setWordWrap(True)
        d_lbl.setStyleSheet(f"font-size:11px;color:{desc_fg};font-family:'Microsoft YaHei UI';line-height:1.4;")
        c_lay.addWidget(d_lbl)

        card.mousePressEvent = lambda e, p=prompt: self._summon_with_prompt(p)
        return card

    def _toggle_skill_install(self, skill: Dict, btn: QPushButton):
        sid = skill.get("id", "")
        d = self._is_dark
        if sid in self._installed_skills:
            self._installed_skills.discard(sid)
            btn.setText("+ 添加")
            btn.setStyleSheet(
                f"QPushButton{{background:{'#27272a' if d else '#f1f5f9'};color:{'#f4f4f5' if d else '#475569'};border:1px solid {'#3f3f46' if d else '#e2e8f0'};"
                f"border-radius:6px;font-size:11px;font-weight:bold;}}"
                f"QPushButton:hover{{background:{'#3f3f46' if d else '#6366f1'};color:#fff;border:none;}}"
            )
            self._show_status(f"已移除技能：{skill.get('name','')}")
        else:
            self._installed_skills.add(sid)
            btn.setText("✓ 已安装")
            btn.setStyleSheet(
                "QPushButton{background:#064e3b;color:#34d399;border:none;border-radius:6px;font-size:11px;font-weight:bold;}" if d else
                "QPushButton{background:#dcfce7;color:#15803d;border:none;border-radius:6px;font-size:11px;font-weight:bold;}"
            )
            self._show_status(f"✅ 已添加技能：{skill.get('name','')}")

        self.my_installed_btn.setText(f"📦 我安装的 ({len(self._installed_skills)})")
        self.config.setdefault("plugins", {})["enabled"] = list(self._installed_skills)
        if self.save_config_fn:
            self.save_config_fn(self.config)

    def _switch_hub_tab(self, idx: int):
        self.hub_stack.setCurrentIndex(idx)
        d = self._is_dark
        on_style = ("QPushButton{background:#27272a;color:#ffffff;border:none;border-radius:8px;font-weight:bold;padding:0 16px;font-family:'Microsoft YaHei UI';}" if d else
                    "QPushButton{background:#6366f1;color:#fff;border:none;border-radius:8px;font-weight:bold;padding:0 16px;font-family:'Microsoft YaHei UI';}")
        off_style = ("QPushButton{background:transparent;color:#a1a1aa;border:none;font-weight:500;padding:0 16px;font-family:'Microsoft YaHei UI';} QPushButton:hover{background:#222222;color:#ffffff;}" if d else
                     "QPushButton{background:transparent;color:#64748b;border:none;font-weight:500;padding:0 16px;font-family:'Microsoft YaHei UI';} QPushButton:hover{background:#f1f5f9;}")
        self.hub_tab_expert.setStyleSheet(on_style if idx == 0 else off_style)
        self.hub_tab_skill.setStyleSheet(on_style if idx == 1 else off_style)
        self.hub_tab_conn.setStyleSheet(on_style if idx == 2 else off_style)

    def _on_hub_search(self, text: str):
        kw = text.strip().lower()
        idx = self.hub_stack.currentIndex()
        if idx == 0:
            self._rebuild_expert_cards(filter_kw=kw)
        elif idx == 1:
            cur_cat = next((b.text() for b in self.skill_cat_buttons if b.isChecked()), "全部")
            self._rebuild_skills_grid(filter_cat=cur_cat, filter_kw=kw)
        elif idx == 2:
            self._rebuild_connectors_grid(filter_kw=kw)

    def _on_custom_connector_dialog(self):
        name, ok = QInputDialog.getText(self, "自定义连接器", "输入 MCP 服务器名称或 URL：")
        if ok and name.strip():
            self._show_status(f"已添加自定义连接器：{name.strip()}")

    # ── 连接器 Tab (复刻截图 1) ──────────────────────────────────
    def _create_connectors_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;} QScrollArea > QWidget > QWidget{background:transparent;}")
        scroll.viewport().setStyleSheet("background: transparent;")

        self._conn_scroll_content = QWidget()
        self._conn_scroll_content.setStyleSheet("background: transparent;")
        self.conn_grid = QGridLayout(self._conn_scroll_content)
        self.conn_grid.setSpacing(10)
        self._rebuild_connectors_grid()

        scroll.setWidget(self._conn_scroll_content)
        lay.addWidget(scroll, 1)
        return w

    def _get_connectors_data(self) -> List[Dict]:
        return [
            {"id":"tdx","name":"通达信","char":"通","color":"#ef4444","desc":"通过通达信 MCP 查询全球股票行情数据、条件选股与研究报告"},
            {"id":"tx_stock_mcp","name":"腾讯自选股","char":"腾","color":"#ef4444","desc":"直连腾讯自选股，实时掌握毫秒级行情与资金动态，自然语言分析"},
            {"id":"qq_mail","name":"QQ邮箱","char":"邮","color":"#f59e0b","desc":"收发、搜索和整理 QQ 邮件，用自然语言读取邮件内容与日程"},
            {"id":"ima_kb","name":"ima知识库","char":"🐼","color":"#1e293b","desc":"引用知识库资料及文件，浏览知识库详情"},
            {"id":"enjoy_kb","name":"享知识库","char":"享","color":"#0284c7","desc":"搜索、创建和管理乐享知识库中的文档，支持导入 Markdown"},
            {"id":"tx_docs","name":"腾讯文档","char":"档","color":"#0284c7","desc":"创建、编辑和协作腾讯文档，用自然语言管理在线表格与幻灯片"},
            {"id":"tx_meeting","name":"腾讯会议","char":"会","color":"#0284c7","desc":"通过命令进行创建、查询和管理腾讯会议，支持快速发起会议"},
            {"id":"wecom","name":"企业微信","char":"企","color":"#10b981","desc":"企业微信官方 CLI 套件，覆盖消息、邮件、文档、待办与日程"},
            {"id":"feishu","name":"飞书","char":"飞","color":"#0284c7","desc":"通过命令行管理飞书/Lark全产品能力：即时通讯、邮箱、云文档"},
            {"id":"dingtalk","name":"钉钉","char":"钉","color":"#0284c7","desc":"通过命令行管理钉钉全产品能力：AI表格、考勤、日程与机器人"},
            {"id":"tx_survey","name":"腾讯问卷","char":"问","color":"#10b981","desc":"创建、管理和分析腾讯问卷，用自然语言快速生成问卷与回收数据"},
            {"id":"tapd","name":"TAPD","char":"T","color":"#0284c7","desc":"管理需求、缺陷、任务和迭代，查询项目进度与拆分需求"},
            {"id":"cnb","name":"CNB","char":"🏀","color":"#ea580c","desc":"通过自然语言管理 CNB 平台：仓库、Issue、PR、流水线与制品库"},
            {"id":"weiyun","name":"微云","char":"云","color":"#0284c7","desc":"查看、下载、删除微云文件，并且提供上传文件到微云与生成分享链接"},
            {"id":"fu_helper","name":"福帮手","char":"福","color":"#0284c7","desc":"福群手人机协同连接器：识别当前身份与专家入口，匹配岗位行业方案"},
            {"id":"wps_docs","name":"金山文档","char":"金","color":"#0284c7","desc":"创建、搜索和管理金山文档 (WPS 云文档)，支持多种文件类型"},
            {"id":"pkulaw","name":"北大法宝-法律智能检索","char":"法","color":"#b91c1c","desc":"检索-核验一体：语义 (自然语言描述) 与关键词双模式检索法条"},
            {"id":"qcc","name":"企查查","char":"企","color":"#0284c7","desc":"查询和核实企业工商登记信息，支持股东结构、实际控制人与对外投资"},
            {"id":"tianyancha","name":"天眼查","char":"天","color":"#0284c7","desc":"通过天眼查 MCP 查询多维度企业数据，支持工商登记、司法风险"},
            {"id":"baidu_pan","name":"百度网盘","char":"度","color":"#ef4444","desc":"连接百度网盘，支持文件与分类浏览、关键词与语义检索、文件管理"},
            {"id":"github_mcp","name":"GitHub","char":"G","color":"#0f172a","desc":"在 GitHub 上克隆、推送代码，查看和管理仓库与 Pull Request"},
            {"id":"notion_mcp","name":"Notion","char":"N","color":"#0f172a","desc":"创建、搜索和管理 Notion 工作区，用自然语言读取页面与整理知识库"},
            {"id":"tx_qidian","name":"腾讯企点客服","char":"企","color":"#4338ca","desc":"腾讯企点客服连接器：用自然语言处理工单与查询拉取客户资料"},
            {"id":"edgeone","name":"EdgeOne Makers","char":"E","color":"#0284c7","desc":"将项目部署到 EdgeOne Makers 并返回线上访问地址，支持全栈与函数"},
            {"id":"tcb","name":"腾讯云 CloudBase","char":"腾","color":"#0284c7","desc":"腾讯云开发 CloudBase 全栈开发、部署、调试与排障连接器"},
            {"id":"bugly","name":"Bugly 质量概览","char":"B","color":"#0284c7","desc":"查看产品的质量概览 包括崩溃率 anr率 foom (oom) 率 启动耗时"},
            {"id":"xiaoshouyi","name":"销售易CRM","char":"销","color":"#0284c7","desc":"用自然语言查客户、推商机、盘线索、领公海、写跟进，打通销售"},
            {"id":"xiaoetong","name":"小鹅通","char":"鹅","color":"#0284c7","desc":"用自然语言管理小鹅通店铺：查询课程与学员，创建和编辑课程"},
            {"id":"huayu","name":"华宇元典法律数据","char":"华","color":"#0284c7","desc":"华宇元典法律数据为智能体提供法律法规、案例文书与企业信息"},
            {"id":"weisheng","name":"微盛企微管家SCRM","char":"微","color":"#1e3a8a","desc":"查询或管理企业微信中的客户信息、客户标签、客户群与营销素材"},
            {"id":"zhongxing","name":"中兴新云AI报销","char":"云","color":"#0284c7","desc":"财务云 AI 报销助手：用自然语言完成报销申请、发票查询与费用审核"},
            {"id":"tx_ads","name":"腾讯营销投放","char":"腾","color":"#0284c7","desc":"腾讯营销投放 Skill，为大模型赋予广告投放管理能力：支持账户授权"},
        ]

    def _rebuild_connectors_grid(self, filter_kw: str = ""):
        for i in reversed(range(self.conn_grid.count())):
            w = self.conn_grid.itemAt(i).widget()
            if w: w.setParent(None)

        connectors = self._get_connectors_data()
        kw = filter_kw.strip().lower()
        col = 0; row = 0
        for c in connectors:
            name = c.get("name", "")
            desc = c.get("desc", "")
            if kw and kw not in name.lower() and kw not in desc.lower():
                continue

            card = self._build_connector_card(c)
            self.conn_grid.addWidget(card, row, col)
            col += 1
            if col >= 4:
                col = 0; row += 1

    def _build_connector_card(self, c: Dict) -> QFrame:
        card = QFrame()
        card.setFixedHeight(115)
        d = self._is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        border = "#2a2a2a" if d else "#e2e8f0"
        title_fg = "#f4f4f5" if d else "#0f172a"
        desc_fg = "#a1a1aa" if d else "#64748b"
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border-color: {'#404040' if d else '#6366f1'};
            }}
        """)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        top = QHBoxLayout(); top.setSpacing(8)
        icon_lbl = QLabel(c.get("char", "连"))
        icon_lbl.setFixedSize(28, 28)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        icon_lbl.setStyleSheet(f"background: {c.get('color', '#6366f1')}; color: #ffffff; border-radius: 6px;")
        top.addWidget(icon_lbl)

        name_lbl = QLabel(c.get("name", "连接器"))
        name_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {title_fg}; font-family: 'Microsoft YaHei UI';")
        top.addWidget(name_lbl, 1)

        cid = c.get("id", c.get("name", ""))
        is_conn = cid in self.config.get("connected_connectors", [])

        conn_btn = QPushButton("✓" if is_conn else "＋")
        conn_btn.setFixedSize(24, 24)
        conn_btn.setCursor(Qt.PointingHandCursor)
        if is_conn:
            conn_btn.setStyleSheet("background: #064e3b; color: #34d399; border: none; border-radius: 6px; font-size: 12px; font-weight: bold;" if d else "background: #dcfce7; color: #15803d; border: none; border-radius: 6px; font-size: 12px; font-weight: bold;")
        else:
            conn_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#27272a' if d else '#f1f5f9'};
                    color: {'#f4f4f5' if d else '#64748b'};
                    border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                    border-radius: 6px; font-size: 13px; font-weight: bold;
                }}
                QPushButton:hover {{ background: {'#3f3f46' if d else '#6366f1'}; color: #ffffff; border: none; }}
            """)
        conn_btn.clicked.connect(lambda ch, conn=c, b=conn_btn: self._on_connect_mcp(conn, b))
        top.addWidget(conn_btn)
        lay.addLayout(top)

        desc_lbl = QLabel(c.get("desc", ""))
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"font-size: 11px; color: {desc_fg}; font-family: 'Microsoft YaHei UI'; line-height: 1.4;")
        lay.addWidget(desc_lbl)

        return card

    def _on_connect_mcp(self, c: dict, btn: QPushButton):
        cid = c.get("id", c.get("name", ""))
        connected_set = set(self.config.get("connected_connectors", []))
        if btn.text() == "＋":
            btn.setText("✓")
            btn.setStyleSheet("background: #064e3b; color: #34d399; border: none; border-radius: 6px; font-size: 12px; font-weight: bold;" if self._is_dark else "background: #dcfce7; color: #15803d; border: none; border-radius: 6px; font-size: 12px; font-weight: bold;")
            connected_set.add(cid)
            self.config["connected_connectors"] = list(connected_set)
            if self.save_config_fn: self.save_config_fn(self.config)
            self._show_status(f"✅ 已连接 MCP：{c.get('name')}")
        else:
            btn.setText("＋")
            btn.setStyleSheet(f"background: {'#27272a' if self._is_dark else '#f1f5f9'}; color: {'#f4f4f5' if self._is_dark else '#64748b'}; border: 1px solid {'#3f3f46' if self._is_dark else '#e2e8f0'}; border-radius: 6px; font-size: 13px; font-weight: bold;")
            connected_set.discard(cid)
            self.config["connected_connectors"] = list(connected_set)
            if self.save_config_fn: self.save_config_fn(self.config)
            self._show_status(f"已断开连接：{c.get('name')}")

    # ══════════════════════════════════════════════════════════
    #  自动化页 (1:1 像素复刻截图 2 与截图 3)
    # ══════════════════════════════════════════════════════════
    def _create_automation_page(self) -> QWidget:
        page = QWidget()
        self.auto_main_stack = QStackedWidget(page)
        p_lay = QVBoxLayout(page)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.addWidget(self.auto_main_stack)

        # ── 视图 1：自动化主页 (截图 2)
        auto_home = QWidget()
        ml = QVBoxLayout(auto_home)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        auto_top = QWidget()
        auto_top.setFixedHeight(52)
        at_lay = QHBoxLayout(auto_top)
        at_lay.setContentsMargins(20, 8, 20, 8)
        at_lay.setSpacing(6)

        self.tab_sch = QPushButton("⏰ 定时任务")
        self.tab_log = QPushButton("📋 运行记录")
        for t in [self.tab_sch, self.tab_log]:
            t.setFixedHeight(32); t.setCheckable(True)
        self.tab_sch.clicked.connect(lambda: self._switch_auto_tab(0))
        self.tab_log.clicked.connect(lambda: self._switch_auto_tab(1))
        at_lay.addWidget(self.tab_sch); at_lay.addWidget(self.tab_log)
        at_lay.addStretch()
        ml.addWidget(auto_top)

        self.auto_stack = QStackedWidget()

        # Tab 0 — 定时任务主列表 & 空态 & 模板
        sch_page = QWidget()
        sch_lay = QVBoxLayout(sch_page)
        sch_lay.setContentsMargins(24, 16, 24, 16)
        sch_lay.setSpacing(14)

        # 上半部分：空态 (时钟图标 + 提示 + 黑色胶囊按钮)
        self.auto_empty_box = QWidget()
        e_lay = QVBoxLayout(self.auto_empty_box)
        e_lay.setContentsMargins(0, 20, 0, 24)
        e_lay.setSpacing(12)
        e_lay.setAlignment(Qt.AlignCenter)

        clock_icon = QLabel("⏰")
        clock_icon.setFont(QFont("Segoe UI Emoji", 36))
        clock_icon.setAlignment(Qt.AlignCenter)
        e_lay.addWidget(clock_icon)

        empty_tip = QLabel("开启你的第一个自动化任务吧")
        empty_tip.setStyleSheet(f"color: {'#a1a1aa' if self._is_dark else '#64748b'}; font-size: 13px; font-family: 'Microsoft YaHei UI';")
        empty_tip.setAlignment(Qt.AlignCenter)
        e_lay.addWidget(empty_tip)

        add_main_btn = QPushButton("＋ 添加自动化")
        add_main_btn.setFixedSize(140, 36)
        add_main_btn.setCursor(Qt.PointingHandCursor)
        add_main_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#27272a' if self._is_dark else '#0f172a'};
                color: #ffffff;
                border: 1px solid {'#3f3f46' if self._is_dark else 'none'};
                border-radius: 18px;
                font-size: 12.5px;
                font-weight: bold;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{ background-color: {'#3f3f46' if self._is_dark else '#1e293b'}; }}
        """)
        add_main_btn.clicked.connect(self._open_add_auto_view)
        e_lay.addWidget(add_main_btn, 0, Qt.AlignCenter)
        sch_lay.addWidget(self.auto_empty_box)

        # 当前激活任务列表 (有任务时展示)
        self.task_list_widget = QListWidget()
        self.task_list_widget.setFixedHeight(140)
        self.task_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_list_widget.customContextMenuRequested.connect(self._show_task_context_menu)
        sch_lay.addWidget(self.task_list_widget)
        self.task_list_widget.hide()

        # 下半部分：自动化任务模版
        self.tpl_head = QLabel("自动化任务模版")
        self.tpl_head.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
        sch_lay.addWidget(self.tpl_head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;} QScrollArea > QWidget > QWidget{background:transparent;}")
        scroll.viewport().setStyleSheet("background: transparent;")

        self._tpl_scroll_content = QWidget()
        self._tpl_scroll_content.setStyleSheet("background: transparent;")
        self.tpl_grid = QGridLayout(self._tpl_scroll_content)
        self.tpl_grid.setSpacing(12)
        self._rebuild_template_cards()

        scroll.setWidget(self._tpl_scroll_content)
        sch_lay.addWidget(scroll, 1)
        self.auto_stack.addWidget(sch_page)

        # Tab 1 — 运行记录
        log_page = QWidget()
        log_lay = QVBoxLayout(log_page)
        log_lay.setContentsMargins(24, 16, 24, 16)
        log_lay.setSpacing(10)

        log_head_row = QHBoxLayout()
        log_head = QLabel("运行记录")
        log_head.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        log_head_row.addWidget(log_head)
        log_head_row.addStretch()
        clear_log_btn = QPushButton("🗑 清空记录")
        clear_log_btn.setFixedHeight(28)
        clear_log_btn.clicked.connect(self._clear_auto_log)
        log_head_row.addWidget(clear_log_btn)
        log_lay.addLayout(log_head_row)

        self.log_list = QListWidget()
        self.log_list.setStyleSheet(
            "QListWidget{background:transparent;border:none;font-family:'Microsoft YaHei UI';font-size:12px;}"
            "QListWidget::item{padding:6px 10px;border-bottom:1px solid #f1f5f9;}"
            "QListWidget::item:selected{background:#f1f5f9;}"
        )
        log_lay.addWidget(self.log_list, 1)
        self.auto_stack.addWidget(log_page)

        ml.addWidget(self.auto_stack, 1)
        self.auto_main_stack.addWidget(auto_home)

        # ── 视图 2：添加自动化任务专属视图 (1:1 复刻截图 3)
        self.view_add_auto = self._create_add_auto_view()
        self.auto_main_stack.addWidget(self.view_add_auto)

        self._switch_auto_tab(0)
        self._refresh_task_list()
        return page

    def _create_add_auto_view(self) -> QWidget:
        """1:1 复刻截图 3 的全屏/专属添加自动化任务页面"""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(12)

        # 顶部导航行：⏰ 自动化 / 添加自动化任务  [取消] [保存]
        top_row = QHBoxLayout()
        nav_lbl = QLabel("⏰ 自动化 / 添加自动化任务")
        nav_lbl.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        top_row.addWidget(nav_lbl)
        top_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(68, 32)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {'#27272a' if self._is_dark else '#f1f5f9'}; color: {'#f4f4f5' if self._is_dark else '#475569'}; border: 1px solid {'#3f3f46' if self._is_dark else '#e2e8f0'};
                border-radius: 8px; font-size: 12px; font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{ background: {'#3f3f46' if self._is_dark else '#e2e8f0'}; }}
        """)
        cancel_btn.clicked.connect(lambda: self.auto_main_stack.setCurrentIndex(0))
        top_row.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setFixedSize(68, 32)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {'#27272a' if self._is_dark else '#0f172a'}; color: #ffffff; border: 1px solid {'#3f3f46' if self._is_dark else 'none'};
                border-radius: 8px; font-size: 12px; font-weight: bold; font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{ background: {'#3f3f46' if self._is_dark else '#1e293b'}; }}
        """)
        save_btn.clicked.connect(self._save_new_automation_from_view)
        top_row.addWidget(save_btn)
        lay.addLayout(top_row)

        # 滚动表单区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        form_w = QWidget()
        f_lay = QVBoxLayout(form_w)
        f_lay.setContentsMargins(0, 4, 0, 10)
        f_lay.setSpacing(12)

        # 蓝色提示条
        d = self._is_dark
        tip_box = QFrame()
        if d:
            tip_box.setStyleSheet("background: #0f172a; border: 1px solid #1e3a8a; border-radius: 8px;")
        else:
            tip_box.setStyleSheet("background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px;")
        t_lay = QHBoxLayout(tip_box)
        t_lay.setContentsMargins(12, 8, 12, 8)
        tip_icon = QLabel("提示")
        tip_icon.setStyleSheet("background: #3b82f6; color: #fff; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: bold;")
        t_lay.addWidget(tip_icon)
        tip_text = QLabel("自动化任务执行时，请勿关闭电脑或退出客户端，否则任务将无法正常执行")
        tip_text.setStyleSheet(f"color: {'#93c5fd' if d else '#1d4ed8'}; font-size: 12px; font-family: 'Microsoft YaHei UI';")
        t_lay.addWidget(tip_text, 1)
        close_tip = QPushButton("✕")
        close_tip.setFixedSize(20, 20)
        close_tip.setStyleSheet(f"background: transparent; color: {'#93c5fd' if d else '#60a5fa'}; border: none;")
        close_tip.clicked.connect(lambda: tip_box.hide())
        t_lay.addWidget(close_tip)
        f_lay.addWidget(tip_box)

        inp_style = f"""
            QLineEdit, QTextEdit, QComboBox {{
                background: {'#1e1e1e' if d else '#ffffff'};
                color: {'#f4f4f5' if d else '#0f172a'};
                border: 1px solid {'#2e2e2e' if d else '#e2e8f0'};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12.5px;
                font-family: 'Microsoft YaHei UI';
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-color: #6366f1;
            }}
        """

        # 1. 名称
        name_lbl = QLabel("名称")
        name_lbl.setStyleSheet(f"font-size: 12px; color: {'#a1a1aa' if d else '#64748b'};")
        f_lay.addWidget(name_lbl)
        self.auto_name_edit = QLineEdit()
        self.auto_name_edit.setFixedHeight(36)
        self.auto_name_edit.setStyleSheet(inp_style)
        f_lay.addWidget(self.auto_name_edit)

        # 2. 工作空间 (可选)
        ws_lbl = QLabel("工作空间 (可选)")
        ws_lbl.setStyleSheet(f"font-size: 12px; color: {'#a1a1aa' if d else '#64748b'};")
        f_lay.addWidget(ws_lbl)
        self.auto_ws_btn = QPushButton("＋")
        self.auto_ws_btn.setFixedSize(36, 36)
        self.auto_ws_btn.setStyleSheet(f"background: {'#1e1e1e' if d else '#ffffff'}; border: 1px dashed {'#3f3f46' if d else '#cbd5e1'}; border-radius: 8px; font-size: 16px; color: {'#a1a1aa' if d else '#64748b'};")
        self.auto_ws_btn.clicked.connect(self._open_workspace_selector_popup)
        f_lay.addWidget(self.auto_ws_btn)

        # 3. 提示词
        prompt_lbl = QLabel("提示词")
        prompt_lbl.setStyleSheet(f"font-size: 12px; color: {'#a1a1aa' if d else '#64748b'};")
        f_lay.addWidget(prompt_lbl)
        self.auto_prompt_edit = QTextEdit()
        self.auto_prompt_edit.setFixedHeight(120)
        self.auto_prompt_edit.setPlaceholderText("输入自动化任务执行时交给 AI 的指令...")
        self.auto_prompt_edit.setStyleSheet(inp_style)
        f_lay.addWidget(self.auto_prompt_edit)

        # 提示词下方辅助胶囊行：⚙️ Auto ∨、🪄 技能 ∨、🎓 召唤专家 ∨、⚠️ 完全访问权限 ∨ (1:1 复刻截图 3/4/5)
        pill_row = QHBoxLayout()
        pill_row.setSpacing(8)

        capsule_style = f"""
            QPushButton {{
                background: {'#27272a' if d else '#f1f5f9'}; color: {'#f4f4f5' if d else '#334155'}; border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                border-radius: 6px; padding: 0 10px; font-size: 11.5px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{ background: {'#3f3f46' if d else '#e2e8f0'}; color: {'#ffffff' if d else '#0f172a'}; }}
        """

        self.auto_pill_model = QPushButton("⚙️ Auto ∨")
        self.auto_pill_model.setFixedHeight(28)
        self.auto_pill_model.setCursor(Qt.PointingHandCursor)
        self.auto_pill_model.setStyleSheet(capsule_style)
        self.auto_pill_model.clicked.connect(self._on_auto_model_pill_clicked)
        pill_row.addWidget(self.auto_pill_model)

        self.auto_pill_skill = QPushButton("🪄 技能 ∨")
        self.auto_pill_skill.setFixedHeight(28)
        self.auto_pill_skill.setCursor(Qt.PointingHandCursor)
        self.auto_pill_skill.setStyleSheet(capsule_style)
        self.auto_pill_skill.clicked.connect(self._on_auto_skill_pill_clicked)
        pill_row.addWidget(self.auto_pill_skill)

        self.auto_pill_expert = QPushButton("🎓 召唤专家 ∨")
        self.auto_pill_expert.setFixedHeight(28)
        self.auto_pill_expert.setCursor(Qt.PointingHandCursor)
        self.auto_pill_expert.setStyleSheet(capsule_style)
        self.auto_pill_expert.clicked.connect(self._on_auto_expert_pill_clicked)
        pill_row.addWidget(self.auto_pill_expert)

        self.auto_pill_perm = QPushButton("⚠️ 完全访问权限 ∨")
        self.auto_pill_perm.setFixedHeight(28)
        self.auto_pill_perm.setCursor(Qt.PointingHandCursor)
        self.auto_pill_perm.setStyleSheet(f"""
            QPushButton {{
                background: {'#431407' if d else '#fff7ed'}; color: {'#fdba74' if d else '#ea580c'}; border: 1px solid {'#7c2d12' if d else '#ffedd5'};
                border-radius: 6px; padding: 0 10px; font-size: 11.5px;
                font-family: 'Microsoft YaHei UI'; font-weight: 500;
            }}
            QPushButton:hover {{ background: {'#7c2d12' if d else '#ffedd5'}; }}
        """)
        self.auto_pill_perm.clicked.connect(self._on_auto_perm_pill_clicked)
        pill_row.addWidget(self.auto_pill_perm)

        pill_row.addStretch()
        f_lay.addLayout(pill_row)

        # 4. 连接器
        conn_lbl = QLabel("连接器 (勾选即授权该连接器在任务中免确认使用)")
        conn_lbl.setStyleSheet(f"font-size: 12px; color: {'#a1a1aa' if d else '#64748b'};")
        f_lay.addWidget(conn_lbl)
        self.auto_conn_combo = QComboBox()
        self.auto_conn_combo.setFixedHeight(36)
        self.auto_conn_combo.addItems(["选择连接器", "腾讯自选股", "通达信", "企业微信", "飞书", "钉钉", "百度网盘", "GitHub", "Notion", "北大法宝", "金山文档", "企查查"])
        self.auto_conn_combo.setStyleSheet(inp_style)
        f_lay.addWidget(self.auto_conn_combo)

        # 5. 执行频率 (1:1 复刻截图 1 & 截图 2)
        self.freq_title_lbl = QLabel("执行频率")
        self.freq_title_lbl.setStyleSheet("font-size: 12px; color: #64748b;")
        f_lay.addWidget(self.freq_title_lbl)

        freq_btn_row = QHBoxLayout(); freq_btn_row.setSpacing(6)
        self.freq_btn_period = QPushButton("周期")
        self.freq_btn_interval = QPushButton("按间隔")
        self.freq_btn_single = QPushButton("单次")
        for fb in [self.freq_btn_period, self.freq_btn_interval, self.freq_btn_single]:
            fb.setFixedSize(68, 28)
            fb.setCursor(Qt.PointingHandCursor)
            fb.setCheckable(True)
        self.freq_btn_period.clicked.connect(lambda: self._switch_freq_mode(0))
        self.freq_btn_interval.clicked.connect(lambda: self._switch_freq_mode(1))
        self.freq_btn_single.clicked.connect(lambda: self._switch_freq_mode(2))
        freq_btn_row.addWidget(self.freq_btn_period)
        freq_btn_row.addWidget(self.freq_btn_interval)
        freq_btn_row.addWidget(self.freq_btn_single)
        freq_btn_row.addStretch()
        f_lay.addLayout(freq_btn_row)

        # 频率具体配置 Stack (3 种模式动态切换)
        self.freq_stack = QStackedWidget()

        # ── 模式 0：周期
        w_period = QWidget()
        l_period = QHBoxLayout(w_period); l_period.setContentsMargins(0, 4, 0, 4); l_period.setSpacing(8)
        self.auto_cycle_combo = QComboBox()
        self.auto_cycle_combo.setFixedSize(90, 34)
        self.auto_cycle_combo.addItems(["每天", "工作日", "每周", "每月"])
        self.auto_cycle_combo.setStyleSheet(inp_style)
        l_period.addWidget(self.auto_cycle_combo)

        self.auto_time_edit = QTimeEdit()
        self.auto_time_edit.setDisplayFormat("HH:mm")
        self.auto_time_edit.setTime(QTime.currentTime())
        self.auto_time_edit.setFixedSize(110, 34)
        self.auto_time_edit.setStyleSheet(inp_style)
        l_period.addWidget(self.auto_time_edit)
        l_period.addStretch()
        self.freq_stack.addWidget(w_period)

        # ── 模式 1：按间隔 (复刻截图 1)
        w_interval = QWidget()
        l_interval = QHBoxLayout(w_interval); l_interval.setContentsMargins(0, 4, 0, 4); l_interval.setSpacing(8)
        lbl_every = QLabel("每")
        lbl_every.setStyleSheet("font-size: 12.5px; color: #0f172a;")
        l_interval.addWidget(lbl_every)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 24)
        self.interval_spin.setValue(1)
        self.interval_spin.setFixedSize(60, 32)
        self.interval_spin.setStyleSheet(inp_style)
        l_interval.addWidget(self.interval_spin)

        lbl_hour = QLabel("小时")
        lbl_hour.setStyleSheet("font-size: 12.5px; color: #0f172a;")
        l_interval.addWidget(lbl_hour)
        l_interval.addSpacing(10)

        # 星期选择胶囊组：周一 ~ 周日
        self.weekday_buttons = []
        for wd in ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]:
            wb = QPushButton(wd)
            wb.setFixedSize(48, 28)
            wb.setCursor(Qt.PointingHandCursor)
            wb.setCheckable(True)
            wb.setChecked(True)
            wb.setStyleSheet("""
                QPushButton {
                    background: #f1f5f9; color: #334155; border: 1px solid #e2e8f0;
                    border-radius: 6px; font-size: 11.5px; font-family: 'Microsoft YaHei UI';
                }
                QPushButton:checked {
                    background: #e2e8f0; color: #0f172a; font-weight: bold; border-color: #cbd5e1;
                }
            """)
            l_interval.addWidget(wb)
            self.weekday_buttons.append(wb)
        l_interval.addStretch()
        self.freq_stack.addWidget(w_interval)

        # ── 模式 2：单次 (复刻截图 2)
        w_single = QWidget()
        l_single = QHBoxLayout(w_single); l_single.setContentsMargins(0, 4, 0, 4); l_single.setSpacing(8)
        self.single_time_edit = QTimeEdit()
        self.single_time_edit.setDisplayFormat("HH:mm")
        self.single_time_edit.setTime(QTime.currentTime())
        self.single_time_edit.setFixedSize(110, 34)
        self.single_time_edit.setStyleSheet(inp_style)
        l_single.addWidget(self.single_time_edit)

        self.single_date_edit = QDateEdit()
        self.single_date_edit.setDisplayFormat("yyyy/MM/dd ddd")
        self.single_date_edit.setDate(QDate.currentDate())
        self.single_date_edit.setFixedSize(160, 34)
        self.single_date_edit.setStyleSheet(inp_style)
        l_single.addWidget(self.single_date_edit)
        l_single.addStretch()
        self.freq_stack.addWidget(w_single)

        f_lay.addWidget(self.freq_stack)
        self._switch_freq_mode(0)

        # 6. 生效日期区间 (可选)
        date_lbl = QLabel("生效日期区间 (可选，留空表示始终生效。)")
        date_lbl.setStyleSheet("font-size: 12px; color: #64748b;")
        f_lay.addWidget(date_lbl)
        self.auto_date_edit = QLineEdit()
        self.auto_date_edit.setFixedHeight(36)
        self.auto_date_edit.setPlaceholderText("选择生效日期")
        self.auto_date_edit.setStyleSheet(inp_style)
        f_lay.addWidget(self.auto_date_edit)

        # 7. 推送配置
        push_row1 = QHBoxLayout()
        push_lbl1 = QLabel("推送到 NovaDesk 微信小程序 ⓘ")
        push_lbl1.setStyleSheet("font-size: 12px; color: #0f172a;")
        push_row1.addWidget(push_lbl1)
        push_row1.addStretch()
        push_sw1 = ToggleSwitch(checked=False)
        push_row1.addWidget(push_sw1)
        f_lay.addLayout(push_row1)

        push_row2 = QHBoxLayout()
        push_lbl2 = QLabel("推送到企业微信 bot ⓘ")
        push_lbl2.setStyleSheet("font-size: 12px; color: #0f172a;")
        push_row2.addWidget(push_lbl2)
        push_row2.addStretch()
        push_sw2 = ToggleSwitch(checked=False)
        push_row2.addWidget(push_sw2)
        f_lay.addLayout(push_row2)

        scroll.setWidget(form_w)
        lay.addWidget(scroll, 1)
        return w

    def _switch_freq_mode(self, idx: int):
        self.freq_stack.setCurrentIndex(idx)
        btns = [self.freq_btn_period, self.freq_btn_interval, self.freq_btn_single]
        for i, b in enumerate(btns):
            active = (i == idx)
            b.setChecked(active)
            b.setStyleSheet(
                "background: #0f172a; color: #fff; border: none; border-radius: 6px; font-size: 11.5px; font-weight: bold;"
                if active else
                "background: #f1f5f9; color: #475569; border: none; border-radius: 6px; font-size: 11.5px;"
            )
        if idx == 2:
            self.freq_title_lbl.setText("执行频率 (建议避开上午高峰时段，高峰期容易排队等待；选择非高峰期执行更稳定)")
        else:
            self.freq_title_lbl.setText("执行频率")

    def _on_auto_model_pill_clicked(self):
        models = ["⚙️ Auto", "🤖 DeepSeek-V3", "🤖 DeepSeek-R1", "🤖 Qwen2.5-Coder"]
        menu = QMenu(self)
        for m in models:
            act = menu.addAction(m)
            act.triggered.connect(lambda ch, mod=m: self.auto_pill_model.setText(f"{mod} ∨"))
        sender = self.sender() or self.auto_pill_model
        menu.exec_(sender.mapToGlobal(QPoint(0, sender.height() + 2)))

    def _on_auto_skill_pill_clicked(self):
        skills = self._get_skills_data()
        popup = AutoSkillSelectPopup(skills=skills, is_dark=self._is_dark, parent=self)
        popup.skill_selected.connect(self._insert_skill_into_auto_prompt)
        popup.import_requested.connect(lambda: self._show_status("已唤起技能导入向导"))
        sender = self.sender() or self.auto_pill_skill
        pos = sender.mapToGlobal(QPoint(0, -popup.sizeHint().height() - 8))
        popup.move(pos)
        popup.show()

    def _insert_skill_into_auto_prompt(self, name: str, prompt: str):
        cursor = self.auto_prompt_edit.textCursor()
        cursor.insertText(f" [技能: {name}] ")
        self.auto_prompt_edit.setFocus()
        self._show_status(f"已引入技能：{name}")

    def _on_auto_expert_pill_clicked(self):
        popup = AutoExpertSelectPopup(is_dark=self._is_dark, parent=self)
        popup.expert_selected.connect(self._insert_expert_into_auto_prompt)
        popup.more_requested.connect(lambda: self._switch_nav(1))
        sender = self.sender() or self.auto_pill_expert
        pos = sender.mapToGlobal(QPoint(0, -popup.sizeHint().height() - 8))
        popup.move(pos)
        popup.show()

    def _insert_expert_into_auto_prompt(self, name: str, prompt: str):
        cursor = self.auto_prompt_edit.textCursor()
        cursor.insertText(f" @{name} ")
        self.auto_prompt_edit.setFocus()
        self._show_status(f"已召唤专家：{name}")

    def _on_auto_perm_pill_clicked(self):
        is_full = ("完全" in self.auto_pill_perm.text())
        popup = AutoPermissionSelectPopup(
            current_perm="full" if is_full else "standard",
            is_dark=self._is_dark,
            parent=self
        )
        popup.permission_chosen.connect(self._on_auto_perm_chosen)
        sender = self.sender() or self.auto_pill_perm
        pos = sender.mapToGlobal(QPoint(0, -popup.sizeHint().height() - 8))
        popup.move(pos)
        popup.show()

    def _on_auto_perm_chosen(self, mode: str):
        if mode == "full":
            self.auto_pill_perm.setText("⚠️ 完全访问权限 ∨")
            self.auto_pill_perm.setStyleSheet("""
                QPushButton {
                    background: #fff7ed; color: #ea580c; border: 1px solid #ffedd5;
                    border-radius: 6px; padding: 0 10px; font-size: 11.5px;
                    font-family: 'Microsoft YaHei UI'; font-weight: 500;
                }
                QPushButton:hover { background: #ffedd5; }
            """)
        else:
            self.auto_pill_perm.setText("🛡️ 默认权限 ∨")
            self.auto_pill_perm.setStyleSheet("""
                QPushButton {
                    background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0;
                    border-radius: 6px; padding: 0 10px; font-size: 11.5px;
                    font-family: 'Microsoft YaHei UI'; font-weight: 500;
                }
                QPushButton:hover { background: #e2e8f0; }
            """)

    def _open_add_auto_view(self, name: str = "", prompt: str = ""):
        self.auto_name_edit.setText(name)
        self.auto_prompt_edit.setText(prompt)
        self.auto_main_stack.setCurrentIndex(1)

    def _save_new_automation_from_view(self):
        name = self.auto_name_edit.text().strip()
        prompt = self.auto_prompt_edit.toPlainText().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请填写任务名称")
            return
        if not prompt:
            QMessageBox.warning(self, "提示", "请填写提示词指令")
            return

        t = self.auto_time_edit.time()
        time_str = f"{t.hour():02d}:{t.minute():02d}"

        try:
            from core.pet_scheduler import PetScheduler
            sched = PetScheduler.get_instance()
            sched.add_reminder(
                content=prompt,
                target_time_str=time_str,
                title=f"⏰ {name}",
                motion="nod"
            )
            self._log_auto_run(name, prompt, "已创建", "pending")
            self._refresh_task_list()
            self.auto_main_stack.setCurrentIndex(0)
            self._show_status(f"✅ 自动化任务已创建：{name} ({time_str})")
        except Exception as e:
            QMessageBox.warning(self, "创建失败", f"创建自动化任务失败：{e}")

    def _refresh_task_list(self):
        if not hasattr(self, 'task_list_widget'):
            return
        self.task_list_widget.clear()
        try:
            from core.pet_scheduler import PetScheduler
            sched = PetScheduler.get_instance()
            reminders = sched.get_all_reminders()
        except Exception:
            reminders = []

        has_tasks = (len(reminders) > 0)
        self.auto_empty_box.setVisible(not has_tasks)
        self.task_list_widget.setVisible(has_tasks)

        for r in reminders:
            remain = r.get("remain_sec", 0)
            h = remain // 3600; m = (remain % 3600) // 60; s = remain % 60
            remain_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
            item = QListWidgetItem(
                f"  ⏰  {r.get('content','')[:40]}   |   触发时间: {r.get('time','')}   |   剩余: {remain_str}"
            )
            item.setData(Qt.UserRole, r.get("id"))
            self.task_list_widget.addItem(item)


    def _rebuild_template_cards(self):
        if not hasattr(self, 'tpl_grid'):
            return
        for i in reversed(range(self.tpl_grid.count())):
            w = self.tpl_grid.itemAt(i).widget()
            if w: w.setParent(None)

        templates = [
            ("📑","每日 AI 新闻推送","关注当前 AI 领域的重磅动态，精准 AI coding 与具身智能进展，筛选推送...","查全网热搜新闻与最新科技动态"),
            ("🗣️","每日 5 个英语单词","每天推荐 5 个高频实用英语单词，包含词义、音标、例句与记忆提示。","生成今日英语单词学习卡片"),
            ("🌙","每日儿童睡前故事","生成 3-5 分钟可读的温和睡前故事，情节完整附带寓意，符合儿童心理。","写一篇今晚的温馨儿童睡前故事"),
            ("📊","每周工作周报","每周五汇总仓库 PR 与 Issue 进展，输出关键变更与待关注事项。","生成本周工作总结与下周计划"),
            ("🎬","经典电影推荐","推荐一部高分经典电影，简要介绍剧情梗概、亮点与推荐理由，全程...","推荐一部高分经典电影并解析其艺术特色"),
            ("📅","历史上的今天","从科技、电影、音乐等领域挑选一件“今天发生过”的有趣事件，200-30...","查历史上的今天有哪些大事发生"),
            ("💡","每日一个为什么","每天挑出一个有趣问题，先提问再解答，通俗易懂，例句轻松，答案...","每日一个为什么趣味科普问答"),
            ("☎️","父母联系提醒","每周日 10:00 提醒你给家人打电话或发消息，简单问候近况。","起草一份给父母的温馨问候信息"),
            ("💊","体检预约提醒","在 2026/04/08 07:00 提醒你确认体检时间、准备证件，并注意空腹与...","生成体检前注意事项清单"),
            ("🎯","面试准备提醒","工作日每 2 小时提醒你复习大模型面试内容，生成 3 个模拟题。","生成 3 道大模型高频面试真题"),
            ("🤝","会议前准备","在会议开始前提醒你整理议题、目标、待确认问题和关键结论。","梳理高效会议准备清单"),
            ("🖼️","可爱萌宠手机壁纸","随机从 7 种不同风格中挑选一种，为你生成一张 9:16 竖版高清壁纸方案...","设计一张治愈系萌宠壁纸方案"),
        ]
        for idx, (icon, tname, tdesc, tcmd) in enumerate(templates):
            tcard = self._build_template_card(icon, tname, tdesc, tcmd)
            self.tpl_grid.addWidget(tcard, idx // 3, idx % 3)

    def _build_template_card(self, icon, name, desc, cmd) -> QFrame:
        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        d = self._is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        border = "#2a2a2a" if d else "#e2e8f0"
        title_fg = "#f4f4f5" if d else "#0f172a"
        desc_fg = "#a1a1aa" if d else "#64748b"
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QFrame:hover {{ border-color: {'#404040' if d else '#6366f1'}; }}
        """)
        c_lay = QHBoxLayout(card)
        c_lay.setContentsMargins(14, 12, 14, 12)
        c_lay.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 18))
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignCenter)
        c_lay.addWidget(icon_lbl)

        v = QVBoxLayout(); v.setSpacing(2)
        n_lbl = QLabel(name)
        n_lbl.setStyleSheet(f"font-size:12.5px;font-weight:bold;color:{title_fg};font-family:'Microsoft YaHei UI';")
        d_lbl = QLabel(desc)
        d_lbl.setWordWrap(True)
        d_lbl.setStyleSheet(f"font-size:11px;color:{desc_fg};font-family:'Microsoft YaHei UI';")
        v.addWidget(n_lbl); v.addWidget(d_lbl)
        c_lay.addLayout(v, 1)

        exec_btn = QPushButton("▶")
        exec_btn.setFixedSize(32, 32)
        exec_btn.setToolTip("立即执行")
        exec_btn.setStyleSheet(f"""
            QPushButton {{
                background: {'#27272a' if d else '#f1f5f9'};
                color: {'#f4f4f5' if d else '#475569'};
                border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                border-radius: 8px; font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {'#3f3f46' if d else '#6366f1'}; color: #fff; border: none; }}
        """)
        exec_btn.clicked.connect(lambda c, t_name=name, t_cmd=cmd: self._execute_template(t_name, t_cmd))
        c_lay.addWidget(exec_btn)

        # 点击卡片进入完整配置视图
        card.mousePressEvent = lambda e, t_name=name, t_cmd=cmd: self._open_add_auto_view(t_name, t_cmd)
        return card

    def _add_automation_task(self):
        self._open_add_auto_view()


    def _show_task_context_menu(self, pos):
        item = self.task_list_widget.itemAt(pos)
        if not item:
            return
        rid = item.data(Qt.UserRole)
        menu = QMenu(self)
        act_cancel = menu.addAction("🗑 取消此任务")
        act = menu.exec_(self.task_list_widget.mapToGlobal(pos))
        if act == act_cancel:
            try:
                from core.pet_scheduler import PetScheduler
                PetScheduler.get_instance().cancel_reminder(rid)
                self._refresh_task_list()
                self._show_status("任务已取消")
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def _execute_template(self, name: str, cmd: str):
        reply = QMessageBox.question(
            self, f"执行模板：{name}",
            f"确认立即执行此自动化任务？\n\n指令：{cmd}\n\n执行后将自动发送到 AI 对话。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._log_auto_run(name, cmd, "已执行", "success")
            self._refresh_auto_log()
            self._summon_with_prompt(cmd)

    def _switch_auto_tab(self, idx: int):
        self.auto_stack.setCurrentIndex(idx)
        d = self._is_dark
        on_style = ("QPushButton{background:#27272a;color:#ffffff;border:none;border-radius:8px;font-weight:bold;padding:0 16px;font-family:'Microsoft YaHei UI';}" if d else
                    "QPushButton{background:#0f172a;color:#fff;border:none;border-radius:8px;font-weight:bold;padding:0 16px;font-family:'Microsoft YaHei UI';}")
        off_style = ("QPushButton{background:transparent;color:#a1a1aa;border:none;font-weight:500;padding:0 16px;font-family:'Microsoft YaHei UI';} QPushButton:hover{background:#222222;color:#ffffff;}" if d else
                     "QPushButton{background:transparent;color:#64748b;border:none;font-weight:500;padding:0 16px;font-family:'Microsoft YaHei UI';} QPushButton:hover{background:#f1f5f9;}")
        self.tab_sch.setStyleSheet(on_style if idx == 0 else off_style)
        self.tab_log.setStyleSheet(on_style if idx == 1 else off_style)
        if idx == 0:
            self._refresh_task_list()
        else:
            self._refresh_auto_log()

    def _log_auto_run(self, name: str, cmd: str, status: str, result: str):
        log = load_auto_log()
        log.append({
            "name": name,
            "cmd": cmd,
            "status": status,
            "result": result,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        save_auto_log(log)

    def _refresh_auto_log(self):
        if not hasattr(self, 'log_list'):
            return
        self.log_list.clear()
        log = load_auto_log()
        for entry in reversed(log[-100:]):
            status_icon = "✅" if entry.get("result") == "success" else "⏳"
            item = QListWidgetItem(
                f"  {status_icon}  [{entry.get('time','')[:16]}]  {entry.get('name','')}  —  {entry.get('status','')}"
            )
            self.log_list.addItem(item)
        if self.log_list.count() == 0:
            item = QListWidgetItem("  暂无运行记录")
            item.setForeground(QColor("#94a3b8"))
            self.log_list.addItem(item)

    def _clear_auto_log(self):
        reply = QMessageBox.question(self, "清空记录", "确认清空所有运行记录？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            save_auto_log([])
            self._refresh_auto_log()

    # ══════════════════════════════════════════════════════════
    #  设置与模型页 (真实 models_list 双向同步)
    # ══════════════════════════════════════════════════════════
    def _create_settings_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(14)

        top_h = QHBoxLayout()
        head = QLabel("已配置模型")
        head.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        top_h.addWidget(head)
        top_h.addStretch()

        self.add_model_btn = QPushButton("+ 添加新模型")
        self.add_model_btn.setFixedHeight(32)
        self.add_model_btn.setStyleSheet(
            "QPushButton{background:#6366f1;color:#fff;border:none;border-radius:8px;"
            "font-weight:bold;padding:0 16px;font-family:'Microsoft YaHei UI';}"
            "QPushButton:hover{background:#4f46e5;}"
        )
        self.add_model_btn.clicked.connect(self._add_new_model)
        top_h.addWidget(self.add_model_btn)
        lay.addLayout(top_h)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(240)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;} QScrollArea > QWidget > QWidget{background:transparent;}")
        scroll.viewport().setStyleSheet("background: transparent;")

        self._model_list_content = QWidget()
        self._model_list_content.setStyleSheet("background: transparent;")
        self._model_list_vlay = QVBoxLayout(self._model_list_content)
        self._model_list_vlay.setContentsMargins(0, 0, 0, 0)
        self._model_list_vlay.setSpacing(8)
        self._model_list_vlay.addStretch()
        scroll.setWidget(self._model_list_content)
        lay.addWidget(scroll)
        self._refresh_model_cards()

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#2e2e2e;min-height:1px;max-height:1px;" if self._is_dark else "background:#e2e8f0;min-height:1px;max-height:1px;")
        lay.addWidget(sep)

        edit_head = QLabel("快速配置当前模型")
        edit_head.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        edit_head.setStyleSheet(f"color:{'#f4f4f5' if self._is_dark else '#0f172a'};")
        lay.addWidget(edit_head)

        self.form_card = QFrame()
        f_lay = QFormLayout(self.form_card)
        f_lay.setSpacing(10)
        f_lay.setContentsMargins(16, 14, 16, 14)

        self.cfg_name_edit = QLineEdit()
        self.cfg_name_edit.setFixedHeight(34)
        f_lay.addRow("显示名称：", self.cfg_name_edit)

        self.cfg_provider_combo = QComboBox()
        self.cfg_provider_combo.addItems(["openai_compatible", "ollama", "custom"])
        f_lay.addRow("提供商：", self.cfg_provider_combo)

        self.cfg_model_name = QLineEdit()
        self.cfg_model_name.setFixedHeight(34)
        f_lay.addRow("模型 ID：", self.cfg_model_name)

        self.cfg_api_url = QLineEdit()
        self.cfg_api_url.setFixedHeight(34)
        f_lay.addRow("API Base URL：", self.cfg_api_url)

        self.cfg_api_key = QLineEdit()
        self.cfg_api_key.setEchoMode(QLineEdit.Password)
        self.cfg_api_key.setFixedHeight(34)
        f_lay.addRow("API Key：", self.cfg_api_key)

        lay.addWidget(self.form_card)

        act_row = QHBoxLayout(); act_row.setSpacing(10)
        self.test_btn = QPushButton("🔍 测试连接")
        self.test_btn.setFixedHeight(34)
        self.test_btn.clicked.connect(self._test_api_connection)
        act_row.addWidget(self.test_btn)

        self.test_result_lbl = QLabel("")
        self.test_result_lbl.setStyleSheet("font-size:11.5px;font-family:'Microsoft YaHei UI';")
        act_row.addWidget(self.test_result_lbl, 1)

        self.save_curr_btn = QPushButton("💾 保存为当前模型")
        self.save_curr_btn.setFixedHeight(34)
        self.save_curr_btn.clicked.connect(self._save_settings)
        act_row.addWidget(self.save_curr_btn)
        lay.addLayout(act_row)
        lay.addStretch()

        self._load_active_model_into_form()
        return page

    def _refresh_model_cards(self):
        for i in reversed(range(self._model_list_vlay.count())):
            item = self._model_list_vlay.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        models = self.config.get("models_list", [])
        active_id = self.config.get("active_model_id", "")
        d = self._is_dark

        for m in models:
            mid = m.get("id", "")
            name = m.get("name", "未命名")
            provider = m.get("provider", "")
            model_name = m.get("model_name", "")
            url = m.get("api_base_url", "")
            is_active = (mid == active_id)

            card = QFrame()
            bg = "#181818" if d else "#ffffff"
            border = "#2e2e2e" if d else "#e2e8f0"
            active_border = "#6366f1" if d else "#6366f1"
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg};
                    border: 1px solid {active_border if is_active else border};
                    border-radius: 10px;
                }}
            """)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(14, 10, 14, 10)
            c_lay.setSpacing(10)

            icon = QLabel("⚡" if provider == "ollama" else "🌐")
            icon.setFont(QFont("Segoe UI Emoji", 14))
            icon.setStyleSheet("background: transparent;")
            c_lay.addWidget(icon)

            info = QVBoxLayout(); info.setSpacing(2)
            n_lbl = QLabel(name)
            name_color = "#818cf8" if is_active and d else ("#4f46e5" if is_active else ("#f4f4f5" if d else "#0f172a"))
            n_lbl.setStyleSheet(f"font-size:12.5px;font-weight:bold;color:{name_color};font-family:'Microsoft YaHei UI';background:transparent;")
            info.addWidget(n_lbl)

            d_lbl = QLabel(f"[{provider}] {model_name} · {url[:50]}")
            d_lbl.setStyleSheet(f"color:{'#a1a1aa' if d else '#64748b'};font-size:11px;font-family:'Microsoft YaHei UI';background:transparent;")
            info.addWidget(d_lbl)
            c_lay.addLayout(info, 1)

            if is_active:
                curr_lbl = QLabel("✓ 使用中")
                curr_lbl.setStyleSheet(f"color:{'#34d399' if d else '#10b981'};font-weight:bold;font-size:11.5px;background:transparent;")
                c_lay.addWidget(curr_lbl)
            else:
                use_btn = QPushButton("设为使用")
                use_btn.setFixedSize(72, 28)
                use_btn.setCursor(Qt.PointingHandCursor)
                use_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {'#27272a' if d else '#f1f5f9'};
                        color: {'#f4f4f5' if d else '#0f172a'};
                        border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                        border-radius: 6px; font-size: 11px; font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background: {'#3f3f46' if d else '#0f172a'};
                        color: #ffffff;
                    }}
                """)
                use_btn.clicked.connect(lambda c, mod=m: self._set_active_model_by_config(mod))
                c_lay.addWidget(use_btn)

            edit_btn = QPushButton("✎ 编辑")
            edit_btn.setFixedSize(58, 28)
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#27272a' if d else '#f1f5f9'};
                    color: {'#a1a1aa' if d else '#64748b'};
                    border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                    border-radius: 6px; font-size: 11px;
                }}
                QPushButton:hover {{
                    background: {'#3f3f46' if d else '#e2e8f0'};
                    color: {'#ffffff' if d else '#0f172a'};
                }}
            """)
            edit_btn.clicked.connect(lambda c, mod=m: self._edit_model(mod))
            c_lay.addWidget(edit_btn)

            del_btn = QPushButton("🗑")
            del_btn.setFixedSize(32, 28)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#3f1d1d' if d else '#fef2f2'};
                    color: {'#f87171' if d else '#ef4444'};
                    border: 1px solid {'#5c2424' if d else '#fecaca'};
                    border-radius: 6px; font-size: 11px;
                }}
                QPushButton:hover {{
                    background: #ef4444; color: #ffffff; border: none;
                }}
            """)
            del_btn.clicked.connect(lambda c, mod=m: self._delete_model(mod))
            c_lay.addWidget(del_btn)

            self._model_list_vlay.insertWidget(self._model_list_vlay.count() - 1, card)

    def _add_new_model(self):
        dlg = AddModelDialog(parent=self, is_dark=self._is_dark)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_result()
            if data:
                models = self.config.setdefault("models_list", [])
                models.append(data)
                if self.save_config_fn:
                    self.save_config_fn(self.config)
                self._refresh_model_cards()
                self._show_status(f"✅ 已添加模型：{data['name']}")

    def _edit_model(self, model: dict):
        dlg = AddModelDialog(parent=self, is_dark=self._is_dark, model_data=model)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_result()
            if data:
                models = self.config.get("models_list", [])
                for i, m in enumerate(models):
                    if m.get("id") == data.get("id"):
                        models[i] = data
                        break
                if self.save_config_fn:
                    self.save_config_fn(self.config)
                self._refresh_model_cards()
                self._load_active_model_into_form()
                self._show_status(f"✅ 模型已更新：{data['name']}")

    def _delete_model(self, model: dict):
        mid = model.get("id", "")
        name = model.get("name", "")
        if mid == self.config.get("active_model_id", ""):
            QMessageBox.warning(self, "无法删除", "当前正在使用的模型无法删除，请先切换到其他模型。")
            return
        reply = QMessageBox.question(self, "删除模型", f"确认删除模型「{name}」？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            models = self.config.get("models_list", [])
            self.config["models_list"] = [m for m in models if m.get("id") != mid]
            if self.save_config_fn:
                self.save_config_fn(self.config)
            self._refresh_model_cards()
            self._show_status(f"已删除模型：{name}")

    def _set_active_model_by_config(self, model: dict):
        mid = model.get("id", "")
        self.config["active_model_id"] = mid
        self.config["active_model_name"] = model.get("name", "")
        prov = model.get("provider", "custom")
        self.config.setdefault("ai", {})["provider"] = prov
        if prov == "ollama":
            self.config["ai"].setdefault("ollama", {})["chat_model"] = model.get("model_name", "")
            self.config["ai"]["ollama"]["api_base"] = model.get("api_base_url", "")
            self.config["ai"]["ollama"]["base_url"] = model.get("api_base_url", "")
        else:
            self.config["ai"].setdefault("custom", {})["chat_model"] = model.get("model_name", "")
            self.config["ai"]["custom"]["api_base"] = model.get("api_base_url", "")
            self.config["ai"]["custom"]["base_url"] = model.get("api_base_url", "")
            self.config["ai"]["custom"]["api_key"] = model.get("api_key", "")

        if self.save_config_fn:
            self.save_config_fn(self.config)
        if self.ai_engine:
            try:
                if hasattr(self.ai_engine, "set_active_model"):
                    self.ai_engine.set_active_model(model)
                elif hasattr(self.ai_engine, "reload_config"):
                    self.ai_engine.reload_config(self.config)
            except Exception as e:
                print(f"[AIEngine Switch Error] {e}")

        self._refresh_model_cards()
        self._load_active_model_into_form()
        disp = self._get_active_model_display()
        if hasattr(self, 'model_pill'):
            self.model_pill.setText(f"🤖 {disp} ∨")
        if hasattr(self, 'hero_model_pill'):
            self.hero_model_pill.setText(f"🤖 {disp} ∨")
        self._show_status(f"✅ 已切换模型：{model.get('name','')}")

    def _load_active_model_into_form(self):
        try:
            active_id = self.config.get("active_model_id", "")
            models = self.config.get("models_list", [])
            active = next((m for m in models if m.get("id") == active_id), None)
            if not active and models:
                active = models[0]
            if active:
                self.cfg_name_edit.setText(active.get("name", ""))
                idx = self.cfg_provider_combo.findText(active.get("provider", "custom"))
                if idx >= 0: self.cfg_provider_combo.setCurrentIndex(idx)
                self.cfg_model_name.setText(active.get("model_name", ""))
                self.cfg_api_url.setText(active.get("api_base_url", ""))
                self.cfg_api_key.setText(active.get("api_key", ""))
        except Exception:
            pass

    def _test_api_connection(self):
        url = self.cfg_api_url.text().strip()
        key = self.cfg_api_key.text().strip()
        prov = self.cfg_provider_combo.currentText()
        target_model = self.cfg_model_name.text().strip()

        if not url:
            self.test_result_lbl.setText("⚠️ 请输入 API URL")
            self.test_result_lbl.setStyleSheet("color:#f59e0b;font-size:11.5px;font-weight:bold;")
            return
        if not target_model:
            self.test_result_lbl.setText("⚠️ 请输入模型 ID")
            self.test_result_lbl.setStyleSheet("color:#f59e0b;font-size:11.5px;font-weight:bold;")
            return

        self.test_btn.setEnabled(False)
        self.test_btn.setText("⏳ 校验中...")
        self.test_result_lbl.setText("正在真实探测模型是否已下载/就绪...")
        self.test_result_lbl.setStyleSheet(f"color:{'#a1a1aa' if self._is_dark else '#64748b'};font-size:11.5px;")

        def _do():
            import time
            start_t = time.time()
            try:
                try:
                    import httpx
                except ImportError:
                    self.test_done_signal.emit(False, "❌ 缺少 httpx 库，请安装 httpx 后重试")
                    return

                headers = {"Content-Type": "application/json"}
                if key:
                    headers["Authorization"] = f"Bearer {key}"

                if prov == "ollama":
                    # 针对 Ollama 进行真正的本地已安装模型列表校验
                    tags_url = url.rstrip("/")
                    if not tags_url.endswith("/api/tags"):
                        tags_url += "/api/tags"

                    with httpx.Client(timeout=4.5, follow_redirects=True) as client:
                        resp = client.get(tags_url)

                    elapsed = int((time.time() - start_t) * 1000)
                    if resp.status_code in [200, 201]:
                        try:
                            data = resp.json()
                            installed_models = [m.get("name", "").lower() for m in data.get("models", [])]
                            target_clean = target_model.lower()
                            
                            match_found = any(
                                target_clean == m or target_clean + ":latest" == m or m.startswith(target_clean + ":") or target_clean == m.split(":")[0]
                                for m in installed_models
                            )
                            if match_found:
                                self.test_done_signal.emit(True, f"✅ 本地模型已就绪 (已安装 {target_model} · {elapsed}ms)")
                            else:
                                installed_str = ", ".join(installed_models[:4]) or "无"
                                self.test_done_signal.emit(False, f"❌ 本地未安装该模型 (已安装: {installed_str}，请先执行: ollama pull {target_model})")
                        except Exception:
                            self.test_done_signal.emit(True, f"✅ Ollama 服务已连通 (HTTP 200 · {elapsed}ms)")
                    else:
                        self.test_done_signal.emit(False, f"❌ Ollama 服务异常 (HTTP {resp.status_code})")

                else:
                    # 针对 OpenAI Compatible / Custom 进行真实模型可用性探测
                    base_url = url.rstrip("/")
                    chat_url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
                    payload = {
                        "model": target_model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 1
                    }

                    with httpx.Client(timeout=5.5, follow_redirects=True) as client:
                        resp = client.post(chat_url, headers=headers, json=payload)

                    elapsed = int((time.time() - start_t) * 1000)
                    if resp.status_code in [200, 201]:
                        self.test_done_signal.emit(True, f"✅ 模型已就绪可用 (HTTP 200 · {elapsed}ms)")
                    elif resp.status_code in [401, 403]:
                        self.test_done_signal.emit(False, f"❌ 认证失败 (HTTP {resp.status_code}, 请核对 API Key)")
                    elif resp.status_code in [404, 400]:
                        err_txt = resp.text[:60]
                        self.test_done_signal.emit(False, f"❌ 模型不存在或不可用 (HTTP {resp.status_code}: {err_txt})")
                    else:
                        self.test_done_signal.emit(True, f"✅ 服务响应 (HTTP {resp.status_code} · {elapsed}ms)")

            except Exception as e:
                err_str = str(e)
                if "ConnectTimeout" in type(e).__name__ or "timeout" in err_str.lower():
                    self.test_done_signal.emit(False, "❌ 连接超时 (请检查 API Base URL 或网络连接)")
                elif "ConnectError" in type(e).__name__ or "refused" in err_str.lower():
                    self.test_done_signal.emit(False, "❌ 无法连接服务器 (端口未开启或本地 Ollama 未启动)")
                else:
                    self.test_done_signal.emit(False, f"❌ 测试失败: {err_str[:50]}")

        threading.Thread(target=_do, daemon=True).start()

    def _on_test_result(self, ok: bool, msg: str):
        self.test_btn.setEnabled(True)
        self.test_btn.setText("🔍 测试连接")
        self.test_result_lbl.setText(msg)
        self.test_result_lbl.setStyleSheet(
            f"color:{'#10b981' if ok else '#ef4444'};font-size:11.5px;font-weight:bold;font-family:'Microsoft YaHei UI';"
        )

    def _save_settings(self):
        name   = self.cfg_name_edit.text().strip() or "自定义模型"
        prov   = self.cfg_provider_combo.currentText()
        model  = self.cfg_model_name.text().strip()
        url    = self.cfg_api_url.text().strip()
        key    = self.cfg_api_key.text().strip()

        active_id = self.config.get("active_model_id", "")
        models = self.config.get("models_list", [])
        found = False
        for m in models:
            if m.get("id") == active_id:
                m.update({"name": name, "provider": prov, "model_name": model,
                           "api_base_url": url, "api_key": key})
                found = True
                break
        if not found:
            import uuid
            new_m = {
                "id": f"model_{uuid.uuid4().hex[:8]}",
                "name": name, "provider": prov, "model_name": model,
                "api_base_url": url, "api_key": key,
                "system_prompt": "你是一个全能的桌面 AI 智能体助理。"
            }
            models.append(new_m)
            self.config["active_model_id"] = new_m["id"]

        self.config.setdefault("ai", {})["provider"] = prov
        if prov == "ollama":
            self.config["ai"].setdefault("ollama", {})["chat_model"] = model
            self.config["ai"]["ollama"]["base_url"] = url
        else:
            self.config["ai"].setdefault("custom", {})["chat_model"] = model
            self.config["ai"]["custom"]["api_base"] = url
            self.config["ai"]["custom"]["api_key"] = key

        if self.save_config_fn:
            self.save_config_fn(self.config)
        if self.ai_engine:
            try:
                if hasattr(self.ai_engine, "reload_config"):
                    self.ai_engine.reload_config(self.config)
            except Exception:
                pass

        disp = self._get_active_model_display()
        self.model_pill.setText(f"🤖 {disp} ∨")
        self.hero_model_pill.setText(f"🤖 {disp} ∨")
        self._refresh_model_cards()
        self._show_status("✨ 模型配置已保存！")

    def _open_model_selector_popup(self):
        models = self.config.get("models_list", [])
        active_id = self.config.get("active_model_id", "")
        popup = ModelSelectorPopupCard(
            models=models,
            active_model_id=active_id,
            is_dark=self._is_dark,
            parent=self
        )
        popup.model_selected.connect(self._set_active_model_by_config)
        sender = self.sender() or self.model_pill
        if sender and isinstance(sender, QWidget):
            pos = sender.mapToGlobal(QPoint(0, -popup.sizeHint().height() - 10))
        else:
            pos = self.model_pill.mapToGlobal(QPoint(0, -popup.sizeHint().height() - 10))
        popup.move(pos)
        popup.show()

    # ══════════════════════════════════════════════════════════
    #  工作空间管理 (联动侧边栏与弹窗)
    # ══════════════════════════════════════════════════════════
    def _open_workspace_selector_popup(self):
        popup = WorkspaceSelectorPopup(
            workspaces=self.workspaces,
            current_name=self.current_workspace_name,
            is_dark=self._is_dark,
            parent=self
        )
        popup.workspace_selected.connect(self._on_workspace_selected)
        popup.create_new_requested.connect(self._create_new_workspace_dialog)
        popup.open_folder_requested.connect(self._choose_custom_folder_dialog)

        # 弹窗定位
        sender = self.sender()
        if sender and isinstance(sender, QWidget):
            pos = sender.mapToGlobal(QPoint(0, -popup.sizeHint().height() - 10))
        else:
            pos = self.ws_pill.mapToGlobal(QPoint(0, -popup.sizeHint().height() - 10))
        popup.move(pos)
        popup.show()

    def _on_workspace_selected(self, ws: dict):
        self.current_workspace_name = ws.get("name", "工作空间")
        self.current_workspace_path = ws.get("path", str(ROOT_DIR))
        self.config["current_workspace_name"] = self.current_workspace_name
        self.config["workspace_dir"] = self.current_workspace_path
        if self.save_config_fn:
            self.save_config_fn(self.config)

        self.ws_pill.setText(f"📁 {self.current_workspace_name} ∨")
        self.hero_ws_pill.setText(f"📁 {self.current_workspace_name} ∨")
        self._refresh_sidebar_workspaces()
        self._show_status(f"已切换工作空间：{self.current_workspace_name}")

    def _create_new_workspace_dialog(self):
        name, ok = QInputDialog.getText(self, "新建工作空间", "工作空间名称：")
        if ok and name.strip():
            clean_name = name.strip()
            target_path = ROOT_DIR / clean_name
            target_path.mkdir(parents=True, exist_ok=True)
            new_ws = {"name": clean_name, "path": str(target_path)}
            self.workspaces.append(new_ws)
            self.config["workspaces"] = self.workspaces
            self._on_workspace_selected(new_ws)

    def _choose_custom_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "选择本地项目工作空间", str(ROOT_DIR))
        if folder:
            p = Path(folder)
            new_ws = {"name": p.name, "path": folder}
            if not any(w["path"] == folder for w in self.workspaces):
                self.workspaces.append(new_ws)
                self.config["workspaces"] = self.workspaces
            self._on_workspace_selected(new_ws)

    def _refresh_sidebar_workspaces(self):
        self.ws_list.clear()
        self.ws_head.setText(f"空间 ({len(self.workspaces)}) ∨")
        for ws in self.workspaces:
            name = ws.get("name", "")
            is_active = (name == self.current_workspace_name)
            item = QListWidgetItem(f"📁  {name}")
            item.setData(Qt.UserRole, ws)
            if is_active:
                item.setForeground(QColor("#6366f1"))
                self.ws_list.setCurrentItem(item)
            self.ws_list.addItem(item)

    def _on_ws_list_item_clicked(self, item):
        ws = item.data(Qt.UserRole)
        if ws:
            self._on_workspace_selected(ws)

    def _toggle_sidebar_collapse(self):
        is_visible = self.sidebar.isVisible()
        self.sidebar.setVisible(not is_visible)
        if hasattr(self, 'expand_sb_btn'):
            self.expand_sb_btn.setVisible(is_visible)

    def _open_global_task_search_popup(self):
        sessions = self.memory.get_all_sessions() if self.memory else []
        popup = GlobalTaskSearchPopup(
            sessions=sessions,
            current_ws=self.current_workspace_name,
            is_dark=self._is_dark,
            parent=self
        )
        popup.session_selected.connect(self._load_session)
        sender = self.sender() or self.btn_search_tasks
        pos = sender.mapToGlobal(QPoint(0, 30))
        popup.move(pos)
        popup.show()

    def _open_task_filter_popup(self):
        popup = TaskFilterPopup(
            current_status=getattr(self, '_filter_status', '全部状态'),
            current_time=getattr(self, '_filter_time', '全部时间'),
            is_dark=self._is_dark,
            parent=self
        )
        popup.filter_applied.connect(self._on_task_filter_applied)
        sender = self.sender() or self.btn_filter_tasks
        pos = sender.mapToGlobal(QPoint(0, 30))
        popup.move(pos)
        popup.show()

    def _on_task_filter_applied(self, status: str, time_range: str):
        self._filter_status = status
        self._filter_time = time_range
        self._refresh_history_list()
        self._show_status(f"已应用筛选：{status} · {time_range}")

    # ══════════════════════════════════════════════════════════
    #  安全权限
    # ══════════════════════════════════════════════════════════
    def _open_permission_popup(self):
        popup = PermissionPopupCard(current_perm=self.current_permission, is_dark=self._is_dark, parent=self)
        popup.permission_changed.connect(self._set_permission_mode)
        sender = self.sender() or self.perm_pill
        pos = sender.mapToGlobal(QPoint(0, -popup.sizeHint().height() - 10))
        popup.move(pos); popup.show()

    def _set_permission_mode(self, mode: str):
        self.current_permission = mode
        self.config["permission_mode"] = mode
        if self.save_config_fn: self.save_config_fn(self.config)
        try:
            from core.security_guard import SecurityGuard
            SecurityGuard.get_instance().set_mode(mode)
        except Exception: pass
        txt = "🛡️ 默认权限 ∨" if mode == "standard" else "🚀 完全访问 ∨"
        self.perm_pill.setText(txt)
        self.hero_perm_pill.setText(txt)

    # ══════════════════════════════════════════════════════════
    #  会话管理与双态切换
    # ══════════════════════════════════════════════════════════
    def _enter_hero_mode(self):
        self.chat_page_stack.setCurrentIndex(0)
        self.hero_input_edit.setFocus()

    def _enter_active_chat_mode(self):
        self.chat_page_stack.setCurrentIndex(1)
        self.input_edit.setFocus()

    def _create_new_session_action(self):
        self._stream_id += 1
        self._is_generating = False
        if hasattr(self, 'send_btn'):
            self.send_btn.setEnabled(True)
            self.send_btn.setText("▲")
        if hasattr(self, 'hero_send_btn'):
            self.hero_send_btn.setEnabled(True)
            self.hero_send_btn.setText("▲")

        ws_name = self.current_workspace_name or (self.workspaces[0].get("name", "") if self.workspaces else "")
        txt = f"📁 {ws_name} ∨" if ws_name else "📁 选择工作空间 ∨"
        if hasattr(self, 'ws_pill'):
            self.ws_pill.setText(txt)
        if hasattr(self, 'hero_ws_pill'):
            self.hero_ws_pill.setText(txt)

        if self.memory:
            sid = self.memory.create_session("新任务会话", workspace_name=ws_name)
            self._current_session_id = sid
            self._clear_chat_blocks()
            self._refresh_history_list()
            self._refresh_sidebar_workspaces()
            self.chat_title_lbl.setText("新任务会话")
            self._enter_hero_mode()
        else:
            self._clear_chat_blocks()
            self._enter_hero_mode()
        self._switch_nav(0)

    def _load_session(self, session_id: int):
        self._stream_id += 1
        self._is_generating = False
        if hasattr(self, 'send_btn'):
            self.send_btn.setEnabled(True)
            self.send_btn.setText("▲")
        self._current_session_id = session_id
        self._clear_chat_blocks()

        # 1. 强制切回 0 号主聊天导航
        self._switch_nav(0)
        
        # 2. 自动同步会话所属的工作空间
        if self.memory:
            all_s = self.memory.get_all_sessions()
            cur_s = next((s for s in all_s if s.get("id") == session_id), None)
            if cur_s and cur_s.get("workspace_name"):
                ws_name = cur_s.get("workspace_name")
                self.current_workspace_name = ws_name
                ws_obj = next((w for w in self.workspaces if w.get("name") == ws_name), None)
                if ws_obj:
                    self.current_workspace_path = ws_obj.get("path", "")
                txt = f"📁 {ws_name} ∨"
                if hasattr(self, 'ws_pill'): self.ws_pill.setText(txt)
                if hasattr(self, 'hero_ws_pill'): self.hero_ws_pill.setText(txt)

        self._refresh_history_list()
        self._refresh_sidebar_workspaces()

        if not self.memory:
            self._enter_hero_mode()
            return

        try:
            messages = self.memory.get_session_messages(session_id)
            sessions = self.memory.get_all_sessions()
            curr = next((s for s in sessions if s["id"] == session_id), None)
            title = curr.get("title", "对话任务") if curr else "对话任务"
            self.chat_title_lbl.setText(title)

            # 3. 无论是否有历史消息，直接进入对话态对话流界面
            self._enter_active_chat_mode()

            if messages:
                history = []
                for m in messages:
                    sender = "user" if m.get("role") in ["user", "human"] else "ai"
                    raw_ts = str(m.get("timestamp", ""))
                    fmt_ts = raw_ts[11:16] if len(raw_ts) >= 16 else datetime.now().strftime("%H:%M")
                    self._add_message_block(sender, m.get("content", ""), timestamp=fmt_ts)
                    history.append({"role": m.get("role"), "content": m.get("content")})
                if self.ai_engine:
                    self.ai_engine.conversation_history = history
                    if hasattr(self.ai_engine, 'session_histories'):
                        self.ai_engine.session_histories[str(session_id)] = list(history)
            elif title and title != "新任务会话":
                # 针对早期未持久化子消息的老存量会话，自动恢复初始问答与就绪状态
                self._add_message_block("user", title)
                self._add_message_block("ai", f"已载入任务「{title}」的历史上下文。您可以直接在下方输入框继续向我提问或执行操作。")
                if self.memory:
                    self.memory.add_message(session_id, "user", title)
                    self.memory.add_message(session_id, "assistant", f"已载入任务「{title}」的历史上下文。您可以直接在下方输入框继续向我提问或执行操作。")
                if self.ai_engine:
                    fallback_hist = [
                        {"role": "user", "content": title},
                        {"role": "assistant", "content": f"已载入任务「{title}」的历史上下文。"}
                    ]
                    self.ai_engine.conversation_history = fallback_hist
                    if hasattr(self.ai_engine, 'session_histories'):
                        self.ai_engine.session_histories[str(session_id)] = fallback_hist
        except Exception as e:
            print(f"[SessionLoad Error] {e}")
            self._enter_active_chat_mode()

        QTimer.singleShot(60, self._scroll_to_bottom)

    def _on_session_item_clicked(self, item):
        if not item: return
        sid = item.data(Qt.UserRole)
        if sid:
            self._load_session(sid)
            self._switch_nav(0)

    def _refresh_history_list(self):
        self.session_list.clear()
        if not self.memory: return
        try:
            all_sessions = self.memory.get_all_sessions()
            pinned_ids = set(self.config.get("pinned_sessions", []))
            archived_ids = set(self.config.get("archived_sessions", []))

            # 排除已归档与根据筛选条件过滤
            active_sessions = [s for s in all_sessions if s["id"] not in archived_ids]

            t_filter = getattr(self, '_filter_time', '全部时间')
            if t_filter != "全部时间":
                now = datetime.now()
                filtered = []
                for s in active_sessions:
                    try:
                        s_dt = datetime.strptime(s.get("created_at", "")[:19], "%Y-%m-%d %H:%M:%S")
                        diff = (now - s_dt).total_seconds()
                        if t_filter == "今天" and diff <= 86400:
                            filtered.append(s)
                        elif t_filter == "最近 7 天" and diff <= 7 * 86400:
                            filtered.append(s)
                        elif t_filter == "最近 30 天" and diff <= 30 * 86400:
                            filtered.append(s)
                    except Exception:
                        filtered.append(s)
                active_sessions = filtered

            pinned_list = [s for s in active_sessions if s["id"] in pinned_ids]
            normal_list = [s for s in active_sessions if s["id"] not in pinned_ids]

            total = len(active_sessions)
            self.task_head.setText(f"任务 ({total}) ∨")

            limit = 5
            show_all = getattr(self, '_show_all_sessions', False)
            display_normal = normal_list if show_all else normal_list[:limit]
            self._has_more_sessions = (len(normal_list) > limit)

            # 1. 渲染置顶会话项
            if pinned_list:
                pin_head_item = QListWidgetItem("✦ 置顶任务")
                pin_head_item.setSizeHint(QSize(200, 24))
                pin_head_item.setFlags(Qt.NoItemFlags)
                pin_head_item.setForeground(QColor("#818cf8" if self._is_dark else "#6366f1"))
                font = QFont("Microsoft YaHei UI", 9, QFont.Bold)
                pin_head_item.setFont(font)
                self.session_list.addItem(pin_head_item)

                for s in pinned_list:
                    self._add_session_list_item(s, is_pinned=True)

                if display_normal:
                    div_item = QListWidgetItem("─── 常规任务 ───")
                    div_item.setSizeHint(QSize(200, 24))
                    div_item.setFlags(Qt.NoItemFlags)
                    div_item.setForeground(QColor("#71717a" if self._is_dark else "#94a3b8"))
                    div_font = QFont("Microsoft YaHei UI", 8, QFont.Bold)
                    div_item.setFont(div_font)
                    div_item.setTextAlignment(Qt.AlignCenter)
                    self.session_list.addItem(div_item)

            # 2. 渲染常规会话项
            for s in display_normal:
                self._add_session_list_item(s, is_pinned=False)

            d = self._is_dark
            see_more_style = f"""
                QPushButton {{
                    background-color: {'#27272a' if d else '#f1f5f9'};
                    color: {'#a1a1aa' if d else '#64748b'};
                    border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11.5px;
                    font-family: 'Microsoft YaHei UI';
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {'#3f3f46' if d else '#e2e8f0'};
                    color: {'#ffffff' if d else '#0f172a'};
                }}
            """

            # 隐藏外部独立悬浮按钮，彻底消除重叠遮挡
            if hasattr(self, 'see_more_btn'):
                self.see_more_btn.hide()

            # 3. 将「查看更多 / 收起」作为最后一项嵌入列表中，流式自然排版
            if self._has_more_sessions:
                more_item = QListWidgetItem()
                more_item.setSizeHint(QSize(200, 34))
                more_item.setFlags(Qt.NoItemFlags)

                remain_cnt = len(normal_list) - limit
                btn_text = "收起 ∧" if show_all else f"查看更多 ({remain_cnt}) ∨"
                more_btn = QPushButton(btn_text)
                more_btn.setCursor(Qt.PointingHandCursor)
                more_btn.setStyleSheet(see_more_style)
                more_btn.clicked.connect(self._toggle_show_all_sessions)

                self.session_list.addItem(more_item)
                self.session_list.setItemWidget(more_item, more_btn)

            # 双独立滑动视口模式：session_list 自然弹性拉伸并支持独立滚动
            pass
        except Exception as e:
            print(f"[SessionList Error] {e}")

    def _add_session_list_item(self, s: dict, is_pinned: bool):
        sid = s.get("id")
        title = str(s.get("title", "未命名")).strip()
        rel_t = format_relative_time(s.get("created_at", ""))
        is_active = (sid == self._current_session_id)

        item = QListWidgetItem()
        item.setSizeHint(QSize(200, 36))
        item.setData(Qt.UserRole, sid)
        item.setData(Qt.UserRole + 1, title)

        widget = SidebarTaskItemWidget(
            session_id=sid,
            title=title if len(title) <= 12 else title[:11] + "...",
            time_str=rel_t,
            is_pinned=is_pinned,
            is_active=is_active,
            is_dark=self._is_dark,
            parent=self.session_list
        )

        widget.clicked.connect(self._load_session)
        widget.rename_requested.connect(self._rename_session)
        widget.delete_requested.connect(self._delete_session_by_id)
        widget.export_requested.connect(self._export_session_markdown)
        widget.pin_toggled.connect(self._toggle_pin_session)
        widget.archive_requested.connect(self._archive_session)
        widget.save_to_ws_requested.connect(self._save_session_to_workspace)

        self.session_list.addItem(item)
        self.session_list.setItemWidget(item, widget)

    def _toggle_pin_session(self, sid: int, pin: bool):
        pinned = set(self.config.get("pinned_sessions", []))
        if pin:
            pinned.add(sid)
            self._show_status("已置顶任务")
        else:
            pinned.discard(sid)
            self._show_status("已取消置顶")
        self.config["pinned_sessions"] = list(pinned)
        if self.save_config_fn:
            self.save_config_fn(self.config)
        self._refresh_history_list()

    def _archive_session(self, sid: int):
        archived = set(self.config.get("archived_sessions", []))
        archived.add(sid)
        self.config["archived_sessions"] = list(archived)
        if self.save_config_fn:
            self.save_config_fn(self.config)
        self._refresh_history_list()
        self._show_status("已归档会话")

    def _save_session_to_workspace(self, sid: int, title: str):
        if not self.memory: return
        messages = self.memory.get_session_messages(sid)
        if not messages:
            QMessageBox.information(self, "提示", "当前会话暂无消息。")
            return
        target_dir = Path(self.current_workspace_path)
        target_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c for c in title if c not in r'\/:*?"<>|').strip() or "任务会话"
        path = target_dir / f"{safe}.md"
        lines = [f"# {title}", f"> 工作空间：{self.current_workspace_name}", f"> 保存时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "---", ""]
        for m in messages:
            name = "👤 用户" if m["role"] == "user" else "🤖 NovaDesk AI"
            lines.append(f"### {name} (`{m['timestamp']}`)\n{m['content']}\n")
        try:
            path.write_text("\n".join(lines), encoding="utf-8")
            self._show_status(f"✅ 已保存至工作空间：{path.name}")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", str(e))

    def _toggle_session_list(self):
        self._session_collapsed = not self._session_collapsed
        self.session_list.setVisible(not self._session_collapsed)
        self.see_more_btn.setVisible(not self._session_collapsed and getattr(self, '_has_more_sessions', False))
        self.task_head.setText(
            self.task_head.text().replace("∨","∧") if self._session_collapsed
            else self.task_head.text().replace("∧","∨")
        )

    def _toggle_show_all_sessions(self):
        self._show_all_sessions = not getattr(self, '_show_all_sessions', False)
        self._refresh_history_list()

    def _show_session_context_menu(self, pos):
        item = self.session_list.itemAt(pos)
        if not item: return
        sid   = item.data(Qt.UserRole)
        title = item.data(Qt.UserRole + 1) or "未命名"
        menu = QMenu(self)
        d = self._is_dark
        menu.setStyleSheet(f"""
            QMenu{{background:{'#1e293b' if d else '#fff'};color:{'#e2e8f0' if d else '#0f172a'};
                  border:1px solid {'#334155' if d else '#e2e8f0'};border-radius:10px;padding:4px;
                  font-family:'Microsoft YaHei UI';font-size:12px;}}
            QMenu::item{{padding:7px 22px;border-radius:6px;}}
            QMenu::item:selected{{background:{'#334155' if d else '#f1f5f9'};}}
        """)
        act_open   = menu.addAction("💬 载入对话")
        act_rename = menu.addAction("✏️ 重命名")
        act_export = menu.addAction("📄 导出 Markdown")
        menu.addSeparator()
        act_delete = menu.addAction("🗑️ 删除")
        act = menu.exec_(self.session_list.mapToGlobal(pos))
        if act == act_open:
            self._load_session(sid); self._switch_nav(0)
        elif act == act_rename:
            self._rename_session(sid, title)
        elif act == act_export:
            self._export_session_markdown(sid, title)
        elif act == act_delete:
            self._delete_session_by_id(sid)

    def _rename_session(self, sid: int, old_title: str):
        new_title, ok = QInputDialog.getText(self, "重命名会话", "新名称：", text=old_title)
        if ok and new_title.strip():
            if self.memory: self.memory.update_session_title(sid, new_title.strip())
            self._refresh_history_list()
            if self._current_session_id == sid:
                self.chat_title_lbl.setText(new_title.strip())

    def _export_session_markdown(self, sid: int, title: str):
        if not self.memory: return
        messages = self.memory.get_session_messages(sid)
        if not messages:
            QMessageBox.information(self, "提示", "当前会话暂无消息。"); return
        desktop = Path.home() / "Desktop"
        safe = "".join(c for c in title if c not in r'\/:*?"<>|').strip() or "对话记录"
        path = desktop / f"NovaDesk_{safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        lines = [f"# 💬 {title}", f"> 导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "---", ""]
        for m in messages:
            name = "👤 我" if m["role"] == "user" else "🤖 NovaDesk AI"
            lines.append(f"### {name} (`{m['timestamp']}`)")
            lines.append(f"{m['content']}\n")
        try:
            path.write_text("\n".join(lines), encoding="utf-8")
            os.startfile(str(path))
            QMessageBox.information(self, "导出成功", f"已导出至桌面：{path.name}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))

    def _delete_session_by_id(self, sid: int):
        if not self.memory: return
        self.memory.delete_session(sid)
        self._refresh_history_list()
        self._refresh_sidebar_workspaces()
        sessions = self.memory.get_all_sessions()
        if sessions: self._load_session(sessions[0]["id"])
        else: self._create_new_session_action()

    # ══════════════════════════════════════════════════════════
    #  工作空间树形联动与管理
    # ══════════════════════════════════════════════════════════
    def _toggle_workspace_area(self):
        self._ws_collapsed = not self._ws_collapsed
        self.ws_list.setVisible(not self._ws_collapsed)
        self.ws_head.setText(
            self.ws_head.text().replace("∨", "∧") if self._ws_collapsed
            else self.ws_head.text().replace("∧", "∨")
        )

    def _refresh_sidebar_workspaces(self):
        if not hasattr(self, 'ws_list'):
            return
        self.ws_list.clear()
        self.ws_head.setText(f"空间 ({len(self.workspaces)}) ∨")

        all_sessions = self.memory.get_all_sessions() if self.memory else []

        for ws in self.workspaces:
            ws_name = ws.get("name", "未命名空间")
            ws_path = ws.get("path", str(ROOT_DIR))
            is_active = (ws_name == self.current_workspace_name)
            is_collapsed = ws.get("collapsed", False)

            # 1. 渲染工作空间头部项
            header_item = QListWidgetItem()
            header_item.setSizeHint(QSize(200, 36))
            header_widget = SidebarWorkspaceHeaderWidget(
                name=ws_name,
                path=ws_path,
                is_active=is_active,
                is_collapsed=is_collapsed,
                is_dark=self._is_dark,
                parent=self.ws_list
            )
            header_widget.clicked.connect(self._on_ws_header_clicked)
            header_widget.add_task_clicked.connect(self._create_new_session_in_workspace)
            header_widget.open_folder_requested.connect(self._open_workspace_folder)
            header_widget.remove_requested.connect(self._remove_workspace)

            self.ws_list.addItem(header_item)
            self.ws_list.setItemWidget(header_item, header_widget)

            # 2. 如果展开，渲染下属任务列表
            if not is_collapsed:
                ws_sessions = [s for s in all_sessions if s.get("workspace_name") == ws_name]
                if not ws_sessions:
                    empty_item = QListWidgetItem("        暂无任务")
                    empty_item.setFlags(Qt.NoItemFlags)
                    empty_item.setForeground(QColor("#71717a" if self._is_dark else "#94a3b8"))
                    font = QFont("Microsoft YaHei UI", 8)
                    empty_item.setFont(font)
                    empty_item.setSizeHint(QSize(200, 26))
                    self.ws_list.addItem(empty_item)
                else:
                    for s in ws_sessions[:8]:
                        s_item = QListWidgetItem()
                        s_item.setSizeHint(QSize(200, 32))
                        sid = s.get("id")
                        title = str(s.get("title", "未命名")).strip()
                        rel_t = format_relative_time(s.get("created_at", ""))
                        is_curr = (sid == self._current_session_id)

                        task_widget = SidebarTaskItemWidget(
                            session_id=sid,
                            title=title if len(title) <= 10 else title[:9] + "...",
                            time_str=rel_t,
                            is_pinned=sid in set(self.config.get("pinned_sessions", [])),
                            is_active=is_curr,
                            is_dark=self._is_dark,
                            is_sub_item=True,
                            parent=self.ws_list
                        )
                        task_widget.clicked.connect(self._load_session)
                        task_widget.rename_requested.connect(self._rename_session)
                        task_widget.delete_requested.connect(self._delete_session_by_id)
                        task_widget.export_requested.connect(self._export_session_markdown)
                        task_widget.pin_toggled.connect(self._toggle_pin_session)
                        task_widget.archive_requested.connect(self._archive_session)

                        self.ws_list.addItem(s_item)
                        self.ws_list.setItemWidget(s_item, task_widget)

        # 双独立滑动视口模式：ws_list 自然弹性拉伸并支持独立滚动
        pass

    def _on_ws_header_clicked(self, ws_name: str, ws_path: str):
        for ws in self.workspaces:
            if ws.get("name") == ws_name:
                ws["collapsed"] = not ws.get("collapsed", False)
                break
        self._switch_to_workspace(ws_name, ws_path)

    def _switch_to_workspace(self, ws_name: str, ws_path: str):
        self.current_workspace_name = ws_name
        self.current_workspace_path = ws_path
        self.config["current_workspace_name"] = ws_name
        self.config["workspace_dir"] = ws_path
        if self.save_config_fn:
            self.save_config_fn(self.config)

        try:
            from core.security_guard import SecurityGuard
            SecurityGuard.get_instance().set_workspace_root(ws_path)
        except Exception: pass

        txt = f"📁 {ws_name} ∨"
        if hasattr(self, 'ws_pill'):
            self.ws_pill.setText(txt)
        if hasattr(self, 'hero_ws_pill'):
            self.hero_ws_pill.setText(txt)

        self._refresh_sidebar_workspaces()
        self._refresh_history_list()
        self._show_status(f"📁 已切换至工作空间：{ws_name}")

        # 立即切换至聊天页面并加载该空间最新任务或进入 Hero 卡片
        self._switch_nav(0)
        ws_sessions = [s for s in (self.memory.get_all_sessions() if self.memory else []) if s.get("workspace_name") == ws_name]
        if ws_sessions:
            self._load_session(ws_sessions[0]["id"])
        else:
            self._clear_chat_blocks()
            self._enter_hero_mode()

    def _create_new_session_in_workspace(self, ws_name: str, ws_path: str):
        self._stream_id += 1
        self._is_generating = False
        if hasattr(self, 'send_btn'):
            self.send_btn.setEnabled(True)
            self.send_btn.setText("▲")
        if hasattr(self, 'hero_send_btn'):
            self.hero_send_btn.setEnabled(True)
            self.hero_send_btn.setText("▲")

        self._switch_to_workspace(ws_name, ws_path)
        if self.memory:
            sid = self.memory.create_session("新任务会话", workspace_name=ws_name)
            self._current_session_id = sid
            self._clear_chat_blocks()
            self._refresh_history_list()
            self._refresh_sidebar_workspaces()
            self.chat_title_lbl.setText("新任务会话")
            self._enter_hero_mode()

    def _open_workspace_folder(self, ws_path: str):
        try:
            p = Path(ws_path)
            p.mkdir(parents=True, exist_ok=True)
            os.startfile(str(p))
            self._show_status(f"📁 已打开工作空间目录：{p.name}")
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法打开文件夹：{e}")

    def _remove_workspace(self, ws_name: str):
        if len(self.workspaces) <= 1:
            QMessageBox.warning(self, "提示", "至少需保留一个工作空间。")
            return
        reply = QMessageBox.question(self, "移除工作空间", f"确认从列表中移除工作空间「{ws_name}」？\n（实际文件夹不会被删除）", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.workspaces = [w for w in self.workspaces if w.get("name") != ws_name]
            self.config["workspaces"] = self.workspaces
            if self.current_workspace_name == ws_name:
                self.current_workspace_name = self.workspaces[0].get("name", "")
                self.current_workspace_path = self.workspaces[0].get("path", "")
            if self.save_config_fn:
                self.save_config_fn(self.config)
            self._refresh_sidebar_workspaces()
            self._show_status(f"已移除工作空间：{ws_name}")

    def _clear_chat_blocks(self):
        for b in getattr(self, "_message_blocks", []):
            try:
                self.chat_layout.removeWidget(b); b.deleteLater()
            except Exception: pass
        self._message_blocks = []
        self._current_ai_block = None

    def _init_or_load_latest_session(self):
        if not self.memory:
            self._enter_hero_mode()
            return
        sessions = self.memory.get_all_sessions()
        if sessions:
            self._load_session(sessions[0]["id"])
        else:
            self._create_new_session_action()

    # ══════════════════════════════════════════════════════════
    #  消息发送与本地文件引用
    # ══════════════════════════════════════════════════════════
    def _on_plus_attach_file_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择要引用或分析的本地文件",
            self.current_workspace_path or str(ROOT_DIR),
            "支持文件 (*.txt *.md *.py *.json *.csv *.docx *.pdf *.html *.js *.java *.cpp *.sql);;所有文件 (*.*)"
        )
        if not file_path:
            return

        p = Path(file_path)
        content_preview = ""
        try:
            if p.suffix.lower() in [".txt", ".md", ".py", ".json", ".csv", ".html", ".js", ".java", ".cpp", ".sql", ".sh", ".bat"]:
                content_preview = p.read_text(encoding="utf-8", errors="ignore")[:3000]
            elif p.suffix.lower() == ".docx":
                try:
                    import docx
                    doc = docx.Document(str(p))
                    content_preview = "\n".join([para.text for para in doc.paragraphs if para.text])[:3000]
                except Exception:
                    content_preview = f"[Word文档: {p.name}]"
            elif p.suffix.lower() == ".pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(str(p))
                    text_parts = [page.extract_text() or "" for page in reader.pages[:5]]
                    content_preview = "\n".join(text_parts)[:3000]
                except Exception:
                    content_preview = f"[PDF文档: {p.name}]"
            else:
                content_preview = f"[本地文件: {p.name}, 大小: {p.stat().st_size} 字节]"
        except Exception as e:
            content_preview = f"[读取文件失败: {e}]"

        insert_tag = f"📄 @引用文件 [{p.name}]:\n```\n{content_preview}\n```\n请帮我分析上述文件并回答："
        
        if self.chat_page_stack.currentIndex() == 0:
            cur = self.hero_input_edit.toPlainText().strip()
            self.hero_input_edit.setText((cur + "\n\n" if cur else "") + insert_tag)
            self.hero_input_edit.setFocus()
        else:
            cur = self.input_edit.toPlainText().strip()
            self.input_edit.setText((cur + "\n\n" if cur else "") + insert_tag)
            self.input_edit.setFocus()

        self._show_status(f"📎 已成功载入文件：{p.name}")

    def _send_hero_message(self):
        text = self.hero_input_edit.toPlainText().strip()
        if not text: return
        if self._is_generating:
            self._show_status("⚠️ AI 正在生成回答，请稍候...")
            return
        self.hero_input_edit.clear()
        self._enter_active_chat_mode()
        self._do_send(text)

    def _send_active_message(self):
        text = self.input_edit.toPlainText().strip()
        if not text: return
        if self._is_generating:
            self._show_status("⚠️ AI 正在生成回答，请稍候...")
            return
        self.input_edit.clear()
        self._do_send(text)

    def _do_send(self, text: str):
        if self._is_generating: return
        self._is_generating = True
        self.send_btn.setEnabled(False)
        self.send_btn.setText("⏳")

        if self.memory and self._current_session_id:
            msgs = self.memory.get_session_messages(self._current_session_id)
            if len(msgs) == 0:
                short = text[:18] + ("..." if len(text) > 18 else "")
                self.memory.update_session_title(self._current_session_id, short)
                self.chat_title_lbl.setText(short)
                self._refresh_history_list()
            # 实时持久化用户输入消息到 SQLite
            self.memory.add_message(self._current_session_id, "user", text)

        self._add_message_block("user", text)
        self._current_ai_block = self._add_message_block("ai", "⏳ 正在思考...")
        self._stream_id += 1
        active_id = self._stream_id
        threading.Thread(target=self._stream_worker, args=(active_id, text), daemon=True).start()

    def _stream_worker(self, active_id: int, user_msg: str):
        full = ""
        sid = self._current_session_id
        try:
            async def _run():
                nonlocal full
                async for chunk in self.ai_engine.chat_stream(user_msg, session_id=sid):
                    if active_id != self._stream_id: break
                    full += chunk
                    self.message_chunk_signal.emit(active_id, full)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_run())
            loop.close()
            if active_id == self._stream_id:
                self.message_done_signal.emit(active_id, full)
        except Exception as e:
            if active_id == self._stream_id:
                self.message_error_signal.emit(active_id, str(e))

    def _on_chunk(self, sid: int, text: str):
        if sid == self._stream_id and self._current_ai_block:
            self._current_ai_block.set_text(text)
            self._scroll_to_bottom()

    def _on_done(self, sid: int, text: str):
        if sid == self._stream_id:
            self._is_generating = False
            self.send_btn.setEnabled(True)
            self.send_btn.setText("▲")
            if self._current_ai_block:
                self._current_ai_block.set_text(text)
                self._scroll_to_bottom()
            # 实时持久化 AI 回复消息到 SQLite
            if self.memory and self._current_session_id and text:
                self.memory.add_message(self._current_session_id, "assistant", text)

    def _on_error(self, sid: int, err: str):
        if sid == self._stream_id:
            self._is_generating = False
            self.send_btn.setEnabled(True)
            self.send_btn.setText("▲")
            if self._current_ai_block:
                self._current_ai_block.set_text(f"⚠️ 请求失败: {err}")

    def _add_message_block(self, sender: str, text: str, timestamp: str = "") -> MessageBlock:
        block = MessageBlock(
            sender, text, timestamp=timestamp,
            model_name=self._get_active_model_display(),
            is_dark=self._is_dark
        )
        if sender == "ai":
            block.retry_requested.connect(self._on_retry_message)
        self._message_blocks.append(block)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, block)
        self._scroll_to_bottom()
        return block

    def _on_retry_message(self, ai_text: str):
        if self._is_generating: return
        # 查找对应上一条用户消息
        last_user_text = ""
        for b in reversed(self._message_blocks):
            if b.sender == "user" and b.raw_text.strip():
                last_user_text = b.raw_text.strip()
                break
        if not last_user_text and hasattr(self, 'chat_title_lbl'):
            t = self.chat_title_lbl.text().strip()
            if t and t != "新任务会话":
                last_user_text = t
        if not last_user_text:
            return

        self._show_status("🔄 正在重新向 AI 提问生成...")
        self._is_generating = True
        self.send_btn.setEnabled(False)
        self.send_btn.setText("⏳")

        # 找到要重试的 AI 消息块并原地重置
        target_ai_block = None
        for b in reversed(self._message_blocks):
            if b.sender == "ai":
                target_ai_block = b
                break
        if target_ai_block:
            target_ai_block.set_text("⏳ 正在思考...")
            self._current_ai_block = target_ai_block
        else:
            self._current_ai_block = self._add_message_block("ai", "⏳ 正在思考...")

        self._stream_id += 1
        active_id = self._stream_id
        threading.Thread(target=self._stream_worker, args=(active_id, last_user_text), daemon=True).start()

    def _scroll_to_bottom(self):
        QTimer.singleShot(20, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def _summon_with_prompt(self, prompt: str):
        self._switch_nav(0)
        self._enter_active_chat_mode()
        self.input_edit.setText(prompt)
        self._send_active_message()

    def _on_scenario_chip(self, name: str):
        prompt_map = {
            "日常办公":  "请帮我制定一份今天的工作计划与待办事项清单",
            "代码开发":  "写一个 Python 异步高并发处理数据的示例",
            "设计创意":  "为一款现代科技感桌面 AI 助手设计一套 UI 配色方案",
            "文档处理":  "帮我把这份技术文档提炼出核心大纲与关键行动项",
            "金融服务":  "分析当前全球宏观经济与科技行业投资要点",
            "数据分析及可视化": "编写一段 Python 代码绘制多维业务数据分析图表",
            "个人工作台": "整理今天的所有待办任务与邮件回复要点",
            "幻灯片":    "生成一份 10 页商业计划书 PPT 大纲与演讲脚本",
            "深度研究":  "深度调研当前 AI Agent 框架的技术架构与发展趋势",
            "视频生成":  "设计一段 60 秒科技产品宣传短视频的分镜脚本",
        }
        p = prompt_map.get(name, f"请帮我处理关于【{name}】的任务")
        self._enter_active_chat_mode()
        self.input_edit.setText(p)
        self._send_active_message()

    def _get_active_model_display(self) -> str:
        active_id = self.config.get("active_model_id", "")
        models = self.config.get("models_list", [])
        m = next((m for m in models if m.get("id") == active_id), None)
        if m:
            name = m.get("name", "未知模型")
            return name if len(name) <= 20 else name[:18] + ".."
        return "DeepSeek-R1"

    def _open_model_selector_popup(self):
        models = self.config.get("models_list", [])
        active_id = self.config.get("active_model_id", "")
        popup = ModelSelectorPopupCard(models=models, active_model_id=active_id,
                                       is_dark=self._is_dark, parent=self)
        popup.model_selected.connect(self._set_active_model_by_config)
        sender = self.sender() or self.model_pill
        pos = sender.mapToGlobal(QPoint(0, -popup.sizeHint().height() - 10))
        popup.move(pos); popup.show()

    def _show_status(self, msg: str):
        self.status_lbl.setText(f"● {msg}")
        QTimer.singleShot(4000, lambda: self.status_lbl.setText("🟢 智能体 就绪"))

    # ══════════════════════════════════════════════════════════
    #  主题与窗口控制 (1:1 像素级复刻截图黑夜主题)
    # ══════════════════════════════════════════════════════════
    def _apply_theme(self):
        d = self._is_dark
        # 截图 1:1 黑夜主题色系 (沉浸式深炭黑 + 高可读性冷白字)
        bg      = "#141414" if d else "#f8fafc"
        side_bg = "#181818" if d else "#f1f5f9"
        card_bg = "#1e1e1e" if d else "#ffffff"
        dock_bg = "#222222" if d else "#ffffff"
        hover   = "#27272a" if d else "#e2e8f0"
        fg      = "#f4f4f5" if d else "#0f172a"
        sub_fg  = "#a1a1aa" if d else "#64748b"
        border  = "#2a2a2a" if d else "#e2e8f0"

        rad = "0px" if self._is_maximized else "16px"
        frame_border = "none" if self._is_maximized else f"1px solid {border}"
        self.main_frame.setStyleSheet(
            f"QFrame#MainFrame{{background-color:{bg};border:{frame_border};border-radius:{rad};}}"
        )
        self.topbar.setStyleSheet(
            f"QWidget#TopBar{{background-color:{side_bg};border-top-left-radius:{rad};"
            f"border-top-right-radius:{rad};border-bottom:1px solid {border};}}"
        )
        self.sidebar.setStyleSheet(
            f"QWidget#SideBar{{background-color:{side_bg};border-right:1px solid {border};}}"
        )
        self.title_lbl.setStyleSheet(f"color:{fg};font-weight:bold;font-family:'Microsoft YaHei UI';")
        if hasattr(self, 'work_lbl'):
            self.work_lbl.setStyleSheet(f"color:{fg};font-size:11px;font-weight:bold;font-family:'Microsoft YaHei UI';")
        self.theme_btn.setText("🌙" if d else "☀️")
        for btn in [self.theme_btn, self.min_btn, self.max_btn]:
            btn.setStyleSheet(
                f"QPushButton{{background:transparent;color:{sub_fg};border:none;font-size:12px;}}"
                f"QPushButton:hover{{background:{hover};color:{fg};border-radius:6px;}}"
            )
        self.close_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{sub_fg};border:none;font-size:12px;}}"
            "QPushButton:hover{background:#ef4444;color:#fff;border-radius:6px;}"
        )
        
        # 新建任务按钮 (深色下沉稳深灰底白字)
        new_task_bg = "#27272a" if d else "#ffffff"
        self.new_task_btn.setStyleSheet(
            f"QPushButton{{background:{new_task_bg};color:{fg};border:1px solid {border};"
            f"border-radius:10px;font-weight:bold;font-size:12.5px;font-family:'Microsoft YaHei UI';}}"
            f"QPushButton:hover{{background:{hover};}}"
        )

        # 侧边栏列表与 4px 定制深灰极细滚动条 (彻底消除纯白粗条)
        scrollbar_style = f"""
            QScrollBar:vertical {{
                width: 4px;
                background: transparent;
                border: none;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {'#3f3f46' if d else '#cbd5e1'};
                border-radius: 2px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {'#52525b' if d else '#94a3b8'};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """
        self.session_list.setStyleSheet(
            f"QListWidget{{background:transparent;border:none;color:{fg};font-size:12px;"
            f"font-family:'Microsoft YaHei UI';outline:none;}}"
            f"QListWidget::item{{border-radius:7px;padding:6px 8px;margin:1px 0;}}"
            f"QListWidget::item:hover{{background:{hover};}}"
            f"QListWidget::item:selected{{background:{'#27272a' if d else '#e0e7ff'};color:{'#ffffff' if d else '#3730a3'};font-weight:bold;}}"
            + scrollbar_style
        )
        self.ws_list.setStyleSheet(
            f"QListWidget{{background:transparent;border:none;color:{fg};font-size:12px;"
            f"font-family:'Microsoft YaHei UI';outline:none;}}"
            f"QListWidget::item{{border-radius:7px;padding:5px 8px;margin:1px 0;}}"
            f"QListWidget::item:hover{{background:{hover};}}"
            f"QListWidget::item:selected{{background:{'#27272a' if d else '#e0e7ff'};color:{'#ffffff' if d else '#3730a3'};font-weight:bold;}}"
            + scrollbar_style
        )

        # 悬浮 DockCard 与 固底 DockCard (深色下 #222222，边框 #2e2e2e)
        dock_style = f"""
            QFrame#HeroDockCard, QFrame#DockCard {{
                background-color: {dock_bg};
                border: 1px solid {'#2e2e2e' if d else '#e2e8f0'};
                border-radius: 16px;
            }}
        """
        self.hero_dock_card.setStyleSheet(dock_style)
        self.dock_card.setStyleSheet(dock_style)

        text_edit_style = f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: {fg};
                font-size: 13.5px;
                font-family: 'Microsoft YaHei UI';
            }}
        """
        self.hero_input_edit.setStyleSheet(text_edit_style)
        self.input_edit.setStyleSheet(text_edit_style)

        # 场景选择胶囊
        for cb in self.chip_buttons:
            chip_bg = "#222222" if d else "#ffffff"
            cb.setStyleSheet(
                f"QPushButton{{background:{chip_bg};color:{fg};border:1px solid {'#2e2e2e' if d else border};"
                f"border-radius:14px;padding:4px 12px;font-size:12px;font-family:'Microsoft YaHei UI';}}"
                f"QPushButton:hover{{background:{'#2e2e32' if d else '#e0e7ff'};color:{'#ffffff' if d else '#3730a3'};}}"
            )

        pill_style = f"""
            QPushButton {{
                background: transparent;
                color: {sub_fg};
                border: none;
                font-size: 11.5px;
                padding: 0 4px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{ color: {fg}; }}
        """
        self.ws_pill.setStyleSheet(pill_style)
        self.perm_pill.setStyleSheet(pill_style)
        self.hero_ws_pill.setStyleSheet(pill_style)
        self.hero_perm_pill.setStyleSheet(pill_style)

        btn_circle_style = f"""
            QPushButton {{
                background: {'#ffffff' if d else '#0f172a'};
                color: {'#0f172a' if d else '#ffffff'};
                border: none;
                border-radius: 15px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {'#e4e4e7' if d else '#334155'}; }}
        """
        self.send_btn.setStyleSheet(btn_circle_style)
        self.hero_send_btn.setStyleSheet(btn_circle_style)

        # 加号按钮 (左侧添加附件) 显式高亮对比度
        plus_btn_style = f"""
            QPushButton {{
                background: {'#2a2a2e' if d else '#f1f5f9'};
                color: {'#e4e4e7' if d else '#334155'};
                border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {'#3f3f46' if d else '#e2e8f0'};
                color: {'#ffffff' if d else '#0f172a'};
            }}
        """
        if hasattr(self, 'plus_btn'): self.plus_btn.setStyleSheet(plus_btn_style)
        if hasattr(self, 'hero_plus_btn'): self.hero_plus_btn.setStyleSheet(plus_btn_style)

        # 底部模型选择胶囊 (高对比度清晰文字)
        model_pill_style = f"""
            QPushButton {{
                background: {'#2a2a2e' if d else '#f8fafc'};
                color: {'#f4f4f5' if d else '#0f172a'};
                border: 1px solid {'#3f3f46' if d else '#cbd5e1'};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {'#3f3f46' if d else '#e2e8f0'};
                color: {'#ffffff' if d else '#0f172a'};
            }}
        """
        if hasattr(self, 'model_pill'): self.model_pill.setStyleSheet(model_pill_style)
        if hasattr(self, 'hero_model_pill'): self.hero_model_pill.setStyleSheet(model_pill_style)

        # 聊天区域全面适配深色模式 (彻底消除白色背景与低对比度文字)
        content_bg = "#141414" if d else "#ffffff"
        if hasattr(self, 'page_chat'): self.page_chat.setStyleSheet(f"background-color: {content_bg};")
        if hasattr(self, 'chat_page_stack'): self.chat_page_stack.setStyleSheet(f"background-color: {content_bg};")
        if hasattr(self, 'view_hero'): self.view_hero.setStyleSheet(f"background-color: {content_bg};")
        if hasattr(self, 'view_active'): self.view_active.setStyleSheet(f"background-color: {content_bg};")
        if hasattr(self, 'main_stack'): self.main_stack.setStyleSheet(f"background-color: {content_bg};")
        if hasattr(self, 'chat_content'): self.chat_content.setStyleSheet("background: transparent;")
        if hasattr(self, 'scroll_area'):
            self.scroll_area.viewport().setStyleSheet("background: transparent;")
            self.scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background: transparent;
                    border: none;
                }}
                QScrollBar:vertical {{
                    width: 5px;
                    background: transparent;
                    border-radius: 3px;
                }}
                QScrollBar::handle:vertical {{
                    background: {'#3f3f46' if d else '#cbd5e1'};
                    border-radius: 3px;
                    min-height: 24px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: {'#52525b' if d else '#94a3b8'};
                }}
            """)

        for b in self._message_blocks:
            b.set_theme(d)

        if hasattr(self, 'h_title'):
            self.h_title.setStyleSheet(f"color:{fg};font-size:24px;font-weight:bold;font-family:'Microsoft YaHei UI';")
        if hasattr(self, 'task_head'):
            self.task_head.setStyleSheet(f"color:{sub_fg};font-size:11px;font-weight:bold;")
        if hasattr(self, 'ws_head'):
            self.ws_head.setStyleSheet(f"color:{sub_fg};font-size:11px;font-weight:bold;")
        if hasattr(self, 'chat_title_lbl'):
            self.chat_title_lbl.setStyleSheet(f"color:{fg};font-size:12.5px;font-weight:bold;font-family:'Microsoft YaHei UI';")
        if hasattr(self, 'search_chat_btn'):
            self.search_chat_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#27272a' if d else '#ffffff'};
                    color: {fg};
                    border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                    border-radius: 6px;
                    font-size: 12px;
                }}
                QPushButton:hover {{ background: {hover}; }}
            """)
        if hasattr(self, 'export_chat_btn'):
            self.export_chat_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#27272a' if d else '#ffffff'};
                    color: {fg};
                    border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                    border-radius: 6px;
                    padding: 0 10px;
                    font-size: 11.5px;
                    font-family: 'Microsoft YaHei UI';
                }}
                QPushButton:hover {{ background: {hover}; }}
            """)
        if hasattr(self, 'hub_search'):
            self.hub_search.setStyleSheet(
                f"QLineEdit{{background:{card_bg};color:{fg};border:1px solid {border};"
                f"border-radius:8px;padding:0 8px;font-size:12px;font-family:'Microsoft YaHei UI';}}"
            )
        if hasattr(self, 'custom_conn_btn'):
            self.custom_conn_btn.setStyleSheet(
                f"QPushButton{{background:{card_bg};color:{fg};border:1px solid {border};"
                f"border-radius:8px;padding:0 12px;font-size:11.5px;font-family:'Microsoft YaHei UI';}}"
                f"QPushButton:hover{{background:{hover};}}"
            )
        if hasattr(self, 'my_installed_btn'):
            self.my_installed_btn.setStyleSheet(
                f"QPushButton{{background:{card_bg};color:{fg};border:1px solid {border};"
                f"border-radius:8px;padding:0 12px;font-size:11.5px;font-family:'Microsoft YaHei UI';}}"
                f"QPushButton:hover{{background:{hover};}}"
            )
        if hasattr(self, 'sound_btn'):
            self.sound_btn.setStyleSheet(
                f"QPushButton{{background:transparent;border:none;border-radius:6px;font-size:13px;padding:2px;}}"
                f"QPushButton:hover{{background:{hover};}}"
            )
        if hasattr(self, 'see_more_btn'):
            self.see_more_btn.setStyleSheet(f"""
                QPushButton#SeeMoreBtn {{
                    background-color: {'#27272a' if d else '#f1f5f9'};
                    color: {'#a1a1aa' if d else '#64748b'};
                    border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                    border-radius: 6px;
                    padding: 5px 10px;
                    font-size: 11.5px;
                    font-family: 'Microsoft YaHei UI';
                    font-weight: 500;
                }}
                QPushButton#SeeMoreBtn:hover {{
                    background-color: {'#3f3f46' if d else '#e2e8f0'};
                    color: {'#ffffff' if d else '#0f172a'};
                }}
            """)

        # 设置页面表单输入控件沉浸式暗黑调色 (解决纯白刺眼底色)
        if hasattr(self, 'form_card'):
            self.form_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {card_bg};
                    border: 1px solid {border};
                    border-radius: 12px;
                }}
                QLabel {{
                    color: {sub_fg};
                    font-size: 12px;
                    font-family: 'Microsoft YaHei UI';
                }}
            """)
            input_box_style = f"""
                QLineEdit {{
                    background-color: {'#141414' if d else '#ffffff'};
                    color: {fg};
                    border: 1px solid {'#2e2e2e' if d else '#e2e8f0'};
                    border-radius: 8px;
                    padding: 0 10px;
                    font-size: 12.5px;
                    font-family: 'Microsoft YaHei UI';
                }}
                QLineEdit:focus {{
                    border-color: #6366f1;
                }}
            """
            for ed in [self.cfg_name_edit, self.cfg_model_name, self.cfg_api_url, self.cfg_api_key]:
                ed.setStyleSheet(input_box_style)
            self.cfg_provider_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {'#141414' if d else '#ffffff'};
                    color: {fg};
                    border: 1px solid {'#2e2e2e' if d else '#e2e8f0'};
                    border-radius: 8px;
                    padding: 0 10px;
                    font-size: 12.5px;
                    font-family: 'Microsoft YaHei UI';
                }}
                QComboBox:focus {{
                    border-color: #6366f1;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 24px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {'#1e1e1e' if d else '#ffffff'};
                    color: {fg};
                    border: 1px solid {border};
                    selection-background-color: {'#27272a' if d else '#e0e7ff'};
                    selection-color: {'#ffffff' if d else '#3730a3'};
                }}
            """)
        if hasattr(self, 'test_btn'):
            self.test_btn.setStyleSheet(
                f"QPushButton{{background:{'#27272a' if d else '#f1f5f9'};color:{fg};border:1px solid {border};"
                f"border-radius:8px;font-size:12px;font-weight:bold;font-family:'Microsoft YaHei UI';}}"
                f"QPushButton:hover{{background:{hover};}}"
            )
        if hasattr(self, 'save_curr_btn'):
            self.save_curr_btn.setStyleSheet(
                f"QPushButton{{background:{'#ffffff' if d else '#0f172a'};color:{'#0f172a' if d else '#ffffff'};border:none;border-radius:8px;"
                f"font-size:12px;font-weight:bold;font-family:'Microsoft YaHei UI';}}"
                f"QPushButton:hover{{background:{'#e4e4e7' if d else '#1e293b'};}}"
            )
        if hasattr(self, 'tpl_head'):
            self.tpl_head.setStyleSheet(f"color:{fg};font-size:13px;font-weight:bold;font-family:'Microsoft YaHei UI';")

        # 技能大厅分类胶囊与刷新按钮同步更新
        if hasattr(self, 'skill_cat_buttons'):
            for b in self.skill_cat_buttons:
                self._apply_cat_btn_style(b, b.isChecked())
        if hasattr(self, 'skill_refresh_btn'):
            self.skill_refresh_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#27272a' if d else '#f1f5f9'};
                    color: {'#a1a1aa' if d else '#64748b'};
                    border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                    border-radius: 6px; padding: 0 10px; font-size: 11.5px;
                }}
                QPushButton:hover {{
                    background: {'#3f3f46' if d else '#e2e8f0'};
                    color: {'#ffffff' if d else '#0f172a'};
                }}
            """)

        # 刷新所有子页面网格卡片背景颜色 (沉浸式暗黑重绘)
        if hasattr(self, 'experts_grid'):
            self._rebuild_expert_cards()
        if hasattr(self, 'skills_grid'):
            self._rebuild_skills_grid()
        if hasattr(self, 'conn_grid'):
            self._rebuild_connectors_grid()
        if hasattr(self, 'tpl_grid'):
            self._rebuild_template_cards()
        if hasattr(self, 'task_list_widget'):
            self._refresh_task_list()
        self._refresh_model_cards()
        self._refresh_history_list()
        self._refresh_sidebar_workspaces()
        self._switch_nav(self.main_stack.currentIndex())

    def _switch_nav(self, index: int):
        self.main_stack.setCurrentIndex(index)
        d = self._is_dark
        on  = ("QPushButton{background:%s;color:%s;font-weight:bold;border-radius:9px;"
               "text-align:left;padding-left:12px;font-size:12.5px;border:none;"
               "font-family:'Microsoft YaHei UI';}") % (
                    "#27272a" if d else "#e0e7ff",
                    "#ffffff" if d else "#3730a3"
               )
        off = ("QPushButton{background:transparent;color:%s;border:none;border-radius:9px;"
               "text-align:left;padding-left:12px;font-size:12.5px;"
               "font-family:'Microsoft YaHei UI';} QPushButton:hover{background:%s;color:%s;}") % (
                    "#a1a1aa" if d else "#475569",
                    "#222222" if d else "#e2e8f0",
                    "#ffffff" if d else "#0f172a"
               )
        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == index)
            btn.setStyleSheet(on if i == index else off)

        if index == 0:
            if self.chat_page_stack.currentIndex() == 0:
                self.hero_input_edit.setFocus()
            else:
                self.input_edit.setFocus()
        elif index == 3:
            self._load_active_model_into_form()
            self._refresh_model_cards()

    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        self.config["ui_theme"] = "dark" if self._is_dark else "light"
        if self.save_config_fn:
            self.save_config_fn(self.config)
        self._apply_theme()

    def _toggle_maximize(self):
        if not self._is_maximized:
            self._normal_geometry = self.geometry()
            try:
                avail = QApplication.primaryScreen().availableGeometry()
                self.setGeometry(avail)
            except Exception:
                self.resize(1200, 860)

            # 最大化时消除四周留白与阴影发虚
            if hasattr(self, 'root_layout'):
                self.root_layout.setContentsMargins(0, 0, 0, 0)
            if hasattr(self, 'main_frame_shadow'):
                self.main_frame_shadow.setEnabled(False)

            self._is_maximized = True
            self.max_btn.setText("❐")
            self._apply_theme()
        else:
            # 还原普通悬浮窗口，恢复优雅阴影与 8px 边距
            if hasattr(self, 'root_layout'):
                self.root_layout.setContentsMargins(8, 8, 8, 8)
            if hasattr(self, 'main_frame_shadow'):
                self.main_frame_shadow.setEnabled(True)

            self._is_maximized = False
            self.max_btn.setText("▢")
            if self._normal_geometry:
                self.setGeometry(self._normal_geometry)
            else:
                self.resize(1120, 780)
            self._apply_theme()

    def open_settings(self):
        self.show(); self.raise_(); self.activateWindow()
        self._switch_nav(3)
