# -*- coding: utf-8 -*-
"""
NovaDesk v4.0 - 全功能桌面 AI 工作台 (WorkBuddy 级像素复刻)
- 聊天主页：空态悬浮居中输入框 vs 对话态底部固定输入框双态无缝切换
- 消息展示：纯净 Markdown 优雅排版 + 底部快捷工具条 (复制/点赞/点踩/重试/Token统计)
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
import time
import asyncio
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
        QLineEdit, QTextEdit, QScrollArea, QFrame, QApplication, QStackedWidget,
        QSplitter, QTableWidget, QTableWidgetItem, QComboBox, QFormLayout,
        QListWidget, QListWidgetItem, QHeaderView, QMessageBox, QFileDialog,
        QSizePolicy, QDialog, QGraphicsDropShadowEffect, QMenu, QAction,
        QInputDialog, QCheckBox, QSpinBox, QTimeEdit, QDateEdit, QDialogButtonBox,
        QTabWidget, QScrollBar, QToolButton, QGraphicsOpacityEffect, QSpacerItem,
        QAbstractItemView, QCalendarWidget, QAbstractSpinBox
    )
    from PyQt5.QtCore import (
        Qt, pyqtSignal, QPoint, QPointF, QRectF, QTimer, QSize, QRect, QTime, QDate,
        QPropertyAnimation, QEasingCurve, pyqtProperty, QEvent
    )
    from PyQt5.QtGui import (
        QFont, QColor, QIcon, QPainter, QPainterPath, QPen, QBrush, QPixmap,
        QCursor, QTextCursor, QFontMetrics, QLinearGradient, QTransform,
        QTextCharFormat, QKeySequence
    )
    from PyQt5.QtSvg import QSvgRenderer
    from PyQt5.QtCore import QByteArray
except ImportError:
    pass

try:
    from PyQt5.QtWinExtras import QWinTaskbarButton, QWinTaskbarProgress
    HAS_WIN_EXTRAS = True
except Exception:
    HAS_WIN_EXTRAS = False

import html
try:
    import pygments
    from pygments.lexers import get_lexer_by_name, TextLexer
    from pygments.formatters import HtmlFormatter
    HAS_PYGMENTS = True
except Exception:
    HAS_PYGMENTS = False

try:
    import markdown
    HAS_MARKDOWN = True
except Exception:
    HAS_MARKDOWN = False

import ctypes
from ctypes import wintypes

class FLASHWINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('hwnd', wintypes.HWND),
        ('dwFlags', wintypes.DWORD),
        ('uCount', wintypes.UINT),
        ('dwTimeout', wintypes.DWORD)
    ]

FLASHW_STOP = 0
FLASHW_ALL = 3
FLASHW_TIMERNOFG = 12

def flash_window_taskbar(hwnd):
    try:
        finfo = FLASHWINFO()
        finfo.cbSize = ctypes.sizeof(FLASHWINFO)
        finfo.hwnd = int(hwnd)
        finfo.dwFlags = FLASHW_ALL | FLASHW_TIMERNOFG
        finfo.uCount = 0
        finfo.dwTimeout = 0
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(finfo))
    except Exception as e:
        pass

def stop_flash_window(hwnd):
    try:
        finfo = FLASHWINFO()
        finfo.cbSize = ctypes.sizeof(FLASHWINFO)
        finfo.hwnd = int(hwnd)
        finfo.dwFlags = FLASHW_STOP
        finfo.uCount = 0
        finfo.dwTimeout = 0
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(finfo))
    except Exception as e:
        pass

ROOT_DIR = Path(__file__).parent.parent
ICON_PATH = ROOT_DIR / "assets" / "icons" / "pet_icon.png"
UI_ICONS_DIR = ROOT_DIR / "assets" / "icons" / "ui"
MCP_CONFIG_PATH = ROOT_DIR / "mcp_config.json"
SKILLS_DIR = ROOT_DIR / "skills"
AUTO_LOG_PATH = ROOT_DIR / "data" / "auto_run_log.json"


# ─────────────────────────── 工具函数 ───────────────────────────

def load_ui_icon(name: str, color: str = "#f4f4f5", size: int = 16, dpi: int = 96) -> QIcon:
    """从 assets/icons/ui/{name}.svg 加载图标，按指定颜色和尺寸渲染。"""
    svg_path = UI_ICONS_DIR / f"{name}.svg"
    if not svg_path.exists():
        return QIcon()
    try:
        from PyQt5.QtSvg import QSvgRenderer
        from PyQt5.QtCore import QByteArray
        text = svg_path.read_text(encoding="utf-8")
        # 把 currentColor 替换为实际颜色
        text = text.replace('currentColor', color)
        renderer = QSvgRenderer(QByteArray(text.encode("utf-8")))
        pm = QPixmap(size * dpi // 96, size * dpi // 96)
        pm.fill(QColor(0, 0, 0, 0))  # 透明背景
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        renderer.render(painter)
        painter.end()
        return QIcon(pm)
    except Exception:
        return QIcon()

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
    logs = []
    seen = set()
    
    # 1. 先读 auto_run_log.json
    if AUTO_LOG_PATH.exists():
        try:
            with open(AUTO_LOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        k = (item.get("name"), item.get("cmd"), item.get("time"))
                        if k not in seen:
                            seen.add(k)
                            logs.append(item)
        except Exception:
            pass

    # 2. 回退与合并旧日志 data/automation_logs.json
    legacy_path = ROOT_DIR / "data" / "automation_logs.json"
    if legacy_path.exists():
        try:
            with open(legacy_path, "r", encoding="utf-8") as f:
                legacy_data = json.load(f)
                if isinstance(legacy_data, list):
                    added_new = False
                    for item in legacy_data:
                        k = (item.get("name"), item.get("cmd"), item.get("time"))
                        if k not in seen:
                            seen.add(k)
                            logs.append(item)
                            added_new = True
                    if added_new:
                        save_auto_log(logs)
        except Exception:
            pass
            
    return logs


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

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            win = self.window()
            if win and hasattr(win, '_toggle_maximize'):
                win._toggle_maximize()
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


# ─────────────────────────── 聊天输入框 ───────────────────────────

class ChatTextEdit(QTextEdit):
    return_pressed = pyqtSignal()
    file_attached = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.return_pressed.emit()
                event.accept()
        elif event.matches(QKeySequence.Paste) or (event.key() == Qt.Key_V and (event.modifiers() & Qt.ControlModifier)):
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData() if clipboard else None
            if mime_data:
                # 检查剪贴板中是否有截图/图片
                if mime_data.hasImage():
                    img = clipboard.image()
                    if not img.isNull():
                        import time
                        cache_dir = ROOT_DIR / ".desk_cache" / "uploads"
                        cache_dir.mkdir(parents=True, exist_ok=True)
                        target_p = cache_dir / f"paste_{int(time.time()*1000)}.png"
                        img.save(str(target_p), "PNG")
                        self.file_attached.emit(str(target_p))
                        event.accept()
                        return
                # 检查剪贴板中复制的文件列表
                elif mime_data.hasUrls():
                    handled = False
                    for url in mime_data.urls():
                        l_path = url.toLocalFile()
                        if l_path and Path(l_path).exists():
                            self.file_attached.emit(l_path)
                            handled = True
                    if handled:
                        event.accept()
                        return
            super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data and mime_data.hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data and mime_data.hasUrls():
            for url in mime_data.urls():
                l_path = url.toLocalFile()
                if l_path and Path(l_path).exists():
                    self.file_attached.emit(l_path)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

# ─────────────────────────── 侧边栏工作空间头部组件 ───────────────────────────

class SidebarWorkspaceHeaderWidget(QWidget):
    """工作空间卡片头部 [folder + 名称 + chevron] 右侧显示 [··· 更多 + 💬+ 新建任务]"""
    clicked = pyqtSignal(str, str)             # ws_name, ws_path
    add_task_clicked = pyqtSignal(str, str)    # ws_name, ws_path
    open_folder_requested = pyqtSignal(str)   # ws_path
    remove_requested = pyqtSignal(str)        # ws_name
    batch_requested = pyqtSignal()            # 批量管理空间信号

    def __init__(self, name: str, path: str, is_active: bool = False, is_collapsed: bool = False, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self.ws_name = name
        self.ws_path = path
        self.is_active = is_active
        self.is_collapsed = is_collapsed
        self.is_dark = is_dark
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._init_ui()

    def _init_ui(self):
        d = self.is_dark
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 8, 0)
        lay.setSpacing(6)

        # 左侧 folder SVG 图标
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(16, 16)
        self.icon_lbl.setStyleSheet("background: transparent;")
        ic_color = "#ffffff" if (self.is_active and d) else ("#0f172a" if self.is_active else ("#a1a1aa" if d else "#64748b"))
        self.icon_lbl.setPixmap(load_ui_icon("folder", ic_color, 15).pixmap(QSize(15, 15)))
        lay.addWidget(self.icon_lbl, 0, Qt.AlignVCenter)

        # 空间名称
        self.title_lbl = QLabel()
        font = QFont("Microsoft YaHei UI", 10, QFont.DemiBold if self.is_active else QFont.Normal)
        font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
        self.title_lbl.setFont(font)
        self.title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        fm = QFontMetrics(font)
        self.title_lbl.setText(fm.elidedText(self.ws_name, Qt.ElideRight, 135))
        self.title_lbl.setToolTip(self.ws_name)
        text_color = "#ffffff" if (self.is_active and d) else ("#0f172a" if self.is_active else ("#e4e4e7" if d else "#334155"))
        self.title_lbl.setStyleSheet(f"color: {text_color}; background: transparent;")
        lay.addWidget(self.title_lbl, 0, Qt.AlignVCenter)

        # 右侧 chevron SVG（紧随名称之后，展开时朝下 ⌵，收起时朝右 >）
        self.chev_lbl = QLabel()
        self.chev_lbl.setFixedSize(12, 12)
        self.chev_lbl.setStyleSheet("background: transparent;")
        chev_name = "chevron-down" if not self.is_collapsed else "chevron-right"
        chev_color = "#a1a1aa" if d else "#94a3b8"
        self.chev_lbl.setPixmap(load_ui_icon(chev_name, chev_color, 12).pixmap(QSize(12, 12)))
        self.chev_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(self.chev_lbl, 0, Qt.AlignVCenter)

        # 弹性空白拉伸，将操作按钮推至最右侧
        lay.addStretch(1)

        # 右侧操作按钮组 (··· 更多操作 + 💬+ 新建任务)
        self.actions_widget = QWidget(self)
        self.actions_widget.setStyleSheet("background: transparent;")
        a_lay = QHBoxLayout(self.actions_widget)
        a_lay.setContentsMargins(0, 0, 0, 0)
        a_lay.setSpacing(5)

        icon_btn_style = f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 5px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background: {'#3f3f46' if d else '#e2e8f0'};
            }}
        """

        # 1. ··· 更多操作按钮
        self.btn_more = QPushButton()
        self.btn_more.setFixedSize(22, 22)
        self.btn_more.setToolTip("更多操作")
        self.btn_more.setCursor(Qt.PointingHandCursor)
        self.btn_more.setIcon(load_ui_icon("more", "#e4e4e7" if d else "#475569", 14))
        self.btn_more.setIconSize(QSize(14, 14))
        self.btn_more.setStyleSheet(icon_btn_style)
        self.btn_more.clicked.connect(self._show_more_menu)
        a_lay.addWidget(self.btn_more)

        # 2. 💬+ 在当前空间新建任务按钮
        self.btn_add = QPushButton()
        self.btn_add.setFixedSize(22, 22)
        self.btn_add.setToolTip("在当前空间新建任务")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setIcon(load_ui_icon("chat-plus", "#e4e4e7" if d else "#475569", 15))
        self.btn_add.setIconSize(QSize(15, 15))
        self.btn_add.setStyleSheet(icon_btn_style)
        self.btn_add.clicked.connect(lambda: self.add_task_clicked.emit(self.ws_name, self.ws_path))
        a_lay.addWidget(self.btn_add)

        lay.addWidget(self.actions_widget, 0, Qt.AlignVCenter)

        # 初始化背景与显隐状态
        if self.is_active:
            bg = "#27272a" if d else "#f1f5f9"
            self.setStyleSheet(f"background-color: {bg}; border-radius: 8px;")
            self.actions_widget.show()
        else:
            self.setStyleSheet("background-color: transparent; border-radius: 8px;")
            self.actions_widget.hide()

    def enterEvent(self, event):
        self.actions_widget.show()
        if not self.is_active:
            bg = "#222225" if self.is_dark else "#f8fafc"
            self.setStyleSheet(f"background-color: {bg}; border-radius: 8px;")
        else:
            bg = "#2e2e32" if self.is_dark else "#e2e8f0"
            self.setStyleSheet(f"background-color: {bg}; border-radius: 8px;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.is_active:
            self.actions_widget.hide()
            self.setStyleSheet("background-color: transparent; border-radius: 8px;")
        else:
            bg = "#27272a" if self.is_dark else "#f1f5f9"
            self.setStyleSheet(f"background-color: {bg}; border-radius: 8px;")
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 点击右侧操作按钮区时不触发整行折叠/切换
            if hasattr(self, 'actions_widget') and self.actions_widget.isVisible():
                if self.actions_widget.geometry().contains(event.pos()):
                    event.accept()
                    return
            self.clicked.emit(self.ws_name, self.ws_path)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if hasattr(self, 'actions_widget') and self.actions_widget.isVisible():
                if self.actions_widget.geometry().contains(event.pos()):
                    event.accept()
                    return
            self.clicked.emit(self.ws_name, self.ws_path)
        super().mouseDoubleClickEvent(event)

    def _show_more_menu(self):
        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.Popup | Qt.FramelessWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground, True)
        d = self.is_dark
        bg = "#1e1e20" if d else "#ffffff"
        fg = "#f4f4f5" if d else "#0f172a"
        border = "#2e2e32" if d else "#e2e8f0"
        item_hover_bg = "#2a2a2d" if d else "#f1f5f9"
        item_hover_fg = "#ffffff" if d else "#0f172a"
        sep_bg = "#2e2e32" if d else "#e2e8f0"

        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 12px;
                padding: 6px 5px;
                font-family: -apple-system, 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
                font-size: 12.5px;
                font-weight: 500;
            }}
            QMenu::item {{
                padding: 7px 18px;
                border-radius: 6px;
                background-color: transparent;
            }}
            QMenu::item:selected {{
                background-color: {item_hover_bg};
                color: {item_hover_fg};
            }}
            QMenu::separator {{
                height: 1px;
                background: {sep_bg};
                margin: 4px 6px;
            }}
        """)
        act_open = menu.addAction("📁 打开文件夹")
        menu.addSeparator()
        act_batch = menu.addAction("⚙️ 批量管理空间...")
        act_remove = menu.addAction("🗑️ 从列表中移除")

        # 对齐显示在更多按钮下方
        btn_pos = self.btn_more.mapToGlobal(QPoint(-75, self.btn_more.height() + 4))
        act = menu.exec_(btn_pos)
        if act == act_open:
            self.open_folder_requested.emit(self.ws_path)
        elif act == act_batch:
            self.batch_requested.emit()
        elif act == act_remove:
            self.remove_requested.emit(self.ws_name)


# ─────────────────────────── 侧边栏任务项小部件 (Hover 悬浮显示操作图标) ───────────────────────────

# ─────────────────────────── 侧边栏任务项小部件 (Hover 悬浮显示操作图标) ───────────────────────────

class RotatingSpinner(QWidget):
    """中心锚定平滑旋转 Spinner (0.0px 摆动，严格围绕几何中心点自转)"""
    def __init__(self, icon_name: str = "loader", color: str = "#2dd4bf", size: int = 14, parent=None):
        super().__init__(parent)
        self.size_val = size
        self.setFixedSize(16, 16)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background: transparent;")
        self._angle = 0
        self._pix = load_ui_icon(icon_name, color, size).pixmap(QSize(size, size))
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

    def start(self):
        if not self._timer.isActive():
            self._timer.start()
        self.show()

    def stop(self):
        if self._timer.isActive():
            self._timer.stop()
        self.hide()

    def _tick(self):
        self._angle = (self._angle + 30) % 360
        self.update()

    def paintEvent(self, event):
        if not self.isVisible():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        p.translate(cx, cy)
        p.rotate(self._angle)
        p.translate(-cx, -cy)
        x = int((self.width() - self._pix.width()) / 2.0)
        y = int((self.height() - self._pix.height()) / 2.0)
        p.drawPixmap(x, y, self._pix)
        p.end()


class SidebarTaskItemWidget(QWidget):
    """复刻截图：
    - 左侧：上行任务标题 + 下行相对时间
    - 右侧：
        * 正在生成时常驻显示旋转的青绿色星芒 Spinner (※ #2dd4bf / 8-ray loader，零晃动平滑自转)
        * 鼠标 Hover 时平滑切换为操作按钮组 [更多 ...][归档 🗄️][置顶 📌]
        * 鼠标移出后，若任务仍在生成中，则无缝切回旋转 Spinner
        * 支持多任务并发独立旋转与状态同步
    """
    clicked = pyqtSignal(int)
    rename_requested = pyqtSignal(int, str)
    delete_requested = pyqtSignal(int)
    archive_requested = pyqtSignal(int)
    pin_toggled = pyqtSignal(int, bool)
    save_to_ws_requested = pyqtSignal(int, str)
    export_requested = pyqtSignal(int, str)
    batch_requested = pyqtSignal()

    def __init__(self, session_id: int, title: str, time_str: str = "", is_pinned: bool = False, is_active: bool = False, is_dark: bool = False, is_sub_item: bool = False, is_generating: bool = False, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.full_title = str(title).strip()
        self.title = self.full_title
        self.time_str = time_str
        self.is_pinned = is_pinned
        self.is_active = is_active
        self.is_dark = is_dark
        self.is_sub_item = is_sub_item
        self.is_generating = is_generating
        self._is_hovered = False
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()

    def _init_ui(self):
        self._update_background_style()

        lay = QHBoxLayout(self)
        left_margin = 20 if self.is_sub_item else 8
        lay.setContentsMargins(left_margin, 3, 6, 3)
        lay.setSpacing(4)

        # ── 左侧：标题与时间文本列 ──
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(1)

        self.title_lbl = QLabel(self.full_title)
        t_font = QFont("Microsoft YaHei UI", 9, QFont.Bold if self.is_active else QFont.Normal)
        t_font.setPointSizeF(9.5)
        t_font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
        self.title_lbl.setFont(t_font)
        self.title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.title_lbl.setStyleSheet("background: transparent;")
        if self.is_active:
            text_color = "#ffffff" if self.is_dark else "#6366f1"
        else:
            text_color = ("#cbd5e1" if self.is_sub_item else "#e4e4e7") if self.is_dark else ("#475569" if self.is_sub_item else "#0f172a")
        self.title_lbl.setStyleSheet(f"color: {text_color}; background: transparent;")
        self.setToolTip(self.full_title)
        self.title_lbl.setToolTip(self.full_title)
        text_col.addWidget(self.title_lbl)

        self.time_lbl = QLabel(self.time_str)
        self.time_lbl.setStyleSheet(f"color: {'#71717a' if self.is_dark else '#94a3b8'}; font-size: 11px; background: transparent;")
        self.time_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        text_col.addWidget(self.time_lbl)

        lay.addLayout(text_col, 1)

        # ── 右侧：旋转 Loader 与 Hover 操作按钮组 ──
        self.right_container = QWidget(self)
        self.right_container.setStyleSheet("background: transparent;")
        right_lay = QHBoxLayout(self.right_container)
        right_lay.setContentsMargins(0, 2, 0, 0)
        right_lay.setSpacing(2)

        # 1. 旋转 Loader (青绿星芒 #2dd4bf，精准中心旋转零摆动)
        self.loader_spinner = RotatingSpinner(icon_name="loader", color="#2dd4bf", size=14, parent=self.right_container)
        right_lay.addWidget(self.loader_spinner, 0, Qt.AlignCenter)

        # 2. 操作按钮容器
        self.actions_widget = QWidget(self.right_container)
        self.actions_widget.setStyleSheet("background: transparent;")
        a_lay = QHBoxLayout(self.actions_widget)
        a_lay.setContentsMargins(0, 0, 0, 0)
        a_lay.setSpacing(2)

        icon_btn_style = f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background: {'#2e2e32' if self.is_dark else '#e2e8f0'};
            }}
        """
        _icon_color = "#a1a1aa" if self.is_dark else "#64748b"
        _pin_color = "#818cf8" if self.is_dark else "#6366f1"

        # 更多 ...
        self.btn_more = QPushButton()
        self.btn_more.setFixedSize(20, 20)
        self.btn_more.setToolTip("更多")
        self.btn_more.setStyleSheet(icon_btn_style)
        self.btn_more.setIcon(load_ui_icon("more", _icon_color, 14))
        self.btn_more.setIconSize(QSize(14, 14))
        self.btn_more.clicked.connect(self._show_more_menu)
        a_lay.addWidget(self.btn_more)

        # 归档
        self.btn_archive = QPushButton()
        self.btn_archive.setFixedSize(20, 20)
        self.btn_archive.setToolTip("归档任务")
        self.btn_archive.setStyleSheet(icon_btn_style)
        self.btn_archive.setIcon(load_ui_icon("archive", _icon_color, 14))
        self.btn_archive.setIconSize(QSize(14, 14))
        self.btn_archive.clicked.connect(lambda: self.archive_requested.emit(self.session_id))
        a_lay.addWidget(self.btn_archive)

        # 置顶
        pin_icon_name = "pin"
        pin_tip = "取消置顶" if self.is_pinned else "置顶任务"
        self.btn_pin = QPushButton()
        self.btn_pin.setFixedSize(20, 20)
        self.btn_pin.setToolTip(pin_tip)
        self.btn_pin.setIcon(load_ui_icon(pin_icon_name, _pin_color if self.is_pinned else _icon_color, 14))
        self.btn_pin.setIconSize(QSize(14, 14))
        self.btn_pin.setStyleSheet(icon_btn_style)
        self.btn_pin.clicked.connect(lambda: self.pin_toggled.emit(self.session_id, not self.is_pinned))
        a_lay.addWidget(self.btn_pin)

        right_lay.addWidget(self.actions_widget, 0, Qt.AlignCenter)
        lay.addWidget(self.right_container, 0, Qt.AlignRight | Qt.AlignTop)

        # 同步可见状态
        self.actions_widget.hide()
        if self.is_generating:
            self.loader_spinner.start()
        else:
            self.loader_spinner.stop()
        self._update_elided_title()

    def _update_elided_title(self):
        """当侧边栏宽度不足或显示悬浮按钮时，自动使用三个点 ... 优雅省略标题"""
        if not hasattr(self, 'title_lbl') or not getattr(self, 'full_title', None):
            return
        total_w = self.width()
        if total_w <= 10:
            total_w = 214
        left_m = 20 if self.is_sub_item else 8
        right_m = 6
        spacing = 4
        if hasattr(self, 'actions_widget') and self.actions_widget.isVisible():
            right_w = 68
        elif getattr(self, 'is_generating', False):
            right_w = 20
        else:
            right_w = 4
        avail_w = max(30, total_w - left_m - right_m - spacing - right_w - 4)

        fm = QFontMetrics(self.title_lbl.font())
        if fm.width(self.full_title) <= avail_w:
            self.title_lbl.setText(self.full_title)
        else:
            suffix = "..."
            s_w = fm.width(suffix)
            target_w = avail_w - s_w
            if target_w <= 0:
                self.title_lbl.setText(suffix)
            else:
                low, high, best = 0, len(self.full_title), 0
                while low <= high:
                    mid = (low + high) // 2
                    if fm.width(self.full_title[:mid]) <= target_w:
                        best = mid
                        low = mid + 1
                    else:
                        high = mid - 1
                self.title_lbl.setText(self.full_title[:best] + suffix)

    def set_title(self, new_title: str):
        self.full_title = str(new_title).strip()
        self.title = self.full_title
        self.setToolTip(self.full_title)
        if hasattr(self, 'title_lbl'):
            self.title_lbl.setToolTip(self.full_title)
        self._update_elided_title()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_title()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_elided_title()

    def _update_background_style(self):
        if self.is_active:
            bg = "#27272a" if self.is_dark else "#e0e7ff"
            self.setStyleSheet(f"background-color: {bg}; border-radius: 8px;")
        elif getattr(self, '_is_hovered', False):
            bg = "#232326" if self.is_dark else "#f1f5f9"
            self.setStyleSheet(f"background-color: {bg}; border-radius: 8px;")
        else:
            self.setStyleSheet("background-color: transparent;")

    def set_active(self, is_active: bool):
        if getattr(self, 'is_active', False) == is_active:
            return
        self.is_active = is_active
        self._update_background_style()
        if hasattr(self, 'title_lbl'):
            t_font = QFont("Microsoft YaHei UI", 9, QFont.Bold if self.is_active else QFont.Normal)
            t_font.setPointSizeF(9.5)
            self.title_lbl.setFont(t_font)
            text_color = "#ffffff" if (self.is_dark and self.is_active) else ("#6366f1" if self.is_active else ("#e4e4e7" if self.is_dark else "#0f172a"))
            self.title_lbl.setStyleSheet(f"color: {text_color}; background: transparent;")

    def set_generating(self, is_gen: bool):
        """外部调用：标记当前任务项是否正在生成 (支持多任务独立并发)"""
        self.is_generating = is_gen
        if is_gen:
            if not self._is_hovered:
                self.loader_spinner.start()
                self.actions_widget.hide()
            else:
                self.loader_spinner.hide()
        else:
            self.loader_spinner.stop()
            if not self._is_hovered:
                self.actions_widget.hide()
        self._update_elided_title()

    def enterEvent(self, event):
        self._is_hovered = True
        self._update_background_style()
        self.actions_widget.show()
        self.loader_spinner.hide()
        self._update_elided_title()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self._update_background_style()
        self.actions_widget.hide()
        if self.is_generating:
            self.loader_spinner.start()
        self._update_elided_title()
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
            if show_themed_confirm(self, "确认删除", f"确定要永久删除任务「{self.title}」吗？\n删除后会话记录将无法恢复。", self.is_dark):
                self.delete_requested.emit(self.session_id)
        elif action == act_ws:
            self.save_to_ws_requested.emit(self.session_id, self.title)
        elif action == act_export:
            self.export_requested.emit(self.session_id, self.title)
        elif action == act_batch:
            self.batch_requested.emit()
        elif action == act_folder:
            import os
            os.system(f'explorer "{ROOT_DIR}"')
        elif action == act_share:
            QApplication.clipboard().setText(f"NovaDesk 任务分享：{self.title}")
            show_themed_info(self, "分享成功", "任务分享文案已成功复制到系统剪贴板！", self.is_dark)


def extract_and_remove_tool_json(text: str):
    """准确提取并移除所有嵌套花括号的工具调用 JSON，杜绝底层调试数据泄露"""
    tools_found = []
    cleaned_chars = []
    i = 0
    n = len(text)
    
    while i < n:
        if text[i] == '{':
            snippet = text[i:min(n, i + 60)]
            if any(k in snippet for k in ['"name"', '"tool"', '"tool_name"', '"function"']):
                depth = 0
                j = i
                in_str = False
                escape = False
                matched_data = None
                
                while j < n:
                    ch = text[j]
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
                                json_str = text[i:j+1]
                                try:
                                    data = json.loads(json_str)
                                    if isinstance(data, dict):
                                        t_name = data.get("name") or data.get("tool") or data.get("tool_name") or data.get("function")
                                        if t_name and isinstance(t_name, str):
                                            matched_data = data
                                except Exception:
                                    pass
                                break
                    j += 1
                
                if matched_data:
                    tools_found.append(matched_data)
                    i = j + 1
                    continue

        cleaned_chars.append(text[i])
        i += 1
        
    return "".join(cleaned_chars), tools_found


def parse_and_clean_message_text(text: str, return_thought: bool = False):
    """
    解析消息中的工具调用元数据与思考链过程，返回清洗后的纯净 Markdown 正文、工具状态元数据与思考过程
    若 return_thought 为 True: 返回 (cleaned_text, tool_info, thought_text)
    若 return_thought 为 False (兼容旧调用): 返回 (cleaned_text, tool_info)
    """
    if not text:
        return ("", None, "") if return_thought else ("", None)

    from ui.dev_mode_view import strip_emojis, clean_markdown_tables, extract_thought_process

    # 1. 优先提取大模型思维链 (<think>...</think>)，与主正文彻底隔离
    clean_src, thought_text = extract_thought_process(text)

    tool_info = None

    # 2. 匹配新规范结构化标记 :::tool_call:status:name:friendly:::
    m_tag = re.search(r':::tool_call:(running|done):([a-zA-Z0-9_-]+)(?::([^:\n]+))?:::', clean_src)
    if m_tag:
        status, t_name, friendly = m_tag.group(1), m_tag.group(2), m_tag.group(3) or ""
        friendly_name = friendly.strip() if friendly else ""
        if not friendly_name:
            try:
                from core.ai_engine import get_tool_friendly_name
                friendly_name = get_tool_friendly_name(t_name)
            except Exception:
                friendly_name = t_name.replace("_", " ").title()
        tool_info = {"tool_name": t_name, "friendly_name": friendly_name, "status": status}
    else:
        # 3. 兼容匹配历史遗留文本提示
        m_old_done = re.search(r'✅\s*\*工具[「"]?([a-zA-Z0-9_-]+)[」"]?\s*执行完毕', clean_src)
        m_old_running = re.search(r'⚙️\s*\*正在执行工具[「"]?([a-zA-Z0-9_-]+)[」"]?\.\.\.\*', clean_src)
        if m_old_done:
            t_name = m_old_done.group(1)
            try:
                from core.ai_engine import get_tool_friendly_name
                f_name = get_tool_friendly_name(t_name)
            except Exception:
                f_name = t_name.replace("_", " ").title()
            tool_info = {"tool_name": t_name, "friendly_name": f_name, "status": "done"}
        elif m_old_running:
            t_name = m_old_running.group(1)
            try:
                from core.ai_engine import get_tool_friendly_name
                f_name = get_tool_friendly_name(t_name)
            except Exception:
                f_name = t_name.replace("_", " ").title()
            tool_info = {"tool_name": t_name, "friendly_name": f_name, "status": "running"}

    # 4. 彻底移除开发模式协议标记与结构化标记
    cleaned = re.sub(r':::tool_call:[^:\n]+:[^:\n]+(?::[^:\n]+)?:::', '', clean_src)
    cleaned = re.sub(r'\[\[WORKSPACE_DIFF:[^\]]+\]\]', '', cleaned)
    cleaned = re.sub(r'\[\[WORKSPACE_EXPLORE:[^\]]+\]\]', '', cleaned)
    cleaned = re.sub(r'\[\[WORKSPACE_CMD:[^\]]+\]\]', '', cleaned)
    cleaned = re.sub(r'```(?:tool|json)?\s*\{[\s\S]*?\}\s*```', '', cleaned)
    cleaned = re.sub(r'TOOL:\s*[a-zA-Z0-9_-]+\s*\{[\s\S]*?\}', '', cleaned)
    cleaned = re.sub(r'⚙️\s*\*正在执行工具[^\n]*\*', '', cleaned)
    cleaned = re.sub(r'✅\s*\*工具[^\n]*执行完毕[^\n]*\*', '', cleaned)

    # 5. 平衡括号彻底移除内嵌的花括号工具 JSON 块
    cleaned, found_tools = extract_and_remove_tool_json(cleaned)
    if not tool_info and found_tools:
        t_data = found_tools[0]
        t_name = t_data.get("name") or t_data.get("tool") or ""
        if t_name:
            try:
                from core.ai_engine import get_tool_friendly_name
                f_name = get_tool_friendly_name(t_name)
            except Exception:
                f_name = t_name.replace("_", " ").title()
            tool_info = {"tool_name": t_name, "friendly_name": f_name, "status": "done"}

    # 6. 表格深度清洗与 Emoji 脱水
    cleaned = clean_markdown_tables(cleaned)
    cleaned = strip_emojis(cleaned)
    if thought_text:
        thought_text = strip_emojis(thought_text)

    # 7. 清理首尾与连续多余空行
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()

    if return_thought:
        return cleaned, tool_info, thought_text
    return cleaned, tool_info


class ThoughtAccordionWidget(QFrame):
    """现代化深度思考折叠卡片（对标 DeepSeek / ChatGPT 思考链展示，生成完毕后默认隐藏收起）"""
    def __init__(self, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self._thought_text = ""
        self._is_expanded = False
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("ThoughtAccordion")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 4)
        lay.setSpacing(4)

        # 头部折叠控制条 (极简低调胶囊式)
        self.header_btn = QFrame(self)
        self.header_btn.setCursor(Qt.PointingHandCursor)
        h_lay = QHBoxLayout(self.header_btn)
        h_lay.setContentsMargins(8, 4, 8, 4)
        h_lay.setSpacing(6)

        self.icon_lbl = QLabel("💭", self.header_btn)
        self.icon_lbl.setStyleSheet("font-size: 12px; background: transparent;")
        h_lay.addWidget(self.icon_lbl)

        self.title_lbl = QLabel("已深度思考 (点击展开)", self.header_btn)
        self.title_lbl.setStyleSheet(f"color: {'#a1a1aa' if self.is_dark else '#64748b'}; font-size: 11.5px; font-weight: 500; font-family: 'PingFang SC', 'Microsoft YaHei UI'; background: transparent;")
        h_lay.addWidget(self.title_lbl)

        h_lay.addStretch()

        self.arrow_lbl = QLabel("›", self.header_btn)
        self.arrow_lbl.setStyleSheet(f"color: {'#71717a' if self.is_dark else '#94a3b8'}; font-size: 13px; font-weight: bold; background: transparent;")
        h_lay.addWidget(self.arrow_lbl)

        lay.addWidget(self.header_btn)

        # 展开的内容展示区 (默认折叠隐藏，点击展开查阅)
        self.body_container = QFrame(self)
        self.body_container.hide()
        b_lay = QVBoxLayout(self.body_container)
        b_lay.setContentsMargins(8, 6, 8, 6)
        b_lay.setSpacing(0)

        self.thought_edit = QTextEdit(self.body_container)
        self.thought_edit.setReadOnly(True)
        self.thought_edit.setMaximumHeight(200)
        self.thought_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                color: {'#a1a1aa' if self.is_dark else '#64748b'};
                border: none;
                font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
                font-size: 11.5px;
                line-height: 1.45;
            }}
        """)
        b_lay.addWidget(self.thought_edit)

        lay.addWidget(self.body_container)
        self._update_style()

    def _update_style(self):
        d = self.is_dark
        border_c = "#27272a" if d else "#e2e8f0"
        bg_c = "rgba(39, 39, 42, 0.4)" if d else "rgba(241, 245, 249, 0.6)"
        body_bg = "#18181b" if d else "#f8fafc"
        self.setStyleSheet("""
            QFrame#ThoughtAccordion {
                background: transparent;
                border: none;
            }
        """)
        self.header_btn.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_c};
                border: 1px solid {border_c};
                border-radius: 6px;
            }}
            QFrame:hover {{
                background-color: {'#27272a' if d else '#e2e8f0'};
                border-color: {'#3f3f46' if d else '#cbd5e1'};
            }}
        """)
        self.body_container.setStyleSheet(f"""
            QFrame {{
                background-color: {body_bg};
                border: 1px solid {border_c};
                border-radius: 6px;
            }}
        """)

    def apply_theme(self, is_dark: bool):
        """运行时切换主题时刷新已存在的 ThoughtAccordionWidget 样式
        （之前 __init__ 一次性按 self.is_dark 写死样式，运行时切主题没刷新导致字色对比度低）"""
        self.is_dark = is_dark
        # 重新刷新 title / arrow 文字色（背景由 _update_style 决定）
        text_color = '#a1a1aa' if is_dark else '#64748b'
        arrow_color = '#71717a' if is_dark else '#94a3b8'
        try:
            self.title_lbl.setStyleSheet(
                f"color: {text_color}; font-size: 11.5px; font-weight: 500;"
                f" font-family: 'PingFang SC', 'Microsoft YaHei UI'; background: transparent;"
            )
            self.arrow_lbl.setStyleSheet(
                f"color: {arrow_color}; font-size: 13px; font-weight: bold; background: transparent;"
            )
            self.thought_edit.setStyleSheet(f"""
                QTextEdit {{
                    background-color: transparent;
                    color: {text_color};
                    border: none;
                    font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
                    font-size: 11.5px;
                    line-height: 1.45;
                }}
            """)
        except Exception:
            pass
        self._update_style()

    def set_thought(self, text: str):
        self._thought_text = (text or "").strip()
        self.thought_edit.setPlainText(self._thought_text)
        self._is_expanded = False
        self.body_container.hide()
        self.arrow_lbl.setText("›")
        self.title_lbl.setText("已深度思考 (点击展开)")

    @property
    def is_expanded(self) -> bool:
        return self._is_expanded

    def toggle_expand(self):
        self._is_expanded = not self._is_expanded
        self.body_container.setVisible(self._is_expanded)
        self.arrow_lbl.setText("▾" if self._is_expanded else "›")
        self.title_lbl.setText("已深度思考 (点击收起)" if self._is_expanded else "已深度思考 (点击展开)")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_expand()
        super().mousePressEvent(event)


class ToolStatusCapsule(QFrame):
    """现代化双主题极简工具执行胶囊卡片（拒绝 raw JSON 裸露，高质感包装）"""
    def __init__(self, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.tool_name = ""
        self.friendly_name = ""
        self.status = "done"
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("toolCapsule")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 12, 6)
        lay.setSpacing(8)

        # 状态图标
        self.icon_lbl = QLabel("⚡")
        self.icon_lbl.setFont(QFont("Segoe UI Emoji", 10))
        self.icon_lbl.setStyleSheet("background: transparent;")
        lay.addWidget(self.icon_lbl)

        # 标题
        self.title_lbl = QLabel("已调用工具")
        self.title_lbl.setFont(QFont("PingFang SC", 9) if sys.platform == "darwin" else QFont("Microsoft YaHei UI", 9))
        self.title_lbl.setStyleSheet("background: transparent;")
        lay.addWidget(self.title_lbl)

        lay.addStretch()

        # 右侧状态徽章
        self.badge_lbl = QLabel("✓ 数据已就绪")
        self.badge_lbl.setFont(QFont("Microsoft YaHei UI", 8, QFont.Bold))
        self.badge_lbl.setStyleSheet("background: transparent;")
        lay.addWidget(self.badge_lbl)

        self._apply_style()

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self._apply_style()

    def _apply_style(self):
        d = self.is_dark
        if self.status == "running":
            border_color = "rgba(99, 102, 241, 0.45)" if d else "#c7d2fe"
            bg_color = "rgba(99, 102, 241, 0.12)" if d else "#eef2ff"
            text_color = "#a5b4fc" if d else "#4338ca"
            badge_color = "#818cf8" if d else "#4f46e5"
            badge_text = "⏳ 执行中..."
            icon_char = "⚙️"
        else:
            border_color = "rgba(16, 185, 129, 0.3)" if d else "#bbf7d0"
            bg_color = "rgba(16, 185, 129, 0.08)" if d else "#f0fdf4"
            text_color = "#d1d5db" if d else "#334155"
            badge_color = "#34d399" if d else "#059669"
            badge_text = "✓ 数据已就绪"
            icon_char = "⚡"

        self.setStyleSheet(f"""
            QFrame#toolCapsule {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
        """)
        self.icon_lbl.setText(icon_char)
        self.title_lbl.setStyleSheet(f"color: {text_color}; background: transparent; font-size: 12px; font-weight: 500;")
        self.badge_lbl.setText(badge_text)
        self.badge_lbl.setStyleSheet(f"color: {badge_color}; background: transparent; font-size: 11px;")

    def set_tool_info(self, friendly_name: str, tool_name: str = "", status: str = "done"):
        self.friendly_name = friendly_name or tool_name or "本地工具"
        self.tool_name = tool_name
        self.status = status

        if status == "running":
            display_title = f"正在调用工具 · {self.friendly_name}"
        else:
            display_title = f"已调用工具 · {self.friendly_name}"

        if tool_name and tool_name != self.friendly_name and "、" not in self.friendly_name:
            display_title += f" ({tool_name})"

# ─────────────────────────── 实施方案确认交互卡片 (PlanActionCard) ───────────────────────────

# ─────────────────────────── 实施方案顶栏操作条 (PlanDocumentBar) ───────────────────────────

class PlanDocumentBar(QFrame):
    """实施方案交互导航条 (中文版 Implementation Plan Action Bar)
    复刻高端 AI 工作台方案条，全中文呈现：
    - 左侧：📋 任务实施方案  [会话临时草案 · 刚刚]
    - 右侧操作：
      1. 【📋 复制】：一键复制 Markdown 方案正文到剪贴板；
      2. 【📥 下载】：弹出保存路径选择器，将方案下载导出为本地 .md 文件；
      3. 【👁️ 审阅 ∨ / 收起 ∧】：折叠或展开下方的 Markdown 详细方案内容；
      4. 【🚀 立即执行 (Proceed)】：批准方案并安全加入执行队列。
    """
    proceed_clicked = pyqtSignal(str)
    review_toggled = pyqtSignal(bool) # True 为展开，False 为收起

    def __init__(self, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.plan_text = ""
        self.is_proceeded = False
        self.is_expanded = True
        self.created_time = datetime.now()
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("PlanDocumentBar")
        self.setFixedHeight(40)
        bar_lay = QHBoxLayout(self)
        bar_lay.setContentsMargins(12, 0, 12, 0)
        bar_lay.setSpacing(10)

        # 左侧图标 + 标题 + 提示标签
        self.icon_lbl = QLabel("📋")
        self.icon_lbl.setFont(QFont("Segoe UI Emoji", 12))
        bar_lay.addWidget(self.icon_lbl)

        self.title_lbl = QLabel("任务实施方案")
        self.title_lbl.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        bar_lay.addWidget(self.title_lbl)

        self.time_lbl = QLabel("会话临时草案 · 刚刚")
        self.time_lbl.setFont(QFont("Microsoft YaHei UI", 9))
        bar_lay.addWidget(self.time_lbl)

        bar_lay.addStretch()

        # 右侧操作按钮组
        # 1. 复制按钮
        self.copy_btn = QPushButton("📋 复制")
        self.copy_btn.setFixedHeight(26)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setToolTip("复制方案 Markdown 纯文本到剪贴板")
        self.copy_btn.clicked.connect(self._do_copy)
        bar_lay.addWidget(self.copy_btn)

        # 2. 下载导出按钮
        self.download_btn = QPushButton("📥 下载")
        self.download_btn.setFixedHeight(26)
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setToolTip("选择路径下载保存为 .md 文档")
        self.download_btn.clicked.connect(self._do_download)
        bar_lay.addWidget(self.download_btn)

        # 2.5 独立窗口预览按钮
        self.preview_btn = QPushButton("📖 独立预览")
        self.preview_btn.setFixedHeight(26)
        self.preview_btn.setCursor(Qt.PointingHandCursor)
        self.preview_btn.setToolTip("在新窗口中独立预览并审阅完整实施方案")
        self.preview_btn.clicked.connect(self._do_preview)
        bar_lay.addWidget(self.preview_btn)

        # 3. 审阅 / 折叠按钮
        self.review_btn = QPushButton("收起 ∧")
        self.review_btn.setFixedHeight(26)
        self.review_btn.setCursor(Qt.PointingHandCursor)
        self.review_btn.setToolTip("折叠或展开方案详细正文")
        self.review_btn.clicked.connect(self._toggle_review)
        bar_lay.addWidget(self.review_btn)

        # 4. 立即执行 (Proceed) 按钮
        self.proceed_btn = QPushButton("🚀 立即执行 (Proceed)")
        self.proceed_btn.setFixedHeight(26)
        self.proceed_btn.setCursor(Qt.PointingHandCursor)
        self.proceed_btn.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        self.proceed_btn.clicked.connect(self._on_proceed)
        bar_lay.addWidget(self.proceed_btn)

        self._apply_style()

    def _apply_style(self):
        d = self.is_dark
        bar_bg = "#222228" if d else "#f1f5f9"
        bar_border = "#33333f" if d else "#cbd5e1"
        text_color = "#f4f4f5" if d else "#0f172a"
        time_color = "#71717a" if d else "#94a3b8"

        self.setStyleSheet(f"""
            QFrame#PlanDocumentBar {{
                background-color: {bar_bg};
                border: 1px solid {bar_border};
                border-left: 3.5px solid #2563eb;
                border-radius: 7px;
            }}
        """)
        self.title_lbl.setStyleSheet(f"color: {text_color}; background: transparent;")
        self.time_lbl.setStyleSheet(f"color: {time_color}; background: transparent;")

        btn_bg = "#2c2c36" if d else "#ffffff"
        btn_border = "#3e3e4e" if d else "#cbd5e1"
        btn_color = "#e4e4e7" if d else "#334155"

        common_btn_qss = f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_color};
                border: 1px solid {btn_border};
                border-radius: 5px;
                padding: 0 9px;
                font-size: 11px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{
                background-color: {'#3e3e4e' if d else '#e2e8f0'};
                color: {'#ffffff' if d else '#0f172a'};
            }}
        """
        self.copy_btn.setStyleSheet(common_btn_qss)
        self.download_btn.setStyleSheet(common_btn_qss)
        self.preview_btn.setStyleSheet(common_btn_qss)
        self.review_btn.setStyleSheet(common_btn_qss)

        if self.is_proceeded:
            self.proceed_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'#27272a' if d else '#e2e8f0'};
                    color: {'#71717a' if d else '#94a3b8'};
                    border: 1px solid {'#3f3f46' if d else '#cbd5e1'};
                    border-radius: 5px;
                    padding: 0 11px;
                    font-size: 11px;
                }}
            """)
        else:
            self.proceed_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2563eb;
                    color: #ffffff;
                    border: none;
                    border-radius: 5px;
                    padding: 0 11px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #1d4ed8;
                }}
                QPushButton:pressed {{
                    background-color: #1e40af;
                }}
            """)

    def set_plan_text(self, text: str):
        self.plan_text = text

    def set_dark(self, is_dark: bool):
        self.is_dark = is_dark
        self._apply_style()

    def _do_copy(self):
        txt = self.plan_text.strip()
        if txt:
            QApplication.clipboard().setText(txt)
            self.copy_btn.setText("✅ 已复制")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋 复制"))

    def _do_download(self):
        txt = self.plan_text.strip()
        if not txt:
            return
        default_name = f"实施方案_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择路径下载保存实施方案文档",
            default_name,
            "Markdown 文档 (*.md);;所有文件 (*.*)"
        )
        if file_path:
            try:
                Path(file_path).write_text(txt, encoding="utf-8")
                self.download_btn.setText("✅ 已下载")
                QTimer.singleShot(2000, lambda: self.download_btn.setText("📥 下载"))
            except Exception as e:
                show_themed_warning(self, "下载失败", f"无法写入文件：{e}", self.is_dark)

    def _do_preview(self):
        try:
            win = PlanDocumentPreviewWindow(self.plan_text, is_dark=self.is_dark, parent=self.window())
            win.proceed_clicked.connect(self._on_proceed)
            win.show()
            win.raise_()
            win.activateWindow()
            self._preview_win = win
        except Exception as e:
            print("打开方案预览窗口异常:", e)

    def _toggle_review(self):
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.review_btn.setText("收起 ∧")
        else:
            self.review_btn.setText("审阅 ∨")
        self.review_toggled.emit(self.is_expanded)

    def _on_proceed(self):
        if self.is_proceeded:
            return
        self.is_proceeded = True
        self.proceed_btn.setEnabled(False)
        self.proceed_btn.setText("✅ 已确认执行")
        self.time_lbl.setText("已批准 · 执行中")
        self._apply_style()
        self.proceed_clicked.emit(self.plan_text)

    def update_status(self, text: str, is_completed: bool = False):
        if is_completed:
            self.time_lbl.setText("✅ 方案已落地完成")
        else:
            self.time_lbl.setText(text)


class PlanActionCard(QFrame):
    """实施方案确认交互卡片 (Proceed Plan Action Card)
    呈现于 AI 输出的计划方案下方，提供：
    1. 【🚀 接收并立即执行 (Proceed)】粗体高质感按钮；
    2. 【✏️ 补充修改意见】幽灵微边框按钮；
    3. 状态提示栏（显示待确认、已入排队队列、正在执行中、已完成等）。
    """
    proceed_clicked = pyqtSignal(str) # 发送 plan 文本
    feedback_clicked = pyqtSignal()

    def __init__(self, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.plan_text = ""
        self.is_proceeded = False
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("PlanActionCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        # 头部行：图标 + 标题 + 提示徽章
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self.title_icon = QLabel("📋")
        self.title_icon.setFont(QFont("Segoe UI Emoji", 13))
        header_row.addWidget(self.title_icon)

        self.title_lbl = QLabel("实施方案已就绪 · 请审阅")
        self.title_lbl.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        header_row.addWidget(self.title_lbl)

        header_row.addStretch()

        self.badge_lbl = QLabel("等待确认")
        self.badge_lbl.setFont(QFont("Microsoft YaHei UI", 9))
        header_row.addWidget(self.badge_lbl)
        lay.addLayout(header_row)

        # 描述说明文字
        self.desc_lbl = QLabel("AI 已为您制定结构化落地规划。点击「接收并立即执行」将正式进入分步编写代码与交付阶段；如有调整需要，可点击补充修改意见。")
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setFont(QFont("Microsoft YaHei UI", 9))
        lay.addWidget(self.desc_lbl)

        # 按钮与状态行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.proceed_btn = QPushButton("🚀 接收并立即执行 (Proceed)")
        self.proceed_btn.setFixedHeight(32)
        self.proceed_btn.setCursor(Qt.PointingHandCursor)
        self.proceed_btn.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        self.proceed_btn.clicked.connect(self._on_proceed)
        btn_row.addWidget(self.proceed_btn)

        self.feedback_btn = QPushButton("✏️ 补充修改意见")
        self.feedback_btn.setFixedHeight(32)
        self.feedback_btn.setCursor(Qt.PointingHandCursor)
        self.feedback_btn.setFont(QFont("Microsoft YaHei UI", 9))
        self.feedback_btn.clicked.connect(self.feedback_clicked.emit)
        btn_row.addWidget(self.feedback_btn)

        self.preview_btn = QPushButton("📖 独立窗口预览")
        self.preview_btn.setFixedHeight(32)
        self.preview_btn.setCursor(Qt.PointingHandCursor)
        self.preview_btn.setFont(QFont("Microsoft YaHei UI", 9))
        self.preview_btn.setToolTip("在新窗口中独立预览并审阅完整方案文档")
        self.preview_btn.clicked.connect(self._do_preview)
        btn_row.addWidget(self.preview_btn)

        btn_row.addStretch()
        lay.addLayout(btn_row)

        # 状态反馈标签 (排队中/执行中/已完成)
        self.status_lbl = QLabel("")
        self.status_lbl.setFont(QFont("Microsoft YaHei UI", 9))
        self.status_lbl.setWordWrap(True)
        self.status_lbl.hide()
        lay.addWidget(self.status_lbl)

        self._apply_style()

    def _apply_style(self):
        d = self.is_dark
        card_bg = "#18181b" if d else "#f8fafc"
        card_border = "#2563eb" if d else "#3b82f6"
        text_color = "#f4f4f5" if d else "#0f172a"
        desc_color = "#a1a1aa" if d else "#64748b"

        self.setStyleSheet(f"""
            QFrame#PlanActionCard {{
                background-color: {card_bg};
                border: 1.5px solid {card_border};
                border-left: 4px solid {card_border};
                border-radius: 8px;
            }}
        """)
        self.title_lbl.setStyleSheet(f"color: {text_color}; background: transparent;")
        self.desc_lbl.setStyleSheet(f"color: {desc_color}; background: transparent; line-height: 1.4;")
        self.badge_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {'#1e3a8a' if d else '#dbeafe'};
                color: {'#60a5fa' if d else '#1d4ed8'};
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
        """)

        if self.is_proceeded:
            self.proceed_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'#27272a' if d else '#e2e8f0'};
                    color: {'#71717a' if d else '#94a3b8'};
                    border: 1px solid {'#3f3f46' if d else '#cbd5e1'};
                    border-radius: 6px;
                    padding: 0 14px;
                }}
            """)
        else:
            self.proceed_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2563eb;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 0 14px;
                }}
                QPushButton:hover {{
                    background-color: #1d4ed8;
                }}
                QPushButton:pressed {{
                    background-color: #1e40af;
                }}
            """)

        self.feedback_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#27272a' if d else '#f1f5f9'};
                color: {'#e4e4e7' if d else '#334155'};
                border: 1px solid {'#3f3f46' if d else '#cbd5e1'};
                border-radius: 6px;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background-color: {'#3f3f46' if d else '#e2e8f0'};
                color: {'#ffffff' if d else '#0f172a'};
            }}
        """)

        if hasattr(self, 'preview_btn'):
            self.preview_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'#27272a' if d else '#f1f5f9'};
                    color: {'#e4e4e7' if d else '#334155'};
                    border: 1px solid {'#3f3f46' if d else '#cbd5e1'};
                    border-radius: 6px;
                    padding: 0 12px;
                    font-size: 12px;
                    font-family: 'Microsoft YaHei UI';
                }}
                QPushButton:hover {{
                    background-color: {'#3f3f46' if d else '#e2e8f0'};
                    color: {'#ffffff' if d else '#0f172a'};
                }}
            """)

    def _do_preview(self):
        try:
            win = PlanDocumentPreviewWindow(self.plan_text, is_dark=self.is_dark, parent=self.window())
            win.proceed_clicked.connect(self._on_proceed)
            win.show()
            win.raise_()
            win.activateWindow()
            self._preview_win = win
        except Exception as e:
            print("打开方案预览窗口异常:", e)

    def set_plan_text(self, text: str):
        self.plan_text = text

    def set_dark(self, is_dark: bool):
        self.is_dark = is_dark
        self._apply_style()

    def _on_proceed(self):
        if self.is_proceeded:
            return
        self.is_proceeded = True
        self.proceed_btn.setEnabled(False)
        self.proceed_btn.setText("✅ 已接收并批准")
        self.feedback_btn.setEnabled(False)
        self.badge_lbl.setText("已接收")
        self.badge_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {'#064e3b' if self.is_dark else '#d1fae5'};
                color: {'#34d399' if self.is_dark else '#047857'};
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
        """)
        self._apply_style()
        self.proceed_clicked.emit(self.plan_text)

    def update_status_message(self, msg: str, is_queued: bool = False, is_completed: bool = False):
        self.status_lbl.show()
        if is_completed:
            self.badge_lbl.setText("已完成")
            self.badge_lbl.setStyleSheet(f"""
                QLabel {{
                    background-color: {'#064e3b' if self.is_dark else '#d1fae5'};
                    color: {'#34d399' if self.is_dark else '#047857'};
                    border-radius: 10px; padding: 2px 8px; font-size: 11px; font-weight: 500;
                }}
            """)
            self.status_lbl.setStyleSheet("color: #10b981; font-weight: 500;")
        elif is_queued:
            self.badge_lbl.setText("队列排队中")
            self.badge_lbl.setStyleSheet(f"""
                QLabel {{
                    background-color: {'#78350f' if self.is_dark else '#fef3c7'};
                    color: {'#fbbf24' if self.is_dark else '#d97706'};
                    border-radius: 10px; padding: 2px 8px; font-size: 11px; font-weight: 500;
                }}
            """)
            self.status_lbl.setStyleSheet("color: #f59e0b; font-weight: 500;")
        else:
            self.status_lbl.setStyleSheet(f"color: {'#60a5fa' if self.is_dark else '#2563eb'}; font-weight: 500;")
        self.status_lbl.setText(msg)


# ─────────────────────────── 极客代码卡片与智能混排 (CodeBlockCard & MessageContentArea) ───────────────────────────

class CodeBlockCard(QFrame):
    """
    极客质感代码/指令卡片 (CodeBlockCard):
    - 顶部工具栏: 语言指示标签 (如 java, c, python, bash 等) + 一键复制代码按钮 (带 Checkmark 绿色动效反馈)
    - 代码区域: One-Dark 丰富语法高亮，等宽字体，支持水平滚动条无损显示长代码，长内容智能截断垂直滚动
    - 适配暗黑/明亮双主题极客卡片
    """
    def __init__(self, lang: str = "", code: str = "", is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.lang = (lang or "").strip().lower() or "code"
        self.code = code or ""
        self.is_dark = is_dark
        self.setObjectName("CodeBlockCard")
        self._init_ui()
        self.set_code(self.lang, self.code)

    def _init_ui(self):
        self.setMinimumWidth(360)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 1. 顶部操作栏
        self.header = QWidget(self)
        self.header.setFixedHeight(34)
        h_lay = QHBoxLayout(self.header)
        h_lay.setContentsMargins(14, 0, 8, 0)
        h_lay.setSpacing(6)

        # 语言指示器
        self.lang_lbl = QLabel(self.lang, self.header)
        self.lang_lbl.setObjectName("CodeLangLabel")
        f = QFont("JetBrains Mono", 9)
        f.setStyleHint(QFont.Monospace)
        self.lang_lbl.setFont(f)
        h_lay.addWidget(self.lang_lbl)
        h_lay.addStretch()

        # 复制代码按钮
        self.copy_btn = QPushButton(self.header)
        self.copy_btn.setObjectName("CodeCopyBtn")
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setFixedSize(28, 26)
        self.copy_btn.setToolTip("复制代码")
        self._reset_copy_icon()
        self.copy_btn.clicked.connect(self._do_copy)
        h_lay.addWidget(self.copy_btn)

        lay.addWidget(self.header)

        # 2. 代码正文展示区域 (QTextEdit)
        self.code_edit = QTextEdit(self)
        self.code_edit.setReadOnly(True)
        self.code_edit.setLineWrapMode(QTextEdit.NoWrap)
        self.code_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.code_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.code_edit.setFrameShape(QFrame.NoFrame)
        self.code_edit.document().setDocumentMargin(12)

        lay.addWidget(self.code_edit)
        self._apply_style()

    def _reset_copy_icon(self):
        ic_color = "#94a3b8" if self.is_dark else "#64748b"
        self.copy_btn.setIcon(load_ui_icon("copy", ic_color, 14))
        self.copy_btn.setIconSize(QSize(14, 14))
        self.copy_btn.setToolTip("复制代码")

    def _do_copy(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.code)
        # 绿色勾勾反馈
        self.copy_btn.setIcon(load_ui_icon("check", "#10b981", 14))
        self.copy_btn.setIconSize(QSize(14, 14))
        self.copy_btn.setToolTip("已复制到剪贴板")
        QTimer.singleShot(1600, self._reset_copy_icon)

    def set_dark(self, is_dark: bool):
        self.is_dark = is_dark
        self._apply_style()
        self.set_code(self.lang, self.code)

    def _apply_style(self):
        d = self.is_dark
        bg = "#16161a" if d else "#1e1e24"
        border = "#27272a" if d else "#334155"
        header_bg = "#1b1b20" if d else "#24242c"
        lang_color = "#94a3b8" if d else "#a1a1aa"
        btn_hover = "#27272f" if d else "#32323d"

        self.setStyleSheet(f"""
            QFrame#CodeBlockCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QWidget {{
                background-color: transparent;
            }}
            QLabel#CodeLangLabel {{
                color: {lang_color};
                font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
            QPushButton#CodeCopyBtn {{
                background-color: transparent;
                border: none;
                border-radius: 5px;
                padding: 4px;
            }}
            QPushButton#CodeCopyBtn:hover {{
                background-color: {btn_hover};
            }}
        """)
        self.header.setStyleSheet(f"""
            background-color: {header_bg};
            border-top-left-radius: 7px;
            border-top-right-radius: 7px;
            border-bottom: 1px solid {border};
        """)
        self.code_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg};
                border: none;
                border-bottom-left-radius: 7px;
                border-bottom-right-radius: 7px;
                color: #f1f5f9;
                font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, 'Microsoft YaHei UI', monospace;
                font-size: 13px;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
            }}
            QScrollBar:horizontal {{
                height: 5px;
                background: transparent;
                margin: 0px 6px 4px 6px;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: #3f3f46;
                border-radius: 2px;
                min-width: 24px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: #52525b;
            }}
            QScrollBar:vertical {{
                width: 5px;
                background: transparent;
                margin: 4px 0px 4px 0px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: #3f3f46;
                border-radius: 2px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #52525b;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                width: 0px;
                height: 0px;
                background: none;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

    def set_code(self, lang: str, code: str):
        self.lang = (lang or "").strip().lower() or "code"
        self.code = code or ""
        self.lang_lbl.setText(self.lang)

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
        lookup_lang = LANG_ALIASES.get(self.lang, self.lang)

        highlighted = ""
        if HAS_PYGMENTS:
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
            highlighted = pygments.highlight(code, lexer, formatter)
            highlighted = highlighted.replace('line-height: 125%', 'line-height: 145%')
            highlighted = highlighted.replace('background: #282C34', 'background: transparent').replace('background: #272822', 'background: transparent')
        else:
            highlighted = f"<pre>{html.escape(code)}</pre>"

        wrapped_html = f"""
        <html>
        <head>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: transparent;
                font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, 'Microsoft YaHei UI', monospace;
                font-size: 13px;
            }}
            pre {{
                margin: 0;
                padding: 0;
                line-height: 145%;
                font-family: inherit;
            }}
            span {{
                font-style: normal !important;
            }}
        </style>
        </head>
        <body>{highlighted}</body>
        </html>
        """
        self.code_edit.setHtml(wrapped_html)

        # 动态自适应高度计算 (支持长代码智能内嵌垂直滚动，防止撑爆界面)
        line_count = len(code.splitlines()) or 1
        line_height = 20
        content_height = line_count * line_height + 24
        max_content_height = 650
        if content_height > max_content_height:
            self.code_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            actual_content_height = max_content_height
        else:
            self.code_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            actual_content_height = content_height

        total_height = 34 + actual_content_height
        self.setFixedHeight(total_height)
        self.code_edit.setFixedHeight(actual_content_height)


class MessageContentArea(QWidget):
    """
    智能混排消息展示区：
    - 普通文本 / 标题 / 列表通过 Markdown + 行内胶囊标签渲染
    - 代码块 / 指令块自动解析并嵌入 CodeBlockCard 卡片
    - 高性能复用，支持流式 60fps 动态渲染
    """
    def __init__(self, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(10)
        self._content_widgets = []
        self._raw_text = ""

    def set_dark(self, is_dark: bool):
        self.is_dark = is_dark
        for w in self._content_widgets:
            if isinstance(w, CodeBlockCard):
                w.set_dark(is_dark)
            elif isinstance(w, QLabel):
                w.setStyleSheet(self._label_style())
        if self._raw_text:
            self.set_content(self._raw_text)

    def _label_style(self) -> str:
        color = '#e4e4e7' if self.is_dark else '#1f2937'
        return f"""
            QLabel {{
                background-color: transparent;
                color: {color};
                padding: 2px 0px;
                font-size: 14px;
                line-height: 1.65;
                letter-spacing: 0.2px;
                font-family: 'PingFang SC', 'Microsoft YaHei UI', 'Source Han Sans CN', -apple-system, sans-serif;
            }}
        """

    def set_content(self, text: str):
        self._raw_text = text
        if not text:
            while self._content_widgets:
                w = self._content_widgets.pop()
                self.lay.removeWidget(w)
                w.deleteLater()
            return

        segments = self._parse_segments(text)
        for i, seg in enumerate(segments):
            stype = seg['type']
            if i < len(self._content_widgets):
                curr_w = self._content_widgets[i]
                if stype == 'text' and isinstance(curr_w, QLabel):
                    curr_w.setText(self._format_markdown_text(seg['content']))
                    continue
                elif stype == 'code' and isinstance(curr_w, CodeBlockCard):
                    curr_w.set_code(seg.get('lang', ''), seg.get('code', ''))
                    continue
                else:
                    self.lay.removeWidget(curr_w)
                    curr_w.deleteLater()
                    new_w = self._create_segment_widget(seg)
                    self._content_widgets[i] = new_w
                    self.lay.insertWidget(i, new_w)
            else:
                new_w = self._create_segment_widget(seg)
                self._content_widgets.append(new_w)
                self.lay.addWidget(new_w)

        while len(self._content_widgets) > len(segments):
            w = self._content_widgets.pop()
            self.lay.removeWidget(w)
            w.deleteLater()

    def _parse_segments(self, text: str):
        segments = []
        pattern = re.compile(r'```([a-zA-Z0-9_\+#\.\-]*)\r?\n(.*?)```', re.DOTALL)
        last = 0
        for m in pattern.finditer(text):
            if m.start() > last:
                t = text[last:m.start()].strip('\r\n')
                if t:
                    segments.append({'type': 'text', 'content': t})
            segments.append({'type': 'code', 'lang': m.group(1), 'code': m.group(2).rstrip('\r\n')})
            last = m.end()

        tail = text[last:]
        if tail:
            unclosed_m = re.search(r'```([a-zA-Z0-9_\+#\.\-]*)\r?\n?(.*)$', tail, re.DOTALL)
            if unclosed_m:
                before = tail[:unclosed_m.start()].strip('\r\n')
                if before:
                    segments.append({'type': 'text', 'content': before})
                code_body = unclosed_m.group(2)
                segments.append({'type': 'code', 'lang': unclosed_m.group(1), 'code': code_body.rstrip('\r\n')})
            else:
                t = tail.strip('\r\n')
                if t:
                    segments.append({'type': 'text', 'content': t})

        if not segments and text:
            segments = [{'type': 'text', 'content': text}]

        return segments

    def _create_segment_widget(self, seg):
        if seg['type'] == 'code':
            return CodeBlockCard(seg.get('lang', ''), seg.get('code', ''), is_dark=self.is_dark, parent=self)
        else:
            lbl = QLabel(self)
            lbl.setTextFormat(Qt.RichText)
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
            lbl.setOpenExternalLinks(True)
            lbl.setStyleSheet(self._label_style())
            lbl.setText(self._format_markdown_text(seg['content']))
            return lbl

    def _format_markdown_text(self, text: str) -> str:
        from ui.dev_mode_view import clean_markdown_tables
        clean_t = clean_markdown_tables(text)

        if HAS_MARKDOWN:
            try:
                raw_html = markdown.markdown(clean_t, extensions=['tables'])
            except Exception:
                raw_html = html.escape(clean_t).replace('\n', '<br>')
        else:
            raw_html = html.escape(clean_t).replace('\n', '<br>')

        bg_col = "#27272a" if self.is_dark else "#e2e8f0"
        txt_col = "#f1f5f9" if self.is_dark else "#0f172a"
        border_col = "#383e4a" if self.is_dark else "#d0d7de"
        th_bg = "#21262d" if self.is_dark else "#f6f8fa"
        th_txt = "#e6edf3" if self.is_dark else "#1f2328"
        td_txt = "#c9d1d9" if self.is_dark else "#24292f"

        table_style = (
            f'style="border-collapse: collapse; width: 100%; margin: 8px 0; '
            f'border: 1px solid {border_col}; border-radius: 6px; overflow: hidden;"'
        )
        th_style = (
            f'style="background-color: {th_bg}; color: {th_txt}; '
            f'padding: 8px 14px; border: 1px solid {border_col}; font-weight: 600; text-align: left; font-size: 13px;"'
        )
        td_style = (
            f'style="padding: 8px 14px; border: 1px solid {border_col}; '
            f'color: {td_txt}; font-size: 13px; line-height: 1.5;"'
        )

        styled_html = re.sub(r'<table(\s*[^>]*)>', f'<table {table_style}>', raw_html)
        styled_html = re.sub(r'<th(\s*[^>]*)>', f'<th {th_style}>', styled_html)
        styled_html = re.sub(r'<td(\s*[^>]*)>', f'<td {td_style}>', styled_html)

        def code_replacer(match):
            inner = match.group(1)
            return (
                f'<span style="background-color: {bg_col}; color: {txt_col}; '
                f'border: 1px solid {border_col}; border-radius: 4px; padding: 2px 6px; '
                f'font-family: \'JetBrains Mono\', Consolas, monospace; font-size: 12.5px;">&nbsp;{inner}&nbsp;</span>'
            )

        styled_html = re.sub(r'<code>(.*?)</code>', code_replacer, styled_html)
        return styled_html


# ─────────────────────────── 实施方案独立全屏/大窗预览 (PlanDocumentPreviewWindow) ───────────────────────────

class PlanDocumentPreviewWindow(QDialog):
    """
    实施方案独立窗口预览 (Non-Modal Document Preview Window)
    - 仿 Antigravity IDE 独立文档审查窗口：顶部工具栏 + 完整 Markdown 方案正文
    - 支持一键导出 .md 文件、一键复制代码、一键批准执行 (Proceed)
    - 支持暗黑/明亮主题自适应，独立非模态窗口
    """
    proceed_clicked = pyqtSignal(str)

    def __init__(self, plan_text: str, is_dark: bool = True, parent=None):
        super().__init__(parent, Qt.Window)
        self.plan_text = plan_text
        self.is_dark = is_dark
        self.is_proceeded = False
        self.setWindowTitle("📋 任务实施方案预览 (Implementation Plan)")
        self.resize(920, 680)
        self.setMinimumSize(720, 480)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self._init_ui()

    def _init_ui(self):
        d = self.is_dark
        bg_col = "#18181b" if d else "#f8fafc"
        self.setStyleSheet(f"QDialog {{ background-color: {bg_col}; }}")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # 1. 顶部操作导航栏
        top_bar = QFrame(self)
        top_bar.setFixedHeight(56)
        top_bar_bg = "#202026" if d else "#ffffff"
        top_bar_border = "#2e2e38" if d else "#e2e8f0"
        top_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {top_bar_bg};
                border-bottom: 1px solid {top_bar_border};
            }}
        """)
        top_lay = QHBoxLayout(top_bar)
        top_lay.setContentsMargins(18, 0, 18, 0)
        top_lay.setSpacing(12)

        # 标题与元数据
        icon_lbl = QLabel("📋", top_bar)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 14))
        top_lay.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        title_vbox.setContentsMargins(0, 8, 0, 8)

        main_title = QLabel("任务实施方案文档", top_bar)
        main_title.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        main_title.setStyleSheet(f"color: {'#f4f4f5' if d else '#0f172a'}; background: transparent;")
        title_vbox.addWidget(main_title)

        words_cnt = len(self.plan_text)
        sub_title = QLabel(f"会话临时草案 · 共 {words_cnt} 字 · 支持独立对比与审阅", top_bar)
        sub_title.setFont(QFont("Microsoft YaHei UI", 8))
        sub_title.setStyleSheet(f"color: {'#a1a1aa' if d else '#64748b'}; background: transparent;")
        title_vbox.addWidget(sub_title)
        top_lay.addLayout(title_vbox)

        top_lay.addStretch()

        # 操作按钮样式
        btn_bg = "#2c2c36" if d else "#f1f5f9"
        btn_border = "#3e3e4e" if d else "#cbd5e1"
        btn_fg = "#e4e4e7" if d else "#334155"

        btn_style = f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_fg};
                border: 1px solid {btn_border};
                border-radius: 6px;
                padding: 0 12px;
                height: 30px;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{
                background-color: {'#3e3e4e' if d else '#e2e8f0'};
                color: {'#ffffff' if d else '#0f172a'};
            }}
        """

        # 复制按钮
        self.copy_btn = QPushButton("📋 复制全文", top_bar)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setStyleSheet(btn_style)
        self.copy_btn.clicked.connect(self._do_copy)
        top_lay.addWidget(self.copy_btn)

        # 导出按钮
        self.export_btn = QPushButton("📥 导出 Markdown", top_bar)
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setStyleSheet(btn_style)
        self.export_btn.clicked.connect(self._do_export)
        top_lay.addWidget(self.export_btn)

        # 批准执行按钮
        self.proceed_btn = QPushButton("🚀 批准执行 (Proceed)", top_bar)
        self.proceed_btn.setCursor(Qt.PointingHandCursor)
        self.proceed_btn.setFixedHeight(30)
        self.proceed_btn.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        self.proceed_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:pressed { background-color: #1e40af; }
        """)
        self.proceed_btn.clicked.connect(self._on_proceed)
        top_lay.addWidget(self.proceed_btn)

        # 关闭按钮
        close_btn = QPushButton("✖️ 关闭", top_bar)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(btn_style)
        close_btn.clicked.connect(self.close)
        top_lay.addWidget(close_btn)

        main_lay.addWidget(top_bar)

        # 2. 居中可滚动方案内容区
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet(f"QScrollArea {{ background-color: {bg_col}; border: none; }}")

        container = QWidget()
        container.setStyleSheet(f"background-color: {bg_col};")
        cnt_lay = QVBoxLayout(container)
        cnt_lay.setContentsMargins(32, 24, 32, 32)
        cnt_lay.setSpacing(12)

        self.content_area = MessageContentArea(is_dark=self.is_dark, parent=container)
        self.content_area.set_content(self.plan_text)
        cnt_lay.addWidget(self.content_area)
        cnt_lay.addStretch()

        scroll_area.setWidget(container)
        main_lay.addWidget(scroll_area, 1)

        # 3. 底部微提示栏
        bottom_bar = QFrame(self)
        bottom_bar.setFixedHeight(32)
        bottom_bar_bg = "#1f1f24" if d else "#f1f5f9"
        bottom_bar.setStyleSheet(f"QFrame {{ background-color: {bottom_bar_bg}; border-top: 1px solid {top_bar_border}; }}")
        bot_lay = QHBoxLayout(bottom_bar)
        bot_lay.setContentsMargins(18, 0, 18, 0)
        tip_lbl = QLabel("💡 提示：本方案可随时在对话中微调或补充；点击「批准并立即执行」后大模型将自动分步推进实施。", bottom_bar)
        tip_lbl.setFont(QFont("Microsoft YaHei UI", 8))
        tip_lbl.setStyleSheet(f"color: {'#71717a' if d else '#94a3b8'}; background: transparent;")
        bot_lay.addWidget(tip_lbl)
        bot_lay.addStretch()
        main_lay.addWidget(bottom_bar)

    def _do_copy(self):
        txt = self.plan_text.strip()
        if txt:
            QApplication.clipboard().setText(txt)
            self.copy_btn.setText("✅ 已复制全文")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋 复制全文"))

    def _do_export(self):
        txt = self.plan_text.strip()
        if not txt:
            return
        default_name = f"实施方案_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出实施方案 Markdown 文档",
            default_name,
            "Markdown 文档 (*.md);;所有文件 (*.*)"
        )
        if file_path:
            try:
                Path(file_path).write_text(txt, encoding="utf-8")
                self.export_btn.setText("✅ 已导出")
                QTimer.singleShot(2000, lambda: self.export_btn.setText("📥 导出 Markdown"))
            except Exception as e:
                show_themed_warning(self, "导出失败", f"无法写入文件：{e}", self.is_dark)

    def _on_proceed(self):
        if self.is_proceeded:
            return
        self.is_proceeded = True
        self.proceed_btn.setEnabled(False)
        self.proceed_btn.setText("✅ 已批准执行")
        self.proceed_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
            }
        """)
        self.proceed_clicked.emit(self.plan_text)


# ─────────────────────────── 代码变动红绿对比审查窗口 (CodeDiffPreviewWindow) ───────────────────────────

class CodeDiffPreviewWindow(QDialog):
    """
    代码开发差异对比审查窗口 (Code Diff Preview Window)
    - 仿 Antigravity IDE 代码审阅开发模式
    - 逐行高精比对修改前 vs 修改后差异 (红绿色块对比：删除为红、新增为绿)
    - 提供 [✅ 接收变更] 与 [❌ 还原撤回 (Revert)] 以及 [📂 打开所在目录]
    - 支持暗黑/明亮主题，独立非模态窗口
    """
    change_reverted = pyqtSignal(str)
    change_accepted = pyqtSignal(str)

    def __init__(self, record_or_path, is_dark: bool = True, parent=None):
        super().__init__(parent, Qt.Window)
        self.is_dark = is_dark
        self.tracker = None
        try:
            from core.file_diff_tracker import FileDiffTracker
            self.tracker = FileDiffTracker.get_instance()
        except Exception:
            pass

        if isinstance(record_or_path, str):
            self.abs_path = record_or_path
            self.record = self.tracker.get_record(record_or_path) if self.tracker else None
        else:
            self.record = record_or_path
            self.abs_path = self.record.abs_path if self.record else ""

        rel_display = self.record.rel_path if self.record else (os.path.basename(self.abs_path) if self.abs_path else "未知文件")
        self.setWindowTitle(f"📁 代码变更审查与对比 - {rel_display}")
        self.resize(1020, 720)
        self.setMinimumSize(800, 520)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self._init_ui()
        self._render_diff()

    def _init_ui(self):
        d = self.is_dark
        bg_col = "#141417" if d else "#f8fafc"
        self.setStyleSheet(f"QDialog {{ background-color: {bg_col}; }}")

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # 1. 顶部操作与元数据栏
        top_bar = QFrame(self)
        top_bar.setFixedHeight(56)
        top_bar_bg = "#1e1e24" if d else "#ffffff"
        top_bar_border = "#2a2a34" if d else "#e2e8f0"
        top_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {top_bar_bg};
                border-bottom: 1px solid {top_bar_border};
            }}
        """)
        top_lay = QHBoxLayout(top_bar)
        top_lay.setContentsMargins(18, 0, 18, 0)
        top_lay.setSpacing(12)

        icon_lbl = QLabel("📄", top_bar)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 14))
        top_lay.addWidget(icon_lbl)

        # 标题与路径
        path_vbox = QVBoxLayout()
        path_vbox.setSpacing(2)
        path_vbox.setContentsMargins(0, 8, 0, 8)

        rel_display = self.record.rel_path if self.record else os.path.basename(self.abs_path)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        self.lbl_filename = QLabel(rel_display, top_bar)
        self.lbl_filename.setFont(QFont("JetBrains Mono", 11, QFont.Bold))
        self.lbl_filename.setStyleSheet(f"color: {'#f4f4f5' if d else '#0f172a'}; background: transparent;")
        title_row.addWidget(self.lbl_filename)

        # 状态徽章 (新建/修改)
        is_new = (self.record.status == "created") if self.record else False
        status_text = "新建文件" if is_new else "修改文件"
        status_bg = "#064e3b" if is_new else ("#1e3a8a" if d else "#dbeafe")
        status_fg = "#34d399" if is_new else ("#60a5fa" if d else "#1d4ed8")
        badge_lbl = QLabel(status_text, top_bar)
        badge_lbl.setFont(QFont("Microsoft YaHei UI", 9))
        badge_lbl.setAlignment(Qt.AlignCenter)
        badge_lbl.setMinimumWidth(62)
        badge_lbl.setStyleSheet(f"""
            background-color: {status_bg};
            color: {status_fg};
            border-radius: 4px;
            padding: 2px 6px;
        """)
        title_row.addWidget(badge_lbl)

        # 增删统计
        added = self.record.added_lines if self.record else 0
        removed = self.record.removed_lines if self.record else 0
        stat_lbl = QLabel(f"+{added}  -{removed} 行", top_bar)
        stat_lbl.setFont(QFont("JetBrains Mono", 9, QFont.Bold))
        stat_lbl.setStyleSheet("color: #10b981; background: transparent;")
        title_row.addWidget(stat_lbl)
        title_row.addStretch()

        path_vbox.addLayout(title_row)

        sub_lbl = QLabel(f"绝对路径: {self.abs_path}", top_bar)
        sub_lbl.setFont(QFont("JetBrains Mono", 8))
        sub_lbl.setStyleSheet(f"color: {'#71717a' if d else '#94a3b8'}; background: transparent;")
        path_vbox.addWidget(sub_lbl)

        top_lay.addLayout(path_vbox)
        top_lay.addStretch()

        # 按钮样式
        btn_bg = "#27272f" if d else "#f1f5f9"
        btn_border = "#3a3a48" if d else "#cbd5e1"
        btn_fg = "#e4e4e7" if d else "#334155"
        common_btn_qss = f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_fg};
                border: 1px solid {btn_border};
                border-radius: 6px;
                padding: 0 12px;
                height: 30px;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{
                background-color: {'#3e3e4e' if d else '#e2e8f0'};
                color: {'#ffffff' if d else '#0f172a'};
            }}
        """

        # 1. 复制最新代码
        self.copy_btn = QPushButton("📋 复制新代码", top_bar)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setStyleSheet(common_btn_qss)
        self.copy_btn.clicked.connect(self._do_copy_new_code)
        top_lay.addWidget(self.copy_btn)

        # 2. 定位文件目录
        self.locate_btn = QPushButton("📂 打开所在目录", top_bar)
        self.locate_btn.setCursor(Qt.PointingHandCursor)
        self.locate_btn.setStyleSheet(common_btn_qss)
        self.locate_btn.clicked.connect(self._do_locate_file)
        top_lay.addWidget(self.locate_btn)

        # 3. 接收变更 (Accept)
        self.accept_btn = QPushButton("✅ 接收变更 (Accept)", top_bar)
        self.accept_btn.setCursor(Qt.PointingHandCursor)
        self.accept_btn.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        self.accept_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
                height: 30px;
            }
            QPushButton:hover { background-color: #059669; }
            QPushButton:pressed { background-color: #047857; }
        """)
        self.accept_btn.clicked.connect(self._do_accept)
        top_lay.addWidget(self.accept_btn)

        # 4. 还原撤回 (Reject)
        self.revert_btn = QPushButton("❌ 还原撤回 (Reject)", top_bar)
        self.revert_btn.setCursor(Qt.PointingHandCursor)
        self.revert_btn.setFont(QFont("Microsoft YaHei UI", 9))
        self.revert_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.12);
                color: #ef4444;
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 6px;
                padding: 0 12px;
                height: 30px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
            }
        """)
        self.revert_btn.clicked.connect(self._do_revert)
        top_lay.addWidget(self.revert_btn)

        # 5. 关闭
        close_btn = QPushButton("✖️ 关闭", top_bar)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(common_btn_qss)
        close_btn.clicked.connect(self.close)
        top_lay.addWidget(close_btn)

        main_lay.addWidget(top_bar)

        # 2. 中间 Diff 视窗 (QTextEdit + 精准 HTML Table 渲染)
        self.diff_view = QTextEdit(self)
        self.diff_view.setReadOnly(True)
        self.diff_view.setLineWrapMode(QTextEdit.NoWrap)
        diff_bg = "#111114" if d else "#ffffff"
        self.diff_view.setStyleSheet(f"""
            QTextEdit {{
                background-color: {diff_bg};
                border: none;
                padding: 12px 16px;
                selection-background-color: {'#2563eb' if d else '#bfdbfe'};
                selection-color: {'#ffffff' if d else '#1e3a8a'};
            }}
        """)
        main_lay.addWidget(self.diff_view, 1)

        # 3. 底部信息提示
        bottom_bar = QFrame(self)
        bottom_bar.setFixedHeight(30)
        bot_bg = "#19191e" if d else "#f1f5f9"
        bottom_bar.setStyleSheet(f"QFrame {{ background-color: {bot_bg}; border-top: 1px solid {top_bar_border}; }}")
        bot_lay = QHBoxLayout(bottom_bar)
        bot_lay.setContentsMargins(18, 0, 18, 0)
        info_lbl = QLabel("🔴 浅红底色带 '-' 为修改前删除的代码行  |  🟢 浅绿底色带 '+' 为新写入的代码行  |  无色为保持不变的代码", bottom_bar)
        info_lbl.setFont(QFont("Microsoft YaHei UI", 8))
        info_lbl.setStyleSheet(f"color: {'#71717a' if d else '#94a3b8'}; background: transparent;")
        bot_lay.addWidget(info_lbl)
        bot_lay.addStretch()
        main_lay.addWidget(bottom_bar)

    def _render_diff(self):
        if not self.record:
            self.diff_view.setHtml(f"<div style='color: {'#a1a1aa' if self.is_dark else '#64748b'}; padding: 20px;'>暂无该文件的对比差异记录</div>")
            return

        blocks = self.record.get_diff_blocks()
        rows_html = []
        d = self.is_dark

        for b in blocks:
            btype = b['type']
            mark = b.get('mark', '-' if btype == 'del' else ('+' if btype == 'add' else ' '))
            old_no = str(b.get('old_no', '')) if b.get('old_no', '') is not None else ""
            new_no = str(b.get('new_no', '')) if b.get('new_no', '') is not None else ""
            escaped_code = html.escape(b.get('text', ''))

            if btype == 'del':
                bg = "#3a171a" if d else "#fee2e2"
                fg = "#fca5a5" if d else "#991b1b"
                mfg = "#ef4444" if d else "#dc2626"
            elif btype == 'add':
                bg = "#143324" if d else "#dcfce7"
                fg = "#86efac" if d else "#166534"
                mfg = "#10b981" if d else "#16a34a"
            else:
                bg = "transparent"
                fg = "#e4e4e7" if d else "#1e293b"
                mfg = "#52525b" if d else "#94a3b8"

            gutter_fg = "#52525b" if d else "#94a3b8"
            rows_html.append(
                f'<tr style="background-color: {bg};">'
                f'<td style="width: 44px; text-align: right; padding-right: 8px; color: {gutter_fg}; font-family: Consolas, monospace; font-size: 11px; user-select: none;">{old_no}</td>'
                f'<td style="width: 44px; text-align: right; padding-right: 8px; color: {gutter_fg}; font-family: Consolas, monospace; font-size: 11px; user-select: none;">{new_no}</td>'
                f'<td style="width: 22px; text-align: center; color: {mfg}; font-weight: bold; font-family: Consolas, monospace; font-size: 12px; user-select: none;">{mark}</td>'
                f'<td style="white-space: pre-wrap; font-family: \'JetBrains Mono\', Consolas, \'Courier New\', monospace; font-size: 12.5px; color: {fg}; padding-left: 8px; line-height: 1.5;">{escaped_code}</td>'
                f'</tr>'
            )

        full_html = f"""
        <html>
        <head>
            <style>
                body {{ margin: 0; padding: 0; background: transparent; }}
                table {{ width: 100%; border-collapse: collapse; border-spacing: 0; }}
                tr {{ height: 22px; }}
            </style>
        </head>
        <body>
            <table>
                {''.join(rows_html)}
            </table>
        </body>
        </html>
        """
        self.diff_view.setHtml(full_html)

    def _do_copy_new_code(self):
        if self.record and self.record.after_content:
            QApplication.clipboard().setText(self.record.after_content)
            self.copy_btn.setText("✅ 已复制新代码")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋 复制新代码"))

    def _do_locate_file(self):
        if self.abs_path and os.path.exists(self.abs_path):
            try:
                import subprocess
                subprocess.Popen(f'explorer /select,"{os.path.normpath(self.abs_path)}"')
            except Exception as e:
                print("定位文件失败:", e)

    def _do_accept(self):
        if self.tracker and self.abs_path:
            self.tracker.accept_change(self.abs_path)
        self.accept_btn.setEnabled(False)
        self.accept_btn.setText("✅ 变更已确认接收")
        self.revert_btn.setEnabled(False)
        self.change_accepted.emit(self.abs_path)

    def _do_revert(self):
        if not self.tracker or not self.abs_path:
            return
        ok, msg = self.tracker.revert_change(self.abs_path)
        if ok:
            self.revert_btn.setEnabled(False)
            self.revert_btn.setText("✅ 已还原回退")
            self.accept_btn.setEnabled(False)
            self.record = self.tracker.get_record(self.abs_path)
            self._render_diff()
            self.change_reverted.emit(self.abs_path)
        else:
            show_themed_warning(self, "回滚失败", msg, self.is_dark)


# ─────────────────────────── 工作空间代码变更审查卡片 (WorkspaceChangesCard) ───────────────────────────

class WorkspaceChangesCard(QFrame):
    """
    嵌入在消息块内的工作空间变更审查卡片
    - 显示本次生成或操作涉及修改的代码文件列表
    - 每个文件带有 [新建/修改] 徽章与 +N -M 统计
    - 点击任意文件条目即可弹出 CodeDiffPreviewWindow 独立审查对比
    """
    def __init__(self, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.records = []
        self._preview_windows = []
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("WorkspaceChangesCard")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(14, 12, 14, 12)
        self.lay.setSpacing(8)
        self._apply_style()

    def set_dark(self, is_dark: bool):
        self.is_dark = is_dark
        self._apply_style()
        self._refresh_content()

    def _apply_style(self):
        d = self.is_dark
        card_bg = "#18181b" if d else "#f8fafc"
        card_border = "#10b981" if d else "#059669"
        self.setStyleSheet(f"""
            QFrame#WorkspaceChangesCard {{
                background-color: {card_bg};
                border: 1.5px solid {card_border};
                border-left: 4px solid {card_border};
                border-radius: 8px;
            }}
        """)

    def set_records(self, records: list):
        self.records = records or []
        self._refresh_content()

    def _refresh_content(self):
        while self.lay.count():
            item = self.lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                pass

        if not self.records:
            self.hide()
            return

        d = self.is_dark
        total_add = sum(r.added_lines for r in self.records)
        total_del = sum(r.removed_lines for r in self.records)

        # 头部
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        icon_lbl = QLabel("📁")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 13))
        header_row.addWidget(icon_lbl)

        title_lbl = QLabel(f"工作空间代码变更 · 共修改 {len(self.records)} 个文件")
        title_lbl.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {'#f4f4f5' if d else '#0f172a'}; background: transparent;")
        header_row.addWidget(title_lbl)

        header_row.addStretch()

        stat_badge = QLabel(f"+{total_add}  -{total_del} 行")
        stat_badge.setFont(QFont("JetBrains Mono", 9, QFont.Bold))
        stat_badge.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border-radius: 4px;
            padding: 2px 8px;
        """)
        header_row.addWidget(stat_badge)
        self.lay.addLayout(header_row)

        desc_lbl = QLabel("AI 已在当前工作空间生成或修改代码文件。点击下方任意文件可独立新开窗口查看修改前后红绿差异对比与代码审阅：")
        desc_lbl.setWordWrap(True)
        desc_lbl.setFont(QFont("Microsoft YaHei UI", 9))
        desc_lbl.setStyleSheet(f"color: {'#a1a1aa' if d else '#64748b'}; background: transparent;")
        self.lay.addWidget(desc_lbl)

        # 文件列表
        for rec in self.records:
            item_btn = QPushButton()
            item_btn.setCursor(Qt.PointingHandCursor)
            item_btn.setFixedHeight(34)
            btn_bg = "#222228" if d else "#ffffff"
            btn_border = "#33333f" if d else "#cbd5e1"
            item_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_bg};
                    border: 1px solid {btn_border};
                    border-radius: 6px;
                    text-align: left;
                    padding: 0 10px;
                }}
                QPushButton:hover {{
                    background-color: {'#2c2c36' if d else '#e2e8f0'};
                    border-color: #10b981;
                }}
            """)

            btn_lay = QHBoxLayout(item_btn)
            btn_lay.setContentsMargins(8, 0, 8, 0)
            btn_lay.setSpacing(8)

            f_icon = QLabel("📄")
            f_icon.setStyleSheet("background: transparent;")
            btn_lay.addWidget(f_icon)

            f_name = QLabel(rec.rel_path)
            f_name.setFont(QFont("JetBrains Mono", 9, QFont.Bold))
            f_name.setStyleSheet(f"color: {'#e4e4e7' if d else '#1e293b'}; background: transparent;")
            btn_lay.addWidget(f_name)

            is_new = (rec.status == "created")
            st_text = "新建" if is_new else "修改"
            st_bg = "#064e3b" if is_new else ("#1e3a8a" if d else "#dbeafe")
            st_fg = "#34d399" if is_new else ("#60a5fa" if d else "#1d4ed8")
            badge = QLabel(f" {st_text} ")
            badge.setFont(QFont("Microsoft YaHei UI", 8))
            badge.setStyleSheet(f"background-color: {st_bg}; color: {st_fg}; border-radius: 3px; padding: 1px 4px;")
            btn_lay.addWidget(badge)

            diff_stat = QLabel(f"+{rec.added_lines}  -{rec.removed_lines}")
            diff_stat.setFont(QFont("JetBrains Mono", 8))
            diff_stat.setStyleSheet("color: #10b981; background: transparent;")
            btn_lay.addWidget(diff_stat)

            btn_lay.addStretch()

            action_hint = QLabel("🔍 点击对比差异 →")
            action_hint.setFont(QFont("Microsoft YaHei UI", 8))
            action_hint.setStyleSheet("color: #10b981; background: transparent;")
            btn_lay.addWidget(action_hint)

            item_btn.clicked.connect(lambda checked=False, r=rec: self._open_diff_window(r))
            self.lay.addWidget(item_btn)

    def _open_diff_window(self, record):
        try:
            win = CodeDiffPreviewWindow(record, is_dark=self.is_dark, parent=self.window())
            win.show()
            win.raise_()
            win.activateWindow()
            self._preview_windows.append(win)
        except Exception as e:
            print("打开代码差异对比窗口异常:", e)


# ─────────────────────────── 精美纯净对话消息块 (MessageBlock) ───────────────────────────

class MessageBlock(QWidget):
    """WorkBuddy 风格纯净排版消息展示，带底部操作栏与实施方案卡片"""
    retry_requested = pyqtSignal(str)
    proceed_plan_signal = pyqtSignal(object, str)
    feedback_plan_signal = pyqtSignal()

    def __init__(self, sender: str, text: str, timestamp: str = "", model_name: str = "DeepSeek", is_dark: bool = False, user_avatar_path: str = None, parent=None):
        super().__init__(parent)
        self.sender = sender
        self.raw_text = text
        self.timestamp = timestamp or datetime.now().strftime("%H:%M")
        self.model_name = model_name
        self.is_dark = is_dark
        self.user_avatar_path = user_avatar_path
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 12)
        main_layout.setSpacing(6)

        if self.sender == "user":
            # 用户消息：右头像 + 气泡右对齐
            self.user_avatar = self._make_avatar(is_user=True)
            self.lbl_text = QLabel(self.raw_text)
            self.lbl_text.setWordWrap(True)
            self.lbl_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
            u_font = QFont("Microsoft YaHei UI", 10)
            u_font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
            self.lbl_text.setFont(u_font)
            self._apply_user_text_style()
            self.lbl_text.setMaximumWidth(860)
            row = QHBoxLayout()
            row.addStretch()
            row.addWidget(self.lbl_text, 0, Qt.AlignTop)
            row.addSpacing(8)
            row.addWidget(self.user_avatar, 0, Qt.AlignTop)
            main_layout.addLayout(row)
        else:
            # AI 消息：左侧精致 Avatar + 右侧一体化内容区域 (思考态/正文 + 底部操作栏)
            self.ai_avatar = self._make_avatar(is_user=False)

            # 右侧垂直内容容器
            content_vbox = QVBoxLayout()
            content_vbox.setContentsMargins(0, 0, 0, 0)
            content_vbox.setSpacing(6)

            # 1. 思考中 loader (与头像水平对齐)
            self.loader_widget = QWidget()
            self.loader_widget.setStyleSheet("background: transparent;")
            loader_lay = QHBoxLayout(self.loader_widget)
            loader_lay.setContentsMargins(0, 4, 0, 4)
            loader_lay.setSpacing(6)
            self.loader_icon = QLabel()
            self.loader_icon.setFixedSize(16, 16)
            self.loader_icon.setStyleSheet("background: transparent;")
            loader_lay.addWidget(self.loader_icon)
            self.loader_text = QLabel("正在思考")
            self.loader_text.setStyleSheet(f"color: {'#a1a1aa' if self.is_dark else '#64748b'}; font-size: 13.5px; font-weight: 500; font-family: 'PingFang SC', 'Microsoft YaHei UI', sans-serif; background: transparent;")
            loader_lay.addWidget(self.loader_text)
            self.loader_dots = QLabel("...")
            self.loader_dots.setStyleSheet(f"color: {'#a1a1aa' if self.is_dark else '#64748b'}; font-size: 13.5px; font-weight: bold; font-family: 'Microsoft YaHei UI'; background: transparent;")
            loader_lay.addWidget(self.loader_dots)
            loader_lay.addStretch()
            self.loader_widget.hide()
            content_vbox.addWidget(self.loader_widget)

            # 1.5 现代化极简工具调用胶囊卡片（告别 raw json 暴露）
            self.tool_capsule = ToolStatusCapsule(is_dark=self.is_dark)
            self.tool_capsule.hide()
            content_vbox.addWidget(self.tool_capsule)

            # 1.6 现代化深度思考折叠卡片 (ThoughtAccordionWidget) - 彻底隔离思考链与正文，生成完毕后默认收起
            self.thought_accordion = ThoughtAccordionWidget(is_dark=self.is_dark)
            self.thought_accordion.hide()
            content_vbox.addWidget(self.thought_accordion)

            self._loader_dot_state = 0
            self.loader_timer = QTimer(self.loader_widget)
            self.loader_timer.setInterval(380)

            # 1.8 实施方案顶栏操作条 (PlanDocumentBar) - 纯中文，置于方案正文上方
            self.plan_bar = PlanDocumentBar(is_dark=self.is_dark)
            self.plan_bar.proceed_clicked.connect(lambda txt: self._handle_proceed_clicked(txt))
            self.plan_bar.review_toggled.connect(self._on_plan_review_toggled)
            self.plan_bar.hide()
            content_vbox.addWidget(self.plan_bar)

            # 2. Markdown 消息正文与极客代码卡片
            self.lbl_text = QLabel(self.raw_text)
            self.lbl_text.setTextFormat(Qt.MarkdownText)
            self.lbl_text.setWordWrap(True)
            self.lbl_text.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
            ai_font = QFont("Microsoft YaHei UI", 10)
            ai_font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
            self.lbl_text.setFont(ai_font)
            self._apply_ai_text_style()
            self.lbl_text.setMaximumWidth(880)
            content_vbox.addWidget(self.lbl_text)

            self.content_area = MessageContentArea(is_dark=self.is_dark, parent=self)
            self.content_area.setMaximumWidth(880)
            content_vbox.addWidget(self.content_area)
            self.lbl_text.hide()

            # 2.2 代码与文件变更审查卡片 (WorkspaceChangesCard)
            self.changes_card = WorkspaceChangesCard(is_dark=self.is_dark, parent=self)
            self.changes_card.hide()
            content_vbox.addWidget(self.changes_card)

            # 2.5 实施方案确认卡片 (PlanActionCard)
            self.plan_card = PlanActionCard(is_dark=self.is_dark)
            self.plan_card.proceed_clicked.connect(lambda txt: self._handle_proceed_clicked(txt))
            self.plan_card.feedback_clicked.connect(self.feedback_plan_signal.emit)
            self.plan_card.hide()
            content_vbox.addWidget(self.plan_card)

            # 3. 底部操作工具条
            self.toolbar = QHBoxLayout()
            self.toolbar.setContentsMargins(0, 4, 0, 0)
            self.toolbar.setSpacing(6)

            # 1. 复制按钮
            self.copy_btn = QPushButton()
            self.copy_btn.setCursor(Qt.PointingHandCursor)
            self._update_copy_btn_ui(copied=False)
            self.copy_btn.clicked.connect(self._do_copy)
            self.toolbar.addWidget(self.copy_btn)

            # 2. 点赞按钮
            self.is_liked = False
            self.like_btn = QPushButton()
            self.like_btn.setCursor(Qt.PointingHandCursor)
            self._update_like_btn_ui()
            self.like_btn.clicked.connect(self._toggle_like)
            self.toolbar.addWidget(self.like_btn)

            # 3. 点踩按钮
            self.is_disliked = False
            self.dislike_btn = QPushButton()
            self.dislike_btn.setCursor(Qt.PointingHandCursor)
            self._update_dislike_btn_ui()
            self.dislike_btn.clicked.connect(self._toggle_dislike)
            self.toolbar.addWidget(self.dislike_btn)

            # 4. 重试按钮
            self.retry_btn = QPushButton()
            self.retry_btn.setCursor(Qt.PointingHandCursor)
            self.retry_btn.setIcon(load_ui_icon("refresh", "#a1a1aa" if self.is_dark else "#64748b", 14))
            self.retry_btn.setIconSize(QSize(14, 14))
            self.retry_btn.setText("  重试")
            self.retry_btn.setStyleSheet(self._get_action_btn_style(active=False))
            self.retry_btn.setToolTip("重新生成此回答")
            self.retry_btn.clicked.connect(lambda: self.retry_requested.emit(self.raw_text))
            self.toolbar.addWidget(self.retry_btn)

            self.toolbar.addSpacing(10)

            # 5. Token 统计
            self.stats_lbl = QLabel(self._calc_real_token_stat())
            self.stats_lbl.setStyleSheet(f"color: {'#71717a' if self.is_dark else '#94a3b8'}; font-size: 11px; font-family: 'Microsoft YaHei UI';")
            self.toolbar.addWidget(self.stats_lbl)

            self.toolbar.addStretch()
            content_vbox.addLayout(self.toolbar)

            # 整体行：左侧头像 + 右侧一体化内容区域
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(10)
            row.addWidget(self.ai_avatar, 0, Qt.AlignTop)
            row.addLayout(content_vbox, 1)
            main_layout.addLayout(row)

            # 初始化完成后立即统一执行工具解析与正文清洗渲染
            self.set_text(self.raw_text, is_finished=True)

    def _calc_real_token_stat(self) -> str:
        clean_txt, _ = parse_and_clean_message_text(self.raw_text)
        txt = clean_txt.strip()
        if not txt or txt == "⏳ 正在思考...":
            return f"共消耗 0 Tokens · {self.model_name}"
        import re
        # 汉字统计 (1汉字 ≈ 1.5 token)
        chinese_cnt = len(re.findall(r'[\u4e00-\u9fa5]', txt))
        other_cnt = max(0, len(txt) - chinese_cnt)
        # 英文/标点/代码符号约 0.35 token/字符
        est_tokens = max(1, int(chinese_cnt * 1.45 + other_cnt * 0.35))
        return f"共消耗 ≈ {est_tokens} Tokens · {self.model_name}"

    def _get_action_btn_style(self, active: bool = False, active_color: str = "#6366f1") -> str:
        d = self.is_dark
        if active:
            if active_color == "#10b981":
                bg = "rgba(16, 185, 129, 0.15)" if d else "#ecfdf5"
                border = "rgba(16, 185, 129, 0.4)" if d else "#a7f3d0"
            elif active_color == "#ef4444":
                bg = "rgba(239, 68, 68, 0.15)" if d else "#fef2f2"
                border = "rgba(239, 68, 68, 0.4)" if d else "#fecaca"
            else:
                bg = "rgba(99, 102, 241, 0.16)" if d else "#eef2ff"
                border = "rgba(99, 102, 241, 0.4)" if d else "#c7d2fe"
            return f"""
                QPushButton {{
                    background: {bg};
                    color: {active_color};
                    border: 1px solid {border};
                    border-radius: 5px;
                    padding: 2px 7px;
                    font-size: 11px;
                    font-family: 'PingFang SC', 'Microsoft YaHei UI', sans-serif;
                    font-weight: 600;
                }}
            """
        else:
            color = '#a1a1aa' if d else '#64748b'
            hover_color = '#ffffff' if d else '#0f172a'
            hover_bg = '#27272a' if d else '#f1f5f9'
            return f"""
                QPushButton {{
                    background: transparent;
                    color: {color};
                    border: 1px solid transparent;
                    border-radius: 5px;
                    padding: 2px 7px;
                    font-size: 11px;
                    font-family: 'PingFang SC', 'Microsoft YaHei UI', sans-serif;
                }}
                QPushButton:hover {{
                    color: {hover_color};
                    background: {hover_bg};
                }}
            """

    def _update_copy_btn_ui(self, copied: bool = False):
        d = self.is_dark
        if copied:
            self.copy_btn.setIcon(load_ui_icon("check", "#10b981", 14))
            self.copy_btn.setIconSize(QSize(14, 14))
            self.copy_btn.setText("  已复制")
            self.copy_btn.setStyleSheet(self._get_action_btn_style(active=True, active_color="#10b981"))
        else:
            self.copy_btn.setIcon(load_ui_icon("copy", "#a1a1aa" if d else "#64748b", 14))
            self.copy_btn.setIconSize(QSize(14, 14))
            self.copy_btn.setText("  复制")
            self.copy_btn.setStyleSheet(self._get_action_btn_style(active=False))

    def _update_like_btn_ui(self):
        d = self.is_dark
        if getattr(self, 'is_liked', False):
            hi_color = "#818cf8" if d else "#4f46e5"
            self.like_btn.setIcon(load_ui_icon("thumbs-up", hi_color, 14))
            self.like_btn.setIconSize(QSize(14, 14))
            self.like_btn.setText("  已赞")
            self.like_btn.setStyleSheet(self._get_action_btn_style(active=True, active_color=hi_color))
            self.like_btn.setToolTip("取消赞同")
        else:
            self.like_btn.setIcon(load_ui_icon("thumbs-up", "#a1a1aa" if d else "#64748b", 14))
            self.like_btn.setIconSize(QSize(14, 14))
            self.like_btn.setText("")
            self.like_btn.setStyleSheet(self._get_action_btn_style(active=False))
            self.like_btn.setToolTip("觉得很棒 (赞同此回答)")

    def _update_dislike_btn_ui(self):
        d = self.is_dark
        if getattr(self, 'is_disliked', False):
            self.dislike_btn.setIcon(load_ui_icon("thumbs-down", "#ef4444", 14))
            self.dislike_btn.setIconSize(QSize(14, 14))
            self.dislike_btn.setText("  已反馈")
            self.dislike_btn.setStyleSheet(self._get_action_btn_style(active=True, active_color="#ef4444"))
            self.dislike_btn.setToolTip("取消反馈")
        else:
            self.dislike_btn.setIcon(load_ui_icon("thumbs-down", "#a1a1aa" if d else "#64748b", 14))
            self.dislike_btn.setIconSize(QSize(14, 14))
            self.dislike_btn.setText("")
            self.dislike_btn.setStyleSheet(self._get_action_btn_style(active=False))
            self.dislike_btn.setToolTip("内容有待改进")

    def _do_copy(self):
        clean_txt, _ = parse_and_clean_message_text(self.raw_text)
        txt = clean_txt.strip()
        if txt and txt != "⏳ 正在思考...":
            QApplication.clipboard().setText(txt)
            self._update_copy_btn_ui(copied=True)
            QTimer.singleShot(1500, lambda: self._update_copy_btn_ui(copied=False))

    def _toggle_like(self):
        self.is_liked = not getattr(self, 'is_liked', False)
        if self.is_liked:
            self.is_disliked = False
        self._update_like_btn_ui()
        self._update_dislike_btn_ui()

    def _toggle_dislike(self):
        self.is_disliked = not getattr(self, 'is_disliked', False)
        if self.is_disliked:
            self.is_liked = False
        self._update_dislike_btn_ui()
        self._update_like_btn_ui()

    def _apply_user_text_style(self):
        d = self.is_dark
        user_bg = "#27272a" if d else "#f1f5f9"
        user_fg = "#f4f4f5" if d else "#0f172a"
        user_border = "#3f3f46" if d else "#cbd5e1"
        self.lbl_text.setStyleSheet(f"""
            QLabel {{
                background-color: {user_bg};
                color: {user_fg};
                border: 1px solid {user_border};
                border-radius: 18px;
                border-bottom-right-radius: 4px;
                padding: 11px 18px;
                font-size: 13.5px;
                line-height: 1.55;
                letter-spacing: 0.2px;
                font-family: 'PingFang SC', 'Microsoft YaHei UI', 'Source Han Sans CN', 'HarmonyOS Sans SC', -apple-system, 'Segoe UI', sans-serif;
            }}
        """)

    def _apply_ai_text_style(self):
        text_color = "#e4e4e7" if self.is_dark else "#1f2937"
        self.lbl_text.setStyleSheet(f"""
            QLabel {{
                background-color: transparent;
                color: {text_color};
                padding: 4px 8px;
                font-size: 14px;
                line-height: 1.65;
                letter-spacing: 0.2px;
                font-family: 'PingFang SC', 'Microsoft YaHei UI', 'Source Han Sans CN', 'HarmonyOS Sans SC', -apple-system, 'Segoe UI', sans-serif;
            }}
        """)

    def set_text(self, text: str, is_finished: bool = False):
        self.raw_text = text
        if hasattr(self, 'lbl_text'):
            if self.sender != "user":
                # 解析工具状态与深度净化正文（彻底抹平生硬 raw JSON 与内部调试提示）
                clean_text, tool_info, thought_text = parse_and_clean_message_text(text, return_thought=True)

                # 动态联动深度思考折叠面板（思考过程与正文物理隔离）
                if hasattr(self, 'thought_accordion') and self.thought_accordion:
                    if thought_text:
                        self.thought_accordion.set_thought(thought_text)
                        self.thought_accordion.show()
                    else:
                        self.thought_accordion.hide()

                # 动态联动工具调用胶囊卡片
                if hasattr(self, 'tool_capsule') and self.tool_capsule:
                    if tool_info:
                        self.tool_capsule.set_tool_info(
                            friendly_name=tool_info.get("friendly_name", ""),
                            tool_name=tool_info.get("tool_name", ""),
                            status=tool_info.get("status", "done")
                        )
                        self.tool_capsule.show()
                    else:
                        self.tool_capsule.hide()

                # 检查是否有工作空间代码变动记录并联动 WorkspaceChangesCard
                diff_tags = re.findall(r'\[\[WORKSPACE_DIFF:([^\]]+)\]\]', text)
                if diff_tags:
                    try:
                        from core.file_diff_tracker import FileDiffTracker, FileChangeRecord
                        tracker = FileDiffTracker.get_instance()
                        records = []
                        for tag_str in diff_tags:
                            parts = tag_str.split('|')
                            if len(parts) >= 2:
                                rel_p = parts[0]
                                abs_p = parts[1]
                                rec = tracker.get_record(abs_p) if tracker else None
                                if rec:
                                    records.append(rec)
                                else:
                                    st = parts[2] if len(parts) > 2 else "modified"
                                    add_l = int(parts[3].lstrip('+')) if len(parts) > 3 and parts[3].lstrip('+').isdigit() else 0
                                    del_l = int(parts[4].lstrip('-')) if len(parts) > 4 and parts[4].lstrip('-').isdigit() else 0
                                    records.append(FileChangeRecord(
                                        rel_path=rel_p,
                                        abs_path=abs_p,
                                        status=st,
                                        before_content="",
                                        after_content="",
                                        added_lines=add_l,
                                        removed_lines=del_l
                                    ))
                        if hasattr(self, 'changes_card') and self.changes_card and records:
                            self.changes_card.set_records(records)
                            self.changes_card.show()
                    except Exception as e:
                        print(f"[WorkspaceChangesCard] 解析异常: {e}")
                else:
                    if hasattr(self, 'changes_card') and self.changes_card:
                        self.changes_card.hide()

                # 思考中状态：用 loader_widget 替代 lbl_text / content_area 显示
                if text == "⏳ 正在思考...":
                    self.lbl_text.hide()
                    if hasattr(self, 'content_area') and self.content_area:
                        self.content_area.hide()
                    if hasattr(self, 'loader_widget'):
                        self.loader_widget.show()
                        # 渲染 hourglass SVG 图标
                        loader_color = "#a1a1aa" if self.is_dark else "#64748b"
                        self.loader_icon.setPixmap(
                            load_ui_icon("hourglass", loader_color, 16).pixmap(QSize(16, 16))
                        )
                        # 启动三点动画
                        self._loader_dot_state = 0
                        self.loader_dots.setText(".")
                        self.loader_timer.timeout.connect(self._tick_loader_dots)
                        if not self.loader_timer.isActive():
                            self.loader_timer.start()
                elif tool_info and tool_info.get("status") == "running" and not clean_text:
                    # 正在调用工具且第二轮正文尚未吐出时，聚焦于工具卡片执行中状态
                    self.lbl_text.hide()
                    if hasattr(self, 'content_area') and self.content_area:
                        self.content_area.hide()
                    if hasattr(self, 'loader_widget'):
                        self.loader_widget.hide()
                        if hasattr(self, 'loader_timer') and self.loader_timer.isActive():
                            self.loader_timer.stop()
                else:
                    clean_for_display = re.sub(r'\[\[WORKSPACE_DIFF:[^\]]+\]\]\n?', '', clean_text)
                    display_content = clean_for_display.replace("<!-- PLAN_DOCUMENT_READY -->", "").replace("<!-- plan_document_ready -->", "").replace("📋 实施方案已就绪，请审阅确认", "").strip()
                    self.lbl_text.setTextFormat(Qt.MarkdownText)
                    self.lbl_text.setText(display_content)
                    self.lbl_text.hide()
                    if hasattr(self, 'content_area') and self.content_area:
                        self.content_area.set_content(display_content)
                        self.content_area.show()
                    else:
                        self.lbl_text.show()
                    if hasattr(self, 'loader_widget'):
                        self.loader_widget.hide()
                        if hasattr(self, 'loader_timer') and self.loader_timer.isActive():
                            self.loader_timer.stop()

                    # 智能检测实施方案文档：必须在内容完整生成完毕(is_finished=True)且满足特征时才展示 PlanDocumentBar 与 PlanActionCard
                    is_plan_doc = is_finished and (
                        "<!-- PLAN_DOCUMENT_READY -->" in text.upper() or
                        ("方案已就绪" in text or "方案已生成" in text or "实施方案已就绪" in text or "计划已就绪" in text) or
                        ("# " in clean_text and ("实施方案" in clean_text or "实施计划" in clean_text or "实现计划" in clean_text) and ("涉及文件" in clean_text or "实施步骤" in clean_text or "架构设计" in clean_text or "需求理解" in clean_text)) or
                        ("Implementation Plan" in clean_text and ("Proposed Changes" in clean_text or "Verification Plan" in clean_text)) or
                        ("计划文档" in clean_text and ("实现计划" in clean_text or "实施步骤" in clean_text or "分步实施" in clean_text or "项目目标" in clean_text))
                    )
                    if is_plan_doc:
                        # 方案规划输出模式：聊天气泡内只呈现精简的步骤流程概要，完整技术方案存入操作栏与独立预览
                        try:
                            from ui.dev_mode_view import _generate_plan_chat_summary
                            plan_summary = _generate_plan_chat_summary(display_content)
                            if hasattr(self, 'content_area') and self.content_area:
                                self.content_area.set_content(plan_summary)
                        except Exception as e:
                            print(f"[MessageBlock] 方案摘要提炼异常: {e}")

                        if hasattr(self, 'plan_bar') and self.plan_bar:
                            self.plan_bar.set_plan_text(display_content)
                            self.plan_bar.show()
                        if hasattr(self, 'plan_card') and self.plan_card:
                            self.plan_card.set_plan_text(display_content)
                            self.plan_card.show()
                    else:
                        if hasattr(self, 'plan_bar') and self.plan_bar:
                            self.plan_bar.hide()
                        if hasattr(self, 'plan_card') and self.plan_card:
                            self.plan_card.hide()
            else:
                # 用户提问展示：若含有系统附加的文档长文本，提炼为精美胶囊附件摘要与干净的用户问题
                if ("【用户上传并附加了" in text or "【用户上传了" in text) and ("--- 附件正文内容开始 ---" in text or "【用户上传了图片附件】" in text):
                    lines = text.splitlines()
                    badge_items = []
                    user_q_lines = []
                    in_q = False
                    for l in lines:
                        if "📎 文件名:" in l:
                            fn = l.replace("📎 文件名:", "").strip()
                            badge_items.append(f"📎 `{fn}`")
                        elif "图片文件:" in l or "图片名称:" in l:
                            fn = l.split(":", 1)[-1].strip()
                            badge_items.append(f"🖼️ `{fn}`")
                        elif "用户需求与问题:" in l or "用户针对附件的提问与指令:" in l or "用户提问:" in l:
                            in_q = True
                            continue
                        elif in_q:
                            user_q_lines.append(l)
                    badge_prefix = "  ".join(badge_items)
                    q_text = "\n".join(user_q_lines).strip()
                    clean_text = f"{badge_prefix}\n\n{q_text}" if (badge_prefix and q_text) else (badge_prefix or q_text or text)
                    self.lbl_text.setTextFormat(Qt.MarkdownText)
                    self.lbl_text.setText(clean_text)
                else:
                    self.lbl_text.setTextFormat(Qt.MarkdownText)
                    self.lbl_text.setText(text)
        if hasattr(self, 'stats_lbl'):
            self.stats_lbl.setText(self._calc_real_token_stat())

    def _handle_proceed_clicked(self, txt: str):
        if hasattr(self, 'plan_bar') and self.plan_bar:
            self.plan_bar.proceed_btn.setText("✅ 已确认执行")
            self.plan_bar.proceed_btn.setEnabled(False)
            self.plan_bar.is_proceeded = True
            self.plan_bar.time_lbl.setText("已批准 · 执行中")
            self.plan_bar._apply_style()
        if hasattr(self, 'plan_card') and self.plan_card:
            self.plan_card.proceed_btn.setText("✅ 已接收并批准")
            self.plan_card.proceed_btn.setEnabled(False)
            self.plan_card.is_proceeded = True
            self.plan_card.badge_lbl.setText("执行中")
            self.plan_card._apply_style()
        self.proceed_plan_signal.emit(self, txt)

    def _on_plan_review_toggled(self, expanded: bool):
        if hasattr(self, 'lbl_text'):
            self.lbl_text.setVisible(expanded and not hasattr(self, 'content_area'))
        if hasattr(self, 'content_area') and self.content_area:
            self.content_area.setVisible(expanded)
        if hasattr(self, 'plan_card'):
            self.plan_card.setVisible(expanded)

    def _tick_loader_dots(self):
        # 三点动画 "." → ".." → "..." → "" 循环
        states = [".", "..", "...", ""]
        self._loader_dot_state = (self._loader_dot_state + 1) % len(states)
        self.loader_dots.setText(states[self._loader_dot_state])

    def _make_avatar(self, is_user: bool) -> QLabel:
        """生成消息头像（用户上传则用图片，AI 使用微光 sparkles 图标，默认首字母高质感徽章）"""
        avatar = QLabel()
        avatar.setAlignment(Qt.AlignCenter)
        if is_user and self.user_avatar_path:
            try:
                from pathlib import Path as _P
                if _P(self.user_avatar_path).exists():
                    pix = QPixmap(self.user_avatar_path).scaled(
                        60, 60, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                    )
                    rounded = QPixmap(30, 30)
                    rounded.fill(QColor(0, 0, 0, 0))
                    p = QPainter(rounded)
                    p.setRenderHint(QPainter.Antialiasing, True)
                    path = QPainterPath()
                    path.addEllipse(0, 0, 30, 30)
                    p.setClipPath(path)
                    p.drawPixmap((30 - pix.width()) // 2, (30 - pix.height()) // 2, pix)
                    p.end()
                    avatar.setFixedSize(30, 30)
                    avatar.setPixmap(rounded)
                    return avatar
            except Exception:
                pass

        if is_user:
            avatar.setFixedSize(30, 30)
            avatar.setText("U")
            avatar.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
            avatar.setStyleSheet("""
                QLabel {
                    background: #10b981;
                    color: #ffffff;
                    border-radius: 15px;
                    font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
                }
            """)
            return avatar
        else:
            avatar.setFixedSize(28, 28)
            avatar.setStyleSheet(f"""
                QLabel {{
                    background: {'#18181b' if self.is_dark else '#eef2ff'};
                    border: 1px solid {'#3f3f46' if self.is_dark else '#c7d2fe'};
                    border-radius: 8px;
                }}
            """)
            ic = load_ui_icon("sparkles", "#818cf8" if self.is_dark else "#4f46e5", 15)
            avatar.setPixmap(ic.pixmap(QSize(15, 15)))
            return avatar

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        if self.sender == "user":
            self._apply_user_text_style()
        else:
            self._apply_ai_text_style()
            if hasattr(self, 'content_area') and self.content_area:
                self.content_area.set_dark(is_dark)
            if hasattr(self, 'tool_capsule') and self.tool_capsule:
                self.tool_capsule.set_theme(is_dark)
            if hasattr(self, 'plan_bar') and self.plan_bar:
                self.plan_bar.set_dark(is_dark)
            if hasattr(self, 'plan_card') and self.plan_card:
                self.plan_card.set_dark(is_dark)
            if hasattr(self, 'changes_card') and self.changes_card:
                self.changes_card.set_dark(is_dark)
            if hasattr(self, 'ai_avatar') and self.ai_avatar:
                self.ai_avatar.setStyleSheet(f"""
                    QLabel {{
                        background: {'#18181b' if self.is_dark else '#eef2ff'};
                        border: 1px solid {'#3f3f46' if self.is_dark else '#c7d2fe'};
                        border-radius: 8px;
                    }}
                """)
                ic = load_ui_icon("sparkles", "#818cf8" if self.is_dark else "#4f46e5", 15)
                self.ai_avatar.setPixmap(ic.pixmap(QSize(15, 15)))
            if hasattr(self, 'copy_btn'): self._update_copy_btn_ui(copied=False)
            if hasattr(self, 'like_btn'): self._update_like_btn_ui()
            if hasattr(self, 'dislike_btn'): self._update_dislike_btn_ui()
            if hasattr(self, 'retry_btn'):
                self.retry_btn.setIcon(load_ui_icon("refresh", "#a1a1aa" if self.is_dark else "#64748b", 14))
                self.retry_btn.setStyleSheet(self._get_action_btn_style(active=False))
            if hasattr(self, 'stats_lbl'):
                self.stats_lbl.setStyleSheet(f"color: {'#71717a' if self.is_dark else '#94a3b8'}; font-size: 11px; font-family: 'Microsoft YaHei UI';")


# ─────────────────────────── 高对比度清晰主题弹窗工具集 ───────────────────────────

def _show_themed_dialog(parent, kind: str, title: str, text: str, is_dark: bool, with_cancel: bool = False) -> bool:
    """统一精致主题对话框（info / warning / confirm 三种 kind）"""
    d = is_dark
    bg = "#1e1e1e" if d else "#ffffff"
    fg = "#f4f4f5" if d else "#0f172a"
    sub_fg = "#a1a1aa" if d else "#475569"
    border = "#2e2e2e" if d else "#e2e8f0"
    btn_bg = "#27272a" if d else "#f1f5f9"
    accent = "#6366f1"
    danger = "#ef4444"

    # 顶部 icon + 标题颜色（按 kind 区分）
    if kind == "warning":
        icon_name, accent_color = "warning", danger
    elif kind == "confirm":
        icon_name, accent_color = "help", accent
    else:
        icon_name, accent_color = "check", accent

    # 自定义 QDialog（不用 QMessageBox，避免系统默认风格覆盖样式）
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setMinimumWidth(360)
    dlg.setMaximumWidth(480)
    dlg.setModal(True)
    # 关键：用 setWindowFlag 移除标题栏，重新绘制
    dlg.setWindowFlags(dlg.windowFlags() | Qt.Dialog)

    # 整体样式
    dlg.setStyleSheet(f"""
        QDialog {{
            background-color: {bg};
            border: 1px solid {border};
            border-radius: 12px;
        }}
        QLabel#IconLbl {{ background: transparent; }}
        QLabel#TitleLbl {{
            color: {fg};
            font-size: 15px;
            font-weight: bold;
            font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            background: transparent;
        }}
        QLabel#BodyLbl {{
            color: {sub_fg};
            font-size: 13px;
            font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            background: transparent;
            line-height: 1.5;
        }}
        QPushButton {{
            background: {btn_bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 0 18px;
            font-size: 13px;
            font-family: 'Microsoft YaHei UI';
            min-height: 34px;
            min-width: 88px;
        }}
        QPushButton:hover {{ background: {'#3f3f46' if d else '#e2e8f0'}; }}
        QPushButton#PrimaryBtn {{
            background: {accent_color};
            color: #ffffff;
            border: none;
            font-weight: 600;
        }}
        QPushButton#PrimaryBtn:hover {{
            background: {'#4f46e5' if kind != 'warning' else '#dc2626'};
        }}
    """)

    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(20, 18, 20, 16)
    lay.setSpacing(12)

    # 顶部行：SVG 图标 + 标题
    head_row = QHBoxLayout()
    head_row.setSpacing(10)
    icon_lbl = QLabel()
    icon_lbl.setObjectName("IconLbl")
    icon_lbl.setFixedSize(28, 28)
    icon_pixmap = load_ui_icon(icon_name, accent_color, 28).pixmap(QSize(28, 28))
    icon_lbl.setPixmap(icon_pixmap)
    head_row.addWidget(icon_lbl, 0, Qt.AlignTop)

    title_lbl = QLabel(title)
    title_lbl.setObjectName("TitleLbl")
    title_lbl.setWordWrap(True)
    head_row.addWidget(title_lbl, 1, Qt.AlignVCenter)
    lay.addLayout(head_row)

    # 正文
    body_lbl = QLabel(text)
    body_lbl.setObjectName("BodyLbl")
    body_lbl.setWordWrap(True)
    body_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    lay.addWidget(body_lbl)

    lay.addSpacing(6)

    # 按钮行
    btn_row = QHBoxLayout()
    btn_row.setSpacing(8)
    btn_row.addStretch()
    if with_cancel:
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)
    primary_text = "知道了" if kind == "info" else ("确定" if kind == "confirm" else "知道了")
    primary_btn = QPushButton(primary_text)
    primary_btn.setObjectName("PrimaryBtn")
    primary_btn.setCursor(Qt.PointingHandCursor)
    primary_btn.clicked.connect(dlg.accept)
    primary_btn.setDefault(True)
    btn_row.addWidget(primary_btn)
    lay.addLayout(btn_row)

    result = dlg.exec_()
    if with_cancel:
        return result == QDialog.Accepted
    return True


def show_themed_confirm(parent, title: str, text: str, is_dark: bool = False) -> bool:
    """弹出精致主题确认对话框"""
    return _show_themed_dialog(parent, "confirm", title, text, is_dark, with_cancel=True)


def show_themed_info(parent, title: str, text: str, is_dark: bool = False):
    """弹出精致主题提示对话框"""
    _show_themed_dialog(parent, "info", title, text, is_dark, with_cancel=False)


def show_themed_warning(parent, title: str, text: str, is_dark: bool = False):
    """弹出精致主题警告/错误提示对话框"""
    _show_themed_dialog(parent, "warning", title, text, is_dark, with_cancel=False)


# ─────────────────────────── 会话批量管理对话框 (BatchSessionDialog) ───────────────────────────

class BatchSessionDialog(QDialog):
    """批量管理会话对话框（支持多选、批量删除、批量导出，高对比度清晰视觉）"""
    def __init__(self, parent=None, is_dark: bool = False, sessions: list = None, memory=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.sessions = sessions or []
        self.memory = memory
        self.setWindowTitle("会话批量管理")
        self.setFixedSize(620, 460)
        self.setModal(True)
        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        head_h = QHBoxLayout()
        title_lbl = QLabel("📑 批量管理会话任务")
        title_lbl.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        head_h.addWidget(title_lbl)

        self.lbl_count = QLabel(f"共 {len(self.sessions)} 个任务 · 已选 0 项")
        self.lbl_count.setStyleSheet(f"color: {'#a1a1aa' if self.is_dark else '#64748b'}; font-size: 11px; padding-left: 6px;")
        head_h.addWidget(self.lbl_count)
        head_h.addStretch()

        self.btn_select_all = QPushButton("全选")
        self.btn_select_all.setFixedSize(60, 26)
        self.btn_select_all.clicked.connect(self._select_all)
        head_h.addWidget(self.btn_select_all)

        self.btn_invert = QPushButton("反选")
        self.btn_invert.setFixedSize(60, 26)
        self.btn_invert.clicked.connect(self._invert_selection)
        head_h.addWidget(self.btn_invert)
        layout.addLayout(head_h)

        # 列表
        self.list_widget = QListWidget()
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for s in self.sessions:
            sid = s.get("id", "")
            title = s.get("title", "未命名任务")
            created_at = s.get("created_at", "")[:16]
            ws_n = s.get("workspace_name", "")
            ws_tag = f" [📁 {ws_n}]" if ws_n else ""
            item = QListWidgetItem(f"  {title}{ws_tag}    ({created_at})")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, sid)
            self.list_widget.addItem(item)
        self.list_widget.itemChanged.connect(self._update_counter)
        layout.addWidget(self.list_widget, 1)

        # 底部操作栏
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)
        self.del_btn = QPushButton("🗑️ 批量删除选中")
        self.del_btn.setFixedHeight(32)
        self.del_btn.setMinimumWidth(160)
        self.del_btn.setStyleSheet("background: #ef4444; color: #ffffff; border: none; border-radius: 6px; font-weight: bold; font-size: 12px; padding: 0 12px;")
        self.del_btn.clicked.connect(self._batch_delete)
        btn_bar.addWidget(self.del_btn)

        self.export_btn = QPushButton("📤 批量导出 Markdown")
        self.export_btn.setFixedHeight(32)
        self.export_btn.setMinimumWidth(180)
        self.export_btn.setStyleSheet("background: #6366f1; color: #ffffff; border: none; border-radius: 6px; font-weight: bold; font-size: 12px; padding: 0 12px;")
        self.export_btn.clicked.connect(self._batch_export)
        btn_bar.addWidget(self.export_btn)

        btn_bar.addStretch()
        close_btn = QPushButton("完成")
        close_btn.setFixedSize(70, 32)
        close_btn.clicked.connect(self.accept)
        btn_bar.addWidget(close_btn)
        layout.addLayout(btn_bar)

    def _apply_style(self):
        d = self.is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        fg = "#f4f4f5" if d else "#0f172a"
        border = "#2e2e32" if d else "#e2e8f0"
        item_bg = "#27272a" if d else "#f8fafc"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; font-family: 'Microsoft YaHei UI'; }}
            QLabel {{ color: {fg}; }}
            QListWidget {{
                background-color: {item_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 6px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-radius: 6px;
                color: {fg};
            }}
            QListWidget::item:hover {{
                background-color: {'#3f3f46' if d else '#e2e8f0'};
            }}
            QPushButton {{
                background-color: {'#27272a' if d else '#f1f5f9'};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{
                background-color: {'#3f3f46' if d else '#e2e8f0'};
            }}
        """)

    def _select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Checked)
        self._update_counter()

    def _invert_selection(self):
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            it.setCheckState(Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked)
        self._update_counter()

    def _get_checked_ids(self):
        checked = []
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if it.checkState() == Qt.Checked:
                checked.append((it.data(Qt.UserRole), it.text().strip()))
        return checked

    def _update_counter(self):
        checked = self._get_checked_ids()
        cnt = len(checked)
        self.lbl_count.setText(f"共 {self.list_widget.count()} 个任务 · 已选 {cnt} 项")
        self.del_btn.setText(f"🗑️ 批量删除选中 ({cnt})" if cnt > 0 else "🗑️ 批量删除选中")
        self.export_btn.setText(f"📤 批量导出 Markdown ({cnt})" if cnt > 0 else "📤 批量导出 Markdown")

    def _batch_delete(self):
        checked = self._get_checked_ids()
        if not checked:
            show_themed_info(self, "提示", "请先勾选需要删除的会话任务。", self.is_dark)
            return
        if show_themed_confirm(self, "批量删除确认", f"确定要永久删除选中的 {len(checked)} 个会话任务吗？\n删除后不可恢复。", self.is_dark):
            if self.memory:
                for sid, _ in checked:
                    try:
                        self.memory.delete_session(sid)
                    except Exception:
                        pass
            # 刷新列表
            for i in reversed(range(self.list_widget.count())):
                it = self.list_widget.item(i)
                if it.checkState() == Qt.Checked:
                    self.list_widget.takeItem(i)
            self._update_counter()
            show_themed_info(self, "删除成功", f"已成功删除 {len(checked)} 个任务。", self.is_dark)

    def _batch_export(self):
        checked = self._get_checked_ids()
        if not checked:
            show_themed_info(self, "提示", "请先勾选需要导出的会话任务。", self.is_dark)
            return
        desktop = Path.home() / "Desktop"
        export_count = 0
        if self.memory:
            for sid, title in checked:
                try:
                    msgs = self.memory.get_session_messages(sid)
                    lines = [f"# {title}\n"]
                    for m in msgs:
                        role = "🧑 User" if m.get("role") == "user" else "🤖 AI"
                        content = m.get("content", "")
                        lines.append(f"### {role}\n\n{content}\n")
                    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip() or f"session_{sid}"
                    target_p = desktop / f"{safe_title}.md"
                    if target_p.exists():
                        target_p = desktop / f"{safe_title}_{sid}.md"
                    target_p.write_text("\n".join(lines), encoding="utf-8")
                    export_count += 1
                except Exception:
                    pass
        show_themed_info(self, "导出成功", f"已成功将 {export_count} 个任务导出至桌面！", self.is_dark)


# ─────────────────────────── 工作空间批量管理对话框 (BatchWorkspaceDialog) ───────────────────────────

class BatchWorkspaceDialog(QDialog):
    """批量管理工作空间对话框（支持多选、批量从列表移除、连带删除关联任务与本地磁盘安全保护）"""
    def __init__(self, parent=None, is_dark: bool = False, workspaces: list = None, memory=None, config: dict = None, save_config_fn=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.workspaces = list(workspaces or [])
        self.memory = memory
        self.config = config or {}
        self.save_config_fn = save_config_fn
        self.removed_workspaces = []
        self.deleted_sids = []
        self.setWindowTitle("工作空间批量管理")
        self.setFixedSize(640, 480)
        self.setModal(True)
        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        head_h = QHBoxLayout()
        title_lbl = QLabel("📁 批量管理工作空间")
        title_lbl.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        head_h.addWidget(title_lbl)

        self.lbl_count = QLabel(f"共 {len(self.workspaces)} 个空间 · 已选 0 项")
        self.lbl_count.setStyleSheet(f"color: {'#a1a1aa' if self.is_dark else '#64748b'}; font-size: 11px; padding-left: 6px;")
        head_h.addWidget(self.lbl_count)
        head_h.addStretch()

        self.btn_select_all = QPushButton("全选")
        self.btn_select_all.setFixedSize(60, 26)
        self.btn_select_all.clicked.connect(self._select_all)
        head_h.addWidget(self.btn_select_all)

        self.btn_invert = QPushButton("反选")
        self.btn_invert.setFixedSize(60, 26)
        self.btn_invert.clicked.connect(self._invert_selection)
        head_h.addWidget(self.btn_invert)
        layout.addLayout(head_h)

        # 空间列表
        self.list_widget = QListWidget()
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        all_sessions = self.memory.get_all_sessions() if self.memory else []
        curr_name = self.config.get("current_workspace_name", "")

        for ws in self.workspaces:
            name = ws.get("name", "未命名空间")
            path = ws.get("path", "")
            task_cnt = sum(1 for s in all_sessions if s.get("workspace_name") == name)
            is_active = (name == curr_name)
            active_badge = " [当前激活]" if is_active else ""
            item_text = f"  📁 {name}{active_badge}    ({task_cnt} 个关联任务)    [{path}]"
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, name)
            self.list_widget.addItem(item)

        self.list_widget.itemChanged.connect(self._update_counter)
        layout.addWidget(self.list_widget, 1)

        # 关联选项与安全提示
        opt_lay = QVBoxLayout()
        opt_lay.setSpacing(4)
        self.chk_del_sessions = QCheckBox("同时删除选中空间下的全部历史任务与会话记录")
        self.chk_del_sessions.setChecked(True)
        self.chk_del_sessions.setStyleSheet(f"""
            QCheckBox {{
                color: {'#f4f4f5' if self.is_dark else '#0f172a'};
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
        """)
        opt_lay.addWidget(self.chk_del_sessions)

        safe_lbl = QLabel("🛡️ 安全说明：仅从本软件列表中移除工作空间，您磁盘上的本地文件夹与工程代码不会被物理删除。")
        safe_lbl.setStyleSheet(f"color: {'#a1a1aa' if self.is_dark else '#64748b'}; font-size: 11px;")
        safe_lbl.setWordWrap(True)
        opt_lay.addWidget(safe_lbl)
        layout.addLayout(opt_lay)

        # 底部操作栏
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)
        self.del_btn = QPushButton("🗑️ 批量移除选中空间")
        self.del_btn.setFixedHeight(32)
        self.del_btn.setMinimumWidth(180)
        self.del_btn.setStyleSheet("background: #ef4444; color: #ffffff; border: none; border-radius: 6px; font-weight: bold; font-size: 12px; padding: 0 16px;")
        self.del_btn.clicked.connect(self._batch_remove)
        btn_bar.addWidget(self.del_btn)

        btn_bar.addStretch()
        close_btn = QPushButton("完成")
        close_btn.setFixedSize(70, 32)
        close_btn.clicked.connect(self.accept)
        btn_bar.addWidget(close_btn)
        layout.addLayout(btn_bar)

    def _apply_style(self):
        d = self.is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        fg = "#f4f4f5" if d else "#0f172a"
        border = "#2e2e32" if d else "#e2e8f0"
        item_bg = "#27272a" if d else "#f8fafc"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; font-family: 'Microsoft YaHei UI'; }}
            QLabel {{ color: {fg}; }}
            QListWidget {{
                background-color: {item_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 6px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 7px 8px;
                border-radius: 6px;
                color: {fg};
            }}
            QListWidget::item:hover {{
                background-color: {'#3f3f46' if d else '#e2e8f0'};
            }}
            QPushButton {{
                background-color: {'#27272a' if d else '#f1f5f9'};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{
                background-color: {'#3f3f46' if d else '#e2e8f0'};
            }}
        """)

    def _select_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Checked)
        self._update_counter()

    def _invert_selection(self):
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            it.setCheckState(Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked)
        self._update_counter()

    def _get_checked_names(self):
        checked = []
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if it.checkState() == Qt.Checked:
                checked.append(it.data(Qt.UserRole))
        return checked

    def _update_counter(self):
        checked = self._get_checked_names()
        cnt = len(checked)
        self.lbl_count.setText(f"共 {self.list_widget.count()} 个空间 · 已选 {cnt} 项")
        self.del_btn.setText(f"🗑️ 批量移除选中空间 ({cnt})" if cnt > 0 else "🗑️ 批量移除选中空间")

    def _batch_remove(self):
        checked = self._get_checked_names()
        if not checked:
            show_themed_info(self, "提示", "请先勾选需要移除的工作空间。", self.is_dark)
            return

        del_sessions = self.chk_del_sessions.isChecked()
        extra_info = "• 将同时删除选中的空间及其下属的所有关联任务会话\n" if del_sessions else "• 将保留下属任务并将空间属性解绑\n"
        extra_info += "• 本地磁盘上的实际工程文件夹与代码文件将被安全保留，不会被物理删除"

        if show_themed_confirm(self, "批量移除空间确认", f"确定要从列表中移除选中的 {len(checked)} 个工作空间吗？\n\n{extra_info}", self.is_dark):
            for ws_name in checked:
                if del_sessions and self.memory:
                    try:
                        sids = self.memory.delete_sessions_by_workspace(ws_name)
                        self.deleted_sids.extend(sids)
                    except Exception:
                        pass
                elif not del_sessions and self.memory:
                    try:
                        for s in self.memory.get_all_sessions():
                            if s.get("workspace_name") == ws_name:
                                self.memory.update_session_workspace(s["id"], "")
                    except Exception:
                        pass

            self.workspaces = [w for w in self.workspaces if w.get("name") not in checked]
            self.removed_workspaces.extend(checked)

            for i in reversed(range(self.list_widget.count())):
                it = self.list_widget.item(i)
                if it.data(Qt.UserRole) in checked:
                    self.list_widget.takeItem(i)

            self._update_counter()
            show_themed_info(self, "移除成功", f"已成功移除 {len(checked)} 个工作空间。", self.is_dark)


# ─────────────────────────── 附件卡片与附件预览栏 (Attachment System) ───────────────────────────

def extract_file_attachment_info(file_path: str) -> dict:
    """解析本地文件或图片，返回结构化附件信息字典（支持图片、Word、PDF、Excel、代码与文本）"""
    p = Path(file_path)
    if not p.exists():
        return None

    size_bytes = p.stat().st_size
    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

    ext = p.suffix.lower()
    is_image = ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]

    info = {
        "path": str(p),
        "name": p.name,
        "ext": ext,
        "size_bytes": size_bytes,
        "size_str": size_str,
        "type": "image" if is_image else "doc",
        "thumbnail": None,
        "extracted_text": "",
        "base64_data": ""
    }

    if is_image:
        try:
            pix = QPixmap(str(p))
            if not pix.isNull():
                info["thumbnail"] = pix.scaled(28, 28, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            import base64
            with open(p, "rb") as f:
                info["base64_data"] = base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            pass
    elif ext == ".docx":
        try:
            import docx
            doc = docx.Document(str(p))
            lines = []
            for para in doc.paragraphs:
                t = para.text.strip()
                if t:
                    lines.append(t)
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                    lines.append(" | ".join(row_cells))
            info["extracted_text"] = "\n".join(lines)
        except Exception as e:
            info["extracted_text"] = f"[无法解析 Word 文档: {e}]"
    elif ext == ".pdf":
        try:
            text_lines = []
            try:
                import pdfplumber
                with pdfplumber.open(str(p)) as pdf:
                    for idx, page in enumerate(pdf.pages[:30]):
                        txt = page.extract_text()
                        if txt:
                            text_lines.append(f"--- 第 {idx+1} 页 ---\n{txt}")
            except Exception:
                import PyPDF2
                reader = PyPDF2.PdfReader(str(p))
                for idx, page in enumerate(reader.pages[:30]):
                    txt = page.extract_text()
                    if txt:
                        text_lines.append(f"--- 第 {idx+1} 页 ---\n{txt}")
            info["extracted_text"] = "\n\n".join(text_lines)
        except Exception as e:
            info["extracted_text"] = f"[无法解析 PDF 文档: {e}]"
    elif ext in [".xlsx", ".xls"]:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(p), data_only=True)
            sheet_texts = []
            for sname in wb.sheetnames[:5]:
                ws = wb[sname]
                rows = []
                for r in ws.iter_rows(max_row=60, values_only=True):
                    row_str = " | ".join([str(c) if c is not None else "" for c in r])
                    if row_str.strip():
                        rows.append(row_str)
                sheet_texts.append(f"### 工作表: {sname}\n" + "\n".join(rows))
            info["extracted_text"] = "\n\n".join(sheet_texts)
        except Exception as e:
            info["extracted_text"] = f"[无法解析 Excel 文档: {e}]"
    else:
        try:
            info["extracted_text"] = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            info["extracted_text"] = f"[读取失败: {e}]"

    return info


class AttachmentChipWidget(QFrame):
    """单个附件胶囊卡片（支持图片缩略图、文档徽章、文件名截断、大小显示及 ✕ 移除按钮）"""
    removed = pyqtSignal(str)  # file_path

    def __init__(self, file_info: dict, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self.file_info = file_info
        self.is_dark = is_dark
        self.file_path = file_info.get("path", "")
        self.file_name = file_info.get("name", "")
        self.file_type = file_info.get("type", "doc")
        self.ext = file_info.get("ext", "").lower()
        self.size_str = file_info.get("size_str", "")
        self.setFixedHeight(32)
        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.setSpacing(6)

        if self.file_type == "image" and self.file_info.get("thumbnail"):
            img_lbl = QLabel()
            img_lbl.setFixedSize(24, 24)
            img_lbl.setScaledContents(True)
            img_lbl.setPixmap(self.file_info["thumbnail"])
            img_lbl.setStyleSheet("border-radius: 4px;")
            lay.addWidget(img_lbl)
        else:
            badge_lbl = QLabel()
            badge_text = self.ext.replace(".", "").upper()[:4] or "FILE"
            badge_lbl.setText(f"📄 {badge_text}")
            badge_lbl.setFont(QFont("Microsoft YaHei UI", 8, QFont.Bold))
            badge_lbl.setStyleSheet(f"""
                QLabel {{
                    background: {'#312e81' if self.is_dark else '#e0e7ff'};
                    color: {'#a5b4fc' if self.is_dark else '#4338ca'};
                    border-radius: 4px;
                    padding: 1px 4px;
                }}
            """)
            lay.addWidget(badge_lbl)

        info_lay = QHBoxLayout()
        info_lay.setSpacing(4)
        name_lbl = QLabel()
        font = QFont("Microsoft YaHei UI", 9)
        name_lbl.setFont(font)
        fm = QFontMetrics(font)
        name_lbl.setText(fm.elidedText(self.file_name, Qt.ElideMiddle, 160))
        name_lbl.setToolTip(f"{self.file_name} ({self.size_str})\n路径: {self.file_path}")
        name_lbl.setStyleSheet(f"color: {'#f4f4f5' if self.is_dark else '#0f172a'}; background: transparent;")
        info_lay.addWidget(name_lbl)

        if self.size_str:
            size_lbl = QLabel(f"({self.size_str})")
            size_lbl.setStyleSheet(f"color: {'#71717a' if self.is_dark else '#94a3b8'}; font-size: 8.5px; background: transparent;")
            info_lay.addWidget(size_lbl)
        lay.addLayout(info_lay)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(16, 16)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setToolTip("移除此附件")
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {'#a1a1aa' if self.is_dark else '#94a3b8'};
                border: none;
                border-radius: 8px;
                font-size: 11px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {'#3f3f46' if self.is_dark else '#e2e8f0'};
                color: #ef4444;
            }}
        """)
        del_btn.clicked.connect(lambda: self.removed.emit(self.file_path))
        lay.addWidget(del_btn)

    def _apply_style(self):
        d = self.is_dark
        bg = "#27272a" if d else "#f8fafc"
        border = "#3f3f46" if d else "#cbd5e1"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
        """)


class AttachmentPreviewBar(QWidget):
    """附件暂存预览栏（置于输入框上方，显示所有已选择待发送的附件，空时自动隐藏）"""
    attachments_changed = pyqtSignal()

    def __init__(self, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.attachments = []
        self._init_ui()

    def _init_ui(self):
        self.main_lay = QHBoxLayout(self)
        self.main_lay.setContentsMargins(0, 0, 0, 4)
        self.main_lay.setSpacing(6)
        self.chips_lay = QHBoxLayout()
        self.chips_lay.setSpacing(6)
        self.main_lay.addLayout(self.chips_lay)
        self.main_lay.addStretch(1)
        self.hide()

    def add_attachment(self, file_info: dict):
        for item in self.attachments:
            if item.get("path") == file_info.get("path"):
                return
        self.attachments.append(file_info)
        self._refresh_chips()

    def remove_attachment(self, file_path: str):
        self.attachments = [a for a in self.attachments if a.get("path") != file_path]
        self._refresh_chips()

    def clear(self):
        self.attachments.clear()
        self._refresh_chips()

    def _refresh_chips(self):
        while self.chips_lay.count() > 0:
            child = self.chips_lay.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self.attachments:
            self.hide()
            self.attachments_changed.emit()
            return

        for item in self.attachments:
            chip = AttachmentChipWidget(item, is_dark=self.is_dark, parent=self)
            chip.removed.connect(self.remove_attachment)
            self.chips_lay.addWidget(chip)

        self.show()
        self.attachments_changed.emit()

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self._refresh_chips()


# ─────────────────────────── 添加/编辑模型对话框 ───────────────────────────

class AddModelDialog(QDialog):
    def __init__(self, parent=None, is_dark: bool = False, model_data: dict = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.model_data = model_data or {}
        is_edit = bool(model_data)
        self.setWindowTitle("编辑模型" if is_edit else "添加新模型")
        self.setMinimumSize(520, 560)
        self.resize(520, 560)
        self.setModal(True)
        self._result_data = None
        self._init_ui(is_edit)
        self._apply_style()

    def _init_ui(self, is_edit: bool):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 24, 28, 24)

        title = QLabel("✏️ 编辑模型配置" if is_edit else "➕ 添加新 AI 模型")
        title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        layout.addWidget(title)

        # 字段分组：垂直堆叠，每段"小标题 + 输入框"，去掉 QFormLayout 表格感
        form = QVBoxLayout()
        form.setSpacing(16)

        def _field(form_layout, label_text, widget):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {'#a1a1aa' if self.is_dark else '#475569'}; font-size: 11.5px; font-weight: 600; font-family: 'Microsoft YaHei UI'; margin-bottom: 2px;")
            form_layout.addWidget(lbl)
            form_layout.addWidget(widget)

        self.name_edit = QLineEdit(self.model_data.get("name", ""))
        self.name_edit.setPlaceholderText("例：GPT-4o-mini")
        self.name_edit.setFixedHeight(38)
        _field(form, "显示名称", self.name_edit)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["openai_compatible", "ollama", "custom"])
        prov = self.model_data.get("provider", "openai_compatible")
        idx = self.provider_combo.findText(prov)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.setFixedHeight(38)
        _field(form, "提供商", self.provider_combo)

        self.model_name_edit = QLineEdit(self.model_data.get("model_name", ""))
        self.model_name_edit.setPlaceholderText("例：gpt-4o-mini")
        self.model_name_edit.setFixedHeight(38)
        _field(form, "模型 ID", self.model_name_edit)

        self.api_url_edit = QLineEdit(self.model_data.get("api_base_url", ""))
        self.api_url_edit.setPlaceholderText("例：https://api.openai.com/v1")
        self.api_url_edit.setFixedHeight(38)
        _field(form, "API Base URL", self.api_url_edit)

        self.api_key_edit = QLineEdit(self.model_data.get("api_key", ""))
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("输入 API Key（无需则留空）")
        self.api_key_edit.setFixedHeight(38)
        _field(form, "API Key", self.api_key_edit)

        self.system_prompt_edit = QTextEdit()
        self.system_prompt_edit.setPlainText(
            self.model_data.get("system_prompt", "你是一个全能的桌面 AI 智能体助理。")
        )
        self.system_prompt_edit.setFixedHeight(90)
        _field(form, "系统提示词", self.system_prompt_edit)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(88, 38)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        ok_btn = QPushButton("✓ 保存模型")
        ok_btn.setFixedSize(130, 38)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok)
        btn_box.addWidget(ok_btn)
        layout.addLayout(btn_box)

    def _on_ok(self):
        name = self.name_edit.text().strip()
        model_name = self.model_name_edit.text().strip()
        api_url = self.api_url_edit.text().strip()
        if not name or not model_name:
            show_themed_warning(self, "提示", "请填写显示名称和模型 ID", self.is_dark)
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


# ─────────────────────────── 自定义 MCP 连接器配置对话框 (AddCustomConnectorDialog) ───────────────────────────

class AddCustomConnectorDialog(QDialog):
    """自定义 MCP 连接器配置对话框（支持 stdio 命令行与 SSE 远程服务配置，暗黑/浅色高质感设计）"""
    def __init__(self, parent=None, is_dark: bool = False, conn_data: dict = None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.conn_data = conn_data or {}
        is_edit = bool(conn_data)
        self.setWindowTitle("编辑自定义连接器" if is_edit else "添加自定义 MCP 连接器")
        self.setMinimumSize(540, 580)
        self.resize(540, 580)
        self.setModal(True)
        self._result_data = None
        self._init_ui(is_edit)
        self._apply_style()

    def _init_ui(self, is_edit: bool):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(28, 22, 28, 22)

        title = QLabel("✏️ 编辑自定义连接器" if is_edit else "🧩 添加自定义 MCP 连接器")
        title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        layout.addWidget(title)

        form = QVBoxLayout()
        form.setSpacing(12)

        def _field(form_layout, label_text, widget):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {'#a1a1aa' if self.is_dark else '#475569'}; font-size: 11.5px; font-weight: 600; font-family: 'Microsoft YaHei UI'; margin-bottom: 2px;")
            form_layout.addWidget(lbl)
            form_layout.addWidget(widget)

        self.name_edit = QLineEdit(self.conn_data.get("name", ""))
        self.name_edit.setPlaceholderText("例：sqlite-mcp 或 本地知识库工具")
        self.name_edit.setFixedHeight(36)
        _field(form, "连接器显示名称 *", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["stdio (本地命令行 / npx / uvx / Python)", "SSE (HTTP 远程接口 / URL)"])
        saved_type = self.conn_data.get("type", "stdio")
        if saved_type == "sse":
            self.type_combo.setCurrentIndex(1)
        self.type_combo.setFixedHeight(36)
        _field(form, "协议与传输类型 *", self.type_combo)

        self.cmd_edit = QLineEdit(self.conn_data.get("command", ""))
        self.cmd_edit.setPlaceholderText("例：npx 或 uvx 或 python 或 D:/tools/my_mcp.exe")
        self.cmd_edit.setFixedHeight(36)
        _field(form, "启动命令 / 可执行程序 *", self.cmd_edit)

        # 参数 / URL
        raw_args = self.conn_data.get("args", [])
        args_str = " ".join(raw_args) if isinstance(raw_args, list) else str(raw_args)
        self.args_edit = QLineEdit(args_str)
        self.args_edit.setPlaceholderText("例：-y @modelcontextprotocol/server-sqlite --db-path ./test.db")
        self.args_edit.setFixedHeight(36)
        _field(form, "命令行参数 (空格分隔) 或 SSE 接口 URL", self.args_edit)

        # 环境变量
        env_val = self.conn_data.get("env", {})
        if isinstance(env_val, dict):
            env_str = ", ".join([f"{k}={v}" for k, v in env_val.items()])
        else:
            env_str = str(env_val)
        self.env_edit = QLineEdit(env_str)
        self.env_edit.setPlaceholderText("例：API_KEY=sk-xxxx, DB_PORT=5432 (可选，逗号分隔)")
        self.env_edit.setFixedHeight(36)
        _field(form, "环境变量 (KEY=VALUE，逗号分隔)", self.env_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(self.conn_data.get("desc", ""))
        self.desc_edit.setPlaceholderText("填写该 MCP 连接器的功能说明与使用场景...")
        self.desc_edit.setFixedHeight(64)
        _field(form, "功能描述与提示", self.desc_edit)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(88, 38)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        ok_btn = QPushButton("✓ 保存并启用")
        ok_btn.setFixedSize(130, 38)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok)
        btn_box.addWidget(ok_btn)
        layout.addLayout(btn_box)

    def _on_ok(self):
        name = self.name_edit.text().strip()
        cmd = self.cmd_edit.text().strip()
        if not name:
            show_themed_warning(self, "提示", "请填写连接器显示名称", self.is_dark)
            return
        if not cmd:
            show_themed_warning(self, "提示", "请填写启动命令或可执行程序路径", self.is_dark)
            return

        import uuid
        cid = self.conn_data.get("id") or f"custom_mcp_{uuid.uuid4().hex[:8]}"

        # 解析参数
        raw_args_text = self.args_edit.text().strip()
        import shlex
        try:
            parsed_args = shlex.split(raw_args_text) if raw_args_text else []
        except Exception:
            parsed_args = raw_args_text.split() if raw_args_text else []

        # 解析环境变量
        env_dict = {}
        raw_env = self.env_edit.text().strip()
        if raw_env:
            for item in raw_env.split(","):
                if "=" in item:
                    k, v = item.split("=", 1)
                    if k.strip():
                        env_dict[k.strip()] = v.strip()

        ptype = "sse" if "SSE" in self.type_combo.currentText() else "stdio"

        self._result_data = {
            "id": cid,
            "name": name,
            "char": name[0] if name else "自",
            "color": "#8b5cf6",
            "desc": self.desc_edit.toPlainText().strip() or f"自定义 {name} MCP 连接器服务",
            "type": ptype,
            "command": cmd,
            "args": parsed_args,
            "env": env_dict,
            "is_custom": True
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
            QComboBox QAbstractItemView {{
                background-color: {inp_bg}; color: {fg}; selection-background-color: #6366f1;
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

        # 1. 顶部选项：不关联工作空间（无空间独立任务）
        btn_none = QPushButton()
        btn_none.setFixedHeight(36)
        btn_none.setCursor(Qt.PointingHandCursor)
        btn_none.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 8px;
                padding: 0 8px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {hover};
            }}
        """)
        btn_none_l = QHBoxLayout(btn_none)
        btn_none_l.setContentsMargins(4, 0, 4, 0)
        btn_none_l.setSpacing(8)

        icon_none = QLabel()
        icon_none.setFixedSize(14, 14)
        icon_none.setStyleSheet("background: transparent;")
        icon_none.setPixmap(load_ui_icon("minus", "#a1a1aa" if d else "#64748b", 14).pixmap(QSize(14, 14)))
        btn_none_l.addWidget(icon_none)

        name_none = QLabel("不关联工作空间")
        name_none.setStyleSheet(f"font-size: 12px; color: {fg}; font-family: 'Microsoft YaHei UI';")
        btn_none_l.addWidget(name_none, 1)

        btn_none.clicked.connect(lambda ch: self._on_select({"name": "", "path": ""}))
        lay.addWidget(btn_none)

        if not self.workspaces:
            empty_tip = QLabel("暂无工作空间（可点击下方新建）")
            empty_tip.setStyleSheet(f"font-size: 11px; color: {sub_fg}; padding: 6px 8px; font-family: 'Microsoft YaHei UI';")
            lay.addWidget(empty_tip)

        for ws in self.workspaces:
            name = ws.get("name", "未命名空间")
            path = ws.get("path", "")

            btn = QPushButton()
            btn.setFixedHeight(38)
            btn.setCursor(Qt.PointingHandCursor)
            # 不再默认勾选任何项（用户没主动选择前全部平级显示）
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
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

            icon_lbl = QLabel()
            icon_lbl.setFixedSize(14, 14)
            icon_lbl.setStyleSheet("background: transparent;")
            icon_lbl.setPixmap(load_ui_icon("folder", "#a1a1aa" if d else "#64748b", 14).pixmap(QSize(14, 14)))
            btn_l.addWidget(icon_lbl)

            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(f"font-size: 12px; color: {fg}; font-family: 'Microsoft YaHei UI';")
            btn_l.addWidget(name_lbl, 1)

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
        self.setMinimumSize(320, 160)
        self.setMaximumSize(420, 520)
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
        self.search_input.setPlaceholderText("搜索任务名称或内容...")
        self.search_input.setFixedHeight(34)
        search_action = QAction(load_ui_icon("search", "#a1a1aa" if d else "#64748b", 14), "", self.search_input)
        self.search_input.addAction(search_action, QLineEdit.LeadingPosition)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {'#27272a' if d else '#f8fafc'};
                color: {fg};
                border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
            QLineEdit:focus {{ border: 1px solid #6366f1; }}
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
                padding: 8px 10px;
                border-radius: 6px;
            }}
            QListWidget::item:hover {{
                background: {'#27272a' if d else '#f1f5f9'};
            }}
            QListWidget::item:selected {{
                background: #6366f1;
                color: #ffffff;
            }}
            QScrollBar:vertical{{width:6px;background:transparent;border:none;margin:0;}}
            QScrollBar::handle:vertical{{background:{'#3e4451' if d else '#cbd5e1'};border-radius:3px;min-height:24px;border:none;}}
            QScrollBar::handle:vertical:hover{{background:{'#5c6370' if d else '#94a3b8'};}}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical{{height:0;width:0;background:transparent;border:none;}}
        """)
        self.list_w.itemClicked.connect(self._on_item_clicked)
        lay.addWidget(self.list_w, 1)

        self._populate_list(self.sessions)
        # 根据内容动态调整高度：每个项 32px 估算 + 搜索框 50px + 边距 30px
        item_h = 36
        ideal_h = min(520, max(160, 50 + item_h * len(self.sessions) + 30))
        self.resize(360, ideal_h)
        outer_lay.addWidget(inner)

    def _populate_list(self, sessions: List[dict]):
        self.list_w.clear()
        for s in sessions:
            title = s.get("title", "未命名会话")
            sid = s.get("id")
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, sid)
            item.setIcon(load_ui_icon("chat", "#a1a1aa" if self.is_dark else "#64748b", 14))
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
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
        """)
        scroll.viewport().setStyleSheet("background: transparent;")
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(4)

        # 增加“不使用技能 / 清空”选项
        clear_btn = QPushButton("✕ 不使用特定技能 (默认)")
        clear_btn.setFixedHeight(30)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {sub_fg}; border: none; border-radius: 6px;
                text-align: left; padding: 0 8px; font-size: 11.5px; font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{ background: {hover}; color: {fg}; }}
        """)
        clear_btn.clicked.connect(lambda: self._on_choose("", ""))
        c_lay.addWidget(clear_btn)

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
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
        """)
        scroll.viewport().setStyleSheet("background: transparent;")
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(4)

        # 增加“不指定专家 / 默认”选项
        clear_exp_btn = QPushButton("✕ 不指定专家 (默认通用助手)")
        clear_exp_btn.setFixedHeight(30)
        clear_exp_btn.setCursor(Qt.PointingHandCursor)
        clear_exp_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {sub_fg}; border: none; border-radius: 6px;
                text-align: left; padding: 0 8px; font-size: 11.5px; font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{ background: {hover}; color: {fg}; }}
        """)
        clear_exp_btn.clicked.connect(lambda: self._on_choose("", ""))
        c_lay.addWidget(clear_exp_btn)

        try:
            from core.ai_engine import EXPERTS_MAP
            experts = list(EXPERTS_MAP.values())
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


class ModernTimeEdit(QComboBox):
    """
    现代可编辑时间选择下拉框：
    - 预置常用整点与半点时间项 (00:00 ~ 23:30)，一键点击秒选
    - 支持自由键盘键入任意时间 (如 06:05、14:23)
    - 鼠标滚轮在输入框上滑动时，支持以 5 分钟步长快捷增减时间
    - 彻底消灭 Windows 原生微调上下双小方块，高质感现代深色/浅色适配
    - API 兼容 QTimeEdit: time(), setTime(), setDisplayFormat(), text()
    """
    timeChanged = pyqtSignal(QTime)

    def __init__(self, parent=None, is_dark=True):
        super().__init__(parent)
        self.is_dark = is_dark
        self.setEditable(True)
        self.setMaxVisibleItems(10)
        self.setInsertPolicy(QComboBox.NoInsert)
        
        # 填充常用整点与半点
        for h in range(24):
            for m in (0, 30):
                self.addItem(f"{h:02d}:{m:02d}")
                
        # 默认当前时间
        self._current_time = QTime.currentTime()
        self.setTime(self._current_time)
        
        le = self.lineEdit()
        if le:
            le.setAlignment(Qt.AlignCenter)
            le.editingFinished.connect(self._on_editing_finished)

        v = self.view()
        if v:
            v.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
        self.currentIndexChanged.connect(self._on_index_changed)

    def _on_index_changed(self, idx):
        if idx >= 0:
            t = self.time()
            self._current_time = t
            self.timeChanged.emit(t)

    def _on_editing_finished(self):
        t = self.time()
        self.setTime(t)
        self.timeChanged.emit(t)

    def time(self) -> QTime:
        txt = self.currentText().strip().replace("🕒", "").strip()
        try:
            parts = txt.split(":")
            if len(parts) >= 2:
                h = max(0, min(23, int(parts[0])))
                m = max(0, min(59, int(parts[1])))
                return QTime(h, m)
        except Exception:
            pass
        return self._current_time or QTime.currentTime()

    def setTime(self, qt: QTime):
        if not qt or not qt.isValid():
            return
        self._current_time = qt
        t_str = f"{qt.hour():02d}:{qt.minute():02d}"
        idx = self.findText(t_str)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.setEditText(t_str)

    def setDisplayFormat(self, fmt):
        pass

    def wheelEvent(self, e):
        # 滚轮支持 5 分钟步长快捷增减时间
        steps = e.angleDelta().y() // 120
        if steps != 0:
            cur = self.time()
            total_min = (cur.hour() * 60 + cur.minute() + steps * 5) % (24 * 60)
            if total_min < 0:
                total_min += 24 * 60
            new_t = QTime(total_min // 60, total_min % 60)
            self.setTime(new_t)
            self.timeChanged.emit(new_t)
            e.accept()
            return
        super().wheelEvent(e)


class WeComConfigDialog(QDialog):
    """企业微信群机器人 Webhook 配置与测试对话框"""
    def __init__(self, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.setWindowTitle("企业微信群机器人配置")
        self.setFixedSize(500, 270)
        self._init_ui()

    def _init_ui(self):
        d = self.is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        fg = "#f4f4f5" if d else "#0f172a"
        sub_fg = "#a1a1aa" if d else "#64748b"
        border = "#2e2e2e" if d else "#e2e8f0"
        self.setStyleSheet(f"QDialog {{ background-color: {bg}; color: {fg}; }}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        title = QLabel("💼 企业微信群机器人 (WeCom Webhook)")
        title.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        title.setStyleSheet(f"color: {fg};")
        lay.addWidget(title)

        desc = QLabel("在企业微信群中点击【群设置】->【添加群机器人】，将生成的 Webhook 完整地址粘贴在下方。自动化任务触发执行后，机器人将自动向该群推送结果报告。")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {sub_fg}; font-size: 11.5px; line-height: 1.4;")
        lay.addWidget(desc)

        from core.mobile_push import get_push_config, save_push_config, send_wecom_webhook
        conf = get_push_config()

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...")
        self.url_edit.setText(conf.get("wecom_webhook", ""))
        self.url_edit.setFixedHeight(36)
        self.url_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {'#27272a' if d else '#f8fafc'};
                color: {fg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: #6366f1; }}
        """)
        lay.addWidget(self.url_edit)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size: 11px;")
        lay.addWidget(self.status_lbl)

        btn_row = QHBoxLayout()
        test_btn = QPushButton("🚀 发送测试消息")
        test_btn.setFixedHeight(34)
        test_btn.setCursor(Qt.PointingHandCursor)
        test_btn.setStyleSheet(f"""
            QPushButton {{
                background: {'#3f3f46' if d else '#f1f5f9'};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 0 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: {'#52525b' if d else '#e2e8f0'}; }}
        """)
        test_btn.clicked.connect(self._test_push)
        btn_row.addWidget(test_btn)

        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(70, 34)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(f"background: transparent; color: {sub_fg}; border: none; font-size: 12px;")
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("保存配置")
        save_btn.setFixedSize(84, 34)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #6366f1; color: #ffffff; border: none;
                border-radius: 6px; font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { background: #4f46e5; }
        """)
        save_btn.clicked.connect(self._save_config)
        btn_row.addWidget(save_btn)

        lay.addLayout(btn_row)

    def _test_push(self):
        url = self.url_edit.text().strip()
        if not url:
            self.status_lbl.setText("❌ 请先输入有效的企业微信 Webhook 地址")
            self.status_lbl.setStyleSheet("color: #ef4444; font-size: 11px;")
            return
        from core.mobile_push import send_wecom_webhook
        self.status_lbl.setText("⏳ 正在向企业微信发送测试消息...")
        self.status_lbl.setStyleSheet("color: #38bdf8; font-size: 11px;")
        QApplication.processEvents()
        ok, msg = send_wecom_webhook(url, "NovaDesk 连通性测试", "🎉 恭喜！NovaDesk 企业微信机器人通道已成功连通！后续自动化任务将实时推送到此群。")
        if ok:
            self.status_lbl.setText(f"✅ {msg}")
            self.status_lbl.setStyleSheet("color: #22c55e; font-size: 11px;")
        else:
            self.status_lbl.setText(f"❌ {msg}")
            self.status_lbl.setStyleSheet("color: #ef4444; font-size: 11px;")

    def _save_config(self):
        url = self.url_edit.text().strip()
        from core.mobile_push import save_push_config
        save_push_config(wecom_webhook=url)
        self.accept()


class WeChatConfigDialog(QDialog):
    """手机个人微信推送 (Server酱/PushDeer/Webhook) 配置与测试对话框"""
    def __init__(self, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self.is_dark = is_dark
        self.setWindowTitle("手机微信推送配置")
        self.setFixedSize(500, 300)
        self._init_ui()

    def _init_ui(self):
        d = self.is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        fg = "#f4f4f5" if d else "#0f172a"
        sub_fg = "#a1a1aa" if d else "#64748b"
        border = "#2e2e2e" if d else "#e2e8f0"
        self.setStyleSheet(f"QDialog {{ background-color: {bg}; color: {fg}; }}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        title = QLabel("📲 手机个人微信通知 (Server酱 / PushDeer)")
        title.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        title.setStyleSheet(f"color: {fg};")
        lay.addWidget(title)

        desc = QLabel(
            "通过微信服务号直接推送提醒到您的手机：\n"
            "• 方式 1：打开 Server酱 (sct.ftqq.com)，扫码关注公众号并获取 SendKey (以 SCT 开头)\n"
            "• 方式 2：使用 PushDeer (pushdeer.com) 的 PushKey (以 PDU 开头)\n"
            "• 方式 3：自定义 HTTP POST Webhook 地址"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {sub_fg}; font-size: 11.5px; line-height: 1.4;")
        lay.addWidget(desc)

        from core.mobile_push import get_push_config, save_push_config, send_wechat_notification
        conf = get_push_config()

        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("填入 SendKey (如 SCTxxxxxxxx 或 PDUxxxx 或 Webhook URL)")
        self.key_edit.setText(conf.get("wechat_sendkey", ""))
        self.key_edit.setFixedHeight(36)
        self.key_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {'#27272a' if d else '#f8fafc'};
                color: {fg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: #6366f1; }}
        """)
        lay.addWidget(self.key_edit)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-size: 11px;")
        lay.addWidget(self.status_lbl)

        btn_row = QHBoxLayout()
        test_btn = QPushButton("🚀 发送测试消息到手机")
        test_btn.setFixedHeight(34)
        test_btn.setCursor(Qt.PointingHandCursor)
        test_btn.setStyleSheet(f"""
            QPushButton {{
                background: {'#3f3f46' if d else '#f1f5f9'};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 0 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: {'#52525b' if d else '#e2e8f0'}; }}
        """)
        test_btn.clicked.connect(self._test_push)
        btn_row.addWidget(test_btn)

        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(70, 34)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(f"background: transparent; color: {sub_fg}; border: none; font-size: 12px;")
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("保存配置")
        save_btn.setFixedSize(84, 34)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #10b981; color: #ffffff; border: none;
                border-radius: 6px; font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { background: #059669; }
        """)
        save_btn.clicked.connect(self._save_config)
        btn_row.addWidget(save_btn)

        lay.addLayout(btn_row)

    def _test_push(self):
        key = self.key_edit.text().strip()
        if not key:
            self.status_lbl.setText("❌ 请先输入 SendKey 或 Webhook 地址")
            self.status_lbl.setStyleSheet("color: #ef4444; font-size: 11px;")
            return
        from core.mobile_push import send_wechat_notification
        self.status_lbl.setText("⏳ 正在向手机微信通道发送测试消息...")
        self.status_lbl.setStyleSheet("color: #38bdf8; font-size: 11px;")
        QApplication.processEvents()
        ok, msg = send_wechat_notification(key, "NovaDesk 手机微信连通测试", "🎉 恭喜！手机微信推送已成功打通！后续自动化任务到期执行完成后，将第一时间把任务总结推送到您的手机。")
        if ok:
            self.status_lbl.setText(f"✅ {msg}")
            self.status_lbl.setStyleSheet("color: #22c55e; font-size: 11px;")
        else:
            self.status_lbl.setText(f"❌ {msg}")
            self.status_lbl.setStyleSheet("color: #ef4444; font-size: 11px;")

    def _save_config(self):
        key = self.key_edit.text().strip()
        from core.mobile_push import save_push_config
        save_push_config(wechat_sendkey=key)
        self.accept()


# ═══════════════════════════════════════════════════════════════
#  ChatWindow  —  主窗口
# ═══════════════════════════════════════════════════════════════

class _ResizeHandle(QWidget):
    """无边框窗口的边缘/角落缩放句柄"""
    def __init__(self, parent, edge: str):
        super().__init__(parent)
        self._edge = edge
        self.setStyleSheet("background: transparent;")
        # 设置光标形状
        if edge in ("left", "right"):
            self.setCursor(Qt.SizeHorCursor)
        elif edge in ("top", "bottom"):
            self.setCursor(Qt.SizeVerCursor)
        elif edge in ("top-left", "bottom-right"):
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.SizeBDiagCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.window()._begin_resize(self._edge, e.globalPos())
            e.accept()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self.window()._do_resize(e.globalPos())
            e.accept()

    def mouseReleaseEvent(self, e):
        self.window()._end_resize()
        e.accept()


HERO_SCENARIOS_MAP = {
    "代码开发": {
        "icon": "💻",
        "sub_scenarios": [
            {
                "id": "daily_dev",
                "icon": "</>",
                "name": "日常开发",
                "templates": [
                    ("Python 算法实现 ↘", "请帮我实现一个高效的 Python 异步并发处理算法，包含异常处理与性能基准测试。"),
                    ("API 接口编写 ↘", "请帮我设计并编写一套 RESTful API 接口，包含请求参数校验、业务逻辑与 JSON 响应封装。"),
                    ("Bug 诊断与修复 ↘", "我遇到了一段代码报错，请帮我分析潜在的边界异常、内存泄漏或死锁问题并给出修复方案：\n"),
                    ("代码重构优化 ↘", "请帮我重构优化以下代码，遵循 SOLID 原则、降低圈复杂度并提高可测试性：\n")
                ]
            },
            {
                "id": "web_dev",
                "icon": "🌐",
                "name": "网站开发",
                "templates": [
                    ("企业官网开发 ↘", "请调用 web_development 技能，帮我生成一套现代化高端企业官方网站（HTML5/CSS3/JS），包含 Hero 头部、特性展示、解决方案与响应式布局。"),
                    ("后台管理系统 ↘", "请调用 web_development 技能，帮我构建一个现代化的数据后台管理控制台（Admin Dashboard），包含侧边导航、KPI 仪表盘卡片与订单数据表格。"),
                    ("个人博客网站 ↘", "请帮我设计并生成一个优雅的个人技术博客站点，支持文章卡片流、标签分类与阅读模式。"),
                    ("电商首页开发 ↘", "请帮我开发一个高转化率的电商产品展示首页，包含焦点轮播图、商品货架分类与购物车结算交互。")
                ]
            },
            {
                "id": "agent_app",
                "icon": "🤖",
                "name": "Agent 应用",
                "templates": [
                    ("多智能体编排 ↘", "请调用 agent_development 技能，帮我设计一个多智能体协同架构，拆解 Planner、Executor 与 Reviewer 的分工与交互协议。"),
                    ("自定义工作流开发 ↘", "请帮我构建一个自动化的业务处理 Agent 工作流，包含触发条件、工具调用链与回退重试策略。"),
                    ("工具调用链设计 ↘", "请帮我规划设计一组符合标准规范的 Agent 工具函数签名与参数定义。"),
                    ("知识库 RAG 增强 ↘", "请帮我设计一套基于本地向量检索与知识库文档的 Agent 问答增强检索流水线。")
                ]
            },
            {
                "id": "skill_dev",
                "icon": "🔨",
                "name": "Skill 开发",
                "templates": [
                    ("创建新 Skill 插件 ↘", "请调用 skill_creator 技能，帮我在项目中自动生成一个全新的 Skill 规范套件（包含 SKILL.md 与配套 Python 插件）。"),
                    ("MCP 工具注册 ↘", "请帮我编写一个标准的 MCP 工具函数，包含 @register_tool 装饰器、入参类型注解与详细 docstring。"),
                    ("编写 SKILL.md 规范 ↘", "请帮我为新工具编写完整的 YAML frontmatter 元数据与场景使用说明。"),
                    ("插件单元测试 ↘", "请帮我为当前插件工具集编写一套健壮的自动化单元测试用例。")
                ]
            },
            {
                "id": "cicd",
                "icon": "🔗",
                "name": "CI/CD",
                "templates": [
                    ("GitHub Actions 配置 ↘", "请调用 cicd_automation 技能，为当前项目生成生产级的 .github/workflows/ci.yml 自动化测试与构建流水线。"),
                    ("自动化测试流水线 ↘", "请帮我设计一套自动化代码 Lint、类型检查与 Pytest 测试流。"),
                    ("Docker 镜像构建 ↘", "请调用 cicd_automation 技能，为项目生成优化的多阶段构建 Dockerfile 与 docker-compose.yml。"),
                    ("部署脚本编写 ↘", "请帮我编写一段安全可靠的一键自动化部署 Shell/PowerShell 脚本。")
                ]
            },
            {
                "id": "doc_eng",
                "icon": "📄",
                "name": "文档",
                "templates": [
                    ("项目 README 编写 ↘", "请调用 doc_engineering 技能，为当前项目自动生成一份符合顶级开源规范的专业 README.md 文档。"),
                    ("API 文档生成 ↘", "请扫描项目源码，提取所有核心类与函数的 docstring 并生成 Markdown 格式的 API 接口参考手册。"),
                    ("架构设计说明书 ↘", "请帮我撰写一份系统的技术架构设计方案，包含模块分层、数据流图与核心交互时序。"),
                    ("使用手册撰写 ↘", "请为终端用户编写一份步骤清晰、图文并茂的软件操作使用手册。")
                ]
            }
        ]
    },
    "日常办公": {
        "icon": "☕",
        "sub_scenarios": [
            {
                "id": "data_analysis",
                "icon": "📊",
                "name": "数据分析",
                "templates": [
                    ("Excel 自动透视分析 ↘", "请读取我上传的数据表格，进行多维透视汇总、异常值检测并提取核心业务洞察。"),
                    ("数据清洗与转换 ↘", "请帮我编写一段数据清洗脚本，处理缺失值、重复项与日期格式标准化。"),
                    ("图表可视化生成 ↘", "请利用 matplotlib/seaborn 绘制柱状图、趋势折线图与占比饼图并保存为高清图片。"),
                    ("统计报表输出 ↘", "请根据业务数据生成一份包含环比、同比与核心指标总结的周度经营分析报表。")
                ]
            },
            {
                "id": "doc_proc",
                "icon": "📄",
                "name": "文档处理",
                "templates": [
                    ("Word 文档排版 ↘", "请帮我规范化整理这份文档的标题层级、字体样式、段落行距与项目符号。"),
                    ("PDF 提取与转换 ↘", "请解析提取 PDF 文档中的所有文字与表格数据，并转换为结构化 Markdown 格式。"),
                    ("长文档摘要提炼 ↘", "请深度提炼这篇长文档的核心结论、关键数据与后续行动建议。"),
                    ("合同条款审查 ↘", "请帮我核对这份协议条款中的权责约定、违约责任与潜在法律合规风险。")
                ]
            },
            {
                "id": "ppt_pres",
                "icon": "🖥️",
                "name": "幻灯片制作",
                "templates": [
                    ("商业计划书 PPT ↘", "请调用 ppt_master 技能，帮我生成一份 10 页高端商业计划书 PPT，包含痛点、解决方案与商业模式。"),
                    ("工作汇报 PPT ↘", "请帮我制作一份季度工作总结与复盘汇报 PPT，突出核心产出与下一步规划。"),
                    ("产品发布演讲稿 ↘", "请为新产品发布会设计一份引人入胜的演说大纲与逐页幻灯片内容。"),
                    ("技术分享幻灯片 ↘", "请围绕技术架构演进主题生成一份专业的技术分享 PPT 提纲。")
                ]
            },
            {
                "id": "email_org",
                "icon": "✉️",
                "name": "邮件整理",
                "templates": [
                    ("商务邮件润色 ↘", "请帮我把以下草稿润色为语气得体、专业干练的商务合作沟通邮件：\n"),
                    ("周报邮件草拟 ↘", "请根据本周完成的任务清单，生成一份格式标准的部门周报邮件。"),
                    ("通知公告撰写 ↘", "请帮我撰写一份关于系统升级维护与服务暂停的正式公司通知。"),
                    ("会议纪要提炼 ↘", "请把以下会议发言记录提炼为包含决议事项与责任人的会议纪要邮件。")
                ]
            },
            {
                "id": "wechat_pub",
                "icon": "💬",
                "name": "微信公众号分析",
                "templates": [
                    ("公众号爆文拆解 ↘", "请调用 wechat_tools 技能，深度拆解目标微信公众号文章的选题逻辑、引流标题与行文结构。"),
                    ("文章核心观点提炼 ↘", "请提取微信文章的主题思想、论据论点与金句摘录。"),
                    ("传播数据归纳 ↘", "请分析该文章的传播受众心理、互动槽点与完读驱动力。"),
                    ("排版结构优化 ↘", "请帮我将以下文稿优化为适合微信手机端阅读的呼吸感排版样式。")
                ]
            },
            {
                "id": "travel_trip",
                "icon": "🚆",
                "name": "差旅出行",
                "templates": [
                    ("12306 车票查询 ↘", "请调用 ticket_12306 技能，帮我查询明天从北京到上海的高铁车次余票与时刻表。"),
                    ("高德周边生活规划 ↘", "请调用 amap_lbs 技能，规划出差酒店周边 2 公里内的商务餐厅与交通路线。"),
                    ("出差行程规划 ↘", "请帮我制定一份为期 3 天的高效商务出差行程安排与行李清单。"),
                    ("快递物流追踪 ↘", "请调用 kuaidi100 技能，帮我查询顺丰/京东快递单号的最新在途物流轨迹。")
                ]
            }
        ]
    },
    "设计创意": {
        "icon": "🎨",
        "sub_scenarios": [
            {
                "id": "xhs_copy",
                "icon": "📝",
                "name": "爆款小红书",
                "templates": [
                    ("小红书爆款标题 ↘", "请针对【主题】，生成 10 个高点击率的爆款小红书二极管标题（包含数字、痛点与情绪词）。"),
                    ("种草文案带货 ↘", "请调用 xiaohongshu_article 技能，生成一篇高互动率的真实体验式种草带货笔记。"),
                    ("干货合集文案 ↘", "请撰写一篇干货满满的收藏级小红书攻略长图文文案，包含步骤序号与重点 Emoji。"),
                    ("一键配图与标签 ↘", "请为该主题推荐 5 张爆款封面拍摄构图建议与 10 个高流量小红书话题标签。")
                ]
            },
            {
                "id": "creative_art",
                "icon": "✨",
                "name": "创意文章",
                "templates": [
                    ("故事叙事创作 ↘", "请以富有张力的镜头感，创作一个充满反转与温情的科幻职场故事。"),
                    ("公众号深度长文 ↘", "请就当下的科技趋势撰写一篇 2500 字有深度、有洞察的行业评论长文。"),
                    ("营销广告文案 ↘", "请为一款智能硬件产品撰写一组打动人心的电梯海报与社交媒体宣传文案。"),
                    ("品牌品牌故事 ↘", "请为初创科技品牌撰写一段富有情怀与使命感的品牌创立故事。")
                ]
            },
            {
                "id": "video_script",
                "icon": "🎬",
                "name": "视频脚本",
                "templates": [
                    ("口播科普脚本 ↘", "请调用 video_script_creator 技能，策划一份 60 秒黄金完播率的科技科普口播短视频分镜脚本。"),
                    ("剧情短剧大纲 ↘", "请设计一份 3 集连续短剧的故事大纲、人物小传与每集反转悬念钩子。"),
                    ("产品宣传片分镜 ↘", "请为新产品概念片输出包含景别、运镜、配乐与画面的工业级分镜表格。"),
                    ("直播带货话术 ↘", "请设计一套直播间 5 分钟憋单、逼单与高潮放福利的连环话术。")
                ]
            },
            {
                "id": "visual_design",
                "icon": "🎨",
                "name": "视觉海报",
                "templates": [
                    ("主视觉 Banner 构思 ↘", "请为科技主题活动设计一套包含光影、空间层次与色彩对比的主视觉设计构思。"),
                    ("宣传海报文案 ↘", "请提炼出一组极具视觉冲击力的主副标题与海报金句。"),
                    ("UI 界面原型设计 ↘", "请为移动端 App 规划一套符合现代设计美学的信息架构与页面线框图说明。"),
                    ("配色方案推荐 ↘", "请推荐一套 5 色系的暗黑赛博/现代极简色彩搭配方案（包含 HEX 与语义用途）。")
                ]
            }
        ]
    }
}


class ChatWindow(QWidget):
    """NovaDesk v4.0 主工作台 (WorkBuddy 复刻)"""
    message_chunk_signal = pyqtSignal(int, int, str)  # (session_id, stream_id, full_text)
    message_done_signal  = pyqtSignal(int, int, str)  # (session_id, stream_id, full_text)
    message_error_signal = pyqtSignal(int, int, str)  # (session_id, stream_id, error_str)
    test_done_signal     = pyqtSignal(bool, str)

    def __init__(self, config: dict, ai_engine,
                 pet_window=None, save_config_fn=None):
        super().__init__()
        self.config          = config
        self.ai_engine       = ai_engine
        self.pet_window      = pet_window
        self.save_config_fn  = save_config_fn
        self.memory          = getattr(ai_engine, "memory", None)
        if not self.memory:
            try:
                from core.memory_manager import MemoryManager
                self.memory = MemoryManager(ROOT_DIR / "memory.db")
            except Exception:
                pass

        self._is_dark        = (config.get("ui_theme", "light") == "dark")
        self._is_maximized   = False
        self._normal_geometry = None
        self._current_ai_block = None
        self._current_session_id = None
        self._active_streams: Dict[int, dict] = {}  # session_id -> {"stream_id": int, "full_text": str, "is_stopped": bool, "user_msg": str}
        self._session_message_queues: Dict[int, List[str]] = {}  # session_id -> [queued_msg_1, queued_msg_2, ...]
        self._stream_counter = 0
        self._message_blocks: List[MessageBlock] = []
        self._session_collapsed = False
        self._ws_collapsed   = False
        self._installed_skills = set(config.get("plugins", {}).get("enabled", []))
        self._active_primary_cat = "代码开发"
        self._active_sub_scenario = None
        self._primary_cat_btns = {}
        self._sub_scen_buttons = []
        self._template_buttons = []
        self._selected_model = "⚙️ Auto"
        self._selected_skill = {}
        self._selected_expert = {}
        self._selected_permission = "full"
        self._editing_task_id = None

        if "workspaces" in config and isinstance(config["workspaces"], list):
            self.workspaces = config["workspaces"]
        else:
            self.workspaces = [
                {"name": "Study笔记", "path": str(ROOT_DIR / "Study笔记")},
                {"name": "Agent开发", "path": str(ROOT_DIR / "Agent开发")},
                {"name": "langchain_demo", "path": str(ROOT_DIR / "langchain_demo")},
                {"name": "tjxt", "path": str(ROOT_DIR / "tjxt")},
                {"name": "Spring_AI_MCP", "path": str(ROOT_DIR / "Spring_AI_MCP")},
            ]
        # 启动时强制折叠非当前空间
        cur_ws = config.get("current_workspace_name", "")
        for ws in self.workspaces:
            if ws.get("name") != cur_ws:
                ws["collapsed"] = True
        config["workspaces"] = self.workspaces
        for ws in self.workspaces:
            try:
                os.makedirs(ws.get("path", ""), exist_ok=True)
            except Exception:
                pass
        self.current_workspace_name = config.get("current_workspace_name", "")
        self.current_workspace_path = config.get("workspace_dir", "")
        self.current_permission     = config.get("permission_mode", "standard")
        try:
            from core.security_guard import SecurityGuard
            guard = SecurityGuard.get_instance()
            if self.current_workspace_path:
                guard.set_workspace_root(self.current_workspace_path)
            guard.set_mode(self.current_permission)
        except Exception:
            pass

        self.setWindowTitle("NovaDesk v4.0")
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self._init_window()
        self._build_ui()
        self._connect_signals()
        self._init_or_load_latest_session()
        # 自适应网格列数：根据主内容区宽度计算每页 (专家/技能/连接器) 网格的列数
        self._col_max = 3
        self._last_resize_bucket = -1
        # 定期刷新侧栏正在生成状态（spinner 实时跟随）
        self._generating_status_timer = QTimer(self)
        self._generating_status_timer.setInterval(800)
        self._generating_status_timer.timeout.connect(self._refresh_generating_status)
        self._generating_status_timer.start()

    def _show_status(self, text: str):
        """控制台日志与桌面桌宠气泡反馈"""
        print(f"[Status] {text}")
        try:
            if hasattr(self, 'pet_window') and self.pet_window and hasattr(self.pet_window, 'show_bubble'):
                self.pet_window.show_bubble(text, duration=3500)
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 缩放句柄跟随窗口尺寸重排（全屏时会自动隐藏）
        self._layout_resize_handles()
        if not hasattr(self, 'main_stack'):
            return
        # 【核心性能突破】：仅当用户当前真正位于【专家·技能大厅】(index == 1) 时才重排网格；
        # 在聊天主页(0)、自动化(2)或设置(3)时仅打上脏标记，切页时按需排布，彻底根除缩放全屏时的百毫秒主线程卡顿！
        if self.main_stack.currentIndex() != 1:
            self._grid_needs_relayout = True
            return
        self._check_and_update_grid_cols()

    def _relayout_grid(self, grid, new_cols: int):
        """轻量级网格重定位：仅调整现有卡片在 QGridLayout 中的 (row, col)，绝不暴力销毁重建组件 (耗时 < 0.1ms)"""
        if not grid:
            return
        count = grid.count()
        if count == 0:
            return
        widgets = []
        for i in range(count):
            item = grid.itemAt(i)
            if item and item.widget():
                widgets.append(item.widget())
        for idx, w in enumerate(widgets):
            row = idx // new_cols
            col = idx % new_cols
            grid.addWidget(w, row, col)

    def _check_and_update_grid_cols(self):
        """检查并毫秒级重排专家、技能与连接器大厅的列数"""
        if not hasattr(self, 'main_stack'):
            return
        w = self.main_stack.width()
        avail = max(400, w - 60)  # 减去 padding
        min_card_w = 240
        spacing = 12
        new_cols = max(2, min(5, avail // (min_card_w + spacing)))
        if new_cols == getattr(self, '_col_max', 3):
            return
        self._col_max = new_cols
        if hasattr(self, 'experts_grid'):
            self._relayout_grid(self.experts_grid, new_cols)
        if hasattr(self, 'skills_grid'):
            self._relayout_grid(self.skills_grid, new_cols)
        if hasattr(self, 'conn_grid'):
            self._relayout_grid(self.conn_grid, new_cols)


    def _init_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Window |
            Qt.WindowMinimizeButtonHint | Qt.WindowSystemMenuHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(1120, 780)
        self.setMinimumSize(900, 640)
        self._taskbar_btn = None

    def changeEvent(self, event):
        if event.type() == QEvent.ActivationChange and self.isActiveWindow():
            self._clear_taskbar_alert()
        super().changeEvent(event)

    def closeEvent(self, event):
        # 始终保持窗口实例在内存中隐藏而非销毁，保证桌宠双击秒开与零卡顿
        event.ignore()
        if hasattr(self, 'dev_mode_view') and self.dev_mode_view:
            try:
                self.dev_mode_view._save_dev_workspace_session_state()
            except Exception:
                pass
        if bool(self._active_streams) or any(self._session_message_queues.values()):
            self.showMinimized()
            self._show_status("✨ 任务正在后台执行中，已最小化至任务栏")
        else:
            self.hide()

    def _on_close_clicked(self):
        """点击右上角关闭按钮：任务执行中时最小化至任务栏，否则隐藏"""
        if hasattr(self, 'dev_mode_view') and self.dev_mode_view:
            try:
                self.dev_mode_view._save_dev_workspace_session_state()
            except Exception:
                pass
        if bool(self._active_streams) or any(self._session_message_queues.values()):
            self.showMinimized()
            self._show_status("✨ 任务正在后台执行中，已最小化至任务栏")
        else:
            self.hide()

    def _ensure_taskbar_btn(self):
        if not HAS_WIN_EXTRAS:
            return None
        if not hasattr(self, '_taskbar_btn') or self._taskbar_btn is None:
            try:
                self._taskbar_btn = QWinTaskbarButton(self)
            except Exception:
                self._taskbar_btn = None
        if self._taskbar_btn and self.windowHandle() and not self._taskbar_btn.window():
            try:
                self._taskbar_btn.setWindow(self.windowHandle())
            except Exception:
                pass
        return self._taskbar_btn

    def _set_taskbar_running(self):
        btn = self._ensure_taskbar_btn()
        if btn:
            try:
                prog = btn.progress()
                prog.setRange(0, 0)
                prog.resume()
                prog.setVisible(True)
            except Exception:
                pass

    def _set_taskbar_completed(self):
        btn = self._ensure_taskbar_btn()
        if btn:
            try:
                prog = btn.progress()
                prog.setRange(0, 100)
                prog.setValue(100)
                prog.pause()  # 任务栏底色进度条置为橙黄色高亮
                prog.setVisible(True)
            except Exception:
                pass
        try:
            flash_window_taskbar(int(self.winId()))
            QApplication.alert(self, 0)
        except Exception:
            pass

    def _clear_taskbar_alert(self):
        try:
            stop_flash_window(int(self.winId()))
        except Exception:
            pass
        btn = getattr(self, '_taskbar_btn', None)
        if btn:
            try:
                btn.progress().setVisible(False)
            except Exception:
                pass

    def _setup_resize_handles(self):
        self._resize_margin = 8
        self._resize_handles = []
        self._resize_edge = None
        self._resize_start_geo = None
        self._resize_start_pos = None
        edges = ["left", "right", "top", "bottom",
                 "top-left", "top-right", "bottom-left", "bottom-right"]
        # handle 挂在 main_frame 上（窗口内容区），避免透明圆角区域不响应鼠标
        parent = getattr(self, 'main_frame', self)
        for edge in edges:
            h = _ResizeHandle(parent, edge)
            h.hide()
            self._resize_handles.append(h)

    def _layout_resize_handles(self):
        if not hasattr(self, '_resize_handles'):
            return
        if getattr(self, '_is_maximized', False):
            for handle in self._resize_handles:
                handle.hide()
            return
        m = self._resize_margin
        parent = getattr(self, 'main_frame', self)
        w = parent.width()
        h = parent.height()
        positions = {
            "left":         (0, m, m, h - 2 * m),
            "right":        (w - m, m, m, h - 2 * m),
            "top":          (m, 0, w - 2 * m, m),
            "bottom":       (m, h - m, w - 2 * m, m),
            "top-left":     (0, 0, m, m),
            "top-right":    (w - m, 0, m, m),
            "bottom-left":  (0, h - m, m, m),
            "bottom-right": (w - m, h - m, m, m),
        }
        for handle in self._resize_handles:
            edge = handle._edge
            x, y, hw, hh = positions[edge]
            handle.setGeometry(x, y, hw, hh)
            handle.show()
            handle.raise_()

    def _begin_resize(self, edge: str, global_pos: QPoint):
        self._resize_edge = edge
        self._resize_start_geo = self.geometry()
        self._resize_start_pos = global_pos

    def _do_resize(self, global_pos: QPoint):
        if not self._resize_edge or self._resize_start_geo is None:
            return
        dx = global_pos.x() - self._resize_start_pos.x()
        dy = global_pos.y() - self._resize_start_pos.y()
        g = QRect(self._resize_start_geo)
        edge = self._resize_edge
        if "left" in edge:
            g.setLeft(g.left() + dx)
        if "right" in edge:
            g.setRight(g.right() + dx)
        if "top" in edge:
            g.setTop(g.top() + dy)
        if "bottom" in edge:
            g.setBottom(g.bottom() + dy)
        # 最小尺寸约束
        min_w = self.minimumWidth()
        min_h = self.minimumHeight()
        if g.width() < min_w:
            if "left" in edge:
                g.setLeft(g.right() - min_w)
            else:
                g.setRight(g.left() + min_w)
        if g.height() < min_h:
            if "top" in edge:
                g.setTop(g.bottom() - min_h)
            else:
                g.setBottom(g.top() + min_h)
        self.setGeometry(g)

    def _end_resize(self):
        self._resize_edge = None
        self._resize_start_geo = None
        self._resize_start_pos = None

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
        self._show_status(f"⏰ 自动化流水线触发执行：{title}")
        self.execute_automation_task(rid, title, content)
        QTimer.singleShot(200, self._refresh_task_list)
        QTimer.singleShot(200, self._refresh_auto_log)

    def execute_automation_task(self, rid: int, title: str, content: str):
        """真正的自动化任务执行引擎：在聊天窗口中建立独立任务会话，注入专家人设与技能，流式生成完整执行结果并落盘持久化"""
        clean_name = title.replace("⏰", "").strip()
        if not content.strip():
            content = clean_name

        # 0. 幂等去重保护：防止多处信号监听或外部多次调用导致瞬间并发执行两次
        now_ts = time.time()
        if not hasattr(self, '_recent_executed_tasks'):
            self._recent_executed_tasks = {}
        # 清除超过 10 秒的旧记录
        self._recent_executed_tasks = {k: v for k, v in self._recent_executed_tasks.items() if now_ts - v < 10.0}
        dedup_key = (rid, clean_name)
        if dedup_key in self._recent_executed_tasks and (now_ts - self._recent_executed_tasks[dedup_key] < 5.0):
            print(f"[ChatWindow] 自动化任务 {clean_name} (rid={rid}) 刚在近期触发过，跳过重复执行")
            return
        self._recent_executed_tasks[dedup_key] = now_ts

        # 1. 查找任务绑定的专家、技能、模型等元数据
        expert_name = ""
        skill_name = ""
        model_name = ""
        perm_mode = "full"
        try:
            from core.pet_scheduler import PetScheduler
            r = PetScheduler.get_instance().get_reminder_by_id(rid)
            if r:
                expert_name = r.get("expert", "")
                skill_name = r.get("skill", "")
                model_name = r.get("model", "")
                perm_mode = r.get("permission", "full")
        except Exception:
            pass

        # 2. 组装交给 AI 深度推理的 Prompt（注入专家人设与技能指令）
        final_prompt = content.strip()
        expert_sys_prompt = ""
        if expert_name:
            try:
                from core.ai_engine import EXPERTS_MAP
                for exp in EXPERTS_MAP.values():
                    if exp.get("name") == expert_name:
                        expert_sys_prompt = exp.get("system_prompt", "")
                        break
            except Exception:
                pass

        if expert_sys_prompt:
            final_prompt = f"【行业专家身份：{expert_name}】\n【专业职责与思维规范】：\n{expert_sys_prompt}\n\n【待执行自动化任务指令】：\n{final_prompt}"

        if skill_name:
            final_prompt = f"【指定执行技能：{skill_name}】请遵循该技能工作流要求执行：\n{final_prompt}"

        # 3. 联动桌宠展示执行状态
        if hasattr(self, 'pet_window') and self.pet_window:
            try:
                self.pet_window.web.page().runJavaScript(
                    f"if (window.showCareMessage) window.showCareMessage('🚀 正在执行任务', '正在为你执行自动化任务：【{clean_name}】<br>AI 正在深度思考并生成完整报告...'); "
                    f"if (window.triggerAction) window.triggerAction('nod', 3500);"
                )
            except Exception:
                pass

        # 4. 在 SQLite MemoryManager 中创建真正的独立任务会话
        session_title = f"🤖 {clean_name}"
        sid = None
        if self.memory:
            ws_name = self.current_workspace_name or ""
            sid = self.memory.create_session(session_title, workspace_name=ws_name)
            self._current_session_id = sid

        # 5. 切到主聊天视图并展示任务信息
        self._switch_nav(0)
        self._enter_active_chat_mode()
        self._clear_chat_blocks()
        self.chat_title_lbl.setText(session_title)
        self.setWindowTitle(f"{session_title} - NovaDesk")

        # 渲染用户触发指令卡片
        user_display_msg = f"📋 【自动化任务触发执行】\n任务名称：{clean_name}\n执行指令：{content}"
        if expert_name:
            user_display_msg += f"\n绑定专家：{expert_name}"
        if skill_name:
            user_display_msg += f"\n指定技能：{skill_name}"
        
        if self.memory and sid:
            self.memory.add_message(sid, "user", user_display_msg)
        self._add_message_block("user", user_display_msg)

        self._refresh_history_list()
        self._refresh_sidebar_workspaces()
        self._show_status(f"🚀 正在自动执行任务：{clean_name}...")

        # 6. 启动真实的流式推理与工具链调用
        if sid:
            self._start_stream_for_session(sid, final_prompt)
        else:
            self._do_send(final_prompt)

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

        # 顶层双模式堆栈容器 (100% 独立隔离：Work 模式原样保持，Dev 代码开发模式独立封装)
        from ui.dev_mode_view import DevModeView
        self.dev_mode_view = DevModeView(self.config, self.ai_engine, self.memory, self.save_config_fn, self)

        self.mode_stack = QStackedWidget()
        self.mode_stack.addWidget(self.splitter)       # index 0: 原有 Work 办公模式
        self.mode_stack.addWidget(self.dev_mode_view)  # index 1: 全新 Dev 代码开发模式
        fl.addWidget(self.mode_stack, 1)

        self.root_layout.addWidget(self.main_frame)
        self._apply_theme()
        # 无边框窗口四角/四边缩放句柄（必须在 main_frame 创建后）
        self._setup_resize_handles()
        self._layout_resize_handles()

    # ══════════════════════════════════════════════════════════
    #  顶部标题栏 (含双模式切换胶囊: 💼 办公模式 | 💻 代码开发)
    # ══════════════════════════════════════════════════════════
    def _create_topbar(self) -> QWidget:
        bar = DraggableTopBar(self)
        bar.setFixedHeight(46)
        bar.setObjectName("TopBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 10, 0)
        lay.setSpacing(8)
        _ic = "#a1a1aa" if self._is_dark else "#64748b"

        dot_r = QLabel("●"); dot_r.setStyleSheet("color:#ef4444;font-size:10px;")
        dot_y = QLabel("●"); dot_y.setStyleSheet("color:#f59e0b;font-size:10px;")
        dot_g = QLabel("●"); dot_g.setStyleSheet("color:#10b981;font-size:10px;")
        for d in [dot_r, dot_y, dot_g]:
            lay.addWidget(d)

        lay.addSpacing(10)
        self.title_lbl = QLabel("NovaDesk v4.0")
        self.title_lbl.setFont(QFont("Microsoft YaHei UI", 9, QFont.Bold))
        self.title_lbl.setFixedWidth(96)
        lay.addWidget(self.title_lbl)

        lay.addSpacing(10)

        # 模式切换胶囊 (双模式胶囊：💼 办公 | 💻 开发，常驻顶部标题栏，一键切换)
        self.mode_capsule = QFrame()
        self.mode_capsule.setFixedHeight(28)
        self.mode_capsule.setFixedWidth(136)
        mc_lay = QHBoxLayout(self.mode_capsule)
        mc_lay.setContentsMargins(2, 2, 2, 2)
        mc_lay.setSpacing(2)

        self.btn_mode_work = QPushButton("💼 办公")
        self.btn_mode_work.setCursor(Qt.PointingHandCursor)
        self.btn_mode_work.setFixedWidth(64)
        self.btn_mode_work.setToolTip("切换到办公助手工作台")
        self.btn_mode_work.clicked.connect(lambda: self._switch_app_mode(0))
        mc_lay.addWidget(self.btn_mode_work)

        self.btn_mode_dev = QPushButton("💻 开发")
        self.btn_mode_dev.setCursor(Qt.PointingHandCursor)
        self.btn_mode_dev.setFixedWidth(64)
        self.btn_mode_dev.setToolTip("切换到代码开发模式 (IDE)")
        self.btn_mode_dev.clicked.connect(lambda: self._switch_app_mode(1))
        mc_lay.addWidget(self.btn_mode_dev)

        self._update_mode_capsule_style()
        lay.addWidget(self.mode_capsule)

        # 展开侧边栏按钮 (仅在办公模式且侧边栏收起时呈现，置于胶囊右侧，绝不影响切换胶囊基准位置)
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

        lay.addStretch()

        self.theme_btn = QPushButton()
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.setIcon(load_ui_icon("moon" if self._is_dark else "sun", _ic, 16))
        self.theme_btn.setIconSize(QSize(16, 16))
        self.theme_btn.setToolTip("切换主题")
        self.theme_btn.clicked.connect(self._toggle_theme)
        lay.addWidget(self.theme_btn)

        self.min_btn = QPushButton()
        self.min_btn.setFixedSize(32, 32)
        self.min_btn.setIcon(load_ui_icon("minus", _ic, 16))
        self.min_btn.setIconSize(QSize(16, 16))
        self.min_btn.clicked.connect(self.showMinimized)
        lay.addWidget(self.min_btn)

        self.max_btn = QPushButton()
        self.max_btn.setFixedSize(32, 32)
        self.max_btn.setIcon(load_ui_icon("square", _ic, 16))
        self.max_btn.setIconSize(QSize(16, 16))
        self.max_btn.clicked.connect(self._toggle_maximize)
        lay.addWidget(self.max_btn)

        self.close_btn = QPushButton()
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setIcon(load_ui_icon("close", _ic, 16))
        self.close_btn.setIconSize(QSize(16, 16))
        self.close_btn.clicked.connect(self._on_close_clicked)
        lay.addWidget(self.close_btn)
        return bar

    def _update_mode_capsule_style(self):
        if not hasattr(self, 'mode_capsule') or not hasattr(self, 'btn_mode_work') or not hasattr(self, 'btn_mode_dev'):
            return
        d = self._is_dark
        capsule_bg = "#27272a" if d else "#e2e8f0"
        capsule_border = "#3f3f46" if d else "#cbd5e1"
        self.mode_capsule.setStyleSheet(f"""
            QFrame {{
                background-color: {capsule_bg};
                border: 1px solid {capsule_border};
                border-radius: 7px;
            }}
        """)
        cur_idx = self.mode_stack.currentIndex() if hasattr(self, 'mode_stack') else 0
        if cur_idx == 0:
            self.btn_mode_work.setStyleSheet("""
                QPushButton {
                    background-color: #0e639c; color: #ffffff; border: none;
                    border-radius: 5px; padding: 2px 4px; font-size: 11px; font-weight: bold;
                    font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
                }
            """)
            self.btn_mode_dev.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; color: {'#a1a1aa' if d else '#64748b'}; border: none;
                    border-radius: 5px; padding: 2px 4px; font-size: 11px;
                    font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
                }}
                QPushButton:hover {{ color: {'#ffffff' if d else '#0f172a'}; background-color: {'#333338' if d else '#f1f5f9'}; }}
            """)
        else:
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

    def _switch_app_mode(self, mode_idx: int):
        """无缝在工作模式 (0) 与代码开发模式 (1) 之间切换 (100% 独立隔离)"""
        if not hasattr(self, 'mode_stack'):
            return

        self.mode_stack.setCurrentIndex(mode_idx)
        self._update_mode_capsule_style()

        # 无论切到哪个模式，都同步 dev_mode_view 的主题（避免切回开发模式时看到旧主题）
        if hasattr(self, 'dev_mode_view') and self.dev_mode_view:
            if hasattr(self.dev_mode_view, 'apply_theme'):
                try:
                    self.dev_mode_view.apply_theme(self._is_dark)
                except Exception:
                    pass
            # 强制重画（解决某些 PyQt 版本 setStyleSheet 设了但不触发重画）
            try:
                self.dev_mode_view.update()
                self.dev_mode_view.repaint()
            except Exception:
                pass

        if mode_idx == 0:
            if hasattr(self, 'expand_sb_btn') and hasattr(self, 'sidebar'):
                self.expand_sb_btn.setVisible(not self.sidebar.isVisible())
            self._show_status("💼 已切换至「办公模式」")
        else:
            if hasattr(self, 'expand_sb_btn'):
                self.expand_sb_btn.hide()
            # 同步最新工作空间路径、模型列表与主题给 Dev 模式
            if hasattr(self, 'dev_mode_view') and self.dev_mode_view:
                self.dev_mode_view.refresh_models_list()
                ws_path = getattr(self, 'current_workspace_path', '') or getattr(self, 'workspace_root', '')
                if ws_path:
                    self.dev_mode_view.set_workspace_root(ws_path)
                if hasattr(self.dev_mode_view, 'update_pet_btn_state'):
                    self.dev_mode_view.update_pet_btn_state()
                if hasattr(self.dev_mode_view, 'update_sound_btn_state'):
                    self.dev_mode_view.update_sound_btn_state()
            self._show_status("💻 已切换至「代码开发模式 (IDE)」")

    # ══════════════════════════════════════════════════════════
    #  侧边栏 (任务 + 空间联动)
    # ══════════════════════════════════════════════════════════
    def _create_sidebar(self) -> QWidget:
        sb = QWidget()
        sb.setObjectName("SideBar")
        sb.setFixedWidth(260)
        sb.setAttribute(Qt.WA_StyledBackground, True)  # 强制样式背景生效，避免透出 main_frame 阴影
        lay = QVBoxLayout(sb)
        lay.setContentsMargins(10, 12, 10, 10)
        lay.setSpacing(6)
        # 图标颜色（深浅主题跟随）
        _ic = "#a1a1aa" if self._is_dark else "#64748b"

        # 头部工作台信息与快捷操作 (复刻截图：WorkBuddy + [收起侧边栏][搜索][筛选])
        top_info = QHBoxLayout()
        top_info.setSpacing(4)
        
        self.sidebar_title = QLabel("工作台")
        self.sidebar_title.setStyleSheet(f"color: {'#e4e4e7' if self._is_dark else '#1e293b'}; font-size: 12px; font-weight: bold; font-family: 'Microsoft YaHei UI';")
        top_info.addWidget(self.sidebar_title)
        top_info.addStretch()

        top_icon_btn_style = f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background: {'#27272a' if self._is_dark else '#e2e8f0'};
            }}
        """

        # 1. 收起侧边栏
        self.btn_collapse_sb = QPushButton()
        self.btn_collapse_sb.setFixedSize(26, 26)
        self.btn_collapse_sb.setToolTip("收起侧边栏")
        self.btn_collapse_sb.setStyleSheet(top_icon_btn_style)
        self.btn_collapse_sb.setIcon(load_ui_icon("panel-left", _ic, 15))
        self.btn_collapse_sb.setIconSize(QSize(15, 15))
        self.btn_collapse_sb.clicked.connect(self._toggle_sidebar_collapse)
        top_info.addWidget(self.btn_collapse_sb)

        # 2. 搜索
        self.btn_search_tasks = QPushButton()
        self.btn_search_tasks.setFixedSize(26, 26)
        self.btn_search_tasks.setToolTip("搜索")
        self.btn_search_tasks.setStyleSheet(top_icon_btn_style)
        self.btn_search_tasks.setIcon(load_ui_icon("search", _ic, 15))
        self.btn_search_tasks.setIconSize(QSize(15, 15))
        self.btn_search_tasks.clicked.connect(self._open_global_task_search_popup)
        top_info.addWidget(self.btn_search_tasks)

        # 3. 筛选
        self.btn_filter_tasks = QPushButton()
        self.btn_filter_tasks.setFixedSize(26, 26)
        self.btn_filter_tasks.setToolTip("筛选")
        self.btn_filter_tasks.setStyleSheet(top_icon_btn_style)
        self.btn_filter_tasks.setIcon(load_ui_icon("filter", _ic, 15))
        self.btn_filter_tasks.setIconSize(QSize(15, 15))
        self.btn_filter_tasks.clicked.connect(self._open_task_filter_popup)
        top_info.addWidget(self.btn_filter_tasks)

        lay.addLayout(top_info)
        lay.addSpacing(4)

        # + 新建任务
        self.new_task_btn = QPushButton("＋  新建任务")
        self.new_task_btn.setFixedHeight(34)
        self.new_task_btn.clicked.connect(self._create_new_session_action)
        lay.addWidget(self.new_task_btn)
        lay.addSpacing(2)

        # 主导航（单色 SVG 图标 + 文字，统一视觉语言）
        self.nav_btns = []
        nav_items = [
            ("chat", "助理", 0),
            ("grid", "专家·技能·连接器", 1),
            ("clock", "自动化", 2),
            ("settings", "设置与模型", 3),
        ]
        for icon_name, label, idx in nav_items:
            btn = QPushButton(f"  {label}")
            btn.setFixedHeight(32)
            btn.setCheckable(True)
            btn.setIcon(load_ui_icon(icon_name, _ic, 14))
            btn.setIconSize(QSize(14, 14))
            btn.clicked.connect(lambda checked, i=idx: self._switch_nav(i))
            lay.addWidget(btn)
            self.nav_btns.append(btn)
        self.nav_btns[0].setChecked(True)

        lay.addSpacing(6)

        # ── 统一平滑滚动视口 (单滚动条，整体自然流式排版，彻底告别死板切块与嵌套视口) ──
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.sidebar_scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
        """)
        self.sidebar_scroll.viewport().setStyleSheet("background: transparent;")
        self.sidebar_scroll.verticalScrollBar().setSingleStep(15)

        self.sidebar_scroll_content = QWidget()
        self.sidebar_scroll_content.setStyleSheet("background: transparent;")
        sc_lay = QVBoxLayout(self.sidebar_scroll_content)
        sc_lay.setContentsMargins(0, 0, 8, 24)
        sc_lay.setSpacing(6)

        # 1. 任务模块
        self.task_box = QWidget()
        self.task_box.setStyleSheet("background: transparent;")
        tb_lay = QVBoxLayout(self.task_box)
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.setSpacing(2)

        task_header = QHBoxLayout()
        task_header.setContentsMargins(0, 0, 4, 0)
        self.task_head = QLabel("任务 (0) ∨")
        self.task_head.setStyleSheet(f"color:{'#a1a1aa' if self._is_dark else '#64748b'};font-size:11px;font-weight:bold;")
        self.task_head.setCursor(Qt.PointingHandCursor)
        self.task_head.setToolTip("点击展开/折叠任务列表")
        self.task_head.mousePressEvent = lambda e: self._toggle_session_list()
        task_header.addWidget(self.task_head)
        task_header.addStretch(1)

        # 顶栏右侧固定切换按钮 (位置永远固定不动，点击时绝对零乱跳！)
        self.task_header_toggle_btn = QPushButton()
        self.task_header_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.task_header_toggle_btn.setFixedHeight(20)
        self.task_header_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {'#71717a' if self._is_dark else '#94a3b8'};
                border: none;
                border-radius: 4px;
                font-size: 10.5px;
                font-family: 'PingFang SC', 'Microsoft YaHei UI', sans-serif;
                padding: 1px 6px;
            }}
            QPushButton:hover {{
                background: {'#27272a' if self._is_dark else '#e2e8f0'};
                color: {'#e4e4e7' if self._is_dark else '#18181b'};
            }}
        """)
        self.task_header_toggle_btn.clicked.connect(self._toggle_show_all_sessions)
        self.task_header_toggle_btn.hide()
        task_header.addWidget(self.task_header_toggle_btn)

        # 批量管理任务按钮
        self.task_batch_btn = QPushButton("批量")
        self.task_batch_btn.setCursor(Qt.PointingHandCursor)
        self.task_batch_btn.setFixedHeight(20)
        self.task_batch_btn.setToolTip("批量管理与删除历史任务")
        self.task_batch_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {'#71717a' if self._is_dark else '#94a3b8'};
                border: none;
                border-radius: 4px;
                font-size: 10.5px;
                font-family: 'PingFang SC', 'Microsoft YaHei UI', sans-serif;
                padding: 1px 6px;
            }}
            QPushButton:hover {{
                background: {'#27272a' if self._is_dark else '#e2e8f0'};
                color: {'#e4e4e7' if self._is_dark else '#18181b'};
            }}
        """)
        self.task_batch_btn.clicked.connect(self._open_batch_dialog)
        task_header.addWidget(self.task_batch_btn)
        tb_lay.addLayout(task_header)

        self.task_items_container = QWidget()
        self.task_items_container.setStyleSheet("background: transparent;")
        self.task_items_lay = QVBoxLayout(self.task_items_container)
        self.task_items_lay.setContentsMargins(0, 2, 0, 2)
        self.task_items_lay.setSpacing(2)
        tb_lay.addWidget(self.task_items_container)

        sc_lay.addWidget(self.task_box)

        # 任务区与空间区之间的间距
        sc_lay.addSpacing(10)

        # 2. 空间模块
        self.ws_box = QWidget()
        self.ws_box.setStyleSheet("background: transparent;")
        wb_lay = QVBoxLayout(self.ws_box)
        wb_lay.setContentsMargins(0, 0, 0, 0)
        wb_lay.setSpacing(2)

        ws_header = QHBoxLayout()
        ws_header.setContentsMargins(0, 0, 4, 0)
        self.ws_head = QLabel(f"空间 ({len(self.workspaces)}) ∨")
        self.ws_head.setStyleSheet(f"color:{'#a1a1aa' if self._is_dark else '#64748b'};font-size:11px;font-weight:bold;")
        self.ws_head.setCursor(Qt.PointingHandCursor)
        self.ws_head.setToolTip("点击展开/折叠工作空间列表")
        self.ws_head.mousePressEvent = lambda e: self._toggle_workspace_area()
        ws_header.addWidget(self.ws_head)
        ws_header.addStretch(1)

        # 批量管理空间按钮
        self.ws_batch_btn = QPushButton("批量")
        self.ws_batch_btn.setCursor(Qt.PointingHandCursor)
        self.ws_batch_btn.setFixedHeight(20)
        self.ws_batch_btn.setToolTip("批量管理与移除工作空间")
        self.ws_batch_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {'#71717a' if self._is_dark else '#94a3b8'};
                border: none;
                border-radius: 4px;
                font-size: 10.5px;
                font-family: 'PingFang SC', 'Microsoft YaHei UI', sans-serif;
                padding: 1px 6px;
            }}
            QPushButton:hover {{
                background: {'#27272a' if self._is_dark else '#e2e8f0'};
                color: {'#e4e4e7' if self._is_dark else '#18181b'};
            }}
        """)
        self.ws_batch_btn.clicked.connect(self._open_batch_workspace_dialog)
        ws_header.addWidget(self.ws_batch_btn)
        wb_lay.addLayout(ws_header)

        self.ws_items_container = QWidget()
        self.ws_items_container.setStyleSheet("background: transparent;")
        self.ws_items_lay = QVBoxLayout(self.ws_items_container)
        self.ws_items_lay.setContentsMargins(0, 2, 0, 2)
        self.ws_items_lay.setSpacing(2)
        wb_lay.addWidget(self.ws_items_container)

        sc_lay.addWidget(self.ws_box)
        sc_lay.addStretch(1)

        self.sidebar_scroll.setWidget(self.sidebar_scroll_content)
        lay.addWidget(self.sidebar_scroll, 1)

        # 底部状态、桌宠显隐开关与全局声音喇叭
        bot = QHBoxLayout()
        bot.setContentsMargins(4, 2, 4, 0)
        self.status_lbl = QLabel("智能体 就绪")
        self.status_lbl.setStyleSheet(f"color:{'#a1a1aa' if self._is_dark else '#64748b'};font-size:11px;font-family:'Microsoft YaHei UI';")
        bot.addWidget(self.status_lbl)
        bot.addStretch()

        # 桌宠显示/隐藏开关 (位置：声音开关左侧，持久化记录状态，下次启动自动保持)
        self.pet_toggle_btn = QPushButton()
        self.pet_toggle_btn.setFixedSize(22, 22)
        self.pet_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.pet_toggle_btn.setIconSize(QSize(14, 14))
        self.pet_toggle_btn.clicked.connect(self._toggle_pet_visible)
        bot.addWidget(self.pet_toggle_btn)
        bot.addSpacing(2)

        # 声音控制开关
        self.sound_btn = QPushButton()
        self.sound_btn.setFixedSize(22, 22)
        self.sound_btn.setCursor(Qt.PointingHandCursor)
        self.sound_btn.setIconSize(QSize(13, 13))
        self.sound_btn.clicked.connect(self._toggle_sound_muted)
        bot.addWidget(self.sound_btn)

        self._update_pet_btn_state()
        self._update_sound_btn_state()
        lay.addLayout(bot)
        return sb

    def _update_pet_btn_state(self):
        """更新桌宠开关按钮的图标、Tooltip 与深浅色主题样式"""
        if hasattr(self, 'dev_mode_view') and self.dev_mode_view and hasattr(self.dev_mode_view, 'update_pet_btn_state'):
            self.dev_mode_view.update_pet_btn_state()
        if not hasattr(self, 'pet_toggle_btn'):
            return
        d = getattr(self, '_is_dark', True)
        is_pet_on = self.config.get("pet", {}).get("enabled", self.config.get("pet_enabled", True))
        icon_color = ("#10b981" if is_pet_on else "#a1a1aa") if d else ("#059669" if is_pet_on else "#94a3b8")
        icon_name = "pet" if is_pet_on else "pet-off"
        self.pet_toggle_btn.setIcon(load_ui_icon(icon_name, icon_color, 14))
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

    def _update_sound_btn_state(self):
        """更新声音开关按钮的图标、Tooltip 与深浅色主题样式"""
        if hasattr(self, 'dev_mode_view') and self.dev_mode_view and hasattr(self.dev_mode_view, 'update_sound_btn_state'):
            self.dev_mode_view.update_sound_btn_state()
        if not hasattr(self, 'sound_btn'):
            return
        d = getattr(self, '_is_dark', True)
        is_sound_on = self.config.get("sound_enabled", True)
        icon_color = "#a1a1aa" if d else "#64748b"
        icon_name = "volume" if is_sound_on else "volume-off"
        self.sound_btn.setText("")
        self.sound_btn.setIcon(load_ui_icon(icon_name, icon_color, 13))
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

    def _toggle_pet_visible(self):
        """切换桌宠开启/关闭，并持久化记录状态（下次启动自动保持）"""
        curr = self.config.get("pet", {}).get("enabled", self.config.get("pet_enabled", True))
        new_val = not curr
        self.config.setdefault("pet", {})["enabled"] = new_val
        self.config["pet_enabled"] = new_val
        if self.save_config_fn:
            try:
                self.save_config_fn(self.config)
            except Exception as e:
                print(f"[ChatWindow] Error saving pet visibility: {e}")

        if self.pet_window:
            if hasattr(self.pet_window, 'set_pet_visible'):
                self.pet_window.set_pet_visible(new_val, persist=False)
            else:
                if new_val:
                    self.pet_window.show()
                    self.pet_window.raise_()
                    self.pet_window.activateWindow()
                else:
                    self.pet_window.hide()

        self._update_pet_btn_state()
        self._show_status("桌宠已开启" if new_val else "桌宠已关闭")

    def _toggle_sound_muted(self):
        curr = self.config.get("sound_enabled", True)
        new_val = not curr
        self.config["sound_enabled"] = new_val
        self.config.setdefault("behavior", {})["sound_enabled"] = new_val
        if self.pet_window and hasattr(self.pet_window, "set_sound_enabled"):
            self.pet_window.set_sound_enabled(new_val)
        if self.save_config_fn:
            self.save_config_fn(self.config)
        self._update_sound_btn_state()
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
        vh_lay.setContentsMargins(20, 16, 20, 20)

        vh_lay.addStretch(1)

        # 居中核心容器 (限制最大宽度，非常高级)
        center_box = QWidget()
        center_box.setFixedWidth(780)
        cb_lay = QVBoxLayout(center_box)
        cb_lay.setContentsMargins(0, 0, 0, 0)
        cb_lay.setSpacing(12)
        cb_lay.setAlignment(Qt.AlignCenter)

        # 1. 顶部大标题
        header_row = QHBoxLayout()
        header_row.setAlignment(Qt.AlignCenter)
        self.h_title = QLabel("NovaDesk, 我帮你")
        self.h_title.setFont(QFont("Microsoft YaHei UI", 24, QFont.Bold))
        header_row.addWidget(self.h_title)
        cb_lay.addLayout(header_row)

        # 2. 顶层主分类切换药丸栏 (日常办公 / 代码开发 / 设计创意)
        self._primary_cat_btns = {}
        p_row = QHBoxLayout()
        p_row.setAlignment(Qt.AlignCenter)
        p_row.setSpacing(8)

        p_container = QFrame()
        p_container.setStyleSheet(f"""
            QFrame {{
                background: {'rgba(255,255,255,0.03)' if self._is_dark else 'rgba(0,0,0,0.03)'};
                border: 1px solid {'#27272a' if self._is_dark else '#e2e8f0'};
                border-radius: 20px;
                padding: 2px 4px;
            }}
        """)
        p_box = QHBoxLayout(p_container)
        p_box.setContentsMargins(4, 2, 4, 2)
        p_box.setSpacing(6)

        for cat_name, cat_data in HERO_SCENARIOS_MAP.items():
            pb = QPushButton(f"{cat_data['icon']}  {cat_name}")
            pb.setFixedHeight(32)
            pb.setCursor(Qt.PointingHandCursor)
            pb.clicked.connect(lambda ch, cn=cat_name: self._switch_primary_category(cn))
            p_box.addWidget(pb)
            self._primary_cat_btns[cat_name] = pb

        p_row.addWidget(p_container)
        cb_lay.addLayout(p_row)

        # 3. 二级场景胶囊栏 (动态根据主分类渲染，如日常开发、网站开发、Agent应用、Skill开发等)
        self._sub_scenarios_container = QWidget()
        self._sub_scenarios_layout = QHBoxLayout(self._sub_scenarios_container)
        self._sub_scenarios_layout.setAlignment(Qt.AlignCenter)
        self._sub_scenarios_layout.setContentsMargins(0, 0, 0, 0)
        self._sub_scenarios_layout.setSpacing(8)
        cb_lay.addWidget(self._sub_scenarios_container)

        # 4. 悬浮居中大输入卡片 (含场景药丸 Tag、多行输入与底部动作栏)
        self.hero_dock_card = QFrame()
        self.hero_dock_card.setObjectName("HeroDockCard")
        _hd_bg = "#1e1e1e" if self._is_dark else "#ffffff"
        _hd_border = "#2e2e2e" if self._is_dark else "#e2e8f0"
        self.hero_dock_card.setStyleSheet(f"""
            QFrame#HeroDockCard {{
                background-color: {_hd_bg};
                border: 1px solid {_hd_border};
                border-radius: 14px;
            }}
        """)
        _hd_shadow = QGraphicsDropShadowEffect(self.hero_dock_card)
        _hd_shadow.setBlurRadius(18)
        _hd_shadow.setColor(QColor(0, 0, 0, 50 if self._is_dark else 22))
        _hd_shadow.setOffset(0, 4)
        self.hero_dock_card.setGraphicsEffect(_hd_shadow)
        h_dock_l = QVBoxLayout(self.hero_dock_card)
        h_dock_l.setContentsMargins(16, 12, 16, 12)
        h_dock_l.setSpacing(6)

        # 输入框内场景药丸徽章 (复刻截图3翠绿质感徽标，如 [ 🌐 网站开发 ✕ ])
        self.hero_scenario_tag_widget = QWidget()
        tag_lay = QHBoxLayout(self.hero_scenario_tag_widget)
        tag_lay.setContentsMargins(0, 0, 0, 2)
        tag_lay.setSpacing(6)

        self.hero_tag_pill_frame = QFrame()
        self.hero_tag_pill_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {'#064e3b' if self._is_dark else '#ecfdf5'};
                border: 1px solid {'#059669' if self._is_dark else '#a7f3d0'};
                border-radius: 12px;
                padding: 1px 8px;
            }}
        """)
        pill_l = QHBoxLayout(self.hero_tag_pill_frame)
        pill_l.setContentsMargins(6, 2, 6, 2)
        pill_l.setSpacing(6)

        self.hero_tag_name_lbl = QLabel("🌐 网站开发")
        self.hero_tag_name_lbl.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {'#34d399' if self._is_dark else '#065f46'}; background: transparent;")
        pill_l.addWidget(self.hero_tag_name_lbl)

        self.hero_tag_close_btn = QPushButton("✕")
        self.hero_tag_close_btn.setFixedSize(14, 14)
        self.hero_tag_close_btn.setCursor(Qt.PointingHandCursor)
        self.hero_tag_close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {'#34d399' if self._is_dark else '#059669'};
                border: none; font-size: 11px; font-weight: bold; padding: 0;
            }}
            QPushButton:hover {{ color: #ef4444; }}
        """)
        self.hero_tag_close_btn.clicked.connect(self._clear_sub_scenario)
        pill_l.addWidget(self.hero_tag_close_btn)

        tag_lay.addWidget(self.hero_tag_pill_frame)
        tag_lay.addStretch()
        h_dock_l.addWidget(self.hero_scenario_tag_widget)
        self.hero_scenario_tag_widget.hide()

        # 真实附件与图片上传暂存条 (Hero 模式)
        self.hero_attach_bar = AttachmentPreviewBar(is_dark=self._is_dark)
        h_dock_l.addWidget(self.hero_attach_bar)

        self.hero_input_edit = ChatTextEdit()
        self.hero_input_edit.setFixedHeight(64)
        self.hero_input_edit.setPlaceholderText(
            "今天帮你做些什么？ @ 引用对话文件，/ 调用技能与指令"
        )
        self.hero_input_edit.return_pressed.connect(self._send_hero_message)
        self.hero_input_edit.textChanged.connect(self._update_send_button_state)
        self.hero_input_edit.file_attached.connect(lambda p: self._on_file_attached(p, is_hero=True))
        h_dock_l.addWidget(self.hero_input_edit)

        h_dock_bot = QHBoxLayout(); h_dock_bot.setSpacing(8)
        self.hero_plus_btn = QPushButton("＋")
        self.hero_plus_btn.setFixedSize(28, 28)
        self.hero_plus_btn.setToolTip("添加/引用本地项目文件与文档")
        self.hero_plus_btn.clicked.connect(self._on_plus_attach_file_clicked)
        h_dock_bot.addWidget(self.hero_plus_btn)

        self.hero_plan_mode_btn = QPushButton("📋 计划模式")
        self.hero_plan_mode_btn.setFixedHeight(28)
        self.hero_plan_mode_btn.setCheckable(True)
        self.hero_plan_mode_btn.setCursor(Qt.PointingHandCursor)
        self.hero_plan_mode_btn.setToolTip("先出方案再执行：AI 将先为您制定结构化实施计划，待您审阅接收后再落地")
        self.hero_plan_mode_btn.clicked.connect(lambda chk: self._toggle_plan_mode(chk))
        self._update_plan_btn_style(self.hero_plan_mode_btn, False)
        h_dock_bot.addWidget(self.hero_plan_mode_btn)

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

        # 初始化主分类与二级场景展示
        self._switch_primary_category("代码开发")

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

        self.search_chat_btn = QPushButton()
        self.search_chat_btn.setFixedSize(28, 28)
        self.search_chat_btn.setCursor(Qt.PointingHandCursor)
        self.search_chat_btn.setToolTip("搜索对话")
        self.search_chat_btn.setIcon(load_ui_icon("search", "#a1a1aa", 14))
        self.search_chat_btn.setIconSize(QSize(14, 14))
        self.search_chat_btn.clicked.connect(self._open_global_task_search_popup)
        self.chat_header.addWidget(self.search_chat_btn)

        self.export_chat_btn = QPushButton()
        self.export_chat_btn.setFixedHeight(28)
        self.export_chat_btn.setCursor(Qt.PointingHandCursor)
        self.export_chat_btn.setToolTip("导出为 Markdown")
        self.export_chat_btn.setIcon(load_ui_icon("share", "#a1a1aa", 13))
        self.export_chat_btn.setIconSize(QSize(13, 13))
        self.export_chat_btn.clicked.connect(lambda: self._export_session_markdown(self._current_session_id, self.chat_title_lbl.text()))
        self.chat_header.addSpacing(4)
        self.chat_header.addWidget(self.export_chat_btn)

        va_lay.addLayout(self.chat_header)

        # 滚动消息区
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        init_sb_style = (
            "QScrollBar:vertical{width:6px;background:transparent;border:none;margin:0px;}"
            "QScrollBar::handle:vertical{background:#3e4451;border-radius:3px;min-height:24px;border:none;}"
            "QScrollBar::handle:vertical:hover{background:#5c6370;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical,"
            "QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{height:0px;width:0px;background:transparent;border:none;}"
            "QScrollBar:horizontal{height:0px;background:transparent;border:none;}"
            "QScrollBar::handle:horizontal,QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal,"
            "QScrollBar::add-page:horizontal,QScrollBar::sub-page:horizontal{width:0px;height:0px;background:transparent;border:none;}"
        )
        self.scroll_area.setStyleSheet(f"QScrollArea{{background:transparent;border:none;}}\n{init_sb_style}")
        if hasattr(self.scroll_area, 'verticalScrollBar') and self.scroll_area.verticalScrollBar():
            self.scroll_area.verticalScrollBar().setStyleSheet(init_sb_style)

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
        _d_bg = "#1e1e1e" if self._is_dark else "#ffffff"
        _d_border = "#2e2e2e" if self._is_dark else "#e2e8f0"
        self.dock_card.setStyleSheet(f"""
            QFrame#DockCard {{
                background-color: {_d_bg};
                border: 1px solid {_d_border};
                border-radius: 14px;
            }}
        """)
        _d_shadow = QGraphicsDropShadowEffect(self.dock_card)
        _d_shadow.setBlurRadius(18)
        _d_shadow.setColor(QColor(0, 0, 0, 50 if self._is_dark else 22))
        _d_shadow.setOffset(0, 4)
        self.dock_card.setGraphicsEffect(_d_shadow)
        dock_l = QVBoxLayout(self.dock_card)
        dock_l.setContentsMargins(16, 12, 16, 10)
        dock_l.setSpacing(8)

        # 真实附件与图片上传暂存条 (对话模式)
        self.active_attach_bar = AttachmentPreviewBar(is_dark=self._is_dark)
        dock_l.addWidget(self.active_attach_bar)

        self.input_edit = ChatTextEdit()
        self.input_edit.setFixedHeight(54)
        self.input_edit.setPlaceholderText(
            "今天帮你做些什么？ @ 引用对话文件，/ 调用技能与指令"
        )
        self.input_edit.return_pressed.connect(self._send_active_message)
        self.input_edit.textChanged.connect(self._update_send_button_state)
        self.input_edit.file_attached.connect(lambda p: self._on_file_attached(p, is_hero=False))
        dock_l.addWidget(self.input_edit)

        dock_bot = QHBoxLayout(); dock_bot.setSpacing(8)
        self.plus_btn = QPushButton("＋")
        self.plus_btn.setFixedSize(26, 26)
        self.plus_btn.setToolTip("添加/引用本地项目文件与文档")
        self.plus_btn.clicked.connect(self._on_plus_attach_file_clicked)
        dock_bot.addWidget(self.plus_btn)

        self.active_plan_mode_btn = QPushButton("📋 计划模式")
        self.active_plan_mode_btn.setFixedHeight(26)
        self.active_plan_mode_btn.setCheckable(True)
        self.active_plan_mode_btn.setCursor(Qt.PointingHandCursor)
        self.active_plan_mode_btn.setToolTip("先出方案再执行：AI 将先为您制定结构化实施计划，待您审阅接收后再落地")
        self.active_plan_mode_btn.clicked.connect(lambda chk: self._toggle_plan_mode(chk))
        self._update_plan_btn_style(self.active_plan_mode_btn, False)
        dock_bot.addWidget(self.active_plan_mode_btn)

        # 快捷指令 chips（点击即把提示词填入输入框）
        self._quick_chips_active = []
        for _q in ["写代码", "翻译", "总结"]:
            _chip = self._make_quick_chip(_q, self.input_edit)
            self._quick_chips_active.append(_chip)
            dock_bot.addWidget(_chip)
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
        footer_hint.setStyleSheet(f"color: {'#a1a1aa' if self._is_dark else '#64748b'}; font-size: 11px;")
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
        d_local = self._is_dark

        # 顶部返回行
        back_btn = QPushButton("‹ 全部技能")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {'#a1a1aa' if self._is_dark else '#64748b'};
                border: none;
                font-size: 13px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{ color: #6366f1; }}
        """)
        back_btn.clicked.connect(lambda: self.hub_main_stack.setCurrentIndex(0))
        lay.addWidget(back_btn, 0, Qt.AlignLeft)

        # 标题与搜索行
        header_row = QHBoxLayout()
        self.installed_title_lbl = QLabel(f"我安装的  ({len(self._installed_skills)})")
        self.installed_title_lbl.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        # 标题字色强制显眼（深色主题纯白 #ffffff，浅色主题深黑 #0f172a，避免看不清）
        self.installed_title_lbl.setStyleSheet(
            f"color: {'#ffffff' if d_local else '#0f172a'}; "
            f"font-family: 'Microsoft YaHei UI'; background: transparent;"
        )
        header_row.addWidget(self.installed_title_lbl)
        header_row.addStretch()

        self.installed_search = QLineEdit()
        self.installed_search.setPlaceholderText("搜索已安装的技能")
        self.installed_search.setFixedSize(220, 32)
        # 加搜索图标（左侧 action）
        search_action = QAction(load_ui_icon("search", "#a1a1aa" if d_local else "#64748b", 14), "", self.installed_search)
        self.installed_search.addAction(search_action, QLineEdit.LeadingPosition)
        self.installed_search.setStyleSheet(f"""
            QLineEdit {{
                background: {'#27272a' if d_local else '#f8fafc'};
                color: {'#f4f4f5' if d_local else '#0f172a'};
                border: 1px solid {'#3f3f46' if d_local else '#e2e8f0'};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
            QLineEdit:focus {{ border: 1px solid #6366f1; }}
        """)
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
        title_lbl.setStyleSheet(f"font-size: 13.5px; font-weight: bold; color: {'#f4f4f5' if self._is_dark else '#0f172a'}; font-family: 'Microsoft YaHei UI';")
        top.addWidget(title_lbl)
        top.addStretch()

        switch = ToggleSwitch(checked=True)
        switch.toggled.connect(lambda ch, s_=s: self._on_installed_switch_toggled(s_, ch))
        top.addWidget(switch)
        lay.addLayout(top)

        desc_lbl = QLabel(s.get("description", ""))
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"font-size: 11.5px; color: {'#a1a1aa' if self._is_dark else '#64748b'}; font-family: 'Microsoft YaHei UI'; line-height: 1.4;")
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
        head.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
        # 强制对比度字色（深色主题纯白 + 浅色主题深黑）
        head.setStyleSheet(
            f"color: {'#ffffff' if self._is_dark else '#0f172a'}; "
            f"font-family: 'Microsoft YaHei UI'; background: transparent;"
        )
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
            if col >= getattr(self, '_col_max', 3):
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
        head.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
        # 强制对比度（深色主题纯白 + 浅色主题深黑，避免看不清）
        head.setStyleSheet(
            f"color: {'#ffffff' if d else '#0f172a'}; "
            f"font-family: 'Microsoft YaHei UI'; "
            f"background: transparent;"
        )
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
        d_local = self._is_dark
        scroll.setStyleSheet(f"""
            QScrollArea{{background:transparent;border:none;}}
            QScrollArea > QWidget > QWidget{{background:transparent;}}
            QScrollBar:vertical{{width:6px;background:transparent;border:none;margin:0;}}
            QScrollBar::handle:vertical{{background:{'#3e4451' if d_local else '#cbd5e1'};border-radius:3px;min-height:24px;border:none;}}
            QScrollBar::handle:vertical:hover{{background:{'#5c6370' if d_local else '#94a3b8'};}}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical{{height:0;width:0;background:transparent;border:none;}}
        """)
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
            if col >= getattr(self, '_col_max', 3):
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
        _sk_shadow = QGraphicsDropShadowEffect(card)
        _sk_shadow.setBlurRadius(12)
        _sk_shadow.setColor(QColor(0, 0, 0, 45 if d else 20))
        _sk_shadow.setOffset(0, 2)
        card.setGraphicsEffect(_sk_shadow)

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
        dlg = AddCustomConnectorDialog(self, is_dark=self._is_dark)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_result()
            if not data:
                return
            customs = list(self.config.get("custom_connectors", []))
            existing_idx = next((i for i, c in enumerate(customs) if c.get("id") == data["id"]), None)
            if existing_idx is not None:
                customs[existing_idx] = data
            else:
                customs.insert(0, data)
            self.config["custom_connectors"] = customs

            # 默认自动启用并持久化
            connected_set = set(self.config.get("connected_connectors", []))
            connected_set.add(data["id"])
            self.config["connected_connectors"] = list(connected_set)

            if self.save_config_fn:
                self.save_config_fn(self.config)

            self._rebuild_connectors_grid()
            self._show_status(f"✅ 成功添加并启用自定义 MCP 连接器：{data.get('name')}")

    def _delete_custom_connector(self, c: dict):
        cid = c.get("id")
        name = c.get("name", "连接器")
        if show_themed_confirm(self, "删除自定义连接器", f"确认彻底删除自定义 MCP 连接器「{name}」？", self._is_dark):
            customs = [x for x in self.config.get("custom_connectors", []) if x.get("id") != cid]
            self.config["custom_connectors"] = customs
            connected_set = set(self.config.get("connected_connectors", []))
            connected_set.discard(cid)
            self.config["connected_connectors"] = list(connected_set)
            if self.save_config_fn:
                self.save_config_fn(self.config)
            self._rebuild_connectors_grid()
            self._show_status(f"🗑 已删除自定义连接器：{name}")

    # ── 连接器 Tab (复刻截图 1) ──────────────────────────────────
    def _create_connectors_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        d_local = self._is_dark
        scroll.setStyleSheet(f"""
            QScrollArea{{background:transparent;border:none;}}
            QScrollArea > QWidget > QWidget{{background:transparent;}}
            QScrollBar:vertical{{width:6px;background:transparent;border:none;margin:0;}}
            QScrollBar::handle:vertical{{background:{'#3e4451' if d_local else '#cbd5e1'};border-radius:3px;min-height:24px;border:none;}}
            QScrollBar::handle:vertical:hover{{background:{'#5c6370' if d_local else '#94a3b8'};}}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical{{height:0;width:0;background:transparent;border:none;}}
        """)
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
        customs = list(self.config.get("custom_connectors", []))
        builtins = [
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
        return customs + builtins

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
            if col >= getattr(self, '_col_max', 3):
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
        _cn_shadow = QGraphicsDropShadowEffect(card)
        _cn_shadow.setBlurRadius(12)
        _cn_shadow.setColor(QColor(0, 0, 0, 45 if d else 20))
        _cn_shadow.setOffset(0, 2)
        card.setGraphicsEffect(_cn_shadow)

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

        name_box = QHBoxLayout(); name_box.setSpacing(6)
        name_lbl = QLabel(c.get("name", "连接器"))
        name_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {title_fg}; font-family: 'Microsoft YaHei UI';")
        name_box.addWidget(name_lbl)

        if c.get("is_custom"):
            tag_lbl = QLabel("自定义")
            tag_lbl.setStyleSheet("font-size: 10px; color: #a855f7; background: rgba(168,85,247,0.15); border: 1px solid rgba(168,85,247,0.3); border-radius: 4px; padding: 1px 4px; font-weight: bold;")
            name_box.addWidget(tag_lbl)
        name_box.addStretch()
        top.addLayout(name_box, 1)

        # 如果是自定义连接器，提供删除按钮
        if c.get("is_custom"):
            del_btn = QPushButton("✕")
            del_btn.setFixedSize(22, 22)
            del_btn.setToolTip("删除该自定义连接器")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {'#a1a1aa' if d else '#94a3b8'};
                    border: none; border-radius: 4px; font-size: 11px; font-weight: bold;
                }}
                QPushButton:hover {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; }}
            """)
            del_btn.clicked.connect(lambda ch, conn=c: self._delete_custom_connector(conn))
            top.addWidget(del_btn)

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
            self._show_status(f"✅ 已启用连接器配置：{c.get('name')}（标准 MCP 协议已就绪）")
        else:
            btn.setText("＋")
            btn.setStyleSheet(f"background: {'#27272a' if self._is_dark else '#f1f5f9'}; color: {'#f4f4f5' if self._is_dark else '#64748b'}; border: 1px solid {'#3f3f46' if self._is_dark else '#e2e8f0'}; border-radius: 6px; font-size: 13px; font-weight: bold;")
            connected_set.discard(cid)
            self.config["connected_connectors"] = list(connected_set)
            if self.save_config_fn: self.save_config_fn(self.config)
            self._show_status(f"已禁用连接器配置：{c.get('name')}")

    # ══════════════════════════════════════════════════════════
    #  自动化页 (1:1 像素复刻截图 2 与截图 3)
    # ══════════════════════════════════════════════════════════
    def _create_automation_page(self) -> QWidget:
        d = self._is_dark
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
        empty_tip.setStyleSheet(f"color: {'#a1a1aa' if self._is_dark else '#64748b'}; font-size: 13.5px; font-weight: 500; font-family: 'Microsoft YaHei UI';")
        empty_tip.setAlignment(Qt.AlignCenter)
        e_lay.addWidget(empty_tip)
        self.auto_empty_tip = empty_tip

        self.auto_empty_subtip = QLabel("当前暂无待触发任务 · 历史执行记录请查看上方「📋 运行记录」")
        self.auto_empty_subtip.setStyleSheet(f"color: {'#71717a' if self._is_dark else '#94a3b8'}; font-size: 11.5px; font-family: 'Microsoft YaHei UI';")
        self.auto_empty_subtip.setAlignment(Qt.AlignCenter)
        e_lay.addWidget(self.auto_empty_subtip)

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
        self.tpl_head.setStyleSheet(f"color: {'#f4f4f5' if d else '#0f172a'}; font-size: 13px; font-weight: bold; font-family: 'Microsoft YaHei UI';")
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
        self.log_head = QLabel("📋 运行记录")
        self.log_head.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
        self.log_head.setStyleSheet(f"color: {'#f4f4f5' if d else '#0f172a'}; font-size: 13px; font-weight: bold; font-family: 'Microsoft YaHei UI';")
        log_head_row.addWidget(self.log_head)
        log_head_row.addStretch()

        self.clear_log_btn = QPushButton("🗑 清空记录")
        self.clear_log_btn.setFixedHeight(30)
        self.clear_log_btn.setCursor(Qt.PointingHandCursor)
        self.clear_log_btn.setStyleSheet(f"""
            QPushButton {{
                background: {'#27272a' if d else '#f1f5f9'};
                color: {'#a1a1aa' if d else '#64748b'};
                border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{
                background: {'#3f3f46' if d else '#e2e8f0'};
                color: {'#ef4444' if d else '#dc2626'};
                border-color: {'#ef4444' if d else '#dc2626'};
            }}
        """)
        self.clear_log_btn.clicked.connect(self._clear_auto_log)
        log_head_row.addWidget(self.clear_log_btn)
        log_lay.addLayout(log_head_row)

        self.log_list = QListWidget()
        self.log_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent; border: none; color: {'#f4f4f5' if d else '#0f172a'};
                font-family: 'Microsoft YaHei UI'; font-size: 12px;
            }}
            QListWidget::item {{
                padding: 7px 10px; border-bottom: 1px solid {'#27272a' if d else '#f1f5f9'};
            }}
            QListWidget::item:hover {{
                background: {'#27272a' if d else '#f8fafc'};
            }}
            QListWidget::item:selected {{
                background: {'#312e81' if d else '#e0e7ff'}; color: {'#ffffff' if d else '#1e1b4b'};
            }}
            QListWidget QScrollBar:vertical {{
                background: transparent; width: 6px; margin: 2px 0px; border: none;
            }}
            QListWidget QScrollBar::handle:vertical {{
                background: {'#3f3f46' if d else '#cbd5e1'}; min-height: 24px; border-radius: 3px;
            }}
            QListWidget QScrollBar::handle:vertical:hover {{
                background: #6366f1;
            }}
            QListWidget QScrollBar::add-line:vertical, QListWidget QScrollBar::sub-line:vertical {{
                height: 0px; width: 0px; background: none; border: none;
            }}
            QListWidget QScrollBar::add-page:vertical, QListWidget QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
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

    def _setup_calendar_widget(self, date_edit: QDateEdit):
        """为 QDateEdit 弹出的 QCalendarWidget 注入现代极简暗黑/浅色高对比度主题，彻底告别白底与文字看不清"""
        if not date_edit:
            return
        cal = date_edit.calendarWidget()
        if not cal:
            return
        d = self._is_dark
        try:
            cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
            cal.setGridVisible(False)
            btn_prev = cal.findChild(QToolButton, "qt_calendar_prevmonth")
            btn_next = cal.findChild(QToolButton, "qt_calendar_nextmonth")
            if btn_prev:
                btn_prev.setIcon(QIcon())
                btn_prev.setText(" ◀ ")
            if btn_next:
                btn_next.setIcon(QIcon())
                btn_next.setText(" ▶ ")

            # 彻底禁用月份和年份按钮的下拉菜单与指示器，直接使用 ◀ ▶ 翻月，防止出现遮挡黑块
            btn_month = cal.findChild(QToolButton, "qt_calendar_monthbutton")
            if btn_month:
                btn_month.setMenu(None)
                btn_month.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            btn_year = cal.findChild(QToolButton, "qt_calendar_yearbutton")
            if btn_year:
                btn_year.setMenu(None)
                btn_year.setAttribute(Qt.WA_TransparentForMouseEvents, True)

            fmt = QTextCharFormat()
            fmt.setForeground(QColor("#e4e4e7" if d else "#334155"))
            fmt.setBackground(QColor("#27272a" if d else "#f1f5f9"))
            fmt.setFontWeight(QFont.Bold)
            for day in [Qt.Monday, Qt.Tuesday, Qt.Wednesday, Qt.Thursday, Qt.Friday]:
                cal.setWeekdayTextFormat(day, fmt)

            weekend_fmt = QTextCharFormat()
            weekend_fmt.setForeground(QColor("#f87171" if d else "#dc2626"))
            weekend_fmt.setBackground(QColor("#27272a" if d else "#f1f5f9"))
            weekend_fmt.setFontWeight(QFont.Bold)
            cal.setWeekdayTextFormat(Qt.Saturday, weekend_fmt)
            cal.setWeekdayTextFormat(Qt.Sunday, weekend_fmt)

            cal_qss = f"""
                QCalendarWidget {{
                    background-color: {'#18181b' if d else '#ffffff'};
                    border: 1px solid {'#3f3f46' if d else '#cbd5e1'};
                    border-radius: 8px;
                }}
                QCalendarWidget QWidget#qt_calendar_navigationbar {{
                    background-color: {'#27272a' if d else '#f8fafc'};
                    border-bottom: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                    min-height: 38px;
                }}
                QCalendarWidget QToolButton {{
                    background-color: transparent;
                    color: {'#f4f4f5' if d else '#0f172a'};
                    font-size: 13px; font-weight: bold;
                    border: none; border-radius: 6px; padding: 4px 10px;
                    font-family: 'Microsoft YaHei UI';
                }}
                QCalendarWidget QToolButton:hover {{
                    background-color: {'#3f3f46' if d else '#e2e8f0'};
                }}
                QCalendarWidget QToolButton#qt_calendar_monthbutton,
                QCalendarWidget QToolButton#qt_calendar_yearbutton {{
                    padding: 4px 6px;
                }}
                QCalendarWidget QToolButton#qt_calendar_monthbutton::menu-indicator,
                QCalendarWidget QToolButton#qt_calendar_yearbutton::menu-indicator {{
                    image: none;
                    width: 0px;
                    height: 0px;
                }}
                QCalendarWidget QTableView {{
                    background-color: {'#18181b' if d else '#ffffff'};
                    selection-background-color: {'#6366f1' if d else '#4f46e5'};
                    selection-color: #ffffff;
                    color: {'#f4f4f5' if d else '#0f172a'};
                    font-size: 12.5px; font-family: 'Microsoft YaHei UI';
                    outline: 0; border: none;
                }}
                QCalendarWidget QTableView:enabled {{
                    color: {'#f4f4f5' if d else '#0f172a'};
                }}
                QCalendarWidget QTableView:disabled {{
                    color: {'#52525b' if d else '#94a3b8'};
                }}
                QCalendarWidget QHeaderView::section {{
                    background-color: {'#27272a' if d else '#f1f5f9'};
                    color: {'#e4e4e7' if d else '#334155'};
                    font-size: 12px; font-weight: bold; border: none; padding: 6px 0;
                }}
            """
            cal.setStyleSheet(cal_qss)
        except Exception as e:
            print(f"[Calendar] Failed to setup calendar style: {e}")

    def _create_add_auto_view(self) -> QWidget:
        """1:1 复刻全屏专属添加/编辑自动化任务页面"""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(12)

        d = self._is_dark

        # 顶部导航行：⏰ 自动化 / 添加自动化任务  [取消] [保存]
        top_row = QHBoxLayout()
        self.auto_nav_lbl = QLabel("⏰ 自动化 / ＋ 添加自动化任务")
        self.auto_nav_lbl.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        self.auto_nav_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {'#f4f4f5' if d else '#0f172a'}; font-family: 'Microsoft YaHei UI';")
        top_row.addWidget(self.auto_nav_lbl)
        top_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(68, 32)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {'#27272a' if d else '#f1f5f9'}; color: {'#f4f4f5' if d else '#475569'}; border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                border-radius: 8px; font-size: 12px; font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{ background: {'#3f3f46' if d else '#e2e8f0'}; }}
        """)
        cancel_btn.clicked.connect(lambda: self.auto_main_stack.setCurrentIndex(0))
        top_row.addWidget(cancel_btn)

        self.auto_save_btn = QPushButton("保存")
        self.auto_save_btn.setFixedSize(78, 32)
        self.auto_save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {'#27272a' if d else '#0f172a'}; color: #ffffff; border: 1px solid {'#3f3f46' if d else 'none'};
                border-radius: 8px; font-size: 12px; font-weight: bold; font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{ background: {'#3f3f46' if d else '#1e293b'}; }}
        """)
        self.auto_save_btn.clicked.connect(self._save_new_automation_from_view)
        top_row.addWidget(self.auto_save_btn)
        lay.addLayout(top_row)

        # 滚动表单区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;} QScrollArea > QWidget > QWidget{background:transparent;}")
        scroll.viewport().setStyleSheet("background: transparent;")

        form_w = QWidget()
        form_w.setStyleSheet("background: transparent;")
        f_lay = QVBoxLayout(form_w)
        f_lay.setContentsMargins(0, 4, 0, 10)
        f_lay.setSpacing(12)

        # 蓝色提示条
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
        tip_text = QLabel("自动化任务后台由 PetScheduler 守护线程按频次自动触发，支持一键测试、专家角色思维链及多端推送。")
        tip_text.setStyleSheet(f"color: {'#93c5fd' if d else '#1d4ed8'}; font-size: 12px; font-family: 'Microsoft YaHei UI';")
        t_lay.addWidget(tip_text, 1)
        close_tip = QPushButton("✕")
        close_tip.setFixedSize(20, 20)
        close_tip.setStyleSheet(f"background: transparent; color: {'#93c5fd' if d else '#60a5fa'}; border: none;")
        close_tip.clicked.connect(lambda: tip_box.hide())
        t_lay.addWidget(close_tip)
        f_lay.addWidget(tip_box)

        inp_style = f"""
            QLineEdit, QTextEdit, QSpinBox {{
                background: {'#1e1e1e' if d else '#ffffff'};
                color: {'#f4f4f5' if d else '#0f172a'};
                border: 1px solid {'#2e2e2e' if d else '#cbd5e1'};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12.5px;
                font-family: 'Microsoft YaHei UI';
                selection-background-color: {'#3b3b40' if d else '#c7d2fe'};
                selection-color: {'#ffffff' if d else '#1e1b4b'};
            }}
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {{
                border-color: #6366f1;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: {'#27272a' if d else '#f1f5f9'};
                border: none;
                width: 18px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background: {'#3f3f46' if d else '#e2e8f0'};
            }}
            QSpinBox::up-arrow {{
                image: none; width: 0; height: 0;
                border-left: 4px solid transparent; border-right: 4px solid transparent;
                border-bottom: 5px solid {'#a1a1aa' if d else '#64748b'};
            }}
            QSpinBox::down-arrow {{
                image: none; width: 0; height: 0;
                border-left: 4px solid transparent; border-right: 4px solid transparent;
                border-top: 5px solid {'#a1a1aa' if d else '#64748b'};
            }}
            
            QComboBox, QDateEdit {{
                background: {'#1e1e1e' if d else '#ffffff'};
                color: {'#f4f4f5' if d else '#0f172a'};
                border: 1px solid {'#2e2e2e' if d else '#cbd5e1'};
                border-radius: 8px;
                padding: 4px 24px 4px 10px;
                font-size: 13px;
                font-family: Consolas, 'Segoe UI', 'Microsoft YaHei UI';
                selection-background-color: {'#3b3b40' if d else '#c7d2fe'};
                selection-color: {'#ffffff' if d else '#1e1b4b'};
            }}
            QComboBox:hover, QDateEdit:hover {{
                border-color: #6366f1;
            }}
            QComboBox:focus, QDateEdit:focus {{
                border-color: #818cf8;
            }}
            QComboBox::drop-down, QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 22px;
                border: none;
                background: transparent;
            }}
            QComboBox::down-arrow, QDateEdit::down-arrow {{
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {'#a1a1aa' if d else '#64748b'};
                width: 0px;
                height: 0px;
                margin-right: 8px;
            }}
            QComboBox::down-arrow:hover, QDateEdit::down-arrow:hover {{
                border-top-color: #6366f1;
            }}
            QComboBox QAbstractItemView {{
                background: {'#1e1e1e' if d else '#ffffff'};
                color: {'#f4f4f5' if d else '#0f172a'};
                border: 1px solid {'#3f3f46' if d else '#cbd5e1'};
                border-radius: 8px;
                padding: 4px 2px;
                selection-background-color: #6366f1;
                selection-color: #ffffff;
                outline: none;
                font-family: 'Segoe UI', 'Microsoft YaHei UI';
                font-size: 13px;
            }}
            QComboBox QAbstractItemView::item {{
                height: 28px;
                padding: 2px 10px;
                margin: 1px 4px;
                border-radius: 5px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {'#27272a' if d else '#e2e8f0'};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: #6366f1;
                color: #ffffff;
                font-weight: bold;
            }}
            /* 现代极简平滑细长暗黑滚动条：彻底消灭 Windows 98 点状灰方块与大黑箭头 */
            QComboBox QAbstractItemView QScrollBar:vertical {{
                background: transparent;
                width: 5px;
                margin: 4px 2px 4px 0px;
                border: none;
            }}
            QComboBox QAbstractItemView QScrollBar::handle:vertical {{
                background: {'#3f3f46' if d else '#cbd5e1'};
                min-height: 24px;
                border-radius: 2.5px;
            }}
            QComboBox QAbstractItemView QScrollBar::handle:vertical:hover {{
                background: #6366f1;
            }}
            QComboBox QAbstractItemView QScrollBar::add-line:vertical,
            QComboBox QAbstractItemView QScrollBar::sub-line:vertical {{
                height: 0px;
                width: 0px;
                background: none;
                border: none;
            }}
            QComboBox QAbstractItemView QScrollBar::add-page:vertical,
            QComboBox QAbstractItemView QScrollBar::sub-page:vertical {{
                background: none;
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

        # 提示词下方辅助胶囊行：⚙️ Auto ∨、🪄 技能 ∨、🎓 召唤专家 ∨、⚠️ 完全访问权限 ∨
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

        # 5. 执行频率
        self.freq_title_lbl = QLabel("执行频率")
        self.freq_title_lbl.setStyleSheet(f"font-size: 12px; color: {'#a1a1aa' if d else '#64748b'};")
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

        # 频率具体配置 Stack (3 种模式动态切换，紧凑无多余间隙)
        self.freq_stack = QStackedWidget()
        self.freq_stack.setFixedHeight(44)
        self.freq_stack.setStyleSheet("background: transparent;")

        # ── 模式 0：周期
        w_period = QWidget()
        w_period.setStyleSheet("background: transparent;")
        l_period = QHBoxLayout(w_period); l_period.setContentsMargins(0, 0, 0, 0); l_period.setSpacing(10)
        self.auto_cycle_combo = QComboBox()
        self.auto_cycle_combo.setFixedSize(96, 34)
        self.auto_cycle_combo.addItems(["每天", "工作日", "每周", "每月"])
        self.auto_cycle_combo.setStyleSheet(inp_style)
        l_period.addWidget(self.auto_cycle_combo)

        p_t_icon = QLabel("🕒")
        p_t_icon.setStyleSheet(f"font-size: 14px; color: {'#a1a1aa' if d else '#64748b'};")
        l_period.addWidget(p_t_icon)

        self.auto_time_edit = ModernTimeEdit(is_dark=d)
        self.auto_time_edit.setTime(QTime.currentTime())
        self.auto_time_edit.setFixedSize(115, 34)
        self.auto_time_edit.setStyleSheet(inp_style)
        l_period.addWidget(self.auto_time_edit)
        l_period.addStretch()
        self.freq_stack.addWidget(w_period)

        # ── 模式 1：按间隔
        w_interval = QWidget()
        w_interval.setStyleSheet("background: transparent;")
        l_interval = QHBoxLayout(w_interval); l_interval.setContentsMargins(0, 0, 0, 0); l_interval.setSpacing(8)
        lbl_every = QLabel("每")
        lbl_every.setStyleSheet(f"font-size: 12.5px; color: {'#f4f4f5' if d else '#0f172a'};")
        l_interval.addWidget(lbl_every)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 24)
        self.interval_spin.setValue(1)
        self.interval_spin.setFixedSize(60, 32)
        self.interval_spin.setStyleSheet(inp_style)
        l_interval.addWidget(self.interval_spin)

        lbl_hour = QLabel("小时")
        lbl_hour.setStyleSheet(f"font-size: 12.5px; color: {'#f4f4f5' if d else '#0f172a'};")
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
            wb.setStyleSheet(f"""
                QPushButton {{
                    background: {'#27272a' if d else '#f1f5f9'};
                    color: {'#f4f4f5' if d else '#334155'};
                    border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                    border-radius: 6px; font-size: 11.5px; font-family: 'Microsoft YaHei UI';
                }}
                QPushButton:checked {{
                    background: {'#3f3f46' if d else '#e2e8f0'};
                    color: {'#ffffff' if d else '#0f172a'};
                    font-weight: bold; border-color: {'#6366f1' if d else '#cbd5e1'};
                }}
            """)
            l_interval.addWidget(wb)
            self.weekday_buttons.append(wb)
        l_interval.addStretch()
        self.freq_stack.addWidget(w_interval)

        # ── 模式 2：单次
        w_single = QWidget()
        w_single.setStyleSheet("background: transparent;")
        l_single = QHBoxLayout(w_single); l_single.setContentsMargins(0, 0, 0, 0); l_single.setSpacing(10)

        s_t_icon = QLabel("🕒")
        s_t_icon.setStyleSheet(f"font-size: 14px; color: {'#a1a1aa' if d else '#64748b'};")
        l_single.addWidget(s_t_icon)

        self.single_time_edit = ModernTimeEdit(is_dark=d)
        now_future = datetime.now() + timedelta(minutes=10)
        self.single_time_edit.setTime(QTime(now_future.hour, now_future.minute))
        self.single_time_edit.setFixedSize(115, 34)
        self.single_time_edit.setStyleSheet(inp_style)
        l_single.addWidget(self.single_time_edit)

        s_d_icon = QLabel("📅")
        s_d_icon.setStyleSheet(f"font-size: 14px; color: {'#a1a1aa' if d else '#64748b'};")
        l_single.addWidget(s_d_icon)

        self.single_date_edit = QDateEdit()
        self.single_date_edit.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.single_date_edit.setDisplayFormat("yyyy/MM/dd ddd")
        self.single_date_edit.setDate(QDate(now_future.year, now_future.month, now_future.day))
        self.single_date_edit.setFixedSize(165, 34)
        self.single_date_edit.setStyleSheet(inp_style)
        self.single_date_edit.setCalendarPopup(True)
        self._setup_calendar_widget(self.single_date_edit)
        l_single.addWidget(self.single_date_edit)
        l_single.addStretch()
        self.freq_stack.addWidget(w_single)

        f_lay.addWidget(self.freq_stack)
        self._switch_freq_mode(0)

        # 6. 生效日期区间 (周期与间隔模式适用)
        self.auto_range_box = QWidget()
        range_box_lay = QVBoxLayout(self.auto_range_box)
        range_box_lay.setContentsMargins(0, 4, 0, 4)
        range_box_lay.setSpacing(6)

        self.auto_range_cb = QCheckBox("限制任务生效日期区间 (不勾选则长期生效)")
        self.auto_range_cb.setStyleSheet(f"font-size: 12px; color: {'#f4f4f5' if d else '#0f172a'}; font-family: 'Microsoft YaHei UI';")
        range_box_lay.addWidget(self.auto_range_cb)

        self.auto_range_dates_w = QWidget()
        range_dates_lay = QHBoxLayout(self.auto_range_dates_w)
        range_dates_lay.setContentsMargins(0, 0, 0, 0)
        range_dates_lay.setSpacing(8)

        r_lbl1 = QLabel("📅 开始生效:")
        r_lbl1.setStyleSheet(f"font-size: 12px; color: {'#a1a1aa' if d else '#64748b'};")
        range_dates_lay.addWidget(r_lbl1)
        self.auto_start_date_edit = QDateEdit()
        self.auto_start_date_edit.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.auto_start_date_edit.setDate(QDate.currentDate())
        self.auto_start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.auto_start_date_edit.setFixedSize(130, 34)
        self.auto_start_date_edit.setStyleSheet(inp_style)
        self.auto_start_date_edit.setCalendarPopup(True)
        self._setup_calendar_widget(self.auto_start_date_edit)
        range_dates_lay.addWidget(self.auto_start_date_edit)

        r_lbl2 = QLabel("📅 截止生效:")
        r_lbl2.setStyleSheet(f"font-size: 12px; color: {'#a1a1aa' if d else '#64748b'};")
        range_dates_lay.addWidget(r_lbl2)
        self.auto_end_date_edit = QDateEdit()
        self.auto_end_date_edit.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.auto_end_date_edit.setDate(QDate.currentDate().addMonths(1))
        self.auto_end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.auto_end_date_edit.setFixedSize(130, 34)
        self.auto_end_date_edit.setStyleSheet(inp_style)
        self.auto_end_date_edit.setCalendarPopup(True)
        self._setup_calendar_widget(self.auto_end_date_edit)
        range_dates_lay.addWidget(self.auto_end_date_edit)
        range_dates_lay.addStretch()

        self.auto_range_dates_w.hide()
        self.auto_range_cb.toggled.connect(self.auto_range_dates_w.setVisible)
        range_box_lay.addWidget(self.auto_range_dates_w)

        r_hint = QLabel("💡 提示：在生效区间外的日期，即使到达设定时间，调度器也会自动跳过执行。")
        r_hint.setStyleSheet(f"font-size: 11px; color: {'#71717a' if d else '#94a3b8'};")
        range_box_lay.addWidget(r_hint)
        f_lay.addWidget(self.auto_range_box)

        # 底部弹性间距，保持所有控件紧凑置顶
        f_lay.addStretch(1)

        scroll.setWidget(form_w)
        lay.addWidget(scroll, 1)
        return w

    def _switch_freq_mode(self, idx: int):
        self.freq_stack.setCurrentIndex(idx)
        btns = [self.freq_btn_period, self.freq_btn_interval, self.freq_btn_single]
        d = self._is_dark
        active_bg = "#27272a" if d else "#0f172a"
        active_fg = "#ffffff"
        active_border = "#6366f1" if d else "#0f172a"
        inactive_bg = "#1e1e1e" if d else "#f1f5f9"
        inactive_fg = "#a1a1aa" if d else "#475569"
        inactive_border = "#2e2e2e" if d else "#e2e8f0"

        for i, b in enumerate(btns):
            active = (i == idx)
            b.setChecked(active)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {active_bg if active else inactive_bg};
                    color: {active_fg if active else inactive_fg};
                    border: 1px solid {active_border if active else inactive_border};
                    border-radius: 6px; font-size: 11.5px;
                    font-family: 'Microsoft YaHei UI';
                    font-weight: {'bold' if active else 'normal'};
                }}
                QPushButton:hover {{
                    background: {'#3f3f46' if d else '#e2e8f0'};
                    color: {'#ffffff' if d else '#0f172a'};
                }}
            """)
        if idx == 2:
            self.freq_title_lbl.setText("执行频率 (单次指定年月日执行；建议避开上午高峰时段更稳定)")
            if hasattr(self, 'auto_range_box'):
                self.auto_range_box.hide()
        else:
            self.freq_title_lbl.setText("执行频率")
            if hasattr(self, 'auto_range_box'):
                self.auto_range_box.show()

    def _open_wecom_config(self):
        dlg = WeComConfigDialog(is_dark=self._is_dark, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self._show_status("✅ 企业微信群机器人配置已保存")

    def _open_wechat_config(self):
        dlg = WeChatConfigDialog(is_dark=self._is_dark, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self._show_status("✅ 手机微信推送配置已保存")

    def _on_auto_model_pill_clicked(self):
        models = ["⚙️ Auto", "🤖 DeepSeek-V3", "🤖 DeepSeek-R1", "🤖 Qwen2.5-Coder"]
        menu = QMenu(self)
        for m in models:
            act = menu.addAction(m)
            act.triggered.connect(lambda ch, mod=m: self._on_auto_model_chosen(mod))
        sender = self.sender() or self.auto_pill_model
        menu.exec_(sender.mapToGlobal(QPoint(0, sender.height() + 2)))

    def _on_auto_model_chosen(self, mod: str):
        self._selected_model = mod
        self.auto_pill_model.setText(f"{mod} ∨")
        self._show_status(f"已选定模型：{mod}")

    def _on_auto_skill_pill_clicked(self):
        # 若当前已选技能（按钮带 ✕），点击该按钮立即清空重置，回到重新选择状态
        if getattr(self, "_selected_skill", None) and self._selected_skill.get("name"):
            self._on_auto_skill_chosen("", "")
            return

        skills = self._get_skills_data()
        popup = AutoSkillSelectPopup(skills=skills, is_dark=self._is_dark, parent=self)
        popup.skill_selected.connect(self._on_auto_skill_chosen)
        popup.import_requested.connect(lambda: self._show_status("已唤起技能导入向导"))
        sender = self.sender() or self.auto_pill_skill
        p_global = sender.mapToGlobal(QPoint(0, 0))
        target_x = p_global.x()
        target_y = p_global.y() + sender.height() + 4
        screen = QApplication.desktop().availableGeometry(sender)
        if target_y + popup.height() > screen.bottom() - 10:
            target_y = max(screen.top() + 10, p_global.y() - popup.height() - 4)
        target_x = max(screen.left() + 10, min(target_x, screen.right() - popup.width() - 10))
        popup.move(target_x, target_y)
        popup.show()

    def _on_auto_skill_chosen(self, name: str, prompt: str):
        d = self._is_dark
        if name:
            self._selected_skill = {"name": name, "prompt": prompt}
            self.auto_pill_skill.setText(f"🪄 {name} ✕")
            self.auto_pill_skill.setStyleSheet(f"""
                QPushButton {{
                    background: {'#1e1b4b' if d else '#e0e7ff'};
                    color: {'#a5b4fc' if d else '#4338ca'};
                    border: 1px solid {'#4338ca' if d else '#c7d2fe'};
                    border-radius: 6px; padding: 0 10px; font-size: 11.5px;
                    font-family: 'Microsoft YaHei UI'; font-weight: bold;
                }}
                QPushButton:hover {{ background: {'#312e81' if d else '#c7d2fe'}; }}
            """)
            self._show_status(f"已绑定技能：{name}")
        else:
            self._selected_skill = {}
            self.auto_pill_skill.setText("🪄 技能 ∨")
            self.auto_pill_skill.setStyleSheet(f"""
                QPushButton {{
                    background: {'#27272a' if d else '#f1f5f9'}; color: {'#f4f4f5' if d else '#334155'}; border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                    border-radius: 6px; padding: 0 10px; font-size: 11.5px;
                    font-family: 'Microsoft YaHei UI';
                }}
                QPushButton:hover {{ background: {'#3f3f46' if d else '#e2e8f0'}; color: {'#ffffff' if d else '#0f172a'}; }}
            """)
            self._show_status("已清除选定的技能，可重新选择")

    def _on_auto_expert_pill_clicked(self):
        # 若当前已选专家（按钮带 ✕），点击该按钮立即清空重置，回到重新选择状态
        if getattr(self, "_selected_expert", None) and self._selected_expert.get("name"):
            self._on_auto_expert_chosen("", "")
            return

        popup = AutoExpertSelectPopup(is_dark=self._is_dark, parent=self)
        popup.expert_selected.connect(self._on_auto_expert_chosen)
        popup.more_requested.connect(lambda: self._switch_nav(1))
        sender = self.sender() or self.auto_pill_expert
        p_global = sender.mapToGlobal(QPoint(0, 0))
        target_x = p_global.x()
        target_y = p_global.y() + sender.height() + 4
        screen = QApplication.desktop().availableGeometry(sender)
        if target_y + popup.height() > screen.bottom() - 10:
            target_y = max(screen.top() + 10, p_global.y() - popup.height() - 4)
        target_x = max(screen.left() + 10, min(target_x, screen.right() - popup.width() - 10))
        popup.move(target_x, target_y)
        popup.show()

    def _on_auto_expert_chosen(self, name: str, prompt: str):
        d = self._is_dark
        if name:
            self._selected_expert = {"name": name, "prompt": prompt}
            self.auto_pill_expert.setText(f"🎓 {name} ✕")
            self.auto_pill_expert.setStyleSheet(f"""
                QPushButton {{
                    background: {'#064e3b' if d else '#d1fae5'};
                    color: {'#6ee7b7' if d else '#065f46'};
                    border: 1px solid {'#065f46' if d else '#a7f3d0'};
                    border-radius: 6px; padding: 0 10px; font-size: 11.5px;
                    font-family: 'Microsoft YaHei UI'; font-weight: bold;
                }}
                QPushButton:hover {{ background: {'#065f46' if d else '#a7f3d0'}; }}
            """)
            self._show_status(f"已召唤专家：{name}")
        else:
            self._selected_expert = {}
            self.auto_pill_expert.setText("🎓 召唤专家 ∨")
            self.auto_pill_expert.setStyleSheet(f"""
                QPushButton {{
                    background: {'#27272a' if d else '#f1f5f9'}; color: {'#f4f4f5' if d else '#334155'}; border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                    border-radius: 6px; padding: 0 10px; font-size: 11.5px;
                    font-family: 'Microsoft YaHei UI';
                }}
                QPushButton:hover {{ background: {'#3f3f46' if d else '#e2e8f0'}; color: {'#ffffff' if d else '#0f172a'}; }}
            """)
            self._show_status("已清除专家，使用默认通用助手，可重新选择")

    def _on_auto_perm_pill_clicked(self):
        is_full = ("完全" in self.auto_pill_perm.text())
        popup = AutoPermissionSelectPopup(
            current_perm="full" if is_full else "standard",
            is_dark=self._is_dark,
            parent=self
        )
        popup.permission_chosen.connect(self._on_auto_perm_chosen)
        sender = self.sender() or self.auto_pill_perm
        p_global = sender.mapToGlobal(QPoint(0, 0))
        target_x = p_global.x()
        target_y = p_global.y() + sender.height() + 4
        screen = QApplication.desktop().availableGeometry(sender)
        if target_y + popup.height() > screen.bottom() - 10:
            target_y = max(screen.top() + 10, p_global.y() - popup.height() - 4)
        target_x = max(screen.left() + 10, min(target_x, screen.right() - popup.width() - 10))
        popup.move(target_x, target_y)
        popup.show()

    def _on_auto_perm_chosen(self, mode: str):
        self._selected_permission = mode
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
        self._editing_task_id = None
        self.auto_nav_lbl.setText("⏰ 自动化 / ＋ 添加自动化任务")
        self.auto_save_btn.setText("保存")
        self.auto_name_edit.setText(name)
        self.auto_prompt_edit.setText(prompt)
        self._switch_freq_mode(0)
        now_dt = datetime.now()
        future_dt = now_dt + timedelta(minutes=10)
        self.auto_time_edit.setTime(QTime(future_dt.hour, future_dt.minute))
        self.single_time_edit.setTime(QTime(future_dt.hour, future_dt.minute))
        self.single_date_edit.setDate(QDate(future_dt.year, future_dt.month, future_dt.day))
        self._on_auto_expert_chosen("", "")
        self._on_auto_skill_chosen("", "")
        self._on_auto_model_chosen("⚙️ Auto")
        self._on_auto_perm_chosen("full")
        self.auto_range_cb.setChecked(False)
        self.auto_main_stack.setCurrentIndex(1)

    def _open_add_auto_view_from_template(self, t_data: dict):
        """点击模版卡片：精确反填模版对应的名称、提示词、执行频率类型及预设时间"""
        self._editing_task_id = None
        self.auto_nav_lbl.setText("⏰ 自动化 / ＋ 添加自动化任务 (来自模版)")
        self.auto_save_btn.setText("保存")
        name = t_data.get("name", "")
        prompt = t_data.get("cmd", "")
        self.auto_name_edit.setText(name)
        self.auto_prompt_edit.setText(prompt)

        self._on_auto_expert_chosen("", "")
        self._on_auto_skill_chosen("", "")
        self._on_auto_model_chosen("⚙️ Auto")
        self._on_auto_perm_chosen("full")
        self.auto_range_cb.setChecked(False)

        freq_mode = t_data.get("freq_mode", 0)
        self._switch_freq_mode(freq_mode)

        if freq_mode == 2:  # 单次提醒（如：体检预约）
            date_str = t_data.get("date", "")
            if not date_str:
                date_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            time_str = t_data.get("time", "08:00")
            qd = QDate.fromString(date_str, "yyyy-MM-dd")
            if qd.isValid():
                self.single_date_edit.setDate(qd)
            qt = QTime.fromString(time_str, "HH:mm")
            if qt.isValid():
                self.single_time_edit.setTime(qt)
        elif freq_mode == 1:  # 按间隔（如：工作日每2小时）
            self.interval_spin.setValue(t_data.get("interval", 2))
        else:  # 周期循环（如：每天/每周）
            cycle = t_data.get("cycle", "每天")
            self.auto_cycle_combo.setCurrentText(cycle)
            time_str = t_data.get("time", "09:00")
            qt = QTime.fromString(time_str, "HH:mm")
            if qt.isValid():
                self.auto_time_edit.setTime(qt)

        self.auto_main_stack.setCurrentIndex(1)

    def _edit_automation_task(self, task_id: int):
        """编辑修改已有自动化任务"""
        try:
            from core.pet_scheduler import PetScheduler
            r = PetScheduler.get_instance().get_reminder_by_id(task_id)
            if not r:
                show_themed_warning(self, "编辑失败", "未找到该任务信息，可能已被删除", self._is_dark)
                return

            self._editing_task_id = task_id
            self.auto_nav_lbl.setText("⏰ 自动化 / ✏️ 编辑自动化任务")
            self.auto_save_btn.setText("更新任务")

            title = r.get("title", "").replace("⏰", "").strip()
            self.auto_name_edit.setText(title)
            self.auto_prompt_edit.setText(r.get("content", ""))

            # 频率模式反填
            repeat = r.get("repeat", "once")
            trig_dt = r.get("trigger_dt")
            if repeat == "once":
                self._switch_freq_mode(2)
                if isinstance(trig_dt, datetime):
                    self.single_date_edit.setDate(QDate(trig_dt.year, trig_dt.month, trig_dt.day))
                    self.single_time_edit.setTime(QTime(trig_dt.hour, trig_dt.minute))
            elif repeat == "interval":
                self._switch_freq_mode(1)
                sec = r.get("interval_sec", 3600)
                self.interval_spin.setValue(max(1, int(sec // 3600)))
            else:
                self._switch_freq_mode(0)
                self.auto_cycle_combo.setCurrentText("每周" if repeat == "weekly" else "每天")
                if isinstance(trig_dt, datetime):
                    self.auto_time_edit.setTime(QTime(trig_dt.hour, trig_dt.minute))

            # 专家反填
            exp_name = r.get("expert", "")
            self._on_auto_expert_chosen(exp_name, "")

            # 技能反填
            sk_name = r.get("skill", "")
            self._on_auto_skill_chosen(sk_name, "")

            # 模型反填
            mod = r.get("model", "") or "⚙️ Auto"
            self._on_auto_model_chosen(mod)

            # 权限反填
            perm = r.get("permission", "full")
            self._on_auto_perm_chosen(perm)

            # 生效日期区间反填
            st_d = r.get("start_date", "")
            ed_d = r.get("end_date", "")
            if st_d or ed_d:
                self.auto_range_cb.setChecked(True)
                if st_d:
                    qd = QDate.fromString(st_d, "yyyy-MM-dd")
                    if qd.isValid(): self.auto_start_date_edit.setDate(qd)
                if ed_d:
                    qd = QDate.fromString(ed_d, "yyyy-MM-dd")
                    if qd.isValid(): self.auto_end_date_edit.setDate(qd)
            else:
                self.auto_range_cb.setChecked(False)

            self.auto_main_stack.setCurrentIndex(1)
            self._show_status(f"✏️ 正在编辑任务：{title}")
        except Exception as e:
            show_themed_warning(self, "编辑异常", f"加载任务信息失败: {e}", self._is_dark)

    def _test_trigger_automation_task(self, task_id: int):
        """立即测试触发自动化任务：直接启动 AI 任务执行并联动桌宠"""
        try:
            from core.pet_scheduler import PetScheduler
            sched = PetScheduler.get_instance()
            r = sched.get_reminder_by_id(task_id)
            if not r:
                show_themed_warning(self, "测试失败", "未找到指定任务，可能已被删除", self._is_dark)
                return

            self._show_status(f"⚡ 正在立即测试执行任务：{r.get('title', '')}")
            # 1. 触发调度器广播（桌宠动作、提示音）
            sched.trigger_reminder_now(task_id)
            # 2. 真正执行任务：在聊天会话中生成完整结果
            self.execute_automation_task(task_id, r.get("title", "自动化任务"), r.get("content", ""))
        except Exception as e:
            show_themed_warning(self, "测试失败", f"触发任务失败: {e}", self._is_dark)

    def _save_new_automation_from_view(self):
        name = self.auto_name_edit.text().strip()
        prompt = self.auto_prompt_edit.toPlainText().strip()
        if not name:
            show_themed_warning(self, "提示", "请填写任务名称", self._is_dark)
            return
        if not prompt:
            show_themed_warning(self, "提示", "请填写提示词指令", self._is_dark)
            return

        mode = self.freq_stack.currentIndex()
        start_date = ""
        end_date = ""
        if mode == 2:  # 单次
            d = self.single_date_edit.date()
            t = self.single_time_edit.time()
            target_dt = datetime(d.year(), d.month(), d.day(), t.hour(), t.minute(), 0)
            if target_dt <= datetime.now():
                show_themed_warning(
                    self, 
                    "时间设置无效", 
                    f"单次任务设定时间 ({target_dt.strftime('%Y-%m-%d %H:%M')}) 不能早于当前时间！\n请选择未来的日期与时间，避免保存后立即判定为过期。", 
                    self._is_dark
                )
                return
            date_str = f"{d.year():04d}-{d.month():02d}-{d.day():02d}"
            time_str = f"{date_str} {t.hour():02d}:{t.minute():02d}:00"
            repeat_mode = "once"
            interval_sec = 0
            log_desc = f"设定单次定时任务 ({date_str} {t.hour():02d}:{t.minute():02d})"
        elif mode == 1:  # 按间隔
            hours = self.interval_spin.value()
            interval_sec = hours * 3600
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            repeat_mode = "interval"
            log_desc = f"设定间隔任务 (每 {hours} 小时)"
            if self.auto_range_cb.isChecked():
                start_date = self.auto_start_date_edit.date().toString("yyyy-MM-dd")
                end_date = self.auto_end_date_edit.date().toString("yyyy-MM-dd")
        else:  # 周期
            cycle = self.auto_cycle_combo.currentText()
            t = self.auto_time_edit.time()
            time_str = f"{t.hour():02d}:{t.minute():02d}"
            repeat_mode = "weekly" if cycle == "每周" else "daily"
            interval_sec = 0
            log_desc = f"设定周期定时任务 ({cycle} {time_str})"
            if self.auto_range_cb.isChecked():
                start_date = self.auto_start_date_edit.date().toString("yyyy-MM-dd")
                end_date = self.auto_end_date_edit.date().toString("yyyy-MM-dd")

        expert_name = self._selected_expert.get("name", "") if isinstance(self._selected_expert, dict) else ""
        skill_name = self._selected_skill.get("name", "") if isinstance(self._selected_skill, dict) else ""
        model_name = getattr(self, "_selected_model", "⚙️ Auto")
        perm_mode = getattr(self, "_selected_permission", "full")
        push_wecom = False
        push_wechat = False

        try:
            from core.pet_scheduler import PetScheduler
            sched = PetScheduler.get_instance()
            if self._editing_task_id:
                # 更新已有任务
                sched.update_reminder(
                    reminder_id=self._editing_task_id,
                    content=prompt,
                    target_time_str=time_str,
                    title=f"⏰ {name}",
                    repeat=repeat_mode,
                    interval_sec=interval_sec,
                    start_date=start_date,
                    end_date=end_date,
                    expert=expert_name,
                    skill=skill_name,
                    model=model_name,
                    permission=perm_mode,
                    push_wecom=push_wecom,
                    push_wechat=push_wechat
                )
                self._show_status(f"✅ 自动化任务已更新：{name}")
                self._log_auto_run(name, prompt, "updated", f"已更新任务配置 ({log_desc})")
            else:
                # 新建任务
                sched.add_reminder(
                    content=prompt,
                    target_time_str=time_str,
                    title=f"⏰ {name}",
                    motion="nod",
                    repeat=repeat_mode,
                    interval_sec=interval_sec,
                    start_date=start_date,
                    end_date=end_date,
                    expert=expert_name,
                    skill=skill_name,
                    model=model_name,
                    permission=perm_mode,
                    push_wecom=push_wecom,
                    push_wechat=push_wechat
                )
                self._show_status(f"✅ 自动化任务已创建：{name}")
                self._log_auto_run(name, prompt, "pending", log_desc)

            self._editing_task_id = None
            self._refresh_task_list()
            self._refresh_auto_log()
            self.auto_main_stack.setCurrentIndex(0)
        except Exception as e:
            print("[DEBUG _save Exception]:", e)
            import traceback
            traceback.print_exc()
            show_themed_warning(self, "保存失败", f"保存自动化任务失败：{e}", self._is_dark)

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

        d = self._is_dark
        if not has_tasks and hasattr(self, 'auto_empty_tip') and hasattr(self, 'auto_empty_subtip'):
            self.auto_empty_tip.setStyleSheet(f"color: {'#e4e4e7' if d else '#334155'}; font-size: 13.5px; font-weight: 500; font-family: 'Microsoft YaHei UI';")
            self.auto_empty_subtip.setStyleSheet(f"color: {'#71717a' if d else '#94a3b8'}; font-size: 11.5px; font-family: 'Microsoft YaHei UI';")
            try:
                logs = load_auto_log()
            except Exception:
                logs = []
            if logs:
                self.auto_empty_tip.setText("暂无待触发的定时任务")
                self.auto_empty_subtip.setText(f"共有 {len(logs)} 条历史执行任务已归档 · 请切换上方「📋 运行记录」查看")
            else:
                self.auto_empty_tip.setText("开启你的第一个自动化任务吧")
                self.auto_empty_subtip.setText("创建每日/每周定时提醒，到点全自动调用 AI 分析并汇报")
        self.task_list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {'#18181b' if d else '#ffffff'};
                border: 1px solid {'#27272a' if d else '#e2e8f0'};
                border-radius: 12px;
                padding: 6px;
                outline: none;
            }}
            QListWidget::item {{
                background: transparent;
                border: none;
                padding: 0px;
                margin: 2px 0px;
            }}
        """)
        self.task_list_widget.setFixedHeight(min(280, max(82, len(reminders) * 80 + 16)))

        for r in reminders:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 74))
            item.setData(Qt.UserRole, r.get("id"))

            card = QFrame()
            card_bg = "#222225" if d else "#f8fafc"
            card_border = "#2e2e32" if d else "#e2e8f0"
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {card_bg};
                    border: 1px solid {card_border};
                    border-radius: 10px;
                }}
                QFrame:hover {{
                    border-color: {'#404040' if d else '#6366f1'};
                }}
            """)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(14, 8, 14, 8)
            c_lay.setSpacing(10)

            icon_lbl = QLabel("⏰")
            icon_lbl.setFont(QFont("Segoe UI Emoji", 16))
            icon_lbl.setStyleSheet("background: transparent; border: none;")
            c_lay.addWidget(icon_lbl)

            v_box = QVBoxLayout()
            v_box.setSpacing(2)
            title_text = r.get("title", "自动化任务").replace("⏰", "").strip()
            title_lbl = QLabel(title_text)
            title_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {'#f4f4f5' if d else '#0f172a'}; font-family: 'Microsoft YaHei UI'; background: transparent; border: none;")

            content_text = r.get("content", "")
            if len(content_text) > 38:
                content_text = content_text[:38] + "..."
            content_lbl = QLabel(f"指令: {content_text}")
            content_lbl.setStyleSheet(f"font-size: 11px; color: {'#a1a1aa' if d else '#64748b'}; font-family: 'Microsoft YaHei UI'; background: transparent; border: none;")

            # 徽章行：显示绑定的专家、技能、推送方式与区间
            tags_row = QHBoxLayout()
            tags_row.setSpacing(5)

            exp = r.get("expert", "")
            if exp:
                tag_e = QLabel(f"🎓 {exp}")
                tag_e.setStyleSheet("background: #064e3b; color: #6ee7b7; border-radius: 4px; padding: 1px 5px; font-size: 10px; font-weight: bold;")
                tags_row.addWidget(tag_e)

            sk = r.get("skill", "")
            if sk:
                tag_s = QLabel(f"🪄 {sk}")
                tag_s.setStyleSheet("background: #1e1b4b; color: #a5b4fc; border-radius: 4px; padding: 1px 5px; font-size: 10px; font-weight: bold;")
                tags_row.addWidget(tag_s)

            st_d = r.get("start_date", "")
            ed_d = r.get("end_date", "")
            if st_d or ed_d:
                tag_dr = QLabel(f"📅 {st_d}~{ed_d}")
                tag_dr.setStyleSheet("background: #374151; color: #d1d5db; border-radius: 4px; padding: 1px 5px; font-size: 10px;")
                tags_row.addWidget(tag_dr)

            tags_row.addStretch()

            v_box.addWidget(title_lbl)
            v_box.addWidget(content_lbl)
            v_box.addLayout(tags_row)
            c_lay.addLayout(v_box, 1)

            time_box = QVBoxLayout()
            time_box.setSpacing(3)
            time_box.setAlignment(Qt.AlignRight)

            time_val = r.get("time", "")
            repeat_val = r.get("repeat", "once")
            repeat_tag = "单次" if repeat_val == "once" else ("每天" if repeat_val == "daily" else ("每周" if repeat_val == "weekly" else "间隔"))

            trigger_lbl = QLabel(f"触发: {time_val} ({repeat_tag})")
            trigger_lbl.setStyleSheet(f"font-size: 11.5px; font-weight: 500; color: {'#38bdf8' if d else '#0284c7'}; font-family: 'Microsoft YaHei UI'; background: transparent; border: none;")

            remain = r.get("remain_sec", 0)
            days = remain // 86400
            rem_sec = remain % 86400
            h = rem_sec // 3600
            m = (rem_sec % 3600) // 60
            s = rem_sec % 60
            if days > 0:
                remain_str = f"{days}天 {h:02d}:{m:02d}:{s:02d}"
            elif h > 0:
                remain_str = f"{h:02d}:{m:02d}:{s:02d}"
            else:
                remain_str = f"{m:02d}:{s:02d}"
            remain_lbl = QLabel(f"倒计时: {remain_str}")
            remain_lbl.setStyleSheet(f"font-size: 11px; color: {'#a1a1aa' if d else '#64748b'}; font-family: 'Microsoft YaHei UI'; background: transparent; border: none;")

            time_box.addWidget(trigger_lbl)
            time_box.addWidget(remain_lbl)
            c_lay.addLayout(time_box)

            # 操作按钮区：【⚡ 测试】+ 【✏️ 编辑】+ 【✕ 删除】
            btn_act_lay = QHBoxLayout()
            btn_act_lay.setSpacing(4)

            test_btn = QPushButton("⚡ 测试")
            test_btn.setFixedSize(54, 28)
            test_btn.setCursor(Qt.PointingHandCursor)
            test_btn.setToolTip("立即测试触发此任务（模拟时间到达，桌宠动画、提示音、AI执行与推送闭环）")
            test_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#312e81' if d else '#e0e7ff'}; color: {'#c7d2fe' if d else '#4338ca'};
                    border: 1px solid {'#4338ca' if d else '#c7d2fe'}; border-radius: 6px; font-size: 11px; font-weight: bold;
                }}
                QPushButton:hover {{
                    background: {'#4338ca' if d else '#c7d2fe'}; color: #ffffff;
                }}
            """)
            test_btn.clicked.connect(lambda ch, tid=r.get("id"): self._test_trigger_automation_task(tid))
            btn_act_lay.addWidget(test_btn)

            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(28, 28)
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setToolTip("编辑修改此任务")
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {'#a1a1aa' if d else '#64748b'};
                    border: 1px solid {'#3f3f46' if d else '#e2e8f0'}; border-radius: 6px; font-size: 12px;
                }}
                QPushButton:hover {{
                    background: {'#3f3f46' if d else '#e2e8f0'}; color: {'#ffffff' if d else '#0f172a'};
                }}
            """)
            edit_btn.clicked.connect(lambda ch, tid=r.get("id"): self._edit_automation_task(tid))
            btn_act_lay.addWidget(edit_btn)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(28, 28)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setToolTip("删除此任务")
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {'#a1a1aa' if d else '#64748b'};
                    border: none; border-radius: 6px; font-size: 12px; font-weight: bold;
                }}
                QPushButton:hover {{
                    background: #ef4444; color: #ffffff;
                }}
            """)
            del_btn.clicked.connect(lambda ch, tid=r.get("id"): self._delete_automation_task(tid))
            btn_act_lay.addWidget(del_btn)

            c_lay.addLayout(btn_act_lay)

            self.task_list_widget.addItem(item)
            self.task_list_widget.setItemWidget(item, card)

    def _delete_automation_task(self, task_id: int):
        try:
            from core.pet_scheduler import PetScheduler
            PetScheduler.get_instance().cancel_reminder(task_id)
            self._refresh_task_list()
            self._show_status("已删除自动化任务")
        except Exception as e:
            show_themed_warning(self, "删除失败", str(e), self._is_dark)

    def _rebuild_template_cards(self):
        if not hasattr(self, 'tpl_grid'):
            return
        for i in reversed(range(self.tpl_grid.count())):
            w = self.tpl_grid.itemAt(i).widget()
            if w: w.setParent(None)

        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        templates = [
            {"icon": "📑", "name": "每日 AI 新闻推送", "desc": "关注当前 AI 领域的重磅动态，精准 AI coding 与具身智能进展，筛选推送...", "cmd": "查全网热搜新闻与最新科技动态", "freq_mode": 0, "cycle": "每天", "time": "09:00"},
            {"icon": "🗣️", "name": "每日 5 个英语单词", "desc": "每天推荐 5 个高频实用英语单词，包含词义、音标、例句与记忆提示。", "cmd": "生成今日英语单词学习卡片", "freq_mode": 0, "cycle": "每天", "time": "08:30"},
            {"icon": "🌙", "name": "每日儿童睡前故事", "desc": "生成 3-5 分钟可读的温和睡前故事，情节完整附带寓意，符合儿童心理。", "cmd": "写一篇今晚的温馨儿童睡前故事", "freq_mode": 0, "cycle": "每天", "time": "21:00"},
            {"icon": "📊", "name": "每周工作周报", "desc": "每周五汇总仓库 PR 与 Issue 进展，输出关键变更与待关注事项。", "cmd": "生成本周工作总结与下周计划", "freq_mode": 0, "cycle": "每周", "time": "18:00"},
            {"icon": "🎬", "name": "经典电影推荐", "desc": "推荐一部高分经典电影，简要介绍剧情梗概、亮点与推荐理由，全程...", "cmd": "推荐一部高分经典电影并解析其艺术特色", "freq_mode": 0, "cycle": "每周", "time": "20:00"},
            {"icon": "📅", "name": "历史上的今天", "desc": "从科技、电影、音乐等领域挑选一件“今天发生过”的有趣事件，200-30...", "cmd": "查历史上的今天有哪些大事发生", "freq_mode": 0, "cycle": "每天", "time": "08:00"},
            {"icon": "💡", "name": "每日一个为什么", "desc": "每天挑出一个有趣问题，先提问再解答，通俗易懂，例句轻松，答案...", "cmd": "每日一个为什么趣味科普问答", "freq_mode": 0, "cycle": "每天", "time": "12:00"},
            {"icon": "☎️", "name": "父母联系提醒", "desc": "每周日 10:00 提醒你给家人打电话或发消息，简单问候近况。", "cmd": "起草一份给父母的温馨问候信息", "freq_mode": 0, "cycle": "每周", "time": "10:00"},
            {"icon": "💊", "name": "体检预约提醒", "desc": f"在 {tomorrow_str.replace('-', '/')} 08:00 提醒你确认体检时间、准备证件，并注意空腹...", "cmd": "生成体检前注意事项清单与准备材料", "freq_mode": 2, "date": tomorrow_str, "time": "08:00"},
            {"icon": "🎯", "name": "面试准备提醒", "desc": "工作日每 2 小时提醒你复习大模型面试内容，生成 3 个模拟题。", "cmd": "生成 3 道大模型高频面试真题", "freq_mode": 1, "interval": 2},
            {"icon": "🤝", "name": "会议前准备", "desc": "在会议开始前提醒你整理议题、目标、待确认问题和关键结论。", "cmd": "梳理高效会议准备清单", "freq_mode": 0, "cycle": "工作日", "time": "09:30"},
            {"icon": "🖼️", "name": "可爱萌宠手机壁纸", "desc": "随机从 7 种不同风格中挑选一种，为你生成一张 9:16 竖版高清壁纸方案...", "cmd": "设计一张治愈系萌宠壁纸方案", "freq_mode": 0, "cycle": "每天", "time": "10:00"},
        ]
        for idx, t_data in enumerate(templates):
            tcard = self._build_template_card(t_data)
            self.tpl_grid.addWidget(tcard, idx // 3, idx % 3)

    def _build_template_card(self, t_data: dict) -> QFrame:
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

        icon_lbl = QLabel(t_data["icon"])
        icon_lbl.setFont(QFont("Segoe UI Emoji", 18))
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignCenter)
        c_lay.addWidget(icon_lbl)

        v = QVBoxLayout(); v.setSpacing(2)
        n_lbl = QLabel(t_data["name"])
        n_lbl.setStyleSheet(f"font-size:12.5px;font-weight:bold;color:{title_fg};font-family:'Microsoft YaHei UI';")
        d_lbl = QLabel(t_data["desc"])
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
        exec_btn.clicked.connect(lambda c, td=t_data: self._execute_template(td["name"], td["cmd"]))
        c_lay.addWidget(exec_btn)

        # 点击卡片进入完整配置视图，同时自动反填该模板预设的频率模式与时间
        card.mousePressEvent = lambda e, td=t_data: self._open_add_auto_view_from_template(td)
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
                show_themed_warning(self, "错误", str(e), self._is_dark)

    def _execute_template(self, name: str, cmd: str):
        if show_themed_confirm(
            self, f"执行模板：{name}",
            f"确认立即执行此自动化任务？\n\n指令：{cmd}\n\n执行后将自动发送到 AI 对话。",
            self._is_dark
        ):
            self._log_auto_run(name, cmd, "success", "手动触发即时执行")
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
            st = entry.get("status", "success")
            status_icon = "✅" if st == "success" else ("❌" if st == "failed" else "⏳")
            res_txt = entry.get("result", "")
            full_line = f"{status_icon}  [{entry.get('time','')[:16]}]  {entry.get('name','')}  —  {res_txt}"
            # 列表行只展示前 200 字符（避免单行过长挤掉所有记录），完整内容挂到 tooltip
            display_line = (full_line[:200] + "  …") if len(full_line) > 200 else full_line
            item = QListWidgetItem("  " + display_line)
            item.setToolTip(full_line)
            item.setData(Qt.UserRole, full_line)
            self.log_list.addItem(item)
        if self.log_list.count() == 0:
            item = QListWidgetItem("  暂无运行记录")
            item.setForeground(QColor("#94a3b8"))
            self.log_list.addItem(item)

    def _clear_auto_log(self):
        if show_themed_confirm(self, "清空记录", "确认清空所有运行记录？", self._is_dark):
            save_auto_log([])
            self._refresh_auto_log()

    # ══════════════════════════════════════════════════════════
    #  设置与模型页 (真实 models_list 双向同步)
    # ══════════════════════════════════════════════════════════
    def _create_settings_page(self) -> QWidget:
        container = QWidget()
        page_lay = QVBoxLayout(container)
        page_lay.setContentsMargins(0, 0, 0, 0)
        page_lay.setSpacing(0)

        scroll = QScrollArea()
        self.settings_scroll = scroll
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollArea > QWidget > QWidget {{ background: transparent; }}
            QScrollBar:vertical {{ width: 6px; background: transparent; border: none; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {'#3f3f46' if self._is_dark else '#cbd5e1'}; border-radius: 3px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background: {'#52525b' if self._is_dark else '#94a3b8'}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        scroll.viewport().setStyleSheet("background: transparent;")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(28, 20, 28, 24)
        lay.setSpacing(16)

        # ── 1. 用户信息与大模型专属规则/红线卡片 ──
        self.user_card = QFrame()
        self.user_card.setObjectName("UserProfileCard")
        d_card = self._is_dark
        self.user_card.setStyleSheet(f"""
            QFrame#UserProfileCard {{
                background-color: {'#27272a' if d_card else '#ffffff'};
                border: 1px solid {'#3f3f46' if d_card else '#e2e8f0'};
                border-radius: 12px;
            }}
        """)
        uc_outer_lay = QVBoxLayout(self.user_card)
        uc_outer_lay.setContentsMargins(20, 18, 20, 18)
        uc_outer_lay.setSpacing(12)

        # 头部第一排：头像 + 昵称 + 记忆备注 + 操作按钮
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # 头像
        self.user_avatar_lbl = QLabel()
        self.user_avatar_lbl.setFixedSize(56, 56)
        self.user_avatar_lbl.setAlignment(Qt.AlignCenter)
        self.user_avatar_lbl.setStyleSheet(
            "background: #10b981; color: #ffffff; border-radius: 28px; "
            "font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif; "
            "font-weight: bold; font-size: 22px;"
        )
        self._refresh_user_avatar()
        top_row.addWidget(self.user_avatar_lbl)

        # 信息输入列
        info_v = QVBoxLayout()
        info_v.setSpacing(6)
        self.user_info_title = QLabel("用户信息与大模型记忆")
        self.user_info_title.setStyleSheet(
            f"color: {'#f4f4f5' if d_card else '#0f172a'}; "
            f"font-size: 14px; font-weight: 600; "
            f"font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif; "
            f"background: transparent;"
        )
        info_v.addWidget(self.user_info_title)

        edit_border = '#3f3f46' if d_card else '#cbd5e1'
        edit_bg = '#18181b' if d_card else '#ffffff'
        edit_fg = '#f4f4f5' if d_card else '#0f172a'

        # 昵称
        self.user_name_edit = QLineEdit(self.config.get("user_name", ""))
        self.user_name_edit.setPlaceholderText("你的昵称（让 AI 知道怎么称呼你）")
        self.user_name_edit.setFixedHeight(34)
        self.user_name_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {edit_bg};
                color: {edit_fg};
                border: 1px solid {edit_border};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            }}
            QLineEdit:focus {{ border: 1px solid #6366f1; }}
        """)
        info_v.addWidget(self.user_name_edit)

        # 记忆备注
        self.user_memo_edit = QLineEdit(self.config.get("user_memo", ""))
        self.user_memo_edit.setPlaceholderText("记忆备注（例：我喜欢玩无畏契约，日常用 Python 编写程序）")
        self.user_memo_edit.setFixedHeight(34)
        self.user_memo_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {edit_bg};
                color: {edit_fg};
                border: 1px solid {edit_border};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            }}
            QLineEdit:focus {{ border: 1px solid #6366f1; }}
        """)
        info_v.addWidget(self.user_memo_edit)
        top_row.addLayout(info_v, 1)

        # 按钮列
        btn_v = QVBoxLayout()
        btn_v.setSpacing(6)
        btn_v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # 保存按钮
        self.save_profile_btn = QPushButton()
        self.save_profile_btn.setText("  保存设置")
        self.save_profile_btn.setFixedHeight(34)
        self.save_profile_btn.setCursor(Qt.PointingHandCursor)
        self.save_profile_btn.setIcon(load_ui_icon("check", "#ffffff", 14))
        self.save_profile_btn.setIconSize(QSize(14, 14))
        self.save_profile_btn.setStyleSheet(f"""
            QPushButton {{
                background: #6366f1;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 0 18px;
                font-size: 12.5px;
                font-weight: 600;
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            }}
            QPushButton:hover {{ background: #4f46e5; }}
        """)
        self.save_profile_btn.clicked.connect(self._on_save_user_profile)
        btn_v.addWidget(self.save_profile_btn)

        # 上传头像按钮
        self.upload_btn = QPushButton()
        self.upload_btn.setText("  上传头像")
        self.upload_btn.setFixedHeight(34)
        self.upload_btn.setCursor(Qt.PointingHandCursor)
        self.upload_btn.setIcon(load_ui_icon("upload", "#a1a1aa" if d_card else "#64748b", 14))
        self.upload_btn.setIconSize(QSize(14, 14))
        self.upload_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {'#18181b' if d_card else '#f1f5f9'};
                color: {'#f4f4f5' if d_card else '#334155'};
                border: 1px solid {edit_border};
                border-radius: 8px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 500;
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            }}
            QPushButton:hover {{ background-color: {'#27272a' if d_card else '#e2e8f0'}; border: 1px solid #6366f1; }}
        """)
        self.upload_btn.clicked.connect(self._on_upload_avatar)
        btn_v.addWidget(self.upload_btn)

        top_row.addLayout(btn_v)
        uc_outer_lay.addLayout(top_row)

        # 第二排：大模型规则与强制红线设定
        rules_head_row = QHBoxLayout()
        self.rules_lbl = QLabel("🛡️ 大模型专属规则与行为红线（最高约束力，永久注入大模型记忆）")
        self.rules_lbl.setStyleSheet(
            f"color: {'#a1a1aa' if d_card else '#64748b'}; "
            f"font-size: 12px; font-weight: 600; "
            f"font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif; "
            f"background: transparent;"
        )
        rules_head_row.addWidget(self.rules_lbl)
        rules_head_row.addStretch()
        uc_outer_lay.addLayout(rules_head_row)

        self.user_rules_edit = QTextEdit()
        self.user_rules_edit.setPlainText(self.config.get("user_rules") or self.config.get("custom_rules") or "")
        self.user_rules_edit.setPlaceholderText(
            "输入大模型在所有对话与任务中必须无条件严格遵守的规则与红线，例如：\n"
            "1. 回复直接切入核心重点，拒绝无意义的客套与冗余套话；\n"
            "2. 生成或修改 Python/前端代码时，必须附带详细、规范的中文注释；\n"
            "3. 严禁擅自改动未被用户要求的核心架构或已验证的运行逻辑；\n"
            "4. 遇到存在歧义的业务需求时，必须先主动向用户提问确认再继续执行。"
        )
        self.user_rules_edit.setFixedHeight(95)
        self.user_rules_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {edit_bg};
                color: {edit_fg};
                border: 1px solid {edit_border};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12.5px;
                line-height: 1.45;
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            }}
            QTextEdit:focus {{ border: 1px solid #6366f1; }}
        """)
        uc_outer_lay.addWidget(self.user_rules_edit)

        lay.addWidget(self.user_card)

        # ── 2. 已配置模型区域 ──
        lay.addSpacing(6)
        top_h = QHBoxLayout()
        self.settings_head = QLabel("已配置模型")
        self.settings_head.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
        self.settings_head.setStyleSheet(
            f"color: {'#ffffff' if self._is_dark else '#0f172a'}; "
            f"font-family: 'Microsoft YaHei UI'; background: transparent;"
        )
        top_h.addWidget(self.settings_head)
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

        self._model_list_content = QWidget()
        self._model_list_content.setStyleSheet("background: transparent;")
        self._model_list_vlay = QVBoxLayout(self._model_list_content)
        self._model_list_vlay.setContentsMargins(0, 0, 0, 0)
        self._model_list_vlay.setSpacing(8)
        lay.addWidget(self._model_list_content)
        self._refresh_model_cards()

        # ── 3. 快速配置当前模型区域 (空间开阔，独立卡片) ──
        lay.addSpacing(14)

        self.edit_head = QLabel("快速配置当前模型")
        self.edit_head.setFont(QFont("Microsoft YaHei UI", 13, QFont.Bold))
        self.edit_head.setStyleSheet(f"color:{'#ffffff' if self._is_dark else '#0f172a'}; background: transparent;")
        lay.addWidget(self.edit_head)

        self.form_card = QFrame()
        self.form_card.setObjectName("QuickConfigCard")
        self.form_card.setStyleSheet(f"""
            QFrame#QuickConfigCard {{
                background-color: {'#27272a' if d_card else '#ffffff'};
                border: 1px solid {'#3f3f46' if d_card else '#e2e8f0'};
                border-radius: 12px;
            }}
        """)
        f_lay = QFormLayout(self.form_card)
        f_lay.setSpacing(12)
        f_lay.setContentsMargins(20, 18, 20, 18)

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
        self.test_btn = QPushButton("  测试连接")
        self.test_btn.setFixedHeight(36)
        self.test_btn.setIcon(load_ui_icon("search", "#a1a1aa", 14))
        self.test_btn.setIconSize(QSize(14, 14))
        self.test_btn.clicked.connect(self._test_api_connection)
        act_row.addWidget(self.test_btn)

        self.test_result_lbl = QLabel("")
        self.test_result_lbl.setStyleSheet(f"color: {'#a1a1aa' if self._is_dark else '#64748b'}; font-size: 12px; font-family: 'Microsoft YaHei UI';")
        act_row.addWidget(self.test_result_lbl, 1)

        self.save_curr_btn = QPushButton("  保存为当前模型")
        self.save_curr_btn.setFixedHeight(36)
        self.save_curr_btn.setIcon(load_ui_icon("check", "#ffffff", 14))
        self.save_curr_btn.setIconSize(QSize(14, 14))
        self.save_curr_btn.clicked.connect(self._save_settings)
        act_row.addWidget(self.save_curr_btn)
        lay.addLayout(act_row)
        lay.addStretch(1)

        scroll.setWidget(content)
        page_lay.addWidget(scroll)

        self._load_active_model_into_form()
        return container

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
            bg = "#1e1e1e" if d else "#f8fafc"   # 与页面底色轻微区分，替代 1px 描边
            active_bg = "#252548" if d else "#eef2ff"  # active 用淡蓝底色作为强调
            active_bar = "#6366f1"  # active 卡片左侧 3px 强调条
            card.setObjectName("ModelCard")
            card.setProperty("active", "1" if is_active else "0")
            card.setStyleSheet(f"""
                QFrame#ModelCard {{
                    background-color: {active_bg if is_active else bg};
                    border: none;
                    border-radius: 10px;
                }}
                QFrame#ModelCard[active="1"] {{
                    border-left: 3px solid {active_bar};
                }}
            """)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(14, 10, 14, 10)
            c_lay.setSpacing(10)

            # 模型图标：彩色圆角方块 + 提供商首字母（与连接器卡片视觉语言统一，去彩色 emoji）
            _prov_char = "O" if provider == "ollama" else "C"
            _prov_color = "#10b981" if provider == "ollama" else "#6366f1"
            icon = QLabel(_prov_char)
            icon.setFixedSize(28, 28)
            icon.setAlignment(Qt.AlignCenter)
            icon.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
            icon.setStyleSheet(f"background: {_prov_color}; color: #ffffff; border-radius: 7px;")
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

            # 更多操作（把「编辑 / 删除」收敛为一个 ⋯ 菜单，减少右侧按钮堆叠与线条）
            more_btn = QPushButton("⋯")
            more_btn.setFixedSize(28, 28)
            more_btn.setCursor(Qt.PointingHandCursor)
            more_btn.setToolTip("更多操作")
            more_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {'#a1a1aa' if d else '#64748b'};
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background: {'#27272a' if d else '#f1f5f9'};
                    color: {'#f4f4f5' if d else '#0f172a'};
                }}
            """)
            more_btn.clicked.connect(lambda c, mod=m, btn=more_btn: self._show_model_more_menu(mod, btn))
            c_lay.addWidget(more_btn)

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
            show_themed_warning(self, "无法删除", "当前正在使用的模型无法删除，请先切换到其他模型。", self._is_dark)
            return
        if show_themed_confirm(self, "删除模型", f"确认删除模型「{name}」？", self._is_dark):
            models = self.config.get("models_list", [])
            self.config["models_list"] = [m for m in models if m.get("id") != mid]
            if self.save_config_fn:
                self.save_config_fn(self.config)
            self._refresh_model_cards()
            self._show_status(f"已删除模型：{name}")

    def _show_model_more_menu(self, model: dict, anchor_btn: QPushButton):
        d = self._is_dark
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {'#1e1e20' if d else '#ffffff'};
                color: {'#f4f4f5' if d else '#0f172a'};
                border: 1px solid {'#2e2e32' if d else '#e2e8f0'};
                border-radius: 10px;
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
        act_edit = menu.addAction("✎ 编辑")
        act_del = menu.addAction("🗑 删除")
        act = menu.exec_(anchor_btn.mapToGlobal(QPoint(0, anchor_btn.height())))
        if act == act_edit:
            self._edit_model(model)
        elif act == act_del:
            self._delete_model(model)

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

    def _refresh_user_avatar(self):
        """刷新设置页用户头像：有上传图片用图片，否则用首字母 U 绿色方块"""
        d = self._is_dark
        avatar_path = self.config.get("user_avatar_path")
        if avatar_path and Path(avatar_path).exists():
            try:
                pix = QPixmap(avatar_path).scaled(108, 108, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                rounded = QPixmap(54, 54)
                rounded.fill(QColor(0, 0, 0, 0))
                p = QPainter(rounded)
                p.setRenderHint(QPainter.Antialiasing, True)
                path = QPainterPath()
                path.addEllipse(0, 0, 54, 54)
                p.setClipPath(path)
                p.drawPixmap((54 - pix.width()) // 2, (54 - pix.height()) // 2, pix)
                p.end()
                self.user_avatar_lbl.setPixmap(rounded)
                return
            except Exception:
                pass
        # 默认首字母
        name = (self.config.get("user_name") or "U").strip()
        initial = name[0].upper() if name else "U"
        self.user_avatar_lbl.setText(initial)
        self.user_avatar_lbl.setFont(QFont("Microsoft YaHei UI", 18, QFont.Bold))
        self.user_avatar_lbl.setStyleSheet("background: #10b981; color: #ffffff; border-radius: 27px; font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif; font-weight: bold;")

    def _on_upload_avatar(self):
        """上传头像：选图片后保存到 data/user_avatar.png，更新 config，刷新所有消息头像"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择头像图片", str(Path.home()),
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        try:
            # 复制到 data/user_avatar.png
            from shutil import copyfile
            target = ROOT_DIR / "data" / "user_avatar.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            copyfile(path, target)
            self.config["user_avatar_path"] = str(target)
            if self.save_config_fn:
                self.save_config_fn(self.config)
            self._refresh_user_avatar()
            self._show_status("✅ 头像已上传，下次对话生效")
        except Exception as e:
            self._show_status(f"上传失败：{e}")

    def _on_save_user_profile(self):
        """保存用户昵称 + 记忆备注 + 规则红线到 config 并实时注入 AI 引擎记忆"""
        name = self.user_name_edit.text().strip()
        memo = self.user_memo_edit.text().strip()
        rules = self.user_rules_edit.toPlainText().strip() if hasattr(self, "user_rules_edit") else ""
        self.config["user_name"] = name
        self.config["user_memo"] = memo
        self.config["user_rules"] = rules
        if self.save_config_fn:
            self.save_config_fn(self.config)
        self._refresh_user_avatar()
        if self.ai_engine:
            self.ai_engine.config["user_name"] = name
            self.ai_engine.config["user_memo"] = memo
            self.ai_engine.config["user_rules"] = rules
            self._inject_user_profile_into_prompt()

        # 按钮动态反馈
        if hasattr(self, "save_profile_btn"):
            self.save_profile_btn.setText("✓ 保存成功")
            self.save_profile_btn.setStyleSheet("""
                QPushButton {
                    background: #059669;
                    color: #ffffff;
                    border: none;
                    border-radius: 8px;
                    padding: 0 18px;
                    font-size: 12.5px;
                    font-weight: 600;
                    font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
                }
            """)
            QTimer.singleShot(2000, self._reset_save_profile_btn)

        self._show_status("✅ 用户设定与规则红线已保存，大模型已实时同步记住")
        show_themed_info(
            self,
            "保存成功",
            f"用户信息、永久记忆与规则红线已成功保存入库！\n\n• 用户昵称：{name or '（未设置）'}\n• 记忆档案：{memo or '（未设置）'}\n• 规则与红线：{rules or '（未设置）'}\n\n✨ AI 智能体已在所有对话、技能与任务流中永久生效并严格执行你的规则约束。",
            self._is_dark
        )

    def _reset_save_profile_btn(self):
        if hasattr(self, "save_profile_btn"):
            self.save_profile_btn.setText("  保存设置")
            self.save_profile_btn.setIcon(load_ui_icon("check", "#ffffff", 14))
            self.save_profile_btn.setIconSize(QSize(14, 14))
            self.save_profile_btn.setStyleSheet("""
                QPushButton {
                    background: #6366f1;
                    color: #ffffff;
                    border: none;
                    border-radius: 8px;
                    padding: 0 18px;
                    font-size: 12.5px;
                    font-weight: 600;
                    font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
                }
                QPushButton:hover { background: #4f46e5; }
            """)

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
        ws_name = (ws.get("name") or "").strip()
        ws_path = (ws.get("path") or "").strip()
        self.current_workspace_name = ws_name
        self.current_workspace_path = ws_path
        self.config["current_workspace_name"] = ws_name
        self.config["workspace_dir"] = ws_path
        if self.save_config_fn:
            self.save_config_fn(self.config)

        try:
            from core.security_guard import SecurityGuard
            if ws_path:
                SecurityGuard.get_instance().set_workspace_root(ws_path)
        except Exception:
            pass

        txt = f"📁 {ws_name} ∨" if ws_name else "📁 选择工作空间 ∨"
        if hasattr(self, 'ws_pill'):
            self.ws_pill.setText(txt)
        if hasattr(self, 'hero_ws_pill'):
            self.hero_ws_pill.setText(txt)
        self._refresh_sidebar_workspaces()
        if ws_name:
            self._show_status(f"📁 已切换工作空间：{ws_name}")
        else:
            self._show_status("已切换为：不关联工作空间")

    def _create_new_workspace_dialog(self):
        """新建工作空间：精致的双主题对话框（含输入框），替代 Qt 默认丑样式"""
        d = self._is_dark
        bg = "#1e1e1e" if d else "#ffffff"
        fg = "#f4f4f5" if d else "#0f172a"
        sub_fg = "#a1a1aa" if d else "#475569"
        border = "#2e2e2e" if d else "#e2e8f0"
        btn_bg = "#27272a" if d else "#f1f5f9"

        dlg = QDialog(self)
        dlg.setWindowTitle("新建工作空间")
        dlg.setMinimumWidth(380)
        dlg.setModal(True)
        dlg.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QLabel#TitleLbl {{
                color: {fg};
                font-size: 15px;
                font-weight: bold;
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
                background: transparent;
            }}
            QLabel#BodyLbl {{
                color: {sub_fg};
                font-size: 13px;
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
                background: transparent;
            }}
            QLineEdit#NameEdit {{
                background: {'#18181b' if d else '#f8fafc'};
                color: {fg};
                border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
            }}
            QLineEdit#NameEdit:focus {{ border: 1px solid #6366f1; }}
            QPushButton {{
                background: {btn_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 0 18px;
                font-size: 13px;
                font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
                min-height: 34px;
                min-width: 88px;
            }}
            QPushButton:hover {{ background: {'#3f3f46' if d else '#e2e8f0'}; }}
            QPushButton#PrimaryBtn {{
                background: #6366f1;
                color: #ffffff;
                border: none;
                font-weight: 600;
            }}
            QPushButton#PrimaryBtn:hover {{ background: #4f46e5; }}
        """)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(12)

        title_lbl = QLabel("新建工作空间")
        title_lbl.setObjectName("TitleLbl")
        lay.addWidget(title_lbl)

        body_lbl = QLabel("工作空间名称：")
        body_lbl.setObjectName("BodyLbl")
        lay.addWidget(body_lbl)

        name_edit = QLineEdit()
        name_edit.setObjectName("NameEdit")
        name_edit.setPlaceholderText("例如：我的新项目")
        name_edit.setFixedHeight(38)
        lay.addWidget(name_edit)

        lay.addSpacing(6)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)
        primary_btn = QPushButton("创建")
        primary_btn.setObjectName("PrimaryBtn")
        primary_btn.setCursor(Qt.PointingHandCursor)
        primary_btn.setDefault(True)
        primary_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(primary_btn)
        lay.addLayout(btn_row)

        name_edit.setFocus()
        if dlg.exec() == QDialog.Accepted:
            clean_name = name_edit.text().strip()
            if clean_name:
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

    def _toggle_sidebar_collapse(self):
        is_visible = self.sidebar.isVisible()
        self.sidebar.setVisible(not is_visible)
        if hasattr(self, 'expand_sb_btn'):
            in_work_mode = (self.mode_stack.currentIndex() == 0) if hasattr(self, 'mode_stack') else True
            self.expand_sb_btn.setVisible(in_work_mode and is_visible)

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
        # 屏幕边界检测：右对齐可能溢出 → 改左对齐
        btn_global = sender.mapToGlobal(QPoint(0, 0))
        desired_pos = sender.mapToGlobal(QPoint(0, sender.height() + 6))
        screen = QApplication.screenAt(btn_global)
        if screen is None:
            screen = QApplication.primaryScreen()
        avail = screen.availableGeometry()
        popup_w = popup.width()
        popup_h = popup.height()
        # X：如果右对齐溢出，改左对齐
        if desired_pos.x() + popup_w > avail.right():
            desired_pos.setX(btn_global.x() + sender.width() - popup_w)
            if desired_pos.x() < avail.left():
                desired_pos.setX(avail.left() + 4)
        # Y：如果下方溢出，改到按钮上方
        if desired_pos.y() + popup_h > avail.bottom():
            desired_pos.setY(btn_global.y() - popup_h - 6)
            if desired_pos.y() < avail.top():
                desired_pos.setY(avail.top() + 4)
        popup.move(desired_pos)
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
        """点击 + 新建任务：重置到 Hero 模式，不预先在任务栏增加空任务，待发送首条消息后再建任务"""
        self.current_workspace_name = ""
        self.current_workspace_path = ""
        ws_pill_txt = "📁 选择工作空间 ∨"
        if hasattr(self, 'ws_pill'):
            self.ws_pill.setText(ws_pill_txt)
        if hasattr(self, 'hero_ws_pill'):
            self.hero_ws_pill.setText(ws_pill_txt)

        if self.memory:
            self.memory.cleanup_empty_sessions()

        self._current_session_id = None
        self._clear_chat_blocks()
        self.chat_title_lbl.setText("新任务会话")
        self.setWindowTitle("NovaDesk v4.0")
        self._refresh_history_list()
        self._refresh_sidebar_workspaces()
        self._enter_hero_mode()
        self._update_send_button_state()
        self._switch_nav(0)

    def _highlight_active_session(self, session_id: int):
        if not hasattr(self, 'task_items_lay'):
            return
        for i in range(self.task_items_lay.count()):
            item = self.task_items_lay.itemAt(i)
            w = item.widget() if item else None
            if isinstance(w, SidebarTaskItemWidget):
                w.set_active(w.session_id == session_id)

    def _load_session(self, session_id: int):
        if self._current_session_id == session_id and getattr(self, '_session_loaded_once', False):
            return
        self._session_loaded_once = True
        self._current_session_id = session_id

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

        # 核心流畅优化：仅高亮当前选中项，避免对侧边栏列表进行高代价的全量重建
        self._highlight_active_session(session_id)

        if not self.memory:
            self._clear_chat_blocks()
            self._enter_hero_mode()
            self._update_send_button_state()
            return

        try:
            messages = self.memory.get_session_messages(session_id)
            sessions = self.memory.get_all_sessions()
            curr = next((s for s in sessions if s["id"] == session_id), None)
            title = curr.get("title", "对话任务") if curr else "对话任务"
            self.chat_title_lbl.setText(title)
            self.setWindowTitle(f"{title} - NovaDesk")

            # 3. 无论是否有历史消息，直接进入对话态对话流界面
            self._enter_active_chat_mode()

            # 核心性能优化：冻结滚动区域更新，批量清空与插入，完成后一次性解冻并滚动，丝滑零卡顿
            if hasattr(self, 'chat_scroll'):
                self.chat_scroll.setUpdatesEnabled(False)
            try:
                self._clear_chat_blocks()
                if messages:
                    history = []
                    for m in messages:
                        sender = "user" if m.get("role") in ["user", "human"] else "ai"
                        raw_ts = str(m.get("timestamp", ""))
                        fmt_ts = raw_ts[11:16] if len(raw_ts) >= 16 else datetime.now().strftime("%H:%M")
                        self._add_message_block(sender, m.get("content", ""), timestamp=fmt_ts, auto_scroll=False)
                        history.append({"role": m.get("role"), "content": m.get("content")})
                    if self.ai_engine:
                        self.ai_engine.conversation_history = history
                        if hasattr(self.ai_engine, 'session_histories'):
                            self.ai_engine.session_histories[str(session_id)] = list(history)
                elif title and title != "新任务会话":
                    # 针对早期未持久化子消息的老存量会话，自动恢复初始问答与就绪状态
                    self._add_message_block("user", title, auto_scroll=False)
                    self._add_message_block("ai", f"已载入任务「{title}」的历史上下文。您可以直接在下方输入框继续向我提问或执行操作。", auto_scroll=False)
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

                # 4. 如果该会话正在后台并发流式生成中，实时接续渲染正在打字的 AI 消息块
                if session_id in self._active_streams:
                    stream_info = self._active_streams[session_id]
                    curr_text = stream_info.get("full_text", "") or "⏳ 正在思考..."
                    self._current_ai_block = self._add_message_block("ai", curr_text, auto_scroll=False)
                else:
                    self._current_ai_block = None
            finally:
                if hasattr(self, 'chat_scroll'):
                    self.chat_scroll.setUpdatesEnabled(True)

            self._scroll_to_bottom()

        except Exception as e:
            print(f"[SessionLoad Error] {e}")
            self._enter_active_chat_mode()

        self._update_send_button_state()
        QTimer.singleShot(60, self._scroll_to_bottom)

    def _on_session_item_clicked(self, item):
        if not item: return
        sid = item.data(Qt.UserRole)
        if sid:
            self._load_session(sid)
            self._switch_nav(0)

    def _clear_layout(self, lay):
        """递归且彻底清理布局及所有子部件，解除父子关系并立即隐藏，杜绝孤儿浮动部件"""
        if not lay:
            return
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.hide()
                w.deleteLater()
            sub = item.layout()
            if sub:
                self._clear_layout(sub)

    def _refresh_history_list(self):
        if not hasattr(self, 'task_items_lay'):
            return
        self._clear_layout(self.task_items_lay)

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
                pin_lbl = QLabel("✦ 置顶任务")
                pin_lbl.setStyleSheet(f"color: {'#818cf8' if self._is_dark else '#6366f1'}; font-size: 11px; font-weight: bold; padding: 2px 8px; font-family: 'Microsoft YaHei UI';")
                self.task_items_lay.addWidget(pin_lbl)

                for s in pinned_list:
                    self._add_session_widget(s, is_pinned=True)

                if display_normal:
                    div_lbl = QLabel("── 常规任务 ──")
                    div_lbl.setAlignment(Qt.AlignCenter)
                    div_lbl.setStyleSheet(f"color: {'#71717a' if self._is_dark else '#94a3b8'}; font-size: 10px; font-weight: bold; padding: 2px 0; font-family: 'Microsoft YaHei UI';")
                    self.task_items_lay.addWidget(div_lbl)

            # 2. 渲染常规会话项
            for s in display_normal:
                self._add_session_widget(s, is_pinned=False)

            d = self._is_dark
            # 同步顶栏固定切换按钮状态 (永远锚定在标题栏右侧，零跳动)
            if hasattr(self, 'task_header_toggle_btn'):
                if self._has_more_sessions:
                    remain_cnt = len(normal_list) - limit
                    if show_all:
                        self.task_header_toggle_btn.setText("收起 ∧")
                        self.task_header_toggle_btn.setToolTip("收起多余历史任务")
                    else:
                        self.task_header_toggle_btn.setText(f"+{remain_cnt} 更多 ∨")
                        self.task_header_toggle_btn.setToolTip(f"展开其余 {remain_cnt} 个任务")
                    self.task_header_toggle_btn.show()
                else:
                    self.task_header_toggle_btn.hide()

            # 3. 将「查看更多 / 收起」作为最后一项直接加入列表中（居中对称，严防多层容器带来的右偏遮挡与残留悬浮）
            if self._has_more_sessions:
                remain_cnt = len(normal_list) - limit
                btn_text = "收起历史任务 ∧" if show_all else f"查看更多 ({remain_cnt} 个任务) ∨"

                self.see_more_btn = QPushButton(btn_text)
                self.see_more_btn.setObjectName("SeeMoreTasksBtn")
                self.see_more_btn.setFixedHeight(30)
                self.see_more_btn.setCursor(Qt.PointingHandCursor)
                self.see_more_btn.setStyleSheet(f"""
                    QPushButton#SeeMoreTasksBtn {{
                        background-color: transparent;
                        color: {'#a1a1aa' if d else '#64748b'};
                        border: 1px dashed {'#3f3f46' if d else '#cbd5e1'};
                        border-radius: 6px;
                        text-align: center;
                        padding: 0 8px;
                        margin: 4px 6px 8px 6px;
                        font-size: 11.5px;
                        font-family: 'PingFang SC', 'Microsoft YaHei UI', -apple-system, sans-serif;
                        font-weight: 500;
                    }}
                    QPushButton#SeeMoreTasksBtn:hover {{
                        background-color: {'#27272a' if d else '#f1f5f9'};
                        color: {'#ffffff' if d else '#0f172a'};
                        border: 1px solid {'#6366f1' if d else '#4f46e5'};
                    }}
                """)
                self.see_more_btn.clicked.connect(self._toggle_show_all_sessions)
                self.task_items_lay.addWidget(self.see_more_btn)

        except Exception as e:
            print(f"[SessionList Error] {e}")

    def _add_session_widget(self, s: dict, is_pinned: bool):
        sid = s.get("id")
        title = str(s.get("title", "未命名")).strip()
        rel_t = format_relative_time(s.get("created_at", ""))
        is_active = (sid == self._current_session_id)

        widget = SidebarTaskItemWidget(
            session_id=sid,
            title=title,
            time_str=rel_t,
            is_pinned=is_pinned,
            is_active=is_active,
            is_dark=self._is_dark,
            is_generating=(sid in self._active_streams),
            parent=self.task_items_container
        )

        widget.clicked.connect(self._load_session)
        widget.rename_requested.connect(self._rename_session)
        widget.delete_requested.connect(self._delete_session_by_id)
        widget.export_requested.connect(self._export_session_markdown)
        widget.pin_toggled.connect(self._toggle_pin_session)
        widget.archive_requested.connect(self._archive_session)
        widget.save_to_ws_requested.connect(self._save_session_to_workspace)
        widget.batch_requested.connect(self._open_batch_dialog)

        self.task_items_lay.addWidget(widget)

    def _open_batch_dialog(self):
        if not self.memory: return
        sessions = self.memory.get_all_sessions()
        dlg = BatchSessionDialog(self, is_dark=self._is_dark, sessions=sessions, memory=self.memory)
        dlg.exec_()
        self._refresh_history_list()
        self._refresh_sidebar_workspaces()
        sessions_after = self.memory.get_all_sessions()
        if sessions_after:
            remaining_sids = set(s["id"] for s in sessions_after)
            pinned = self.config.get("pinned_sessions", [])
            self.config["pinned_sessions"] = [sid for sid in pinned if sid in remaining_sids]
            archived = self.config.get("archived_sessions", [])
            self.config["archived_sessions"] = [sid for sid in archived if sid in remaining_sids]
            if self.save_config_fn:
                self.save_config_fn(self.config)
            if self._current_session_id not in remaining_sids:
                self._load_session(sessions_after[0]["id"])
        else:
            self.config["pinned_sessions"] = []
            self.config["archived_sessions"] = []
            if self.save_config_fn:
                self.save_config_fn(self.config)
            self._create_new_session_action()

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
            show_themed_info(self, "提示", "当前会话暂无消息。", self._is_dark)
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
            show_themed_warning(self, "保存失败", str(e), self._is_dark)

    def _toggle_session_list(self):
        self._session_collapsed = not getattr(self, '_session_collapsed', False)
        if hasattr(self, 'task_items_container'):
            self.task_items_container.setVisible(not self._session_collapsed)
        if self._session_collapsed:
            self.task_head.setText(self.task_head.text().replace("∨", "∧"))
        else:
            self.task_head.setText(self.task_head.text().replace("∧", "∨"))

    def _toggle_show_all_sessions(self):
        self._show_all_sessions = not getattr(self, '_show_all_sessions', False)
        # 记录切换前的滚动条位置，防止列表重新渲染造成视口疯狂跳动
        sb = self.sidebar_scroll.verticalScrollBar() if hasattr(self, 'sidebar_scroll') else None
        prev_val = sb.value() if sb else 0
        self._refresh_history_list()
        if sb:
            if not self._show_all_sessions:
                # 收起时平滑回到顶部，确保任务标题与空间模块始终尽收眼底
                sb.setValue(min(prev_val, 40))
            else:
                # 展开时保持视口稳定
                sb.setValue(prev_val)

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
            show_themed_info(self, "提示", "当前会话暂无消息。", self._is_dark); return
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
            show_themed_info(self, "导出成功", f"已导出至桌面：{path.name}", self._is_dark)
        except Exception as e:
            show_themed_warning(self, "导出失败", str(e), self._is_dark)

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
        self._ws_collapsed = not getattr(self, '_ws_collapsed', False)
        if hasattr(self, 'ws_items_container'):
            self.ws_items_container.setVisible(not self._ws_collapsed)
        if self._ws_collapsed:
            self.ws_head.setText(self.ws_head.text().replace("∨", "∧"))
        else:
            self.ws_head.setText(self.ws_head.text().replace("∧", "∨"))

    def _refresh_sidebar_workspaces(self):
        if not hasattr(self, 'ws_items_lay'):
            return
        self._clear_layout(self.ws_items_lay)

        arr = "∧" if getattr(self, '_ws_collapsed', False) else "∨"
        self.ws_head.setText(f"空间 ({len(self.workspaces)}) {arr}")

        if not self.workspaces:
            empty_ws_lbl = QLabel("        暂无工作空间")
            empty_ws_lbl.setStyleSheet(f"color: {'#71717a' if self._is_dark else '#94a3b8'}; font-size: 11px; padding: 4px 0; font-family: 'Microsoft YaHei UI';")
            self.ws_items_lay.addWidget(empty_ws_lbl)
            return

        all_sessions = self.memory.get_all_sessions() if self.memory else []

        for ws in self.workspaces:
            ws_name = ws.get("name", "未命名空间")
            ws_path = ws.get("path", str(ROOT_DIR))
            is_active = (ws_name == self.current_workspace_name)
            is_collapsed = ws.get("collapsed", False)

            # 1. 渲染工作空间头部项
            header_widget = SidebarWorkspaceHeaderWidget(
                name=ws_name,
                path=ws_path,
                is_active=is_active,
                is_collapsed=is_collapsed,
                is_dark=self._is_dark,
                parent=self.ws_items_container
            )
            header_widget.clicked.connect(self._on_ws_header_clicked)
            header_widget.add_task_clicked.connect(self._create_new_session_in_workspace)
            header_widget.open_folder_requested.connect(self._open_workspace_folder)
            header_widget.remove_requested.connect(self._remove_workspace)
            header_widget.batch_requested.connect(self._open_batch_workspace_dialog)

            self.ws_items_lay.addWidget(header_widget)

            # 2. 如果展开，渲染下属任务列表
            if not is_collapsed:
                ws_sessions = [s for s in all_sessions if s.get("workspace_name") == ws_name]
                if not ws_sessions:
                    empty_lbl = QLabel("        暂无任务")
                    empty_lbl.setStyleSheet(f"color: {'#71717a' if self._is_dark else '#94a3b8'}; font-size: 11px; padding: 3px 0; font-family: 'Microsoft YaHei UI';")
                    self.ws_items_lay.addWidget(empty_lbl)
                else:
                    for s in ws_sessions[:8]:
                        sid = s.get("id")
                        title = str(s.get("title", "未命名")).strip()
                        rel_t = format_relative_time(s.get("created_at", ""))
                        is_curr = (sid == self._current_session_id)

                        task_widget = SidebarTaskItemWidget(
                            session_id=sid,
                            title=title,
                            time_str=rel_t,
                            is_pinned=sid in set(self.config.get("pinned_sessions", [])),
                            is_active=is_curr,
                            is_dark=self._is_dark,
                            is_sub_item=True,
                            is_generating=(sid in self._active_streams),
                            parent=self.ws_items_container
                        )
                        task_widget.clicked.connect(self._load_session)
                        task_widget.rename_requested.connect(self._rename_session)
                        task_widget.delete_requested.connect(self._delete_session_by_id)
                        task_widget.export_requested.connect(self._export_session_markdown)
                        task_widget.pin_toggled.connect(self._toggle_pin_session)
                        task_widget.archive_requested.connect(self._archive_session)

                        self.ws_items_lay.addWidget(task_widget)

    def _on_ws_header_clicked(self, ws_name: str, ws_path: str):
        for ws in self.workspaces:
            if ws.get("name") == ws_name:
                ws["collapsed"] = not ws.get("collapsed", False)
                break
        self._switch_to_workspace(ws_name, ws_path)

    def _switch_to_workspace(self, ws_name: str, ws_path: str):
        try:
            os.makedirs(ws_path, exist_ok=True)
        except Exception:
            pass
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
        # 确保该空间展开，以便用户直观看到新建任务
        for ws in self.workspaces:
            if ws.get("name") == ws_name:
                ws["collapsed"] = False
                break
        self._switch_to_workspace(ws_name, ws_path)
        if self.memory:
            self.memory.cleanup_empty_sessions()
        self._current_session_id = None
        self._clear_chat_blocks()
        self.chat_title_lbl.setText("新任务会话")
        self._refresh_history_list()
        self._refresh_sidebar_workspaces()
        self._enter_hero_mode()
        self._update_send_button_state()
        self._switch_nav(0)
        if hasattr(self, 'hero_input_edit'):
            self.hero_input_edit.setFocus()
        self._show_status(f"✨ 已在工作空间「{ws_name}」开启新任务")

    def _open_workspace_folder(self, ws_path: str):
        try:
            p = Path(ws_path)
            p.mkdir(parents=True, exist_ok=True)
            os.startfile(str(p))
            self._show_status(f"📁 已打开工作空间目录：{p.name}")
        except Exception as e:
            show_themed_warning(self, "打开失败", f"无法打开文件夹：{e}", self._is_dark)

    def _remove_workspace(self, ws_name: str):
        if show_themed_confirm(self, "移除工作空间", f"确认从列表中移除工作空间「{ws_name}」？\n（该空间下的所有关联任务将同时被删除，物理文件夹保留）", self._is_dark):
            # 1. 从 SQLite 数据库中连带删除属于该工作空间的所有任务会话及其全部消息
            deleted_sids = []
            if self.memory:
                deleted_sids = self.memory.delete_sessions_by_workspace(ws_name)

            # 2. 清理 AI 引擎中的多会话隔离历史、排队消息与活跃流
            if hasattr(self, 'ai_engine') and self.ai_engine:
                for sid in deleted_sids:
                    self.ai_engine.session_histories.pop(str(sid), None)
            for sid in deleted_sids:
                self._session_message_queues.pop(sid, None)
                self._active_streams.pop(sid, None)

            # 3. 从工作空间列表中移除，并清理可能包含的置顶与归档会话配置
            if deleted_sids:
                pinned = self.config.get("pinned_sessions", [])
                self.config["pinned_sessions"] = [sid for sid in pinned if sid not in deleted_sids]
                archived = self.config.get("archived_sessions", [])
                self.config["archived_sessions"] = [sid for sid in archived if sid not in deleted_sids]

            self.workspaces = [w for w in self.workspaces if w.get("name") != ws_name]
            self.config["workspaces"] = self.workspaces
            if self.current_workspace_name == ws_name or not self.workspaces:
                if self.workspaces:
                    self.current_workspace_name = self.workspaces[0].get("name", "")
                    self.current_workspace_path = self.workspaces[0].get("path", "")
                    txt = f"📁 {self.current_workspace_name} ∨"
                else:
                    self.current_workspace_name = ""
                    self.current_workspace_path = ""
                    txt = "📁 选择工作空间 ∨"
                self.config["current_workspace_name"] = self.current_workspace_name
                self.config["workspace_dir"] = self.current_workspace_path
                if hasattr(self, 'ws_pill'):
                    self.ws_pill.setText(txt)
                if hasattr(self, 'hero_ws_pill'):
                    self.hero_ws_pill.setText(txt)
            if self.save_config_fn:
                self.save_config_fn(self.config)

            # 4. 如果当前处于刚刚被删除的任务，自动切换到剩余有效会话或开启全新任务
            if self._current_session_id in deleted_sids:
                remaining_sessions = self.memory.get_all_sessions() if self.memory else []
                if remaining_sessions:
                    self._load_session(remaining_sessions[0]["id"])
                else:
                    self._create_new_session_action()

            self._refresh_history_list()
            self._refresh_sidebar_workspaces()
            del_count_str = f"（已同时清空该空间下 {len(deleted_sids)} 个任务）" if deleted_sids else ""
            self._show_status(f"🗑 已移除工作空间「{ws_name}」{del_count_str}")

    def _open_batch_workspace_dialog(self):
        """打开工作空间批量管理对话框（支持多选、批量从列表移除及关联任务清理）"""
        if not hasattr(self, 'workspaces'):
            return
        dlg = BatchWorkspaceDialog(
            self,
            is_dark=self._is_dark,
            workspaces=self.workspaces,
            memory=self.memory,
            config=self.config,
            save_config_fn=self.save_config_fn
        )
        dlg.exec_()
        if dlg.removed_workspaces:
            self.workspaces = dlg.workspaces
            self.config["workspaces"] = self.workspaces

            if hasattr(self, 'ai_engine') and self.ai_engine:
                for sid in dlg.deleted_sids:
                    self.ai_engine.session_histories.pop(str(sid), None)
            for sid in dlg.deleted_sids:
                self._session_message_queues.pop(sid, None)
                self._active_streams.pop(sid, None)

            if dlg.deleted_sids:
                pinned = self.config.get("pinned_sessions", [])
                self.config["pinned_sessions"] = [sid for sid in pinned if sid not in dlg.deleted_sids]
                archived = self.config.get("archived_sessions", [])
                self.config["archived_sessions"] = [sid for sid in archived if sid not in dlg.deleted_sids]

            if self.current_workspace_name in dlg.removed_workspaces or not self.workspaces:
                if self.workspaces:
                    self.current_workspace_name = self.workspaces[0].get("name", "")
                    self.current_workspace_path = self.workspaces[0].get("path", "")
                    txt = f"📁 {self.current_workspace_name} ∨"
                else:
                    self.current_workspace_name = ""
                    self.current_workspace_path = ""
                    txt = "📁 选择工作空间 ∨"
                self.config["current_workspace_name"] = self.current_workspace_name
                self.config["workspace_dir"] = self.current_workspace_path
                if hasattr(self, 'ws_pill'):
                    self.ws_pill.setText(txt)
                if hasattr(self, 'hero_ws_pill'):
                    self.hero_ws_pill.setText(txt)

            if self.save_config_fn:
                self.save_config_fn(self.config)

            if self._current_session_id in dlg.deleted_sids:
                remaining_sessions = self.memory.get_all_sessions() if self.memory else []
                if remaining_sessions:
                    self._load_session(remaining_sessions[0]["id"])
                else:
                    self._create_new_session_action()

            self._refresh_history_list()
            self._refresh_sidebar_workspaces()
            del_info = f"（同时清空 {len(dlg.deleted_sids)} 个关联任务）" if dlg.deleted_sids else ""
            self._show_status(f"🗑️ 已成功批量移除 {len(dlg.removed_workspaces)} 个工作空间 {del_info}")

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
        self.memory.cleanup_empty_sessions()
        sessions = self.memory.get_all_sessions()
        if sessions:
            self._load_session(sessions[0]["id"])
        else:
            self._create_new_session_action()

    # ══════════════════════════════════════════════════════════
    #  消息发送与本地文件引用
    # ══════════════════════════════════════════════════════════
    def _on_plus_attach_file_clicked(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择要上传或分析的本地文件与图片",
            self.current_workspace_path or str(ROOT_DIR),
            "支持文件 (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.docx *.pdf *.xlsx *.csv *.txt *.md *.py *.json *.html *.js *.java *.cpp *.sql);;图片文件 (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;文档文件 (*.docx *.pdf *.xlsx *.csv *.txt *.md);;所有文件 (*.*)"
        )
        if not file_paths:
            return

        is_hero = (self.chat_page_stack.currentIndex() == 0)
        target_bar = self.hero_attach_bar if is_hero else self.active_attach_bar

        added_cnt = 0
        for fpath in file_paths:
            info = extract_file_attachment_info(fpath)
            if info:
                target_bar.add_attachment(info)
                added_cnt += 1

        if added_cnt:
            self._show_status(f"📎 已成功添加 {added_cnt} 个文件/图片附件，随时提问AI即可进行深入分析")

    def _on_file_attached(self, fpath: str, is_hero: bool = False):
        """处理直接粘贴或拖拽入输入框的文件与图片附件"""
        info = extract_file_attachment_info(fpath)
        if info:
            target_bar = self.hero_attach_bar if is_hero else self.active_attach_bar
            target_bar.add_attachment(info)
            self._show_status(f"📷 已附加: {Path(fpath).name}")
            self._update_send_button_state()

    def _is_session_generating(self, session_id: Optional[int] = None) -> bool:
        """检查指定会话（或当前活动会话）是否正在后台流式生成中"""
        sid = session_id if session_id is not None else self._current_session_id
        return bool(sid is not None and sid in self._active_streams)

    @property
    def _is_generating(self) -> bool:
        """兼容性属性：当前视图会话是否处于生成状态"""
        return self._is_session_generating(self._current_session_id)

    def _update_send_button_state(self):
        """根据当前活动会话的生成状态与输入框内容动态更新发送/停止按钮外观"""
        is_gen = self._is_session_generating(self._current_session_id)
        has_text = bool(self.input_edit.toPlainText().strip()) if hasattr(self, 'input_edit') else False
        has_attach = bool(self.active_attach_bar.attachments) if hasattr(self, 'active_attach_bar') else False

        if hasattr(self, 'send_btn'):
            self.send_btn.setEnabled(True)
            if is_gen and not has_text and not has_attach:
                self.send_btn.setText("⏹")
                self.send_btn.setToolTip("点击停止当前任务会话的生成")
            elif is_gen and (has_text or has_attach):
                self.send_btn.setText("▲")
                self.send_btn.setToolTip("发送并排队等待执行 (Ctrl+Enter)")
            else:
                self.send_btn.setText("▲")
                self.send_btn.setToolTip("发送消息 (Ctrl+Enter)")
        if hasattr(self, 'hero_send_btn'):
            self.hero_send_btn.setEnabled(True)
            self.hero_send_btn.setText("▲")

    def _stop_session_generation(self, session_id: int):
        """停止指定会话的 AI 流式生成并清空该会话的等待队列"""
        active = self._active_streams.get(session_id)
        q_count = len(self._session_message_queues.get(session_id, []))
        self._session_message_queues.pop(session_id, None)

        if active:
            active["is_stopped"] = True
            saved_text = active.get("full_text", "")
            self._active_streams.pop(session_id, None)
            self._update_send_button_state()
            if q_count > 0:
                self._show_status(f"⏹️ 已停止回答生成，并清空该会话剩余 {q_count} 条排队消息")
            else:
                self._show_status("⏹️ 已停止当前任务会话的回答生成")
            if session_id == self._current_session_id and self._current_ai_block:
                if self._current_ai_block.raw_text == "⏳ 正在思考...":
                    self._current_ai_block.set_text("⏹ *(回答生成已由用户中止)*")
                elif saved_text and self.memory:
                    self.memory.add_message(session_id, "assistant", saved_text)
            elif saved_text and self.memory:
                self.memory.add_message(session_id, "assistant", saved_text)

    def _send_hero_message(self):
        raw_text = self.hero_input_edit.toPlainText().strip()
        attachments = list(self.hero_attach_bar.attachments) if hasattr(self, 'hero_attach_bar') else []
        if not raw_text and not attachments:
            return

        user_text = raw_text if raw_text else "请帮我全面分析以上上传的附件内容并给出详细解答。"
        self.hero_input_edit.clear()
        if hasattr(self, 'hero_attach_bar'):
            self.hero_attach_bar.clear()

        self._enter_active_chat_mode()
        self._inject_user_profile_into_prompt()
        if self._active_sub_scenario:
            scen_name = self._active_sub_scenario.get("name", "")
            if scen_name and scen_name not in user_text and "技能" not in user_text:
                final_text = f"【场景：{scen_name}】{user_text}"
            else:
                final_text = user_text
        else:
            final_text = user_text
        self._do_send(final_text, attachments=attachments)

    def _send_active_message(self):
        cur_sid = self._current_session_id
        raw_text = self.input_edit.toPlainText().strip()
        attachments = list(self.active_attach_bar.attachments) if hasattr(self, 'active_attach_bar') else []

        if raw_text or attachments:
            user_text = raw_text if raw_text else "请帮我全面分析以上上传的附件内容并给出详细解答。"
            self.input_edit.clear()
            if hasattr(self, 'active_attach_bar'):
                self.active_attach_bar.clear()

            self._inject_user_profile_into_prompt()
            self._do_send(user_text, attachments=attachments)
            return

        # 仅当输入框为空且当前正在生成时，点击按钮才触发停止
        if self._is_session_generating(cur_sid):
            if cur_sid is not None:
                self._stop_session_generation(cur_sid)
            return

    def _inject_user_profile_into_prompt(self):
        """把用户在设置页保存的昵称 + 记忆备注 + 规则红线追加到 system_prompt 末尾，让大模型永久生效并严格执行"""
        if not self.ai_engine or not hasattr(self.ai_engine, 'system_prompt'):
            return
        user_name = (self.config.get("user_name") or "").strip()
        user_memo = (self.config.get("user_memo") or "").strip()
        user_rules = (self.config.get("user_rules") or self.config.get("custom_rules") or "").strip()
        if not user_name and not user_memo and not user_rules:
            return

        profile_lines = []
        if user_name:
            profile_lines.append(f"用户的昵称是「{user_name}」，请你称呼他/她「{user_name}」。")
        if user_memo:
            profile_lines.append(f"关于这位用户的持久记忆与偏好：{user_memo}")

        profile_block = ""
        if profile_lines:
            profile_block += "\n\n【用户档案与永久记忆 - 永久生效】\n" + "\n".join(profile_lines)
        if user_rules:
            profile_block += (
                f"\n\n【用户自定义核心规则与强制红线 - 必须最高优先级无条件严格执行】\n"
                f"用户为你设定了以下行为准则、输出要求与不可触碰的红线约束，你在所有对话、代码编写与任务执行中必须严格遵守：\n"
                f"{user_rules}\n"
                f"【红线效力准则】：若上述规则与任何通用回复习惯产生冲突，必须以用户设定的上述规则与红线为最高标准执行！"
            )

        base_sp = self.ai_engine.system_prompt or ""
        if "【用户档案与永久记忆 - 永久生效】" in base_sp:
            base_sp = base_sp.split("【用户档案与永久记忆 - 永久生效】")[0].rstrip()
        elif "【用户档案 - 永久生效】" in base_sp:
            base_sp = base_sp.split("【用户档案 - 永久生效】")[0].rstrip()
        if "【用户自定义核心规则与强制红线" in base_sp:
            base_sp = base_sp.split("【用户自定义核心规则与强制红线")[0].rstrip()

        self.ai_engine.system_prompt = base_sp + profile_block

    def _update_plan_btn_style(self, btn: QPushButton, is_on: bool):
        d = self._is_dark
        if is_on:
            btn.setText("📋 计划模式 (ON)")
            bg = "#1e3a8a" if d else "#eff6ff"
            border = "#3b82f6"
            color = "#93c5fd" if d else "#1d4ed8"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    color: {color};
                    border: 1px solid {border};
                    border-radius: 13px;
                    padding: 0 10px;
                    font-size: 11px;
                    font-weight: bold;
                    font-family: 'PingFang SC', 'Microsoft YaHei UI', sans-serif;
                }}
                QPushButton:hover {{
                    background-color: {'#1d4ed8' if d else '#dbeafe'};
                }}
            """)
        else:
            btn.setText("📋 计划模式")
            bg = "#27272a" if d else "#f1f5f9"
            border = "#3f3f46" if d else "#e2e8f0"
            color = "#a1a1aa" if d else "#64748b"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    color: {color};
                    border: 1px solid {border};
                    border-radius: 13px;
                    padding: 0 10px;
                    font-size: 11px;
                    font-weight: 500;
                    font-family: 'PingFang SC', 'Microsoft YaHei UI', sans-serif;
                }}
                QPushButton:hover {{
                    background-color: {'#3f3f46' if d else '#e2e8f0'};
                    color: {'#ffffff' if d else '#0f172a'};
                }}
            """)

    def _toggle_plan_mode(self, checked: bool):
        if hasattr(self, 'hero_plan_mode_btn'):
            self.hero_plan_mode_btn.setChecked(checked)
            self._update_plan_btn_style(self.hero_plan_mode_btn, checked)
        if hasattr(self, 'active_plan_mode_btn'):
            self.active_plan_mode_btn.setChecked(checked)
            self._update_plan_btn_style(self.active_plan_mode_btn, checked)
        if checked:
            self._show_status("📋 计划模式已开启：AI 将先为您制定结构化实施方案，待您确认接收后再落地执行")
        else:
            self._show_status("💬 已切回普通对话模式")

    @staticmethod
    def _is_planning_mode_intent(text: str) -> bool:
        """多维度智能意图识别：全面检测用户自然语言是否包含计划先行（先计划再执行）的诉求"""
        if not text:
            return False
        t = text.strip().lower()
        # 1. 明确的执行/落地/批准意图，绝对不能误判为计划模式
        exec_keywords = [
            "【用户已确认接收并批准", "立即按方案分步执行落地", "执行落地", "开始执行",
            "按方案执行", "开始落地", "批准执行", "确认执行", "立即执行", "proceed",
            "开始写代码", "开始编写", "实现方案"
        ]
        if any(ek in t for ek in exec_keywords):
            return False

        if any(k in t for k in [
            "当前处于「计划模式", "先制定完整实施计划",
            "plan-then-execute", "plan mode", "计划模式"
        ]):
            return True

        import re
        # 正则1: 先/首先/提前/请先 ... 计划/方案/规划/文档/架构 ... 再/然后/之后/后/确认/审核/批准 ... 执行/做/实现/落地/编写/写/代码/实施/动手
        if re.search(r'(先|首先|提前|请先).*(计划|方案|规划|文档|架构).*(再|然后|之后|后|确认|审核|批准).*(执行|做|实现|落地|编写|写|代码|实施|动手)', t, re.DOTALL):
            return True

        # 正则2: 先/首先/提前/请先 ... 生成/制定/出/写/做/设计/提供/给 ... 计划/方案/规划/文档
        if re.search(r'(先|首先|提前|请先).*(生成|制定|出|写|做|设计|提供|给).*(计划|方案|规划|文档)', t, re.DOTALL):
            return True

        # 正则3: 生成/制定/编写/出 ... 实施方案/实施计划/计划文档/执行方案/落地方案
        if re.search(r'(生成|制定|编写|出|写).*(实施方案|实施计划|计划文档|执行方案|落地方案|落地规划)', t, re.DOTALL):
            return True

        plan_keywords = [
            "先制定计划", "先做计划", "先写规划", "先出方案", "先做规划", 
            "制定实施计划", "出个方案再做", "先设计好方案再执行", "先制定方案", 
            "先制定好计划后再执行", "制定好计划后再执行", "先制定计划后再执行",
            "先生成计划", "生成计划文档", "生成实施方案", "出个实施方案", "制定实施方案",
            "先规划再实现", "先规划再写代码", "先写计划再执行", "先出计划再执行",
            "先出计划文档", "先给计划文档", "先出规划", "实施方案预览"
        ]
        return any(k in t for k in plan_keywords)

    def _do_send(self, text: str, attachments: list = None):
        attachments = attachments or []

        # 1. 构建聊天气泡呈现的内容 (用户端精美胶囊 + 用户问题)
        if attachments:
            badges = []
            for att in attachments:
                nm = att.get("name", "")
                sz = att.get("size_str", "")
                ext = att.get("ext", "").replace(".", "").upper() or "FILE"
                if att.get("type") == "image":
                    badges.append(f"🖼️ `{nm}` *({sz})*")
                else:
                    badges.append(f"📎 `{nm}` *({ext} · {sz})*")
            badge_str = "  ".join(badges)
            user_display = f"{badge_str}\n\n{text}" if text else badge_str
        else:
            user_display = text

        # 2. 构建大模型与 SQLite 上下文包含的完整内容
        if attachments:
            p_parts = []
            for att in attachments:
                nm = att.get("name", "")
                sz = att.get("size_str", "")
                ext = att.get("ext", "").replace(".", "").upper() or "FILE"
                content = att.get("extracted_text", "").strip()
                if att.get("type") == "image":
                    p_parts.append(f"【用户上传了图片附件】\n- 图片文件: {nm}\n- 规格大小: {sz}\n- 本地路径: {att.get('path')}")
                else:
                    p_parts.append(f"【用户上传了文档附件】\n📎 文件名: {nm} ({ext} · {sz})\n--- 附件正文内容开始 ---\n{content}\n--- 附件正文内容结束 ---")
            p_parts.append(f"用户需求与问题:\n{text}")
            ai_prompt = "\n\n".join(p_parts)
        else:
            ai_prompt = text

        # 3. 检查是否处于计划模式 (显式按钮开启 或 自然语言关键词/句式意图命中)
        # 若用户明确表达了执行/落地/开始实施的意图，必须自动关闭计划模式
        has_exec_intent = any(k in (text or "").lower() for k in [
            "【用户已确认接收并批准", "立即按方案分步执行落地", "执行落地", "开始执行", 
            "按方案执行", "开始落地", "批准执行", "确认执行", "立即执行", "proceed",
            "开始写代码", "开始编写", "实现方案"
        ])
        if has_exec_intent:
            self._toggle_plan_mode(False)
            is_plan_mode = False
        else:
            is_plan_mode = False
            if hasattr(self, 'active_plan_mode_btn') and self.active_plan_mode_btn.isChecked():
                is_plan_mode = True
            elif hasattr(self, 'hero_plan_mode_btn') and self.hero_plan_mode_btn.isChecked():
                is_plan_mode = True
            else:
                is_plan_mode = self._is_planning_mode_intent(text)
                if is_plan_mode:
                    # 智能识别自然语言意图，自动联动点亮 UI 按钮并提示用户
                    self._toggle_plan_mode(True)

        if is_plan_mode:
            plan_instruction = (
                "\n\n【核心指令：当前处于「计划模式（Plan-then-Execute）」】\n"
                "用户明确要求你「先制定完整实施计划后再执行」。\n"
                "【重要执行红线 - 严禁调用任何写文件与执行代码工具】：\n"
                "1. 本阶段为会话内的方案预览阶段，严禁调用任何外部工具（包括 generate_project_readme、run_python_code、create_file、file_tools 等任何工具）！\n"
                "2. 严禁尝试在磁盘或桌面上创建或写入任何物理文件！严禁在本次回复中输出直接可执行的源码全文！\n"
                "3. 该实施方案是作为当前对话内的纯文本 Markdown 文档呈现给用户，用户界面已提供「复制」与「下载」按钮，用户可点击下载后自主选择路径保存为 .md 文件；\n"
                "4. 请直接在本次回复中输出结构清晰、详尽落地的 Markdown 实施计划方案，严格遵循以下结构输出：\n"
                "# [实施方案名称与核心目标]\n"
                "## 一、 需求理解与目标概述\n"
                "## 二、 核心架构设计与决策分析\n"
                "## 三、 涉及文件与模块清单（请标明 [MODIFY] 修改 或 [NEW] 新建）\n"
                "## 四、 详细分步实施步骤（Step 1, Step 2, Step 3...）\n"
                "## 五、 验证与测试方案\n\n"
                "【方案就绪确认标记 - 必须输出】：请在方案结尾务必单独一行输出以下标记：\n"
                "<!-- PLAN_DOCUMENT_READY -->\n"
                "📋 实施方案已就绪，请审阅确认\n"
            )
            ai_prompt += plan_instruction


        # 若尚未存在会话，在数据库中正式创建新任务会话
        if self.memory and self._current_session_id is None:
            ws_name = self.current_workspace_name or ""
            if attachments:
                short_title = f"文档分析: {attachments[0].get('name', '未命名')[:14]}"
            else:
                short_title = text.strip()[:18] + ("..." if len(text.strip()) > 18 else "") or "新任务会话"
            self._current_session_id = self.memory.create_session(short_title, workspace_name=ws_name)
            self.chat_title_lbl.setText(short_title)
            self.setWindowTitle(f"{short_title} - NovaDesk")
            self._refresh_history_list()
            self._refresh_sidebar_workspaces()

        cur_sid = self._current_session_id

        # 驱动动漫桌宠情绪系统
        try:
            if hasattr(self, 'pet_window') and self.pet_window:
                if hasattr(self.pet_window, 'emotion_system') and self.pet_window.emotion_system:
                    self.pet_window.emotion_system.update_by_text(text)
        except Exception:
            pass

        if self.memory and cur_sid:
            msgs = self.memory.get_session_messages(cur_sid)
            if len(msgs) == 0:
                if attachments:
                    short = f"文档分析: {attachments[0].get('name', '未命名')[:14]}"
                else:
                    short = text.strip()[:18] + ("..." if len(text.strip()) > 18 else "")
                self.memory.update_session_title(cur_sid, short)
                self.chat_title_lbl.setText(short)
                self.setWindowTitle(f"{short} - NovaDesk")
                self._refresh_history_list()
            # 实时持久化完整上下文到 SQLite
            self.memory.add_message(cur_sid, "user", ai_prompt)

        # 立即在聊天气泡区添加 User 消息块（优雅展示精美胶囊 + 问题）
        self._add_message_block("user", user_display)

        # 查找附件中是否有图片文件
        first_img_path = None
        if attachments:
            for att in attachments:
                if att.get("type") == "image" and att.get("path"):
                    first_img_path = att.get("path")
                    break

        # 排队检查或启动流式推理
        if self._is_session_generating(cur_sid):
            self._session_message_queues.setdefault(cur_sid, []).append((ai_prompt, first_img_path))
            q_len = len(self._session_message_queues[cur_sid])
            self._show_status(f"⏳ 消息已加入等待队列（前方排队 {q_len} 条），上一条完成后自动发送")
            self._update_send_button_state()
            return

        self._start_stream_for_session(cur_sid, ai_prompt, image_path=first_img_path)

    def _start_stream_for_session(self, session_id: int, user_msg: str, image_path: Optional[str] = None):
        """启动指定会话的 AI 流式推理"""
        # 确保当前会话对应的工作空间与 SecurityGuard 强同步
        ws_path = self.current_workspace_path
        if self.memory and session_id:
            try:
                sess = self.memory.get_session(session_id)
                if sess and sess.get("workspace_path"):
                    ws_path = sess.get("workspace_path")
            except Exception:
                pass
        if ws_path:
            try:
                from core.security_guard import SecurityGuard
                SecurityGuard.get_instance().set_workspace_root(ws_path)
            except Exception:
                pass

        if session_id == self._current_session_id:
            self._current_ai_block = self._add_message_block("ai", "⏳ 正在思考...")
        else:
            self._current_ai_block = None

        self._stream_counter += 1
        stream_id = self._stream_counter
        self._active_streams[session_id] = {
            "stream_id": stream_id,
            "full_text": "",
            "is_stopped": False,
            "user_msg": user_msg
        }
        self._update_send_button_state()
        self._refresh_generating_status()
        self._set_taskbar_running()

        threading.Thread(target=self._stream_worker, args=(session_id, stream_id, user_msg, image_path), daemon=True).start()

    def _stream_worker(self, session_id: int, stream_id: int, user_msg: str, image_path: Optional[str] = None):
        full = ""
        loop = None
        last_emit_time = 0.0
        try:
            async def _run():
                nonlocal full, last_emit_time
                import time
                async for chunk in self.ai_engine.chat_stream(user_msg, session_id=str(session_id), image_path=image_path):
                    active = self._active_streams.get(session_id)
                    if not active or active.get("is_stopped") or active.get("stream_id") != stream_id:
                        break
                    full += chunk
                    active["full_text"] = full

                    # 核心性能优化：50ms 流式节流自适应批处理（约 20 FPS），关键状态（工具调用/思考链/工作空间变动）即刻强刷
                    now = time.time()
                    is_special = any(k in chunk for k in [":::tool_call:", "[[WORKSPACE_", "<think>", "</think>"])
                    if is_special or (now - last_emit_time >= 0.05):
                        last_emit_time = now
                        self.message_chunk_signal.emit(session_id, stream_id, full)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_run())

            active = self._active_streams.get(session_id)
            if active and not active.get("is_stopped") and active.get("stream_id") == stream_id:
                self.message_done_signal.emit(session_id, stream_id, full)
        except Exception as e:
            active = self._active_streams.get(session_id)
            if active and active.get("stream_id") == stream_id:
                self.message_error_signal.emit(session_id, stream_id, str(e))
        finally:
            if loop:
                try:
                    loop.close()
                except Exception:
                    pass

    def _on_chunk(self, session_id: int, stream_id: int, full_text: str):
        # 仅当用户当前处于该会话时才更新活跃 UI 块
        if session_id == self._current_session_id:
            if self._current_ai_block:
                self._current_ai_block.set_text(full_text, is_finished=False)
                self._scroll_to_bottom()
            elif self._message_blocks and self._message_blocks[-1].sender == "ai":
                self._current_ai_block = self._message_blocks[-1]
                self._current_ai_block.set_text(full_text, is_finished=False)
                self._scroll_to_bottom()

    def _on_done(self, session_id: int, stream_id: int, full_text: str):
        self._active_streams.pop(session_id, None)
        self._refresh_generating_status()
        # 严格按所属 session_id 持久化落库，杜绝多会话串扰
        if self.memory and session_id and full_text:
            self.memory.add_message(session_id, "assistant", full_text)

        if session_id == self._current_session_id:
            if self._current_ai_block:
                self._current_ai_block.set_text(full_text, is_finished=True)
                self._scroll_to_bottom()
            self._current_ai_block = None
            # 联动更新已确认接收的实施方案卡片状态为已完成
            for b in self._message_blocks:
                if hasattr(b, 'plan_card') and b.plan_card and b.plan_card.is_proceeded:
                    b.plan_card.update_status_message("✅ 实施方案已落地执行完成", is_completed=True)

        # 1. 查询当前完成的任务标题（严格匹配任务栏/会话树标题）
        task_title = "新任务"
        if self.memory and session_id:
            try:
                sess = self.memory.get_session(session_id)
                if sess and sess.get("title"):
                    task_title = sess.get("title")
            except Exception:
                pass
        if not task_title or task_title == "新任务":
            if hasattr(self, 'chat_title_lbl'):
                task_title = self.chat_title_lbl.text() or "当前任务"

        # 2. 任务栏变色与高亮闪烁提示：若窗口在后台/已最小化/隐藏，任务栏图标底色变橙色高亮
        if not self._active_streams:
            is_background = self.isMinimized() or self.isHidden() or (not self.isActiveWindow())
            if is_background:
                if self.isHidden():
                    self.showMinimized()
                self._set_taskbar_completed()
            else:
                self._clear_taskbar_alert()

        # 3. 联动 2D 动漫桌宠提示：“主人，【{task_title}】任务已经完成啦”，并播放清脆提示音
        if hasattr(self, 'pet_window') and self.pet_window:
            if hasattr(self.pet_window, 'notify_task_completed'):
                self.pet_window.notify_task_completed(task_title)

        # 检查该会话是否有排队消息等待处理
        queue = self._session_message_queues.get(session_id, [])
        if queue:
            next_item = queue.pop(0)
            if isinstance(next_item, tuple):
                next_msg, next_img = next_item
            else:
                next_msg, next_img = next_item, None
            if session_id == self._current_session_id:
                self._show_status(f"🚀 上一条回答完成，已自动开始处理队列中的下一条消息（剩余排队 {len(queue)} 条）")
            self._start_stream_for_session(session_id, next_msg, image_path=next_img)
        else:
            if session_id == self._current_session_id:
                self._update_send_button_state()

        self._refresh_history_list()

    def _on_error(self, session_id: int, stream_id: int, err: str):
        self._active_streams.pop(session_id, None)
        self._refresh_generating_status()
        if not self._active_streams:
            self._clear_taskbar_alert()
        if session_id == self._current_session_id:
            if self._current_ai_block:
                self._current_ai_block.set_text(f"⚠️ 请求失败: {err}")
            self._current_ai_block = None

        # 遇到错误时，若队列中仍有排队消息，继续处理下一条
        queue = self._session_message_queues.get(session_id, [])
        if queue:
            next_item = queue.pop(0)
            if isinstance(next_item, tuple):
                next_msg, next_img = next_item
            else:
                next_msg, next_img = next_item, None
            if session_id == self._current_session_id:
                self._show_status(f"🚀 自动开始处理队列中的下一条消息（剩余排队 {len(queue)} 条）")
            self._start_stream_for_session(session_id, next_msg, image_path=next_img)
        else:
            if session_id == self._current_session_id:
                self._update_send_button_state()

        self._refresh_history_list()

    def _refresh_generating_status(self):
        """定期刷新侧栏正在生成状态：遍历 task_items_lay + ws_items_lay 现有 widgets，更新 is_generating spinner"""
        if not self._active_streams:
            return
        for lay_name in ('task_items_lay', 'ws_items_lay'):
            lay = getattr(self, lay_name, None)
            if not lay:
                continue
            for i in range(lay.count()):
                item = lay.itemAt(i)
                if not item:
                    continue
                w = item.widget()
                if isinstance(w, SidebarTaskItemWidget):
                    is_gen = (w.session_id in self._active_streams)
                    if getattr(w, 'is_generating', False) != is_gen:
                        w.set_generating(is_gen)

    def _add_message_block(self, sender: str, text: str, timestamp: str = "", auto_scroll: bool = True) -> MessageBlock:
        block = MessageBlock(
            sender, text, timestamp=timestamp,
            model_name=self._get_active_model_display(),
            is_dark=self._is_dark,
            user_avatar_path=self.config.get("user_avatar_path")
        )
        if sender == "ai":
            block.retry_requested.connect(self._on_retry_message)
            block.proceed_plan_signal.connect(self._on_proceed_plan)
            block.feedback_plan_signal.connect(self._on_feedback_plan)
        self._message_blocks.append(block)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, block)
        if auto_scroll:
            self._scroll_to_bottom()
        return block

    def _on_proceed_plan(self, block: MessageBlock, plan_text: str):
        """用户点击【🚀 接收并立即执行 (Proceed)】时的核心调度处理器：
        1. 在当前会话中构造正式落地执行的 Prompt；
        2. 严格遵循会话排队机制（_session_message_queues）：
           - 若当前有正在生成的流或已有排队任务，严格加入队尾，绝不插队，保证原有 FIFO 队列次序完好无损；
           - 若当前空闲且无排队，立即流式启动执行；
        3. 卡片与状态栏反馈实时的排队位次与执行状态；
        4. 记录执行用户徽章与 SQLite 历史。
        """
        cur_sid = self._current_session_id
        if not cur_sid:
            return

        # 1. 方案已批准，自动退出「计划模式」，切回执行落地模式
        self._toggle_plan_mode(False)

        # 2. 确保当前工作空间与 SecurityGuard 强同步
        ws_root = self.current_workspace_path
        if self.memory and cur_sid:
            try:
                sess = self.memory.get_session(cur_sid)
                if sess and sess.get("workspace_path"):
                    ws_root = sess.get("workspace_path")
            except Exception:
                pass
        if ws_root:
            try:
                from core.security_guard import SecurityGuard
                SecurityGuard.get_instance().set_workspace_root(ws_root)
            except Exception:
                pass
        else:
            try:
                from core.security_guard import SecurityGuard
                ws_root = SecurityGuard.get_instance().workspace_root
            except Exception:
                from pathlib import Path
                ws_root = str(Path.cwd().resolve())

        # 提取方案正文作为执行参考
        clean_plan, _ = parse_and_clean_message_text(plan_text)
        
        # 组装给 AI 的落地执行 Prompt（明确指定当前激活工作空间路径，强令必须真实调用 write_workspace_file 写入物理文件）
        exec_prompt = (
            f"【用户已确认接收并批准前述实施方案，请立即按方案分步执行落地】\n\n"
            f"【当前激活工作空间根目录绝对路径】：{ws_root}\n\n"
            f"【批准执行的实施方案要点】：\n"
            f"{clean_plan[:1600]}\n\n"
            f"【执行落地严格指令】：\n"
            f"1. 涉及的所有新文件与修改，必须严格保存在当前激活工作空间【{ws_root}】中，绝对严禁写入软件工作目录或其它无关路径；\n"
            f"2. 严禁使用口头沙箱或纯文本代码块假装写入！必须立即调用 write_workspace_file 工具生成物理文件并提供完整源码；\n"
            f"3. 请立即开始分步执行并调用工具交付落地文件。"
        )

        user_display = "🚀 **[已批准实施方案，开始进入执行落地阶段]**"
        
        # 持久化用户操作到 SQLite 并展示用户消息块
        if self.memory and cur_sid:
            self.memory.add_message(cur_sid, "user", exec_prompt)
        self._add_message_block("user", user_display)

        # 核心排队队列检查：严格保护已有排队任务，绝不打断或插队
        is_generating = self._is_session_generating(cur_sid)
        has_queue = bool(self._session_message_queues.get(cur_sid))

        if is_generating or has_queue:
            # 必须安全加入排队队列末尾，严格保证原有排队任务按序推进
            self._session_message_queues.setdefault(cur_sid, []).append(exec_prompt)
            q_pos = len(self._session_message_queues[cur_sid])
            if hasattr(block, 'plan_bar') and block.plan_bar:
                block.plan_bar.update_status(f"排队中 · 第 {q_pos} 位")
            if hasattr(block, 'plan_card') and block.plan_card:
                block.plan_card.update_status_message(
                    f"⏳ 方案已确认接收并安全加入任务队列（当前排在第 {q_pos} 位），前方任务执行完毕后将自动按序执行！",
                    is_queued=True
                )
            self._show_status(f"⏳ 方案已加入排队队列（当前排第 {q_pos} 位），前方任务完成后自动执行")
            self._update_send_button_state()
        else:
            # 当前会话完全空闲且无排队，立即流式启动执行
            if hasattr(block, 'plan_bar') and block.plan_bar:
                block.plan_bar.update_status("已批准 · 执行落地中...")
            if hasattr(block, 'plan_card') and block.plan_card:
                block.plan_card.update_status_message(
                    "🚀 方案已接收并批准，正在执行落地中...",
                    is_queued=False
                )
            self._show_status("🚀 方案已接收，正在启动流式执行落地...")
            self._start_stream_for_session(cur_sid, exec_prompt)

    def _on_feedback_plan(self):
        """用户点击【✏️ 补充修改意见】"""
        prefix = "关于该实施方案，我建议进行如下调整：\n"
        if hasattr(self, 'input_edit'):
            cur = self.input_edit.toPlainText().strip()
            if not cur.startswith("关于该实施方案"):
                self.input_edit.setText(prefix + cur)
            self.input_edit.setFocus()
            cursor = self.input_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.input_edit.setTextCursor(cursor)

    def _on_retry_message(self, ai_text: str):
        cur_sid = self._current_session_id
        if self._is_session_generating(cur_sid): return
        
        # 1. 查找被点击重试的 AI 消息块及其紧邻的上一条用户提问
        target_ai_block = None
        target_user_text = ""
        target_idx = -1
        
        for i in range(len(self._message_blocks) - 1, -1, -1):
            b = self._message_blocks[i]
            if b.sender == "ai" and (b.raw_text.strip() == ai_text.strip() or not target_ai_block):
                target_ai_block = b
                target_idx = i
                break
                
        if target_idx >= 0:
            for j in range(target_idx - 1, -1, -1):
                prev_b = self._message_blocks[j]
                if prev_b.sender == "user" and prev_b.raw_text.strip():
                    target_user_text = prev_b.raw_text.strip()
                    break

        if not target_user_text:
            for b in reversed(self._message_blocks):
                if b.sender == "user" and b.raw_text.strip():
                    target_user_text = b.raw_text.strip()
                    break
                    
        if not target_user_text and hasattr(self, 'chat_title_lbl'):
            t = self.chat_title_lbl.text().strip()
            if t and t != "新任务会话":
                target_user_text = t

        if not target_user_text:
            return

        self._show_status("🔄 正在重新向 AI 提问生成...")

        # 2. 如果是最后一条 AI 回复的重试，先清理 SQLite 中的旧回复，防止落库重复
        if self.memory and cur_sid:
            try:
                self.memory.delete_last_assistant_message(cur_sid)
            except Exception:
                pass

        # 3. 原地重置目标 AI 块
        if target_ai_block:
            target_ai_block.set_text("⏳ 正在思考...")
            self._current_ai_block = target_ai_block
        else:
            self._current_ai_block = self._add_message_block("ai", "⏳ 正在思考...")

        self._stream_counter += 1
        stream_id = self._stream_counter
        self._active_streams[cur_sid] = {
            "stream_id": stream_id,
            "full_text": "",
            "is_stopped": False,
            "user_msg": target_user_text
        }
        self._update_send_button_state()
        threading.Thread(target=self._stream_worker, args=(cur_sid, stream_id, target_user_text), daemon=True).start()

    def _scroll_to_bottom(self):
        QTimer.singleShot(20, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def _summon_with_prompt(self, prompt: str):
        # 自动化执行或外部召唤：作为全新的独立任务启动，重置旧会话与空间绑定状态
        self._current_session_id = None
        self._clear_chat_blocks()
        self.current_workspace_name = ""
        self.current_workspace_path = ""
        ws_pill_txt = "📁 选择工作空间 ∨"
        if hasattr(self, 'ws_pill'):
            self.ws_pill.setText(ws_pill_txt)
        if hasattr(self, 'hero_ws_pill'):
            self.hero_ws_pill.setText(ws_pill_txt)
        self.chat_title_lbl.setText("新任务会话")

        self._switch_nav(0)
        self._enter_active_chat_mode()
        self.input_edit.setText(prompt)
        self._send_active_message()

    def _switch_primary_category(self, cat_name: str):
        self._active_primary_cat = cat_name
        d = self._is_dark
        # 1. 刷新主分类按钮样式
        for name, btn in getattr(self, "_primary_cat_btns", {}).items():
            is_act = (name == cat_name)
            if is_act:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {'#27272a' if d else '#6366f1'};
                        color: #ffffff;
                        border: 1px solid {'#3f3f46' if d else '#4f46e5'};
                        border-radius: 14px;
                        font-weight: bold;
                        font-size: 13px;
                        padding: 4px 18px;
                        font-family: 'Microsoft YaHei UI';
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {'#a1a1aa' if d else '#64748b'};
                        border: none;
                        border-radius: 14px;
                        font-weight: 500;
                        font-size: 13px;
                        padding: 4px 18px;
                        font-family: 'Microsoft YaHei UI';
                    }}
                    QPushButton:hover {{
                        background: {'#222222' if d else '#f1f5f9'};
                        color: {'#ffffff' if d else '#0f172a'};
                    }}
                """)

        # 2. 刷新二级场景胶囊
        if hasattr(self, "_sub_scenarios_layout"):
            for i in reversed(range(self._sub_scenarios_layout.count())):
                item = self._sub_scenarios_layout.itemAt(i)
                if item and item.widget():
                    item.widget().setParent(None)

            self._sub_scen_buttons = []
            cat_info = HERO_SCENARIOS_MAP.get(cat_name, {})
            sub_scenarios = cat_info.get("sub_scenarios", [])

            for s in sub_scenarios:
                b = QPushButton(f"{s['icon']}  {s['name']}")
                b.setFixedHeight(30)
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(lambda ch, scen=s: self._on_sub_scenario_clicked(scen))
                self._sub_scenarios_layout.addWidget(b)
                self._sub_scen_buttons.append((s, b))

            # 默认不自动选中任何子场景，保持输入框干净清爽
            self._clear_sub_scenario()

    def _on_sub_scenario_clicked(self, s: dict):
        # 若点击已选中的场景，则反选清空
        if self._active_sub_scenario and self._active_sub_scenario.get("id") == s.get("id"):
            self._clear_sub_scenario()
            return

        self._active_sub_scenario = s
        d = self._is_dark

        # 1. 刷新二级场景按钮高亮状态
        for scen, btn in getattr(self, "_sub_scen_buttons", []):
            is_cur = (scen.get("id") == s.get("id"))
            if is_cur:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {'#1e1b4b' if d else '#eef2ff'};
                        color: {'#c7d2fe' if d else '#4f46e5'};
                        border: 1px solid {'#6366f1' if d else '#818cf8'};
                        border-radius: 14px;
                        font-weight: bold;
                        font-size: 12px;
                        padding: 0 14px;
                        font-family: 'Microsoft YaHei UI';
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {'rgba(255,255,255,0.04)' if d else '#f1f5f9'};
                        color: {'#cbd5e1' if d else '#475569'};
                        border: 1px solid {'rgba(255,255,255,0.08)' if d else '#e2e8f0'};
                        border-radius: 14px;
                        font-weight: 500;
                        font-size: 12px;
                        padding: 0 14px;
                        font-family: 'Microsoft YaHei UI';
                    }}
                    QPushButton:hover {{
                        background: {'#27272a' if d else '#e2e8f0'};
                        color: {'#ffffff' if d else '#0f172a'};
                        border-color: {'#6366f1' if d else '#cbd5e1'};
                    }}
                """)

        # 2. 展现输入框内的场景药丸标签 (复刻截图3翠绿质感徽标)
        if hasattr(self, "hero_tag_name_lbl"):
            self.hero_tag_name_lbl.setText(f"{s['icon']} {s['name']}")
        if hasattr(self, "hero_scenario_tag_widget"):
            self.hero_scenario_tag_widget.show()
        if hasattr(self, "hero_input_edit"):
            self.hero_input_edit.setPlaceholderText("今天帮你做些什么？ @ 引用对话文件，/ 调用技能与指令")
            self.hero_input_edit.setFocus()

    def _clear_sub_scenario(self):
        self._active_sub_scenario = None
        if hasattr(self, "hero_scenario_tag_widget"):
            self.hero_scenario_tag_widget.hide()
        if hasattr(self, "hero_input_edit"):
            self.hero_input_edit.setPlaceholderText("今天帮你做些什么？ @ 引用对话文件，/ 调用技能与指令")
        d = self._is_dark
        # 恢复二级场景按钮无激活状态
        for scen, btn in getattr(self, '_sub_scen_buttons', []):
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'rgba(255,255,255,0.04)' if d else '#f1f5f9'};
                    color: {'#cbd5e1' if d else '#475569'};
                    border: 1px solid {'rgba(255,255,255,0.08)' if d else '#e2e8f0'};
                    border-radius: 14px;
                    font-weight: 500;
                    font-size: 12px;
                    padding: 0 14px;
                    font-family: 'Microsoft YaHei UI';
                }}
                QPushButton:hover {{
                    background: {'#27272a' if d else '#e2e8f0'};
                    color: {'#ffffff' if d else '#0f172a'};
                }}
            """)

    def _apply_template_prompt(self, prompt: str):
        if hasattr(self, "hero_input_edit"):
            self.hero_input_edit.setText(prompt)
            self.hero_input_edit.setFocus()
            cursor = self.hero_input_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.hero_input_edit.setTextCursor(cursor)
            self._update_send_button_state()

    def _on_scenario_chip(self, name: str):
        # 查找对应的主分类或二级场景
        for cat_name, cat_data in HERO_SCENARIOS_MAP.items():
            if name == cat_name:
                self._switch_primary_category(cat_name)
                return
            for s in cat_data.get("sub_scenarios", []):
                if s["name"] == name:
                    self._switch_primary_category(cat_name)
                    self._on_sub_scenario_clicked(s)
                    return
        self._switch_primary_category("代码开发")

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
        if hasattr(self, 'status_lbl') and self.status_lbl:
            self.status_lbl.setText(f"● {msg}")
            QTimer.singleShot(4000, lambda: self.status_lbl.setText("🟢 智能体 就绪") if hasattr(self, 'status_lbl') and self.status_lbl else None)
        if hasattr(self, 'dev_mode_view') and self.dev_mode_view and hasattr(self.dev_mode_view, 'set_status'):
            self.dev_mode_view.set_status(msg)

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
            f"QWidget#SideBar{{background-color:{side_bg};}}"
        )
        self.title_lbl.setStyleSheet(f"color:{fg};font-weight:bold;font-family:'Microsoft YaHei UI';")
        if hasattr(self, 'work_lbl'):
            self.work_lbl.setStyleSheet(f"color:{fg};font-size:11px;font-weight:bold;font-family:'Microsoft YaHei UI';")
        # 主题按钮只显示一个 SVG 图标（避免图标+emoji 文本双图标重叠）
        if hasattr(self, 'theme_btn'):
            _icon_color = "#a1a1aa" if d else "#64748b"
            self.theme_btn.setText("")
            self.theme_btn.setIcon(load_ui_icon("moon" if d else "sun", _icon_color, 16))
            self.theme_btn.setIconSize(QSize(16, 16))
        for btn in [self.theme_btn, self.min_btn, self.max_btn]:
            btn.setStyleSheet(
                f"QPushButton{{background:transparent;border:none;font-size:12px;}}"
                f"QPushButton:hover{{background:{hover};border-radius:6px;}}"
            )
        # max_btn 图标根据是否最大化切换（square 单正方形 = 普通 / square-restore 双正方形 = 已最大化）
        if hasattr(self, 'max_btn'):
            max_icon_name = "square-restore" if self._is_maximized else "square"
            self.max_btn.setIcon(load_ui_icon(max_icon_name, _icon_color, 16))
            self.max_btn.setIconSize(QSize(16, 16))
        self.close_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{sub_fg};border:none;font-size:12px;}}"
            "QPushButton:hover{background:#ef4444;color:#fff;border-radius:6px;}"
        )
        
        # 新建任务按钮 (深色下沉稳深灰底白字)
        new_task_bg = "#27272a" if d else "#ffffff"
        self.new_task_btn.setStyleSheet(
            f"QPushButton{{background:{new_task_bg};color:{fg};border:1px solid {border};"
            f"border-radius:10px;font-weight:bold;font-size:13px;font-family:'Microsoft YaHei UI';}}"
            f"QPushButton:hover{{background:{hover};}}"
        )

        # 开发模式同款极简纯净滚动条 (与 DevModeView 完全一致：平滑圆角胶囊滑块、零虚线方格纹理、优雅轻量)
        sb_handle = "#3e4451" if d else "#cbd5e1"
        sb_hover = "#5c6370" if d else "#94a3b8"
        scrollbar_style = f"""
            QScrollBar:vertical {{
                width: 6px;
                background: transparent;
                border: none;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {sb_handle};
                border-radius: 3px;
                min-height: 24px;
                border: none;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {sb_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                height: 0px;
                width: 0px;
                background: transparent;
                border: none;
            }}
            QScrollBar:horizontal {{
                height: 0px;
                background: transparent;
                border: none;
            }}
            QScrollBar::handle:horizontal,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                width: 0px;
                height: 0px;
                background: transparent;
                border: none;
            }}
        """
        if hasattr(self, 'sidebar_scroll'):
            self.sidebar_scroll.setStyleSheet(f"""
                QScrollArea {{
                    background: transparent;
                    border: none;
                }}
                QScrollArea > QWidget > QWidget {{
                    background: transparent;
                }}
                {scrollbar_style}
            """)
            if hasattr(self.sidebar_scroll, 'verticalScrollBar') and self.sidebar_scroll.verticalScrollBar():
                self.sidebar_scroll.verticalScrollBar().setStyleSheet(scrollbar_style)

        # 消息流滚动区与内部画布背景：使用与主卡片完全一致的纯色实体背景，防止透明背景下的脏矩形文字重叠重影
        if hasattr(self, 'scroll_area'):
            self.scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {bg};
                    border: none;
                }}
                QScrollArea > QWidget > QWidget {{
                    background-color: {bg};
                }}
                {scrollbar_style}
            """)
            if self.scroll_area.viewport():
                self.scroll_area.viewport().setStyleSheet(f"background-color: {bg}; border: none;")
            if hasattr(self.scroll_area, 'verticalScrollBar') and self.scroll_area.verticalScrollBar():
                self.scroll_area.verticalScrollBar().setStyleSheet(scrollbar_style)
        if hasattr(self, 'chat_content'):
            self.chat_content.setStyleSheet(f"background-color: {bg}; border: none;")

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

        # 场景选择胶囊 (刷新主分类与二级场景)
        if hasattr(self, "_switch_primary_category") and hasattr(self, "_active_primary_cat"):
            self._switch_primary_category(self._active_primary_cat)

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
        if hasattr(self, 'chat_content'): self.chat_content.setStyleSheet(f"background-color: {content_bg}; border: none;")
        if hasattr(self, 'scroll_area'):
            self.scroll_area.viewport().setStyleSheet(f"background-color: {content_bg}; border: none;")
            self.scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {content_bg};
                    border: none;
                }}
                QScrollArea > QWidget > QWidget {{
                    background-color: {content_bg};
                }}
                {scrollbar_style}
            """)
            if hasattr(self.scroll_area, 'verticalScrollBar') and self.scroll_area.verticalScrollBar():
                self.scroll_area.verticalScrollBar().setStyleSheet(scrollbar_style)

        for b in self._message_blocks:
            b.set_theme(d)

        if hasattr(self, 'h_title'):
            self.h_title.setStyleSheet(f"color:{fg};font-size:24px;font-weight:bold;font-family:'Microsoft YaHei UI';")
        if hasattr(self, 'task_head'):
            self.task_head.setStyleSheet(f"color:{sub_fg};font-size:11px;font-weight:bold;")
        if hasattr(self, 'ws_head'):
            self.ws_head.setStyleSheet(f"color:{sub_fg};font-size:11px;font-weight:bold;")

        batch_btn_style = f"""
            QPushButton {{
                background: transparent;
                color: {'#71717a' if d else '#94a3b8'};
                border: none;
                border-radius: 4px;
                font-size: 10.5px;
                font-family: 'PingFang SC', 'Microsoft YaHei UI', sans-serif;
                padding: 1px 6px;
            }}
            QPushButton:hover {{
                background: {'#27272a' if d else '#e2e8f0'};
                color: {'#e4e4e7' if d else '#18181b'};
            }}
        """
        if hasattr(self, 'task_batch_btn'):
            self.task_batch_btn.setStyleSheet(batch_btn_style)
        if hasattr(self, 'ws_batch_btn'):
            self.ws_batch_btn.setStyleSheet(batch_btn_style)
        if hasattr(self, 'task_header_toggle_btn'):
            self.task_header_toggle_btn.setStyleSheet(batch_btn_style)
        if hasattr(self, 'hero_attach_bar'):
            self.hero_attach_bar.set_theme(d)
        if hasattr(self, 'active_attach_bar'):
            self.active_attach_bar.set_theme(d)
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
        if hasattr(self, 'see_more_btn') and self.see_more_btn:
            self.see_more_btn.setStyleSheet(f"""
                QPushButton#SeeMoreTasksBtn {{
                    background-color: transparent;
                    color: {'#a1a1aa' if d else '#64748b'};
                    border: 1px dashed {'#3f3f46' if d else '#cbd5e1'};
                    border-radius: 6px;
                    text-align: center;
                    padding: 0 8px;
                    margin: 4px 6px 8px 6px;
                    font-size: 11.5px;
                    font-family: 'PingFang SC', 'Microsoft YaHei UI', -apple-system, sans-serif;
                    font-weight: 500;
                }}
                QPushButton#SeeMoreTasksBtn:hover {{
                    background-color: {'#27272a' if d else '#f1f5f9'};
                    color: {'#ffffff' if d else '#0f172a'};
                    border: 1px solid {'#6366f1' if d else '#4f46e5'};
                }}
            """)

        # ── 设置页面：用户信息与大模型记忆卡片动态主题（彻底解决白主题下为黑色的问题）──
        if hasattr(self, 'user_card') and self.user_card:
            u_bg = '#27272a' if d else '#ffffff'
            u_border = '#3f3f46' if d else '#e2e8f0'
            u_edit_bg = '#18181b' if d else '#ffffff'
            u_edit_border = '#3f3f46' if d else '#cbd5e1'
            u_edit_fg = '#f4f4f5' if d else '#0f172a'
            u_title_fg = '#f4f4f5' if d else '#0f172a'
            u_sub_fg = '#a1a1aa' if d else '#64748b'

            self.user_card.setStyleSheet(f"""
                QFrame#UserProfileCard {{
                    background-color: {u_bg};
                    border: 1px solid {u_border};
                    border-radius: 12px;
                }}
            """)
            if hasattr(self, 'user_info_title'):
                self.user_info_title.setStyleSheet(
                    f"color: {u_title_fg}; font-size: 14px; font-weight: 600; "
                    f"font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif; "
                    f"background: transparent;"
                )
            if hasattr(self, 'rules_lbl'):
                self.rules_lbl.setStyleSheet(
                    f"color: {u_sub_fg}; font-size: 12px; font-weight: 600; "
                    f"font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif; "
                    f"background: transparent;"
                )
            edit_style = f"""
                QLineEdit {{
                    background-color: {u_edit_bg};
                    color: {u_edit_fg};
                    border: 1px solid {u_edit_border};
                    border-radius: 8px;
                    padding: 0 12px;
                    font-size: 13px;
                    font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
                }}
                QLineEdit:focus {{ border: 1px solid #6366f1; }}
            """
            if hasattr(self, 'user_name_edit'):
                self.user_name_edit.setStyleSheet(edit_style)
            if hasattr(self, 'user_memo_edit'):
                self.user_memo_edit.setStyleSheet(edit_style)
            if hasattr(self, 'user_rules_edit'):
                self.user_rules_edit.setStyleSheet(f"""
                    QTextEdit {{
                        background-color: {u_edit_bg};
                        color: {u_edit_fg};
                        border: 1px solid {u_edit_border};
                        border-radius: 8px;
                        padding: 8px 12px;
                        font-size: 12.5px;
                        line-height: 1.45;
                        font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
                    }}
                    QTextEdit:focus {{ border: 1px solid #6366f1; }}
                """)
            if hasattr(self, 'upload_btn'):
                self.upload_btn.setIcon(load_ui_icon("upload", u_sub_fg, 14))
                self.upload_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {'#18181b' if d else '#f1f5f9'};
                        color: {'#f4f4f5' if d else '#334155'};
                        border: 1px solid {u_edit_border};
                        border-radius: 8px;
                        padding: 0 16px;
                        font-size: 12px;
                        font-weight: 500;
                        font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
                    }}
                    QPushButton:hover {{
                        background-color: {'#27272a' if d else '#e2e8f0'};
                        border: 1px solid #6366f1;
                    }}
                """)
            if hasattr(self, 'settings_head'):
                self.settings_head.setStyleSheet(f"color: {'#ffffff' if d else '#0f172a'}; font-family: 'Microsoft YaHei UI'; background: transparent;")
            if hasattr(self, 'edit_head'):
                self.edit_head.setStyleSheet(f"color: {'#ffffff' if d else '#0f172a'}; font-family: 'Microsoft YaHei UI'; background: transparent;")
            if hasattr(self, 'settings_scroll'):
                self.settings_scroll.setStyleSheet(f"""
                    QScrollArea {{ background: transparent; border: none; }}
                    QScrollArea > QWidget > QWidget {{ background: transparent; }}
                    {scrollbar_style}
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
                    border: 1px solid {'#2e2e2e' if d else '#cbd5e1'};
                    border-radius: 8px;
                    padding: 0 10px;
                    font-size: 12.5px;
                    font-family: 'Microsoft YaHei UI';
                    selection-background-color: {'#3b3b40' if d else '#c7d2fe'};
                    selection-color: {'#ffffff' if d else '#1e1b4b'};
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
                    border: 1px solid {'#2e2e2e' if d else '#cbd5e1'};
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
            # 测试按钮：胶囊 + search 图标（双主题）
            self.test_btn.setText("  测试连接")
            self.test_btn.setIcon(load_ui_icon("search", sub_fg, 14))
            self.test_btn.setIconSize(QSize(14, 14))
            self.test_btn.setStyleSheet(
                f"QPushButton{{background:{'#27272a' if d else '#f1f5f9'};color:{fg};border:none;border-radius:8px;"
                f"padding:0 16px;font-size:12.5px;font-weight:600;font-family:'Microsoft YaHei UI';}}"
                f"QPushButton:hover{{background:{hover};}}"
            )
        if hasattr(self, 'save_curr_btn'):
            # 保存按钮：主色填充 + check 图标（双主题反色）
            self.save_curr_btn.setText("  保存为当前模型")
            self.save_curr_btn.setIcon(load_ui_icon("check", '#0f172a' if d else '#ffffff', 14))
            self.save_curr_btn.setIconSize(QSize(14, 14))
            self.save_curr_btn.setStyleSheet(
                f"QPushButton{{background:{'#ffffff' if d else '#6366f1'};color:{'#0f172a' if d else '#ffffff'};border:none;border-radius:8px;"
                f"padding:0 16px;font-size:12.5px;font-weight:600;font-family:'Microsoft YaHei UI';}}"
                f"QPushButton:hover{{background:{'#e4e4e7' if d else '#4f46e5'};}}"
            )
        if hasattr(self, 'tpl_head'):
            self.tpl_head.setStyleSheet(f"color:{fg};font-size:13px;font-weight:bold;font-family:'Microsoft YaHei UI';")
        if hasattr(self, 'log_head'):
            self.log_head.setStyleSheet(f"color:{fg};font-size:13px;font-weight:bold;font-family:'Microsoft YaHei UI';")
        if hasattr(self, 'clear_log_btn'):
            self.clear_log_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#27272a' if d else '#f1f5f9'};
                    color: {'#a1a1aa' if d else '#64748b'};
                    border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                    border-radius: 6px;
                    padding: 0 12px;
                    font-size: 12px;
                    font-family: 'Microsoft YaHei UI';
                }}
                QPushButton:hover {{
                    background: {'#3f3f46' if d else '#e2e8f0'};
                    color: {'#ef4444' if d else '#dc2626'};
                    border-color: {'#ef4444' if d else '#dc2626'};
                }}
            """)

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
        # 快捷指令 chips 主题同步
        for _chip in getattr(self, '_quick_chips_hero', []) + getattr(self, '_quick_chips_active', []):
            self._style_quick_chip(_chip)
        if hasattr(self, 'pet_window') and self.pet_window:
            if hasattr(self.pet_window, 'set_theme'):
                self.pet_window.set_theme(self._is_dark)
        self._update_pet_btn_state()
        self._update_sound_btn_state()
        if hasattr(self, 'status_lbl'):
            self.status_lbl.setStyleSheet(f"color:{'#a1a1aa' if self._is_dark else '#64748b'};font-size:11px;font-family:'Microsoft YaHei UI';")
        if hasattr(self, 'hero_plan_mode_btn'):
            self._update_plan_btn_style(self.hero_plan_mode_btn, self.hero_plan_mode_btn.isChecked())
        if hasattr(self, 'active_plan_mode_btn'):
            self._update_plan_btn_style(self.active_plan_mode_btn, self.active_plan_mode_btn.isChecked())
        for b in getattr(self, '_message_blocks', []):
            if hasattr(b, 'plan_card') and b.plan_card:
                b.plan_card.set_dark(d)
            # 已深度思考折叠卡片——切主题时刷新样式（之前一次性 setStyleSheet 没刷新导致字看不清）
            if hasattr(b, 'thought_accordion') and b.thought_accordion:
                if hasattr(b.thought_accordion, 'apply_theme'):
                    try:
                        b.thought_accordion.apply_theme(d)
                    except Exception:
                        pass
        # 同步双模式切换胶囊样式
        self._update_mode_capsule_style()
        # 同步侧边导航按钮（之前 nav_btns 一直没 setStyleSheet，light 主题下字极淡看不清）
        if hasattr(self, 'nav_btns') and self.nav_btns:
            nav_bg_dark = "transparent"
            nav_bg_light = "transparent"
            nav_fg_dark = '#a1a1aa'
            nav_fg_light = '#1f2328'
            nav_fg_active_dark = '#ffffff'
            nav_fg_active_light = '#1d4ed8'
            nav_bg_active_dark = '#312e81'
            nav_bg_active_light = '#dbeafe'
            nav_border_dark = '#3f3f46'
            nav_border_light = '#cbd5e1'
            nav_fg = nav_fg_dark if d else nav_fg_light
            nav_fg_active = nav_fg_active_dark if d else nav_fg_active_light
            nav_bg_active = nav_bg_active_dark if d else nav_bg_active_light
            nav_border = nav_border_dark if d else nav_border_light
            for btn in self.nav_btns:
                try:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: transparent;
                            color: {nav_fg};
                            border: none;
                            border-radius: 6px;
                            padding: 0 10px;
                            text-align: left;
                            font-size: 12.5px;
                            font-family: 'Microsoft YaHei UI';
                        }}
                        QPushButton:hover {{
                            background: {'#27272a' if d else '#f1f5f9'};
                        }}
                        QPushButton:checked {{
                            background: {nav_bg_active};
                            color: {nav_fg_active};
                            border: 1px solid {nav_border};
                            font-weight: bold;
                        }}
                    """)
                except Exception:
                    pass
        # 同步 Dev 代码开发模式主视图主题 (全量重绘编辑器、资源管理器、控制台与AI面板)
        if hasattr(self, 'dev_mode_view') and self.dev_mode_view:
            if hasattr(self.dev_mode_view, 'apply_theme'):
                self.dev_mode_view.apply_theme(d)

        # 同步 sidebar_title（之前是局部变量 _init_ui 创建时一次性 setStyleSheet，
        # 运行时切主题没刷导致 dark 主题下仍显示 light 主题的深蓝色字）
        if hasattr(self, 'sidebar_title') and self.sidebar_title is not None:
            try:
                title_color = '#e4e4e7' if d else '#1e293b'
                self.sidebar_title.setStyleSheet(
                    f"color: {title_color}; font-size: 12px; font-weight: bold; font-family: 'Microsoft YaHei UI'; background: transparent; border: none;"
                )
            except Exception:
                pass

    def _style_quick_chip(self, btn: QPushButton):
        d = self._is_dark
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {'#27272a' if d else '#f1f5f9'};
                color: {'#a1a1aa' if d else '#475569'};
                border: 1px solid {'#3f3f46' if d else '#e2e8f0'};
                border-radius: 12px;
                padding: 0 12px;
                font-size: 11.5px;
                font-family: 'Microsoft YaHei UI';
            }}
            QPushButton:hover {{
                background: {'#3f3f46' if d else '#e2e8f0'};
                color: {'#ffffff' if d else '#0f172a'};
            }}
        """)

    def _make_quick_chip(self, text: str, target_edit) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(24)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip(f"快速指令：{text}")
        self._style_quick_chip(btn)
        btn.clicked.connect(lambda: self._apply_quick_prompt(target_edit, text))
        return btn

    def _apply_quick_prompt(self, edit, text: str):
        prefix_map = {
            "写代码": "请帮我写代码：",
            "翻译": "请帮我翻译：",
            "总结": "请帮我总结：",
        }
        prefix = prefix_map.get(text, f"请帮我{text}：")
        edit.setPlainText(prefix)
        edit.setFocus()
        cursor = edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        edit.setTextCursor(cursor)

    def _switch_nav(self, index: int):
        self.main_stack.setCurrentIndex(index)
        d = self._is_dark
        on  = ("QPushButton{background:%s;color:%s;font-weight:bold;border-radius:9px;"
               "text-align:left;padding-left:14px;font-size:13px;border:none;"
               "font-family:'Microsoft YaHei UI';}") % (
                    "#27272a" if d else "#e0e7ff",
                    "#ffffff" if d else "#3730a3"
               )
        off = ("QPushButton{background:transparent;color:%s;border:none;border-radius:9px;"
               "text-align:left;padding-left:14px;font-size:13px;font-weight:500;"
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
        elif index == 1:
            # 切入【专家·技能大厅】时，若窗口尺寸曾变动则按需极速重排
            if getattr(self, '_grid_needs_relayout', False):
                self._grid_needs_relayout = False
                self._check_and_update_grid_cols()
        elif index == 3:
            self._load_active_model_into_form()
            self._refresh_model_cards()

    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        self.config["ui_theme"] = "dark" if self._is_dark else "light"
        if self.save_config_fn:
            self.save_config_fn(self.config)
        self._apply_theme()
        if hasattr(self, 'pet_window') and self.pet_window:
            if hasattr(self.pet_window, 'set_theme'):
                self.pet_window.set_theme(self._is_dark)

    def _toggle_maximize(self):
        _ic = "#a1a1aa" if self._is_dark else "#64748b"
        try:
            screen = self.windowHandle().screen() if self.windowHandle() else QApplication.primaryScreen()
            avail = screen.availableGeometry() if screen else QApplication.primaryScreen().availableGeometry()
        except Exception:
            avail = QRect(0, 0, 1920, 1080)

        # 停止可能遗留的动画避免冲突
        if hasattr(self, '_geom_anim'):
            try:
                self._geom_anim.stop()
            except Exception:
                pass

        # 核心优化：暂停界面更新，将边距、阴影及几何变换合并为单帧原子提交，彻底消除抽搐闪烁与拖尾
        self.setUpdatesEnabled(False)
        try:
            if not self._is_maximized:
                # 记录当前常规窗口精准坐标与尺寸，用于还原时 1:1 归位
                cur_g = self.geometry()
                self._normal_rect = QRect(cur_g)

                if hasattr(self, 'root_layout'):
                    self.root_layout.setContentsMargins(0, 0, 0, 0)
                if hasattr(self, 'main_frame_shadow'):
                    self.main_frame_shadow.setEnabled(False)

                self.setGeometry(avail)
                self._is_maximized = True
                self.max_btn.setIcon(load_ui_icon("square-restore", _ic, 16))
                self.max_btn.setIconSize(QSize(16, 16))
            else:
                # 缩小还原：优先精准恢复至放大前用户放置的位置；若脱离屏幕可视区则安全居中
                target_rect = getattr(self, '_normal_rect', None)
                if (not target_rect or 
                    target_rect.width() >= avail.width() or 
                    target_rect.height() >= avail.height() or
                    not avail.intersects(target_rect)):
                    norm_w = min(1050, int(avail.width() * 0.82))
                    norm_h = min(700, int(avail.height() * 0.85))
                    center_x = avail.x() + (avail.width() - norm_w) // 2
                    center_y = avail.y() + (avail.height() - norm_h) // 2
                    target_rect = QRect(center_x, center_y, norm_w, norm_h)

                if hasattr(self, 'root_layout'):
                    self.root_layout.setContentsMargins(8, 8, 8, 8)
                if hasattr(self, 'main_frame_shadow'):
                    self.main_frame_shadow.setEnabled(True)

                self.setGeometry(target_rect)
                self._is_maximized = False
                self.max_btn.setIcon(load_ui_icon("square", _ic, 16))
                self.max_btn.setIconSize(QSize(16, 16))
        finally:
            self.setUpdatesEnabled(True)

        # 立即更新拉伸句柄状态（全屏时自动隐藏，还原后就绪）
        self._layout_resize_handles()

    def open_settings(self):
        self.show(); self.raise_(); self.activateWindow()
        self._switch_nav(3)
