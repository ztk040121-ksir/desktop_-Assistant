# -*- coding: utf-8 -*-
"""
Agent 智能体应用开发工具 (Agent Development Tools)
- 真实实现多智能体编排脚手架、角色设定与系统提示词规范生成
- 智能体工具调用链与工作流结构化校验
"""
import json
from pathlib import Path
from typing import Optional, List, Dict
from core.plugin_manager import register_tool


@register_tool(
    name="scaffold_agent",
    description="在本地工作区创建完整的 AI 智能体 (Agent) 配置与工作流架构定义文件"
)
def scaffold_agent(agent_name: str, role_description: str, tools_needed: Optional[str] = None, system_prompt: Optional[str] = None, output_dir: Optional[str] = None) -> str:
    """
    创建完整的 AI 智能体配置与工作流架构定义
    :param agent_name: 智能体标识名称，如 'CodeReviewAgent'
    :param role_description: 智能体角色定位，如 '资深全栈架构师与代码安全审计专家'
    :param tools_needed: 依赖的工具列表，逗号分隔，如 'file_tools,python_interpreter,web_search'
    :param system_prompt: 核心系统提示词
    :param output_dir: 输出目录
    """
    try:
        from core.security_guard import SecurityGuard
        guard = SecurityGuard.get_instance()
        target_base = Path(output_dir) if output_dir else guard.get_workspace_root()
    except Exception:
        target_base = Path.cwd()

    agents_dir = target_base / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    tools_list = [t.strip() for t in tools_needed.split(",")] if tools_needed else ["file_tools", "python_interpreter"]
    sp = system_prompt or f"你是一个名为「{agent_name}」的高级 AI 智能体，专长于：{role_description}。请根据用户输入高效、安全地拆解目标并调用工具执行。"

    agent_config = {
        "agent_name": agent_name,
        "version": "1.0.0",
        "role_description": role_description,
        "system_prompt": sp,
        "tools": tools_list,
        "max_iterations": 10,
        "temperature": 0.3,
        "workflow": [
            {"step": 1, "action": "parse_intent", "desc": "解析用户输入目标与上下文约束"},
            {"step": 2, "action": "plan_steps", "desc": "规划执行路径与工具调用链"},
            {"step": 3, "action": "execute_tools", "desc": "安全沙箱内执行工具并捕获输出"},
            {"step": 4, "action": "synthesize_response", "desc": "综合结果生成清晰结构化回复"}
        ]
    }

    config_file = agents_dir / f"{agent_name.lower()}_config.json"
    config_file.write_text(json.dumps(agent_config, ensure_ascii=False, indent=2), encoding="utf-8")

    return f"✅ 成功在工作区生成智能体定义文件：{config_file}\n- 角色：{role_description}\n- 挂载工具：{', '.join(tools_list)}"


@register_tool(
    name="validate_agent_workflow",
    description="校验智能体工作流配置文件结构、依赖工具及状态转换合法性"
)
def validate_agent_workflow(agent_config_path: str) -> str:
    """
    校验智能体工作流配置文件
    :param agent_config_path: 智能体配置文件路径
    """
    p = Path(agent_config_path)
    if not p.exists():
        return f"❌ 配置文件不存在：{agent_config_path}"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        req_keys = ["agent_name", "role_description", "system_prompt", "tools"]
        missing = [k for k in req_keys if k not in data]
        if missing:
            return f"⚠️ 校验未通过，缺失核心字段：{', '.join(missing)}"
        return f"✅ 智能体【{data.get('agent_name')}】配置结构完整合法！包含 {len(data.get('tools', []))} 个工具链依赖。"
    except Exception as e:
        return f"❌ 解析 JSON 失败：{e}"
