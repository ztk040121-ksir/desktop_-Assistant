---
name: firecrawl_scraper
description: "Firecrawl 智能全网抓取与深度结构化数据提取。支持带 JS 动态渲染的网页抓取、Markdown 文本清洗与整站深度 Crawl。"
version: 2.0.0
tools:
  - firecrawl_scrape
  - firecrawl_search
  - firecrawl_crawl
---

# Firecrawl 智能全网爬虫与提取 Skill (Firecrawl Scraper Skill)

## 技能概述
通过 Firecrawl 强大的 Headless 浏览器引擎与智能解析流水线，将任意复杂网页、SPA 单页应用转化为极其干净的高质量 Markdown，并剔除广告与无用标签。

## 核心功能
1. **单页深度提取 (Scrape)**：渲染 JavaScript 并将正文转换为结构化 Markdown。
2. **全网内容搜索 (Search)**：直接从搜索结果中提取深层网页内容摘要。
3. **整站爬取 (Crawl)**：递归发现并抓取全站相关子页面。

## 触发意图示例
- "抓取这个网页的正文并整理成 Markdown：https://example.com/article"
- "在全网深度搜索关于 DeepSeek-R1 架构解析的技术文章"
