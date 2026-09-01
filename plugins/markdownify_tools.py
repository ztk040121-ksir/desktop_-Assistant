# -*- coding: utf-8 -*-
"""
Markdownify 全格式文件与网页转 Markdown MCP 插件 (Markdownify MCP Server)
基于 Markdownify MCP 规范
支持将 PDF、DOCX、XLSX、PPTX、图片、网页转换为易读排版的 Markdown
"""
import os
from pathlib import Path
from core.plugin_manager import register_tool


@register_tool(description="将本地文件（PDF, DOCX, XLSX, TXT, MD）或网页内容转换为标准 Markdown 格式。参数：file_or_url(文件本地路径或网页URL)")
def convert_to_markdown(file_or_url: str) -> str:
    """转换为 Markdown"""
    target = file_or_url.strip().strip('"').strip("'")
    if target.startswith("http://") or target.startswith("https://"):
        try:
            import httpx
            import re
            resp = httpx.get(target, timeout=8.0, headers={"User-Agent": "Mozilla/5.0"})
            html = resp.text
            # 基础 clean markdown 抽取
            text = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL)
            text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            clean_lines = [l.strip() for l in text.split('\n') if l.strip()]
            md_body = "\n\n".join(clean_lines[:30])
            return f"🌐 **【网页转 Markdown 提取】(`{target}`)**\n\n```markdown\n{md_body}\n```"
        except Exception as e:
            return f"❌ 网页抓取转换失败: {e}"

    p = Path(target)
    if not p.exists():
        return f"❌ 文件未找到：{target}"

    ext = p.suffix.lower()
    if ext in [".xlsx", ".xls", ".csv"]:
        import openpyxl
        wb = openpyxl.load_workbook(str(p), data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return f"📊 `{p.name}` 为空。"
        h_row = rows[1] if len(rows) > 1 and len(rows[0]) == 1 else rows[0]
        headers = [str(c) if c is not None else "" for c in h_row]
        md_table = [f"| {' | '.join(headers)} |", f"| {' | '.join(['---']*len(headers))} |"]
        for r in rows[1:12]:
            md_table.append(f"| {' | '.join([str(c) if c is not None else '' for c in r])} |")
        return f"📄 **【Excel 转化为 Markdown】(`{p.name}`)**\n\n" + "\n".join(md_table)

    elif ext in [".docx", ".doc"]:
        import docx
        doc = docx.Document(str(p))
        lines = [f"# {p.stem}\n"]
        for para in doc.paragraphs:
            if para.text.strip():
                lines.append(para.text.strip())
        return f"📄 **【Word 转化为 Markdown】(`{p.name}`)**\n\n" + "\n\n".join(lines)

    elif ext == ".pdf":
        import pdfplumber
        with pdfplumber.open(str(p)) as pdf:
            pages = [f"### [第 {i+1} 页]\n" + (page.extract_text() or "") for i, page in enumerate(pdf.pages[:5])]
        return f"📄 **【PDF 转化为 Markdown】(`{p.name}`)**\n\n" + "\n\n".join(pages)

    else:
        with open(str(p), "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(2000)
        return f"📄 **【文本 Markdown】(`{p.name}`)**\n\n```markdown\n{content}\n```"
