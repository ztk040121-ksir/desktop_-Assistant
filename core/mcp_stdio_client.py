# -*- coding: utf-8 -*-
"""
NovaDesk v4.0 - MCP-over-stdio 标准客户端
纯标准库实现：基于 subprocess 与 JSON-RPC 2.0 NDJSON 行协议，
支持 initialize 握手、notifications/initialized、tools/call 调用与进程池按需管理。
"""
import os
import sys
import json
import time
import queue
import threading
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent


class MCPClientError(Exception):
    """MCP 客户端调用异常基类"""
    pass


class MCPStdioClient:
    """单个 MCP 服务器的 stdio 进程客户端"""

    def __init__(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None):
        self.name = name
        self.command = command
        self.args = args
        self.custom_env = env or {}
        self.cwd = cwd or str(ROOT_DIR)
        self.process: Optional[subprocess.Popen] = None
        self._req_id = 0
        self._lock = threading.RLock()
        self._responses: Dict[int, Any] = {}
        self._response_events: Dict[int, threading.Event] = {}
        self._reader_thread: Optional[threading.Thread] = None
        self._is_initialized = False
        self._is_closing = False

    def is_alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self, timeout: float = 15.0):
        with self._lock:
            if self.is_alive() and self._is_initialized:
                return

            self._close_process_unlocked()

            # 准备环境变量
            full_env = os.environ.copy()
            full_env.update(self.custom_env)
            # 确保 Windows 下 PATH 正常
            if sys.platform == "win32" and "PATH" not in self.custom_env:
                full_env["PATH"] = os.environ.get("PATH", "")

            cmd = self.command
            if cmd in ("python", "python3") and sys.executable:
                cmd = sys.executable
            cmd_list = [cmd] + self.args
            try:
                # Windows 下使用 shell=True 保证 npx / node / python 正确执行
                use_shell = (sys.platform == "win32" and (self.command in ("npx", "npm", "uvx", "uv")))
                self.process = subprocess.Popen(
                    cmd_list if not use_shell else " ".join(f'"{c}"' if " " in c else c for c in cmd_list),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    cwd=self.cwd,
                    env=full_env,
                    shell=use_shell
                )
            except FileNotFoundError as e:
                raise MCPClientError(f"无法启动 MCP 服务 [{self.name}]：找不到可执行文件 `{self.command}`。请确认已安装相应运行环境并加入系统 PATH。({e})")
            except Exception as e:
                raise MCPClientError(f"启动 MCP 服务 [{self.name}] 失败：{e}")

            self._is_closing = False
            self._reader_thread = threading.Thread(target=self._read_loop, name=f"MCP-Reader-{self.name}", daemon=True)
            self._reader_thread.start()

        # 执行 initialize 握手（必须在释放 _lock 之后执行，避免 _send_rpc 再次获取锁产生死锁）
        self._initialize_handshake(timeout=timeout)

    def _read_loop(self):
        """后台逐行读取 stdout 并派发 JSON-RPC 响应"""
        if not self.process or not self.process.stdout:
            return

        for line in self.process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                if isinstance(msg, dict):
                    msg_id = msg.get("id")
                    if msg_id is not None and msg_id in self._response_events:
                        self._responses[msg_id] = msg
                        self._response_events[msg_id].set()
            except Exception:
                # 忽略非 JSON 行（部分 stderr/stdout 混合输出）
                pass

        # 进程退出清理
        if not self._is_closing:
            for evt in self._response_events.values():
                evt.set()

    def _send_rpc(self, method: str, params: Optional[Dict[str, Any]] = None, is_notification: bool = False, timeout: float = 20.0) -> Optional[Dict[str, Any]]:
        if not self.is_alive():
            raise MCPClientError(f"MCP 服务 [{self.name}] 进程未运行或已异常终止。")

        with self._lock:
            self._req_id += 1
            req_id = self._req_id

            req: Dict[str, Any] = {
                "jsonrpc": "2.0",
                "method": method
            }
            if not is_notification:
                req["id"] = req_id
            if params is not None:
                req["params"] = params

            if not is_notification:
                evt = threading.Event()
                self._response_events[req_id] = evt

            try:
                line = json.dumps(req, ensure_ascii=False) + "\n"
                self.process.stdin.write(line)
                self.process.stdin.flush()
            except Exception as e:
                if not is_notification:
                    self._response_events.pop(req_id, None)
                raise MCPClientError(f"向 MCP 服务 [{self.name}] 发送数据失败：{e}")

        if is_notification:
            return None

        # 等待响应
        ok = evt.wait(timeout=timeout)
        with self._lock:
            self._response_events.pop(req_id, None)
            resp = self._responses.pop(req_id, None)

        if not ok or resp is None:
            raise MCPClientError(f"MCP 服务 [{self.name}] 响应超时（{timeout}s），未能返回结果。")

        if "error" in resp:
            err = resp["error"]
            err_msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            raise MCPClientError(f"MCP 服务 [{self.name}] 返回错误：{err_msg}")

        return resp.get("result", {})

    def _initialize_handshake(self, timeout: float = 15.0):
        """MCP 握手流程"""
        init_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {}
            },
            "clientInfo": {
                "name": "NovaDesk-Agent",
                "version": "3.0.0"
            }
        }
        res = self._send_rpc("initialize", init_params, timeout=timeout)
        self._send_rpc("notifications/initialized", is_notification=True)
        self._is_initialized = True

    def call_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: float = 30.0) -> Any:
        """调用 MCP 注册的工具"""
        if not self.is_alive() or not self._is_initialized:
            self.start(timeout=15.0)

        params = {
            "name": tool_name,
            "arguments": arguments
        }
        result = self._send_rpc("tools/call", params, timeout=timeout)
        return result

    def close(self):
        with self._lock:
            self._close_process_unlocked()

    def _close_process_unlocked(self):
        self._is_closing = True
        self._is_initialized = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=1.5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None


