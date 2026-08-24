# -*- coding: utf-8 -*-
"""
AI 智能对话中枢 - 顶层四角手柄(0误触/100%原生缩放)、输入框边距修正、任务栏最小化、零延迟切换与模型自动扫描
"""
import sys
import json
import asyncio
import threading
import ctypes
import ctypes.wintypes
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QLineEdit, QTextEdit, QScrollArea, QFrame,
        QApplication, QStackedWidget,
        QComboBox, QFormLayout, QListWidget, QListWidgetItem,
        QRadioButton, QButtonGroup, QMessageBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QTimer, QSize, QRect
    from PyQt5.QtGui import QFont, QColor, QIcon, QPainter, QPixmap, QCursor
except ImportError:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QLineEdit, QTextEdit, QScrollArea, QFrame,
        QApplication, QStackedWidget,
        QComboBox, QFormLayout, QListWidget, QListWidgetItem,
        QRadioButton, QButtonGroup, QMessageBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer, QSize, QRect
    from PyQt6.QtGui import QFont, QColor, QIcon, QPainter, QPixmap, QCursor

ROOT_DIR = Path(__file__).parent.parent
ICON_PATH = ROOT_DIR / "assets" / "icons" / "pet_icon.png"

# Windows SC_SIZE 方向参数
SC_SIZE_TOPLEFT = 0xF004
SC_SIZE_TOPRIGHT = 0xF005
SC_SIZE_BOTTOMLEFT = 0xF007
SC_SIZE_BOTTOMRIGHT = 0xF008
CORNER_GRIP_SIZE = 22  # 四个角落手柄大小 (像素)


class CornerResizeHandle(QWidget):
    """置于最顶层的透明角落缩放手柄，解决所有子控件遮挡与光标错乱问题"""
    def __init__(self, parent, corner: str):
        super().__init__(parent)
        self.corner = corner  # "TL", "TR", "BL", "BR"
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        if corner in ("TL", "BR"):
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.SizeBDiagCursor)

    def mousePressEvent(self, event):
        parent = self.parent()
        if event.button() == Qt.LeftButton and parent and not parent._is_maximized:
            try:
                hwnd = int(parent.winId())
                ctypes.windll.user32.ReleaseCapture()
                cmd_map = {
                    "TL": SC_SIZE_TOPLEFT,
                    "TR": SC_SIZE_TOPRIGHT,
                    "BL": SC_SIZE_BOTTOMLEFT,
                    "BR": SC_SIZE_BOTTOMRIGHT,
                }
                cmd = cmd_map.get(self.corner, SC_SIZE_BOTTOMRIGHT)
                # 触发 Windows 系统原生缩放循环
                ctypes.windll.user32.SendMessageW(hwnd, 0x0112, cmd, 0)
                event.accept()
                return
            except Exception:
                pass
        super().mousePressEvent(event)


