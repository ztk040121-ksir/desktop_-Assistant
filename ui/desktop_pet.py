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
    from PyQt6.QtWidgets import QWidget, QMenu, QApplication
    from PyQt6.QtCore import Qt, QTimer, QPoint, QUrl, QObject, pyqtSlot, pyqtSignal
    from PyQt6.QtGui import QColor, QCursor
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    from PyQt6.QtWebChannel import QWebChannel

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
    def createStandardContextMenu(self):
        return None

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
        self._wx = 0
        self._wy = 0
        self._sx = 0
        self._sy = 0

    @pyqtSlot()
    def onModelLoaded(self):
        print("[Live2D] Model ready in WebGL scene!")

    @pyqtSlot(int, int)
    def onDragStart(self, sx, sy):
        pos = self._p.pos()
        self._wx = pos.x()
        self._wy = pos.y()
        self._sx = sx
        self._sy = sy
        if hasattr(self._p, '_on_drag_start'):
            self._p._on_drag_start()

    @pyqtSlot(int, int)
    def onDragMove(self, sx, sy):
        self._p.move(self._wx + sx - self._sx, self._wy + sy - self._sy)

    @pyqtSlot()
    def onDragEnd(self):
        if hasattr(self._p, '_check_edge_dock'):
            self._p._check_edge_dock()
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


