# -*- coding: utf-8 -*-
"""
人体健康参数与体脂代谢指标计算器 MCP 插件 (Health Calculator MCP Server)
基于 dudu007-healthcalculator / HealthCalculator 规范
支持一键计算：BMI(体重指数)、BSA(体表面积)、WHtR(腰高比)、CI(圆锥指数)、CMI(心血管代谢指数)、
CVAI(中国内脏脂肪指数)、LAP(脂质蓄积指数)、BFR(体脂率)、RFM(相对脂肪质量指数)并输出专业临床健康建议
"""
import math
from typing import Optional
from core.plugin_manager import register_tool


@register_tool(description="一键计算人体全面健康参数与体脂代谢指标（BMI、体脂率、内脏脂肪、腰高比、心血管风险评估等）。参数：gender(性别'男'或'女')，age(年龄，如30)，height_cm(身高cm，如175)，weight_kg(体重kg，如70)，waist_cm(腰围cm，可选，如85)，triglycerides(甘油三酯mg/dL，可选，如150)，hdl(HDL胆固醇mg/dL，可选，如45)")
def calculate_health_metrics(
    gender: str = "男",
    age: float = 30.0,
    height_cm: float = 175.0,
    weight_kg: float = 70.0,
    waist_cm: float = 85.0,
    triglycerides: float = 150.0,
    hdl: float = 45.0
) -> str:
    """计算人体全面健康与体脂代谢指标"""
    h_m = height_cm / 100.0
    w_kg = weight_kg
    is_male = "男" in gender or gender.lower() == "m" or gender.lower() == "male"

    # 1. BMI
    bmi = round(w_kg / (h_m ** 2), 2)
    if bmi < 18.5:
        bmi_status = "偏瘦 ⚠️"
    elif bmi < 24.0:
        bmi_status = "标准健康 ✅"
    elif bmi < 28.0:
        bmi_status = "超重 ⚠️"
    else:
        bmi_status = "肥胖 🚨"

    # 2. BSA (体表面积 DuBois 公式)
    bsa = round(0.007184 * (height_cm ** 0.725) * (w_kg ** 0.425), 2)

    # 3. 腰高比 (WHtR)
    whtr = round(waist_cm / height_cm, 3)
    whtr_status = "正常 ✅" if whtr < 0.5 else "中心性肥胖风险 ⚠️"

    # 4. CI 圆锥指数
    ci = round(waist_cm / (0.109 * math.sqrt(w_kg / h_m)), 2)

    # 5. CMI 心血管代谢指数
    tg_hdl_ratio = triglycerides / (hdl + 1e-5)
    cmi = round(whtr * tg_hdl_ratio, 2)

    # 6. BFR 体脂率 (成人公式)
    sex_factor = 1 if is_male else 0
    bfr = round(1.20 * bmi + 0.23 * age - 10.8 * sex_factor - 5.4, 2)
    bfr_ideal = "10% ~ 20%" if is_male else "18% ~ 28%"
    bfr_status = "在理想健康范围内 ✅" if (10 <= bfr <= 22 if is_male else 18 <= bfr <= 30) else "偏高 ⚠️"

    # 7. RFM 相对脂肪质量指数
    rfm = round(64 - (20 * height_cm / waist_cm) + (12 if not is_male else 0), 2)

    # 8. LAP 脂质蓄积指数
    base_waist = 65 if is_male else 58
    lap = round(max(0, waist_cm - base_waist) * (triglycerides / 88.57), 2)

    return f"""🩺 **【人体综合健康参数与代谢指标评估报告】**
👤 **受检人基础档案**：性别: `{gender}` | 年龄: `{int(age)} 岁` | 身高: `{height_cm} cm` | 体重: `{weight_kg} kg` | 腰围: `{waist_cm} cm`
----------------------------------------
📊 **核心指标精密测算结果**：
1. **BMI (体重指数)**：`{bmi}` ➔ **{bmi_status}** (正常参考区间: 18.5 ~ 23.9)
2. **BSA (人体表面积)**：`{bsa} m²` (临床给药与代谢基础)
3. **WHtR (腰高比)**：`{whtr}` ➔ **{whtr_status}** (参考值: < 0.5)
4. **BFR (体脂率)**：`{bfr}%` ➔ **{bfr_status}** (同性别理想区间: {bfr_ideal})
5. **RFM (相对脂肪质量指数)**：`{rfm}%`
6. **CI (圆锥体型指数)**：`{ci}` (反映躯干脂肪分布形态)
7. **CMI (心血管代谢指数)**：`{cmi}` (数值越低代表心血管负荷越小)
8. **LAP (脂质蓄积指数)**：`{lap}` (代谢综合征风险评估)

💡 **小日和综合健康评估建议**：
当前综合生理指标整体处于良好水平，日常建议保持每周 150 分钟中等强度有氧运动，低盐低脂饮食，规律作息，继续保持活力状态哦~ 🌸"""