# 全局 MCP 客户端管理器（按需单例管理）
_MCP_REGISTRY: Dict[str, MCPStdioClient] = {}
_REGISTRY_LOCK = threading.Lock()


def get_mcp_client(server_name: str) -> MCPStdioClient:
    """根据名称从 config.json 获取并初始化 MCP 客户端"""
    with _REGISTRY_LOCK:
        if server_name in _MCP_REGISTRY:
            client = _MCP_REGISTRY[server_name]
            if client.is_alive():
                return client

        # 从 config.json 加载服务器定义
        cfg_path = ROOT_DIR / "config.json"
        config = {}
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                pass

        mcp_servers = config.get("mcp_servers", {})
        srv_cfg = mcp_servers.get(server_name)

        if not srv_cfg:
            # 默认配置兜底
            if server_name == "train12306":
                srv_cfg = {
                    "command": "npx",
                    "args": ["-y", "12306-mcp"],
                    "env": {}
                }
            elif server_name == "kuaidi100":
                srv_cfg = {
                    "command": "npx",
                    "args": ["-y", "@kuaidi100-mcp/kuaidi100-mcp-server"],
                    "env": {},
                    "env_ref": "KUAIDI100_API_KEY"
                }
            else:
                raise MCPClientError(f"未找到 MCP 服务 [{server_name}] 的配置项。")

        cmd = srv_cfg.get("command", "npx")
        args = srv_cfg.get("args", [])
        env = srv_cfg.get("env", {})

        # 处理环境变量与授权 key (严格仅从环境变量读取，不留明文)
        env_ref = srv_cfg.get("env_ref")
        if env_ref:
            key_val = os.environ.get(env_ref, "").strip()
            if key_val:
                env[env_ref] = key_val

        client = MCPStdioClient(
            name=server_name,
            command=cmd,
            args=args,
            env=env,
            cwd=str(ROOT_DIR)
        )
        _MCP_REGISTRY[server_name] = client
        return client
