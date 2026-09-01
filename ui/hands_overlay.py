# -*- coding: utf-8 -*-
"""
HandsOverlay - 独立透明浮窗，加载 Live2D renderer.html?mode=hands
仅显示 Hiyori 的手部区域，贴在主桌宠窗口下方，营造"手放在桌面"的效果
键盘/鼠标输入实时驱动手部动画（与主角色完全同步）
"""
import time
from pathlib import Path

try:
    from PyQt5.QtWidgets import QWidget, QApplication
    from PyQt5.QtCore import Qt, QUrl, QTimer, QPoint
    from PyQt5.QtGui import QColor, QCursor
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
    from PyQt5.QtWebEngineWidgets import QWebEnginePage
    from PyQt5.QtWebChannel import QWebChannel
except ImportError:
    from PyQt6.QtWidgets import QWidget, QApplication
    from PyQt6.QtCore import Qt, QUrl, QTimer, QPoint
    from PyQt6.QtGui import QColor, QCursor
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    from PyQt6.QtWebChannel import QWebChannel


class _SilentPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, msg, line, src):
        pass


class HandsOverlay(QWidget):
    """
    手部覆盖浮窗 - 显示 Live2D Hiyori 手部区域
    尺寸：190 x 60px（与主桌宠同宽，仅显示底部手部区域）
    """

    HAND_W = 190
    HAND_H = 60

    def __init__(self, http_port: int, pet_window=None):
        super().__init__()
        self.http_port = http_port
        self.pet_window = pet_window
        self._last_mouse_pos = (0, 0)

        self._init_window()
        self._init_webview()
        self._load()
        self._start_mouse_tracker()

    def _init_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFixedSize(self.HAND_W, self.HAND_H)

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

        self.web.setGeometry(0, 0, self.HAND_W, self.HAND_H)
        self.web.show()

    def _load(self):
        t = int(time.time() * 1000)
        url = f"http://127.0.0.1:{self.http_port}/renderer.html?mode=hands&v={t}"
        print(f"[HandsOverlay] Loading: {url}")
        self.web.setUrl(QUrl(url))

    def _start_mouse_tracker(self):
        self._mouse_timer = QTimer(self)
        self._mouse_timer.setInterval(33)
        self._mouse_timer.timeout.connect(self._poll_mouse)
        self._mouse_timer.start()

    def _poll_mouse(self):
        try:
            cur = QCursor.pos()
            if self._last_mouse_pos == (cur.x(), cur.y()):
                return
            self._last_mouse_pos = (cur.x(), cur.y())
            pos = self.pos()
            cx = pos.x() + self.HAND_W // 2
            cy = pos.y() + self.HAND_H // 2
            norm_x = max(-1.0, min(1.0, (cur.x() - cx) / 700.0))
            norm_y = max(-1.0, min(1.0, (cur.y() - cy) / 500.0))
            self.web.page().runJavaScript(
                f"window.onGlobalMouseMove({norm_x:.3f}, {norm_y:.3f});"
            )
        except Exception:
            pass

    def on_key_press(self):
        try:
            self.web.page().runJavaScript("window.onGlobalKeyPress();")
        except Exception:
            pass

    def on_mouse_click(self, button='left'):
        try:
            self.web.page().runJavaScript(f"window.onGlobalMouseClick('{button}');")
        except Exception:
            pass

    def snap_to_pet(self, pet_x: int, pet_y: int, pet_h: int):
        hand_x = pet_x
        hand_y = pet_y + pet_h - 18
        self.move(hand_x, hand_y)

    def follow_pet(self):
        if self.pet_window:
            pos = self.pet_window.pos()
            self.snap_to_pet(pos.x(), pos.y(), self.pet_window.height())
