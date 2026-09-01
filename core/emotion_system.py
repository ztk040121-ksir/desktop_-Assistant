# -*- coding: utf-8 -*-
"""
情绪状态系统 - 虚拟宠物与智能体情绪联动
"""
import random
from datetime import datetime
from enum import Enum
from typing import List, Callable


class EmotionState(Enum):
    IDLE = "idle"           # 待命/闲适
    TALKING = "talking"     # 正在对话
    HAPPY = "happy"         # 开心/欢快
    SLEEPY = "sleepy"       # 困倦/休息
    WORKING = "working"     # 专注工作中
    SHY = "shy"             # 害羞/谦逊
    SAD = "sad"             # 委屈/低落


HAPPY_TRIGGERS = ["谢谢", "太棒了", "真好", "喜欢", "厉害", "牛", "成功", "棒", "不错", "搞定", "感谢"]
SAD_TRIGGERS = ["笨", "错", "失败", "差", "没用", "烦", "讨厌", "报错", "异常"]
SHY_TRIGGERS = ["漂亮", "好看", "可爱", "夸你", "聪明", "帅", "美"]
SLEEPY_TRIGGERS = ["去睡吧", "晚安", "困了", "休息吧", "睡觉"]
WORKING_TRIGGERS = ["生成", "开发", "代码", "测试", "自动化", "执行", "分析", "撰写", "编写", "搜索", "运行"]


class EmotionSystem:
    """情绪状态系统"""

    def __init__(self):
        self.current_emotion = EmotionState.IDLE
        self.emotion_callbacks: List[Callable] = []
        self._last_interaction = datetime.now()

    def get_current_emotion(self) -> str:
        """获取当前情绪状态字符串描述（供 AI Engine 与 UI 安全调用）"""
        if isinstance(self.current_emotion, EmotionState):
            mapping = {
                EmotionState.IDLE: "待命 (idle)",
                EmotionState.TALKING: "正在对话 (talking)",
                EmotionState.HAPPY: "开心愉悦 (happy)",
                EmotionState.SLEEPY: "稍事休息 (sleepy)",
                EmotionState.WORKING: "专注工作中 (working)",
                EmotionState.SHY: "谦逊害羞 (shy)",
                EmotionState.SAD: "略感委屈 (sad)"
            }
            return mapping.get(self.current_emotion, self.current_emotion.value)
        return str(self.current_emotion)

    def on_emotion_change(self, callback: Callable):
        """注册情绪变化回调"""
        self.emotion_callbacks.append(callback)

    def _emit(self, emotion: EmotionState):
        """触发情绪变化并通知所有监听者"""
        self.current_emotion = emotion
        for cb in self.emotion_callbacks:
            try:
                cb(emotion)
            except Exception as e:
                print(f"[Emotion callback error] {e}")

    def update_by_text(self, text: str):
        """根据用户输入的文本智能推断并更新情绪"""
        self._last_interaction = datetime.now()
        t = text.lower()
        if any(w in t for w in HAPPY_TRIGGERS):
            self._emit(EmotionState.HAPPY)
        elif any(w in t for w in SAD_TRIGGERS):
            self._emit(EmotionState.SAD)
        elif any(w in t for w in SHY_TRIGGERS):
            self._emit(EmotionState.SHY)
        elif any(w in t for w in SLEEPY_TRIGGERS):
            self._emit(EmotionState.SLEEPY)
        elif any(w in t for w in WORKING_TRIGGERS):
            self._emit(EmotionState.WORKING)
        else:
            self._emit(EmotionState.TALKING)

    def reset_to_idle(self):
        """重置回待命状态"""
        self._emit(EmotionState.IDLE)
