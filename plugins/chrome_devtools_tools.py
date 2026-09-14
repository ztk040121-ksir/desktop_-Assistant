# -*- coding: utf-8 -*-
"""
网页性能与 DOM 结构自动化分析插件 (Web Performance & DOM Inspector)
支持使用系统浏览器导航指定页面，以及对 URL 进行真实网络延迟分段测算 (TTFB、整页耗时) 与 DOM 规模结构审计。
"""
import os
import time
import httpx
from bs4 import BeautifulSoup
from core.plugin_manager import register_tool


@register_tool(description="使用系统默认浏览器打开指定网页链接并导航。参数：url(网页链接，如'https://www.bilibili.com')")
def chrome_navigate_page(url: str) -> str:
    """打开浏览器导航到指定页面"""
    clean_url = url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        clean_url = "https://" + clean_url
    try:
        os.startfile(clean_url)
        return f"🌐 **【网页自动化导航】**：已成功在系统默认浏览器中打开 `{clean_url}`！"
    except Exception as e:
        return f"❌ 浏览器导航失败：{e}"


@register_tool(description="对指定网页进行真实网络时延分段测算与 DOM 结构性能审计。参数：url(网页URL)")
def chrome_performance_insights(url: str = "https://developers.chrome.com") -> str:
    """真实分段探测网络时延并分析 DOM 结构"""
    clean_url = url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        clean_url = "https://" + clean_url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    try:
        t0 = time.perf_counter()
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            req = client.build_request("GET", clean_url, headers=headers)
            resp = client.send(req, stream=True)
            # 真实测量首字节到达时间 (TTFB: 发送请求至收到响应头)
            real_ttfb = round(time.perf_counter() - t0, 3)
            raw_content = resp.read()
            # 真实测量整页传输完成时间
            total_time = round(time.perf_counter() - t0, 3)
            status_code = resp.status_code
            resp.close()

            content_length = len(raw_content)
            html_text = raw_content.decode(resp.encoding or "utf-8", errors="ignore")

            # 解析 DOM 元素与资源统计
            soup = BeautifulSoup(html_text, "html.parser")
            dom_count = len(soup.find_all())
            script_count = len(soup.find_all("script"))
            style_count = len(soup.find_all("link", rel="stylesheet")) + len(soup.find_all("style"))
            img_count = len(soup.find_all("img"))
            title_text = soup.title.string.strip() if soup.title and soup.title.string else "无标题"

            # 估算渲染参考指标 (明确标注为估算值)
            est_fcp = round(real_ttfb + min(0.6, dom_count * 0.00025), 3)
            est_lcp = round(est_fcp + min(1.0, (content_length / 102400) * 0.15), 3)

            # 计算性能综合评分 (100分制)
            score = 100
            if total_time > 1.5: score -= min(30, int((total_time - 1.5) * 15))
            if dom_count > 1500: score -= min(20, int((dom_count - 1500) / 100))
            if content_length > 1024 * 1024: score -= 15
            score = max(35, min(99, score))

            grade = "🟢 优秀" if score >= 85 else ("🟡 良好" if score >= 65 else "🔴 需优化")

            return f"""⚡ **【网页网络性能与 DOM 结构审计报告】**
🔗 **目标站点**：`{clean_url}` ({title_text})
----------------------------------------
📈 **网络分段实测指标**：
• **HTTP 响应状态**：`HTTP {status_code}`
• **首字节响应时延 (TTFB 实测)**：`{real_ttfb}s`
• **整页传输总耗时 (实测)**：`{total_time}s`
• **HTML 源码体积**：`{content_length / 1024:.1f} KB`
• **首次内容绘制 (FCP 估算)**：`{est_fcp}s` *(基于 DOM 与体积估算)*
• **最大内容绘制 (LCP 估算)**：`{est_lcp}s` *(基于 DOM 与体积估算)*

📦 **DOM 与静态资源规模**：
• **DOM 节点总数**：`{dom_count}` 个
• **脚本资源 (JS)**：`{script_count}` 个
• **样式表资源 (CSS)**：`{style_count}` 个
• **图像元素 (IMG)**：`{img_count}` 个

💡 **综合性能评估**：评分 **{score}/100** ({grade})
*建议：{("网络响应迅速，页面结构精炼。" if score >= 85 else "建议开启 Gzip/Brotli 传输压缩并精简内联脚本以加快首屏呈现。")}*"""

    except Exception as e:
        return f"❌ 对 `{clean_url}` 的网络性能审计失败：{e}\n*提示：请检查目标站点是否可访问或网络连接是否正常。*"
