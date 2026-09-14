# -*- coding: utf-8 -*-
"""
12306 铁路客票与高铁动车出行查询 MCP 插件 (12306-mcp Server)
基于 ModelScope 12306-mcp 实现真实车票余票查询、经停站点与到发时刻表检索。
"""
import re
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from core.plugin_manager import register_tool
from core.mcp_stdio_client import get_mcp_client, MCPClientError


def _extract_mcp_text(res: Any) -> str:
    """提取 MCP tools/call 返回的文本内容"""
    if isinstance(res, str):
        return res
    if isinstance(res, dict):
        content = res.get("content", [])
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
                elif isinstance(item, str):
                    texts.append(item)
            if texts:
                return "\n".join(texts)
        if "text" in res:
            return str(res["text"])
    return json.dumps(res, ensure_ascii=False, indent=2)


@register_tool(description="查询 12306 火车票与高铁动车车次与实时余票。参数：from_station(出发站/城市，如'广州'或'北京')，to_station(到达站/城市，如'深圳'或'上海')，date(出发日期，格式'YYYY-MM-DD'，如未提供默认明天)")
def search_12306_tickets(from_station: str, to_station: str, date: str = "") -> str:
    """通过 12306-mcp 查询真实火车票余票与车次信息"""
    clean_from = from_station.replace("站", "").strip() or "广州"
    clean_to = to_station.replace("站", "").strip() or "深圳"

    if not date:
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        client = get_mcp_client("train12306")
        
        # 1. 查询城市对应站码 (如果 MCP 支持站码转换)
        from_code = clean_from
        to_code = clean_to
        try:
            code_res = client.call_tool("get-station-code-of-citys", {"citys": f"{clean_from}|{clean_to}"}, timeout=8.0)
            code_text = _extract_mcp_text(code_res)
            # 解析站码 JSON
            try:
                code_map = json.loads(code_text)
                if isinstance(code_map, dict):
                    from_code = code_map.get(clean_from, clean_from)
                    to_code = code_map.get(clean_to, clean_to)
            except Exception:
                pass
        except Exception:
            pass

        # 2. 查询真实车次与余票
        raw_res = client.call_tool(
            "get-tickets",
            {
                "date": date,
                "fromStation": from_code,
                "toStation": to_code,
                "format": "text"
            },
            timeout=25.0
        )
        result_text = _extract_mcp_text(raw_res)

        return f"""🚄 **【12306 官方实时车票查询结果】**
📅 **出行日期**：`{date}` | 📍 **区间**：`{clean_from}` ➔ `{clean_to}`
----------------------------------------
{result_text}

🔗 **12306 官方购票核验**：[点击直达 12306 官方车票查询](https://kyfw.12306.cn/otn/leftTicket/init)"""

    except MCPClientError as me:
        return f"""🚄 **【12306 火车票查询服务状态】**
📅 **出行日期**：`{date}` | 📍 **区间**：`{clean_from}` ➔ `{clean_to}`
----------------------------------------
⚠️ **12306-MCP 暂不可用**：{me}

🔗 **建议直接前往官方核验与购票**：
👉 [点击直接进入 12306 官方车票查询页面](https://kyfw.12306.cn/otn/leftTicket/init)
💡 **贴士**：全国铁路车票提前 15 天开售，若直达无票建议第一时间在官方 App 提交候补。"""

    except Exception as e:
        return f"""🚄 **【12306 火车票查询服务异常】**
⚠️ 查询 `{clean_from}` 到 `{clean_to}` ({date}) 失败：{e}
🔗 [点击直达 12306 官方车票查询页面](https://kyfw.12306.cn/otn/leftTicket/init)"""


@register_tool(description="查询指定火车/高铁车次的沿途经停站点与到发时刻表。参数：train_no(车次编号，如'G6501'、'D7101'、'G102')，date(出行日期，格式'YYYY-MM-DD'，可选)")
def query_train_stopovers(train_no: str, date: str = "") -> str:
    """通过 12306-mcp 查询指定车次真实经停时刻表"""
    clean_no = train_no.upper().strip()
    if not clean_no:
        return "⚠️ 请提供要查询的车次编号（例如 G6501）。"

    if not date:
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        client = get_mcp_client("train12306")
        raw_res = client.call_tool(
            "get-train-route-stations",
            {
                "trainCode": clean_no,
                "departDate": date
            },
            timeout=20.0
        )
        result_text = _extract_mcp_text(raw_res)

        return f"""🚆 **【12306 车次经停站点与时刻表】· `{clean_no}`**
📅 **运行日期**：`{date}`
----------------------------------------
{result_text}"""

    except MCPClientError as me:
        return f"""🚆 **【12306 车次查询】· `{clean_no}`**
⚠️ **12306-MCP 暂不可用**：{me}
💡 建议在 12306 App 首页「车站大屏 / 正晚点查询」中输入车次 `{clean_no}` 查询即时经停站点。"""

    except Exception as e:
        return f"⚠️ 查询车次 `{clean_no}` 经停站点失败：{e}"
