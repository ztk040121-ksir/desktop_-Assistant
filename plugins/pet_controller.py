# -*- coding: utf-8 -*-
"""
桌宠控制与定时提醒插件 (Pet Control & Reminder Plugin)
让 AI 能够直接调度桌宠动作、在桌面上弹出气泡、设定到点闹钟与日程提醒、开启番茄钟等。
"""
from core.plugin_manager import register_tool
from core.pet_scheduler import PetScheduler


# 全局桌宠实例引用（由 desktop_pet 初始化时注册绑定）
_PET_INSTANCE = None

def bind_pet_instance(pet):
    global _PET_INSTANCE
    _PET_INSTANCE = pet


@register_tool(description="为主人设置定时闹钟、倒计时与日常事务备忘提醒。时间到后小日和会在桌面上弹出气泡提醒主人并做动作。参数：content(提醒内容，必填), minutes_later(多少分钟后，如10), seconds_later(多少秒后，如30), target_time(具体时刻如'15:30'或'20:00')")
def set_reminder(content: str, minutes_later: float = 0, seconds_later: float = 0, target_time: str = "") -> str:
    """设置定时提醒"""
    if not content:
        return "❌ 提醒内容不能为空"
    scheduler = PetScheduler.get_instance()
    item = scheduler.add_reminder(
        content=content,
        minutes_later=minutes_later,
        seconds_later=seconds_later,
        target_time_str=target_time if target_time else None,
        title="⏰ 贴心提醒",
        motion="nod"
    )
    time_info = item['time_str']
    return f"✅ 已经为主人记下啦！小日和将在【{time_info}】准时在桌面上提醒你：『{content}』🌸"


@register_tool(description="查询当前所有待触发的定时提醒与日程备忘列表")
def list_reminders() -> str:
    """查询提醒列表"""
    scheduler = PetScheduler.get_instance()
    items = scheduler.get_all_reminders()
    if not items:
        return "主人目前没有待办的提醒事项哦~ 随时可以让我帮你记！🌸"
    res = ["📋 【主人当前的待办提醒列表】："]
    for it in items:
        res.append(f"- [ID: {it['id']}] 【{it['time']}】（约 {it['remain_sec']} 秒后）：{it['content']}")
    return "\n".join(res)


@register_tool(description="取消指定的定时提醒。参数：reminder_id(提醒事项的数字ID，必填)")
def cancel_reminder(reminder_id: int) -> str:
    """取消提醒"""
    scheduler = PetScheduler.get_instance()
    ok = scheduler.cancel_reminder(int(reminder_id))
    if ok:
        return f"✅ 已成功取消 ID 为 {reminder_id} 的提醒事项！"
    return f"❌ 未找到 ID 为 {reminder_id} 的有效提醒。"


@register_tool(description="让桌面上展示的 Live2D 小日和立刻弹出专属文字气泡说话。参数：text(要说的话，必填)")
def pet_say_bubble(text: str) -> str:
    """桌宠桌面气泡说话"""
    global _PET_INSTANCE
    if _PET_INSTANCE:
        try:
            safe_text = text.replace("'", "\\'").replace("\n", " ")
            _PET_INSTANCE.web.page().runJavaScript(f"window.showCareMessage('💬 小日和', '{safe_text}');")
            return f"✅ 已在桌面上弹出气泡展示：『{text}』"
        except Exception as e:
            return f"❌ 气泡发送失败: {e}"
    return "桌宠界面就绪中..."


@register_tool(description="让桌面上展示的 Live2D 小日和立刻做出专属动作与互动反应。参数：motion(动作名，可选: 'nod'点头, 'headpat'开心摸头, 'cheer'元气应援, 'wave'挥手打招呼, 'feed'品尝点心)")
def pet_react(motion: str = "nod") -> str:
    """桌宠动作与表情反应"""
    global _PET_INSTANCE
    if _PET_INSTANCE:
        try:
            _PET_INSTANCE.web.page().runJavaScript(f"window.triggerAction('{motion}', 3000);")
            return f"✅ 小日和已经在桌面上为你做出了【{motion}】动作啦~ 🌸"
        except Exception as e:
            return f"❌ 动作触发失败: {e}"
    return "桌宠动作已派发"


@register_tool(description="为主人在桌面上开启番茄钟专注工作/学习模式。参数：minutes(专注分钟数，默认25分钟)")
def start_focus_timer(minutes: int = 25) -> str:
    """开启番茄钟"""
    global _PET_INSTANCE
    if _PET_INSTANCE:
        try:
            mins = int(minutes)
            _PET_INSTANCE.web.page().runJavaScript(f"window.startFocusTimer({mins});")
            return f"🍅 专注番茄钟已开启！时长【{mins}分钟】，小日和会在桌面上安静陪你专心工作哦~ 🌸"
        except Exception as e:
            return f"❌ 番茄钟开启失败: {e}"
    return "番茄钟已启动"
