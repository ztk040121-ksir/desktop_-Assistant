"""
插件管理器 - 自动发现并加载 plugins/ 目录下的工具
你可以在 plugins/ 目录下新建 .py 文件并使用 @register_tool 装饰器来扩展功能
"""
import importlib
import importlib.util
import inspect
import asyncio
from pathlib import Path
from typing import Callable, Optional
from functools import wraps


# 全局工具注册表
_TOOL_REGISTRY: dict[str, dict] = {}


def register_tool(description: str, name: Optional[str] = None):
    """
    装饰器：将函数注册为桌宠可用的工具
    用法示例：
        @register_tool(description="打开微信")
        def open_wechat():
            ...
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
    """插件加载与管理器"""

    def __init__(self, plugins_dir: Path, config: dict, ai_engine):
        self.plugins_dir = plugins_dir
        self.config = config
        self.ai_engine = ai_engine
        self.loaded_plugins: dict[str, dict] = {}  # plugin_name -> metadata
        self.enabled_plugins: set[str] = set(config.get("plugins", {}).get("enabled", []))

    def load_all(self):
        """扫描并加载 plugins/ 目录下所有 .py 文件"""
        _TOOL_REGISTRY.clear()
        self.loaded_plugins.clear()

        for py_file in self.plugins_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            plugin_name = py_file.stem
            try:
                self._load_plugin(py_file, plugin_name)
                print(f"  ✅ 插件加载成功: {plugin_name}")
            except Exception as e:
                print(f"  ❌ 插件加载失败 {plugin_name}: {e}")

        print(f"🔌 共加载 {len(self.loaded_plugins)} 个插件，{len(_TOOL_REGISTRY)} 个工具")

    def _load_plugin(self, py_file: Path, plugin_name: str):
        """加载单个插件文件"""
        spec = importlib.util.spec_from_file_location(plugin_name, py_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 统计该插件注册了哪些工具
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
            # 移除旧的工具注册
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

    async def call_tool(self, tool_name: str, **kwargs) -> str:
        """调用指定工具"""
        if tool_name not in _TOOL_REGISTRY:
            return f"❌ 工具 '{tool_name}' 不存在"
        tool = _TOOL_REGISTRY[tool_name]
        try:
            if tool["is_async"]:
                result = await tool["func"](**kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: tool["func"](**kwargs))
            return str(result)
        except Exception as e:
            return f"工具执行失败: {e}"

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
        """启用/禁用插件"""
        if plugin_name in self.loaded_plugins:
            self.loaded_plugins[plugin_name]["enabled"] = enabled
            if enabled:
                self.enabled_plugins.add(plugin_name)
            else:
                self.enabled_plugins.discard(plugin_name)
