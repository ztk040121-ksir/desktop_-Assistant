---
name: knowledge-base-agent
description: "本地 RAG 知识库智能体 — 上传 PDF/Word/TXT/HTML 文档，构建私有向量知识库，通过自然语言提问获取精准回答并标注引用来源。支持 FAISS 向量检索、OpenVINO 推理加速（CPU/GPU/NPU）、INT8 量化，数据完全本地运行。适用场景：论文研报问答、企业内部知识管理、个人笔记智能检索、私有文档知识库搭建。触发词：知识库、RAG、文档问答、本地问答、知识检索、文档导入、私有知识库、向量检索、论文问答、知识管理。"
agent_created: true
---

# Knowledge Base Agent — 本地 RAG 知识库智能体

基于 OpenVINO 优化的本地 RAG（检索增强生成）问答系统。用户上传文档后，系统自动完成解析、分块、向量化与索引构建；通过自然语言提问即可获得精准回答，所有数据完全本地运行，确保隐私安全。

## 触发条件

当用户提出以下意图时触发本技能：
- 上传/导入文档并构建知识库
- 对已有文档进行提问、检索、摘要
- 管理知识库（查看文档列表、删除文档、清空）
- 使用自然语言描述文档处理需求（如"帮我把这些论文整理成知识库"）

## 核心能力

### 1. 多格式文档解析

| 格式 | 扩展名 | 解析引擎 | 说明 |
|------|--------|----------|------|
| PDF | `.pdf` | PyMuPDF | 文本提取，含表格 |
| Word | `.docx` | python-docx | 段落 + 表格提取 |
| 旧版 Word | `.doc` | antiword/LibreOffice | 自动降级策略 |
| 纯文本 | `.txt` | 多编码检测 | UTF-8/GBK/GB2312/Latin-1 |
| Markdown | `.md` | 纯文本 | 保留结构 |
| HTML | `.html` | BeautifulSoup | 自动去除脚本/样式 |

**文本分块策略（递归切分，三层降级）：**
1. 按段落切分（优先保持语义完整性）
2. 段落过长时按句子切分（中英文句号/问号/叹号）
3. 句子仍超长时按固定长度切分（含 overlap 重叠，默认 512 字符 / 128 重叠）

**文本清洗：** 多余空白合并 → 控制字符移除 → 连续空行压缩 → 页码格式移除

### 2. 向量检索引擎

- **Embedding 模型：** BAAI/bge-large-zh-v1.5（1024 维，中文语义优化）
- **向量数据库：** FAISS（IndexFlatIP + IndexIDMap，支持余弦相似度与文档删除）
- **检索策略：** L2 归一化 → 内积相似度 → Top-K 过滤 → 相似度阈值截断（默认 0.7）

### 3. 本地 LLM 推理

- **默认模型：** Qwen/Qwen2.5-7B-Instruct
- **OpenVINO 加速：** 支持 CPU/GPU/NPU 自动选择（优先级 NPU > GPU > CPU）
- **INT8 量化：** 默认启用，7B 模型显存从 ~14GB 降至 ~7GB
- **模型缓存：** 首次转换后持久化存储，后续直接加载

### 4. RAG 问答流水线

提供四种查询模式：

| 模式 | 方法 | 适用场景 |
|------|------|----------|
| 标准查询 | `query()` | 日常问答，检索 → Prompt → 生成 |
| 对话模式 | `chat()` | 多轮追问，支持历史上下文 |
| 带引用查询 | `query_with_citation()` | 学术/研报场景，回答中标注 [1][2] 来源 |
| 多查询检索 | `multi_query_retrieval()` | 复杂问题，LLM 生成查询变体提高召回率 |

## Agent 工作流程

当用户上传文档或提出知识库相关请求时，按以下流程执行：

### 阶段一：文档导入

```
用户上传文档
  → DocumentProcessor.process() 解析 + 分块
  → EmbeddingEngine.encode() 向量化（批量处理，默认 batch_size=32）
  → VectorStore.add() 写入 FAISS 索引 + 持久化
  → 返回处理结果（成功/失败文档列表 + 总分块数）
```

