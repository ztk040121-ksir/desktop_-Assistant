"""
电脑控制工具集 - 鼠标/键盘控制、截图、打开程序、文件搜索
使用 @register_tool 注册的工具可以直接被小人调用
"""
import os
import subprocess
import glob
from pathlib import Path
from core.plugin_manager import register_tool


@register_tool(description="截取当前屏幕截图，保存到桌面并返回路径")
def take_screenshot() -> str:
    try:
        import pyautogui
        from datetime import datetime
        desktop = Path.home() / "Desktop"
        filename = f"截图_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        save_path = desktop / filename
        screenshot = pyautogui.screenshot()
        screenshot.save(str(save_path))
        return f"✅ 截图已保存到桌面：{filename}"
    except Exception as e:
        return f"截图失败：{e}"


@register_tool(description="打开指定的应用程序或文件，参数为应用名称或路径")
def open_application(app_name: str) -> str:
    """
    支持：微信、记事本、计算器、浏览器、文件路径等
    """
    app_map = {
        "微信": r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
        "钉钉": r"C:\Program Files\DingDing\DingTalk.exe",
        "记事本": "notepad.exe",
        "计算器": "calc.exe",
        "画图": "mspaint.exe",
        "资源管理器": "explorer.exe",
        "命令提示符": "cmd.exe",
        "浏览器": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    }
    target = app_map.get(app_name, app_name)
    try:
        if os.path.exists(target):
            subprocess.Popen([target])
        else:
            os.startfile(target)
        return f"✅ 已打开：{app_name}"
    except Exception as e:
        return f"打开失败：{e}"


@register_tool(description="在电脑上搜索文件，参数为文件名或关键词，返回找到的文件路径列表")
def search_files(keyword: str, search_dir: str = "C:/") -> str:
    try:
        results = []
        # 搜索用户常用目录（不全盘搜索，太慢）
        search_paths = [
            Path.home() / "Desktop",
            Path.home() / "Documents",
            Path.home() / "Downloads",
            Path("D:/"),
            Path("E:/"),
        ]
        for base in search_paths:
            if not base.exists():
                continue
            for p in base.rglob(f"*{keyword}*"):
                results.append(str(p))
                if len(results) >= 10:
                    break
            if len(results) >= 10:
                break

        if not results:
            return f"未找到包含「{keyword}」的文件"
        return "找到以下文件：\n" + "\n".join(results[:10])
    except Exception as e:
        return f"搜索失败：{e}"


@register_tool(description="打开指定的文件夹，参数为文件夹路径")
def open_folder(folder_path: str) -> str:
    try:
        path = Path(folder_path)
        if not path.exists():
            return f"文件夹不存在：{folder_path}"
        os.startfile(str(path))
        return f"✅ 已打开文件夹：{folder_path}"
    except Exception as e:
        return f"打开失败：{e}"


@register_tool(description="用鼠标点击屏幕指定坐标位置，参数为 x 和 y 坐标")
def click_position(x: int, y: int) -> str:
    try:
        import pyautogui
        pyautogui.click(x, y)
        return f"✅ 已点击坐标 ({x}, {y})"
    except Exception as e:
        return f"点击失败：{e}"


@register_tool(description="在当前焦点位置输入文字，参数为要输入的文字内容")
def type_text(text: str) -> str:
    try:
        import pyautogui
        import time
        time.sleep(0.3)
        pyautogui.write(text, interval=0.05)
        return f"✅ 已输入文字：{text[:30]}..."
    except Exception as e:
        return f"输入失败：{e}"


@register_tool(description="获取当前屏幕分辨率")
def get_screen_size() -> str:
    try:
        import pyautogui
        w, h = pyautogui.size()
        return f"当前屏幕分辨率：{w} x {h}"
    except Exception as e:
        return f"获取失败：{e}"


@register_tool(description="列出桌面上的所有文件和文件夹")
def list_desktop() -> str:
    try:
        desktop = Path.home() / "Desktop"
        items = list(desktop.iterdir())
        files = [f.name for f in items if f.is_file()]
        folders = [f.name for f in items if f.is_dir()]
        result = f"桌面上共有 {len(items)} 个项目：\n"
        if folders:
            result += f"\n📁 文件夹（{len(folders)}个）：\n" + "\n".join(f"  {f}" for f in folders[:10])
        if files:
            result += f"\n📄 文件（{len(files)}个）：\n" + "\n".join(f"  {f}" for f in files[:10])
        return result
    except Exception as e:
        return f"获取失败：{e}"
