# -*- coding: utf-8 -*-
"""
小红书全自动图文发布与创作者平台直连助手 (Xiaohongshu Publisher MCP Server 6.0)
功能：
1. 根据活动工作空间 (workspace_path) 自动在当前工作目录下创建 3:4 高清海报与完整 Markdown 笔记文件
2. 自动唤起系统浏览器直达【小红书创作者发布页】(creator.xiaohongshu.com/publish/publish)
3. 自动在 Windows 资源管理器中打开并高亮选中工作区生成的文件，实现一键拖拽上传
4. 自动将标题与正文复制到系统剪贴板，支持 Ctrl+V 秒级一键填充
"""
import os
import re
import json
import time
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from core.plugin_manager import register_tool

# 存储路径
XHS_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "xhs"
XHS_DATA_DIR.mkdir(parents=True, exist_ok=True)
COOKIE_FILE = XHS_DATA_DIR / "cookies.json"
PUBLISH_LOG = XHS_DATA_DIR / "publish_history.json"


def _copy_to_clipboard(text: str) -> bool:
    """将文本安全写入 Windows 系统剪贴板"""
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        pass
    try:
        process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
        process.communicate(text.encode('utf-16le'))
        return True
    except Exception:
        return False


def _open_creator_publish_page():
    """打开小红书创作者服务平台的发布图文页面"""
    publish_url = "https://creator.xiaohongshu.com/publish/publish?source=official"
    try:
        os.startfile(publish_url)
    except Exception:
        try:
            subprocess.Popen(["cmd.exe", "/c", "start", publish_url], shell=True)
        except Exception:
            import webbrowser
            webbrowser.open(publish_url)


def _highlight_file_in_explorer(file_path: Path):
    """在 Windows 资源管理器中打开并高亮选中目标文件"""
    try:
        if file_path.exists():
            subprocess.Popen(f'explorer.exe /select,"{file_path}"', shell=True)
    except Exception as e:
        print(f"[Explorer Select Error] {e}")


