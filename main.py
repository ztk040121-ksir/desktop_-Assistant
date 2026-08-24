# -*- coding: utf-8 -*-
import sys
import json
import ctypes
from pathlib import Path

# 设置 Windows 任务栏应用组 ID，确保任务栏图标正常显示
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mycompany.desktools.pet.v2")
except Exception:
    pass

try:
    from PyQt5.QtCore import Qt
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        from PyQt5.QtWidgets import QApplication
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QIcon
except ImportError:
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
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
ICON_PATH = ROOT_DIR / "assets" / "icons" / "pet_icon.png"

_GLOBAL_APP = None
_GLOBAL_PET = None
_GLOBAL_TRAY = None


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config_data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)


def main():
    global _GLOBAL_APP, _GLOBAL_PET, _GLOBAL_TRAY

    config = load_config()

    _GLOBAL_APP = QApplication(sys.argv)
    _GLOBAL_APP.setQuitOnLastWindowClosed(False)

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

    print("==================================================")
    print("Desktop AI Assistant (Live2D Hiyori) Running!")
    print("==================================================")

    sys.exit(_GLOBAL_APP.exec_())


if __name__ == "__main__":
    main()
