# -*- coding: utf-8 -*-
"""
系统托盘图标与全局菜单
"""
from pathlib import Path
try:
    from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QApplication
    from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
    from PyQt5.QtCore import Qt
except ImportError:
    from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
    from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
    from PyQt6.QtCore import Qt

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


class SystemTray(QSystemTrayIcon):
    def __init__(self, app, pet_window, config, save_config_fn):
        super().__init__()
        self.app = app
        self.pet = pet_window
        self.config = config
        self.save_config_fn = save_config_fn

        icon_path = ROOT_DIR / "assets" / "icons" / "app_logo.png"
        if icon_path.exists():
            self.setIcon(QIcon(str(icon_path)))
        else:
            self.setIcon(create_fallback_icon())

        pet_name = self.config.get("behavior", {}).get("pet_name", "桃濑日和")
        app_ver = self.config.get("app_version", "v3.0")
        self.setToolTip(f"NovaDesk {app_ver} · AI 桌面智能助理 ({pet_name})")
        self._init_menu()

        # 双击托盘图标立即唤醒并显示桌宠！
        self.activated.connect(self._on_tray_activated)
        self.show()

    def _on_tray_activated(self, reason):
        # 单击或双击托盘图标唤醒桌宠
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.pet:
                self.pet.show()
                self.pet.raise_()
                self.pet.activateWindow()

    def _init_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: rgba(22, 20, 42, 245);
                color: #eae8f8;
                border: 1px solid rgba(160, 130, 255, 0.35);
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
                background: rgba(140, 110, 255, 0.35);
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(160, 130, 255, 0.2);
                margin: 4px 6px;
            }
        """)

        menu.addAction("🌸 显示桌宠", self._show_pet)
        menu.addAction("💬 开启对话", self._open_chat)
        menu.addAction("⚙️ 控制与设置", self._open_settings)
        menu.addSeparator()
        menu.addAction("❌ 退出程序", QApplication.quit)

        self.setContextMenu(menu)

    def _show_pet(self):
        if self.pet:
            self.pet.show()
            self.pet.raise_()
            self.pet.activateWindow()

    def _open_chat(self):
        if self.pet:
            self.pet._open_chat()

    def _open_settings(self):
        if self.pet and hasattr(self.pet, 'chat_window'):
            self.pet.chat_window.open_settings()
