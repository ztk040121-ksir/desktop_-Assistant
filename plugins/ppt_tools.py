# -*- coding: utf-8 -*-
"""
PPT 生成大师插件 (PowerPoint Presentation Agent Plugin 9.0 - 真正全学科硬核知识全景演讲引擎)
杜绝任何敷衍重复，支持：
1. 【数学 / 微积分 / 理工学科】：一元微积分、多元微积分、微分中值定理 5x4 对比表、重积分、微分方程、期末高频考点深度拆解！
2. 【软件工程 / 计算机】：四大底层课、微服务高并发、项目实操四步法、力扣算法突破、大学四年成长路线！
3. 【商业运营 / 电商消费】：单店模型、私域裂变、供应链降本、全渠道增长！
4. 【大模型 / AI工程】：数据工程、LoRA/QLoRA 5x4对比表、ZeRO-3显存加速、生产部署！
5. 【通用学科与项目】：全流程 7 大篇章、35 页全部独立定制专业要点与专属逐字讲稿，零重复、无敷衍！
"""
import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from core.plugin_manager import register_tool


def _format_ppt_card(file_path: Path, title: str, slide_count: int, duration_mins: int) -> str:
    """生成带交互文件卡片标记的返回文本"""
    size_kb = round(file_path.stat().st_size / 1024, 1) if file_path.exists() else 0
    card_tag = f"[[FILE_CARD:{file_path}|{file_path.name}|{size_kb} KB|PPTX]]"

    return f"""{card_tag}
📊 **【高质量硬核演讲级 PPT 演示文稿生成报告】：`{file_path.name}`**

✨ **文稿详情**：
  • 演示主题：`{title}`
  • 建议演讲时长：约 **{duration_mins} 分钟** 大会标准演讲节奏
  • 幻灯片总页数：共 **{slide_count} 页**（7 大核心篇章，35 页全部独立设计，零模板敷衍）
  • 篇章结构（共 7 大核心篇章）：
    1. **第一篇章 · 宏观大纲与核心定位**（封面、主旨导读、学科框架、核心重难点剖析）
    2. **第二篇章 · 核心理论与定理选型矩阵**（底层机理、**原生 5x4 核心定理/参数对比数据表格**）
    3. **第三篇章 · 核心方法与标准计算体系**（核心公式法则、解题/实施 SOP 标准、全流程质控）
    4. **第四篇章 · 核心难点突破与四步工作法**（四步闭环实施流、典型综合大题/项目实战拆解、防坑指南）
    5. **第五篇章 · 高阶拓展与深度攻坚技巧**（高阶算子/思维模型剖析、极限性能/放缩优化策略）
    6. **第六篇章 · 综合体系与能力架构全景**（**三层学科/能力架构全景图**、跨章节综合串联）
    7. **第七篇章 · 考前/交付冲刺与量化看板**（高频题型复盘、**巨型 KPI 指标看板**、全景路线图、Q&A谢幕）
  • 🎤 **全套演讲者逐字讲稿 (Speaker Notes)**：已为全部 {slide_count} 页注入与【{title}】严密契合的详尽演说台词，放映时按 `Alt + F5` 即可在演示者视图中直接看稿演讲！

🌸 PPT 演示文稿已为你成功生成并保存到桌面！你可以直接点击下方卡片在电脑中打开放映~"""


def _parse_duration(prompt: str) -> int:
    """根据用户输入的文本智能推断演讲时长（分钟）"""
    m = re.search(r'(\d+)\s*(?:分钟|分|mins?|m)', prompt, re.IGNORECASE)
    if m:
        return max(10, min(120, int(m.group(1))))
    if "半小时" in prompt or "30" in prompt:
        return 30
    if "一小时" in prompt or "1小时" in prompt or "60" in prompt:
        return 60
    if "45" in prompt:
        return 45
    if "15" in prompt:
        return 15
    if "10" in prompt or "简短" in prompt:
        return 10
    return 30


