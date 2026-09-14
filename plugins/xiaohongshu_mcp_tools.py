# -*- coding: utf-8 -*-
"""
小红书内容检索与爆款文案生成插件 (Xiaohongshu Rednote Assistant Plugin)
支持小红书热门话题全网检索、提取笔记关键点、以及根据主题动态生成高互动、高转化的精选种草评论与爆款大纲。
"""
import re
import httpx
from typing import Optional
from core.plugin_manager import register_tool


@register_tool(description="检索指定主题的小红书热门笔记与全网讨论焦点。参数：keywords(搜索关键词，如'美食'、'旅游'、'AI工具')，limit(返回条数，默认5)")
def xhs_search_notes(keywords: str, limit: int = 5) -> str:
    """全网检索小红书相关热门笔记与爆款主题"""
    k = keywords.strip() or "生活好物"
    n = max(1, min(10, int(limit) if limit else 5))

    real_results = []
    try:
        url = f"https://html.duckduckgo.com/html/?q={k}+site:xiaohongshu.com"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = httpx.get(url, headers=headers, timeout=5.0)
        if resp.status_code == 200:
            raw_titles = re.findall(r'<a class="result__a"[^>]*>(.*?)</a>', resp.text)
            raw_snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', resp.text)
            for i in range(min(n, len(raw_titles))):
                clean_title = re.sub(r'<[^>]+>', '', raw_titles[i]).strip()
                clean_title = clean_title.replace(" - 小红书", "").replace(" | 小红书", "")
                snippet = re.sub(r'<[^>]+>', '', raw_snippets[i]).strip() if i < len(raw_snippets) else ""
                if clean_title:
                    real_results.append({
                        "title": clean_title,
                        "snippet": snippet[:80] + ("..." if len(snippet) > 80 else "")
                    })
    except Exception:
        pass

    if real_results:
        lines = [f"📕 **【小红书全网收录笔记检索结果】· `{k}`** (获取到 {len(real_results)} 条真实收录)\n"]
        for idx, item in enumerate(real_results, 1):
            snip_str = f"\n   📝 *{item['snippet']}*" if item['snippet'] else ""
            lines.append(f"{idx}. **{item['title']}**{snip_str}")
        lines.append("\n💡 *以上内容来源于公开网络搜索引擎索引，可直接告诉我针对某条笔记提炼核心要点或撰写同款爆款文案。*")
        return "\n".join(lines)

    # 兜底：明确告知由于反爬网络受限，呈现专业爆款选题大纲
    return f"""📕 **【小红书爆款选题与创作指南】· `{k}`**
⚠️ *注：当前外部网络检索受限，已自动为您生成「{k}」垂直领域的 5 大黄金爆款选题结构：*
----------------------------------------
🔥 **高点击率选题方向**：
1. **经验避坑型**：🔥《听劝！关于【{k}】踩过的 3 个大坑，千万别花冤枉钱！》
2. **保姆级干货**：✨《建议收藏！从 0 到 1 搞定【{k}】的保姆级极简实操法》
3. **真实体验型**：😭《后悔没早点知道…关于【{k}】深度体验一个月后的大实话》
4. **高性价比清单**：💡《打工人/学生党狂喜！这套【{k}】高效方案直接封神！》
5. **对比决策型**：⚡《别纠结了！一图看懂当下热门【{k}】到底怎么选》

🏷️ **热门标签推荐**：`#{k} #小红书爆款 #我的日常 #干货分享 #生活好物`"""


@register_tool(description="为指定小红书笔记或话题动态生成高互动、高点赞率的真实评论文案。参数：topic_or_url(笔记主题或URL)，comment_type(评论类型：'点赞种草型'、'经验交流型'、'专业答疑型'、'咨询求助型')")
def xhs_post_smart_comment(topic_or_url: str, comment_type: str = "专业答疑型") -> str:
    """动态组装小红书高互动评论文案"""
    t = topic_or_url.strip() or "当前话题"
    
    # 结合主题词的动态互动文案库
    comments_pool = {
        "专业答疑型": [
            f"博主关于【{t}】的总结非常到位！补充一个小细节：在实际操作中结合日常习惯配合使用，体验感会直接拉满，亲测有效！👏",
            f"逻辑很清晰！尤其是关于【{t}】的实用性与注意事项分析，给正在纠结的人提供了很清晰的决策参考，支持干货分享！✨"
        ],
        "点赞种草型": [
            f"天呐！看完【{t}】直接疯狂心动，博主眼光也太好了吧，质感和细节完全戳在我的心巴上，瞬间被按头种草！❤️",
            f"这个【{t}】太棒了！实用又好看，狠狠爱住了，必须立刻转发给闺蜜一起冲！🥰"
        ],
        "经验交流型": [
            f"同款握爪！我也研究【{t}】好久了，确实省心，博主提到的几个实操小窍门非常地道～🌸",
            f"哈哈我也是！按照博主说的思路去搞【{t}】真的事半功倍，蹲一个后续的进阶实测分享！"
        ],
        "咨询求助型": [
            f"请问博主这个【{t}】日常打理/使用起来方便吗？新手第一次尝试需要注意避开哪些隐藏坑呀？求翻牌！🥺",
            f"被种草了！想问下博主关于【{t}】在不同场景下的表现怎么样，性价比高吗？求推荐入手参考~"
        ]
    }

    c_list = comments_pool.get(comment_type, comments_pool["专业答疑型"])
    c1, c2 = c_list[0], c_list[1]

    return f"""💬 **【小红书高转化互动评论文案库】**
🎯 **目标主题**：`{t}`
🏷️ **文案风格**：`{comment_type}`
----------------------------------------
📝 **精选文案方案 A (高点赞版)**：
“{c1}”

📝 **精选文案方案 B (高互动版)**：
“{c2}”

🏷️ **关联标签**：`#{t} #小红书互动 #种草打卡`
✅ *文案已动态融合主题词并针对小红书算法进行 Emoji 视觉与互动率优化，可直接复制使用。*"""
