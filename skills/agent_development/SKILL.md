---
name: agent_development
description: AI Agent 智能体应用架构与工作流编排开发技能，支持多智能体角色拆解、工具调用链设计、提示词系统构建与自主规划执行。
---

# Agent 应用开发技能 (Agent Development Skill)

本技能为开发者提供端到端的 AI 智能体 (Agent) 架构与工作流编排能力。

## 智能体开发核心阶段

1. **角色定义与边界划分 (Persona & Boundary)**
   - 确定 Agent 的核心专长、约束条件与交互模式；
2. **工具链集成与挂载 (Tool Chain Attachment)**
   - 挂载文件读写、代码解释器、网络检索与特定业务 MCP 工具；
3. **规划与反思循环 (Plan & Re-Act Loop)**
   - 实现目标拆解、单步验证与错误重试机制。

## 配套工具函数 (Tools)

- `scaffold_agent(agent_name, role_description, tools_needed, system_prompt)`: 生成标准智能体配置与工作流定义文件。
- `validate_agent_workflow(agent_config_path)`: 校验智能体配置规范与依赖合法性。