class MessageBubble(QWidget):
    """现代流式消息气泡"""
    def __init__(self, sender: str, text: str):
        super().__init__()
        self.sender = sender
        self.raw_text = text
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(10)

        self.label = QLabel(self.raw_text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setFont(QFont("Microsoft YaHei UI", 10))

        if self.sender == "user":
            layout.addStretch()
            self.label.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7c3aed, stop:1 #9333ea);
                    color: #ffffff;
                    border-radius: 14px;
                    border-bottom-right-radius: 2px;
                    padding: 9px 15px;
                    font-size: 13px;
                }
            """)
            layout.addWidget(self.label)
        else:
            self.label.setStyleSheet("""
                QLabel {
                    background-color: #252044;
                    color: #f3f0ff;
                    border: 1px solid #43396f;
                    border-radius: 14px;
                    border-bottom-left-radius: 2px;
                    padding: 11px 16px;
                    font-size: 13px;
                    line-height: 1.5;
                }
            """)
            layout.addWidget(self.label)
            layout.addStretch()

    def set_text(self, text: str):
        try:
            self.raw_text = text
            if hasattr(self, 'label') and self.label:
                self.label.setText(text)
                self.label.adjustSize()
        except (RuntimeError, Exception):
            pass


class ChatWindow(QWidget):
    message_chunk_signal = pyqtSignal(int, str)
    message_done_signal = pyqtSignal(int, str)
    message_error_signal = pyqtSignal(int, str)
    model_scanned_signal = pyqtSignal(list)

    def __init__(self, config: dict, ai_engine, voice_input=None, voice_output=None, pet_window=None, save_config_fn=None):
        super().__init__()
        self.config = config
        self.ai_engine = ai_engine
        self.pet_window = pet_window
        self.save_config_fn = save_config_fn
        self.memory = getattr(ai_engine, 'memory', None)

        self._is_generating = False
        self._is_maximized = False
        self._normal_geometry = None
        self._current_ai_bubble = None
        self._current_session_id = None
        self._stream_id = 0
        self._drag_pos = None

        pet_name = self.config.get("behavior", {}).get("pet_name", "桃濑日和")
        self.setWindowTitle(f"{pet_name} · AI 对话中枢")

        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self._init_window()
        self._build_ui()
        self._create_corner_grips()
        self._connect_signals()
        self._init_or_load_latest_session()

        QTimer.singleShot(100, self._scan_ollama_models_async)

    def _init_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Window |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowSystemMenuHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(540, 690)
        self.setMinimumSize(420, 500)

        try:
            hwnd = int(self.winId())
            GWL_STYLE = -16
            WS_MINIMIZEBOX = 0x00020000
            WS_SYSMENU = 0x00080000
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_MINIMIZEBOX | WS_SYSMENU)
        except Exception:
            pass

    def _create_corner_grips(self):
        """创建4个置顶透明角落手柄"""
        self.grip_tl = CornerResizeHandle(self, "TL")
        self.grip_tr = CornerResizeHandle(self, "TR")
        self.grip_bl = CornerResizeHandle(self, "BL")
        self.grip_br = CornerResizeHandle(self, "BR")
        self._update_corner_grips_geometry()

    def _update_corner_grips_geometry(self):
        if not hasattr(self, 'grip_tl'):
            return
        w = self.width()
        h = self.height()
        c = CORNER_GRIP_SIZE

        self.grip_tl.setGeometry(0, 0, c, c)
        self.grip_tr.setGeometry(w - c, 0, c, c)
        self.grip_bl.setGeometry(0, h - c, c, c)
        self.grip_br.setGeometry(w - c, h - c, c, c)

        # 始终保持在所有子控件之上
        self.grip_tl.raise_()
        self.grip_tr.raise_()
        self.grip_bl.raise_()
        self.grip_br.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_corner_grips_geometry()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)

        self.card = QFrame()
        self.card.setStyleSheet("""
            QFrame#MainCard {
                background-color: #18152a;
                border: 1px solid #483d73;
                border-radius: 14px;
            }
        """)
        self.card.setObjectName("MainCard")

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        self.top_bar = self._create_topbar()
        card_layout.addWidget(self.top_bar)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #18152a;")

        self.chat_page = self._create_chat_page()
        self.stack.addWidget(self.chat_page)

        self.history_page = self._create_history_page()
        self.stack.addWidget(self.history_page)

        self.settings_page = self._create_settings_page()
        self.stack.addWidget(self.settings_page)

        card_layout.addWidget(self.stack, 1)

        self.bottom_bar = self._create_bottom_bar()
        card_layout.addWidget(self.bottom_bar)

        main_layout.addWidget(self.card)

    def _create_topbar(self):
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet("""
            QFrame {
                background-color: #201c38;
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
                border-bottom: 1px solid #372f5d;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(8)

        avatar = QLabel("🌸")
        avatar.setFont(QFont("Segoe UI Emoji", 15))
        layout.addWidget(avatar)

        pet_name = self.config.get("behavior", {}).get("pet_name", "桃濑日和")
        self.title_lbl = QLabel(f"{pet_name} · AI 对话中枢")
        self.title_lbl.setStyleSheet("color: #f3f0ff; font-weight: bold; font-size: 13px; font-family: 'Microsoft YaHei UI';")
        layout.addWidget(self.title_lbl)

        layout.addStretch()

        self.btn_style_normal = """
            QPushButton {
                background-color: #2b254a;
                color: #d6ceff;
                border: 1px solid #43396f;
                border-radius: 7px;
                padding: 4px 10px;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }
            QPushButton:hover {
                background-color: #3c3468;
                color: #ffffff;
            }
        """
        self.btn_style_active = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #9333ea);
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #a855f7;
                border-radius: 7px;
                padding: 4px 10px;
                font-size: 12px;
                font-family: 'Microsoft YaHei UI';
            }
        """

        self.nav_chat_btn = QPushButton("💬 对话")
        self.nav_chat_btn.setStyleSheet(self.btn_style_active)
        self.nav_chat_btn.clicked.connect(lambda: self._switch_view(0))
        layout.addWidget(self.nav_chat_btn)

        self.nav_history_btn = QPushButton("📜 历史")
        self.nav_history_btn.setStyleSheet(self.btn_style_normal)
        self.nav_history_btn.clicked.connect(lambda: self._switch_view(1))
        layout.addWidget(self.nav_history_btn)

        self.nav_settings_btn = QPushButton("⚙️ 设置")
        self.nav_settings_btn.setStyleSheet(self.btn_style_normal)
        self.nav_settings_btn.clicked.connect(lambda: self._switch_view(2))
        layout.addWidget(self.nav_settings_btn)

        clear_btn = QPushButton("🧹 清空")
        clear_btn.setStyleSheet(self.btn_style_normal)
        clear_btn.clicked.connect(self._clear_current_chat)
        layout.addWidget(clear_btn)

        self.max_btn = QPushButton("⤢")
        self.max_btn.setFixedSize(26, 26)
        self.max_btn.setStyleSheet(self.btn_style_normal)
        self.max_btn.clicked.connect(self._toggle_maximize)
        layout.addWidget(self.max_btn)

        min_btn = QPushButton("—")
        min_btn.setFixedSize(26, 26)
        min_btn.setStyleSheet(self.btn_style_normal)
        min_btn.clicked.connect(self.showMinimized)
        layout.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a1a28;
                color: #ff99aa;
                border: 1px solid #6b283d;
                border-radius: 7px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #e11d48;
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.hide)
        layout.addWidget(close_btn)

        return bar

    def _create_chat_page(self):
        page = QFrame()
        page.setStyleSheet("background-color: #18152a; border: none;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #18152a;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #43396f;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #7c3aed;
            }
        """)

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: #18152a;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(14, 14, 14, 14)
        self.chat_layout.setSpacing(10)
        self.chat_layout.addStretch()

        self.scroll_area.setWidget(self.chat_container)
        layout.addWidget(self.scroll_area)
        return page

    def _create_history_page(self):
        page = QFrame()
        page.setStyleSheet("background-color: #18152a; border: none;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        top_h = QHBoxLayout()
        h_title = QLabel("📜 历史会话管理")
        h_title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: bold; font-family: 'Microsoft YaHei UI';")
        top_h.addWidget(h_title)
        top_h.addStretch()

        new_sess_btn = QPushButton("+ 新建会话")
        new_sess_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #9333ea);
                color: #ffffff;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
            }
            QPushButton:hover { background: #9333ea; }
        """)
        new_sess_btn.clicked.connect(self._create_new_session_action)
        top_h.addWidget(new_sess_btn)
        layout.addLayout(top_h)

        self.session_list = QListWidget()
        self.session_list.setStyleSheet("""
            QListWidget {
                background-color: #201c38;
                border: 1px solid #372f5d;
                border-radius: 10px;
                padding: 6px;
                color: #f1edff;
                font-family: 'Microsoft YaHei UI';
                font-size: 13px;
            }
            QListWidget::item {
                background-color: #272244;
                border: 1px solid #3d3568;
                border-radius: 8px;
                padding: 10px 14px;
                margin: 4px 0;
            }
            QListWidget::item:hover {
                background-color: #352d5b;
                border-color: #7c3aed;
            }
            QListWidget::item:selected {
                background-color: #4c2889;
                border: 1px solid #a855f7;
                color: #ffffff;
            }
        """)
        self.session_list.itemClicked.connect(self._on_session_item_clicked)
        layout.addWidget(self.session_list, 1)

        bot_h = QHBoxLayout()
        del_sess_btn = QPushButton("🗑️ 删除选中会话")
        del_sess_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a1a28;
                color: #ff99aa;
                border: 1px solid #6b283d;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #e11d48; color: #fff; }
        """)
        del_sess_btn.clicked.connect(self._delete_selected_session)
        bot_h.addWidget(del_sess_btn)

        bot_h.addStretch()

        back_to_chat_btn = QPushButton("返回对话")
        back_to_chat_btn.setStyleSheet(self.btn_style_normal)
        back_to_chat_btn.clicked.connect(lambda: self._switch_view(0))
        bot_h.addWidget(back_to_chat_btn)

        layout.addLayout(bot_h)
        return page

    def _create_settings_page(self):
        page = QFrame()
        page.setStyleSheet("background-color: #18152a; border: none;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        title = QLabel("⚙️ 桌面助理 · 内置模型与服务配置")
        title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: bold; font-family: 'Microsoft YaHei UI';")
        layout.addWidget(title)

        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #201c38;
                border: 1px solid #372f5d;
                border-radius: 12px;
                padding: 14px;
            }
            QLabel {
                color: #d6ceff;
                font-size: 13px;
                font-family: 'Microsoft YaHei UI';
            }
            QLineEdit, QComboBox {
                background-color: #282346;
                color: #ffffff;
                border: 1px solid #483d73;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                font-family: 'Microsoft YaHei UI';
            }
            QComboBox QAbstractItemView {
                background-color: #252042;
                color: #ffffff;
                selection-background-color: #7c3aed;
                selection-color: #ffffff;
                border: 1px solid #483d73;
                padding: 4px;
            }
            QRadioButton {
                color: #eae6ff;
                font-size: 13px;
                font-family: 'Microsoft YaHei UI';
                spacing: 6px;
            }
        """)
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(10)

        # 助理昵称
        self.cfg_name_edit = QLineEdit(self.config.get("behavior", {}).get("pet_name", "桃濑日和"))
        form_layout.addRow("🌸 助理昵称：", self.cfg_name_edit)

        # AI 来源单选
        provider_box = QHBoxLayout()
        self.rb_ollama = QRadioButton("🦙 本地 Ollama")
        self.rb_custom = QRadioButton("🌐 外部云端 API (DeepSeek/OpenAI)")
        
        current_provider = self.config.get("ai", {}).get("provider", "ollama")
        if current_provider == "custom" or current_provider == "openai":
            self.rb_custom.setChecked(True)
        else:
            self.rb_ollama.setChecked(True)

        self.rb_ollama.toggled.connect(self._on_provider_changed)
        provider_box.addWidget(self.rb_ollama)
        provider_box.addWidget(self.rb_custom)
        form_layout.addRow("🔌 AI 引擎来源：", provider_box)

        # ── Ollama 配置区 ──
        self.ollama_group = QWidget()
        self.ollama_group.setStyleSheet("background: transparent;")
        ollama_layout = QFormLayout(self.ollama_group)
        ollama_layout.setContentsMargins(0, 0, 0, 0)
        ollama_layout.setSpacing(8)

        self.cfg_ollama_url = QLineEdit(self.config.get("ai", {}).get("ollama", {}).get("base_url", "http://localhost:11434"))
        ollama_layout.addRow("🌐 服务地址：", self.cfg_ollama_url)

        model_h = QHBoxLayout()
        self.cfg_ollama_model = QComboBox()
        self.cfg_ollama_model.setEditable(True)
        cur_ollama_m = self.config.get("ai", {}).get("ollama", {}).get("chat_model", "")
        if cur_ollama_m:
            self.cfg_ollama_model.addItem(cur_ollama_m)
            self.cfg_ollama_model.setCurrentText(cur_ollama_m)

        model_h.addWidget(self.cfg_ollama_model, 1)

        self.scan_btn = QPushButton("🔄 扫描本地模型")
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #4c2889;
                color: #ffffff;
                border: 1px solid #7c3aed;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #6d28d9; }
            QPushButton:disabled { background-color: #322352; color: #8d7faf; }
        """)
        self.scan_btn.clicked.connect(self._scan_ollama_models_async)
        model_h.addWidget(self.scan_btn)
        ollama_layout.addRow("🤖 本地模型：", model_h)

        form_layout.addRow(self.ollama_group)

        # ── 外部 API 配置区 ──
        self.custom_group = QWidget()
        self.custom_group.setStyleSheet("background: transparent;")
        custom_layout = QFormLayout(self.custom_group)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.setSpacing(8)

        self.cfg_custom_url = QLineEdit(self.config.get("ai", {}).get("custom", {}).get("api_base", "https://api.deepseek.com/v1"))
        self.cfg_custom_url.setPlaceholderText("例如: https://api.deepseek.com/v1 或 OpenAI 兼容地址")
        custom_layout.addRow("🔗 API 地址：", self.cfg_custom_url)

        self.cfg_custom_key = QLineEdit(self.config.get("ai", {}).get("custom", {}).get("api_key", ""))
        self.cfg_custom_key.setEchoMode(QLineEdit.Password)
        self.cfg_custom_key.setPlaceholderText("sk-xxxxxxxxxxxxxxxxxxxxxxxx")
        custom_layout.addRow("🔑 API Key：", self.cfg_custom_key)

        self.cfg_custom_model = QLineEdit(self.config.get("ai", {}).get("custom", {}).get("chat_model", "deepseek-chat"))
        self.cfg_custom_model.setPlaceholderText("例如: deepseek-chat, deepseek-reasoner, gpt-4o")
        custom_layout.addRow("🧠 模型名称：", self.cfg_custom_model)

        form_layout.addRow(self.custom_group)

        self._update_provider_ui()
        layout.addWidget(form_frame)

        layout.addStretch()

        btn_h = QHBoxLayout()
        btn_h.addStretch()

        back_btn = QPushButton("返回对话")
        back_btn.setStyleSheet(self.btn_style_normal)
        back_btn.clicked.connect(lambda: self._switch_view(0))
        btn_h.addWidget(back_btn)

        save_btn = QPushButton("💾 保存并应用设置")
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #9333ea);
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 8px 22px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9333ea, stop:1 #a855f7);
            }
        """)
        save_btn.clicked.connect(self._save_settings)
        btn_h.addWidget(save_btn)

        layout.addLayout(btn_h)
        return page

    def _create_bottom_bar(self):
        bar = QFrame()
        bar.setFixedHeight(58)
        bar.setStyleSheet("""
            QFrame {
                background-color: #201c38;
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
                border-top: 1px solid #372f5d;
            }
        """)
        layout = QHBoxLayout(bar)
        # 左右预留 24px 边距，彻底阻绝左下角输入光标冲突
        layout.setContentsMargins(24, 8, 24, 8)
        layout.setSpacing(10)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("和你的 AI 智能助理说点什么吧... (Enter 发送)")
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background-color: #282346;
                color: #ffffff;
                border: 1px solid #483d73;
                border-radius: 18px;
                padding: 0 16px;
                font-size: 13px;
                font-family: 'Microsoft YaHei UI';
                height: 36px;
            }
            QLineEdit:focus {
                border: 1px solid #a855f7;
                background-color: #2e2850;
            }
        """)
        self.input_edit.returnPressed.connect(self._send_message)
        layout.addWidget(self.input_edit, 1)

        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedHeight(36)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #9333ea);
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                border: none;
                border-radius: 18px;
                padding: 0 20px;
                font-family: 'Microsoft YaHei UI';
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9333ea, stop:1 #a855f7);
            }
            QPushButton:disabled {
                background-color: #372f5d;
                color: #716999;
            }
        """)
        self.send_btn.clicked.connect(self._send_message)
        layout.addWidget(self.send_btn)

        return bar

    def _switch_view(self, index: int):
        self.stack.setCurrentIndex(index)

        self.nav_chat_btn.setStyleSheet(self.btn_style_active if index == 0 else self.btn_style_normal)
        self.nav_history_btn.setStyleSheet(self.btn_style_active if index == 1 else self.btn_style_normal)
        self.nav_settings_btn.setStyleSheet(self.btn_style_active if index == 2 else self.btn_style_normal)

        if index == 0:
            self.bottom_bar.show()
            self.input_edit.setFocus()
        else:
            self.bottom_bar.hide()
            if index == 1:
                self._refresh_history_list()

        # 每次切换后确保角落手柄始终置顶
        self._update_corner_grips_geometry()

    def open_settings(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self._switch_view(2)

    def _on_provider_changed(self):
        self._update_provider_ui()

    def _update_provider_ui(self):
        is_ollama = self.rb_ollama.isChecked()
        self.ollama_group.setVisible(is_ollama)
        self.custom_group.setVisible(not is_ollama)

    def _scan_ollama_models_async(self):
        url = self.cfg_ollama_url.text().strip() or "http://localhost:11434"
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("⏳ 正在扫描...")

        def _worker():
            from core.ai_engine import list_ollama_models
            models = list_ollama_models(url)
            self.model_scanned_signal.emit(models)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_models_scanned(self, models: list):
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("🔄 重新扫描")

        self.cfg_ollama_model.clear()
        if models:
            self.cfg_ollama_model.addItems(models)
            saved_m = self.config.get("ai", {}).get("ollama", {}).get("chat_model", "")
            if saved_m in models:
                self.cfg_ollama_model.setCurrentText(saved_m)
            else:
                self.cfg_ollama_model.setCurrentIndex(0)
        else:
            self.cfg_ollama_model.addItem("未检测到本地模型(请先在Ollama运行pull)")

    def _save_settings(self):
        new_name = self.cfg_name_edit.text().strip() or "桃濑日和"
        is_ollama = self.rb_ollama.isChecked()
        provider = "ollama" if is_ollama else "custom"

        self.config.setdefault("behavior", {})["pet_name"] = new_name
        self.config.setdefault("ai", {})["provider"] = provider

        if is_ollama:
            new_url = self.cfg_ollama_url.text().strip() or "http://localhost:11434"
            new_model = self.cfg_ollama_model.currentText().strip()
            self.config.setdefault("ai", {}).setdefault("ollama", {})["base_url"] = new_url
            self.config.setdefault("ai", {}).setdefault("ollama", {})["chat_model"] = new_model
        else:
            new_url = self.cfg_custom_url.text().strip() or "https://api.deepseek.com/v1"
            new_key = self.cfg_custom_key.text().strip()
            new_model = self.cfg_custom_model.text().strip() or "deepseek-chat"
            self.config.setdefault("ai", {}).setdefault("custom", {})["api_base"] = new_url
            self.config.setdefault("ai", {}).setdefault("custom", {})["api_key"] = new_key
            self.config.setdefault("ai", {}).setdefault("custom", {})["chat_model"] = new_model

        if self.save_config_fn:
            self.save_config_fn(self.config)

        if self.ai_engine:
            self.ai_engine.reload_config(self.config)

        self.title_lbl.setText(f"{new_name} · AI 对话中枢")
        self.setWindowTitle(f"{new_name} · AI 对话中枢")
        self._switch_view(0)
        self._add_message_bubble("ai", f"✨ 设置已成功保存并立即生效！当前引擎：`{provider}`，模型：`{self.config.get('ai', {}).get(provider, {}).get('chat_model', '')}`")

    # ── 历史会话管理 ──
    def _init_or_load_latest_session(self):
        if not self.memory:
            self._load_welcome_bubble()
            return

        sessions = self.memory.get_all_sessions()
        if sessions:
            self._load_session(sessions[0]["id"])
        else:
            self._create_new_session_action()

    def _create_new_session_action(self):
        if self.memory:
            sid = self.memory.create_session("新会话")
            self._load_session(sid)
        else:
            self._clear_chat_bubbles()
            self._load_welcome_bubble()
        self._switch_view(0)

    def _load_session(self, session_id: int):
        self._stream_id += 1
        self._current_session_id = session_id
        self._clear_chat_bubbles()

        if self.memory:
            messages = self.memory.get_session_messages(session_id)
            if messages:
                history = []
                for m in messages:
                    sender = "user" if m["role"] == "user" else "ai"
                    self._add_message_bubble(sender, m["content"])
                    history.append({"role": m["role"], "content": m["content"]})
                if self.ai_engine:
                    self.ai_engine.set_conversation_history(history)
            else:
                self._load_welcome_bubble()
        else:
            self._load_welcome_bubble()

    def _refresh_history_list(self):
        self.session_list.clear()
        if not self.memory:
            return

        sessions = self.memory.get_all_sessions()
        for s in sessions:
            item = QListWidgetItem(f"📁 {s['title']}  ({s['created_at'][:16]})")
            item.setData(Qt.UserRole, s["id"])
            self.session_list.addItem(item)
            if s["id"] == self._current_session_id:
                self.session_list.setCurrentItem(item)

    def _on_session_item_clicked(self, item):
        sid = item.data(Qt.UserRole)
        if sid:
            self._load_session(sid)
            self._switch_view(0)

    def _delete_selected_session(self):
        item = self.session_list.currentItem()
        if not item or not self.memory:
            return

        sid = item.data(Qt.UserRole)
        self.memory.delete_session(sid)
        self._refresh_history_list()

        sessions = self.memory.get_all_sessions()
        if sessions:
            self._load_session(sessions[0]["id"])
        else:
            self._create_new_session_action()

    def _clear_current_chat(self):
        self._stream_id += 1
        if self.ai_engine:
            self.ai_engine.clear_history()

        if self.memory and self._current_session_id:
            self.memory.clear_session_messages(self._current_session_id)

        self._clear_chat_bubbles()
        self._load_welcome_bubble()

    def _clear_chat_bubbles(self):
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._current_ai_bubble = None

    def _load_welcome_bubble(self):
        pet_name = self.config.get("behavior", {}).get("pet_name", "桃濑日和")
        welcome_msg = f"你好呀！我是你的桌面智能助理 **{pet_name}** 🌸\n点击上方 `⚙️ 设置` 可自由切换本地 Ollama 或外部 DeepSeek/OpenAI 模型，点击 `📜 历史` 可查看分类历史会话。有什么我可以帮你的吗？"
        self._add_message_bubble("ai", welcome_msg)

    # ── 消息流式处理 ──
    def _send_message(self):
        text = self.input_edit.text().strip()
        if not text or self._is_generating:
            return

        self.input_edit.clear()
        self._is_generating = True
        self.send_btn.setEnabled(False)

        if self.memory and self._current_session_id:
            messages = self.memory.get_session_messages(self._current_session_id)
            if len(messages) == 0:
                short_title = text[:18] + ("..." if len(text) > 18 else "")
                self.memory.update_session_title(self._current_session_id, short_title)

        self._add_message_bubble("user", text)
        self._current_ai_bubble = self._add_message_bubble("ai", "正在思考中...")

        self._stream_id += 1
        active_id = self._stream_id

        threading.Thread(target=self._stream_chat_worker, args=(active_id, text,), daemon=True).start()

    def _stream_chat_worker(self, active_id, user_msg):
        full_text = ""
        sid = self._current_session_id
        try:
            async def _run_stream():
                nonlocal full_text
                async for chunk in self.ai_engine.chat_stream(user_msg, session_id=sid):
                    if active_id != self._stream_id:
                        break
                    full_text += chunk
                    self.message_chunk_signal.emit(active_id, full_text)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_run_stream())
            loop.close()

            if active_id == self._stream_id:
                self.message_done_signal.emit(active_id, full_text)
        except Exception as e:
            if active_id == self._stream_id:
                self.message_error_signal.emit(active_id, str(e))

    def _on_chunk(self, stream_id, partial_text):
        if stream_id == self._stream_id and self._current_ai_bubble:
            try:
                self._current_ai_bubble.set_text(partial_text)
                self._scroll_to_bottom()
            except (RuntimeError, Exception):
                pass

    def _on_done(self, stream_id, full_text):
        if stream_id == self._stream_id:
            self._is_generating = False
            self.send_btn.setEnabled(True)
            if self._current_ai_bubble:
                try:
                    self._current_ai_bubble.set_text(full_text)
                    self._scroll_to_bottom()
                except (RuntimeError, Exception):
                    pass

    def _on_error(self, stream_id, err_msg):
        if stream_id == self._stream_id:
            self._is_generating = False
            self.send_btn.setEnabled(True)
            if self._current_ai_bubble:
                try:
                    self._current_ai_bubble.set_text(f"⚠️ 生成失败: {err_msg}")
                    self._scroll_to_bottom()
                except (RuntimeError, Exception):
                    pass

    def _add_message_bubble(self, sender, text):
        bubble = MessageBubble(sender, text)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self._scroll_to_bottom()
        return bubble

    def _scroll_to_bottom(self):
        QTimer.singleShot(20, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def _connect_signals(self):
        self.message_chunk_signal.connect(self._on_chunk)
        self.message_done_signal.connect(self._on_done)
        self.message_error_signal.connect(self._on_error)
        self.model_scanned_signal.connect(self._on_models_scanned)

    def _toggle_maximize(self):
        if not self._is_maximized:
            self._normal_geometry = self.geometry()
            try:
                avail = QApplication.primaryScreen().availableGeometry()
                inset_geo = QRect(avail.x() + 8, avail.y() + 8, avail.width() - 16, avail.height() - 16)
                self.setGeometry(inset_geo)
            except Exception:
                self.resize(1000, 750)
            self._is_maximized = True
            self.max_btn.setText("❐")
        else:
            if self._normal_geometry:
                self.setGeometry(self._normal_geometry)
            else:
                self.resize(540, 690)
            self._is_maximized = False
            self.max_btn.setText("⤢")

        self._update_corner_grips_geometry()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 顶部拖拽移动
            if event.pos().y() <= 52:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
                return

    def mouseMoveEvent(self, event):
        if self._drag_pos and (event.buttons() & Qt.LeftButton) and not self._is_maximized:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
            return

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
