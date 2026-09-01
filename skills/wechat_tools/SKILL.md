---
name: wechat_tools
description: "微信公众号文章提取与传播分析。支持提取微信文章正文、标题、作者、发布时间、排版结构与核心观点提炼。"
version: 2.0.0
tools:
  - fetch_wechat_article_content
  - analyze_article_structure
---

# 微信公众号文章提取与分析 Skill (WeChat Article Skill)

## 技能概述
支持对微信公众号公开文章链接进行深度内容解析、清洗样式、提取正文与图片链接，并自动梳理行文脉络与爆款文案特征。

## 核心功能
1. **文章正文提取**：输入 mp.weixin.qq.com 链接，提取干净正文与元数据。
2. **结构与观点分析**：输出文章大纲、金句摘录与传播亮点分析。

## 触发意图示例
- "帮我提取这篇微信公众号文章的内容并做个摘要：https://mp.weixin.qq.com/s/..."
