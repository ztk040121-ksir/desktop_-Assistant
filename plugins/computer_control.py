# -*- coding: utf-8 -*-
"""
全能电脑与桌面日常高效控制工具集 (Desktop Automation & System Assistant)
支持常用软件极速启停、音量调节、静音、锁屏、截屏、清空回收站、桌面/近期文件智能查找等。
"""
import os
import subprocess
import ctypes
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from core.plugin_manager import register_tool


def _scan_all_shortcuts() -> Dict[str, str]:
    """扫描 Windows 开始菜单与桌面上的所有快捷方式 (.lnk)"""
    start_menus = [
        Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
        Path(os.environ.get("PROGRAMDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
        Path.home() / "Desktop",
        Path.home() / "Desktop" / "饭碗",
        Path(os.environ.get("PUBLIC", "")) / "Desktop"
    ]
    apps = {}
    for sm in start_menus:
        if not sm.exists():
            continue
        for lnk in sm.rglob("*.lnk"):
            clean_stem = lnk.stem.lower().replace(" - 快捷方式", "").replace("快捷方式", "").strip()
            apps[clean_stem] = str(lnk)
            # 兼容英文别名
            if "wechat" in clean_stem:
                apps["微信"] = str(lnk)
                apps["wechat"] = str(lnk)
            elif "visual studio code" in clean_stem or "code" in clean_stem:
                apps["vscode"] = str(lnk)
                apps["vs code"] = str(lnk)
            elif "cloudmusic" in clean_stem or "网易云" in clean_stem:
                apps["网易云音乐"] = str(lnk)
                apps["网易云"] = str(lnk)
            elif "qqmusic" in clean_stem or "qq音乐" in clean_stem:
                apps["qq音乐"] = str(lnk)
            elif "汽水音乐" in clean_stem:
                apps["汽水音乐"] = str(lnk)
    return apps


@register_tool(description="截取当前屏幕截图，保存到桌面并打开图片预览")
def take_screenshot() -> str:
    """屏幕截图"""
    try:
        desktop = Path.home() / "Desktop"
        filename = f"日和截图_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        save_path = desktop / filename
        
        captured = False
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot.save(str(save_path))
            captured = True
        except Exception:
            pass

        if not captured:
            # 唤起 Windows 截图快捷键
            subprocess.Popen(["explorer.exe", "ms-screenclip:"])
            return "📸 已为你唤起 Windows 原生快速截图工具 (Win+Shift+S)，请框选截图区域~ 🌸"

        # 打开截图文件
        try:
            os.startfile(str(save_path))
        except Exception:
            pass

        return f"📸 截图已成功保存到桌面：`{filename}` 并已为你打开预览！🌸"
    except Exception as e:
        return f"❌ 截图失败：{e}"


@register_tool(description="打开常用的电脑应用程序。参数：app_name(软件名称，如'微信'、'网易云音乐'、'VS Code'、'vscode'、'QQ音乐'、'汽水音乐'、'浏览器'、'记事本'、'计算器'、'任务管理器')")
def open_application(app_name: str) -> str:
    """极速启动指定应用程序"""
    app_clean = app_name.strip().lower()
    
    # 1. 扫描系统快捷方式表 (.lnk)
    shortcut_map = _scan_all_shortcuts()
    for name, lnk_path in shortcut_map.items():
        if app_clean == name or app_clean in name or name in app_clean:
            try:
                os.startfile(lnk_path)
                return f"✅ 已成功启动：{app_name} 🌸"
            except Exception:
                pass

    # 2. 系统内置应用表
    sys_apps = {
        "记事本": "notepad.exe",
        "计算器": "calc.exe",
        "任务管理器": "taskmgr.exe",
        "画图": "mspaint.exe",
        "命令行": "cmd.exe",
        "终端": "cmd.exe",
        "资源管理器": "explorer.exe",
        "浏览器": "https://www.baidu.com"
    }
    for k, v in sys_apps.items():
        if k in app_clean or app_clean in k:
            try:
                os.startfile(v)
                return f"✅ 已成功启动：{app_name} 🌸"
            except Exception:
                pass

    # 3. 常见路径探测
    username = os.getenv("USERNAME", "Administrator")
    hardcoded_candidates = {
        "微信": [
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\微信\微信.lnk",
            r"C:\Program Files\Tencent\WeChat\WeChat.exe",
            r"C:\Program Files (x86)\Tencent\WeChat\WeChat.exe",
            "weixin:"
        ],
        "vs code": [
            r"E:\Study_Cache\visual_studio\Microsoft VS Code\Code.exe",
            rf"C:\Users\{username}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
            "code"
        ]
    }
    for k, paths in hardcoded_candidates.items():
        if k in app_clean or app_clean in k:
            for p in paths:
                try:
                    if os.path.exists(p) or p.startswith("weixin:"):
                        os.startfile(p)
                        return f"✅ 已成功启动：{app_name} 🌸"
                except Exception:
                    continue

    try:
        os.startfile(app_name)
        return f"✅ 已尝试为你启动：{app_name} 🌸"
    except Exception:
        return f"❌ 未能找到【{app_name}】的快捷方式或安装路径，请确认是否已安装或放在桌面。"


@register_tool(description="控制电脑系统音量与静音。参数：action(可选: 'up'增大音量, 'down'减小音量, 'mute'一键静音/取消静音)")
def control_system_volume(action: str = "up") -> str:
    """控制电脑音量"""
    try:
        act = action.lower()
        if "静音" in act or act == "mute":
            ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)
            return "🔇 已为你切换电脑静音状态！🌸"
        elif "小" in act or "减" in act or act == "down":
            for _ in range(4):
                ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)
            return "🔉 已为你调小电脑音量~"
        else:
            for _ in range(4):
                ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
            return "🔊 已为你调大电脑音量！🌸"
    except Exception as e:
        return f"❌ 音量调节失败: {e}"


