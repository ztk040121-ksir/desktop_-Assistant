# -*- coding: utf-8 -*-
"""
小红书种草笔记与自媒体图文大师插件 (Xiaohongshu & Viral Article Agent Plugin)
基于 ModelScope yangzdpssoft/ai-article Skill 规范
支持生成爆款吸睛标题、三段式种草文案、Emoji 情绪排版、专属标签与 AI 生图提示词
"""
import os
import re
from pathlib import Path
from core.plugin_manager import register_tool


@register_tool(description="生成高赞爆款小红书种草笔记或公众号图文文案（包含吸睛大标题、痛点共鸣、核心测评干货、Emoji 视觉排版、热门标签及配套配图提示词）。参数：topic(种草主题或产品名称), target_audience(目标人群/受众), highlight(主打卖点或亮点), tone(文风语气，如'闺蜜种草'、'专业测评'、'搞钱干货')")
def generate_xiaohongshu_note(topic: str, target_audience: str = "学生/打工人/年轻女性", highlight: str = "", tone: str = "闺蜜真诚种草") -> str:
    """生成小红书种草笔记"""
    if not topic:
        return "请提供要种草的主题或产品名称~"

    titles = [
        f"🔥 救命！这个{topic}直接让我相见恨晚！！",
        f"🤫 答应我！在买{topic}之前一定要看完这篇！",
        f"💯 挖到宝了！亲测封神的{topic}，谁用谁知道！",
        f"😭 后悔没早点发现…性价比杀疯了的{topic}大公开！"
    ]

    hl_text = highlight if highlight else "颜值超高、使用感极佳、性价比断层领先"

    note_body = f"""📌 **【爆款吸睛备选标题】**：
1️⃣ `{titles[0]}`
2️⃣ `{titles[1]}`
3️⃣ `{titles[2]}`

---

📝 **【笔记正文（已完成 Emoji 情绪化排版）】**：

姐妹们！！今天必须按头安利这个让我逢人就夸的 **{topic}** ✨！
之前跟风踩雷了无数次，直到用了它，真的有一种“终于被我找到本命”的惊艳感😭！

💡 **【为什么直接封神？核心亮点】**
✅ **击中痛点**：针对我们{target_audience}的日常困扰，精准解决！
✅ **超绝体验**：{hl_text}！
✅ **细节拉满**：品质感直接拉满，用起来幸福感直线上升💯！

👩‍💻 **【使用感受真实测评】**
说实话刚开始我也抱着试试的心态，结果用了一周彻底沦陷！身边好几个朋友问我是在哪淘到的宝藏，真心建议人手一个，早买早享受！

---

🏷️ **【热门流量标签 TAG】**：
#{topic} #我的日常好物 #宝藏挖掘机 #小红书种草 #好物推荐 #{target_audience}必备 #高性价比好物

🎨 **【配套 AI 封面与配图生成提示词 (Prompt)】**：
`aesthetic warm flat-lay photography of {topic}, clean modern minimalist background, soft natural lighting, pastel tone, trending on Xiaohongshu, 8k resolution`"""

    return note_body
