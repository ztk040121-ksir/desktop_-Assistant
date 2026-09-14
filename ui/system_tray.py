# -*- coding: utf-8 -*-
"""
系统托盘图标与全局菜单
"""
from pathlib import Path
try:
    from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QApplication
    from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QCursor
    from PyQt5.QtCore import Qt, QEvent
except ImportError:
    from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
    from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QCursor
    from PyQt6.QtCore import Qt, QEvent

ROOT_DIR = Path(__file__).parent.parent


def create_fallback_icon():
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent if hasattr(Qt, 'transparent') else Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setBrush(QColor(255, 117, 160))
    painter.setPen(Qt.NoPen if hasattr(Qt, 'NoPen') else Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 28, 28)
    painter.end()
    return QIcon(pixmap)


class AutoCloseMenu(QMenu):
    """自定义防残留托盘菜单：失去焦点或点击外部时 100% 可靠自关闭"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def changeEvent(self, event):
        if event.type() == QEvent.ActivationChange:
            if not self.isActiveWindow():
                self.close()
        super().changeEvent(event)


class SystemTray(QSystemTrayIcon):
    def __init__(self, app, pet_window, config, save_config_fn):
        super().__init__()
        self.app = app
        self.pet = pet_window
        self.config = config
        self.save_config_fn = save_config_fn

        # 关联托盘到桌宠双向引用
        if self.pet:
            self.pet.tray = self
            self.pet.tray_icon = self

        self._is_dark = (self.config.get("ui_theme", "light") == "dark")

        icon_path = ROOT_DIR / "assets" / "icons" / "app_logo.png"
        if icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
        else:
            self.setIcon(create_fallback_icon())

        pet_name = self.config.get("behavior", {}).get("pet_name", "桃濑日和")
        app_ver = self.config.get("app_version", "v4.0")
        self.setToolTip(f"NovaDesk {app_ver} · AI 桌面智能助理 ({pet_name})")
        self._init_menu()

        # 双击/单击托盘图标立即唤醒并显示桌宠
        self.activated.connect(self._on_tray_activated)
        self.show()

    def set_theme(self, is_dark: bool):
        """外部同步深浅色主题"""
        self._is_dark = is_dark
        self._apply_menu_theme()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.pet:
                if hasattr(self.pet, 'set_pet_visible'):
                    self.pet.set_pet_visible(True, persist=True)
                else:
                    self.pet.show()
                    self.pet.raise_()
                    self.pet.activateWindow()
        elif reason == QSystemTrayIcon.Context:
            self._popup_menu()

    def _apply_menu_theme(self):
        """遵循主对话窗口现代极简设计规范（支持黑白双主题自适应，保持原有图标）"""
        d = self._is_dark
        bg = "#1e1e20" if d else "#ffffff"
        fg = "#f4f4f5" if d else "#0f172a"
        border = "#2e2e32" if d else "#e2e8f0"
        item_hover_bg = "#2a2a2d" if d else "#f1f5f9"
        item_hover_fg = "#ffffff" if d else "#0f172a"
        sep_bg = "#2e2e32" if d else "#e2e8f0"

        if hasattr(self, 'menu') and self.menu:
            self.menu.setStyleSheet(f"""
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
                    padding: 7px 20px;
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

    def _init_menu(self):
        self.menu = AutoCloseMenu()
        self._apply_menu_theme()

        self.menu.addAction("🌸 显示桌宠", self._show_pet)
        self.menu.addAction("💬 开启对话", self._open_chat)
        self.menu.addAction("⚙️ 控制与设置", self._open_settings)
        self.menu.addSeparator()
        self.menu.addAction("❌ 退出程序", QApplication.quit)

        self.setContextMenu(self.menu)

    def _popup_menu(self):
        # 弹出前与当前最新主题严格同步
        if self.pet and hasattr(self.pet, 'chat_window') and self.pet.chat_window:
            self._is_dark = getattr(self.pet.chat_window, '_is_dark', self._is_dark)
        elif self.config:
            self._is_dark = (self.config.get("ui_theme", "light") == "dark")
        self._apply_menu_theme()

        try:
            import ctypes
            hwnd = int(self.menu.winId()) if hasattr(self.menu, 'winId') else 0
            if hwnd:
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        self.menu.exec_(QCursor.pos())

    def _show_pet(self):
        if self.pet:
            if hasattr(self.pet, 'set_pet_visible'):
                self.pet.set_pet_visible(True, persist=True)
            else:
                self.pet.show()
                self.pet.raise_()
                self.pet.activateWindow()

    def _open_chat(self):
        if self.pet:
            self.pet._open_chat()

    def _open_settings(self):
        if self.pet:
            if hasattr(self.pet, '_open_settings'):
                self.pet._open_settings()
            elif hasattr(self.pet, 'chat_window') and self.pet.chat_window:
                if hasattr(self.pet.chat_window, 'open_settings'):
                    self.pet.chat_window.open_settings()
                elif hasattr(self.pet.chat_window, '_switch_nav'):
                    self.pet.chat_window._switch_nav(3)
                elif hasattr(self.pet.chat_window, '_switch_view'):
                    self.pet.chat_window._switch_view(2)
