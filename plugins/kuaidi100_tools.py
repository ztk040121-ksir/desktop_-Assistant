# -*- coding: utf-8 -*-
"""
快递100 综合物流查询与时效预估 MCP 插件 (kuaidi100-mcp Server)
基于快递100 官方 MCP 服务，实现真实物流轨迹追踪、时效预估与运费估算。
"""
import re
import json
from datetime import datetime
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


@register_tool(description="查询快递包裹物流实时轨迹与派送进度。参数：tracking_number(快递单号)，company(可选快递公司名称，如'顺丰'、'中通'、'圆通'等)，phone(可选收寄件人手机后4位，顺丰/极兔等部分单号核验用)")
def query_kuaidi_tracking(tracking_number: str, company: str = "", phone: str = "") -> str:
    """通过快递100 官方 MCP 服务的 query_trace 工具查询真实物流轨迹"""
    clean_num = tracking_number.strip().replace(" ", "")
    if not clean_num:
        return "⚠️ 请提供要查询的快递单号。"

    c_name = company.strip()
    official_query_url = f"https://www.kuaidi100.com/chaxun?com=&nu={clean_num}"

    try:
        client = get_mcp_client("kuaidi100")
        args = {"kuaidi_num": clean_num}
        if phone.strip():
            args["phone"] = phone.strip()
            
        raw_res = client.call_tool("query_trace", args, timeout=20.0)
        trace_text = _extract_mcp_text(raw_res)

        return f"""📦 **【快递100 官方实时物流轨迹】**
🔖 **运单号码**：`{clean_num}` {f'| 🚚 **承运商**：`{c_name}`' if c_name else ''}
----------------------------------------
{trace_text}

🔗 **快递100 官方核验**：[点击进入官网核对轨迹]({official_query_url})"""

    except MCPClientError as me:
        return f"""📦 **【快递物流单号识别与查询】**
🔖 **运单号码**：`{clean_num}`
----------------------------------------
⚠️ **快递100-MCP 服务暂不可用**：{me}

🔗 **建议前往快递100 官网即时查询**：
👉 [点击直接打开快递100 查询页面]({official_query_url})
💡 **配置提示**：如需在桌面端直连查询，请在系统环境变量设置 `KUAIDI100_API_KEY`。"""

    except Exception as e:
        return f"""📦 **【快递查询异常】**
⚠️ 查询单号 `{clean_num}` 失败：{e}
🔗 [点击直达快递100 查询页面]({official_query_url})"""


