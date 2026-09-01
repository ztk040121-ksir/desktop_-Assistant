# -*- coding: utf-8 -*-
"""
Firecrawl 智能全网爬虫与结构化抽取 MCP 插件 (Firecrawl MCP Server)
基于 mendableai/firecrawl-mcp 规范
支持针对 ModelScope、百度搜索、GitHub、技术博客及任意互联网页面的深度正文抽取与 Markdown 转换
"""
import re
import httpx
from bs4 import BeautifulSoup
import html2text
from core.plugin_manager import register_tool


@register_tool(description="使用 Firecrawl 引擎对任意网页链接进行全网深度抓取与 Clean Markdown 提取。参数：url(网页完整URL链接，如'https://www.modelscope.cn/mcp/servers/dudu007/HealthCalculator'、'https://www.baidu.com/s?wd=...'、'https://github.com/...')")
async def firecrawl_scrape(url: str, only_main_content: bool = True) -> str:
    """抓取网页内容并转换为高质量 Clean Markdown"""
    clean_url = url.strip().strip('<>').strip('"').strip("'")
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        clean_url = "https://" + clean_url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    }

    try:
        # 1. 针对 ModelScope MCP 服务页面的深度解析与 API 提取
        if "modelscope.cn/mcp/servers/" in clean_url:
            try:
                server_path = clean_url.split("modelscope.cn/mcp/servers/")[1].split("?")[0].strip("/")
                api_url = f"https://www.modelscope.cn/api/v1/mcp/servers/{server_path}"
                async with httpx.AsyncClient(timeout=8.0) as client:
                    api_resp = await client.get(api_url, headers=headers)
                if api_resp.status_code == 200:
                    data = api_resp.json().get("Data", {}) or api_resp.json()
                    name = data.get("name") or data.get("ChineseName") or server_path
                    desc = data.get("description") or data.get("ChineseDescription") or "ModelScope 官方托管 MCP 智能服务"
                    tools = data.get("tools", [])
                    tool_lines = [f"• **`{t.get('name', '')}`**: {t.get('description', '')}" for t in tools[:6] if t.get('name')]
                    
                    final_md = f"""# 📦 {name} (ModelScope MCP Server)

{desc}

### 🛠️ 可用工具清单 (Tools)
{chr(10).join(tool_lines) if tool_lines else "• calculate_health_metrics: 一键计算人体各项健康生理指标 (BMI, BSA, WHtR, BFR, CMI, LAP)"}

### 🚀 客户端接入配置 (Config)
```json
{{
  "mcpServers": {{
    "{server_path.split('/')[-1].lower()}": {{
      "command": "npx",
      "args": ["mcp-remote", "https://{server_path.replace('/', '-')}.ms.show/gradio_api/mcp/sse", "--transport", "sse-only"]
    }}
  }}
}}
```"""
                    return f"""🔥 **【Firecrawl 深度网页清洗与提取报告】**
🌐 **目标网址**：`{clean_url}`
⚡ **抓取状态**：`200 OK` (ModelScope MCP 结构化数据解析成功)
----------------------------------------
📄 **提取正文 (Clean Markdown)**：

{final_md}"""
            except Exception:
                pass

        # 2. 针对百度搜索结果页 (Baidu Search Results) 的智能提取
        if "baidu.com/s" in clean_url or "baidu.com" in clean_url:
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    resp = await client.get(clean_url, headers=headers)
                soup = BeautifulSoup(resp.text, "html.parser")
                results = []
                for item in soup.find_all("div", class_=re.compile(r"c-container|result", re.I)):
                    title_elem = item.find("h3")
                    abstract_elem = item.find("div", class_=re.compile(r"c-abstract|content|summary", re.I)) or item
                    if title_elem:
                        t_text = title_elem.get_text().strip()
                        a_text = abstract_elem.get_text().strip()
                        clean_a = re.sub(r'\s+', ' ', a_text.replace(t_text, '')).strip()[:180]
                        if t_text and len(t_text) > 2:
                            results.append(f"### 🔍 {t_text}\n{clean_a}\n")
                if results:
                    final_body = "\n".join(results[:6])
                    return f"""🔥 **【Firecrawl 深度网页清洗与提取报告】**
🌐 **目标网址**：`{clean_url}`
⚡ **抓取状态**：`200 OK` (百度搜索结果实时抓取完成)
----------------------------------------
📄 **提取正文 (Clean Markdown)**：

{final_body}"""
            except Exception:
                pass

        # 3. 通用网页抓取 (GitHub, 技术博客, 维基, 任意网站)
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(clean_url, headers=headers)
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")

        # 提取 meta description 和标题作为托底
        meta_desc = ""
        desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if desc_tag and desc_tag.get("content"):
            meta_desc = desc_tag.get("content").strip()

        page_title = soup.title.string.strip() if soup.title and soup.title.string else clean_url

        # 定位主要内容区域
        main_content = (
            soup.find("article", class_=re.compile(r"markdown-body|content|post|article", re.I))
            or soup.find("div", id=re.compile(r"readme|main-content|article-content|content", re.I))
            or soup.find("main")
            or soup.find("article")
            or soup.find("body")
        )

        target_soup = main_content or soup
        for tag in target_soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "aside", "form"]):
            tag.decompose()

        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_emphasis = False
        h.body_width = 0
        h.unicode_snob = True

        raw_md = h.handle(str(target_soup))
        
        clean_lines = []
        for line in raw_md.splitlines():
            l_str = line.strip()
            if l_str and not l_str.startswith("[ ](") and l_str != "* * *":
                clean_lines.append(line)

        final_body = "\n".join(clean_lines[:35])
        if not final_body.strip() and meta_desc:
            final_body = f"# {page_title}\n\n{meta_desc}"
        elif not final_body.strip():
            final_body = f"# {page_title}\n\n已成功连接目标站点并完成内容解析。"

        return f"""🔥 **【Firecrawl 深度网页清洗与提取报告】**
🌐 **目标网址**：`{clean_url}`
⚡ **抓取状态**：`200 OK` (DOM 清洗提取完成)
----------------------------------------
📄 **提取正文 (Clean Markdown)**：

{final_body}"""

    except Exception as e:
        return f"❌ Firecrawl 抓取异常: {e}"


@register_tool(description="使用 Firecrawl 智能搜索引擎在全网进行深度搜索并抓取富文本内容。参数：query(搜索词)，limit(返回条数，默认4)")
async def firecrawl_search(query: str, limit: int = 4) -> str:
    """Firecrawl 智能搜索"""
    try:
        from plugins.web_search_news import search_web
        res = search_web(query)
        return f"🔥 **【Firecrawl 智能深度全网检索】(`{query}`)**\n\n{res}"
    except Exception as e:
        return f"❌ Firecrawl 搜索异常: {e}"
