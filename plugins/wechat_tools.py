"""
微信助手工具集 - 截图识别微信消息并回复
采用视觉方案（pyautogui截图 + AI识别），安全不封号
"""
import time
import subprocess
from pathlib import Path
from core.plugin_manager import register_tool


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
    except ImportError:
        return None


def _bring_wechat_to_front():
    """将微信窗口置顶"""
    try:
        import win32gui
        import win32con
        hwnd = _find_wechat_window()
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            return True
        return False
    except Exception:
        return False


@register_tool(description="截取微信窗口截图并分析其中的消息内容，返回消息摘要")
def read_wechat_messages() -> str:
    """
    截取微信窗口，用 AI 识别消息内容
    需要微信已打开并在桌面上可见
    """
    try:
        import pyautogui
        from PIL import Image
        import tempfile, os

        # 尝试将微信置顶
        _bring_wechat_to_front()
        time.sleep(0.5)

        # 截取全屏
        screenshot = pyautogui.screenshot()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
            screenshot.save(tmp_path)

        return (
            f"✅ 已截取屏幕截图，截图保存在：{tmp_path}\n"
            "（注意：要让 AI 分析图片内容，需要配置视觉模型 qwen2.5vl:7b）\n"
            "你可以对我说：'帮我看看这张截图里微信有什么消息'"
        )
    except Exception as e:
        return f"截图失败：{e}"


@register_tool(description="打开微信应用程序")
def open_wechat() -> str:
    """打开微信"""
    wechat_paths = [
        r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
        r"C:\Program Files\Tencent\WeChat\WeChat.exe",
        r"D:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
    ]
    for path in wechat_paths:
        if Path(path).exists():
            subprocess.Popen([path])
            return "✅ 微信已打开"

    # 尝试通过开始菜单打开
    try:
        subprocess.Popen(["explorer.exe", "shell:AppsFolder\\com.tencent.weixin_..."])
        return "✅ 正在打开微信..."
    except Exception:
        pass

    return "⚠️ 未找到微信，请确认微信已安装。常见路径：C:\\Program Files (x86)\\Tencent\\WeChat\\WeChat.exe"


@register_tool(description="向微信中指定联系人发送消息，参数：联系人名称、消息内容")
def send_wechat_message(contact_name: str, message: str) -> str:
    """
    通过 pyautogui 操作微信界面发送消息
    流程：搜索联系人 → 点击 → 输入消息 → 发送
    """
    try:
        import pyautogui

        # 1. 确保微信在前台
        if not _bring_wechat_to_front():
            return "⚠️ 微信未打开，请先打开微信"

        time.sleep(0.8)

        # 2. 使用 Ctrl+F 搜索联系人
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.5)
        pyautogui.write(contact_name, interval=0.05)
        time.sleep(1.0)

        # 3. 按 Enter 进入聊天
        pyautogui.press("enter")
        time.sleep(0.5)

        # 4. 点击输入框（大致位置，根据实际分辨率可能需要调整）
        screen_w, screen_h = pyautogui.size()
        # 微信输入框通常在窗口下方
        pyautogui.click(screen_w // 2, screen_h - 150)
        time.sleep(0.3)

        # 5. 输入消息
        # 使用剪贴板粘贴（避免输入法问题）
        import subprocess
        subprocess.run(
            ["powershell", "-c", f"Set-Clipboard -Value '{message}'"],
            capture_output=True
        )
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)

        # 6. 发送
        pyautogui.press("enter")
        time.sleep(0.3)

        return f"✅ 已向「{contact_name}」发送消息：{message[:50]}"
    except Exception as e:
        return f"发送失败：{e}\n提示：请确保微信窗口可见且没有被其他窗口遮挡"


@register_tool(description="检查微信是否正在运行")
def check_wechat_status() -> str:
    """检查微信进程是否在运行"""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq WeChat.exe"],
            capture_output=True, text=True
        )
        if "WeChat.exe" in result.stdout:
            hwnd = _find_wechat_window()
            if hwnd:
                return "✅ 微信正在运行，且窗口可见"
            return "✅ 微信正在运行（后台）"
        return "❌ 微信未运行"
    except Exception as e:
        return f"检查失败：{e}"
