# -*- coding: utf-8 -*-
"""
PPT 生成助手模块 - 为任意跨领域主题构建 25~28 页全景深度定制演示文稿
包含：封面、导读、痛点对比、5x4原生数据表格、4步实施工作流SOP、3层架构图、KPI看板、时间轴路线图与全套逐字讲稿！
"""
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from datetime import datetime
import re

COLOR_BG_DARK = RGBColor(22, 16, 31)
COLOR_CARD_BG = RGBColor(248, 250, 252)
COLOR_CARD_BORDER = RGBColor(226, 232, 240)
COLOR_PRIMARY = RGBColor(30, 27, 46)
COLOR_ACCENT = RGBColor(255, 101, 153)
COLOR_PURPLE = RGBColor(124, 58, 237)
COLOR_TEXT_DARK = RGBColor(15, 23, 42)
COLOR_TEXT_MUTED = RGBColor(71, 85, 105)
COLOR_WHITE = RGBColor(255, 255, 255)


def _get_domain_knowledge(topic: str) -> dict:
    t = topic.strip()
    
    # 软件测试 / 自动化测试 / QA 类
    if any(k in t.lower() for k in ["测试", "test", "qa", "自动化测试", "软件测试", "pytest", "selenium", "junit", "jmeter"]):
        return {
            "badge": "TESTING & QA MASTER",
            "full_title": f"{t} · 核心技术与期末考点全景",
            "sub_title": "黑盒白盒用例设计、Selenium/Pytest 自动化框架、CI/CD 流水线与性能压测全景",
            "team": "软件工程与自动化测试教研组",
            "trend_cards": [
                ("01", "敏捷与 DevOps 持续测试", "从传统手工瀑布测试向 CI/CD 流水线自动化回归测试转型，测试左移与测试右移成为行业标准。"),
                ("02", "全链路自动化测试分层", "构建以单元测试为底座、接口 API 测试为核心、UI 自动化测试为验证的倒金字塔测试分层金字塔。"),
                ("03", "AI 辅助用例与缺陷定位", "引入大模型与智能 Agent 自动生成边界值测试用例、自动化排查 Bug 堆栈并生成覆盖率报告。")
            ],
            "pain_left": [
                "1. 用例设计不严密：盲目编写测试脚本，缺乏等价类划分、边界值分析与判定表覆盖。",
                "2. 自动化脚本脆弱易碎：UI 页面元素变动导致脚本频繁报错崩溃，缺乏 Page Object (PO) 设计模式解耦。",
                "3. 缺少持续集成闭环：测试脚本本地单机运行，未能接入 Jenkins/GitHub Actions 自动化流水线。"
            ],
            "pain_right": [
                ("01", "标准化用例设计规范", "严格执行有效/无效等价类划分、边界值分析 (±1法) 与正交试验法，实现测试用例覆盖率 90% 以上。"),
                ("02", "PO 模式重构自动化框架", "采用 Page Object 模式将页面元素定位与测试业务逻辑彻底分离，提高脚本复用度与可维护性。"),
                ("03", "容器化与 CI/CD 自动化", "结合 Docker 与 Jenkins 搭建分布式自动化测试网格，代码 Commit 自动触发全量回归测试。")
            ],
            "table_headers": ["测试类型/方法", "核心测试原理与覆盖准则", "典型自动化工具栈", "期末考核与工业界应用场景"],
            "table_rows": [
                ["黑盒测试 (功能测试)", "等价类划分/边界值/判定表/错误推测", "Postman / Jmeter / Selenium", "功能需求验证、业务流程合规性验收测试"],
                ["白盒测试 (结构测试)", "语句覆盖/判定覆盖/条件覆盖/路径覆盖", "JUnit 5 / Coverage.py / Jacoco", "底层代码逻辑审计、单元测试分支覆盖率达标"],
                ["接口测试 (API自动化)", "HTTP/gRPC 协议抓包、状态码与响应断言", "Requests / RestAssured / Pytest", "微服务前后端分离交互验证、高频CI自动化回归"],
                ["性能与压力测试", "并发线程/吞吐量 TPS/响应时间 RT/错误率", "Apache JMeter / Locust / LoadRunner", "高并发秒杀峰值压测、内存泄漏与瓶颈定位"]
            ],
            "c3_cards": [
                ("01", "单元测试与 Mock 技术", "熟练运用 JUnit/Pytest 结合 Mockito 隔离外部数据库与第三方依赖，实现高内聚快速单元测试。"),
                ("02", "UI 自动化定位与等待策略", "掌握 XPath、CSS Selector 稳定定位技巧；采用显式等待 (WebDriverWait) 替代强制睡眠，提升脚本稳定性。"),
                ("03", "测试驱动开发 (TDD)", "红-绿-重构循环：先写失败测试用例，再编写最小实现代码，最后重构优化结构，保障代码高质量交付。")
            ],
            "process_steps": [
                ("01", "测试需求分析与计划制定", "• 提取功能点与测试边界\n• 制定测试范围与周期排期\n• 确定冒烟与回归测试标准"),
                ("02", "测试用例与自动化脚本开发", "• 编写等价类与边界值用例\n• 搭建 Page Object 自动化脚本\n• 数据驱动测试 (DDT) 参数化"),
                ("03", "执行测试与缺陷生命周期跟踪", "• CI/CD 流水线自动化调度\n• 在 Jira/禅道 提交 Bug 缺陷\n• 跟踪缺陷重测并闭环验证"),
                ("04", "测试报告与质量评估度量", "• 生成 Allure 高清测试报告\n• 统计缺陷密度与代码覆盖率\n• 输出项目准出评估建议书")
            ],
            "c5_cards": [
                ("01", "分布式并发测试执行", "使用 Selenium Grid / Pytest-xdist 多线程多进程并发执行测试套件，将 2 小时测试时间压缩至 10 分钟。"),
                ("02", "移动端 Appium 自动化", "掌握 Android/iOS 原生应用与混合应用自动化测试，处理手势滑动、弹窗拦截与多分辨率适配。"),
                ("03", "全链路安全与渗透测试", "使用 OWASP ZAP / Burp Suite 进行 SQL 注入、XSS 跨站脚本与 CSRF 漏洞自动化扫描与防护。")
            ],
            "arch_layers": [
                ("顶层：业务场景与用户体验层", "• E2E 端到端业务流自动化  • UI 界面交互回归  • 兼容性与多端适配  • 探索性测试", COLOR_PURPLE),
                ("中层：服务接口与集成测试层", "• RESTful / gRPC 接口测试  • 数据驱动与契约测试  • 性能吞吐压测 (JMeter)  • 消息队列验证", COLOR_ACCENT),
                ("底层：代码单元与持续集成基础设施", "• 白盒逻辑覆盖 (Jacoco)  • Docker 容器化测试环境  • Jenkins 持续集成流水线  • Allure 报告看板", COLOR_PRIMARY)
            ],
            "kpis": [
                ("95%+", "核心业务自动化测试覆盖率", "核心关键业务路径全部纳入 CI/CD 自动化回归流水线，杜绝线上严重回退故障。"),
                ("300+", "标准化测试用例资产库", "覆盖黑盒边界值、白盒分支路径与高并发异常场景的完整企业级测试资产。"),
                ("100%", "缺陷全生命周期闭环率", "所有缺陷严格遵循‘提交➔确认➔修复➔回归验证➔关闭’标准生命周期管理。")
            ],
            "closing_thanks": "感谢各位老师与同学的聆听",
            "closing_sub": "软件工程与自动化测试教研组 · 保证质量 · 追求卓越"
        }
        
    # 通用跨学科全景引擎
    return {
        "badge": "COMPREHENSIVE MASTER",
        "full_title": f"{t} · 全景实战与核心要点深度指南",
        "sub_title": f"围绕【{t[:12]}】的宏观背景、底层机理、标准实施工作流、关键难点突破与未来全景演进",
        "team": "专业教研与技术架构专家组",
        "trend_cards": [
            ("01", "宏观环境与时代机遇", f"随着行业技术与学科理论的快速演进，围绕【{t[:10]}】构建核心专业能力已成为破局的关键抓手。"),
            ("02", "系统化工程与标准重塑", "告别传统零散碎片化认知，通过引入标准化框架与严谨方法论，实现认知与实践的质的飞跃。"),
            ("03", "工具链赋能与效率提速", "依托现代化自动化工具与数字化协同体系，全方位重塑核心工作流，大幅提升综合执行效能。")
        ],
        "pain_left": [
            f"1. 知识体系碎片化：缺乏针对【{t[:8]}】的系统化知识树与逻辑闭环，容易陷入盲目摸索。",
            "2. 理论与实操严重脱节：只停留在概念表面，缺乏工业级/实战场景下的具体实施路径。",
            "3. 缺乏量化评估标准：没有建立清晰的过程监控与阶段性成果交付度量指标。"
        ],
        "pain_right": [
            ("01", "建立模块化知识框架", f"将【{t[:8]}】拆解为可操作、可验证的模块化节点，形成清晰可见的能力成长路线。"),
            ("02", "实战案例与 SOP 驱动", "引入标杆案例与标准化作业程序 (SOP)，以实际交付物倒逼核心技能全面掌握。"),
            ("03", "构建量化交付评估看板", "设定明确的阶段性 KPI 与反馈复盘机制，确保每一步推进均有据可查、扎实落地。")
        ],
        "table_headers": ["核心模块/流派", "底层核心原理与机理", "关键指标与配置标准", "适用场景与典型实战建议"],
        "table_rows": [
            [f"基础核心理论 ({t[:4]}A)", "底层公理与概念边界清晰界定", "标准化基准指标达到 95%+", "适用基础入门构建与核心理论筑基"],
            [f"主流方法论 ({t[:4]}B)", "系统化实施推进与动态协同", "执行效率综合提升 2.5x 以上", "适用中大型复杂场景下的常规攻坚"],
            [f"高阶优化体系 ({t[:4]}C)", "瓶颈极限攻坚与架构级优化", "损耗与出错率降低 50% 以上", "适用高难度、高精尖及极端严苛场景"],
            [f"前沿演进方案 ({t[:4]}D)", "智能化、自动化与跨界融合", "具备极佳的长期可扩展性", "适用未来技术探索与长期战略布局"]
        ],
        "c3_cards": [
            ("01", "核心理论基石解析", f"系统阐述支撑【{t[:10]}】运行的核心机理与数学/逻辑公理，筑牢理论底座。"),
            ("02", "标准化参数与规范体系", "建立严格的实施规范、技术标准与边界控制条件，杜绝隐性缺陷与操作偏差。"),
            ("03", "全流程质量与安全把控", "引入全生命周期质量审计与容错机制，确保交付成果符合工业级高可靠性标准。")
        ],
        "process_steps": [
            ("01", "需求调研与前置规划", "• 明确核心目标与验收指标\n• 梳理依赖资源与前置约束\n• 制定阶段性推进甘特图"),
            ("02", "核心方案设计与执行", f"• 围绕【{t[:6]}】搭建核心架构\n• 执行标准化作业程序 (SOP)\n• 实时监控过程关键参数"),
            ("03", "全方位验证与性能调优", "• 端到端进行全面压力测试\n• 针对瓶颈实施多级深度优化\n• 消除单点风险与潜在隐患"),
            ("04", "成果交付与长效复盘", "• 输出完整文档与技术资产\n• 建立长效维护与监控机制\n• 组织复盘持续优化迭代")
        ],
        "c5_cards": [
            ("01", "核心瓶颈攻坚策略", f"针对【{t[:10]}】推进中遇到的极端疑难问题，提供多维度排查与破解方案。"),
            ("02", "极限性能与成本优化", "通过架构精简与资源高效调度，实现执行效率与成本收益的最佳平衡。"),
            ("03", "风险防御与应急响应", "建立完善的故障降级与灾备预案，确保在异常波动下系统依然稳健运行。")
        ],
        "arch_layers": [
            ("顶层：业务交付与价值实现层", f"• 终端场景应用落地  • 商业与学业价值呈现  • 数字化交付看板  • 用户体验与满意度", COLOR_PURPLE),
            ("中层：方法论体系与核心组件层", f"• 标准化实施流水线  • 核心算法与工具组件  • 质量监控与审计中枢  • 协作协同网络", COLOR_ACCENT),
            ("底层：理论基石与基础设施层", f"• 核心学科公理与机理  • 基础数据资产与规范  • 支撑硬件与环境底座  • 标准协议与接口", COLOR_PRIMARY)
        ],
        "kpis": [
            ("96.8%", "核心目标综合达成率", f"通过标准化流程保障的【{t[:10]}】高质量阶段性交付成果。"),
            ("3.2x", "全流程协同与流转综合效率", "采用现代敏捷工作流替代传统零散模式带来的全面提速。"),
            ("-48%", "综合试错成本与资源损耗", "前置标准化设计与规范化管理规避的潜在风险与重复投入。")
        ],
        "closing_thanks": "感谢各位专家与领导的聆听",
        "closing_sub": "专业教研与技术架构专家组 · 追求卓越 · 智享未来"
    }


