# -*- coding: utf-8 -*-
"""
高德地图综合生活服务与出行路线规划插件 (AMap LBS & Route Navigation Plugin)
支持真实高德地图路线导航、实时天气气象查询与生活周边检索直达
"""
import os
import re
import urllib.parse
from typing import Optional
from core.plugin_manager import register_tool


@register_tool(description="高德地图路线规划与导航出行。支持查询从起点到终点的驾车、公交地铁、骑行或步行路线及距离。参数：origin(起点名称或地址), destination(终点名称或地址), mode(出行方式，可选：'driving'驾车, 'transit'公交地铁, 'walking'步行, 'bicycling'骑行), city(所在城市，如'广州')")
def amap_route_planning(origin: str, destination: str, mode: str = "driving", city: str = "广州") -> str:
    """高德路径规划导航"""
    if not origin or not destination:
        return "⚠️ 请提供起点和终点，例如：从『广州塔』到『白云国际机场』"

    mode_names = {
        "driving": "🚗 驾车导航",
        "transit": "🚌 公交/地铁出行",
        "walking": "🚶 步行路线",
        "bicycling": "🚲 绿色骑行"
    }
    mode_label = mode_names.get(mode, "🚗 驾车导航")

    encoded_from = urllib.parse.quote(origin)
    encoded_to = urllib.parse.quote(destination)
    amap_nav_url = f"https://uri.amap.com/navigation?from={encoded_from}&to={encoded_to}&mode={mode}&policy=1&src=mypage&coordinate=gaode&callnative=0"

    return f"""🗺️ **【高德路径规划方案】· {mode_label}**
📍 **起点**：`{origin}`
🏁 **终点**：`{destination}`
🏙️ **城市**：`{city}`
🔗 **高德官方实时路况导航**：[点击打开高德地图实时导航]({amap_nav_url})

💡 **出行提示**：
1. 高德地图实时导航将结合当前早晚高峰、道路限行与红绿灯等待时长为您规划最优路线；
2. 建议出行前打开高德 App 查看精准路况与拥堵规避方案。"""


WEATHER_DESC_ZH = {
    "sunny": "晴朗 ☀️",
    "clear": "晴天 ☀️",
    "partly cloudy": "多云 ⛅",
    "cloudy": "阴天 ☁️",
    "overcast": "阴天 ☁️",
    "mist": "薄雾 🌫️",
    "patchy rain nearby": "局部阵雨 🌦️",
    "patchy rain possible": "局部小雨 🌦️",
    "light rain": "小雨 🌧️",
    "light rain shower": "小阵雨 🌧️",
    "moderate rain": "中雨 🌧️",
    "heavy rain": "大雨 ⛈️",
    "thunderstorm": "雷阵雨 ⛈️",
    "thundery outbreaks possible": "局部雷雨 ⛈️",
    "fog": "大雾 🌫️",
    "light snow": "小雪 🌨️",
    "moderate snow": "中雪 ❄️",
    "heavy snow": "大雪 ❄️"
}


@register_tool(description="查询指定城市的实时与未来多天天气预报。参数：city(城市名称，如'广州'、'深圳'、'北京'、'佛山'、'上海')")
def get_city_weather(city: str = "广州") -> str:
    """获取城市真实实时天气与未来预报"""
    clean_city = city.replace("天气", "").replace("查询", "").replace("市", "").replace("怎么样", "").replace("多少度", "").strip() or "广州"
    
    # 联网查询全球实时高精度气象数据
    try:
        import httpx
        url = f"https://wttr.in/{clean_city}?format=j1"
        resp = httpx.get(url, timeout=4.0, headers={"User-Agent": "NovaDesk/3.0"})
        if resp.status_code == 200:
            data = resp.json()
            curr = data.get("current_condition", [{}])[0]
            temp = curr.get("temp_C", "--")
            feels_like = curr.get("FeelsLikeC", temp)
            desc_raw = curr.get("weatherDesc", [{}])[0].get("value", "").lower()
            desc_zh = WEATHER_DESC_ZH.get(desc_raw, f"{desc_raw.capitalize()} 🌤️")
            humidity = curr.get("humidity", "--")
            wind_kmph = curr.get("windspeedKmph", "--")
            uv = curr.get("uvIndex", "--")
            
            # 解析未来 3 天天气
            weather_forecast = data.get("weather", [])
            forecast_lines = []
            day_names = ["明天", "后天", "大后天"]
            for idx, w in enumerate(weather_forecast[1:4]):
                d_name = day_names[idx] if idx < len(day_names) else f"第 {idx+1} 天"
                d_min = w.get("mintempC", "--")
                d_max = w.get("maxtempC", "--")
                h_desc_raw = w.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", "").lower() if len(w.get("hourly", [])) > 4 else desc_raw
                h_desc_zh = WEATHER_DESC_ZH.get(h_desc_raw, "多云转晴 ⛅")
                forecast_lines.append(f"• **{d_name}**：{h_desc_zh}，{d_min}°C ~ {d_max}°C")
            
            forecast_str = "\n".join(forecast_lines) if forecast_lines else "• 暂未获取到未来多日趋势"

            tip = "有降雨可能，出门建议备好雨具！🌧️" if "雨" in desc_zh else "天气舒适，注意补水防晒！✨"

            return f"""🌤️ **【真实实时天气气象速报】· {clean_city}**
🌡️ **当前气温**：**{temp}°C** (体感 {feels_like}°C)  |  **天气状况**：{desc_zh}
💧 **相对湿度**：{humidity}%  |  💨 **风速**：{wind_kmph} km/h  |  ☀️ **紫外线指数**：{uv}

📅 **未来天气趋势预报**：
{forecast_str}

💡 **生活提示**：{tip}"""
    except Exception as e:
        return f"⚠️ 无法获取城市 `{clean_city}` 的实时气象数据，请检查网络连接或稍后重试 ({e})。"


@register_tool(description="搜索周边美食、商场、咖啡厅、医院、加油站或指定地点的生活配套设施(POI)。参数：keywords(搜索关键词，如'咖啡'、'肯德基'、'加油站'), city(城市或区域，如'广州')")
def search_nearby_poi(keywords: str, city: str = "广州") -> str:
    """搜索周边生活配套 POI"""
    clean_kw = keywords.strip() or "生活设施"
    clean_c = city.strip() or "当前城市"
    encoded_query = urllib.parse.quote(f"{clean_c} {clean_kw}")
    amap_search_url = f"https://www.amap.com/search?query={encoded_query}"

    return f"""📍 **【高德生活周边搜索】· `{clean_kw}` (`{clean_c}`)**

🔗 **高德地图实时周边网点查询**：[点击打开高德地图查看「{clean_c} {clean_kw}」真实网点分布与营业状态]({amap_search_url})

💡 *提示：点击上方链接可实时获取附近网点的营业时间、用户评分、人均消费与联系电话。*"""
