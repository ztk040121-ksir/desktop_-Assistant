"""
桌面小人窗口 - 真实肢体动作序列 (迈腿奔跑、双手举臂欢呼、抱枕侧躺睡觉、坐姿挥手)
纯净 100% 透明绿幕级渲染，支持自主桌面奔跑漫步
"""
import random
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QLabel, QMenu, QApplication
from PyQt6.QtCore import Qt, QTimer, QPoint, QSize
from PyQt6.QtGui import QPixmap, QGuiApplication

ROOT_DIR = Path(__file__).parent.parent


class DesktopPet(QWidget):
    """拥有真正肢体动作的超萌桌面桌宠"""

    def __init__(self, config, ai_engine, emotion_system,
                 voice_input, voice_output, save_config_fn, plugin_manager=None):
        super().__init__()
        self.config = config
        self.ai_engine = ai_engine
        self.emotion_system = emotion_system
        self.voice_input = voice_input
        self.voice_output = voice_output
        self.save_config_fn = save_config_fn
        self.plugin_manager = plugin_manager

        self.chat_window = None
        self.control_panel = None
        self.drag_pos = None

        self._current_action = "idle"
        self._current_frame_idx = 0
        self._action_frames: dict[str, list[QPixmap]] = {}

        # 自主奔跑漫步物理状态
        self._is_walking = False
        self._walk_direction = 1
        self._walk_steps_left = 0

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._next_frame)

        self.reset_timer = QTimer(self)
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(self._reset_to_idle)

        self._init_window()
        self._load_frames()
        self._setup_autonomous_behaviors()

        self.emotion_system.on_emotion_change(self._on_emotion_change)

        x = config.get("pet", {}).get("position_x", 1250)
        y = config.get("pet", {}).get("position_y", 680)
        self.move(x, y)
        self.show()

    def _init_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(130, 150)

        self.pet_label = QLabel(self)
        self.pet_label.setGeometry(0, 0, 130, 150)
        self.pet_label.setScaledContents(True)
        self.pet_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _load_frames(self):
        char = self.config.get("pet", {}).get("character", "default")
        char_dir = ROOT_DIR / "characters" / char

        actions = ["idle", "walk", "happy", "sleep"]
        for act in actions:
            act_dir = char_dir / act
            frames = []
            if act_dir.exists():
                png_files = sorted(list(act_dir.glob("*.png")))
                for pf in png_files:
                    pix = QPixmap(str(pf))
                    if not pix.isNull():
                        frames.append(pix)
            self._action_frames[act] = frames

        self._play_action("idle")

    def _play_action(self, action_name: str, duration_ms: int = 0):
        if action_name not in self._action_frames or not self._action_frames[action_name]:
            action_name = "idle"
        
        self._current_action = action_name
        self._current_frame_idx = 0
        self.anim_timer.stop()

        # 根据动作设置真实帧率
        if action_name == "walk":
            interval = 95
        elif action_name == "happy":
            interval = 110
        elif action_name == "sleep":
            interval = 220
        else:
            interval = 135

        self.anim_timer.start(interval)
        self._render_current_frame()

        if duration_ms > 0 and action_name != "idle":
            self.reset_timer.stop()
            self.reset_timer.start(duration_ms)

    def _next_frame(self):
        frames = self._action_frames.get(self._current_action, [])
        if not frames:
            return
        self._current_frame_idx = (self._current_frame_idx + 1) % len(frames)
        self._render_current_frame()

        # 如果处于真实奔跑迈步状态，同步位移
        if self._is_walking and self._current_action == "walk" and self._walk_steps_left > 0:
            self._walk_steps_left -= 1
            cur_pos = self.pos()
            screen = QGuiApplication.primaryScreen().geometry()
            new_x = cur_pos.x() + (self._walk_direction * 5)
            # 屏幕边缘反弹
            if new_x < 20:
                new_x = 20
                self._walk_direction = 1
            elif new_x > screen.width() - 150:
                new_x = screen.width() - 150
                self._walk_direction = -1
            self.move(new_x, cur_pos.y())
            if self._walk_steps_left <= 0:
                self._is_walking = False
                self._play_action("idle")

    def _render_current_frame(self):
        frames = self._action_frames.get(self._current_action, [])
        if frames and 0 <= self._current_frame_idx < len(frames):
            self.pet_label.setPixmap(frames[self._current_frame_idx])

    def play_interaction(self):
        """点击互动：双手举起欢呼雀跃跳动"""
        self._is_walking = False
        self._play_action("happy", duration_ms=3000)

    def _reset_to_idle(self):
        self._is_walking = False
        self._play_action("idle")

    def _on_emotion_change(self, emotion):
        val = emotion.value
        if val == "happy":
            self.play_interaction()
        elif val == "sleepy":
            self._play_action("sleep", duration_ms=5000)
        elif val in self._action_frames:
            self._play_action(val, duration_ms=3000)

    def _setup_autonomous_behaviors(self):
        """自主行为引擎：平时每隔 20 秒，小人会自动在桌面上迈步小跑一段路"""
        self.auto_timer = QTimer(self)
        self.auto_timer.setInterval(20000)
        self.auto_timer.timeout.connect(self._do_random_behavior)
        self.auto_timer.start()

    def _do_random_behavior(self):
        if self._current_action == "idle" and not self.drag_pos:
            r = random.random()
            if r < 0.65:
                # 开启真实迈步小跑
                self._is_walking = True
                self._walk_direction = random.choice([1, -1])
                self._walk_steps_left = random.randint(10, 20)
                self._play_action("walk")
            elif r < 0.85:
                # 伸懒腰睡觉一下
                self._play_action("sleep", duration_ms=4500)

    # ── 鼠标交互 ──
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_walking = False
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self.drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self.drag_pos
            self.move(new_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self.frameGeometry().topLeft()
            self.config["pet"]["position_x"] = pos.x()
            self.config["pet"]["position_y"] = pos.y()
            self.save_config_fn(self.config)
        self.drag_pos = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_chat()

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(22, 22, 38, 245);
                color: #e8e8f8;
                border: 1px solid rgba(140, 130, 255, 0.35);
                border-radius: 10px;
                padding: 6px;
                font-family: 'Microsoft YaHei UI';
                font-size: 13px;
            }
            QMenu::item {
                padding: 7px 22px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: rgba(140, 120, 255, 0.35);
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(140, 130, 255, 0.2);
                margin: 4px 6px;
            }
        """)
        menu.addAction("💬 打开对话", self._open_chat)
        menu.addAction("✨ 欢呼互动", self.play_interaction)
        menu.addAction("🏃 桌面小跑", lambda: self._start_manual_walk())
        menu.addAction("😴 抱枕睡觉", lambda: self._play_action("sleep", duration_ms=8000))
        menu.addSeparator()
        menu.addAction("⚙️ 桌宠管理中心", self._open_control_panel)
        menu.addSeparator()
        menu.addAction("❌ 退出程序", QApplication.quit)
        menu.exec(pos)

    def _start_manual_walk(self):
        self._is_walking = True
        self._walk_direction = random.choice([1, -1])
        self._walk_steps_left = 18
        self._play_action("walk")

    def _open_chat(self):
        from ui.chat_window import ChatWindow
        if self.chat_window is not None:
            if self.chat_window.isMinimized():
                self.chat_window.showNormal()
            self.chat_window.show()
            self.chat_window.raise_()
            self.chat_window.activateWindow()
        else:
            self.chat_window = ChatWindow(
                config=self.config,
                ai_engine=self.ai_engine,
                emotion_system=self.emotion_system,
                voice_input=self.voice_input,
                voice_output=self.voice_output,
                pet_window=self
            )
            self.chat_window.show()

    def _open_control_panel(self):
        from ui.control_panel import ControlPanel
        if self.control_panel is not None:
            if self.control_panel.isMinimized():
                self.control_panel.showNormal()
            self.control_panel.show()
            self.control_panel.raise_()
            self.control_panel.activateWindow()
        else:
            self.control_panel = ControlPanel(
                config=self.config,
                ai_engine=self.ai_engine,
                save_config_fn=self.save_config_fn,
                pet_window=self,
                plugin_manager=self.plugin_manager
            )
            self.control_panel.show()
