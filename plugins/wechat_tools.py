# -*- coding: utf-8 -*-
"""
微信桌面助手工具集 (WeChat Automation Tools)
支持微信窗口检测、置顶、Unicode 剪贴板安全暂存/注入、以及消息自动化发送
"""
import time
import subprocess
from pathlib import Path
from core.plugin_manager import register_tool


def _get_clipboard_text() -> str:
    """获取当前系统剪贴板文本（用于备份）"""
    try:
        import win32clipboard
        import win32con
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            return data or ""
        win32clipboard.CloseClipboard()
    except Exception:
        pass
    try:
        import pyperclip
        return pyperclip.paste() or ""
    except Exception:
        pass
    return ""


def _set_clipboard_text(text: str) -> bool:
    """写入 Unicode 文本至系统剪贴板（100% 支持中文字符与长文本）"""
    # 方式 1: pywin32 win32clipboard
    try:
        import win32clipboard
        import win32con
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        return True
    except Exception:
        pass

    # 方式 2: pyperclip
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        pass

    # 方式 3: PyQt5
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.clipboard().setText(text)
            return True
    except Exception:
        pass

    return False


def _find_wechat_window():
    """查找微信窗口句柄"""
    try:
        import win32gui
        def callback(hwnd, result):
            title = win32gui.GetWindowText(hwnd)
            if "微信" in title and win32gui.IsWindowVisible(hwnd):
                result.append(hwnd)
        result = []
        win32gui.EnumWindows(callback, result)
        return result[0] if result else None
    except Exception:
        return None


def _bring_wechat_to_front():
    """将微信窗口激活并置顶在前台"""
    try:
        import win32gui
        import win32con
        hwnd = _find_wechat_window()
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.4)
            return hwnd
        return None
    except Exception:
        return None


@register_tool(description="截取微信当前窗口屏幕并保存为图像文件。")
def read_wechat_messages() -> str:
    """截取微信窗口截图"""
    try:
        import pyautogui
        import tempfile

        hwnd = _bring_wechat_to_front()
        time.sleep(0.5)

        screenshot = pyautogui.screenshot()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
            screenshot.save(tmp_path)

        return (
            f"✅ 已成功截取微信窗口屏幕，截图保存于：`{tmp_path}`\n"
            "💡 *提示：要让 AI 深度识别并提炼图片中的聊天文字，请在设置中配置视觉多模态大模型（如 Qwen2.5-VL / DeepSeek-VL）。*"
        )
    except Exception as e:
        return f"❌ 微信截图失败：{e}"


@register_tool(description="打开微信桌面客户端应用程序。")
def open_wechat() -> str:
    """打开微信"""
    wechat_paths = [
        r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
        r"C:\Program Files\Tencent\WeChat\WeChat.exe",
        r"D:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
        r"D:\Program Files\Tencent\WeChat\WeChat.exe"
    ]
    for path in wechat_paths:
        if Path(path).exists():
            subprocess.Popen([path])
            return "✅ 微信客户端已成功启动！"

    try:
        subprocess.Popen(["explorer.exe", "shell:AppsFolder\\com.tencent.weixin_..."])
        return "✅ 正在通过应用快捷方式启动微信..."
    except Exception:
        pass

    return "⚠️ 未在常见路径找到微信，请确认微信已安装并正在运行。"


@register_tool(description="向微信中指定的中文联系人/好友/群聊发送消息。参数：contact_name(联系人或群名称)，message(需要发送的消息文本)")
def send_wechat_message(contact_name: str, message: str) -> str:
    """向微信联系人发送消息（支持中文联系人、并在发送后自动恢复用户原有剪贴板内容）"""
    c_name = contact_name.strip()
    msg = message.strip()
    if not c_name or not msg:
        return "⚠️ 请提供有效的联系人名称和消息内容。"

    # 1. 备份用户原有剪贴板内容
    user_clip_backup = _get_clipboard_text()

    try:
        import pyautogui

        # 2. 激活微信到前台
        hwnd = _bring_wechat_to_front()
        if not hwnd:
            return "⚠️ 微信客户端未启动或窗口不可见，请先登录并打开微信。"

        time.sleep(0.5)

        # 3. 搜索联系人 (Ctrl+F) 并通过剪贴板安全粘贴中文联系人名
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.3)
        _set_clipboard_text(c_name)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.8)

        # 4. 回车选中第一个匹配项进入聊天窗口
        pyautogui.press("enter")
        time.sleep(0.5)

        # 5. 写入消息文本并发送
        _set_clipboard_text(msg)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.2)

        return f"✅ 已成功向微信好友/群聊「**{c_name}**」发送消息：\n> {msg[:80]}{('...' if len(msg) > 80 else '')}"
    except Exception as e:
        return f"❌ 微信消息发送异常：{e}\n*提示：请确保微信窗口处于前台且联系人名称准确。*"
    finally:
        # 6. 恢复用户原有剪贴板内容
        if user_clip_backup:
            _set_clipboard_text(user_clip_backup)


@register_tool(description="检查微信客户端当前是否处于运行状态。")
def check_wechat_status() -> str:
    """检查微信进程与窗口状态"""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq WeChat.exe"],
            capture_output=True, text=True, errors="ignore"
        )
        if "WeChat.exe" in result.stdout:
            hwnd = _find_wechat_window()
            if hwnd:
                return "✅ 微信正在运行中，且窗口处于前台可用状态。"
            return "✅ 微信正在后台运行中。"
        return "❌ 微信客户端当前未运行。"
    except Exception as e:
        return f"检查状态失败：{e}"
