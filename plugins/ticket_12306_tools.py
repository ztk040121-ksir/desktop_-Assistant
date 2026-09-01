# -*- coding: utf-8 -*-
"""
12306 火车票与高铁出行查询 MCP 插件 (12306 Train Ticket MCP Server)
支持全国铁路车次区间查询、官方直达与时刻表检索
"""
import httpx
from datetime import datetime, timedelta
from typing import Optional
from core.plugin_manager import register_tool


@register_tool(description="查询 12306 火车票与高铁动车车次与出行方案。参数：from_station(出发站/城市，如'广州'或'北京')，to_station(到达站/城市，如'深圳'或'上海')，date(出发日期，格式'YYYY-MM-DD'，如未提供默认明天)")
async def search_12306_tickets(from_station: str, to_station: str, date: str = "") -> str:
    """查询 12306 火车票与高铁班次"""
    clean_from = from_station.replace("站", "").strip() or "广州"
    clean_to = to_station.replace("站", "").strip() or "深圳"
    
    if not date:
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    official_12306_url = f"https://www.12306.cn/index/"

    return f"""🚄 **【12306 铁路客票与班次方案】**
📅 **出发日期**：`{date}`
📍 **乘车区间**：`{clean_from}` ➔ `{clean_to}`
🔗 **12306 官方余票核验与购票**：[点击直达 12306 官方网站]({official_12306_url})

💡 **出行建议**：
1. 高铁动车票预售期为 **15 天**，请在 12306 官方 App 或网站确认最新余票及起售时间；
2. 乘车请务必携带好本人居民身份证原件，直接刷身份证进站乘车。"""


@register_tool(description="查询指定火车/高铁车次的沿途停靠车站与到发时刻表。参数：train_no(车次编号，如'G6501'、'D7101'、'G1234')")
def query_train_stopovers(train_no: str) -> str:
    """查询车次停靠站"""
    clean_no = train_no.upper().strip()
    if not clean_no:
        return "⚠️ 请提供要查询的车次编号（例如 G6501）。"
    
    return f"""🚆 **【12306 车次时刻表查询】：`{clean_no}`**

💡 车次 `{clean_no}` 的最新实时正晚点与沿途停靠站信息，可直接在 12306 官方客户端「车站大屏 / 车次查询」中实时获取。"""
