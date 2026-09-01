# -*- coding: utf-8 -*-
"""
个人知识库智能管家插件 (Local RAG Private Knowledge Base Agent)
基于 ModelScope jeffky/knowledge-base-agent 规范
支持本地文档（PDF / Word / TXT / Markdown / 代码）批量导入、索引构建、余弦相似度检索与精准问答
"""
import os
import re
import json
import math
from pathlib import Path
from typing import List, Dict
from core.plugin_manager import register_tool

KB_DIR = Path(r"E:\Demo\desk_tools\data\knowledge_base")
KB_INDEX_FILE = KB_DIR / "kb_index.json"


def _ensure_kb_dir():
    KB_DIR.mkdir(parents=True, exist_ok=True)
    if not KB_INDEX_FILE.exists():
        KB_INDEX_FILE.write_text(json.dumps({"documents": [], "chunks": []}, ensure_ascii=False, indent=2), encoding='utf-8')


def _simple_tokenize(text: str) -> set:
    """提取关键词字词集合"""
    cleaned = re.sub(r'[^\w\u4e00-\u9fa5]', ' ', text.lower())
    words = set(cleaned.split())
    # 增加双字滑动窗口以提升中文匹配精度
    for i in range(len(cleaned) - 1):
        pair = cleaned[i:i+2].strip()
        if len(pair) == 2:
            words.add(pair)
    return words


@register_tool(description="向本地私有知识库导入并索引文档（支持 .pdf, .docx, .txt, .md）。参数：file_path(文档完整路径)")
def add_document_to_knowledge_base(file_path: str) -> str:
    """导入文档至知识库"""
    _ensure_kb_dir()
    clean_p = file_path.strip().strip('"').strip("'")
    if clean_p.startswith("file:///"):
        clean_p = clean_p[8:]
    p = Path(clean_p)
    if not p.exists():
        return f"❌ 文件不存在：{file_path}"

    text_content = ""
    ext = p.suffix.lower()

    if ext in [".txt", ".md", ".py", ".json", ".csv"]:
        with open(str(p), "r", encoding="utf-8", errors="ignore") as f:
            text_content = f.read()
    elif ext in [".docx", ".doc"]:
        import docx
        doc = docx.Document(str(p))
        text_content = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    elif ext == ".pdf":
        import pdfplumber
        with pdfplumber.open(str(p)) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
            text_content = "\n".join(pages_text)
    else:
        return f"⚠️ 暂不支持的文件格式：{ext}"

    if not text_content.strip():
        return f"⚠️ 文档 `{p.name}` 解析内容为空。"

    # 切分分块 (Chunking)
    chunk_size = 400
    overlap = 50
    chunks = []
    lines = text_content.split("\n")
    cur_chunk = ""
    for line in lines:
        if len(cur_chunk) + len(line) < chunk_size:
            cur_chunk += line + "\n"
        else:
            if cur_chunk.strip():
                chunks.append(cur_chunk.strip())
            cur_chunk = cur_chunk[-overlap:] + line + "\n"
    if cur_chunk.strip():
        chunks.append(cur_chunk.strip())

    # 更新索引库
    index_data = json.loads(KB_INDEX_FILE.read_text(encoding='utf-8'))
    # 移除旧记录
    index_data["documents"] = [d for d in index_data["documents"] if d["path"] != str(p)]
    index_data["chunks"] = [c for c in index_data["chunks"] if c["doc_path"] != str(p)]

    index_data["documents"].append({
        "name": p.name,
        "path": str(p),
        "chunk_count": len(chunks),
        "size_kb": round(p.stat().st_size / 1024, 1)
    })

    for c_idx, c_text in enumerate(chunks):
        index_data["chunks"].append({
            "doc_name": p.name,
            "doc_path": str(p),
            "chunk_id": c_idx,
            "text": c_text
        })

    KB_INDEX_FILE.write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding='utf-8')

    return f"""📚 **【私有知识库入库成功】**
📄 **文档名称**：`{p.name}`
🧩 **知识切块**：已切分为 **{len(chunks)}** 个向量检索分块
💾 **库内状态**：当前知识库共收录 **{len(index_data['documents'])}** 篇本地文档，随时可通过自然语言提问检索！"""


@register_tool(description="在本地私有知识库中检索与提问相关的知识片段(RAG)。参数：query(提问或检索关键词)")
def query_knowledge_base(query: str) -> str:
    """私有知识库 RAG 检索"""
    _ensure_kb_dir()
    index_data = json.loads(KB_INDEX_FILE.read_text(encoding='utf-8'))
    chunks = index_data.get("chunks", [])

    if not chunks:
        return "📚 知识库当前暂无文档，请先通过 `add_document_to_knowledge_base` 导入 PDF/Word/TXT 文档~"

    q_tokens = _simple_tokenize(query)
    scored_chunks = []
    for c in chunks:
        c_tokens = _simple_tokenize(c["text"])
        overlap = len(q_tokens.intersection(c_tokens))
        if overlap > 0:
            score = overlap / (math.sqrt(len(q_tokens)) * math.sqrt(len(c_tokens)) + 1e-5)
            scored_chunks.append((score, c))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_chunks = scored_chunks[:4]

    if not top_chunks or top_chunks[0][0] < 0.05:
        return f"ℹ️ 在知识库中未检索到与『{query}』高度相关的文档段落。"

    results = []
    for rank, (score, chunk) in enumerate(top_chunks, 1):
        results.append(f"📖 **[来源: `{chunk['doc_name']}` (块 #{chunk['chunk_id']})]** (匹配度: {round(score*100, 1)}%)\n```\n{chunk['text'][:350]}\n```")

    return f"🔍 **【知识库精准检索结果】(`{query}`)**：\n\n" + "\n\n".join(results)


@register_tool(description="查看本地私有知识库收录的全部文档列表与知识分块统计。")
def list_knowledge_base_docs() -> str:
    """列出知识库文档"""
    _ensure_kb_dir()
    index_data = json.loads(KB_INDEX_FILE.read_text(encoding='utf-8'))
    docs = index_data.get("documents", [])
    if not docs:
        return "📚 本地知识库暂无文档。"

    lines = [f"📚 **【本地私有知识库目录】(共 {len(docs)} 篇)**："]
    for i, d in enumerate(docs, 1):
        lines.append(f"{i}. **{d['name']}** ({d['size_kb']} KB) · `{d['chunk_count']}` 个知识切块")
    return "\n".join(lines)