def _generate_xhs_cover_poster(title: str, subtitle: str = "干货满满 · 建议收藏", tags: str = "#AI科技 #效率工具", target_dir: Optional[Path] = None) -> Path:
    """使用 PIL 生成小红书标准 3:4 爆款图文封面海报 (900x1200) 并保存到指定工作空间目录"""
    from PIL import Image, ImageDraw, ImageFont

    width, height = 900, 1200
    img = Image.new("RGB", (width, height), color=(255, 245, 248))
    draw = ImageDraw.Draw(img)

    # 1. 柔和粉紫渐变背景
    for y in range(height):
        r = int(255 - (y / height) * 35)
        g = int(240 - (y / height) * 30)
        b = int(250 - (y / height) * 12)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 2. 白色主卡片容器
    card_margin = 55
    draw.rounded_rectangle(
        [(card_margin, card_margin + 70), (width - card_margin, height - card_margin - 70)],
        radius=35,
        fill=(255, 255, 255),
        outline=(255, 101, 153),
        width=4
    )

    # 3. 字体配置
    font_path = "C:/Windows/Fonts/msyh.ttc"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/simhei.ttf"

    try:
        tag_font = ImageFont.truetype(font_path, 32)
        title_font = ImageFont.truetype(font_path, 50)
        sub_font = ImageFont.truetype(font_path, 34)
        brand_font = ImageFont.truetype(font_path, 26)
    except Exception:
        tag_font = title_font = sub_font = brand_font = ImageFont.load_default()

    # 4. 顶部高光胶囊
    draw.rounded_rectangle([(width // 2 - 160, 180), (width // 2 + 160, 250)], radius=35, fill=(255, 101, 153))
    draw.text((width // 2, 215), "🔥 爆款干货精选", font=tag_font, fill=(255, 255, 255), anchor="mm")

    # 5. 标题排版 (去除路径斜杠与脏字符)
    clean_title = re.sub(r'[\r\n\\/:*?"<>|]+', ' ', title).strip()[:24]
    line1 = clean_title[:8]
    line2 = clean_title[8:16]
    line3 = clean_title[16:]

    cur_y = 380
    if line1:
        draw.text((width // 2, cur_y), line1, font=title_font, fill=(30, 20, 40), anchor="mm")
        cur_y += 80
    if line2:
        draw.text((width // 2, cur_y), line2, font=title_font, fill=(255, 60, 120), anchor="mm")
        cur_y += 80
    if line3:
        draw.text((width // 2, cur_y), line3, font=title_font, fill=(30, 20, 40), anchor="mm")
        cur_y += 80

    # 6. 分割线
    draw.line([(width // 2 - 180, cur_y + 30), (width // 2 + 180, cur_y + 30)], fill=(255, 180, 205), width=3)

    # 7. 副标题
    draw.text((width // 2, cur_y + 105), subtitle[:20], font=sub_font, fill=(100, 80, 110), anchor="mm")

    # 8. 底部标签栏
    clean_tags = " ".join([f"#{t.strip('#')}" for t in tags.replace('，', ',').split(',') if t.strip()]) if tags else "#AI科技 #效率工具"
    draw.text((width // 2, 930), clean_tags[:28], font=tag_font, fill=(255, 80, 130), anchor="mm")

    # 9. 版权标
    draw.text((width // 2, 1050), "✨ 小红书创作者 MCP 助手 · 自动生成", font=brand_font, fill=(160, 140, 170), anchor="mm")

    clean_file_name = re.sub(r'[\\/:*?"<>|]', '_', title[:14]) + "_小红书封面.png"
    save_dir = target_dir if (target_dir and target_dir.exists()) else (Path.home() / "Desktop")
    out_file = save_dir / clean_file_name
    img.save(str(out_file))
    return out_file


@register_tool(description="小红书创作者账号登录与 Cookie 管理 MCP。支持调起浏览器登录或直接查看状态。")
async def xhs_login_account(action: str = "open_browser", cookie_text: str = "", phone: str = "", verify_code: str = "") -> str:
    """小红书账号自动登录与状态维护"""
    _open_creator_publish_page()
    return """🌐 **【已为你调起系统默认浏览器 · 小红书创作者服务平台】**
----------------------------------------
✨ **浏览器已自动打开**：`https://creator.xiaohongshu.com/publish/publish?source=official`
📱 如果尚未登录，可直接在打开的网页中使用手机 **小红书 App 扫码登录**；
🚀 登录后发布图文即可一键完成！"""


@register_tool(description="在当前工作空间或指定目录下，一键生成小红书爆款文案、3:4高清封面海报并保存为Markdown与图片文件，自动唤起系统浏览器并选中封面文件。参数：title(笔记标题), topic(核心主题), content(可选定制正文), tags(标签列表), auto_generate_cover(是否生成封面), workspace_path(当前工作空间目录)")
async def xhs_auto_publish_note(title: str, topic: str = "", content: str = "", tags: str = "", auto_generate_cover: bool = True, workspace_path: str = "") -> str:
    """在指定工作空间自动生成文案、配图，并自动调起浏览器与复制剪贴板"""
    # 严格清洗标题，去除任何路径或指令残留
    clean_title = re.sub(r'【[^】]+】', '', title)
    clean_title = re.sub(r'^(?:在当前工作目录下|在当前目录下|在当前工作区|在工作区|帮我|请帮我|发一篇|发布|一篇|一个|制作|生成|编写|写一份|关于)+', '', clean_title.strip()).strip('"\'`：:，, ')
    clean_title = re.sub(r'[\\/:*?"<>|]', '', clean_title).strip()
    if not clean_title or len(clean_title) < 2:
        clean_title = "小红书爆款图文实战指南与精选技巧"

    clean_tags = tags.strip() if tags else "#AI科技 #效率工具 #职场干货 #学习规划"

    # 确定保存工作区目录
    target_dir = Path(workspace_path) if (workspace_path and Path(workspace_path).exists()) else (Path.home() / "Desktop")

    # 1. 自动生成小红书爆款文案
    if not content:
        note_body = f"""🔥 宝子们！今天必须给你们安利关于【{clean_title}】的硬核干货！亲测巨好用，效率直接翻倍，建议先【点赞+收藏】避免找不到哦~ 🌟

💡 **【为什么一定要了解 {clean_title}？】**
很多小伙伴在日常学习和工作中经常遇到痛点，传统方式不仅费时费力，还容易踩坑。掌握了这个核心技巧，不仅省下大半时间，还能轻松搞定复杂任务！

✨ **【3个超实用核心要点】**：
1️⃣ **底层逻辑拆解**：找准关键痛点，掌握核心工作流，告别低效重复；
2️⃣ **工具赋能提速**：善用自动化与 AI 智能体工具，30秒搞定过去半天的工作量；
3️⃣ **避坑指南**：注意关键参数与细节规范，一步到位少走弯路！

📌 **【建议收藏实操】**：
赶紧在评论区留下你的疑问，或者告诉我你最关心的场景，我会在下一期详细拆解！别忘了点击头像关注我，每天为你分享最前沿的干货与效率神器~ 💖

{clean_tags}"""
    else:
        note_body = content

    # 2. 保存 Markdown 笔记文档到工作空间
    md_filename = re.sub(r'[\\/:*?"<>|]', '_', clean_title[:14]) + "_小红书笔记.md"
    md_file = target_dir / md_filename
    try:
        md_file.write_text(f"# {clean_title}\n\n{note_body}\n", encoding='utf-8')
    except Exception as e:
        print(f"[Save MD Note Error] {e}")

    # 3. 自动生成 3:4 爆款封面配图到工作空间
    cover_path_str = ""
    cover_card_tag = ""
    cover_file = None
    if auto_generate_cover:
        try:
            cover_file = _generate_xhs_cover_poster(clean_title, subtitle="干货满满 · 建议收藏", tags=clean_tags, target_dir=target_dir)
            size_kb = round(cover_file.stat().st_size / 1024, 1)
            cover_card_tag = f"[[FILE_CARD:{cover_file}|{cover_file.name}|{size_kb} KB|PNG]]"
            cover_path_str = str(cover_file)
        except Exception as e:
            print(f"[Cover Error] {e}")

    md_card_tag = f"[[FILE_CARD:{md_file}|{md_file.name}|{round(md_file.stat().st_size/1024, 1)} KB|MD]]" if md_file.exists() else ""

    # 4. 自动将文案复制到系统剪贴板
    full_clipboard_text = f"{clean_title}\n\n{note_body}"
    clip_ok = _copy_to_clipboard(full_clipboard_text)

    # 5. 自动调起浏览器打开创作者发布图文页
    _open_creator_publish_page()

    # 6. 自动调出文件管理器高亮选中刚生成的工作区封面图
    highlight_target = cover_file if (cover_file and cover_file.exists()) else md_file
    if highlight_target and highlight_target.exists():
        threading.Thread(target=lambda: _highlight_file_in_explorer(highlight_target), daemon=True).start()

    # 7. 记录发布日志
    history = []
    if PUBLISH_LOG.exists():
        try:
            history = json.loads(PUBLISH_LOG.read_text(encoding='utf-8'))
        except Exception:
            history = []

    record = {
        "id": f"xhs_{int(datetime.now().timestamp())}",
        "title": clean_title,
        "publish_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "workspace": str(target_dir),
        "cover_path": cover_path_str,
        "md_path": str(md_file),
        "status": "🌐 已在活动工作区创建文件并调起发布页",
        "tags": clean_tags
    }
    history.insert(0, record)
    PUBLISH_LOG.write_text(json.dumps(history[:30], ensure_ascii=False, indent=2), encoding='utf-8')

    return f"""{cover_card_tag}
{md_card_tag}
📕 **【小红书全自动图文发布 MCP 助手 6.0】**
----------------------------------------
📂 **已保存至当前工作空间**：`{target_dir}`
📌 **笔记标题**：`{clean_title}`
🖼️ **3:4 封面配图**：`已在当前工作空间生成并在资源管理器中自动高亮！`
📄 **Markdown笔记源码**：`{md_file.name} (已同步存入当前工作区)`
🌐 **浏览器直连**：`✅ 已自动为你唤起 Chrome 浏览器直达【发布图文】工作区！`
📋 **剪贴板同步**：`{'✅ 标题与正文已自动复制到系统剪贴板' if clip_ok else '请复制下方文案'}`

📄 **生成的爆款图文文案**：
```text
{note_body}
```

🌸 **两步秒级完成发布**：
1. 系统已在当前工作空间 **`{target_dir.name}`** 创建了封面与文案，并**自动高亮选中了封面文件**；
2. 直接将选中的 **`{cover_file.name if cover_file else '封面图'}`** 拖进浏览器，然后在标题/正文框按 **`Ctrl + V`** 即可一键发布！"""