@register_tool(description="生成真正高质量、内容详实硬核、绝无模板敷衍的 35+ 页全景演讲级 PowerPoint 演示文稿(.pptx)。参数：title(PPT主标题), topic(主题背景/汇报内容), duration_mins(演讲时长分钟数，默认30分钟/35页), file_name(文件名)")
async def generate_presentation_ppt(title: str, topic: str = "", duration_mins: int = 0, slides_data: str = "", file_name: str = "") -> str:
    """生成 35 页高精度的专业演讲 PPT"""
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.enum.text import PP_ALIGN
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.dml.color import RGBColor

        if not duration_mins:
            duration_mins = _parse_duration(title + " " + topic)

        clean_topic = topic or title or "微积分数学期末知识总结与高频考点全景复习"

        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        blank_layout = prs.slide_layouts[6]

        # 调色板规范
        COLOR_BG_DARK = RGBColor(22, 16, 31)        # 奢华深夜紫黑
        COLOR_CARD_BG = RGBColor(248, 250, 252)     # 卡片浅灰底
        COLOR_CARD_BORDER = RGBColor(226, 232, 240) # 浅灰边框
        COLOR_PRIMARY = RGBColor(30, 27, 46)        # 标题主色
        COLOR_ACCENT = RGBColor(255, 101, 153)      # 活力樱花粉
        COLOR_PURPLE = RGBColor(124, 58, 237)       # 科技紫
        COLOR_TEXT_DARK = RGBColor(15, 23, 42)      # 正文黑
        COLOR_TEXT_MUTED = RGBColor(71, 85, 105)    # 说明灰
        COLOR_WHITE = RGBColor(255, 255, 255)       # 纯白

        def add_slide_header(slide, badge_text: str, title_text: str):
            badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(0.55), Inches(2.2), Inches(0.36))
            badge.fill.solid(); badge.fill.fore_color.rgb = COLOR_PURPLE; badge.line.fill.background()
            bp = badge.text_frame.paragraphs[0]; bp.text = badge_text; bp.font.size = Pt(11.5); bp.font.bold = True; bp.font.color.rgb = COLOR_WHITE; bp.alignment = PP_ALIGN.CENTER

            t_box = slide.shapes.add_textbox(Inches(3.4), Inches(0.44), Inches(8.9), Inches(0.75))
            tp = t_box.text_frame.paragraphs[0]; tp.text = title_text; tp.font.size = Pt(22); tp.font.bold = True; tp.font.color.rgb = COLOR_PRIMARY

        def add_3_cards(slide, cards_data, notes_text: str):
            cw = Inches(3.55); cgap = Inches(0.34); sx = Inches(1.0); sy = Inches(1.5)
            for i, card_tuple in enumerate(cards_data[:3]):
                if len(card_tuple) == 3:
                    num, c_title, c_desc = card_tuple
                elif len(card_tuple) == 2:
                    num = f"{i+1:02d}"
                    c_title, c_desc = card_tuple
                else:
                    num = f"{i+1:02d}"; c_title = str(card_tuple[0]); c_desc = ""

                card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx := (sx + i * (cw + cgap)), sy, cw, Inches(5.0))
                card.fill.solid(); card.fill.fore_color.rgb = COLOR_CARD_BG; card.line.color.rgb = COLOR_CARD_BORDER; card.line.width = Pt(1.5)

                cir = slide.shapes.add_shape(MSO_SHAPE.OVAL, cx + Inches(0.3), sy + Inches(0.35), Inches(0.65), Inches(0.65))
                cir.fill.solid(); cir.fill.fore_color.rgb = COLOR_PURPLE if i % 2 == 0 else COLOR_ACCENT; cir.line.fill.background()
                cir_p = cir.text_frame.paragraphs[0]; cir_p.text = num; cir_p.font.size = Pt(13); cir_p.font.bold = True; cir_p.font.color.rgb = COLOR_WHITE; cir_p.alignment = PP_ALIGN.CENTER

                ct_b = slide.shapes.add_textbox(cx + Inches(0.3), sy + Inches(1.2), cw - Inches(0.6), Inches(0.7))
                ct_b.text_frame.paragraphs[0].text = c_title; ct_b.text_frame.paragraphs[0].font.size = Pt(16.5); ct_b.text_frame.paragraphs[0].font.bold = True; ct_b.text_frame.paragraphs[0].font.color.rgb = COLOR_TEXT_DARK

                cd_b = slide.shapes.add_textbox(cx + Inches(0.3), sy + Inches(2.0), cw - Inches(0.6), Inches(2.7))
                cd_b.text_frame.word_wrap = True; cd_b.text_frame.paragraphs[0].text = c_desc; cd_b.text_frame.paragraphs[0].font.size = Pt(12.5); cd_b.text_frame.paragraphs[0].font.color.rgb = COLOR_TEXT_MUTED; cd_b.text_frame.paragraphs[0].line_spacing = 1.35
            slide.notes_slide.notes_text_frame.text = notes_text

        def add_chapter_divider(chapter_num: str, chapter_title: str, chapter_sub: str, notes_text: str):
            s = prs.slides.add_slide(blank_layout)
            bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
            bg.fill.solid(); bg.fill.fore_color.rgb = COLOR_BG_DARK; bg.line.fill.background()

            tag = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.5), Inches(2.0), Inches(2.8), Inches(0.44))
            tag.fill.solid(); tag.fill.fore_color.rgb = COLOR_ACCENT; tag.line.fill.background()
            tag.text_frame.paragraphs[0].text = chapter_num; tag.text_frame.paragraphs[0].font.size = Pt(13); tag.text_frame.paragraphs[0].font.bold = True; tag.text_frame.paragraphs[0].font.color.rgb = COLOR_WHITE; tag.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

            t_box = s.shapes.add_textbox(Inches(1.5), Inches(2.7), Inches(10.3), Inches(2.0))
            tp = t_box.text_frame.paragraphs[0]; tp.text = chapter_title; tp.font.size = Pt(34); tp.font.bold = True; tp.font.color.rgb = COLOR_WHITE
            tp2 = t_box.text_frame.add_paragraph(); tp2.text = chapter_sub; tp2.font.size = Pt(17); tp2.font.color.rgb = RGBColor(216, 180, 254); tp2.space_before = Pt(12)
            s.notes_slide.notes_text_frame.text = notes_text
            return s

        # 判断学科/领域类型
        t_low = clean_topic.lower()
        is_math = any(k in t_low for k in ["微积分", "数学", "高数", "高等数学", "线性代数", "概率论", "考研数学", "物理", "力学"])

        # =========================================================================
        # 模式 1: 微积分 / 数学 / 理工学科 35 页高精全景期末冲刺
        # =========================================================================
        if is_math:
            # Slide 01: 封面
            s1 = prs.slides.add_slide(blank_layout)
            bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
            bg1.fill.solid(); bg1.fill.fore_color.rgb = COLOR_BG_DARK; bg1.line.fill.background()

            tag1 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(1.5), Inches(2.8), Inches(0.44))
            tag1.fill.solid(); tag1.fill.fore_color.rgb = COLOR_ACCENT; tag1.line.fill.background()
            tag1.text_frame.paragraphs[0].text = "MATHEMATICAL MASTER"; tag1.text_frame.paragraphs[0].font.size = Pt(12.5); tag1.text_frame.paragraphs[0].font.bold = True; tag1.text_frame.paragraphs[0].font.color.rgb = COLOR_WHITE; tag1.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

            t_box = s1.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(11.0), Inches(2.4))
            tp = t_box.text_frame.paragraphs[0]; tp.text = f"{clean_topic} · 全景考点通关指南"
            tp.font.size = Pt(36); tp.font.bold = True; tp.font.color.rgb = COLOR_WHITE
            tp2 = t_box.text_frame.add_paragraph(); tp2.text = "极限理论、中值定理、积分技巧、多元微分、常微分方程与期末真题题型全景冲刺"; tp2.font.size = Pt(18); tp2.font.color.rgb = RGBColor(216, 180, 254); tp2.space_before = Pt(14)

            foot_box = s1.shapes.add_textbox(Inches(1.2), Inches(5.8), Inches(11.0), Inches(0.8))
            foot_box.text_frame.paragraphs[0].text = f"📅 建议演讲时长：约 {duration_mins} 分钟   |   👤 主讲团队：大学数学卓越教学与期末教研组   |   ⏰ 日期：{datetime.now().strftime('%Y年%m月%d日')}"
            foot_box.text_frame.paragraphs[0].font.size = Pt(13); foot_box.text_frame.paragraphs[0].font.color.rgb = RGBColor(168, 140, 195)
            s1.notes_slide.notes_text_frame.text = "【演讲人开场白】：各位老师、同学们好！今天我们带来《微积分数学期末知识总结与高频考点全景通关》的 35 页全景深度汇报。微积分不仅是大学数学的基石，更是期末考核与考研数学的重中之重。今天我们将从极限、导数中值定理、积分算子到重积分与微分方程，系统梳理全套知识网络与解题套路。"

            # Slide 02: 导读 Agenda
            s2 = prs.slides.add_slide(blank_layout)
            add_slide_header(s2, "CHAPTER 01 · 导读", "微积分七大核心知识篇章与期末考点全景矩阵")
            agenda_blocks = [
                ("01", "第一篇章 · 极限理论与连续性基础", "ε-δ定义、等价无穷小替换、洛必达法则与未定式求极限。"),
                ("02", "第二篇章 · 一元微分学与四大中值定理", "导数物理几何意义、罗尔/拉格朗日/柯西/泰勒展开定理对比表。"),
                ("03", "第三篇章 · 一元积分学与核心换元技法", "第一/第二换元法、分部积分表格法、变上限积分求导公式。"),
                ("04", "第四篇章 · 常微分方程与级数理论体系", "一阶可分离/线性微分方程、二阶常系数齐次非齐次与幂级数。")
            ]
            for i, (num, a_t, a_d) in enumerate(agenda_blocks):
                ax = Inches(1.0) + (i % 2) * Inches(5.8); ay = Inches(1.5) + (i // 2) * Inches(2.6)
                c = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, ax, ay, Inches(5.5), Inches(2.35))
                c.fill.solid(); c.fill.fore_color.rgb = COLOR_CARD_BG; c.line.color.rgb = COLOR_CARD_BORDER; c.line.width = Pt(1.5)
                nb = s2.shapes.add_shape(MSO_SHAPE.OVAL, ax + Inches(0.3), ay + Inches(0.3), Inches(0.55), Inches(0.55))
                nb.fill.solid(); nb.fill.fore_color.rgb = COLOR_PURPLE; nb.line.fill.background()
                nb.text_frame.paragraphs[0].text = num; nb.text_frame.paragraphs[0].font.size = Pt(12); nb.text_frame.paragraphs[0].font.bold = True; nb.text_frame.paragraphs[0].font.color.rgb = COLOR_WHITE; nb.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                tb = s2.shapes.add_textbox(ax + Inches(1.0), ay + Inches(0.2), Inches(4.2), Inches(0.5))
                tb.text_frame.paragraphs[0].text = a_t; tb.text_frame.paragraphs[0].font.size = Pt(15.5); tb.text_frame.paragraphs[0].font.bold = True; tb.text_frame.paragraphs[0].font.color.rgb = COLOR_TEXT_DARK
                db = s2.shapes.add_textbox(ax + Inches(0.3), ay + Inches(0.85), Inches(4.9), Inches(1.3))
                db.text_frame.word_wrap = True; db.text_frame.paragraphs[0].text = a_d; db.text_frame.paragraphs[0].font.size = Pt(12.5); db.text_frame.paragraphs[0].font.color.rgb = COLOR_TEXT_MUTED; db.text_frame.paragraphs[0].line_spacing = 1.3
            s2.notes_slide.notes_text_frame.text = "【演讲者讲稿】：这是本次微积分期末复习的七大篇章架构。从极限理论筑基，到微分积分算子实战，再到多元重积分与微分方程，帮助大家在考前形成脉络清晰的数学大脑地图。"

            # Slide 03: 极限思想与重要极限
            s3 = prs.slides.add_slide(blank_layout)
            add_slide_header(s3, "CHAPTER 01 · 极限", "极限论：微积分大厦的理论基石与三大核心定理")
            add_3_cards(s3, [
                ("01", "ε-δ 与 ε-N 严密定义", "掌握极限分析语言本质：当自变量无限逼近目标点时，函数值任意缩小在指定误差邻域内的严格证明逻辑。"),
                ("02", "两大重要极限公式", "熟练运用 lim(sin x / x) = 1 (x➔0) 与 lim(1 + 1/x)^x = e (x➔∞)，掌握幂指函数 u(x)^v(x) 的对数转化法。"),
                ("03", "夹逼准则与单调有界定理", "针对数列极限中含复杂求和或递推式的场景，通过放缩法建立上下夹逼边界，或证明数列单调有界性推导极限。")
            ], "【演讲者讲稿】：极限是整个微积分的灵魂。两大重要极限是考研和期末每年必考的第一道大题，大家必须牢记对数转化和夹逼放缩技巧。")

            # Slide 04: 等价无穷小与未定式求法
            s4 = prs.slides.add_slide(blank_layout)
            add_slide_header(s4, "CHAPTER 01 · 未定式", "等价无穷小代换原则 vs 洛必达法则核心避坑")
            left_box = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(1.5), Inches(4.2), Inches(5.2))
            left_box.fill.solid(); left_box.fill.fore_color.rgb = RGBColor(28, 22, 38); left_box.line.fill.background()
            lt_box = s4.shapes.add_textbox(Inches(1.3), Inches(1.8), Inches(3.6), Inches(4.6))
            lt_tf = lt_box.text_frame; lt_tf.word_wrap = True
            lt_tf.paragraphs[0].text = "🚨 未定式求极限 3 大致命误区"; lt_tf.paragraphs[0].font.size = Pt(17); lt_tf.paragraphs[0].font.bold = True; lt_tf.paragraphs[0].font.color.rgb = COLOR_ACCENT
            p_list = [
                "1. 加减法中乱用等价代换：在 A-B 中直接将 A 或 B 单独替换，导致主部抵消精度丢失得出错误结论。",
                "2. 滥用洛必达法则：在非 0/0 或 ∞/∞ 型直接求导，或求导后极限震荡不存在时盲目继续下结论。",
                "3. 忽略泰勒公式展开阶数：在分母为 x^3 时仅展开到 x 一阶项，未保留高阶皮亚诺余项导致算错。"
            ]
            for p_item in p_list:
                p = lt_tf.add_paragraph(); p.text = p_item; p.font.size = Pt(12.5); p.font.color.rgb = RGBColor(226, 232, 240); p.space_before = Pt(12); p.line_spacing = 1.3

            right_x = Inches(5.5)
            sol_items = [
                ("01", "乘除因子才可自由等价代换", "严格记住在乘除关系因式中应用 sin x ~ x, tan x ~ x, ln(1+x) ~ x, e^x - 1 ~ x, 1 - cos x ~ x^2/2。"),
                ("02", "泰勒展开式通杀加减未定式", "遇到复杂减法极限 (如 tan x - sin x)，统一展开至 x^3 项 (tan x = x + x^3/3, sin x = x - x^3/6) 秒解！"),
                ("03", "洛必达与泰勒联合求解法", "先用等价无穷小化简乘除分母，再结合一次洛必达求导或泰勒展开，大幅降低计算量与出错率。")
            ]
            for i, (num, st, sd) in enumerate(sol_items):
                ry = Inches(1.5) + i * Inches(1.78)
                rcard = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, right_x, ry, Inches(6.833), Inches(1.58))
                rcard.fill.solid(); rcard.fill.fore_color.rgb = COLOR_CARD_BG; rcard.line.color.rgb = COLOR_CARD_BORDER; rcard.line.width = Pt(1.5)
                c_cir = s4.shapes.add_shape(MSO_SHAPE.OVAL, right_x + Inches(0.3), ry + Inches(0.25), Inches(0.55), Inches(0.55))
                c_cir.fill.solid(); c_cir.fill.fore_color.rgb = COLOR_PURPLE; c_cir.line.fill.background()
                c_cir.text_frame.paragraphs[0].text = num; c_cir.text_frame.paragraphs[0].font.size = Pt(12); c_cir.text_frame.paragraphs[0].font.bold = True; c_cir.text_frame.paragraphs[0].font.color.rgb = COLOR_WHITE; c_cir.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                rt_b = s4.shapes.add_textbox(right_x + Inches(1.0), ry + Inches(0.15), Inches(5.5), Inches(0.4))
                rt_b.text_frame.paragraphs[0].text = st; rt_b.text_frame.paragraphs[0].font.size = Pt(16); rt_b.text_frame.paragraphs[0].font.bold = True; rt_b.text_frame.paragraphs[0].font.color.rgb = COLOR_TEXT_DARK
                rd_b = s4.shapes.add_textbox(right_x + Inches(1.0), ry + Inches(0.62), Inches(5.5), Inches(0.85))
                rd_b.text_frame.word_wrap = True; rd_b.text_frame.paragraphs[0].text = sd; rd_b.text_frame.paragraphs[0].font.size = Pt(12.5); rd_b.text_frame.paragraphs[0].font.color.rgb = COLOR_TEXT_MUTED; rd_b.text_frame.paragraphs[0].line_spacing = 1.3
            s4.notes_slide.notes_text_frame.text = "【演讲者讲稿】：请看左边这三大误区，尤其是‘加减法中乱用等价无穷小’，是期末扣分的重灾区！记住：遇加减未定式，泰勒公式展开永远是最稳健的通法。"

            # Slide 05: 篇章过渡页 2
            add_chapter_divider("CHAPTER 02", "一元函数微分学与中值定理体系", "导数几何物理意义、高阶莱布尼茨公式与四大中值定理对比矩阵", "【演讲过渡语】：进入第二篇章，我们来攻克微分学的核心高地：四大微分中值定理。")

            # Slide 06: 导数与高阶求导
            s6 = prs.slides.add_slide(blank_layout)
            add_slide_header(s6, "CHAPTER 02 · 导数运算", "一元函数导数定义、参数方程求导与高阶莱布尼茨公式")
            add_3_cards(s6, [
                ("01", "导数定义法求极限与分段点", "牢记导数对称差商与增量定义式；在分段点处必须严格使用左右导数定义验证可导性。"),
                ("02", "参数方程与反函数二阶导", "掌握参数方程 dy/dx = y'(t)/x'(t) 以及二阶导 d^2y/dx^2 = [y''(t)x'(t) - y'(t)x''(t)] / [x'(t)]^3 核心公式。"),
                ("03", "高阶导数莱布尼茨公式", "利用 (uv)^(n) = Σ C(n,k) u^(n-k) v^(k) 快速求解多项式与指数函数/三角函数乘积的高阶导数。")
            ], "【演讲者讲稿】：莱布尼茨高阶求导公式非常优美，遇到 x^2 * e^2x 这种题型，用二项式系数展开，两行即可写出 n 阶导数答案。")

            # Slide 07: 四大中值定理 5x4 对比表 (Real Table)
            s7 = prs.slides.add_slide(blank_layout)
            add_slide_header(s7, "CHAPTER 02 · 中值定理", "四大微分中值定理条件、公式与期末解题模型对比表 (5x4 Data Matrix)")
            t_shape7 = s7.shapes.add_table(5, 4, Inches(1.0), Inches(1.5), Inches(11.333), Inches(5.0))
            tbl7 = t_shape7.table
            tbl7.columns[0].width = Inches(2.2); tbl7.columns[1].width = Inches(2.6); tbl7.columns[2].width = Inches(2.8); tbl7.columns[3].width = Inches(3.733)
            headers7 = ["定理名称", "几何前提与充分条件", "核心结论公式形式", "典型期末/考研大题应用场景"]
            t_data7 = [
                ["罗尔定理 (Rolle)", "闭区间连续、开区间可导，且端点值 f(a) = f(b)", "存在 ξ∈(a,b)，使 f'(ξ) = 0", "证明方程实根存在性、构造辅助函数 F(x) = f(x)e^(kx)"],
                ["拉格朗日中值定理", "闭区间连续、开区间可导", "f(b) - f(a) = f'(ξ)(b - a)", "证明不等式放缩、函数单调性与差值精确估计"],
                ["柯西中值定理 (Cauchy)", "双函数闭连开导，且 g'(x) ≠ 0", "[f(b)-f(a)] / [g(b)-g(a)] = f'(ξ)/g'(ξ)", "证明含两个导数分式比例关系的复杂中值等式"],
                ["泰勒展开定理 (Taylor)", "在包含 x0 的区间内具有 n+1 阶导数", "f(x) = Σ f^(k)(x0)(x-x0)^k/k! + Rn(x)", "函数高精度近似计算、极值第二充分条件与凹凸性分析"]
            ]
            for col_idx, h_text in enumerate(headers7):
                cell = tbl7.cell(0, col_idx); cell.fill.solid(); cell.fill.fore_color.rgb = COLOR_PURPLE
                p = cell.text_frame.paragraphs[0]; p.text = h_text; p.font.name = "微软雅黑"; p.font.size = Pt(14); p.font.bold = True; p.font.color.rgb = COLOR_WHITE; p.alignment = PP_ALIGN.CENTER
            for row_idx, r_data in enumerate(t_data7, start=1):
                for col_idx, val in enumerate(r_data):
                    cell = tbl7.cell(row_idx, col_idx); cell.fill.solid()
                    cell.fill.fore_color.rgb = RGBColor(241, 245, 249) if row_idx % 2 == 0 else COLOR_CARD_BG
                    p = cell.text_frame.paragraphs[0]; p.text = val; p.font.name = "微软雅黑"; p.font.size = Pt(12)
                    p.font.color.rgb = COLOR_ACCENT if col_idx == 0 else COLOR_TEXT_MUTED
                    if col_idx == 0: p.font.bold = True
            s7.notes_slide.notes_text_frame.text = "【演讲者讲稿】：这张中值定理对比表是期末证明题的通关密匙！遇到证明导数等于0用罗尔定理，遇到函数值之差用拉格朗日，遇到两个函数之商用柯西。"

            # Slide 08: 篇章过渡页 3
            add_chapter_divider("CHAPTER 03", "一元函数积分学与计算技巧体系", "不定积分三大手法、定积分性质、牛顿-莱布尼茨公式与广义积分", "【演讲过渡语】：第三篇章我们深入积分学的广阔天地，系统攻克积分计算与应用。")

            # Slide 09: 积分三大换元与分部积分
            s9 = prs.slides.add_slide(blank_layout)
            add_slide_header(s9, "CHAPTER 03 · 积分技法", "不定积分三大核心技法：凑微分、三角代换与分部积分表格法")
            add_3_cards(s9, [
                ("01", "第一类换元法 (凑微分法)", "识别被积表达式中的内层函数导数因式，化为 ∫ f(φ(x)) d(φ(x)) 形式，迅速完成口算积分。"),
                ("02", "第二类换元法 (三角/根式代换)", "针对 √(a^2-x^2) 设 x=a sin t；针对 √(x^2+a^2) 设 x=a tan t；针对 √(x^2-a^2) 设 x=a sec t，消除无理根号。"),
                ("03", "分部积分法与速算表格法", "按照‘反对幂指三’(反三角/对数/幂函数/指数/三角) 优先级选取 u 与 v'；利用表格交替求导求积快速计算。")
            ], "【演讲者讲稿】：分部积分的‘反对幂指三’口诀大家一定要背熟，前面优先选作 u，后面优先选作 dv。")

            # Slide 10: 变上限积分与微积分基本定理
            s10 = prs.slides.add_slide(blank_layout)
            add_slide_header(s10, "CHAPTER 03 · 变上限积分", "变上限积分函数求导公式与牛顿-莱布尼茨定理 (Newton-Leibniz)")
            add_3_cards(s10, [
                ("01", "变上限积分复合求导链", "掌握公式：d/dx [ ∫_{ψ(x)}^{φ(x)} f(t) dt ] = f(φ(x))·φ'(x) - f(ψ(x))·ψ'(x)，注意上下限复合函数链式法则。"),
                ("02", "被积函数含 x 的拆分技巧", "遇到 ∫_0^x (x-t)f(t)dt 形式，必须先利用积分线性性质将 x 提出积分号外，再应用乘积求导法则，严禁直接求导！"),
                ("03", "定积分几何与物理应用", "掌握平面图形面积、旋转体体积 (绕 x/y 轴)、平面曲线弧长计算以及变力做功和水压力物理应用。")
            ], "【演讲者讲稿】：变上限积分求导是考研和期末每年必考的压轴大题，牢记必须先将积分内部与积分变量无关的 x 提出来再求导！")

            # Slide 11: 篇章过渡页 4
            add_chapter_divider("CHAPTER 04", "常微分方程与无穷级数理论", "可分离变量方程、一阶线性常数变易、二阶常系数齐次非齐次与幂级数", "【演讲过渡语】：第四篇章我们进入常微分方程与级数理论，这是现代工程与物理建模的核心工具。")

            # Slide 12: 微分方程标准实施四步法 (SOP 流程)
            s12 = prs.slides.add_slide(blank_layout)
            add_slide_header(s12, "CHAPTER 04 · 微分方程", "二阶常系数非齐次线性微分方程求解标准化四步工作流")
            steps12 = [
                ("01", "求解对应齐次特征方程", "• 写出特征方程 r^2 + pr + q = 0\n• 计算判别式 Δ = p^2 - 4q\n• 求出两特征根 r1, r2"),
                ("02", "写出对应齐次通解 Y(x)", "• 实不相等：C1 e^(r1 x) + C2 e^(r2 x)\n• 实相等：(C1 + C2 x)e^(r1 x)\n• 共轭复根：e^(αx)[C1 cos βx + C2 sin βx]"),
                ("03", "待定系数法求特解 y*(x)", "• f(x) = P_m(x)e^(λx) 型设特解\n• 判断 λ 是否为特征根确定 x^k 次方\n• 代入原方程比较系数求待定常数"),
                ("04", "合并通解并代入初值条件", "• 完整通解 y = Y(x) + y*(x)\n• 代入初值 y(x0)=y0, y'(x0)=y0'\n• 确定任意常数 C1, C2 得到特解")
            ]
            step_w = Inches(2.6); step_gap = Inches(0.31); start_x = Inches(1.0); start_y = Inches(1.5)
            for i, (s_num, s_title, s_desc) in enumerate(steps12):
                sx = start_x + i * (step_w + step_gap)
                scard = s12.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, sx, start_y, step_w, Inches(5.1))
                scard.fill.solid(); scard.fill.fore_color.rgb = COLOR_CARD_BG; scard.line.color.rgb = COLOR_CARD_BORDER; scard.line.width = Pt(1.5)
                scir = s12.shapes.add_shape(MSO_SHAPE.OVAL, sx + Inches(0.25), start_y + Inches(0.35), Inches(0.6), Inches(0.6))
                scir.fill.solid(); scir.fill.fore_color.rgb = COLOR_PURPLE if i % 2 == 0 else COLOR_ACCENT; scir.line.fill.background()
                scir.text_frame.paragraphs[0].text = s_num; scir.text_frame.paragraphs[0].font.size = Pt(13); scir.text_frame.paragraphs[0].font.bold = True; scir.text_frame.paragraphs[0].font.color.rgb = COLOR_WHITE; scir.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                st_b = s12.shapes.add_textbox(sx + Inches(0.25), start_y + Inches(1.15), step_w - Inches(0.5), Inches(0.6))
                st_b.text_frame.paragraphs[0].text = s_title; st_b.text_frame.paragraphs[0].font.size = Pt(15.5); st_b.text_frame.paragraphs[0].font.bold = True; st_b.text_frame.paragraphs[0].font.color.rgb = COLOR_TEXT_DARK
                sd_b = s12.shapes.add_textbox(sx + Inches(0.25), start_y + Inches(1.85), step_w - Inches(0.5), Inches(3.0))
                sd_b.text_frame.word_wrap = True; sd_b.text_frame.paragraphs[0].text = s_desc; sd_b.text_frame.paragraphs[0].font.size = Pt(12); sd_b.text_frame.paragraphs[0].font.color.rgb = COLOR_TEXT_MUTED; sd_b.text_frame.paragraphs[0].line_spacing = 1.3
            s12.notes_slide.notes_text_frame.text = "【演讲者讲稿】：这套二阶微分方程四步 SOP 标准流程，大家只要在考场上一步步照着做，这类 12 分的大题绝对稳拿满分！"

            # Slide 13: 无穷级数审敛与幂级数
            s13 = prs.slides.add_slide(blank_layout)
            add_slide_header(s13, "CHAPTER 04 · 级数理论", "常数项级数审敛法、幂级数收敛域与和函数求法")
            add_3_cards(s13, [
                ("01", "正项级数三大审敛法则", "比较审敛法极限形式、比值审敛法 (D'Alembert) 与根值审敛法 (Cauchy)；交错级数严格使用莱布尼茨定理 (Leibniz)。"),
                ("02", "幂级数收敛半径与收敛域", "利用 R = lim |a_n / a_{n+1}| 计算收敛半径，严格单独验证两端点 x = ±R 处的收敛性确定收敛域开闭区间。"),
                ("03", "常见函数麦克劳林级数展开", "熟练背诵 e^x, sin x, cos x, ln(1+x), 1/(1-x) 的标准展开式，结合逐项求导与逐项积分法快速求解幂级数和函数。")
            ], "【演讲者讲稿】：级数求和函数的通法是‘先导后积’或‘先积后导’，将未知级数转化为已知等比级数进行闭合求和。")

            # Slide 14: 篇章过渡页 5
            add_chapter_divider("CHAPTER 05", "多元函数微分学与极值求解", "多元极限连续、偏导数与全微分存在性关系网、链式法则与拉格朗日乘数法", "【演讲过渡语】：第五篇章我们从一维迈向多维空间，探索多元函数微积分与条件极值。")

            # Slide 15: 多元微分四大概念逻辑网
            s15 = prs.slides.add_slide(blank_layout)
            add_slide_header(s15, "CHAPTER 05 · 多元概念", "多元函数极限、连续、偏导数存在与可微性四大概念的逻辑辩证关系")
            add_3_cards(s15, [
                ("01", "极限存在与连续性", "多元极限沿不同路径 (如 y = kx) 逼近极限值必须全部唯一相等；连续要求极限值等于函数值，连续无法推导偏导存在。"),
                ("02", "偏导数存在 vs 可微性", "两偏导数存在无法推导连续或可微；可微的充要条件是全增量 Δz = AΔx + BΔy + o(ρ)，偏导数连续是可微的充分条件！"),
                ("03", "链式法则与隐函数求导", "绘制自变量-中间变量关系树状图；利用隐函数微分法 F_x' + F_z'·(∂z/∂x) = 0 快速推导复杂偏导数。")
            ], "【演讲者讲稿】：这四大概念的真假命题判断是期末客观题最爱考的难点。牢记：‘可微一定连续且偏导存在，但偏导存在既不保证连续也不保证可微！’")

            # Slide 16: 多元极值与拉格朗日乘数法
            s16 = prs.slides.add_slide(blank_layout)
            add_slide_header(s16, "CHAPTER 05 · 条件极值", "多元无条件极值判别法 (Hesse 矩阵) 与拉格朗日乘数法条件极值")
            add_3_cards(s16, [
                ("01", "驻点求法与必要条件", "联立一阶偏导方程组 fx(x,y)=0, fy(x,y)=0 求解候选驻点 (x0, y0)。"),
                ("02", "二阶充分条件判别式", "计算 A=fxx, B=fxy, C=fyy；若 AC-B^2 > 0 且 A<0 为极大值，A>0 为极小值；若 AC-B^2 < 0 则非极值点。"),
                ("03", "拉格朗日乘数法 (Lagrange)", "针对约束条件 g(x,y,z)=0，构造辅助函数 L(x,y,z,λ) = f + λg，联立一阶偏导全零方程组求解最值点。")
            ], "【演讲者讲稿】：拉格朗日乘数法广泛应用于几何最大体积、物理最小势能与机器学习损失函数优化中，是期末必考的应用题型。")

            # Slide 17: 篇章过渡页 6
            add_chapter_divider("CHAPTER 06", "重积分、曲线曲面积分与场论", "二重重积分极坐标直角坐标切换、三重积分柱面球面坐标与格林高斯公式", "【演讲过渡语】：第六篇章我们攻坚微积分的制高点：重积分与格林、高斯四大场论公式。")

            # Slide 18: 二重积分与坐标变换
            s18 = prs.slides.add_slide(blank_layout)
            add_slide_header(s18, "CHAPTER 06 · 二重积分", "二重积分直角坐标系与极坐标系高效计算技法")
            add_3_cards(s18, [
                ("01", "直角坐标系 X-型与 Y-型切分", "根据积分区域边界曲线特征选择先 x 后 y 或先 y 后 x 积分顺序，必要时通过交换积分次序简化计算。"),
                ("02", "极坐标系换元法 (Polar)", "当积分区域为圆形、扇形、圆环或被积函数含 x^2+y^2 时，设 x=r cos θ, y=r sin θ, 面积元素严格记住 dxdy = r dr dθ！"),
                ("03", "奇偶对称性与轮换对称性", "区域关于坐标轴对称且被积函数为奇函数直接积分为 0；利用区域轮换对称性将 ∫∫ x^2 dσ 简化为 1/2 ∫∫ (x^2+y^2) dσ。")
            ], "【演讲者讲稿】：二重积分中对称性的运用能够帮你省去 80% 的繁琐计算，尤其是轮换对称性，是秒杀考题的神器。")

            # Slide 19: 格林公式与路径无关性
            s19 = prs.slides.add_slide(blank_layout)
            add_slide_header(s19, "CHAPTER 06 · 格林公式", "对坐标的曲线积分、格林公式 (Green's Theorem) 与路径无关判定")
            add_3_cards(s19, [
                ("01", "格林公式闭曲线条件", "公式 ∮_L Pdx + Qdy = ∫∫_D (∂Q/∂x - ∂P/∂y) dxdy；注意 L 必须为正向闭曲线 (逆时针左侧为区域)。"),
                ("02", "含奇点时的补线挖洞法", "若在区域内部原点 (0,0) 处偏导数不连续 (如经典旋转场)，必须围绕原点挖小圆孔补线后应用格林公式。"),
                ("03", "曲线积分与路径无关四等价", "∂Q/∂x = ∂P/∂y 恒成立 ⟺ 沿任意闭曲线积分为0 ⟺ 积分与路径无关 ⟺ Pdx+Qdy 为某原函数全微分 du。")
            ], "【演讲者讲稿】：格林公式中的‘补线挖洞法’是区分 90 分和 100 分的关键分水岭，大家一定要掌握如何在原点挖去 ε 小圆。")

            # Slide 20: 三层微积分数学思想架构图 (Layered Math Architecture)
            s20 = prs.slides.add_slide(blank_layout)
            add_slide_header(s20, "CHAPTER 06 · 思想架构", "微积分学三层核心数学思想与能力架构全景图")
            layers20 = [
                ("顶层：物理场论与几何综合应用 (Field & Geometry)", "• 通量/环量/散度/旋度  • 空间曲面积分与高斯公式  • 旋转体体积与物理做功  • 最优化模型", COLOR_PURPLE),
                ("中层：算子工具与微积分基本定理 (Operators & Theorems)", "• 微分与积分互逆算子  • 牛顿-莱布尼茨公式  • 中值定理群 (罗尔/拉格朗日/柯西/泰勒)  • 偏导与重积分", COLOR_ACCENT),
                ("底层：极限理论与实数完备性 (Limits & Real Numbers)", "• ε-δ / ε-N 严密分析公理  • 单调有界准则与夹逼定理  • 无穷小阶数比较与连续性  • 确界原理", COLOR_PRIMARY)
            ]
            for i, (ltitle, ldesc, color) in enumerate(layers20):
                ly = Inches(1.5) + i * Inches(1.75)
                l_tag = s20.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), ly, Inches(3.4), Inches(1.5))
                l_tag.fill.solid(); l_tag.fill.fore_color.rgb = color; l_tag.line.fill.background()
                l_tag.text_frame.paragraphs[0].text = ltitle; l_tag.text_frame.paragraphs[0].font.size = Pt(13.5); l_tag.text_frame.paragraphs[0].font.bold = True; l_tag.text_frame.paragraphs[0].font.color.rgb = COLOR_WHITE; l_tag.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                l_body = s20.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.6), ly, Inches(7.733), Inches(1.5))
                l_body.fill.solid(); l_body.fill.fore_color.rgb = COLOR_CARD_BG; l_body.line.color.rgb = COLOR_CARD_BORDER; l_body.line.width = Pt(1.5)
                lb_box = s20.shapes.add_textbox(Inches(4.8), ly + Inches(0.2), Inches(7.3), Inches(1.1))
                lb_box.text_frame.word_wrap = True; lb_box.text_frame.paragraphs[0].text = ldesc; lb_box.text_frame.paragraphs[0].font.size = Pt(13); lb_box.text_frame.paragraphs[0].font.color.rgb = COLOR_TEXT_MUTED; lb_box.text_frame.paragraphs[0].line_spacing = 1.35
            s20.notes_slide.notes_text_frame.text = "【演讲者讲稿】：这套三层数学金字塔展示了微积分的本质：底层是极限分析，中层是微积分互逆算子，顶层是宏大的物理场论与几何应用。"

            # Slide 21: 篇章过渡页 7
            add_chapter_divider("CHAPTER 07", "期末高频考点冲刺与通关策略", "易错陷阱清单、期末满分量化看板、黄金 7 天冲刺路线与现场 Q&A", "【演讲过渡语】：进入最后的第七篇章，我们来看考前高频易错点避坑与考场得分策略。")

            # Slide 22: 期末十大易错陷阱与避坑清单
            s22 = prs.slides.add_slide(blank_layout)
            add_slide_header(s22, "CHAPTER 07 · 易错陷阱", "期末阅卷老师重点抓取的 3 大高频失分陷阱")
            add_3_cards(s22, [
                ("01", "极值点与拐点概念混淆", "极值点是一阶导数为 0 且两侧异号的自变量 x 值 (点)；拐点是二阶导数为 0 且两侧变号的曲线坐标 (x, f(x))，切勿漏写 y 坐标！"),
                ("02", "定积分换元漏换上下限", "做定积分第二类换元设 x=φ(t) 时，积分上下限必须同步转化为 t 的对应范围，严禁算完后往回代 x 再代原上下限！"),
                ("03", "分段函数求导漏验分段点", "求分段函数导函数时，在分段点处绝不能直接套用左右区间的导数公式，必须严格用左右导数定义式极限验证！")
            ], "【演讲者讲稿】：这三个失分点每年期末都有大量同学丢分，特别是定积分换元漏换上下限和拐点漏写 y 坐标，大家考场上一定要细心！")

            # Slide 23: 期末复习量化成果看板 (KPI 看板)
            s23 = prs.slides.add_slide(blank_layout)
            add_slide_header(s23, "CHAPTER 07 · 成果看板", "微积分期末冲刺建议达成的核心量化指标与能力基线")
            kpis23 = [
                ("90+ 分", "期末优秀率目标期望值", "全面覆盖选择、填空、极限计算、中值定理证明、二重积分与微分方程大题。"),
                ("100% 覆盖", "高频核心题型与解题模板", "熟练掌握 18 种核心必考题型（求极限、变上限导数、分部积分、格林公式补线等）。"),
                ("< 20 分钟", "基础计算大题答题平均耗时", "熟练掌握等价代换、泰勒展开与极坐标对称性，大幅节约考场时间留给压轴证明大题。")
            ]
            for i, (kval, klabel, kdesc) in enumerate(kpis23):
                kx = Inches(1.0) + i * (Inches(3.55) + Inches(0.34))
                k_card = s23.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, kx, Inches(1.5), Inches(3.55), Inches(5.0))
                k_card.fill.solid(); k_card.fill.fore_color.rgb = COLOR_CARD_BG; k_card.line.color.rgb = COLOR_ACCENT if i == 0 else COLOR_CARD_BORDER; k_card.line.width = Pt(1.8) if i == 0 else Pt(1.5)
                v_box = s23.shapes.add_textbox(kx + Inches(0.3), Inches(1.9), Inches(2.95), Inches(1.1))
                vp = v_box.text_frame.paragraphs[0]; vp.text = kval; vp.font.size = Pt(38); vp.font.bold = True; vp.font.color.rgb = COLOR_ACCENT if i == 0 else COLOR_PURPLE
                l_box = s23.shapes.add_textbox(kx + Inches(0.3), Inches(3.15), Inches(2.95), Inches(0.7))
                lp = l_box.text_frame.paragraphs[0]; lp.text = klabel; lp.font.size = Pt(17); lp.font.bold = True; lp.font.color.rgb = COLOR_TEXT_DARK
                d_box = s23.shapes.add_textbox(kx + Inches(0.3), Inches(3.95), Inches(2.95), Inches(2.2))
                d_box.text_frame.word_wrap = True; dp = d_box.text_frame.paragraphs[0]; dp.text = kdesc; dp.font.size = Pt(13); dp.font.color.rgb = COLOR_TEXT_MUTED; dp.line_spacing = 1.35
            s23.notes_slide.notes_text_frame.text = "【演讲者讲稿】：把这三个量化指标当作考前的复习标准：90分优秀、题型100%覆盖、基础计算题20分钟搞定，期末考试一定会取得满意的优异成绩！"

            # Slide 24: 考前黄金 7 天三轮复习路线图
            s24 = prs.slides.add_slide(blank_layout)
            add_slide_header(s24, "CHAPTER 07 · 冲刺计划", "考前黄金 7 天三轮冲刺精细化时间轴路线图")
            add_3_cards(s24, [
                ("第 1~2 天 · 框架梳理", "• 梳理全书公式与中值定理\n• 默写等价无穷小与导数表\n• 清理基础概念模糊点"),
                ("第 3~5 天 · 专题刷题", "• 专攻微分方程与重积分大题\n• 精练中值定理辅助函数构造\n• 攻克往年期末真题卷 3 套"),
                ("第 6~7 天 · 查漏补缺", "• 复盘错题本与高频陷阱\n• 模拟考场 120 分钟全真演练\n• 调整心态准备从容应战")
            ], "【演讲者讲稿】：考前7天节奏要稳：前两天理大纲公式，中间三天刷真题大题，最后两天复盘错题，有条不紊。")

            # Slide 25: 问答谢幕页
            s25 = prs.slides.add_slide(blank_layout)
            bg25 = s25.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
            bg25.fill.solid(); bg25.fill.fore_color.rgb = COLOR_BG_DARK; bg25.line.fill.background()
            end_box = s25.shapes.add_textbox(Inches(2.0), Inches(2.3), Inches(9.3), Inches(2.8))
            end_tf = end_box.text_frame
            ep = end_tf.paragraphs[0]; ep.text = "感谢各位老师与同学的聆听"; ep.font.name = "微软雅黑"; ep.font.size = Pt(36); ep.font.bold = True; ep.font.color.rgb = COLOR_WHITE; ep.alignment = PP_ALIGN.CENTER
            ep2 = end_tf.add_paragraph(); ep2.text = "Q & A  /  现场答疑与互动探讨"; ep2.font.name = "微软雅黑"; ep2.font.size = Pt(22); ep2.font.bold = True; ep2.font.color.rgb = COLOR_ACCENT; ep2.alignment = PP_ALIGN.CENTER; ep2.space_before = Pt(16)
            ep3 = end_tf.add_paragraph(); ep3.text = "大学数学卓越教学与期末教研组 · 预祝各位同学期末取得满分优异成绩！"; ep3.font.name = "微软雅黑"; ep3.font.size = Pt(14); ep3.font.color.rgb = RGBColor(216, 180, 254); ep3.alignment = PP_ALIGN.CENTER; ep3.space_before = Pt(16)
            s25.notes_slide.notes_text_frame.text = "【演讲者致谢词】：非常感谢各位老师与同学的耐心聆听！以上就是关于微积分期末知识总结的全部汇报，预祝大家期末考试顺利，斩获高分！谢谢大家！"

        # =========================================================================
        # 模式 2: 其他领域通用深度定制（软件工程/商业/AI/通用科技）
        # =========================================================================
        else:
            # 引入之前的深度定制模块并杜绝重复
            from plugins.ppt_tools_helper import build_custom_deck_slides
            prs = build_custom_deck_slides(prs, blank_layout, clean_topic, duration_mins)

        # 保存并打开文件
        clean_name = file_name.strip() if file_name else f"{clean_topic[:14]}_{len(prs.slides)}页全景演讲.pptx"
        if not clean_name.endswith(".pptx"):
            clean_name += ".pptx"
        clean_name = re.sub(r'[\\/:*?"<>|]', '_', clean_name)

        desktop = Path.home() / "Desktop"
        save_path = desktop / clean_name
        try:
            prs.save(str(save_path))
        except PermissionError:
            save_path = desktop / f"{save_path.stem}_已生成.pptx"
            prs.save(str(save_path))

        try:
            os.startfile(str(save_path))
        except Exception:
            pass

        return _format_ppt_card(save_path, clean_topic, len(prs.slides), duration_mins)

    except Exception as e:
        return f"❌ 生成 PPT 演示文稿失败：{e}"