**Agent 操作指引：**
- 收到文件后立即调用 `add_documents()`，不等待用户确认
- 若文件格式不支持，明确告知用户并列出支持格式
- 处理完成后汇报结果：成功 N 个文档，共 M 个文本块

### 阶段二：知识检索

```
用户提问
  → EmbeddingEngine.encode([query]) 查询向量化
  → VectorStore.search() Top-K 检索 + 阈值过滤
  → RAGPipeline._build_context() 构建上下文
  → LLMEngine.generate() 生成回答
  → 返回 { answer, sources, citations }
```

**Agent 操作指引：**
- 标准问题使用 `query()`，学术/严谨场景使用 `query_with_citation()`
- 回答时展示来源文档信息
- 若检索结果低于阈值，诚实告知"知识库中未找到相关信息"

### 阶段三：知识库管理

**Agent 操作指引：**
- `list_documents()` → 以表格形式展示文档列表
- `delete_document(id)` → 删除前需用户确认
- `clear_knowledge_base()` → 危险操作，必须二次确认
- `get_stats()` → 展示文档数、分块数、模型信息等统计

## 命令行接口

```bash
cd scripts
python main.py --add paper.pdf report.docx    # 导入文档
python main.py --query "核心观点是什么？"       # 查询
python main.py --stats                          # 查看统计
python main.py --clear                          # 清空知识库
python main.py --config custom.json --query ""  # 自定义配置
```

## 测试

```bash
cd scripts
pip install pytest beautifulsoup4
python -m pytest tests/ -v
```

## 详细文档

- **快速开始与示例：** 参见 `references/README.md`
- **完整 API 参考：** 参见 `references/api_reference.md`
- **架构设计详解：** 参见 `references/architecture.md`
- **配置参数说明：** 参见 `references/configuration.md`

## 环境要求

- Python 3.8+
- Intel CPU（AVX2）或 Intel GPU/NPU
- 内存 8GB+（推荐 16GB）
- 磁盘 10GB+（模型缓存）

## 注意事项

- 首次运行自动从 Hugging Face / ModelScope 下载模型，需网络连接
- OpenVINO 为可选加速，未安装时自动回退到标准 HuggingFace 推理
- `.doc` 格式需系统安装 antiword 或 LibreOffice
- 向量数据持久化在 `./vector_db`，删除该目录将丢失所有已导入文档

## 文件结构

```
knowledge-base-agent/
├── SKILL.md                          # 技能描述（本文件）
├── scripts/                          # 核心代码
│   ├── main.py                       # 主入口 + KnowledgeBaseAgent 类
│   ├── document_processor.py         # 文档解析与分块
│   ├── embedding_engine.py           # Embedding 向量化（OpenVINO）
│   ├── vector_store.py               # FAISS 向量数据库
│   ├── llm_engine.py                 # LLM 推理引擎（OpenVINO）
│   ├── rag_pipeline.py               # RAG 检索增强生成流水线
│   ├── openvino_config.py            # OpenVINO 设备检测与优化
│   ├── __init__.py                   # 包初始化
│   ├── requirements.txt              # Python 依赖
│   └── tests/                        # 测试用例
│       ├── test_document_processor.py
│       ├── test_vector_store.py
│       ├── test_rag_pipeline.py
│       └── test_openvino_config.py
├── references/                       # 参考文档（按需加载）
│   ├── README.md                     # 快速开始指南
│   ├── api_reference.md              # Python API 完整参考
│   ├── architecture.md               # 技术架构详解
│   └── configuration.md              # 配置参数与环境要求
└── assets/                           # 资源文件
    └── skill.json                    # 技能配置（模型/参数/UI）
```

## 依赖安装

```bash
cd scripts && pip install -r requirements.txt
```

核心依赖：torch, transformers, sentence-transformers, faiss-cpu, pymupdf, python-docx, openvino, optimum[openvino]
