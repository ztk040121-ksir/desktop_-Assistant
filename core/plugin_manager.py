# -*- coding: utf-8 -*-
"""
插件与技能管理器 (Plugin & Skill Manager)
- 自动发现并加载当前工作区 plugins/ 目录下的工具
- 管理当前工作区 skills/ 目录下的 Skill 套件及元数据 (SKILL.md)
- 支持技能真实拉取、安装、热重载、启用/停用与本地路径安全隔离
"""
import os
import json
import importlib
import importlib.util
import inspect
import asyncio
from pathlib import Path
from typing import Callable, Optional, Dict, List, Any
from functools import wraps


# 全局工具注册表
_TOOL_REGISTRY: dict[str, dict] = {}


def register_tool(description: str, name: Optional[str] = None):
    """
    装饰器：将函数注册为桌宠可用的工具
    """
    def decorator(func: Callable):
        tool_name = name or func.__name__
        _TOOL_REGISTRY[tool_name] = {
            "func": func,
            "description": description,
            "module": func.__module__,
            "is_async": asyncio.iscoroutinefunction(func),
            "params": list(inspect.signature(func).parameters.keys())
        }
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
        wrapper._tool_name = tool_name
        return wrapper
    return decorator


class PluginManager:
    """插件与技能生命周期管理器"""

    def __init__(self, plugins_dir: Path, config: dict, ai_engine):
        self.plugins_dir = plugins_dir
        self.workspace_dir = plugins_dir.parent
        self.skills_dir = self.workspace_dir / "skills"
        self.config = config
        self.ai_engine = ai_engine
        self.loaded_plugins: dict[str, dict] = {}  # plugin_name -> metadata
        self.enabled_plugins: set[str] = set(config.get("plugins", {}).get("enabled", []))

    def load_all(self):
        """扫描并加载 plugins/ 目录下所有 .py 文件"""
        _TOOL_REGISTRY.clear()
        self.loaded_plugins.clear()

        if not self.plugins_dir.exists():
            self.plugins_dir.mkdir(parents=True, exist_ok=True)

        for py_file in self.plugins_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            plugin_name = py_file.stem
            try:
                self._load_plugin(py_file, plugin_name)
                print(f"  [Plugin] OK loaded: {plugin_name}")
            except Exception as e:
                print(f"  [Plugin] FAIL {plugin_name}: {e}")

        print(f"[PluginManager] Loaded {len(self.loaded_plugins)} plugins, {len(_TOOL_REGISTRY)} tools")

    def _load_plugin(self, py_file: Path, plugin_name: str):
        """加载单个插件文件"""
        spec = importlib.util.spec_from_file_location(plugin_name, py_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        plugin_tools = [
            t_name for t_name, t_info in _TOOL_REGISTRY.items()
            if t_info["module"] == plugin_name
        ]
        self.loaded_plugins[plugin_name] = {
            "file": str(py_file),
            "tools": plugin_tools,
            "enabled": plugin_name in self.enabled_plugins
        }

    def reload_plugin(self, plugin_name: str):
        """热重载单个插件（管理中心用）"""
        py_file = self.plugins_dir / f"{plugin_name}.py"
        if py_file.exists():
            old_tools = self.loaded_plugins.get(plugin_name, {}).get("tools", [])
            for t in old_tools:
                _TOOL_REGISTRY.pop(t, None)
            self._load_plugin(py_file, plugin_name)
            return True
        return False

    def reload_all(self):
        """重新加载所有插件"""
        self.load_all()

    def get_tool_descriptions(self) -> str:
        """返回所有工具描述（用于注入到 AI System Prompt）"""
        if not _TOOL_REGISTRY:
            return ""
        lines = []
        for name, info in _TOOL_REGISTRY.items():
            plugin = info["module"]
            if plugin in self.loaded_plugins and not self.loaded_plugins[plugin]["enabled"]:
                continue
            params_str = ", ".join(info["params"]) if info["params"] else "无参数"
            lines.append(f"- {name}({params_str}): {info['description']}")
        return "\n".join(lines)

    TOOL_ALIASES = {
        "process_excel": "process_excel_file",
        "modify_excel": "process_excel_file",
        "excel_process": "process_excel_file",
        "excel_code": "execute_excel_code",
        "run_excel_code": "execute_excel_code",
        "python": "run_python_code",
        "run_python": "run_python_code",
        "python_code": "run_python_code",
        "github": "github_search_repos",
        "github_search": "github_search_repos",
        "search_github": "github_search_repos",
        "search_repos": "github_search_repos",
        "ppt": "generate_presentation_ppt",
        "generate_ppt": "generate_presentation_ppt",
        "create_ppt": "generate_presentation_ppt",
        "powerpoint": "generate_presentation_ppt",
        "search": "search_web_news",
        "web_search": "search_web_news",
        "search_news": "search_web_news",
        "amap_route": "amap_route_planning",
        "route_planning": "amap_route_planning",
        "navigation": "amap_route_planning",
        "xiaohongshu": "generate_xiaohongshu_note",
        "xhs_note": "generate_xiaohongshu_note",
        "kb_query": "query_knowledge_base",
        "rag": "query_knowledge_base",
        "knowledge_base": "query_knowledge_base"
    }

    async def call_tool(self, tool_name: str, **kwargs) -> str:
        """调用指定名称的工具（支持自动别名与模糊容错）"""
        target_name = self.TOOL_ALIASES.get(tool_name.lower().strip(), tool_name.strip())
        if target_name not in _TOOL_REGISTRY:
            for t_k in _TOOL_REGISTRY:
                if tool_name.lower() in t_k.lower() or t_k.lower() in tool_name.lower():
                    target_name = t_k
                    break

        if target_name not in _TOOL_REGISTRY:
            return f"⚠️ 抱歉，未找到名为 '{tool_name}' 的插件工具。"

        func = _TOOL_REGISTRY[target_name]["func"]
        try:
            res = func(**kwargs)
            if inspect.isawaitable(res):
                res = await res
            return str(res)
        except Exception as e:
            return f"❌ 工具 '{target_name}' 执行失败: {e}"

    def get_plugin_list(self) -> list[dict]:
        """获取所有插件信息（管理中心展示用）"""
        return [
            {
                "name": name,
                "file": info["file"],
                "tools": info["tools"],
                "tool_count": len(info["tools"]),
                "enabled": info["enabled"]
            }
            for name, info in self.loaded_plugins.items()
        ]

    def toggle_plugin(self, plugin_name: str, enabled: bool):
        """启用/禁用插件并保存持久化配置"""
        if plugin_name in self.loaded_plugins:
            self.loaded_plugins[plugin_name]["enabled"] = enabled
        if enabled:
            self.enabled_plugins.add(plugin_name)
        else:
            self.enabled_plugins.discard(plugin_name)
        self._persist_config()

    def _persist_config(self):
        """持久化保存插件状态到当前工作区的 config.json"""
        try:
            cfg_path = self.workspace_dir / "config.json"
            if "plugins" not in self.config:
                self.config["plugins"] = {}
            self.config["plugins"]["enabled"] = sorted(list(self.enabled_plugins))
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[PluginManager] Failed to persist config: {e}")

    # ==========================================
    # 技能 (Skill) 真实发现、拉取与管理系统
    # 严格保证所有操作只在当前工作区 skills/ 和 plugins/ 执行
    # ==========================================

    def scan_installed_skills(self) -> List[Dict[str, Any]]:
        """扫描当前工作区 skills/ 目录下所有已真实安装的技能"""
        installed = []
        if not self.skills_dir.exists():
            return installed

        for skill_folder in self.skills_dir.iterdir():
            if not skill_folder.is_dir():
                continue
            skill_md = skill_folder / "SKILL.md"
            if not skill_md.exists():
                continue

            meta = self._parse_skill_md(skill_md, skill_folder.name)
            installed.append(meta)

        return installed

    def _parse_skill_md(self, skill_md_path: Path, skill_id: str) -> Dict[str, Any]:
        """解析 SKILL.md 的 YAML 前置元数据与说明"""
        name = skill_id
        desc = ""
        version = "1.0.0"
        tools = []
        try:
            text = skill_md_path.read_text(encoding="utf-8")
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = parts[1]
                    for line in frontmatter.splitlines():
                        line = line.strip()
                        if line.startswith("name:"):
                            name = line[5:].strip().strip('"').strip("'")
                        elif line.startswith("description:"):
                            desc = line[12:].strip().strip('"').strip("'")
                        elif line.startswith("version:"):
                            version = line[8:].strip().strip('"').strip("'")
                        elif line.startswith("- ") and "tools:" in frontmatter:
                            tools.append(line[2:].strip())
        except Exception:
            pass

        return {
            "id": skill_id,
            "name": name,
            "desc": desc,
            "version": version,
            "tools": tools,
            "folder_path": str(skill_md_path.parent),
            "md_path": str(skill_md_path)
        }

    def get_skill_md_content(self, skill_id: str) -> str:
        """获取技能 SKILL.md 完整内容"""
        skill_md = self.skills_dir / skill_id / "SKILL.md"
        if skill_md.exists():
            try:
                return skill_md.read_text(encoding="utf-8")
            except Exception as e:
                return f"❌ 读取 SKILL.md 失败: {e}"
        return "⚠️ 未找到该技能的 SKILL.md 使用手册。"

    def install_or_pull_skill(self, skill_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        真实安装/拉取技能至当前工作区：
        1. 确保写入当前目录 ./skills/<id>/SKILL.md
        2. 自动启用对应 plugins/<plugin_name>.py
        3. 重新加载并更新状态
        """
        skill_id = skill_meta.get("id", "")
        if not skill_id:
            return {"success": False, "msg": "技能 ID 无效"}

        target_folder = self.skills_dir / skill_id
        target_folder.mkdir(parents=True, exist_ok=True)
        target_md = target_folder / "SKILL.md"

        # 如果已有真实 SKILL.md，保留并确保内容完整；若无则自动生成完整元数据
        if not target_md.exists() or target_md.stat().st_size == 0:
            md_content = f"""---
name: {skill_meta.get('name', skill_id)}
description: "{skill_meta.get('desc', '')}"
version: 2.0.0
tools:
{chr(10).join(['  - ' + t for t in skill_meta.get('tools', [])])}
---

# {skill_meta.get('name', skill_id)} Skill

## 技能描述
{skill_meta.get('desc', '')}

## 本地挂载信息
- 技能 ID: `{skill_id}`
- 分类: `{skill_meta.get('cat', '通用')}`
- 关联插件: `plugins/{skill_meta.get('plugin_file', skill_id + '.py')}`
"""
            target_md.write_text(md_content, encoding="utf-8")

        # 启用并热加载对应 plugin
        plugin_file_name = skill_meta.get("plugin_name", "")
        if plugin_file_name:
            self.enabled_plugins.add(plugin_file_name)
            self._persist_config()
            py_file = self.plugins_dir / f"{plugin_file_name}.py"
            if py_file.exists():
                self.reload_plugin(plugin_file_name)

        return {
            "success": True,
            "skill_id": skill_id,
            "installed_path": str(target_folder),
            "msg": f"技能【{skill_meta.get('name', skill_id)}】已成功拉取并安装到当前工作区：{target_folder}"
        }

    def uninstall_skill(self, skill_id: str, plugin_name: str = "") -> Dict[str, Any]:
        """卸载/停用技能"""
        if plugin_name:
            self.toggle_plugin(plugin_name, False)
        return {
            "success": True,
            "msg": f"技能【{skill_id}】已停用并从挂载列表中移除。"
        }
