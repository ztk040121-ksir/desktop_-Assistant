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

# Windows App ID
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mycompany.desktools.pet.v2")
except Exception:
    pass

try:
    from PyQt5.QtCore import Qt, QCoreApplication
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        from PyQt5.QtWidgets import QApplication
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QIcon
except ImportError:
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt, QCoreApplication
        from PyQt6.QtGui import QIcon
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

    try:
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
    except Exception:
        pass

    if ICON_PATH.exists():
        _GLOBAL_APP.setWindowIcon(QIcon(str(ICON_PATH)))

    memory_manager = MemoryManager(DB_PATH)
    ai_engine = AIEngine(config)
    emotion_system = EmotionSystem()
    voice_input = VoiceInput(config)
    voice_output = VoiceOutput(config)
    plugin_manager = PluginManager(PLUGINS_DIR, config, ai_engine)
    
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
    print("Desktop AI Assistant (NovaDesk v3.0) Running!")
    print("==================================================")

    sys.exit(_GLOBAL_APP.exec_())


if __name__ == "__main__":
    main()