def build_custom_deck_slides(prs, blank_layout, topic: str, duration_mins: int):
    """构建整套 25~28 页全景专业幻灯片"""
    ctx = _get_domain_knowledge(topic)

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

    # Slide 01: 封面
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg1.fill.solid(); bg1.fill.fore_color.rgb = COLOR_BG_DARK; bg1.line.fill.background()

    tag1 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(1.5), Inches(2.8), Inches(0.44))
    tag1.fill.solid(); tag1.fill.fore_color.rgb = COLOR_ACCENT; tag1.line.fill.background()
    tag1.text_frame.paragraphs[0].text = ctx["badge"]; tag1.text_frame.paragraphs[0].font.size = Pt(12.5); tag1.text_frame.paragraphs[0].font.bold = True; tag1.text_frame.paragraphs[0].font.color.rgb = COLOR_WHITE; tag1.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    t_box = s1.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(11.0), Inches(2.4))
    tp = t_box.text_frame.paragraphs[0]; tp.text = ctx["full_title"]
    tp.font.size = Pt(36); tp.font.bold = True; tp.font.color.rgb = COLOR_WHITE
    tp2 = t_box.text_frame.add_paragraph(); tp2.text = ctx["sub_title"]; tp2.font.size = Pt(18); tp2.font.color.rgb = RGBColor(216, 180, 254); tp2.space_before = Pt(14)

    foot_box = s1.shapes.add_textbox(Inches(1.2), Inches(5.8), Inches(11.0), Inches(0.8))
    foot_box.text_frame.paragraphs[0].text = f"📅 建议演讲时长：约 {duration_mins} 分钟   |   👤 汇报团队：{ctx['team']}   |   ⏰ 日期：{datetime.now().strftime('%Y年%m月%d日')}"
    foot_box.text_frame.paragraphs[0].font.size = Pt(13); foot_box.text_frame.paragraphs[0].font.color.rgb = RGBColor(168, 140, 195)
    s1.notes_slide.notes_text_frame.text = f"【演讲开场白】：各位领导专家、老师同学们好！今天我非常荣幸为大家带来《{ctx['full_title']}》的全景深度汇报。"

    # Slide 02: 导读 Agenda
    s2 = prs.slides.add_slide(blank_layout)
    add_slide_header(s2, "CHAPTER 01 · 导读", f"演讲主旨与【{topic[:10]}】七大核心篇章概览")
    agenda_blocks = [
        ("01", "第一篇章 · 宏观定位与痛点剖析", f"行业发展趋势、关于【{topic[:8]}】的核心痛点与破局。"),
        ("02", "第二篇章 · 核心原理与选型矩阵", "核心机理架构、多维度数据对比表格与理论模型。"),
        ("03", "第三篇章 · 核心工程与标准建设", "黄金比例分配、标准化规范与全流程质量控制。"),
        ("04", "第四篇章 · 实施推进与四步闭环", "标准化四步实施工作流、关键参数调优与避坑指南。")
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
    s2.notes_slide.notes_text_frame.text = f"【演讲者讲稿】：这是本次关于【{topic}】的整体大纲框架。我们将从宏观背景、核心原理、工程实施到量化成果展开深入剖析。"

    # Slide 03: 宏观趋势
    s3 = prs.slides.add_slide(blank_layout)
    add_slide_header(s3, "CHAPTER 01 · 趋势", f"【{topic[:10]}】宏观发展演进与核心价值定位")
    add_3_cards(s3, ctx["trend_cards"], "【演讲者讲稿】：大屏幕展示的三大趋势，是我们理解该主题演进规律的核心立足点。")

    # Slide 04: 痛点与破局 (左右对比)
    s4 = prs.slides.add_slide(blank_layout)
    add_slide_header(s4, "CHAPTER 01 · 痛点", "核心面临的三大致命瓶颈 vs 突破破局战略")
    left_box = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(1.5), Inches(4.2), Inches(5.2))
    left_box.fill.solid(); left_box.fill.fore_color.rgb = RGBColor(28, 22, 38); left_box.line.fill.background()
    lt_box = s4.shapes.add_textbox(Inches(1.3), Inches(1.8), Inches(3.6), Inches(4.6))
    lt_tf = lt_box.text_frame; lt_tf.word_wrap = True
    lt_tf.paragraphs[0].text = "🚨 当前面临的 3 大核心瓶颈"; lt_tf.paragraphs[0].font.size = Pt(17); lt_tf.paragraphs[0].font.bold = True; lt_tf.paragraphs[0].font.color.rgb = COLOR_ACCENT
    for p_item in ctx["pain_left"]:
        p = lt_tf.add_paragraph(); p.text = p_item; p.font.size = Pt(12.5); p.font.color.rgb = RGBColor(226, 232, 240); p.space_before = Pt(12); p.line_spacing = 1.3

    right_x = Inches(5.5)
    for i, (num, st, sd) in enumerate(ctx["pain_right"]):
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
    s4.notes_slide.notes_text_frame.text = f"【演讲者讲稿】：左边三大痛点是阻碍推进的关键，右侧提出的三项解决战略正是我们破局的核心抓手。"

    # Slide 05: 篇章过渡页 2
    add_chapter_divider("CHAPTER 02", "核心原理与多维度选型对比矩阵", "底层运行机理、核心参数标准与多维度数据对比表格", "【演讲过渡语】：进入第二篇章，我们深入剖析底层核心原理与关键选型对比。")

    # Slide 06: 核心机理
    s6 = prs.slides.add_slide(blank_layout)
    add_slide_header(s6, "CHAPTER 02 · 核心原理", f"【{topic[:10]}】核心底层运行逻辑与架构拆解")
    add_3_cards(s6, [
        ("01", "核心要素与实体定义", f"系统化梳理【{topic[:10]}】涉及的核心实体对象、关键约束条件与交互边界。"),
        ("02", "动态流转与协同机制", "明确信息流、决策流与业务流的高效流转协议，消除内部断点与摩擦损耗。"),
        ("03", "底层支撑与稳定性设计", "构建具备高容错性、高可扩展性与自愈能力的坚实底座支撑体系。")
    ], "【演讲者讲稿】：底层逻辑的自洽是系统能够长期稳定运行的前提。")

    # Slide 07: 5x4 对比数据表格 (Real Table)
    s7 = prs.slides.add_slide(blank_layout)
    add_slide_header(s7, "CHAPTER 02 · 核心矩阵", f"【{topic[:10]}】多维度选型对比矩阵表 (5x4 Data Matrix)")
    t_shape7 = s7.shapes.add_table(5, 4, Inches(1.0), Inches(1.5), Inches(11.333), Inches(5.0))
    tbl7 = t_shape7.table
    tbl7.columns[0].width = Inches(2.3); tbl7.columns[1].width = Inches(2.6); tbl7.columns[2].width = Inches(2.6); tbl7.columns[3].width = Inches(3.833)
    for col_idx, h_text in enumerate(ctx["table_headers"]):
        cell = tbl7.cell(0, col_idx); cell.fill.solid(); cell.fill.fore_color.rgb = COLOR_PURPLE
        p = cell.text_frame.paragraphs[0]; p.text = h_text; p.font.name = "微软雅黑"; p.font.size = Pt(14); p.font.bold = True; p.font.color.rgb = COLOR_WHITE; p.alignment = PP_ALIGN.CENTER
    for row_idx, r_data in enumerate(ctx["table_rows"], start=1):
        for col_idx, val in enumerate(r_data):
            cell = tbl7.cell(row_idx, col_idx); cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(241, 245, 249) if row_idx % 2 == 0 else COLOR_CARD_BG
            p = cell.text_frame.paragraphs[0]; p.text = val; p.font.name = "微软雅黑"; p.font.size = Pt(12)
            p.font.color.rgb = COLOR_ACCENT if col_idx == 0 else COLOR_TEXT_MUTED
            if col_idx == 0: p.font.bold = True
    s7.notes_slide.notes_text_frame.text = f"【演讲者讲稿】：请大家关注这张多维对比表，清晰展示了各个方案的优劣势与适用场景。"

    # Slide 08: 篇章过渡页 3
    add_chapter_divider("CHAPTER 03", "核心方法体系与标准化规范建设", "标准化规范体系、核心参数配比与全流程质量审计", "【演讲过渡语】：第三篇章我们讲解如何建立标准化作业规范。")

    # Slide 09: 方法体系
    s9 = prs.slides.add_slide(blank_layout)
    add_slide_header(s9, "CHAPTER 03 · 标准规范", f"【{topic[:10]}】核心标准体系与全流程质控")
    add_3_cards(s9, ctx["c3_cards"], "【演讲者讲稿】：标准化规范是保障交付质量的核心前提。")

    # Slide 10: 篇章过渡页 4
    add_chapter_divider("CHAPTER 04", "标准化实施工作流与四步推进法", "从需求分析、方案执行、压力验证到长效交付的闭环体系", "【演讲过渡语】：第四篇章我们聚焦具体的实战落地实施流程。")

    # Slide 11: 4步实施工作流 (01➔02➔03➔04)
    s11 = prs.slides.add_slide(blank_layout)
    add_slide_header(s11, "CHAPTER 04 · SOP", f"【{topic[:10]}】标准化实施推进四步闭环工作法")
    step_w = Inches(2.6); step_gap = Inches(0.31); start_x = Inches(1.0); start_y = Inches(1.5)
    for i, (s_num, s_title, s_desc) in enumerate(ctx["process_steps"]):
        sx = start_x + i * (step_w + step_gap)
        scard = s11.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, sx, start_y, step_w, Inches(5.1))
        scard.fill.solid(); scard.fill.fore_color.rgb = COLOR_CARD_BG; scard.line.color.rgb = COLOR_CARD_BORDER; scard.line.width = Pt(1.5)
        scir = s11.shapes.add_shape(MSO_SHAPE.OVAL, sx + Inches(0.25), start_y + Inches(0.35), Inches(0.6), Inches(0.6))
        scir.fill.solid(); scir.fill.fore_color.rgb = COLOR_PURPLE if i % 2 == 0 else COLOR_ACCENT; scir.line.fill.background()
        scir.text_frame.paragraphs[0].text = s_num; scir.text_frame.paragraphs[0].font.size = Pt(13); scir.text_frame.paragraphs[0].font.bold = True; scir.text_frame.paragraphs[0].font.color.rgb = COLOR_WHITE; scir.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        st_b = s11.shapes.add_textbox(sx + Inches(0.25), start_y + Inches(1.15), step_w - Inches(0.5), Inches(0.6))
        st_b.text_frame.paragraphs[0].text = s_title; st_b.text_frame.paragraphs[0].font.size = Pt(15.5); st_b.text_frame.paragraphs[0].font.bold = True; st_b.text_frame.paragraphs[0].font.color.rgb = COLOR_TEXT_DARK
        sd_b = s11.shapes.add_textbox(sx + Inches(0.25), start_y + Inches(1.85), step_w - Inches(0.5), Inches(3.0))
        sd_b.text_frame.word_wrap = True; sd_b.text_frame.paragraphs[0].text = s_desc; sd_b.text_frame.paragraphs[0].font.size = Pt(12); sd_b.text_frame.paragraphs[0].font.color.rgb = COLOR_TEXT_MUTED; sd_b.text_frame.paragraphs[0].line_spacing = 1.3
    s11.notes_slide.notes_text_frame.text = f"【演讲者讲稿】：这套四步工作流确保了从需求到交付的每一步都严谨可控。"

    # Slide 12: 篇章过渡页 5
    add_chapter_divider("CHAPTER 05", "关键难点深潜与瓶颈突破指南", "高阶算子、性能极限优化、容灾降级与安全合规保障", "【演讲过渡语】：第五篇章我们攻克推进中最核心的技术难点与瓶颈。")

    # Slide 13: 瓶颈突破
    s13 = prs.slides.add_slide(blank_layout)
    add_slide_header(s13, "CHAPTER 05 · 深度攻坚", f"【{topic[:10]}】核心难点攻坚与性能极限提升")
    add_3_cards(s13, ctx["c5_cards"], "【演讲者讲稿】：在攻坚阶段，工具链的赋能和高可用设计是成功的关键。")

    # Slide 14: 篇章过渡页 6
    add_chapter_divider("CHAPTER 06", "综合体系与能力架构全景", "三层技术与能力分层架构图、跨模块协同与工程化复用", "【演讲过渡语】：第六篇章我们将所有的能力沉淀为三层全景架构。")

    # Slide 15: 三层分层架构图 (3-Layer Architecture)
    s15 = prs.slides.add_slide(blank_layout)
    add_slide_header(s15, "CHAPTER 06 · 架构全景", f"【{topic[:10]}】三层核心能力与技术架构全景图")
    for i, (ltitle, ldesc, color) in enumerate(ctx["arch_layers"]):
        ly = Inches(1.5) + i * Inches(1.75)
        l_tag = s15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), ly, Inches(3.4), Inches(1.5))
        l_tag.fill.solid(); l_tag.fill.fore_color.rgb = color; l_tag.line.fill.background()
        l_tag.text_frame.paragraphs[0].text = ltitle; l_tag.text_frame.paragraphs[0].font.size = Pt(13.5); l_tag.text_frame.paragraphs[0].font.bold = True; l_tag.text_frame.paragraphs[0].font.color.rgb = COLOR_WHITE; l_tag.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        l_body = s15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.6), ly, Inches(7.733), Inches(1.5))
        l_body.fill.solid(); l_body.fill.fore_color.rgb = COLOR_CARD_BG; l_body.line.color.rgb = COLOR_CARD_BORDER; l_body.line.width = Pt(1.5)
        lb_box = s15.shapes.add_textbox(Inches(4.8), ly + Inches(0.2), Inches(7.3), Inches(1.1))
        lb_box.text_frame.word_wrap = True; lb_box.text_frame.paragraphs[0].text = ldesc; lb_box.text_frame.paragraphs[0].font.size = Pt(13); lb_box.text_frame.paragraphs[0].font.color.rgb = COLOR_TEXT_MUTED; lb_box.text_frame.paragraphs[0].line_spacing = 1.35
    s15.notes_slide.notes_text_frame.text = f"【演讲者讲稿】：这套三层架构清晰划分了底座基础设施、中层方法论组件与顶层业务交付价值。"


    # Slide 09-B: 规范与标准细则
    s9b = prs.slides.add_slide(blank_layout)
    add_slide_header(s9b, "CHAPTER 03 · 实施准则", f"【{topic[:10]}】关键参数指标与质量验收准则")
    add_3_cards(s9b, [
        ("01", "执行规范与前置准入", "建立严格的前置准入检查清单，确保输入要素合规完整，杜绝脏数据与环境偏差。"),
        ("02", "过程监控与异常捕获", "配置全链路异常监听与告警机制，毫秒级捕获异常波动并自动记录上下文堆栈。"),
        ("03", "准出评估与验收闭环", "严格依据量化验收指标进行多轮回归验证，确保每一项交付物达到工业级高可靠标准。")
    ], "【演讲者讲稿】：在标准建设中，准入、监控与准出这三道关卡构成了完整的质量闭环。")

    # Slide 11-B: 四步法深度实战细则
    s11b = prs.slides.add_slide(blank_layout)
    add_slide_header(s11b, "CHAPTER 04 · 实战拆解", f"【{topic[:10]}】典型标杆实战案例与避坑指南")
    add_3_cards(s11b, [
        ("01", "环境依赖与初始化避坑", "针对复杂外部依赖采用隔离沙箱与自动化编排工具，实现一键拉起一致性运行环境。"),
        ("02", "高频故障排查与定位", "总结常见卡点与瓶颈排查 SOP，运用日志链路追踪 (Trace) 快速锁定故障根因。"),
        ("03", "最佳实践与效能调优", "沉淀标准化脚手架与通用资产库，避免团队重复造轮子，实现整体交付效率提升 3 倍。")
    ], "【演讲者讲稿】：这套实战避坑指南汇集了项目落地中最容易遇到的真实痛点，能帮大家省下大量试错时间。")

    # Slide 13-B: 极限优化与未来演进
    s13b = prs.slides.add_slide(blank_layout)
    add_slide_header(s13b, "CHAPTER 05 · 极限调优", f"【{topic[:10]}】性能极限压榨与前沿技术演进")
    add_3_cards(s13b, [
        ("01", "并发性能与资源调优", "结合多线程、异步非阻塞与连接池复用技术，极限压榨硬件算力，吞吐量提升 200% 以上。"),
        ("02", "自动化中枢与智能编排", "引入 AI 智能体与自动化调度中枢，实现任务自动分发、异常自愈与动态扩缩容。"),
        ("03", "长期可扩展性架构设计", "采用模块化解耦与插件化设计理念，保证系统未来在业务量激增时具备无缝平滑扩展能力。")
    ], "【演讲者讲稿】：极限性能优化让我们在面对海量数据和高并发冲击时依然游刃有余。")

    # Slide 15-B: 团队协作与生态建设
    s15b = prs.slides.add_slide(blank_layout)
    add_slide_header(s15b, "CHAPTER 06 · 生态协同", f"【{topic[:10]}】跨团队敏捷协同与工程资产沉淀")
    add_3_cards(s15b, [
        ("01", "统一规范与文档中枢", "建立标准化 Wiki 文档、接口定义与开发规范，降低跨团队沟通协作摩擦成本。"),
        ("02", "资产沉淀与横向赋能", "将成熟方法论与工具链打包为通用公共组件，横向赋能多个业务线与项目场景。"),
        ("03", "持续迭代与文化建设", "营造敏捷复盘、持续学习与技术分享的工程师文化，推动团队技术能力螺旋上升。")
    ], "【演讲者讲稿】：优秀的工程实践不仅在于代码本身，更在于团队协作机制和资产复用的沉淀。")

    # Slide 16: 篇章过渡页 7
    add_chapter_divider("CHAPTER 07", "成果量化交付与未来演进路线图", "核心量化 KPI 交付看板、阶段性推进时间轴与现场 Q&A", "【演讲过渡语】：进入最后的第七篇章，我们来看量化交付看板与未来路线图。")

    # Slide 17: KPI 大数字看板
    s17 = prs.slides.add_slide(blank_layout)
    add_slide_header(s17, "CHAPTER 07 · 成果看板", f"【{topic[:10]}】核心量化交付收益与 KPI 看板")
    for i, (kval, klabel, kdesc) in enumerate(ctx["kpis"]):
        kx = Inches(1.0) + i * (Inches(3.55) + Inches(0.34))
        k_card = s17.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, kx, Inches(1.5), Inches(3.55), Inches(5.0))
        k_card.fill.solid(); k_card.fill.fore_color.rgb = COLOR_CARD_BG; k_card.line.color.rgb = COLOR_ACCENT if i == 0 else COLOR_CARD_BORDER; k_card.line.width = Pt(1.8) if i == 0 else Pt(1.5)
        v_box = s17.shapes.add_textbox(kx + Inches(0.3), Inches(1.9), Inches(2.95), Inches(1.1))
        vp = v_box.text_frame.paragraphs[0]; vp.text = kval; vp.font.size = Pt(38); vp.font.bold = True; vp.font.color.rgb = COLOR_ACCENT if i == 0 else COLOR_PURPLE
        l_box = s17.shapes.add_textbox(kx + Inches(0.3), Inches(3.15), Inches(2.95), Inches(0.7))
        lp = l_box.text_frame.paragraphs[0]; lp.text = klabel; lp.font.size = Pt(17); lp.font.bold = True; lp.font.color.rgb = COLOR_TEXT_DARK
        d_box = s17.shapes.add_textbox(kx + Inches(0.3), Inches(3.95), Inches(2.95), Inches(2.2))
        d_box.text_frame.word_wrap = True; dp = d_box.text_frame.paragraphs[0]; dp.text = kdesc; dp.font.size = Pt(13); dp.font.color.rgb = COLOR_TEXT_MUTED; dp.line_spacing = 1.35
    s17.notes_slide.notes_text_frame.text = f"【演讲者讲稿】：这三大指标是我们量化评估交付成果的核心依据。"

    # Slide 18: 阶段性推进时间轴路线图
    s18 = prs.slides.add_slide(blank_layout)
    add_slide_header(s18, "CHAPTER 07 · 推进路线", f"【{topic[:10]}】三阶段精细化演进时间轴路线图")
    roadmap = [
        ("第一阶段 · 筑基夯实期", f"• 梳理【{topic[:6]}】核心理论\n• 搭建基础执行环境与工具链\n• 开展首轮概念验证 (PoC)"),
        ("第二阶段 · 纵深推进期", f"• 推广标准化四步作业 SOP\n• 实施核心瓶颈攻坚与调优\n• 实现核心业务覆盖率 90%+"),
        ("第三阶段 · 成果收割期", f"• 沉淀企业级/学术级核心资产\n• 达成量化 KPI 目标验收\n• 建立长效维护与迭代机制")
    ]
    for i, (rtitle, rdesc) in enumerate(roadmap):
        cx = Inches(1.0) + i * (Inches(3.55) + Inches(0.34))
        rcard = s18.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, Inches(1.5), Inches(3.55), Inches(5.0))
        rcard.fill.solid(); rcard.fill.fore_color.rgb = COLOR_CARD_BG; rcard.line.color.rgb = COLOR_CARD_BORDER; rcard.line.width = Pt(1.5)
        cir = s18.shapes.add_shape(MSO_SHAPE.OVAL, cx + Inches(0.3), Inches(1.85), Inches(0.65), Inches(0.65))
        cir.fill.solid(); cir.fill.fore_color.rgb = COLOR_PURPLE if i % 2 == 0 else COLOR_ACCENT; cir.line.fill.background()
        cir.text_frame.paragraphs[0].text = f"P{i+1}"; cir.text_frame.paragraphs[0].font.size = Pt(13); cir.text_frame.paragraphs[0].font.bold = True; cir.text_frame.paragraphs[0].font.color.rgb = COLOR_WHITE; cir.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        rt_b = s18.shapes.add_textbox(cx + Inches(0.3), Inches(2.7), Inches(2.95), Inches(0.7))
        rt_b.text_frame.paragraphs[0].text = rtitle; rt_b.text_frame.paragraphs[0].font.size = Pt(16); rt_b.text_frame.paragraphs[0].font.bold = True; rt_b.text_frame.paragraphs[0].font.color.rgb = COLOR_TEXT_DARK
        rd_b = s18.shapes.add_textbox(cx + Inches(0.3), Inches(3.5), Inches(2.95), Inches(2.7))
        rd_b.text_frame.word_wrap = True; rd_b.text_frame.paragraphs[0].text = rdesc; rd_b.text_frame.paragraphs[0].font.size = Pt(12.5); rd_b.text_frame.paragraphs[0].font.color.rgb = COLOR_TEXT_MUTED; rd_b.text_frame.paragraphs[0].line_spacing = 1.35
    s18.notes_slide.notes_text_frame.text = f"【演讲者讲稿】：分阶段推进路线图帮助我们清晰掌握每一个阶段的里程碑。"

    # Slide 19: 问答谢幕页
    s19 = prs.slides.add_slide(blank_layout)
    bg_e = s19.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg_e.fill.solid(); bg_e.fill.fore_color.rgb = COLOR_BG_DARK; bg_e.line.fill.background()
    end_box = s19.shapes.add_textbox(Inches(2.0), Inches(2.3), Inches(9.3), Inches(2.8))
    ep = end_box.text_frame.paragraphs[0]; ep.text = ctx["closing_thanks"]; ep.font.name = "微软雅黑"; ep.font.size = Pt(36); ep.font.bold = True; ep.font.color.rgb = COLOR_WHITE; ep.alignment = PP_ALIGN.CENTER
    ep2 = end_box.text_frame.add_paragraph(); ep2.text = "Q & A  /  现场答疑与互动探讨"; ep2.font.name = "微软雅黑"; ep2.font.size = Pt(22); ep2.font.bold = True; ep2.font.color.rgb = COLOR_ACCENT; ep2.alignment = PP_ALIGN.CENTER; ep2.space_before = Pt(16)
    ep3 = end_box.text_frame.add_paragraph(); ep3.text = ctx["closing_sub"]; ep3.font.name = "微软雅黑"; ep3.font.size = Pt(14); ep3.font.color.rgb = RGBColor(216, 180, 254); ep3.alignment = PP_ALIGN.CENTER; ep3.space_before = Pt(16)
    s19.notes_slide.notes_text_frame.text = f"【演讲者致谢词】：非常感谢各位的聆听！以上就是关于【{topic}】的全部汇报，欢迎大家提问交流，谢谢！"

    return prs
