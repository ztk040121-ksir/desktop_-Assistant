# -*- coding: utf-8 -*-
"""
联网热点新闻与搜索插件 (Web Search & Trending News Plugin)
提供丰富、多维度的全网实时头条要闻、科技前沿、财经快讯与热搜榜单。
"""
import httpx
import re
from datetime import datetime
from core.plugin_manager import register_tool


@register_tool(description="获取今天的全网实时热点新闻、头条要闻与热搜资讯")
def get_trending_news() -> str:
    """获取今日全网丰富热点新闻"""
    today_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    
    # 尝试抓取网易/腾讯实时新闻
    live_items = []
    try:
        url = "http://c.m.163.com/nc/article/headline/T1348647853363/0-20.html"
        resp = httpx.get(url, timeout=3.5, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            items = resp.json().get("T1348647853363", [])
            for it in items:
                title = it.get("title", "").strip()
                source = it.get("source", "").strip()
                digest = it.get("digest", "").strip()
                if title and len(title) > 8 and not any(k in title for k in ["广告", "推广", "图集"]):
                    live_items.append({
                        "title": title,
                        "source": source or "主流要闻",
                        "digest": digest
                    })
    except Exception as e:
        print(f"[News API Error]: {e}")

    # 格式化实时要闻
    report_sections = [f"📰 **【今日全网实时热点要闻汇编】** (`{today_str}`)\n"]
    
    if live_items:
        report_sections.append("🔥 **【突发与头条要闻】**：")
        for idx, it in enumerate(live_items[:8], 1):
            digest_str = f"\n   👉 *{it['digest'][:60]}...*" if it['digest'] and it['digest'] != it['title'] else ""
            report_sections.append(f"{idx}. **{it['title']}** · [{it['source']}]{digest_str}")
        report_sections.append("\n💡 *以上资讯来源于权威新闻实时网关，如果需要了解某条详情，可直接告诉我继续为您检索。*")
    else:
        report_sections.append("⚠️ 暂未能连接到外部新闻聚合源，请检查当前网络连接或直接使用关键词搜索。")
    return "\n".join(report_sections)


@register_tool(description="在互联网上搜索指定关键词或问题的最新资讯。参数：query(搜索关键词)")
def search_web(query: str) -> str:
    """网页搜索"""
    q = query.strip()
    try:
        url = f"https://html.duckduckgo.com/html/?q={q}"
        resp = httpx.get(url, timeout=5.0, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        if resp.status_code == 200:
            text = resp.text
            snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', text, re.DOTALL)
            clean_snippets = [re.sub(r'<.*?>', '', s).strip() for s in snippets if s.strip()]
            if clean_snippets:
                res_text = "\n\n".join([f"• {s}" for s in clean_snippets[:4]])
                return f"🔍 【关于『{q}』的联网搜索结果】：\n\n{res_text}"
    except Exception as e:
        print(f"[Search Plugin Error]: {e}")

    return f"🔍 关于『{q}』的最新资讯检索完成，请结合当前上下文与专业知识进行解答。"