class DraggableWebView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._parent:
                self._drag_pos = event.globalPos() - self._parent.pos()
        elif event.button() == Qt.RightButton:
            if self._parent:
                self._parent._show_context_menu(QCursor.pos())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_pos is not None and self._parent:
            self._parent.move(event.globalPos() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_pos is not None and self._parent:
            self._drag_pos = None
            pos = self._parent.pos()
            self._parent.config.setdefault("pet", {})["position_x"] = pos.x()
            self._parent.config.setdefault("pet", {})["position_y"] = pos.y()
            self._parent.save_config_fn(self._parent.config)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self._parent:
            self._parent._open_chat()
        super().mouseDoubleClickEvent(event)

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
        # self._init_auto()  # Disabled to prevent random action jitter
        self._init_input_listeners()
        # 绑定 AI 控制桌宠中枢与定时调度器
        try:
            from core.pet_scheduler import PetScheduler
            from plugins.pet_controller import bind_pet_instance
            bind_pet_instance(self)
            self._scheduler = PetScheduler.get_instance()
            self._scheduler.reminder_triggered.connect(self._on_reminder_triggered)
            print("[DesktopPet] OK scheduler and AI pet control bridge connected!")
        except Exception as se:
            print(f"[DesktopPet] Warning connecting scheduler: {se}")

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
        self.setFixedSize(205, 305)

    def _init_webview(self):
        self.web = DraggableWebView(self)
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

        self.web.setGeometry(0, 0, 205, 305)
        self.web.show()

    def _init_channel(self):
        self.bridge = PetBridge(self)
        self.channel = QWebChannel()
        self.channel.registerObject("petBridge", self.bridge)
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
        self._mouse_timer.setInterval(28)
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
            cx = pos.x() + self.width() / 2.0
            cy = pos.y() + self.height() / 2.0

            dx = float(cur.x()) - cx
            dy = float(cur.y()) - cy
            dist_px = (dx * dx + dy * dy) ** 0.5

            norm_x = max(-1.0, min(1.0, dx / 480.0))
            norm_y = max(-1.0, min(1.0, -dy / 380.0))

            self.web.page().runJavaScript(f"if (window.onGlobalMouseMove) window.onGlobalMouseMove({norm_x:.4f}, {norm_y:.4f}, {dist_px:.1f});")
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
                background: rgba(30, 20, 38, 245);
                border: 1px solid rgba(255, 140, 180, 0.45);
                border-radius: 12px;
                padding: 5px;
                color: #fff2f6;
                font-family: -apple-system, 'Microsoft YaHei UI', 'Segoe UI', sans-serif;
                font-size: 11.5px;
            }
            QMenu::item {
                padding: 5px 16px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff6599, stop:1 #ff8da1);
                color: #ffffff;
                font-weight: bold;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 140, 180, 0.2);
                margin: 3px 4px;
            }
        """)

        act_chat = menu.addAction("💬 与春日和聊天")
        menu.addSeparator()
        act_feed = menu.addAction("🍰 投喂小点心")
        act_headpat = menu.addAction("🌸 摸摸头抚慰")
        act_pomodoro = menu.addAction("⏱️ 设定专注与闹钟")
        act_fortune = menu.addAction("🥠 每日樱花运势签")
        act_bond = menu.addAction("❤️ 当前羁绊手帐")
        menu.addSeparator()
        act_history = menu.addAction("📜 历史对话记录")
        act_settings = menu.addAction("⚙️ 助手系统设置")
        menu.addSeparator()
        act_hide = menu.addAction("🙈 隐藏桌面宠物")
        act_quit = menu.addAction("❌ 退出程序")

        # Smart Side Positioning: Place menu to the right of pet so it never blocks Hiyori
        pet_pos = self.pos()
        target_x = pet_pos.x() + self.width() + 6
        target_y = max(50, pet_pos.y() + 20)

        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            if target_x + 160 > screen_geo.right():
                target_x = pet_pos.x() - 170

        # Non-blocking popup to prevent main thread freeze
        menu.triggered.connect(lambda act: self._handle_context_action(
            act, act_chat, act_feed, act_headpat, act_pomodoro, act_fortune, act_bond, act_history, act_settings, act_hide, act_quit
        ))
        menu.popup(QPoint(target_x, target_y))
        return

    def _handle_context_action(self, action, act_chat, act_feed, act_headpat, act_pomodoro, act_fortune, act_bond, act_history, act_settings, act_hide, act_quit):
        if action == act_chat:
            self._open_chat()
        elif action == act_feed:
            self.web.page().runJavaScript("if (window.triggerFeedSnackPrompt) window.triggerFeedSnackPrompt();")
        elif action == act_headpat:
            self.web.page().runJavaScript("if (window.triggerPetHeadpat) window.triggerPetHeadpat();")
        elif action == act_pomodoro:
            self.web.page().runJavaScript("if (window.triggerStartPomodoro) window.triggerStartPomodoro();")
        elif action == act_fortune:
            self.web.page().runJavaScript("if (window.triggerDrawFortune) window.triggerDrawFortune();")
        elif action == act_bond:
            self.web.page().runJavaScript("if (window.triggerShowAffection) window.triggerShowAffection();")
        elif action == act_history:
            self._open_history()
        elif action == act_settings:
            self._open_settings()
        elif action == act_hide:
            self.hide()
        elif action == act_quit:
            QApplication.quit()

    def _open_chat(self):
        try:
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
            if hasattr(self.chat_window, '_switch_nav'):
                self.chat_window._switch_nav(0)
            elif hasattr(self.chat_window, '_switch_view'):
                self.chat_window._switch_view(0)
        except Exception as e:
            print(f"[Chat] Failed to open chat: {e}")

    def _open_history(self):
        self._open_chat()
        if self.chat_window:
            if hasattr(self.chat_window, '_switch_nav'):
                self.chat_window._switch_nav(0)
            elif hasattr(self.chat_window, '_switch_view'):
                self.chat_window._switch_view(1)

    def _open_settings(self):
        self._open_chat()
        if self.chat_window:
            if hasattr(self.chat_window, '_switch_nav'):
                self.chat_window._switch_nav(3)
            elif hasattr(self.chat_window, '_switch_view'):
                self.chat_window._switch_view(2)

    def _show_and_activate(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def hideEvent(self, event):
        """窗口隐藏时自动暂停 PIXI WebGL 渲染，彻底释放 GPU/CPU 资源"""
        try:
            if hasattr(self, 'web') and self.web and self.web.page():
                self.web.page().runJavaScript("if (window.app && window.app.ticker) { window.app.ticker.stop(); }")
        except Exception:
            pass
        super().hideEvent(event)

    def showEvent(self, event):
        """窗口恢复显示时自动恢复 PIXI WebGL 渲染"""
        try:
            if hasattr(self, 'web') and self.web and self.web.page():
                self.web.page().runJavaScript("if (window.app && window.app.ticker) { window.app.ticker.start(); }")
        except Exception:
            pass
        super().showEvent(event)

    # ──────────────────────────────────────────
    # 边缘停靠 / Anime Peeker Edge Dock (春日双手扒边探头)
    # ──────────────────────────────────────────
    def _on_drag_start(self):
        if getattr(self, '_edge_docked', None):
            self._edge_docked = None
            self.web.page().runJavaScript("if (window.onEdgeDockStateChanged) window.onEdgeDockStateChanged(null);")

    def _check_edge_dock(self):
        """拖拽结束后：若拖到屏幕边缘，自动吸附收起为高精动漫双手扒边挂件"""
        try:
            screen = QApplication.primaryScreen()
            if not screen:
                return
            sg = screen.geometry()
            pos = self.pos()
            w = self.width()

            EDGE_THRESHOLD = 65   # 靠近边缘 65px 触发吸附
            PEEK_VISIBLE_W = 52   # 露出的高精贴纸宽度仅 52px

            if pos.x() <= EDGE_THRESHOLD:
                # 贴紧左侧：收起为左侧探头挂件 (仅露 52px)
                self._edge_docked = 'left'
                target_x = -(w - PEEK_VISIBLE_W)
                self.web.page().runJavaScript("if (window.onEdgeDockStateChanged) window.onEdgeDockStateChanged('left');")
                self._animate_to_x(target_x)
            elif pos.x() + w >= sg.width() - EDGE_THRESHOLD:
                # 贴紧右侧：收起为右侧探头挂件 (仅露 52px)
                self._edge_docked = 'right'
                target_x = sg.width() - PEEK_VISIBLE_W
                self.web.page().runJavaScript("if (window.onEdgeDockStateChanged) window.onEdgeDockStateChanged('right');")
                self._animate_to_x(target_x)
            else:
                if getattr(self, '_edge_docked', None) is not None:
                    self._edge_docked = None
                    self.web.page().runJavaScript("if (window.onEdgeDockStateChanged) window.onEdgeDockStateChanged(null);")
        except Exception as e:
            print(f"[EdgeDock] Check error: {e}")

    def _animate_to_x(self, target_x, steps=10, interval=15):
        """平滑滑动动画至目标 X 坐标"""
        try:
            from PyQt5.QtCore import QTimer
            start_x = self.pos().x()
            current_y = self.pos().y()
            step_size = (target_x - start_x) / steps
            step_count = [0]

            if hasattr(self, '_dock_anim_timer') and self._dock_anim_timer:
                self._dock_anim_timer.stop()

            timer = QTimer(self)
            self._dock_anim_timer = timer

            def _step():
                step_count[0] += 1
                new_x = int(start_x + step_size * step_count[0])
                self.move(new_x, current_y)
                if step_count[0] >= steps:
                    self.move(target_x, current_y)
                    timer.stop()

            timer.timeout.connect(_step)
            timer.start(interval)
        except Exception as e:
            self.move(target_x, self.pos().y())

    def _undock_from_edge(self):
        """从边缘滑出复原为完整大模型与写字台"""
        try:
            screen = QApplication.primaryScreen()
            if not screen:
                return
            sg = screen.geometry()
            current_y = self.pos().y()

            if getattr(self, '_edge_docked', None) == 'left':
                self._animate_to_x(15, steps=10)
            elif getattr(self, '_edge_docked', None) == 'right':
                self._animate_to_x(sg.width() - self.width() - 15, steps=10)

            self._edge_docked = None
            self.web.page().runJavaScript("if (window.onEdgeDockStateChanged) window.onEdgeDockStateChanged(null);")
        except Exception as e:
            print(f"[EdgeDock] Undock error: {e}")

    def enterEvent(self, event):
        """鼠标悬浮到探头挂件上时，自动丝滑展开复原"""
        try:
            if getattr(self, '_edge_docked', None):
                self._undock_from_edge()
        except Exception:
            pass
        super().enterEvent(event)
    def set_sound_enabled(self, enabled: bool):
        self.config["sound_enabled"] = enabled
        self.config.setdefault("behavior", {})["sound_enabled"] = enabled
        try:
            js_val = "true" if enabled else "false"
            self.web.page().runJavaScript(f"if (window.setSoundEnabled) window.setSoundEnabled({js_val});")
        except Exception as e:
            print(f"[DesktopPet] Error setting sound enabled: {e}")

    def _on_reminder_triggered(self, reminder_id: int, title: str, content: str, motion: str):
        """定时提醒到期触发：桌面弹气泡、做动作、播放清脆番茄钟/提醒音、托盘通知"""
        try:
            clean_c = content.replace(chr(39), ' ').replace(chr(34), ' ').replace(chr(10), ' ')
            m_name = motion if motion else 'nod'
            # 1. 网页端 Live2D 弹气泡与做动作
            self.web.page().runJavaScript(f"window.showCareMessage('⏰ 提醒时间到啦', '{clean_c}'); window.triggerAction('{m_name}', 4000); if (window.playAlarmChime) window.playAlarmChime();")
            # 2. 播放甜美清脆的番茄闹钟提示音 (四音符水晶琶音 C6 -> E6 -> G6 -> C7，受声音开关控制)
            if self.config.get("behavior", {}).get("sound_enabled", True):
                import threading, winsound
                def _play_alarm_sound():
                    tones = [(1046, 120), (1318, 120), (1568, 140), (2093, 280)]
                    for freq, dur in tones:
                        try:
                            winsound.Beep(freq, dur)
                        except Exception:
                            pass
                threading.Thread(target=_play_alarm_sound, daemon=True).start()
                tones = [(1046, 120), (1318, 120), (1568, 140), (2093, 280)]
                for freq, dur in tones:
                    try:
                        winsound.Beep(freq, dur)
                    except Exception:
                        pass
            # 3. 系统托盘通知
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.showMessage('🌸 春日和提醒你', f'主人，提醒时间到啦：{content}', self.tray_icon.Information, 5000)
            print(f'[DesktopPet] Reminder triggered: {content}')
        except Exception as e:
            print(f'[DesktopPet] Error triggering reminder: {e}')
    def _open_control_panel(self):
        self._open_settings()

    def _toggle_always_on_top(self, checked):
        self.config.setdefault("pet", {})["always_on_top"] = checked
        self.save_config_fn(self.config)
        if (ROOT_DIR / "assets" / "icons" / "pet_icon.png").exists():
            from PyQt5.QtGui import QIcon
            self.setWindowIcon(QIcon(str(ROOT_DIR / "assets" / "icons" / "pet_icon.png")))
    def showEvent(self, event):
        super().showEvent(event)
        try:
            if hasattr(self, 'web') and self.web:
                self.web.page().runJavaScript("if (window.setLive2DRenderingActive) window.setLive2DRenderingActive(true);")
        except Exception:
            pass

    def hideEvent(self, event):
        super().hideEvent(event)
        try:
            if hasattr(self, 'web') and self.web:
                self.web.page().runJavaScript("if (window.setLive2DRenderingActive) window.setLive2DRenderingActive(false);")
        except Exception:
            pass

    def mouseDoubleClickEvent(self, event):
        self._open_chat()
        event.accept()