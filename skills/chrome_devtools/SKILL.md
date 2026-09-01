---
name: chrome_devtools
description: "Chrome DevTools 实时浏览器自动化控制与性能分析。支持打开并导航至指定网页、性能洞察 Web Vitals 评估与控制台调试。"
version: 2.0.0
tools:
  - chrome_navigate_page
  - chrome_performance_insights
---

# Chrome DevTools 浏览器自动化 Skill (Chrome DevTools Skill)

## 技能概述
基于 Chrome DevTools 协议与 MCP 标准，实现对桌面 Chrome 浏览器的实时自动化控制、网页导航、FCP/LCP/CLS 等核心性能指标追踪与分析。

## 核心功能
1. **浏览器导航控制**：快速唤起并跳转到目标网址。
2. **性能与 Web Vitals 分析**：评估页面加载耗时、网络请求数、DOM 解析时间与优化建议。

## 触发意图示例
- "帮我用 Chrome 打开 B站/GitHub 页面"
- "测试一下这个网站的打开速度和性能指标"
