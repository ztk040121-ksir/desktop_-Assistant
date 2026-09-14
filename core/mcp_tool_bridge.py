# -*- coding: utf-8 -*-
"""
MCP 动态工具桥接器 (MCP Dynamic Tool Bridge)
- 动态读取并解析 mcp_config.json 中的 mcpServers
- 将已启用的 MCP 服务所导出的 tools 自动注册挂载到 _TOOL_REGISTRY
- 当大模型触发 MCP 工具调用时，透明通过 MCPStdioClient 路由至子进程执行
- 提供真实启动握手与健康检查 (test_mcp_connection)
"""
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from core.mcp_stdio_client import MCPStdioClient, MCPClientError, get_mcp_client
from core.plugin_manager import _TOOL_REGISTRY

ROOT_DIR = Path(__file__).parent.parent
MCP_CONFIG_PATH = ROOT_DIR / "mcp_config.json"
APP_CONFIG_PATH = ROOT_DIR / "config.json"


class MCPToolBridge:
    """MCP 动态工具挂载与生命周期桥接管理器"""
    _instance: Optional["MCPToolBridge"] = None

    def __init__(self):
        self._mounted_servers: Dict[str, Dict[str, Any]] = {}
        self._mounted_tools: Dict[str, str] = {}  # tool_name -> server_name

    @classmethod
    def get_instance(cls) -> "MCPToolBridge":
        if cls._instance is None:
            cls._instance = MCPToolBridge()
        return cls._instance

    def load_mcp_config(self) -> Dict[str, Any]:
        """读取 mcp_config.json"""
        if not MCP_CONFIG_PATH.exists():
            return {"mcpServers": {}}
        try:
            with open(MCP_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"mcpServers": {}}

    def save_mcp_config(self, data: Dict[str, Any]):
        """持久化保存 mcp_config.json"""
        with open(MCP_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_enabled_server_ids(self) -> set:
        """从 config.json 获取启用的 MCP 服务 ID"""
        if not APP_CONFIG_PATH.exists():
            return set()
        try:
            with open(APP_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            enabled = set(cfg.get("connected_connectors", []))
            enabled.update(cfg.get("enabled_mcp_servers", []))
            return enabled
        except Exception:
            return set()

    def mount_all_mcp_tools(self):
        """扫描 mcp_config.json 并将启用的 MCP 工具动态注入 _TOOL_REGISTRY"""
        cfg_data = self.load_mcp_config()
        servers = cfg_data.get("mcpServers", {})
        enabled_ids = self.get_enabled_server_ids()

        for srv_id, srv_info in servers.items():
            is_enabled = (srv_id in enabled_ids) if enabled_ids else True
            if not is_enabled:
                continue

            tools_list = srv_info.get("tools", [])
            for t_item in tools_list:
                t_name = t_item.get("name")
                t_desc = t_item.get("description", f"MCP [{srv_id}] 服务工具")
                if not t_name:
                    continue
                self._register_dynamic_mcp_tool(srv_id, srv_info, t_name, t_desc)

    def _register_dynamic_mcp_tool(self, server_id: str, server_info: dict, tool_name: str, description: str):
        """将单个 MCP 工具动态注册进 _TOOL_REGISTRY"""
        cmd = server_info.get("command", "npx")
        args = server_info.get("args", [])
        env = server_info.get("env", {})

        def _make_caller(s_id: str, t_name: str, c: str, a: list, e: dict):
            async def _caller(**kwargs) -> str:
                try:
                    client = MCPStdioClient(
                        name=s_id,
                        command=c,
                        args=a,
                        env=e,
                        cwd=str(ROOT_DIR)
                    )
                    res = client.call_tool(t_name, kwargs, timeout=30.0)
                    return json.dumps(res, ensure_ascii=False) if isinstance(res, (dict, list)) else str(res)
                except MCPClientError as err:
                    return f"❌ MCP 服务 [{s_id}] 执行工具 '{t_name}' 失败: {err}"
                except Exception as err:
                    return f"❌ MCP 调用异常: {err}"
            return _caller

        caller_fn = _make_caller(server_id, tool_name, cmd, args, env)
        _TOOL_REGISTRY[tool_name] = {
            "func": caller_fn,
            "description": f"[MCP:{server_id}] {description}",
            "module": f"mcp_{server_id}",
            "is_async": True,
            "params": ["**kwargs"]
        }
        self._mounted_tools[tool_name] = server_id

    def test_mcp_connection(self, server_cfg: dict) -> Tuple[bool, str, float]:
        """
        真实测试 MCP 服务的连通性 (启动子进程并发送 initialize 握手)
        返回: (is_success, detail_message, latency_ms)
        """
        cmd = server_cfg.get("command", "")
        args = server_cfg.get("args", [])
        env = server_cfg.get("env", {})
        srv_name = server_cfg.get("name") or server_cfg.get("id") or "test_mcp"

        if not cmd:
            return False, "❌ 命令不能为空", 0.0

        t0 = time.time()
        client = None
        try:
            client = MCPStdioClient(
                name=srv_name,
                command=cmd,
                args=args,
                env=env,
                cwd=str(ROOT_DIR)
            )
            client.start(timeout=10.0)
            latency = (time.time() - t0) * 1000.0
            return True, f"✅ 握手成功！服务进程运行正常，响应耗时 {latency:.1f}ms", latency
        except Exception as e:
            latency = (time.time() - t0) * 1000.0
            return False, f"❌ 连接失败: {e}", latency
        finally:
            if client:
                try:
                    client.close()
                except Exception:
                    pass

    def add_or_update_server(self, server_id: str, server_info: dict, enable: bool = True):
        """新增或更新 MCP 服务并持久化"""
        data = self.load_mcp_config()
        if "mcpServers" not in data:
            data["mcpServers"] = {}
        data["mcpServers"][server_id] = server_info
        self.save_mcp_config(data)

        if APP_CONFIG_PATH.exists():
            try:
                with open(APP_CONFIG_PATH, "r", encoding="utf-8") as f:
                    app_cfg = json.load(f)
                conn = set(app_cfg.get("connected_connectors", []))
                if enable:
                    conn.add(server_id)
                else:
                    conn.discard(server_id)
                app_cfg["connected_connectors"] = list(conn)
                with open(APP_CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(app_cfg, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        tools = server_info.get("tools", [])
        for t in tools:
            t_name = t.get("name")
            if t_name:
                self._register_dynamic_mcp_tool(
                    server_id,
                    server_info,
                    t_name,
                    t.get("description", f"MCP [{server_id}] 工具")
                )

    def delete_server(self, server_id: str):
        """删除 MCP 服务配置并解挂工具"""
        data = self.load_mcp_config()
        if "mcpServers" in data and server_id in data["mcpServers"]:
            del data["mcpServers"][server_id]
            self.save_mcp_config(data)

        to_del = [t_n for t_n, s_id in self._mounted_tools.items() if s_id == server_id]
        for t_n in to_del:
            _TOOL_REGISTRY.pop(t_n, None)
            self._mounted_tools.pop(t_n, None)
