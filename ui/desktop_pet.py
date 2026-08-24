from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent
# -*- coding: utf-8 -*-
"""
Desktop Pet v2.0 - Live2D Interactive Keyboard & Mouse Sync Desktop Pet
Crash-proof Thread-Safe Signal Architecture for 100% Stability
"""
import sys
import random
import threading
import socketserver
import time
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

try:
    from PyQt5.QtWidgets import QWidget, QMenu, QApplication
    from PyQt5.QtCore import Qt, QTimer, QPoint, QUrl, QObject, pyqtSlot, pyqtSignal
    from PyQt5.QtGui import QColor, QCursor
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings
    from PyQt5.QtWebChannel import QWebChannel
except ImportError:
    try:
        from PyQt6.QtWidgets import QWidget, QMenu, QApplication
        from PyQt6.QtCore import Qt, QTimer, QPoint, QUrl, QObject, pyqtSlot, pyqtSignal
        from PyQt6.QtGui import QColor, QCursor
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
        from PyQt6.QtWebChannel import QWebChannel
    except ImportError:
        pass

CHAR_DIR = Path(__file__).parent.parent / "characters" / "default"
HTTP_PORT = 8789
_server_started = False


class RobustHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(CHAR_DIR), **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format, *args):
        pass


class RobustServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        pass


def _ensure_server():
    global _server_started, HTTP_PORT
    if _server_started:
        return HTTP_PORT
    for port in range(8789, 8840):
        try:
            server = RobustServer(("127.0.0.1", port), RobustHandler)
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            HTTP_PORT = port
            _server_started = True
            print(f"[Live2D Server] Serving models at http://127.0.0.1:{HTTP_PORT}")
            return HTTP_PORT
        except Exception:
            continue
    return HTTP_PORT


class _SilentPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, msg, line, src):
        try:
            enc = sys.stdout.encoding or 'utf-8'
            safe_msg = msg.encode(enc, errors='replace').decode(enc, errors='replace')
            print(f"[Live2D Web] {safe_msg}")
        except Exception:
            pass


class InputSignalBridge(QObject):
    """Thread-safe signal bridge between background keyboard listener and Qt main thread"""
    key_pressed = pyqtSignal()


class PetBridge(QObject):
    def __init__(self, pet):
        super().__init__()
        self._p = pet
        self._wx = self._wy = self._sx = self._sy = 0

    @pyqtSlot()
    def onModelLoaded(self):
        print("[Live2D] Model ready in WebGL scene!")

    @pyqtSlot(int, int)
    def onDragStart(self, sx, sy):
        pos = self._p.pos()
        self._wx, self._wy = pos.x(), pos.y()
        self._sx, self._sy = sx, sy

    @pyqtSlot(int, int)
    def onDragMove(self, sx, sy):
        self._p.move(self._wx + sx - self._sx, self._wy + sy - self._sy)

    @pyqtSlot()
    def onDragEnd(self):
        pos = self._p.pos()
        self._p.config.setdefault("pet", {})["position_x"] = pos.x()
        self._p.config.setdefault("pet", {})["position_y"] = pos.y()
        self._p.save_config_fn(self._p.config)

    @pyqtSlot()
    def onUserDoubleClick(self):
        self._p._open_chat()

    @pyqtSlot(int, int)
    def onRightClick(self, sx, sy):
        self._p._show_context_menu(QCursor.pos())

    def trigger_action(self, action, duration=0.0):
        self._p.web.page().runJavaScript(f"window.triggerAction('{action}', {duration});")

    def trigger_emotion(self, emotion):
        self._p.web.page().runJavaScript(f"window.triggerEmotion('{emotion}');")


