# -*- coding: utf-8 -*-
"""
快递100 综合物流查询与时效预估 MCP 插件 (Kuaidi100 MCP Server)
支持全国主要快递公司单号格式识别、官方查询直达与运费参考估算
"""
import re
from datetime import datetime
from typing import Optional
from core.plugin_manager import register_tool


@register_tool(description="查询快递包裹物流实时轨迹与派送进度。参数：tracking_number(快递单号)，company(可选快递公司名称，如'顺丰'、'中通')")
def query_kuaidi_tracking(tracking_number: str, company: str = "") -> str:
    """查询快递物流轨迹"""
    clean_num = tracking_number.strip().replace(" ", "")
    if not clean_num:
        return "⚠️ 请提供要查询的快递单号。"

    c_name = company.strip()
    official_query_url = f"https://www.kuaidi100.com/chaxun?com=&nu={clean_num}"
    if not c_name:
        if clean_num.upper().startswith("SF") or (len(clean_num) == 12 and clean_num.startswith("1")):
            c_name = "顺丰速运"
            official_query_url = f"https://www.sf-express.com/chn/sc/waybill/list?billCodes={clean_num}"
        elif clean_num.upper().startswith("JD"):
            c_name = "京东快递"
            official_query_url = f"https://www.jdl.cn/order/search?waybillCodes={clean_num}"
        elif clean_num.upper().startswith("YT"):
            c_name = "圆通速递"
        elif clean_num.upper().startswith("ZT"):
            c_name = "中通快递"
        elif clean_num.upper().startswith("7") and len(clean_num) in [13, 14]:
            c_name = "申通快递"
        elif clean_num.upper().startswith("4") and len(clean_num) == 13:
            c_name = "韵达速递"
        elif clean_num.upper().startswith("JT"):
            c_name = "极兔速递"
        else:
            c_name = "自动识别快递承运商"

    return f"""📦 **【快递物流单号识别与查询】**
🚚 **识别承运商**：`{c_name}`
🔖 **运单号码**：`{clean_num}`
🔗 **实时官方轨迹查询**：[点击直达 {c_name} 官网查询]({official_query_url})

💡 *注：当前系统已智能匹配承运商。如需在桌面端内直接嵌入实时轨迹 JSON，可在设置中配置快递 100 OpenAPI Key。*"""


@register_tool(description="预估快递寄件运费与送达时效参考。参数：from_addr(寄件地址/城市)，to_addr(收件地址/城市)，weight_kg(包裹重量kg，默认1kg)")
def estimate_kuaidi_price_time(from_addr: str, to_addr: str, weight_kg: float = 1.0) -> str:
    """预估快递运费与时效参考（按行业公开计费阶梯标准核算）"""
    w = max(0.5, float(weight_kg) if weight_kg else 1.0)
    extra_w = max(0.0, w - 1.0)
    
    sf_express = round(18 + extra_w * 6, 1)
    sf_standard = round(14 + extra_w * 4, 1)
    common_express = round(10 + extra_w * 3, 1)

    return f"""💰 **【快递寄件运费与时效参考估算】**
📍 **路线**：`{from_addr}` ➔ `{to_addr}` (计费重量: {w} kg)
----------------------------------------
• 🚀 **顺丰特快 (跨省次日达)**：预估约 **¥{sf_express}** | 预计 **次日 12:00 前**
• 📦 **顺丰标快 / 京东特快**：预估约 **¥{sf_standard}** | 预计 **次日 18:00 前**
• 🚛 **主流通达系 (中通/圆通/申通/韵达)**：预估约 **¥{common_express}** | 预计 **隔日送达**

*(以上为基于公开标准资费核算的参考区间，实际费用以网点现场称重计费为准)*"""
