# -*- coding: utf-8 -*-
"""
Skill 技能开发与脚手架工具 (Skill Creator Tools)
- 真实实现自动在 skills/ 目录创建标准 SKILL.md 规范与 plugins/ Python 工具
- 语法与 YAML frontmatter 校验
"""
import os
import re
from pathlib import Path
from typing import Optional
from core.plugin_manager import register_tool


@register_tool(
    name="create_custom_skill",
    description="在本地工作区自动创建标准的 Skill 规范目录（含 SKILL.md）与配套 Python 插件工具代码"
)
def create_custom_skill(skill_name: str, description: str, instructions: Optional[str] = None, create_plugin: bool = True) -> str:
    """
    创建标准 Skill 规范目录与配套 Python 插件
    :param skill_name: 技能英文标识，如 'my_custom_tool'
    :param description: 技能功能简述
    :param instructions: 技能详细指南 Markdown 内容
    :param create_plugin: 是否同时在 plugins/ 目录生成 Python 插件源码
    """
    root_dir = Path(__file__).resolve().parent.parent
    skills_dir = root_dir / "skills" / skill_name
    skills_dir.mkdir(parents=True, exist_ok=True)

    body = instructions or f"""# {skill_name} 技能使用指南

本技能为大模型提供【{description}】能力。

## 使用场景与工作流
1. 识别用户对应业务意图；
2. 调用配套工具执行操作并返回结果。
"""

    skill_content = f"""---
name: {skill_name}
description: {description}
---

{body.strip()}
"""
    (skills_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

    plugin_msg = ""
    if create_plugin:
        plugins_dir = root_dir / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)
        py_file = plugins_dir / f"{skill_name}_tools.py"
        if not py_file.exists():
            py_code = f"""# -*- coding: utf-8 -*-
\"\"\"
{skill_name} 插件工具集
\"\"\"
from core.plugin_manager import register_tool

@register_tool(
    name="execute_{skill_name}",
    description="{description}"
)
def execute_{skill_name}(query: str) -> str:
    \"\"\"
    执行 {skill_name} 操作
    :param query: 用户输入指令
    \"\"\"
    return f"[{skill_name}] 处理成功，参数：{{query}}"
"""
            py_file.write_text(py_code, encoding="utf-8")
            plugin_msg = f"\n- 配套插件：{py_file.name}"

    return f"✅ 成功创建 Skill 技能套件：\n- 规范文件：{skills_dir / 'SKILL.md'}{plugin_msg}"


@register_tool(
    name="validate_skill_spec",
    description="校验指定 Skill 目录下的 SKILL.md 是否符合 YAML frontmatter 规范"
)
def validate_skill_spec(skill_name: str) -> str:
    """
    校验指定 Skill 目录规范
    :param skill_name: 技能名称
    """
    root_dir = Path(__file__).resolve().parent.parent
    skill_file = root_dir / "skills" / skill_name / "SKILL.md"
    if not skill_file.exists():
        return f"❌ SKILL.md 文件不存在：{skill_file}"

    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return f"⚠️ 缺少开头的 YAML frontmatter 分隔符 (---)"

    parts = text.split("---", 2)
    if len(parts) < 3:
        return f"⚠️ YAML frontmatter 格式不完整"

    fm = parts[1]
    has_name = "name:" in fm
    has_desc = "description:" in fm

    if has_name and has_desc:
        return f"✅ Skill【{skill_name}】规范校验 100% 通过！"
    return f"⚠️ 缺少必需字段：{'name ' if not has_name else ''}{'description' if not has_desc else ''}"
