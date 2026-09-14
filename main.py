# -*- coding: utf-8 -*-
import os
import sys

# Configure Chromium engine parameters to use memory cache & prevent file locking
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--disable-gpu-shader-disk-cache "
    "--disable-gpu-program-cache "
    "--disable-features=CookiesDatabase "
    "--incognito "
    "--disk-cache-size=1 "
    "--media-cache-size=1 "
    "--no-sandbox "
    "--disable-logging"
)

import json
import ctypes
from pathlib import Path

# Windows High-DPI Per-Monitor V2 Awareness & App ID
try:
    # 启用 Windows 原生 Per-Monitor V2 DPI 感知，彻底禁止系统级位图模糊插值拉伸
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mycompany.desktools.pet.v2")
except Exception:
    pass

try:
    from PyQt5.QtCore import Qt, QCoreApplication
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QIcon, QFont
    # 全局开启 Qt 高分屏动态缩放与高清 Pixmap 采样
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    # 支持 125%、150% 等非整数缩放平滑穿透，杜绝四舍五入为 100% 导致大屏上变极小
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy') and hasattr(QApplication, 'setHighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile
except ImportError:
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt, QCoreApplication
        from PyQt6.QtGui import QIcon, QFont
    except Exception:
        pass

from core.ai_engine import AIEngine
from core.memory_manager import MemoryManager
from core.emotion_system import EmotionSystem
from core.voice_input import VoiceInput
from core.voice_output import VoiceOutput
from core.plugin_manager import PluginManager
from ui.desktop_pet import DesktopPet
from ui.system_tray import SystemTray

ROOT_DIR = Path(__file__).parent
CONFIG_PATH = ROOT_DIR / "config.json"
DB_PATH = ROOT_DIR / "memory.db"
PLUGINS_DIR = ROOT_DIR / "plugins"
ICON_PATH = ROOT_DIR / "assets" / "icons" / "app_logo.png"

_GLOBAL_APP = None
_GLOBAL_PET = None
_GLOBAL_TRAY = None


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"配置文件未找到: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config_data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)


def main():
    global _GLOBAL_APP, _GLOBAL_PET, _GLOBAL_TRAY

    config = load_config()

    # Set unique app name per PID to prevent Chromium database lock conflicts across processes
    QCoreApplication.setOrganizationName("WorkBuddyAI")
    QCoreApplication.setApplicationName(f"DeskPet_{os.getpid()}")

    _GLOBAL_APP = QApplication(sys.argv)
    _GLOBAL_APP.setQuitOnLastWindowClosed(False)

    # 全局字体注入 ClearType 次像素平滑抗锯齿策略，确保字体锐利饱满无毛刺
    app_font = QFont("Microsoft YaHei UI", 9)
    app_font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
    _GLOBAL_APP.setFont(app_font)

    try:
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
    except Exception:
        pass

    if ICON_PATH.exists():
        _GLOBAL_APP.setWindowIcon(QIcon(str(ICON_PATH)))

    memory_manager = MemoryManager(DB_PATH)
    try:
        retention_days = config.get("behavior", {}).get("history_retention_days") or config.get("history_retention_days", 25)
        clean_res = memory_manager.cleanup_expired_history(days=retention_days)
        if clean_res.get("deleted_sessions") or clean_res.get("deleted_messages"):
            print(f"[Main] 启动自动清理超过 {retention_days} 天的历史会话/消息: {clean_res}")
    except Exception as _ce:
        print(f"[Main] 自动清理过期历史失败: {_ce}")

    ai_engine = AIEngine(config)
    emotion_system = EmotionSystem()
    voice_input = VoiceInput(config)
    voice_output = VoiceOutput(config)
    plugin_manager = PluginManager(PLUGINS_DIR, config, ai_engine)
    plugin_manager.load_all()
    
    ai_engine.set_dependencies(memory=memory_manager, emotion=emotion_system, plugins=plugin_manager)

    _GLOBAL_PET = DesktopPet(
        config=config,
        ai_engine=ai_engine,
        emotion_system=emotion_system,
        voice_input=voice_input,
        voice_output=voice_output,
        save_config_fn=save_config,
        plugin_manager=plugin_manager
    )

    _GLOBAL_TRAY = SystemTray(
        app=_GLOBAL_APP,
        pet_window=_GLOBAL_PET,
        config=config,
        save_config_fn=save_config
    )
    _GLOBAL_PET.tray_icon = _GLOBAL_TRAY

    print("==================================================")
    print("Desktop AI Assistant (NovaDesk v4.0) Running!")
    print("==================================================")

    sys.exit(_GLOBAL_APP.exec_())


if __name__ == "__main__":
    main()
