"""
情感状态机 - 管理桌宠的情绪和动画状态
"""
import random
from datetime import datetime
from enum import Enum


class EmotionState(Enum):
    IDLE = "idle"           # 待机
    TALKING = "talking"     # 说话中
    HAPPY = "happy"         # 开心
    SLEEPY = "sleepy"       # 困倦
    WORKING = "working"     # 专注工作
    SHY = "shy"             # 害羞
    SAD = "sad"             # 委屈


# 情感触发关键词
HAPPY_TRIGGERS = ["谢谢", "太棒了", "厉害", "好的", "完成", "成功", "棒", "很好", "完美"]
SAD_TRIGGERS = ["不对", "错了", "失败", "不好", "差劲", "笨", "烦"]
SHY_TRIGGERS = ["你真漂亮", "你好可爱", "喜欢你", "爱你"]
SLEEPY_TRIGGERS = ["去睡觉", "晚安", "休息", "累了"]


class EmotionSystem:
    """情感状态机"""

    def __init__(self):
        self.current_emotion = EmotionState.IDLE
        self.emotion_callbacks = []  # 情感变化时通知 UI
        self._last_interaction = datetime.now()

    def on_emotion_change(self, callback):
        """注册情感变化回调（UI 用）"""
        self.emotion_callbacks.append(callback)

    def _emit(self, emotion: EmotionState):
        """触发情感变化"""
        if self.current_emotion != emotion:
            self.current_emotion = emotion
            for cb in self.emotion_callbacks:
                cb(emotion)

    def update_from_reply(self, reply: str):
        """根据 AI 回复内容更新情绪"""
        self._last_interaction = datetime.now()

        # 检查回复中是否包含情感触发词
        for word in HAPPY_TRIGGERS:
            if word in reply:
                self._emit(EmotionState.HAPPY)
                return

        for word in SAD_TRIGGERS:
            if word in reply:
                self._emit(EmotionState.SAD)
                return

        # 回复较长时进入工作状态
        if len(reply) > 200:
            self._emit(EmotionState.WORKING)
        else:
            self._emit(EmotionState.TALKING)

    def update_from_user_input(self, text: str):
        """根据用户输入更新情绪"""
        for word in SHY_TRIGGERS:
            if word in text:
                self._emit(EmotionState.SHY)
                return
        for word in SLEEPY_TRIGGERS:
            if word in text:
                self._emit(EmotionState.SLEEPY)
                return
        self._emit(EmotionState.TALKING)

    def set_talking(self):
        self._emit(EmotionState.TALKING)

    def set_idle(self):
        self._emit(EmotionState.IDLE)

    def set_working(self):
        self._emit(EmotionState.WORKING)

    def check_idle_behavior(self) -> str | None:
        """
        检查是否需要自主行为（主动说话）
        返回要说的话，或 None 表示不说
        """
        now = datetime.now()
        minutes_idle = (now - self._last_interaction).total_seconds() / 60

        hour = now.hour
        idle_phrases = []

        # 根据时间段和空闲时长选择对话
        if hour >= 23 or hour < 6:
            idle_phrases = [
                "已经这么晚了，要注意休息哦~",
                "夜深了，你还在工作吗？👀",
                "记得早点睡觉，明天还要上班呢~"
            ]
        elif hour >= 6 and hour < 9:
            idle_phrases = [
                "早上好！今天也要加油哦 ☀️",
                "早餐吃了吗？要记得吃哦~"
            ]
        elif hour >= 12 and hour < 13:
            idle_phrases = [
                "到午饭时间啦，去吃点东西吧~",
                "休息一下，不要忘记吃午饭！"
            ]
        elif hour >= 18 and hour < 19:
            idle_phrases = [
                "下班时间到啦，今天辛苦了~",
                "记得准时下班，注意身体！"
            ]
        elif minutes_idle > 30:
            idle_phrases = [
                "你还在吗？我有点想你了呢~",
                f"已经 {int(minutes_idle)} 分钟没理我了，在忙什么呀？",
                "眼睛累了的话记得休息一下哦~",
                "久坐伤身，要不要起来走走？"
            ]

        if idle_phrases and random.random() < 0.3:  # 30% 概率触发
            self._last_interaction = now
            return random.choice(idle_phrases)
        return None

    @property
    def animation_name(self) -> str:
        """返回当前情绪对应的动画名"""
        return self.current_emotion.value