@register_tool(description="一键锁定电脑屏幕(Lock Screen)")
def lock_screen() -> str:
    """锁屏"""
    try:
        ctypes.windll.user32.LockWorkStation()
        return "🔒 电脑屏幕已成功锁定！主人外出记得注意安全哦~ 🌸"
    except Exception as e:
        return f"❌ 锁屏失败: {e}"


@register_tool(description="一键清空 Windows 系统的回收站，释放磁盘垃圾空间")
def empty_recycle_bin() -> str:
    """清空回收站"""
    try:
        flags = 7
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        return "🗑️ 回收站已彻底清空，电脑又变得干干净净啦！🌸"
    except Exception as e:
        return f"❌ 清空回收站失败: {e}"


@register_tool(description="智能查找电脑桌面与常用目录中的最近文件。参数：keyword(关键词)，time_range(可选: 'yesterday'昨天, 'today'今天, 'week'本周, 'all'全部)，file_type(可选: 'excel'表格, 'word'文档, 'pdf', 'image'图片, 'all'全部)")
def find_recent_files(keyword: str = "", time_range: str = "all", file_type: str = "all") -> str:
    """智能文件查找"""
    try:
        search_dirs = [
            Path.home() / "Desktop",
            Path.home() / "Desktop" / "饭碗",
            Path.home() / "Downloads",
            Path.home() / "Documents",
            Path("E:/Demo"),
            Path("D:/Demo")
        ]
        
        now = datetime.now()
        yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_end = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        ext_map = {
            "excel": [".xlsx", ".xls", ".csv"],
            "word": [".docx", ".doc"],
            "pdf": [".pdf"],
            "ppt": [".pptx", ".ppt"],
            "image": [".png", ".jpg", ".jpeg", ".webp"],
            "code": [".py", ".html", ".js", ".json", ".css"]
        }
        target_exts = ext_map.get(file_type.lower(), None)

        found = []
        for base in search_dirs:
            if not base.exists():
                continue
            try:
                for p in base.glob("*"):
                    if p.is_file():
                        if target_exts and p.suffix.lower() not in target_exts:
                            continue
                        if keyword and keyword.lower() not in p.name.lower():
                            continue
                        
                        mtime = datetime.fromtimestamp(p.stat().st_mtime)
                        if time_range == "yesterday" and not (yesterday_start <= mtime <= yesterday_end):
                            continue
                        elif time_range == "today" and not (mtime >= today_start):
                            continue
                        elif time_range == "week" and not (mtime >= week_start):
                            continue

                        size_kb = round(p.stat().st_size / 1024, 1)
                        found.append((p.name, str(p), mtime.strftime("%Y-%m-%d %H:%M"), f"{size_kb} KB"))
            except Exception:
                continue

        if not found:
            return f"🔍 在桌面及常用目录中暂未找到符合条件的文件（关键词: '{keyword}', 时间: {time_range}, 类型: {file_type}）"

        found.sort(key=lambda x: x[2], reverse=True)
        lines = [f"📂 【为你找到的 {len(found[:6])} 个相关文件】："]
        for idx, (name, path_str, mt, sz) in enumerate(found[:6]):
            lines.append(f"{idx+1}. **{name}** ({sz} | 修改于 {mt})\n   📁 路径：`{path_str}`")

        lines.append("\n💡 主人需要我帮你直接打开哪个文件吗？说「帮我打开第1个文件」或者告诉我名字即可！🌸")
        return "\n\n".join(lines)
    except Exception as e:
        return f"❌ 查找文件失败: {e}"


@register_tool(description="打开指定路径的本地文件或文件夹。参数：file_path(完整文件路径)")
def open_file_path(file_path: str) -> str:
    """打开文件或文件夹"""
    try:
        p = Path(file_path.strip().strip('"').strip("'"))
        if not p.exists():
            return f"❌ 文件或路径不存在：`{file_path}`"
        os.startfile(str(p))
        return f"✅ 已成功为你打开：`{p.name}` 🌸"
    except Exception as e:
        return f"❌ 打开失败：{e}"
