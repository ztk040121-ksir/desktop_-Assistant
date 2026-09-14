# -*- coding: utf-8 -*-
"""
Local High-Availability SQLite MCP Server (纯本地零依赖高可用 MCP 服务器)
基于标准库 sqlite3、json、sys 实现标准 MCP-over-stdio 协议 (JSON-RPC 2.0)。
支持 100% 离线、毫秒级启动与握手，为系统提供稳健的数据库管理与查询能力。
"""
import sys
import os
import json
import sqlite3
from pathlib import Path

# 确保 UTF-8 I/O
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = WORKSPACE_ROOT / "memory.db"


def get_connection(db_path_str: str = "") -> sqlite3.Connection:
    if not db_path_str:
        target = DEFAULT_DB_PATH
    else:
        p = Path(db_path_str)
        if not p.is_absolute():
            target = WORKSPACE_ROOT / p
        else:
            target = p
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    return conn


def handle_sqlite_query(query: str, db_path: str = "") -> str:
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute(query)
        if query.strip().upper().startswith("SELECT") or "RETURNING" in query.upper() or query.strip().upper().startswith("PRAGMA"):
            rows = cur.fetchall()
            results = [dict(r) for r in rows]
            conn.close()
            return json.dumps({"status": "success", "count": len(results), "rows": results}, ensure_ascii=False, indent=2)
        else:
            conn.commit()
            affected = cur.rowcount
            conn.close()
            return json.dumps({"status": "success", "affected_rows": affected, "message": "SQL 语句执行成功"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


def handle_sqlite_schema(db_path: str = "") -> str:
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cur.fetchall()
        schema_info = {}
        for t in tables:
            t_name = t["name"]
            t_sql = t["sql"]
            cur.execute(f"PRAGMA table_info('{t_name}');")
            cols = cur.fetchall()
            schema_info[t_name] = {
                "create_sql": t_sql,
                "columns": [{"cid": c["cid"], "name": c["name"], "type": c["type"], "notnull": c["notnull"], "pk": c["pk"]} for c in cols]
            }
        conn.close()
        return json.dumps({"status": "success", "tables": schema_info}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


def send_response(resp: dict):
    line = json.dumps(resp, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def main():
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            req = json.loads(line)
            if not isinstance(req, dict):
                continue
        except Exception:
            continue

        method = req.get("method", "")
        req_id = req.get("id")
        params = req.get("params") or {}

        # 1. 握手协议 initialize
        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "local-sqlite-mcp",
                        "version": "1.0.0"
                    }
                }
            }
            send_response(resp)

        # 2. 握手通知 notifications/initialized
        elif method == "notifications/initialized":
            pass

        # 3. 工具列表 tools/list
        elif method == "tools/list":
            tools = [
                {
                    "name": "sqlite_query",
                    "description": "执行 SQLite SQL 查询语句（支持 SELECT、INSERT、UPDATE、CREATE 等）并返回 JSON 结果",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "要执行的 SQL 查询语句"},
                            "db_path": {"type": "string", "description": "数据库文件路径（可选，默认为工作区 memory.db）"}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "sqlite_schema",
                    "description": "获取 SQLite 数据库所有表结构、字段类型与建表 SQL 元信息",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "db_path": {"type": "string", "description": "数据库文件路径（可选，默认为工作区 memory.db）"}
                        }
                    }
                }
            ]
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": tools}
            }
            send_response(resp)

        # 4. 工具调用 tools/call
        elif method == "tools/call":
            tool_name = params.get("name", "")
            args = params.get("arguments") or {}
            if tool_name == "sqlite_query":
                res_str = handle_sqlite_query(args.get("query", ""), args.get("db_path", ""))
            elif tool_name == "sqlite_schema":
                res_str = handle_sqlite_schema(args.get("db_path", ""))
            else:
                res_str = json.dumps({"status": "error", "error": f"未知工具: {tool_name}"}, ensure_ascii=False)

            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": res_str}
                    ]
                }
            }
            send_response(resp)

        # 5. ping
        elif method == "ping":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}
            send_response(resp)

        else:
            if req_id is not None:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }
                send_response(resp)


if __name__ == "__main__":
    main()
