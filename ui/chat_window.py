"""
对话窗口 - 现代 Glassmorphism 聊天卡片 (纯净高质感、功能全集成)
"""
import asyncio
import threading
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QDragEnterEvent, QDropEvent


class StreamBridge(QObject):
    chunk_sig = pyqtSignal(object, str)
    finish_sig = pyqtSignal(str)
    error_sig = pyqtSignal(str)


class MessageBubble(QWidget):
    """自适应包裹气泡：严密贴合文字、无多余留白"""

    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self._text = text.lstrip()

        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(4, 2, 4, 2)
        outer_layout.setSpacing(8)

        self.label = QLabel(self._text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setMaximumWidth(320)
        self.label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)

        if is_user:
            self.label.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #8b5cf6);
                    color: #ffffff;
                    border-radius: 14px;
                    border-bottom-right-radius: 3px;
                    padding: 8px 13px;
                    font-size: 13px;
                    font-family: 'Microsoft YaHei UI', sans-serif;
                }
            """)
            outer_layout.addStretch(1)
            outer_layout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignRight)
        else:
            self.label.setStyleSheet("""
                QLabel {
                    background: rgba(30, 30, 52, 0.95);
                    color: #f1f5f9;
                    border: 1px solid rgba(140, 130, 255, 0.28);
                    border-radius: 14px;
                    border-bottom-left-radius: 3px;
                    padding: 8px 13px;
                    font-size: 13px;
                    font-family: 'Microsoft YaHei UI', sans-serif;
                }
            """)
            self.avatar = QLabel("🌸")
            self.avatar.setStyleSheet("font-size: 16px; background: transparent;")
            self.avatar.setFixedSize(22, 22)
            self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)

            outer_layout.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignTop)
            outer_layout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignLeft)
            outer_layout.addStretch(1)

    def set_text(self, text: str):
        self._text = text.lstrip()
        self.label.setText(self._text)
        self.label.adjustSize()

    def append_chunk(self, chunk: str):
        self._text += chunk
        if len(self._text) < 10:
            self._text = self._text.lstrip()
        self.label.setText(self._text)
        self.label.adjustSize()


class ChatWindow(QWidget):
    """主对话窗口"""

    def __init__(self, config, ai_engine, emotion_system,
                 voice_input, voice_output, pet_window):
        super().__init__()
        self.config = config
        self.ai_engine = ai_engine
        self.emotion_system = emotion_system
        self.voice_input = voice_input
        self.voice_output = voice_output
        self.pet_window = pet_window
        self._waiting = False

        self.bridge = StreamBridge()
        self.bridge.chunk_sig.connect(self._on_chunk)
        self.bridge.finish_sig.connect(self._on_finish)
        self.bridge.error_sig.connect(self._on_error)

        self._init_ui()
        self._load_history()

        pet_pos = pet_window.pos()
        target_x = max(20, pet_pos.x() - 500)
        target_y = max(40, pet_pos.y() - 200)
        self.move(target_x, target_y)

    def _init_ui(self):
        pet_name = self.config.get("behavior", {}).get("pet_name", "小桃")
        self.setWindowTitle(f"💬 和{pet_name}对话")
        self.setFixedSize(480, 620)
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QWidget {
                background: #121220;
                color: #f0f0ff;
                font-family: "Microsoft YaHei UI", sans-serif;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 顶部集成功能栏 ──
        title_bar = QFrame()
        title_bar.setFixedHeight(54)
        title_bar.setStyleSheet("""
            QFrame {
                background: rgba(20, 20, 36, 0.95);
                border-bottom: 1px solid rgba(140, 130, 255, 0.2);
            }
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(14, 0, 14, 0)
        title_layout.setSpacing(8)

        title_label = QLabel(f"🌸 {pet_name}")
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #a5b4fc;")
        
        self.status_dot = QLabel("🟢 在线")
        self.status_dot.setStyleSheet("font-size: 11px; color: #6ee7b7; margin-left: 4px;")

        action_btn = QPushButton("✨ 互动")
        action_btn.setToolTip("让小人开心跳跃")
        action_btn.setStyleSheet("""
            QPushButton {
                background: rgba(140, 120, 255, 0.15);
                color: #c7d2fe;
                border: 1px solid rgba(140, 130, 255, 0.3);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover { background: rgba(140, 130, 255, 0.3); color: white; }
        """)
        action_btn.clicked.connect(self.pet_window.play_interaction)

        panel_btn = QPushButton("⚙️ 管理中心")
        panel_btn.setToolTip("打开桌宠管理中心")
        panel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(140, 120, 255, 0.15);
                color: #c7d2fe;
                border: 1px solid rgba(140, 130, 255, 0.3);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover { background: rgba(140, 130, 255, 0.3); color: white; }
        """)
        panel_btn.clicked.connect(self.pet_window._open_control_panel)

        clear_btn = QPushButton("🗑️ 清空")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                color: #94a3b8;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.2);
                color: #f87171;
            }
        """)
        clear_btn.clicked.connect(self._clear_chat)

        title_layout.addWidget(title_label)
        title_layout.addWidget(self.status_dot)
        title_layout.addStretch()
        title_layout.addWidget(action_btn)
        title_layout.addWidget(panel_btn)
        title_layout.addWidget(clear_btn)
        main_layout.addWidget(title_bar)

        # ── 消息流展示区 ──
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(140, 130, 255, 0.3);
                border-radius: 3px;
                min-height: 24px;
            }
        """)
        self.msg_container = QWidget()
        self.msg_container.setStyleSheet("background: transparent;")
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setContentsMargins(6, 10, 6, 10)
        self.msg_layout.setSpacing(6)
        self.msg_layout.addStretch()
        self.scroll_area.setWidget(self.msg_container)
        main_layout.addWidget(self.scroll_area, 1)

        # ── 状态栏 ──
        self.status_bar = QFrame()
        self.status_bar.setFixedHeight(22)
        self.status_bar.setStyleSheet("background: transparent;")
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(18, 0, 18, 0)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 11px; color: #a5b4fc; font-weight: 500;")
        status_layout.addWidget(self.status_label)
        main_layout.addWidget(self.status_bar)

        # ── 输入区 ──
        input_frame = QFrame()
        input_frame.setFixedHeight(124)
        input_frame.setStyleSheet("""
            QFrame {
                background: rgba(20, 20, 36, 0.95);
                border-top: 1px solid rgba(140, 130, 255, 0.2);
            }
        """)
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(16, 10, 16, 12)
        input_layout.setSpacing(8)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("输入消息或让小桃处理文件... (Enter 发送，Shift+Enter 换行)")
        self.input_box.setFixedHeight(60)
        self.input_box.setStyleSheet("""
            QTextEdit {
                background: rgba(28, 28, 48, 0.85);
                border: 1px solid rgba(140, 130, 255, 0.25);
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 13px;
                color: #f0f0ff;
                font-family: 'Microsoft YaHei UI';
            }
            QTextEdit:focus {
                border-color: #6366f1;
                background: rgba(32, 32, 56, 0.95);
            }
        """)
        self.input_box.installEventFilter(self)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.hint_drag = QLabel("📁 支持拖入文件分析/真实写入")
        self.hint_drag.setStyleSheet("font-size: 11px; color: #818cf8;")

        self.send_btn = QPushButton("发送 ➤")
        self.send_btn.setFixedHeight(30)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 24px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
            }
        """)
        self.send_btn.clicked.connect(self._on_send)

        btn_row.addWidget(self.hint_drag)
        btn_row.addStretch()
        btn_row.addWidget(self.send_btn)

        input_layout.addWidget(self.input_box)
        input_layout.addLayout(btn_row)
        main_layout.addWidget(input_frame)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent
        if obj == self.input_box and event.type() == QEvent.Type.KeyPress:
            key_event = event
            if (key_event.key() == Qt.Key.Key_Return
                    and not (key_event.modifiers() & Qt.KeyboardModifier.ShiftModifier)):
                self._on_send()
                return True
        return super().eventFilter(obj, event)

    def _add_message(self, text: str, is_user: bool) -> MessageBubble:
        bubble = MessageBubble(text, is_user)
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, bubble)
        QTimer.singleShot(30, self._scroll_to_bottom)
        return bubble

    def _scroll_to_bottom(self):
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _clear_chat(self):
        while self.msg_layout.count() > 1:
            item = self.msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.ai_engine.clear_history()

    def _load_history(self):
        if hasattr(self.ai_engine, 'memory') and self.ai_engine.memory:
            recent = self.ai_engine.memory.get_recent_conversations(8)
            for item in recent:
                self._add_message(item["user"], is_user=True)
                self._add_message(item["ai"], is_user=False)

    def send_message(self, text: str):
        self._add_message(text, is_user=True)
        self._start_ai(text)

    def _on_send(self):
        text = self.input_box.toPlainText().strip()
        if not text or self._waiting:
            return
        self.input_box.clear()
        self._add_message(text, is_user=True)
        self.emotion_system.update_from_user_input(text)
        self._start_ai(text)

    def _start_ai(self, text: str):
        self._waiting = True
        self.send_btn.setEnabled(False)
        self.status_label.setText("✨ 小桃正在处理并执行任务 · · ·")
        self.emotion_system.set_talking()

        ai_bubble = self._add_message("···", is_user=False)
        first_chunk_flag = [False]

        def _thread_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async def _stream():
                    full_reply = ""
                    async for chunk in self.ai_engine.chat_stream(text):
                        if not first_chunk_flag[0]:
                            first_chunk_flag[0] = True
                            self.bridge.chunk_sig.emit(ai_bubble, "__RESET__" + chunk)
                        else:
                            self.bridge.chunk_sig.emit(ai_bubble, chunk)
                        full_reply += chunk
                    return full_reply

                full_res = loop.run_until_complete(_stream())
                self.bridge.finish_sig.emit(full_res)
            except Exception as e:
                self.bridge.error_sig.emit(str(e))
            finally:
                loop.close()

        threading.Thread(target=_thread_task, daemon=True).start()

    def _on_chunk(self, bubble, text: str):
        if text.startswith("__RESET__"):
            bubble.set_text(text[9:])
        else:
            bubble.append_chunk(text)
        self._scroll_to_bottom()

    def _on_finish(self, full_reply: str):
        self._waiting = False
        self.send_btn.setEnabled(True)
        self.status_label.setText("")
        self.emotion_system.set_idle()

    def _on_error(self, err_msg: str):
        self._waiting = False
        self.send_btn.setEnabled(True)
        self.status_label.setText("")
        self._add_message(f"⚠️ 出错了: {err_msg}", is_user=False)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.status_label.setText("📂 松开鼠标立即分析文件...")

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if not urls:
            return
        file_paths = [u.toLocalFile() for u in urls]
        self.status_label.setText("")
        for path in file_paths:
            self._add_message(f"📎 拖入文件: {path}", is_user=True)
        prompt = "我向你提供了以下文件，请帮我分析其内容并给出总结或见解：\n" + "\n".join(file_paths)
        self._start_ai(prompt)