class DesktopPet(QWidget):
    """Live2D 键盘打字与鼠标同步互动桌宠 (稳定防闪退架构)"""

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
        self._last_mouse_pos = None

        _ensure_server()
        if (ROOT_DIR / "assets" / "icons" / "pet_icon.png").exists():
            from PyQt5.QtGui import QIcon
            self.setWindowIcon(QIcon(str(ROOT_DIR / "assets" / "icons" / "pet_icon.png")))
        self._init_window()
        self._init_webview()
        self._init_channel()
        self._load()
        self._init_auto()
        self._init_input_listeners()

        self.emotion_system.on_emotion_change(
            lambda em: self.bridge.trigger_emotion(em.value)
        )

        avail = QApplication.primaryScreen().availableGeometry()
        default_x = max(100, avail.width() - 320)
        default_y = max(100, avail.height() - 440)
        x = config.get("pet", {}).get("position_x", default_x)
        y = config.get("pet", {}).get("position_y", default_y)
        x = max(50, min(x, avail.width() - 260))
        y = max(50, min(y, avail.height() - 380))
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

    def _init_window(self):
        flag = (Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow) if hasattr(Qt, 'FramelessWindowHint') else (
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SubWindow
        )
        self.setWindowFlags(flag)
        
        wa_trans = Qt.WA_TranslucentBackground if hasattr(Qt, 'WA_TranslucentBackground') else Qt.WidgetAttribute.WA_TranslucentBackground
        self.setAttribute(wa_trans)
        self.setFixedSize(190, 235)

    def _init_webview(self):
        self.web = QWebEngineView(self)
        page = _SilentPage(self.web)
        self.web.setPage(page)
        page.setBackgroundColor(QColor(0, 0, 0, 0))

        s = page.settings()
        try:
            s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            s.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        except Exception:
            pass

        self.web.setGeometry(0, 0, 190, 235)
        self.web.show()

    def _init_channel(self):
        self.bridge = PetBridge(self)
        self.channel = QWebChannel()
        self.channel.registerObject("pet", self.bridge)
        self.web.page().setWebChannel(self.channel)

    def _load(self):
        global HTTP_PORT
        t = int(time.time() * 1000)
        url = f"http://127.0.0.1:{HTTP_PORT}/renderer.html?v={t}"
        print(f"[Live2D Pet] Loading URL: {url}")
        self.web.setUrl(QUrl(url))

    def _init_auto(self):
        t = QTimer(self)
        t.setInterval(24000)
        t.timeout.connect(self._auto)
        t.start()

    def _init_input_listeners(self):
        # 1. Thread-safe keyboard listener with Qt Signals
        self.signals = InputSignalBridge()
        self.signals.key_pressed.connect(self._handle_key_pressed)

        if HAS_PYNPUT:
            try:
                def on_press(key):
                    self.signals.key_pressed.emit()

                self._kb_listener = keyboard.Listener(on_press=on_press)
                self._kb_listener.daemon = True
                self._kb_listener.start()
                print("[Input Hook] Global keyboard listener active with thread-safe signals!")
            except Exception as e:
                print(f"[Input Hook] Keyboard listener notice: {e}")

        # 2. Main-thread QTimer for smooth 30fps mouse tracking (Crash-Proof & 0% CPU overhead)
        self._mouse_timer = QTimer(self)
        self._mouse_timer.setInterval(33) # ~30fps
        self._mouse_timer.timeout.connect(self._poll_mouse_pos)
        self._mouse_timer.start()

    def _handle_key_pressed(self):
        try:
            self.web.page().runJavaScript("window.onGlobalKeyPress();")
        except Exception:
            pass

    def _poll_mouse_pos(self):
        try:
            cur = QCursor.pos()
            if self._last_mouse_pos == (cur.x(), cur.y()):
                return
            self._last_mouse_pos = (cur.x(), cur.y())

            pos = self.pos()
            cx = pos.x() + self.width() // 2
            cy = pos.y() + self.height() // 2
            dx = (cur.x() - cx) / 700.0
            dy = (cur.y() - cy) / 500.0
            norm_x = max(-1.0, min(1.0, dx))
            norm_y = max(-1.0, min(1.0, dy))
            self.web.page().runJavaScript(f"window.onGlobalMouseMove({norm_x:.3f}, {norm_y:.3f});")
        except Exception:
            pass

    def _auto(self):
        r = random.random()
        if r < 0.35:
            self.bridge.trigger_action("thinking", 4.0)
        elif r < 0.70:
            self.bridge.trigger_action("kneel", 5.0)

    def play_interaction(self):
        acts = ["happy", "wave", "thinking"]
        self.bridge.trigger_action(random.choice(acts), 4.0)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #201c38;
                border: 1px solid #43396f;
                border-radius: 10px;
                padding: 6px;
                color: #eae6ff;
                font-family: 'Microsoft YaHei UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 7px 22px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: #4c2889;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: #372f5d;
                margin: 4px 6px;
            }
        """)

        act_chat = menu.addAction("💬 开启对话")
        act_history = menu.addAction("📜 历史会话")
        act_settings = menu.addAction("⚙️ 设置与模型")
        menu.addSeparator()
        act_hide = menu.addAction("👁️ 隐藏到托盘")
        act_quit = menu.addAction("❌ 退出程序")

        action = menu.exec_(pos)

        if action == act_chat:
            self._open_chat()
        elif action == act_history:
            self._open_history()
        elif action == act_settings:
            self._open_settings()
        elif action == act_hide:
            self.hide()
        elif action == act_quit:
            QApplication.quit()

    def _open_chat(self):
        from ui.chat_window import ChatWindow
        if self.chat_window is None:
            self.chat_window = ChatWindow(
                config=self.config,
                ai_engine=self.ai_engine,
                pet_window=self,
                save_config_fn=self.save_config_fn
            )
        self.chat_window.show()
        self.chat_window.raise_()
        self.chat_window.activateWindow()
        self.chat_window._switch_view(0)

    def _open_history(self):
        self._open_chat()
        self.chat_window._switch_view(1)

    def _open_settings(self):
        self._open_chat()
        self.chat_window._switch_view(2)

    def _open_chat(self):
        from ui.chat_window import ChatWindow
        if self.chat_window is None:
            self.chat_window = ChatWindow(
                self.config, self.ai_engine, self.emotion_system,
                self.voice_input, self.voice_output
            )
        self.chat_window.show()
        self.chat_window.raise_()
        self.chat_window.activateWindow()

    def _open_control_panel(self):
        self._open_settings()

    def _toggle_always_on_top(self, checked):
        self.config.setdefault("pet", {})["always_on_top"] = checked
        self.save_config_fn(self.config)
        if (ROOT_DIR / "assets" / "icons" / "pet_icon.png").exists():
            from PyQt5.QtGui import QIcon
            self.setWindowIcon(QIcon(str(ROOT_DIR / "assets" / "icons" / "pet_icon.png")))
        self._init_window()
        self.show()


    def mouseDoubleClickEvent(self, event):
        self._open_chat()
        event.accept()
