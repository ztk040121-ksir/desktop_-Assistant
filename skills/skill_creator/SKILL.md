---
name: skill_creator
description: Skill 技能插件开发与自动化脚手架技能，支持自动生成符合 Antigravity/NovaDesk 规范的 SKILL.md 文档、Python 插件工具代码与规范自检。
---

# Skill 开发与创建技能 (Skill Creator Skill)

本技能帮助用户快速编写、扩展与校验桌面助手的技能套件 (Skill) 和 Python 工具插件。

## Skill 规范要求
1. 每个 Skill 存放于 `skills/<skill_name>/` 目录下；
2. 根目录必须包含 `SKILL.md`，以 `---` 开头包含 `name` 和 `description` 的 YAML frontmatter；
3. 配套 Python 工具位于 `plugins/<name>_tools.py`，使用 `@register_tool` 注册。

## 配套工具函数 (Tools)
- `create_custom_skill(skill_name, description, instructions, create_plugin)`: 一键生成 Skill 规范与插件源码。
- `validate_skill_spec(skill_name)`: 自动化校验 Skill 规范完整性。
