# -*- coding: utf-8 -*-
"""
人体健康参数与体脂代谢指标计算器插件 (Health Calculator Plugin)
依据《中国成人超重和肥胖预防控制指南》及世界卫生组织 (WHO) 标准，
支持一键计算：BMI(体重指数)、BSA(体表面积)、WHtR(腰高比)、CI(圆锥指数)、CMI(心血管代谢指数)、
CVAI(中国内脏脂肪指数)、LAP(脂质蓄积指数)、BFR(体脂率)、RFM(相对脂肪质量指数)并输出专业参考建议。
"""
import math
from typing import Optional
from core.plugin_manager import register_tool


@register_tool(description="一键计算人体全面健康参数与体脂代谢指标（BMI、体脂率、内脏脂肪、腰高比、心血管风险评估等）。参数：gender(性别'男'或'女')，age(年龄，如30)，height_cm(身高cm，如175)，weight_kg(体重kg，如70)，waist_cm(腰围cm，可选，如85)，triglycerides(甘油三酯mg/dL，可选，默认150)，hdl(HDL胆固醇mg/dL，可选，默认45)")
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

    # 1. BMI (依据《中国成人超重和肥胖预防控制指南》标准: <18.5偏瘦, 18.5~23.9正常, 24~27.9超重, >=28肥胖)
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
    whtr_status = "正常 ✅" if whtr < 0.5 else "中心性肥胖/腹部脂肪堆积风险 ⚠️"

    # 4. CI 圆锥指数
    ci = round(waist_cm / (0.109 * math.sqrt(w_kg / h_m)), 2)

    # 5. CMI 心血管代谢指数
    tg_hdl_ratio = triglycerides / (hdl + 1e-5)
    cmi = round(whtr * tg_hdl_ratio, 2)

    # 6. BFR 体脂率 (成人公式)
    sex_factor = 1 if is_male else 0
    bfr = round(1.20 * bmi + 0.23 * age - 10.8 * sex_factor - 5.4, 2)
    bfr_ideal = "10% ~ 20%" if is_male else "18% ~ 28%"
    if is_male:
        bfr_status = "偏低 ⚠️" if bfr < 10 else ("标准理想 ✅" if bfr <= 20 else ("偏高 ⚠️" if bfr <= 25 else "严重超标 🚨"))
    else:
        bfr_status = "偏低 ⚠️" if bfr < 18 else ("标准理想 ✅" if bfr <= 28 else ("偏高 ⚠️" if bfr <= 33 else "严重超标 🚨"))

    # 7. RFM 相对脂肪质量指数
    rfm = round(64 - (20 * height_cm / waist_cm) + (12 if not is_male else 0), 2)

    # 8. LAP 脂质蓄积指数
    base_waist = 65 if is_male else 58
    lap = round(max(0, waist_cm - base_waist) * (triglycerides / 88.57), 2)

    # 9. 动态健康建议生成
    advice_items = []
    if bmi < 18.5:
        advice_items.append("• **体重偏轻**：当前 BMI 低于标准下限，建议适当增加优质蛋白质（蛋类、奶制品、瘦肉）摄入，并结合力量抗阻训练增肌，增强机体抵抗力。")
    elif bmi >= 28.0 or bfr >= (25 if is_male else 33):
        advice_items.append("• **减重与心血管防护**：BMI 与体脂指标显示存在明显肥胖风险，建议采取低碳高纤维饮食，减少精制糖和高脂食物，每周进行至少 180 分钟中等强度有氧运动（快走、游泳或骑行）。")
    elif bmi >= 24.0 or bfr >= (21 if is_male else 29):
        advice_items.append("• **超重边缘调控**：当前处于超重或轻度体脂偏高状态，控制晚间碳水摄入，避免久坐，增加日常步数与轻量运动即可有效恢复标准区间。")
    else:
        advice_items.append("• **体脂与形体良好**：当前体重与体脂均在理想标准区间内，请继续保持均衡膳食与规律运动习惯！")

    if whtr >= 0.5 or lap > 30:
        advice_items.append("• **腹部与内脏脂肪关注**：腰高比或脂质蓄积指数偏高，提示内脏脂肪有所积累，需警惕脂肪肝与胰岛素抵抗风险，建议减少加工食品与高糖饮料摄入。")

    if tg_hdl_ratio > 3.0:
        advice_items.append("• **血脂比例提示**：甘油三酯与高密度脂蛋白比值偏高，建议多摄入深海鱼油、坚果等富含 Omega-3 的健康脂肪，并定期监测体检。")

    advice_text = "\n".join(advice_items)
    is_default_lipids = (triglycerides == 150.0 and hdl == 45.0)
    lipids_note = " *(血脂参数未指定，采用成年人常规参考基准值 150/45)*" if is_default_lipids else ""

    return f"""🩺 **【人体综合健康参数与代谢指标评估报告】**
👤 **受检人基础档案**：性别: `{gender}` | 年龄: `{int(age)} 岁` | 身高: `{height_cm} cm` | 体重: `{weight_kg} kg` | 腰围: `{waist_cm} cm`
----------------------------------------
📊 **核心指标测算结果**：
1. **BMI (体重指数)**：`{bmi}` ➔ **{bmi_status}** (《中国成人肥胖防治标准》参考区间: 18.5 ~ 23.9)
2. **BSA (人体表面积)**：`{bsa} m²` (临床给药与代谢面积基础)
3. **WHtR (腰高比)**：`{whtr}` ➔ **{whtr_status}** (健康正常阈值: < 0.5)
4. **BFR (体脂率)**：`{bfr}%` ➔ **{bfr_status}** (同性别理想区间: {bfr_ideal})
5. **RFM (相对脂肪质量指数)**：`{rfm}%`
6. **CI (圆锥体型指数)**：`{ci}` (反映躯干脂肪聚集度)
7. **CMI (心血管代谢指数)**：`{cmi}`{lipids_note}
8. **LAP (脂质蓄积指数)**：`{lap}` (内脏脂肪与代谢综合征风险参考)

💡 **个性化综合健康与干预建议**：
{advice_text}

⚠️ *免责声明：本评估报告及建议仅供日常健康监测与生活方式改善参考，不能作为临床医学诊断依据。如有身体不适，请前往正规医疗机构就诊。*"""