@register_tool(description="预估快递寄件运费与送达时效。参数：from_addr(寄件地址/城市)，to_addr(收件地址/城市)，weight_kg(包裹重量kg，默认1kg)，company(快递公司名称，如'顺丰'、'中通'、'圆通'、'韵达'、'申通'、'京东'、'德邦'、'邮政'、'EMS'、'极兔')，exp_type(业务/服务类型，如'标准快递'、'特快'、'标快')")
def estimate_kuaidi_price_time(from_addr: str, to_addr: str, weight_kg: float = 1.0, company: str = "顺丰", exp_type: str = "标准快递") -> str:
    """通过快递100 官方 MCP 预估运费与送达时效"""
    w = max(0.5, float(weight_kg) if weight_kg else 1.0)
    c_input = company.strip()

    # 官方支持的标准承运商编码映射表
    com_map = {
        "顺丰": "shunfeng", "顺丰速运": "shunfeng", "shunfeng": "shunfeng", "sf": "shunfeng",
        "顺丰快运": "shunfengkuaiyun",
        "中通": "zhongtong", "中通快递": "zhongtong", "zhongtong": "zhongtong", "zt": "zhongtong",
        "圆通": "yuantong", "圆通速递": "yuantong", "yuantong": "yuantong", "yt": "yuantong",
        "韵达": "yunda", "韵达速递": "yunda", "yunda": "yunda",
        "申通": "shentong", "申通快递": "shentong", "shentong": "shentong",
        "极兔": "jtexpress", "极兔速递": "jtexpress", "jtexpress": "jtexpress", "jt": "jtexpress",
        "邮政": "youzhengguonei", "邮政国内": "youzhengguonei", "中国邮政": "youzhengguonei", "youzhengguonei": "youzhengguonei",
        "邮政国际": "youzhengguoji", "youzhengguoji": "youzhengguoji",
        "ems": "ems", "EMS": "ems", "ems特快": "ems",
        "ems国际": "emsguoji", "emsguoji": "emsguoji",
        "京东": "jd", "京东快递": "jd", "jd": "jd",
        "德邦": "debangkuaidi", "德邦快递": "debangkuaidi", "debangkuaidi": "debangkuaidi",
        "跨越": "kuayue", "跨越速运": "kuayue", "kuayue": "kuayue",
        "宅急送": "zhaijisong", "zhaijisong": "zhaijisong",
        "芝麻开门": "zhimakaimen", "zhimakaimen": "zhimakaimen",
        "联邦快递": "lianbangkuaidi", "lianbangkuaidi": "lianbangkuaidi",
        "天地华宇": "tiandihuayu", "tiandihuayu": "tiandihuayu",
        "安能物流": "annengwuliu", "annengwuliu": "annengwuliu",
        "金光速递": "jinguangsudikuaijian",
        "佳运美": "jiayunmeiwuliu"
    }
    
    kuaidi_com = com_map.get(c_input)
    if not kuaidi_com:
        # 如果直接输入了合法的字母代码
        if c_input.lower() in com_map.values():
            kuaidi_com = c_input.lower()
        else:
            supported_names = "顺丰、中通、圆通、韵达、申通、极兔、京东、德邦、邮政、EMS、跨越、宅急送、安能等"
            return f"⚠️ 暂不支持的快递公司名称「{c_input}」。官方支持的快递公司包括：{supported_names}。"

    # 动态匹配或默认产品类型
    actual_exp = exp_type.strip() or ("特快" if kuaidi_com == "shunfeng" else "标准快递")

    try:
        client = get_mcp_client("kuaidi100")
        
        # 官方 schema 键名：kuaidi_com, from_loc, to_loc, exp_type
        time_res = client.call_tool(
            "estimate_time",
            {
                "kuaidi_com": kuaidi_com,
                "from_loc": from_addr,
                "to_loc": to_addr,
                "exp_type": actual_exp
            },
            timeout=15.0
        )
        
        # 官方 schema 键名：kuaidi_com, send_addr, rec_addr, weight
        price_res = client.call_tool(
            "estimate_price",
            {
                "kuaidi_com": kuaidi_com,
                "send_addr": from_addr,
                "rec_addr": to_addr,
                "weight": str(w)
            },
            timeout=15.0
        )
        
        t_text = _extract_mcp_text(time_res)
        p_text = _extract_mcp_text(price_res)

        return f"""💰 **【快递100 寄件时效与资费预估】**
📍 **路线**：`{from_addr}` ➔ `{to_addr}` | 🚚 **承运商**：`{c_input}` ({kuaidi_com}) | ⚖️ **计费重量**: {w} kg | 🏷️ **服务类型**: {actual_exp}
----------------------------------------
⏱️ **送达时效预估**：
{t_text}

💵 **运费估算**：
{p_text}

*(注：以上数据来自快递100 官方 MCP 实时计算接口，实际费用以网点现场称重揽收为准)*"""

    except MCPClientError as me:
        return f"""💰 **【快递100 寄件时效与资费预估】**
📍 **路线**：`{from_addr}` ➔ `{to_addr}` | 🚚 **承运商**：`{c_input}` (重量: {w} kg)
----------------------------------------
⚠️ **快递100-MCP 服务暂不可用**：{me}
💡 **配置提示**：请在系统环境变量设置 `KUAIDI100_API_KEY` 后重试，或直接访问 [快递100 官网运费查询](https://www.kuaidi100.com) 进行核算。"""

    except Exception as e:
        return f"""💰 **【快递100 寄件预估异常】**
⚠️ 预估 `{from_addr}` 至 `{to_addr}` 运费/时效失败：{e}
🔗 [点击进入快递100 官网运费与时效查询](https://www.kuaidi100.com)"""
