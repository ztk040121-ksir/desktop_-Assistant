"""
系统托盘图标 - 右下角常驻图标，快速访问所有功能
"""
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter
from PyQt6.QtCore import Qt, QSize


def _create_tray_icon() -> QIcon:
    """生成一个简单的粉色圆形托盘图标"""
    px = QPixmap(32, 32)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # 外圆
    painter.setBrush(QColor("#ff6699"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 28, 28)
    # 内部白色猫耳
    painter.setBrush(QColor("white"))
    painter.drawEllipse(8, 8, 6, 6)
    painter.drawEllipse(18, 8, 6, 6)
    painter.end()
    return QIcon(px)


class SystemTray(QSystemTrayIcon):
    """系统托盘图标"""

    def __init__(self, app, pet_window, config, ai_engine, plugin_manager, save_config_fn):
        super().__init__(app)
        self.pet_window = pet_window
        self.config = config
        self.ai_engine = ai_engine
        self.plugin_manager = plugin_manager
        self.save_config_fn = save_config_fn

        self.setIcon(_create_tray_icon())
        pet_name = config["behavior"].get("pet_name", "小桃")
        self.setToolTip(f"🐱 {pet_name} - 桌面AI助手")

        self._build_menu()
        self.activated.connect(self._on_activated)
        self.show()

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #2d2d3f;
                color: #ffffff;
                border: 1px solid #5a5a8a;
                border-radius: 8px;
                padding: 4px;
                font-family: "Microsoft YaHei";
                font-size: 13px;
            }
            QMenu::item { padding: 7px 22px; border-radius: 4px; }
            QMenu::item:selected { background: #5a5aba; }
            QMenu::separator { height: 1px; background: #5a5a8a; margin: 4px 0; }
        """)
        pet_name = self.config["behavior"].get("pet_name", "小桃")
        menu.addAction(f"🐱 {pet_name} 已启动").setEnabled(False)
        menu.addSeparator()
        menu.addAction("💬 打开对话", self._open_chat)
        menu.addAction("⚙️ 管理中心", self._open_control_panel)
        menu.addSeparator()
        menu.addAction("👁 显示/隐藏小人", self._toggle_pet)
        menu.addSeparator()
        menu.addAction("❌ 退出", QApplication.quit)
        self.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._open_chat()

    def _open_chat(self):
        self.pet_window._open_chat()

    def _open_control_panel(self):
        self.pet_window._open_control_panel()

    def _toggle_pet(self):
        if self.pet_window.isVisible():
            self.pet_window.hide()
        else:
            self.pet_window.show()
