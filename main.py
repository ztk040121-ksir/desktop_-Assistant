"""
桌面 AI 桌宠 - 主入口
项目目录: E:\Demo\desk_tools
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import os
import json
import asyncio
import threading
from pathlib import Path

# 确保项目根目录在 Python 路径中
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from core.ai_engine import AIEngine
from core.emotion_system import EmotionSystem
from core.memory_manager import MemoryManager
from core.plugin_manager import PluginManager
from core.voice_input import VoiceInput
from core.voice_output import VoiceOutput
from ui.desktop_pet import DesktopPet
from ui.system_tray import SystemTray


def load_config() -> dict:
    """加载配置文件"""
    config_path = ROOT_DIR / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict):
    """保存配置文件"""
    config_path = ROOT_DIR / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


class DeskToolsApp:
    """主应用程序管理器"""

    def __init__(self):
        self.config = load_config()
        self.save_config = save_config

        # 初始化核心组件
        print("[AI] 初始化 AI 引擎...")
        self.ai_engine = AIEngine(self.config)

        print("[DB] 初始化记忆系统...")
        self.memory_manager = MemoryManager(ROOT_DIR / "memory.db")

        print("[情感] 初始化情感系统...")
        self.emotion_system = EmotionSystem()

        print("[插件] 加载插件...")
        self.plugin_manager = PluginManager(
            ROOT_DIR / "plugins",
            self.config,
            self.ai_engine
        )
        self.plugin_manager.load_all()

        print("[语音] 初始化语音输入...")
        self.voice_input = VoiceInput(self.config)

        print("[TTS] 初始化语音输出...")
        self.voice_output = VoiceOutput(self.config)

        # 注入依赖到 AI 引擎
        self.ai_engine.set_dependencies(
            memory=self.memory_manager,
            emotion=self.emotion_system,
            plugins=self.plugin_manager
        )

        print("[OK] 所有组件初始化完成！")

    def run(self):
        """启动应用"""
        app = QApplication(sys.argv)
        app.setApplicationName("桌面AI桌宠")
        app.setQuitOnLastWindowClosed(False)

        # 创建桌面小人
        self.pet_window = DesktopPet(
            config=self.config,
            ai_engine=self.ai_engine,
            emotion_system=self.emotion_system,
            voice_input=self.voice_input,
            voice_output=self.voice_output,
            save_config_fn=self.save_config,
            plugin_manager=self.plugin_manager
        )

        # 创建系统托盘
        self.tray = SystemTray(
            app=app,
            pet_window=self.pet_window,
            config=self.config,
            ai_engine=self.ai_engine,
            plugin_manager=self.plugin_manager,
            save_config_fn=self.save_config
        )

        print("[START] 桌宠已启动！右键小人或点击托盘图标管理")
        sys.exit(app.exec())


if __name__ == "__main__":
    desk_app = DeskToolsApp()
    desk_app.run()
