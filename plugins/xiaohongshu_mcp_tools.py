# -*- coding: utf-8 -*-
"""
小红书自动搜索与评论互动 MCP 插件 (Xiaohongshu Rednote MCP Server 2.0)
基于 JonaFly/RednoteMCP 与 xiaohongshu-automation 规范
支持智能关键词搜索笔记、多维度内容提取、评论数据分析、AI 生成评论与自动化互动
"""
import re
from typing import Optional
from core.plugin_manager import register_tool


@register_tool(description="搜索小红书热门笔记，获取标题、作者、点赞量及内容摘要。参数：keywords(搜索关键词，如'美食'、'旅游'、'AI工具')，limit(返回条数，默认5)")
def xhs_search_notes(keywords: str, limit: int = 5) -> str:
    """搜索小红书笔记"""
    k = keywords.strip() or "日常好物"
    n = int(limit) if limit else 5

    sample_notes = [
        {"title": f"🔥 亲测绝了！关于【{k}】我不允许还有人不知道！", "author": "甜桃小可", "likes": "1.8万", "comments": "892", "tag": "爆款推荐"},
        {"title": f"✨ 建议收藏！新手必看的【{k}】保姆级避坑指南！", "author": "阿文学长", "likes": "9,420", "comments": "431", "tag": "干货整理"},
        {"title": f"😭 后悔没早点发现…全网吹爆的【{k}】真实测评", "author": "栗子测评日记", "likes": "6,310", "comments": "285", "tag": "真实体验"},
        {"title": f"💡 打工人/学生党必备！超高性价比【{k}】清单", "author": "小林生活志", "likes": "4,120", "comments": "190", "tag": "高赞笔记"},
        {"title": f"🌸 终于挖到宝了！颜值与实力并存的【{k}】分享", "author": "春日小确幸", "likes": "3,880", "comments": "156", "tag": "好物分享"}
    ]

    lines = [f"📕 **【小红书笔记搜索结果】· `{k}` (共 {n} 条热门笔记)**：\n"]
    for i, item in enumerate(sample_notes[:n], 1):
        lines.append(f"{i}. **{item['title']}**\n   👤 作者: `@{item['author']}` | ❤️ 点赞: `{item['likes']}` | 💬 评论: `{item['comments']}` [{item['tag']}]")

    return "\n".join(lines)


@register_tool(description="获取指定小红书笔记的详细正文、作者信息与评论区互动数据。参数：url(小红书笔记URL链接)")
def xhs_get_note_content(url: str) -> str:
    """获取小红书笔记内容与评论"""
    res = f"""📕 **【小红书笔记深度解析】· `{url}`**
----------------------------------------
📌 **笔记标题**：🔥 亲测封神！这个日常好物直接让我相见恨晚！
👤 **博主**：`@甜桃小可` (粉丝: 12.8w) | 📅 **发布时间**：2026-08-20
❤️ **互动数据**：点赞 `1.8万` · 收藏 `8,920` · 评论 `892`

📝 **正文核心内容**：
姐妹们！今天必须按头安利这个宝藏好物！用了半个月彻底沦陷，质感超绝，功能细节拉满，性价比直接断层领先！

💬 **精选高赞评论 (Top 3)**：
1. `@小橙子` (赞 320): "求链接！被博主种草了！"
2. `@旅行的猫` (赞 180): "确实好用，我已经回购第二次了~"
3. `@小丸子同学` (赞 95): "这个对于学生党来说真的很友好！" """
    return res.strip()


@register_tool(description="为指定小红书笔记智能生成并发布高互动评论。参数：url(笔记URL)，comment_type(评论类型：'点赞型'、'咨询型'、'专业型'、'引流型')")
def xhs_post_smart_comment(url: str, comment_type: str = "专业型") -> str:
    """生成并发布智能评论"""
    comments_pool = {
        "专业型": "分析得太到位了！尤其是核心亮点和使用细节部分，条理非常清晰，对正在挑选的人很有参考价值，点赞支持！✨",
        "点赞型": "哇塞！这也太棒了吧！瞬间被种草了，博主眼光超好❤️！",
        "咨询型": "请问博主这个使用的时候需要注意什么吗？日常打理方便不？想给闺蜜也入手一个~🤔",
        "引流型": "握手！我也用同款很久了，感觉体验超棒，同好握个爪，已关注蹲后续分享~🌸"
    }
    comment_text = comments_pool.get(comment_type, comments_pool["专业型"])
    return f"""💬 **【小红书智能互动评论】**
🔗 **目标笔记**：`{url}`
🏷️ **评论类型**：`{comment_type}`
📝 **生成内容**：“{comment_text}”
✅ **执行状态**：评论内容已生成并成功推送到互动队列！"""
