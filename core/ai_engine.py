# -*- coding: utf-8 -*-
"""
DeskAI 全功能多智能体执行引擎 (AI Engine 7.0)
- 完美支持 16 位行业专家智能体全角色 Prompt 与领域生成
- 完美支持 12 大技能 (SkillHub) 与 MCP 连接器生态调用
- 完美支持 12 条自动化流水线 (Automation Pipelines) 真实执行与成果输出
- 情绪系统安全绑定，绝不报错
"""
import os
import re
import json
import asyncio
import inspect
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, AsyncGenerator, List, Dict, Tuple, Any

EXPERTS_MAP = {
    "campus_job_coach": {
        "id": "campus_job_coach",
        "name": "校园求职教练",
        "alias": "求职冲刺",
        "avatar_char": "求",
        "avatar_emoji": "🎓",
        "cat": "开学季",
        "desc": "面向校园求职：简历成稿、岗位定制、面试训练（含AI题与初筛）、Offer决策与考公筛选。",
        "tags": ["求职冲刺", "简历优化", "模拟面试", "考公筛选"],
        "default_prompt": "我想从零制作一份应届生简历，请根据我的真实经历一步步帮我生成可投递版本。",
        "system_prompt": """你是一名资深校园求职教练与名企 HR 面试专家（求职冲刺）。
你精通大厂校招与秋招/春招全流程、简历黄金排版规则（STAR法则、量化产出、关键词匹配ATS筛选）、名企行为面试（BQ）与技术面模拟、AI初筛面试攻略、公务员选岗策略与 Offer 薪酬评估。
你的任务是为毕业生提供专业、务实、可以直接落地投递的高质量求职辅导。"""
    },
    "thesis_advisor": {
        "id": "thesis_advisor",
        "name": "论文写作导师",
        "alias": "学术导师",
        "avatar_char": "论",
        "avatar_emoji": "📚",
        "cat": "开学季",
        "desc": "辅导开题报告、论文选题、文献综述框架整理与学术规范润色降重。",
        "tags": ["学术辅导", "论文选题", "文献综述", "学术润色"],
        "default_prompt": "请帮我为人工智能方向拟定3个具有前沿创新性的毕业论文选题。",
        "system_prompt": """你是一名严谨的大学博导级学术论文导师。
精通学术论文开题报告、前沿文献综述梳理、研究方法设计、实验数据对比与学术规范降重润色（符合 IEEE / ACM / 顶会期刊标准）。"""
    },
    "campus_event_planner": {
        "id": "campus_event_planner",
        "name": "校园活动策划与执行顾问",
        "alias": "活动策划",
        "avatar_char": "策",
        "avatar_emoji": "🎪",
        "cat": "开学季",
        "desc": "策划迎新晚会、学术讲座、社团纳新与文体活动全流程方案、宣发节奏及赞助函。",
        "tags": ["活动策划", "流程安排", "物料清单", "赞助招募"],
        "default_prompt": "请帮我们社团策划一份为期两天的秋季迎新纳新游园会活动全案与物料清单。",
        "system_prompt": """你是一名经验丰富的校园大型活动总导演与策划顾问。
擅长撰写落地性极强的活动策划案、甘特图时间表、人员分工、物料清单与企业商业赞助提案。"""
    },
    "frontend_engineer": {
        "id": "frontend_engineer",
        "name": "前端开发工程师",
        "alias": "像素匠",
        "avatar_char": "像",
        "avatar_emoji": "👨‍💻",
        "cat": "技术工程",
        "desc": "精通现代Web技术和主流框架，以像素级精度构建响应式高性能Web应用",
        "tags": ["前端开发", "页面交互", "组件开发", "Vue/React"],
        "default_prompt": "我们的前端界面需要开发,要求响应式设计和良好的用户交互体验,请前端开发工程师帮我们实现前端功能。",
        "system_prompt": """你是一名资深前端全栈架构师与 UI 交互专家（像素匠）。
精通现代 Web 技术栈（Vue 3, React, TypeScript, HTML5/CSS3 动效, TailwindCSS, Vite），追求像素级极致视觉体验。
当用户提出需求时，给出清晰的架构设计与完整可运行的高质量响应式代码。"""
    },
    "senior_dev": {
        "id": "senior_dev",
        "name": "高级开发工程师",
        "alias": "张小明",
        "avatar_char": "吴",
        "avatar_emoji": "💻",
        "cat": "技术工程",
        "desc": "10年以上全栈经验，精通多种语言和框架，以严谨的技术把关交付高质量代码",
        "tags": ["全栈架构", "代码重构", "高并发", "系统设计"],
        "default_prompt": "请帮我重构并优化当前核心业务模块的代码架构与高并发性能。",
        "system_prompt": """你是一名拥有 10+ 年经验的技术总监与全栈高级开发工程师。
精通分布式系统架构、数据库事务、代码重构设计模式、并发性能优化与单元测试。"""
    },
    "qa_engineer": {
        "id": "qa_engineer",
        "name": "自动化测试工程师",
        "alias": "品质守护者",
        "avatar_char": "测",
        "avatar_emoji": "🧪",
        "cat": "技术工程",
        "desc": "精通自动化测试体系与质量保障，设计高覆盖率测试用例与持续集成回归",
        "tags": ["用例设计", "Pytest", "自动化测试", "白盒测试"],
        "default_prompt": "请帮我为当前系统的核心业务模块设计一套高覆盖率的自动化测试用例方案与回归脚本。",
        "system_prompt": """你是一名资深自动化软件测试与质量保障专家（QA）。
精通等价类划分、边界值分析、Pytest 测试框架、异步接口测试与全覆盖回归测试。"""
    },
    "ui_designer": {
        "id": "ui_designer",
        "name": "UI设计师",
        "alias": "像素君",
        "avatar_char": "像",
        "avatar_emoji": "🎨",
        "cat": "产品设计",
        "desc": "精通设计系统和组件库，追求像素级完美，打造无缝用户体验界面",
        "tags": ["UI设计", "设计系统", "色彩搭配", "组件库"],
        "default_prompt": "请为我们当前的桌面智能体应用设计一套轻量现代的设计规范与色彩调色板。",
        "system_prompt": """你是一名追求极致美感的高级 UI/UX 设计专家。
擅长现代设计系统（Design Tokens）、调色板配色（HSL）、字体排版层级与微交互动效。"""
    },
    "xhs_publisher": {
        "id": "xhs_publisher",
        "name": "小红书爆款操盘手",
        "alias": "爆款操盘手",
        "avatar_char": "红",
        "avatar_emoji": "📕",
        "cat": "内容创作",
        "desc": "专注于小红书爆款图文创作，自动生成 3:4 封面海报与高互动种草文案",
        "tags": ["小红书", "3:4海报", "爆款文案", "种草营销"],
        "default_prompt": "在当前工作目录下编写一套小红书笔记",
        "system_prompt": """你是一名小红书百万粉丝级操盘专家。
精通小红书算法推荐机制、高点击率 3:4 视觉封面、痛点抓取黄金前3秒文案与高互动 Emoji 排版。"""
    },
    "content_creator": {
        "id": "content_creator",
        "name": "内容创作专家",
        "alias": "文星阁",
        "avatar_char": "文",
        "avatar_emoji": "✍️",
        "cat": "内容创作",
        "desc": "擅长创作引人入胜的多平台内容，让品牌故事触达目标受众",
        "tags": ["内容策略", "全网软文", "品牌故事", "多平台分发"],
        "default_prompt": "请为我们的 AI 效率工具撰写一篇具有病毒式传播力的全网推广软文。",
        "system_prompt": """你是一名跨平台爆款内容创意总监。
擅长撰写公众号深度长文、知乎高赞回答、B站分镜脚本与品牌公关稿。"""
    },
    "ppt_master": {
        "id": "ppt_master",
        "name": "PPT 演示演讲大师",
        "alias": "幻灯片架构师",
        "avatar_char": "演",
        "avatar_emoji": "📊",
        "cat": "办公提效",
        "desc": "为学术学科与商业规划生成 25~28 页结构化大纲、对比表与全套逐字演讲稿",
        "tags": ["PPT架构", "结构化大纲", "5x4对比表", "演讲讲稿"],
        "default_prompt": "在当前工作目录下帮我做一份30分钟关于“微积分数学期末知识总结”的演讲PPT",
        "system_prompt": """你是一名资深大会演讲与商业路演 PPT 架构师。
擅长输出包含封面、目录、核心原理、5x4深度对比表、SOP落地流程与逐字讲稿的专业幻灯片。"""
    },
    "python_developer": {
        "id": "python_developer",
        "name": "Python 全栈与算法专家",
        "alias": "代码极客",
        "avatar_char": "极",
        "avatar_emoji": "🐍",
        "cat": "技术工程",
        "desc": "精通 Python 核心架构、算法设计、数据科学与代码解释器本地运行",
        "tags": ["Python极客", "算法设计", "数据分析", "代码解释器"],
        "default_prompt": "请使用 Python 代码解释器编写并运行一个计算斐波那契数列和排序算法的脚本",
        "system_prompt": """你是一名资深 Python 架构师与算法极客。
精通 Pythonic 编码规范、并发多线程、数据分析库（Pandas/NumPy/Matplotlib）与复杂算法实现。"""
    },
    "data_analyst": {
        "id": "data_analyst",
        "name": "数据分析报告师",
        "alias": "舒明析",
        "avatar_char": "舒",
        "avatar_emoji": "📈",
        "cat": "数据智能",
        "desc": "将复杂数据转化为战略洞察，提供指标诊断、KPI框架设计与决策报告",
        "tags": ["数据洞察", "指标诊断", "KPI体系", "漏斗分析"],
        "default_prompt": "请帮我为当前业务增长漏斗设计一套核心监控 KPI 体系与数据洞察报告。",
        "system_prompt": """你是一名高级商业智能与数据分析总监。
精通增长漏斗模型、留存归因、A/B测试设计与商业数据可视化看板。"""
    },
    "stock_researcher": {
        "id": "stock_researcher",
        "name": "股票研究专家",
        "alias": "严选深",
        "avatar_char": "严",
        "avatar_emoji": "📉",
        "cat": "金融投资",
        "desc": "全面的股票研究工具集：财报分析、首次覆盖报告、DCF与可比估值与投资决策",
        "tags": ["证券研究", "财报分析", "DCF估值", "投资决策"],
        "default_prompt": "请基于最新财报数据为科技行业的头部公司做一次基本面与 DCF 估值分析。",
        "system_prompt": """你是一名持牌证券研究所首席行业分析师。
精通杜邦财务拆解、现金流折现（DCF）建模、可比公司估值法与投资评级报告。"""
    },
    "startup_partner": {
        "id": "startup_partner",
        "name": "创业伙伴",
        "alias": "林正刚",
        "avatar_char": "林",
        "avatar_emoji": "🤝",
        "cat": "OPC一人公司",
        "desc": "杨老师分身+读书伙伴。读《创业可以学》，陪创业者读书，解决痛点与GTM落地",
        "tags": ["一人公司", "创业心法", "商业闭环", "GTM落地"],
        "default_prompt": "我想开启一个一人 AI 工具公司的创业项目，请帮我梳理第一阶段的核心商业闭环。",
        "system_prompt": """你是一名经验丰富的连续创业者与 OPC 一人公司实战导师。
擅长指导 0-1 商业模式闭环验证、PMF 寻找、冷启动 GTM 策略与极简成本控制。"""
    },
    "doc_editor": {
        "id": "doc_editor",
        "name": "长文档写作与改稿专家",
        "alias": "谢笔手",
        "avatar_char": "福",
        "avatar_emoji": "📑",
        "cat": "办公提效",
        "desc": "把提纲、访谈、旧书和素材整理成清晰的长文档，支持章节排版与前置检查",
        "tags": ["长文档工程", "PRD写作", "逻辑校验", "排版润色"],
        "default_prompt": "请帮我将以下零散的产品设计思路整理为一份结构严密的产品需求文档 (PRD)。",
        "system_prompt": """你是一名资深文档工程与文字总监。
精通长篇 PRD 产品需求文档、行业调研白皮书、章节结构化编排与严谨逻辑一致性校对。"""
    },
    "legal_expert": {
        "id": "legal_expert",
        "name": "资深合同法务专家",
        "alias": "法务顾问",
        "avatar_char": "法",
        "avatar_emoji": "⚖️",
        "cat": "法律咨询",
        "desc": "精通民商事合同起草、合规审查、知识产权保护与法律风险前置排查。",
        "tags": ["合同审查", "法务合规", "知识产权", "劳动人事"],
        "default_prompt": "请帮我起草一份软件开发技术服务合同，重点规避交付延期与知识产权争议风险。",
        "system_prompt": """你是一名拥有 15 年经验的资深企业商事法务总监与律所合伙人。
精通《民法典》合同编、劳动争议、知识产权归属保护、违约赔偿责任界定与法律风险前置排查。"""
    }
}

TOOL_FRIENDLY_MAP = {
    "get_trending_news": "全网热搜与科技要闻",
    "search_web_news": "实时全网热点资讯",
    "search_web": "网络在线实时搜索",
    "get_screen_and_system_info": "系统与屏幕状态检测",
    "take_screenshot": "屏幕实时截图分析",
    "execute_python_code": "Python 代码解释器",
    "generate_presentation_ppt": "PPT 演示演讲大纲架构",
    "generate_xiaohongshu_note": "小红书爆款图文创作",
    "query_knowledge_base": "本地私有知识库检索",
    "amap_route_planning": "高德地图路线导航规划",
    "kuaidi_query": "快递物流轨迹查询",
    "ticket_12306": "12306 火车票实时检索",
    "read_file": "工作区文件深度读取",
    "write_file": "本地文件保存与写入",
    "search_files": "工作区文件全局检索",
    "write_workspace_file": "工作区代码文件写入与追踪",
    "read_workspace_file": "工作区代码文件读取",
    "list_workspace_files": "工作区文件目录检索",
    "run_workspace_command": "工作区终端命令沙箱执行",
    "computer_control": "桌面系统自动化控制",
    "web_dev_preview": "Web 前端代码实时预览",
    "markdownify": "网页 Markdown 提取转换",
}


def get_tool_friendly_name(tool_name: str) -> str:
    """获取工具的友好中文显示名称"""
    if not tool_name:
        return "本地自动化工具"
    t_key = tool_name.lower().strip()
    if t_key in TOOL_FRIENDLY_MAP:
        return TOOL_FRIENDLY_MAP[t_key]
    return t_key.replace("_", " ").title()


def is_vision_capable(model_name: str = "") -> bool:
    """判断指定模型名是否具备视觉多模态分析能力"""
    name = (model_name or "").lower().strip()
    vision_keywords = [
        "vision", "vl", "gpt-4o", "gpt-4-turbo", "gpt-4-vision", 
        "claude-3", "claude-4", "gemini", "llava", "omni",
        "qwen2.5-vl", "qwen-vl", "qwen2-vl", "minicpm-v", "internvl", "deepseek-vl"
    ]
    return any(k in name for k in vision_keywords)


class AIEngine:
    """DeskAI 核心大模型与多智能体执行引擎"""

    def __init__(self, config: dict):
        self.config = config
        self.provider = "ollama"
        self.model_name = "deepseek-r1:14b"
        self.api_base_url = "http://localhost:11434"
        self.api_key = ""
        self.system_prompt = config.get("system_prompt", "你是一个全能的桌面 AI 智能体助理。")

        self.memory = None
        self.emotion = None
        self.plugins = None
        self.conversation_history: List[Dict[str, str]] = []
        self.session_histories: Dict[str, List[Dict[str, str]]] = {}

        # 启动时严格按 active_model_id 初始化模型配置，防止配置漂移
        self.reload_config(config)

    def set_dependencies(self, memory, emotion, plugins):
        self.memory = memory
        self.emotion = emotion
        self.plugins = plugins

    def reload_config(self, config: dict):
        """动态热重载完整应用配置与大模型端点参数"""
        self.config = config
        active_id = config.get("active_model_id", "")
        models_list = config.get("models_list", [])
        active_m = next((m for m in models_list if m.get("id") == active_id), None)
        
        if active_m:
            self.set_active_model(active_m)
            return

        ai_cfg = config.get("ai", {})
        self.provider = ai_cfg.get("provider", config.get("provider", "ollama"))
        if self.provider == "ollama":
            ollama_cfg = ai_cfg.get("ollama", {})
            self.model_name = ollama_cfg.get("chat_model", "deepseek-r1:14b")
            self.api_base_url = ollama_cfg.get("api_base") or ollama_cfg.get("base_url") or "http://localhost:11434"
            self.api_key = ""
        else:
            custom_cfg = ai_cfg.get("custom", {})
            self.model_name = custom_cfg.get("chat_model", "deepseek:deepseek/deepseek-v4-flash-vision-exp")
            self.api_base_url = custom_cfg.get("api_base") or custom_cfg.get("base_url") or "https://api.ohmygpt.com/v1"
            self.api_key = custom_cfg.get("api_key", "")
        print(f"[AIEngine] 重载配置成功 -> Provider: {self.provider}, Model: {self.model_name}, URL: {self.api_base_url}")

    def set_active_model(self, model_config: dict):
        """动态实时热重载大模型参数与连接端点（100% 内存即时替换）"""
        self.provider = model_config.get("provider", "ollama")
        self.model_name = model_config.get("model_name", "deepseek-r1:14b")
        self.api_base_url = model_config.get("api_base_url") or model_config.get("api_base") or model_config.get("base_url") or "http://localhost:11434"
        self.api_key = model_config.get("api_key", "")
        print(f"[AIEngine] [OK] 核心模型已 100% 内存热切换 -> Provider: {self.provider}, Model: {self.model_name}, BaseURL: {self.api_base_url}")

    def is_vision_capable(self, model_name: str = "") -> bool:
        """判断当前或指定模型是否具备视觉多模态分析能力"""
        name = (model_name or self.model_name or "").lower().strip()
        if is_vision_capable(name):
            return True
        ai_cfg = self.config.get("ai", {})
        if ai_cfg.get("ollama", {}).get("vision_model", "").lower() == name:
            return True
        for m in self.config.get("models_list", []):
            if m.get("model_name", "").lower() == name or m.get("id") == self.config.get("active_model_id"):
                if m.get("is_vision") or m.get("vision"):
                    return True
        return False

    def _extract_expert_id(self, message: str) -> str:
        """从消息中提取绑定的专家角色 ID"""
        m = re.search(r'专家角色:\s*([a-zA-Z0-9_-]+)', message)
        if m:
            return m.group(1).strip()
        return ""

    def _get_enabled_skills_prompt(self) -> str:
        """扫描当前工作区 skills/ 目录下所有已启用技能，提取并注入其工作流规则与最佳实践"""
        try:
            from pathlib import Path
            root_dir = Path(__file__).resolve().parent.parent
            skills_dir = root_dir / "skills"
            if not skills_dir.exists():
                return ""

            enabled_skills = set(self.config.get("plugins", {}).get("enabled", []))
            skill_prompts = []
            for s_dir in sorted(skills_dir.iterdir()):
                if not s_dir.is_dir():
                    continue
                skill_id = s_dir.name
                # 如果配置中有启用列表且该技能未启用，则跳过
                if enabled_skills and skill_id not in enabled_skills:
                    continue
                skill_md = s_dir / "SKILL.md"
                if not skill_md.exists():
                    continue
                try:
                    content = skill_md.read_text(encoding="utf-8")
                    name = skill_id
                    desc = ""
                    body = content
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            for line in parts[1].splitlines():
                                if line.startswith("name:"):
                                    name = line[5:].strip().strip('"\'')
                                elif line.startswith("description:"):
                                    desc = line[12:].strip().strip('"\'')
                            body = parts[2].strip()
                    skill_prompts.append(
                        f"### [技能套件: {name} (ID: {skill_id})]\n"
                        f"- 技能说明: {desc}\n"
                        f"- 执行指引与工作流要求:\n{body[:800]}\n"
                    )
                except Exception:
                    continue

            if not skill_prompts:
                return ""

            return (
                "\n[工作空间激活技能 (Workspace Skills) 规范与工作流指引 - 必须深度遵从]:\n"
                "当前工作空间已成功装配并激活以下专业技能套件，遇到对应任务时必须严格执行其规范：\n\n"
                + "\n".join(skill_prompts)
            )
        except Exception:
            return ""

    def _build_full_prompt(self, user_message: str, expert_id: str = "", persona_prompt: str = "", system_prompt_override: str = "") -> str:
        # 动态扫描并挂载 MCP 工具
        try:
            from core.mcp_tool_bridge import MCPToolBridge
            MCPToolBridge.get_instance().mount_all_mcp_tools()
        except Exception:
            pass

        if system_prompt_override:
            prompt_parts = [system_prompt_override]
        elif persona_prompt:
            prompt_parts = [persona_prompt]
        elif expert_id and expert_id in EXPERTS_MAP:
            prompt_parts = [EXPERTS_MAP[expert_id]["system_prompt"]]
        else:
            prompt_parts = [self.system_prompt]

        # 注入工作区已激活技能 (Skills) 规范与工作流指导
        skills_prompt = self._get_enabled_skills_prompt()
        if skills_prompt:
            prompt_parts.append(skills_prompt)

        now = datetime.now()
        weekday_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        time_info = (
            f"\n[系统环境真实时间信息]:\n"
            f"- 当前真实系统时间: {now.strftime('%Y年%m月%d日')} {weekday_map[now.weekday()]} {now.strftime('%H:%M:%S')} (东八区/北京时间)\n"
            f"- 当前年份: {now.year} 年\n"
            f"- 当前月份: {now.month} 月\n"
            f"- 当前日期: {now.day} 日\n"
            f"【核心硬性准则】：当用户询问今天日期、几号、星期几或历史上的今天（即历史上在 {now.month}月{now.day}日 发生的大事）时，"
            f"必须严格基于上述真实系统日期（{now.year}年{now.month}月{now.day}日）进行精准回答，严禁臆造或输出过期的训练截止日期！"
        )
        prompt_parts.append(time_info)

        # 注入用户档案与持久记忆（确保无论切换哪位专家或默认助理，用户记忆永远永久生效！）
        user_name = (self.config.get("user_name") or "").strip()
        user_memo = (self.config.get("user_memo") or "").strip()
        user_rules = (self.config.get("user_rules") or self.config.get("custom_rules") or "").strip()

        if user_name or user_memo:
            profile_lines = []
            if user_name:
                profile_lines.append(f"- 用户的昵称是「{user_name}」，请你称呼他/她「{user_name}」。")
            if user_memo:
                profile_lines.append(f"- 关于这位用户的持久记忆与背景偏好：{user_memo}")
            prompt_parts.append("\n[用户档案与永久记忆 - 永久生效]:\n" + "\n".join(profile_lines))

        # 注入用户设定的核心规则与不可逾越红线（最高约束力）
        if user_rules:
            rules_block = (
                f"\n[用户自定义核心规则与强制红线 - 必须最高优先级无条件严格执行]:\n"
                f"用户为你设定了以下行为准则、输出要求与不可触碰的红线约束，你在所有对话、代码编写与任务执行中必须严格遵守：\n"
                f"{user_rules}\n"
                f"【红线效力准则】：若上述规则与任何通用回复习惯产生冲突，必须以用户设定的上述规则与红线为最高标准执行！"
            )
            prompt_parts.append(rules_block)

        if self.emotion:
            try:
                if hasattr(self.emotion, "get_current_emotion"):
                    emo_str = self.emotion.get_current_emotion()
                elif hasattr(self.emotion, "current_emotion"):
                    emo_val = self.emotion.current_emotion
                    emo_str = emo_val.value if hasattr(emo_val, "value") else str(emo_val)
                else:
                    emo_str = "待命 (idle)"
                prompt_parts.append(f"\n[当前心情状态]: {emo_str}")
            except Exception:
                pass

        is_plan_mode = self._is_planning_intent(user_message)
        if self.plugins and not is_plan_mode:
            try:
                tool_desc = self.plugins.get_tool_descriptions()
                if tool_desc:
                    prompt_parts.append(
                        f"\n[已挂载MCP工具列表]:\n{tool_desc}\n\n"
                        "【工具调用规范】：当你需要使用上述工具执行操作或检索信息时，请输出工具调用代码块：\n"
                        "```tool\n"
                        '{"name": "工具名称", "args": {"参数名": "参数值"}}\n'
                        "```\n"
                        "系统会自动执行工具并将真实结果注入上下文供你生成最终回复。如果不需要使用工具，请直接正常回答。"
                    )
            except Exception:
                pass

        # 代码与指令片段高质感包装规范（统一卡片化展示与语法高亮）
        code_formatting_rule = (
            "\n[代码与指令片段排版包装规范 - 强制执行]:\n"
            "1. 严禁直接输出裸露未包裹的代码、脚本、配置文件或终端指令！\n"
            "2. 所有代码片段与终端命令必须使用标准 Markdown 三反引号代码块包裹，并在第一行反引号后明确注明语言标识符：\n"
            "   - Python 脚本/代码片段必须声明为 ```python（严禁使用裸文本）；\n"
            "   - Linux 终端命令/Shell 操作/安装指令必须声明为 ```bash 或 ```sh（例如 ```bash\\nsudo systemctl restart nginx\\n```）；\n"
            "   - Java/C/C++/Go 等语言声明对应标识符（```java, ```c, ```cpp, ```go 等）；\n"
            "   - 配置文件与结构化数据声明对应格式（```json, ```yaml, ```sql, ```html, ```css 等）。\n"
            "3. 解释说明中提及的变量名、函数名、类名、注解、命令参数等行内标识符，必须使用行内代码反引号包裹（例如 `switch-case`, `python -m venv`, `curl -I`, `@Component`, `systemctl`）。\n"
            "4. 代码与指令排版务必结构清晰，保留规范的缩进与精炼注释，确保前端界面能自动提取语言标签并呈现极客高亮卡片与一键复制。"
        )
        prompt_parts.append(code_formatting_rule)

        # 工作空间代码开发模式与文件落地规范
        try:
            from core.security_guard import SecurityGuard
            ws_root = SecurityGuard.get_instance().workspace_root
            if ws_root and Path(ws_root).exists():
                prompt_parts.append(
                    f"\n[当前激活工作空间根目录]: `{ws_root}`\n"
                    "【工作空间代码开发与落地规范 - 强制严格执行】：\n"
                    f"1. 当前用户绑定的项目工作空间绝对路径为: `{ws_root}`。\n"
                    f"2. 当用户要求你在当前工作空间中编写代码、创建脚本、修改文件或执行已批准的落地计划时，你必须在该工作空间（`{ws_root}`）下操作！\n"
                    "3. 严禁在软件安装目录或其他未知目录中创建文件！必须调用 `write_workspace_file` 工具写入真实代码文件（传入相对于工作空间的相对路径，例如 'calc_tool.py' 或 'src/main.py'）；\n"
                    "4. 严禁仅用自然语言空泛承诺'我将通过本地沙箱执行'，有文件落地需求时，必须直接输出工具调用指令块调用 `write_workspace_file`；\n"
                    "5. 每次写入代码时，系统会自动捕获变更前后代码差异 (Diff)，并在前端呈现代码变更卡片与红绿双色差异对比；\n"
                    "6. 若用户仅要求你提供方案思路或概念代码示例（未要求落地保存），可直接在正文中用规范 Markdown 代码块回答。"
                )
        except Exception:
            pass

        return "\n".join(prompt_parts)

    @staticmethod
    def _is_planning_intent(text: str) -> bool:
        """多维度意图识别：检测用户是否处于或请求计划模式 (Plan-then-Execute)"""
        if not text:
            return False
        t = text.strip().lower()

        # 若为明确的执行落地/批准执行指令，必须直接判定为 False，绝不拦截工具调用
        if any(k in t for k in [
            "【用户已确认接收并批准", "已确认接收并批准", "立即按方案分步执行落地",
            "执行落地", "开始执行", "批准并立即执行", "proceed", "开始落地", "按方案执行",
            "我已审阅并正式批准"
        ]):
            return False

        if any(k in t for k in [
            "当前处于「计划模式", "先制定完整实施计划",
            "plan-then-execute", "plan mode", "计划模式", "/plan"
        ]):
            return True
        # 正则1: 先/首先/提前/请先 ... 计划/方案/规划/文档/架构 ... 再/然后/之后/后/确认/审核/批准/同意 ... 执行/做/实现/落地/编写/写/代码/实施/动手
        if re.search(r'(先|首先|提前|请先).*(计划|方案|规划|文档|架构).*(再|然后|之后|后|确认|审核|批准|同意).*(执行|做|实现|落地|编写|写|代码|实施|动手)', t, re.DOTALL):
            return True
        # 正则2: 先/首先/提前/请先 ... 生成/制定/出/写/做/设计/提供/给 ... 计划/方案/规划/文档
        if re.search(r'(先|首先|提前|请先).*(生成|制定|出|写|做|设计|提供|给).*(计划|方案|规划|文档)', t, re.DOTALL):
            return True
        # 正则3: 生成/制定/编写/出 ... 实施方案/实施计划/计划文档/执行方案/落地方案
        if re.search(r'(生成|制定|编写|出|写).*(实施方案|实施计划|计划文档|执行方案|落地方案|落地规划)', t, re.DOTALL):
            return True
        plan_keywords = [
            "先制定计划", "先做计划", "先写规划", "先出方案", "先做规划", "先写方案", "先做方案",
            "等我同意", "等我确认", "先写好计划", "编写好计划", "先出计划", "先设计",
            "制定实施计划", "出个方案再做", "先设计好方案再执行", "先制定方案", 
            "先制定好计划后再执行", "制定好计划后再执行", "先制定计划后再执行",
            "先生成计划", "生成计划文档", "生成实施方案", "出个实施方案", "制定实施方案",
            "先规划再实现", "先规划再写代码", "先写计划再执行", "先出计划再执行",
            "先出计划文档", "先给计划文档", "先出规划", "实施方案预览"
        ]
        return any(k in t for k in plan_keywords)


    def _parse_all_tool_calls(self, text: str) -> List[Tuple[str, dict]]:
        """解析大模型回复中的所有工具调用请求（支持并行多工具调用、连续 JSON 块与嵌套参数）"""
        if not text:
            return []

        results: List[Tuple[str, dict]] = []
        seen = set()

        # 1. 匹配所有 ```tool ... ``` 或 ```json ... ``` 代码块
        block_patterns = [
            r'```(?:tool|json)?\s*(\{[\s\S]*?\})\s*```',
            r'TOOL:\s*([a-zA-Z0-9_-]+)\s*(\{[\s\S]*?\})'
        ]
        for pat in block_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                if len(m.groups()) == 2:
                    t_name, json_str = m.group(1), m.group(2)
                    try:
                        args = json.loads(json_str)
                        key = (t_name.strip(), json.dumps(args, sort_keys=True))
                        if key not in seen:
                            seen.add(key)
                            results.append((t_name.strip(), args if isinstance(args, dict) else {}))
                    except Exception:
                        pass
                elif len(m.groups()) == 1:
                    json_str = m.group(1)
                    try:
                        data = json.loads(json_str)
                        if isinstance(data, dict):
                            t_name = data.get("name") or data.get("tool") or data.get("tool_name") or data.get("function")
                            args = data.get("args") or data.get("parameters") or data.get("params") or {}
                            if t_name and isinstance(t_name, str):
                                key = (t_name.strip(), json.dumps(args, sort_keys=True))
                                if key not in seen:
                                    seen.add(key)
                                    results.append((t_name.strip(), args if isinstance(args, dict) else {}))
                    except Exception:
                        pass

        # 2. 精确平衡括号遍历全文，捕获所有行首/文中的独立 JSON 工具调用（防止漏掉第2、第3个工具）
        n = len(text)
        i = 0
        while i < n:
            if text[i] == '{':
                snippet = text[i:min(n, i + 60)]
                if any(k in snippet for k in ['"name"', '"tool"', '"tool_name"', '"function"']):
                    depth = 0
                    j = i
                    in_str = False
                    escape = False
                    while j < n:
                        ch = text[j]
                        if in_str:
                            if escape:
                                escape = False
                            elif ch == '\\':
                                escape = True
                            elif ch == '"':
                                in_str = False
                        else:
                            if ch == '"':
                                in_str = True
                            elif ch == '{':
                                depth += 1
                            elif ch == '}':
                                depth -= 1
                                if depth == 0:
                                    raw_json = text[i:j+1]
                                    try:
                                        data = json.loads(raw_json)
                                        if isinstance(data, dict):
                                            t_name = data.get("name") or data.get("tool") or data.get("tool_name") or data.get("function")
                                            args = data.get("args") or data.get("parameters") or data.get("params") or {}
                                            if t_name and isinstance(t_name, str):
                                                key = (t_name.strip(), json.dumps(args, sort_keys=True))
                                                if key not in seen:
                                                    seen.add(key)
                                                    results.append((t_name.strip(), args if isinstance(args, dict) else {}))
                                    except Exception:
                                        pass
                                    i = j
                                    break
                        j += 1
            i += 1

        return results

    def _parse_tool_call(self, text: str) -> Optional[Tuple[str, dict]]:
        """向后兼容：返回大模型回复中的首个工具调用"""
        calls = self._parse_all_tool_calls(text)
        return calls[0] if calls else None

    async def _call_tool_safely(self, func, *args, **kwargs) -> str:
        try:
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        except Exception as e:
            return f"❌ 工具执行异常: {e}"

    async def _fast_local_route(self, user_message: str) -> Optional[str]:
        """确定性基础系统信息直答（仅支持当前真实系统时间/日期与屏幕信息）"""
        clean_msg = user_message.strip()
        now = datetime.now()
        weekday_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

        # 精准回答当前系统真实时间与日期问题 (100% 真实时间)
        time_queries = ["今天几号", "今天几月几号", "今天是多少号", "今天的日期", "今天日期", "现在几点", "现在时间", "今天星期几", "今天周几", "今天是几号"]
        pure_clean = re.sub(r'【[^】]*】', '', clean_msg).strip()
        if pure_clean in time_queries or any(pure_clean == q for q in time_queries):
            return f"今天是 **{now.strftime('%Y年%m月%d日')}**，**{weekday_map[now.weekday()]}**，当前真实系统时间为 **{now.strftime('%H:%M:%S')}**。"

        # 屏幕与系统状态快照
        if any(k == clean_msg for k in ["截图", "截屏", "获取屏幕"]):
            try:
                from plugins.computer_control import get_screen_and_system_info
                return await self._call_tool_safely(get_screen_and_system_info)
            except Exception:
                pass

        return None

    def _record_history(self, user_msg: Any, ai_msg: str, session_id: str = ""):
        """记录多会话隔离的历史消息（自动将多模态消息转换为纯文本以节省历史 Token）"""
        if isinstance(user_msg, list):
            user_text = ""
            for item in user_msg:
                if isinstance(item, dict) and item.get("type") == "text":
                    user_text = item.get("text", "")
            user_msg = user_text or "[用户附带图片]"

        if session_id:
            self.session_histories.setdefault(session_id, []).append({"role": "user", "content": user_msg})
            self.session_histories[session_id].append({"role": "assistant", "content": ai_msg})
            if len(self.session_histories[session_id]) > 40:
                self.session_histories[session_id] = self.session_histories[session_id][-40:]

        self.conversation_history.append({"role": "user", "content": user_msg})
        self.conversation_history.append({"role": "assistant", "content": ai_msg})
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]

    def _get_trimmed_messages(self, system_prompt: str, user_message: str, session_id: Optional[str] = None, image_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """构建多会话隔离的滑动窗口消息列表（保留系统设定 + 目标会话最近 10 轮历史 + 当前提问，支持视觉多模态）"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 严格使用指定 session_id 的独立历史
        if session_id:
            sid_str = str(session_id)
            history = self.session_histories.get(sid_str, [])
        else:
            history = self.conversation_history

        # 滑动窗口预算保护：从最新历史往回逆向取，最多保留 16000 字符历史，防止多轮后撑爆上下文窗口
        max_history_chars = 16000
        accumulated_chars = 0
        safe_history = []
        for msg in reversed(history[-20:]):
            content = msg.get("content", "")
            c_len = len(content) if isinstance(content, str) else 200
            if safe_history and (accumulated_chars + c_len > max_history_chars):
                break
            safe_history.append(msg)
            accumulated_chars += c_len
        safe_history.reverse()

        for msg in safe_history:
            messages.append(msg)

        has_image = bool(image_path and Path(image_path).exists() and Path(image_path).is_file())
        if has_image and self.is_vision_capable():
            try:
                import base64
                img_bytes = Path(image_path).read_bytes()
                # 针对超大图片做等比缩放以提高传输效率
                try:
                    from PIL import Image
                    import io
                    im = Image.open(io.BytesIO(img_bytes))
                    if max(im.size) > 2048:
                        im.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                        out_io = io.BytesIO()
                        fmt = im.format or "JPEG"
                        im.save(out_io, format=fmt, quality=90)
                        img_bytes = out_io.getvalue()
                except Exception:
                    pass

                b64_str = base64.b64encode(img_bytes).decode("utf-8")
                suffix = Path(image_path).suffix.lower().lstrip(".")
                mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif", "bmp": "image/bmp"}
                mime_type = mime_map.get(suffix, "image/jpeg")

                if self.provider == "ollama":
                    messages.append({
                        "role": "user",
                        "content": user_message or "请分析识别此图片内容。",
                        "images": [b64_str]
                    })
                else:
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_message or "请详细分析识别这张图片中的视觉细节与关键信息。"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{b64_str}"
                                }
                            }
                        ]
                    })
            except Exception as e:
                print(f"[AIEngine] 视觉多模态图片编码异常: {e}")
                if user_message:
                    messages.append({"role": "user", "content": user_message})
        else:
            if user_message:
                messages.append({"role": "user", "content": user_message})

        return messages

    async def chat_stream(self, user_message: str, session_id: Optional[str] = None, **kwargs) -> AsyncGenerator[str, None]:
        """流式主入口：支持确定性直答、多轮 ReAct 工具调用、视觉多模态与多会话严格隔离"""
        sid_str = str(session_id) if session_id else ""
        image_path = kwargs.get("image_path")
        has_image = bool(image_path and Path(image_path).exists() and Path(image_path).is_file())
        has_vision = self.is_vision_capable() if has_image else False

        # 1. 基础确定性信息直答 (若附带图片则跳过本地直答，交由大模型图像识别)
        if not has_image:
            fast_reply = await self._fast_local_route(user_message)
            if fast_reply is not None:
                self._record_history(user_message, fast_reply, sid_str)
                lines = fast_reply.splitlines(keepends=True)
                for line in lines:
                    yield line
                    await asyncio.sleep(0.01)
                return

        # 2. 真实大模型端点调用与多轮工具调用执行循环
        expert_id = self._extract_expert_id(user_message)
        persona_prompt = kwargs.get("persona_prompt", "")
        system_prompt_override = kwargs.get("system_prompt_override", "")

        # 若用户附带了图片但当前模型不具备视觉多模态能力：注入强约束系统提示词
        non_vision_prompt = ""
        if has_image and not has_vision:
            img_name = Path(image_path).name
            model_disp = self.model_name
            non_vision_prompt = (
                f"\n\n【用户上传图片附件与纯文本模型限制说明 - 必须严格执行】:\n"
                f"检测到用户在本次提问中上传了一张图片（文件: `{img_name}`）。\n"
                f"但你当前运行的模型端点（`{model_disp}`）为纯文本模型，不具备多模态视觉图像识别 (Vision/Multimodal) 接口，无法直接获取图片像素并解析视觉细节。\n"
                f"【强制回复格式与执行要求】:\n"
                f"1. 你的回答开头第一句话必须友好且清晰地明确告知用户：“检测到您上传了图片「{img_name}」，但当前运行的模型（`{model_disp}`）暂不具备视觉多模态能力，无法直接解析图片细节。不过我已针对您的文字需求进行了分析，解答如下：”；\n"
                f"2. 紧接着，必须完全基于用户输入的文字需求进行深入、严谨、详尽的代码编写与方案解答；\n"
                f"3. 保持热情和专业度，绝对严禁因无法看图而中断回复或拒绝解答用户的文字需求！"
            )

        full_system_prompt = self._build_full_prompt(
            user_message, expert_id, persona_prompt=persona_prompt, system_prompt_override=system_prompt_override
        )
        if non_vision_prompt:
            full_system_prompt += non_vision_prompt

        messages = self._get_trimmed_messages(full_system_prompt, user_message, session_id=sid_str, image_path=image_path)

        # 开发模式任务支持多轮自主探索、执行与报错自愈（最多 8 轮）
        is_dev_mode = (sid_str == "dev_ide_task" or sid_str.startswith("dev_"))
        max_rounds = 8 if is_dev_mode else 3
        current_round = 0
        final_answer = ""

        try:
            while current_round < max_rounds:
                current_round += 1
                round_output = ""
                
                stream_func = self._stream_ollama_messages if self.provider == "ollama" else self._stream_openai_compatible_messages
                
                # 严格基于当前用户输入的意图判断是否为纯计划模式（绝不被历史轮次中的方案残留标记死锁）
                is_plan_mode = self._is_planning_intent(user_message)

                # 全轮次均支持大模型输出工具调用指令代码块（普通聊天计划模式除外，Dev模式下允许探索与写方案文件）
                is_potential_tool_round = bool(self.plugins)
                if is_plan_mode and not is_dev_mode:
                    is_potential_tool_round = False
                intercept_tool_json = False
                pre_buffer = ""

                async for chunk in stream_func(messages):
                    round_output += chunk
                    
                    if is_potential_tool_round:
                        # 1. 若当前正处于 <think> 思考链中，严禁拦截或缓冲，立即把真实思考过程流式输出给前端
                        if "<think>" in round_output and "</think>" not in round_output:
                            if pre_buffer:
                                yield pre_buffer
                                pre_buffer = ""
                            yield chunk
                            continue

                        # 2. 如果当前 chunk 包含 </think>，把 </think> 及之前部分立即吐出，之后部分送入 pre_buffer 探测
                        if "</think>" in chunk:
                            parts = chunk.split("</think>", 1)
                            think_close_part = parts[0] + "</think>"
                            yield think_close_part
                            pre_buffer += parts[1]
                        else:
                            pre_buffer += chunk

                        if not intercept_tool_json:
                            stripped = pre_buffer.lstrip()
                            # 检测是否出现工具调用 JSON 标记
                            if any(k in pre_buffer for k in ['{"name"', '{"tool"', '```tool', '```json', 'TOOL:']):
                                intercept_tool_json = True
                            elif len(stripped) > 0:
                                # 若首个非空白字符根本不是 {、`、T、t，断定绝非工具调用，立即释放缓冲区并放行后续全部流式
                                if not any(stripped.startswith(k) for k in ('{', '`', 'TOOL', 'tool')):
                                    is_potential_tool_round = False
                                    if pre_buffer:
                                        yield pre_buffer
                                        pre_buffer = ""
                                    continue
                                elif stripped.startswith("```"):
                                    # 如果已累积出语言标签（比如 ```java、```python、```bash 等），且不是 tool/json，断定为正文代码
                                    first_line = stripped.splitlines()[0] if "\n" in stripped else ""
                                    if first_line and not any(first_line.startswith(k) for k in ('```tool', '```json')):
                                        is_potential_tool_round = False
                                        if pre_buffer:
                                            yield pre_buffer
                                            pre_buffer = ""
                                        continue
                                elif stripped.startswith("{") and len(stripped) >= 35:
                                    # 累积超过 35 字符仍无 name/tool/function 键，非标准工具调用
                                    if not any(k in stripped for k in ('"name"', '"tool"', '"function"')):
                                        is_potential_tool_round = False
                                        if pre_buffer:
                                            yield pre_buffer
                                            pre_buffer = ""
                                        continue
                    else:
                        yield chunk

                # 若当前轮流式完毕且未检测到工具调用特征，将缓冲区剩余普通文字全部吐出
                if is_potential_tool_round and not intercept_tool_json and pre_buffer:
                    yield pre_buffer

                # 检查大模型是否触发了工具调用（方案制定模式下严禁写入代码或执行终端命令，仅允许只读探测）
                if is_plan_mode:
                    if is_dev_mode:
                        raw_calls = self._parse_all_tool_calls(round_output) if self.plugins else []
                        # 方案制定阶段只允许只读探测，杜绝提前写文件或执行命令
                        tool_calls = [
                            (t_name, t_args) for (t_name, t_args) in raw_calls
                            if t_name in ("read_workspace_file", "list_workspace_files")
                        ]
                    else:
                        tool_calls = []
                else:
                    tool_calls = self._parse_all_tool_calls(round_output) if self.plugins else []
                if tool_calls:
                    executed_results = []
                    # 组合多个工具的友好中文名称
                    names_summary = "、".join([get_tool_friendly_name(t[0]) for t in tool_calls])
                    primary_name = tool_calls[0][0]

                    # 发送运行中状态卡片标记（展示所有正在执行的工具）
                    yield f"\n\n:::tool_call:running:{primary_name}:{names_summary}:::\n\n"

                    # 依次执行所有工具并收集真实数据
                    for t_name, t_args in tool_calls:
                        try:
                            tool_res = await self.plugins.call_tool(t_name, **t_args)
                        except Exception as te:
                            tool_res = f"❌ 工具执行错误: {te}"
                        executed_results.append((t_name, tool_res))
                        # 若工具返回包含 WORKSPACE_EXPLORE、WORKSPACE_DIFF 或 WORKSPACE_CMD 标记，实时在流中向前端输出
                        if isinstance(tool_res, str):
                            if "[[WORKSPACE_EXPLORE:" in tool_res:
                                for exp_line in re.findall(r'(\[\[WORKSPACE_EXPLORE:[^\]]+\]\])', tool_res):
                                    yield f"\n{exp_line}\n"
                            if "[[WORKSPACE_DIFF:" in tool_res:
                                for diff_line in re.findall(r'(\[\[WORKSPACE_DIFF:[^\]]+\]\])', tool_res):
                                    yield f"\n{diff_line}\n"
                            if "[[WORKSPACE_CMD:" in tool_res:
                                for cmd_line in re.findall(r'(\[\[WORKSPACE_CMD:[^\]]+\]\])', tool_res):
                                    yield f"\n{cmd_line}\n"

                    # 发送执行完成状态卡片标记
                    yield f"\n\n:::tool_call:done:{primary_name}:{names_summary}:::\n\n"

                    # 构建包含所有工具真实数据的提示上下文
                    result_blocks = []
                    for idx, (t_name, t_res) in enumerate(executed_results, 1):
                        f_name = get_tool_friendly_name(t_name)
                        result_blocks.append(f"【工具 {idx}（{f_name} / `{t_name}`）执行返回数据】：\n{t_res}")
                    all_results_str = "\n\n".join(result_blocks)

                    # 将工具调用过程与全部真实数据注入上下文，驱动下一轮生成完整回答
                    messages.append({"role": "assistant", "content": round_output})
                    if sid_str == "dev_ide_task" or sid_str.startswith("dev_"):
                        dev_guidance = (
                            f"【系统提示：工作空间沙箱工具执行完毕，真实返回数据如下】：\n\n"
                            f"{all_results_str}\n\n"
                            f"【开发模式自主闭环与报错自愈准则】：\n"
                            f"1. 【报错自愈 (Auto-Healing)】：请仔细检查上述终端沙箱与文件执行输出。若返回了非 0 退出码或 Traceback / 报错（如 ImportError、AssertionError、SyntaxError、运行期异常），说明编写的代码存在缺陷，你必须自主分析原因并启动自愈重试：输出 ```tool ... ``` 代码块调用 `write_workspace_file` 修复代码，并再次调用 `run_workspace_command` 重新执行测试，直到退出码为 0 测试全部通过！\n"
                            f"2. 【连续任务执行】：若需继续阅读切片、列出文件或执行后续构建/测试命令，请继续输出 ```tool ... ``` 工具块；\n"
                            f"3. 【完成总结】：若所有编写与测试任务均已顺利完成（沙箱命令退出码为 0），请输出简要的架构方案小结与测试通过说明。严禁在正文中倾倒数十行完整源码（系统已自动在主屏幕编辑器中打开）。"
                        )
                        messages.append({
                            "role": "user",
                            "content": dev_guidance
                        })
                    else:
                        messages.append({
                            "role": "user",
                            "content": (
                                f"【系统提示：您所请求的所有工具已全部在后台执行完毕，真实数据汇总如下】：\n\n"
                                f"{all_results_str}\n\n"
                                f"【回复准则】：请充分整合上述所有工具返回的真实数据，一次性为用户输出完整、详尽、分类清晰的最终解答。"
                                f"必须完整包含用户请求的所有主题（如全网热搜看点与最新科技动态等），严禁输出“正在检索”、“稍等片刻”等等待性质的过渡语，所有内容直接在本次回答中完整呈现。"
                            )
                        })
                    continue
                else:
                    # 彻底清洗可能残留在最终回答中的未执行工具 JSON 字符块，杜绝 raw JSON 裸露
                    clean_res = re.sub(r'```(?:tool|json)?\s*\{[\s\S]*?"(?:name|tool|function)"[\s\S]*?\}\s*```', '', round_output, flags=re.IGNORECASE)
                    clean_res = re.sub(r'\{\s*"(?:name|tool|function)"\s*:\s*"[^"]+"\s*,\s*"(?:args|parameters|params)"\s*:\s*\{[\s\S]*?\}\s*\}', '', clean_res)
                    clean_res = re.sub(r'TOOL:\s*[a-zA-Z0-9_-]+\s*\{[\s\S]*?\}', '', clean_res)
                    final_answer = clean_res.strip() or round_output
                    break

            # 最终回答记录历史（剔除可能遗留的内部结构标记）
            if final_answer:
                clean_final = re.sub(r':::tool_call:[^:\n]+:[^:\n]+(?::[^:\n]+)?:::', '', final_answer).strip()
                self._record_history(user_message, clean_final or final_answer, sid_str)

        except Exception as e:
            err_msg = f"\n\n❌ **[大模型调用异常]**：{str(e)}\n\n*提示：请检查本地模型服务是否已启动，或在「设置与模型」中核对模型 ID、URL 与 API Key。*"
            for line in err_msg.splitlines(keepends=True):
                yield line
                await asyncio.sleep(0.01)

    async def _stream_ollama_messages(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """向 Ollama /api/chat 发送多轮消息列表并流式读取结果"""
        base = self.api_base_url.strip().rstrip("/")
        if base.endswith("/api/generate"):
            url = base.replace("/api/generate", "/api/chat")
        elif base.endswith("/api/chat"):
            url = base
        else:
            url = f"{base}/api/chat"

        # 动态获取 Ollama 上下文窗口大小（默认提高到 16384 即 16K，彻底解决 4096 超出上限报错）
        ollama_cfg = self.config.get("ai", {}).get("ollama", {})
        num_ctx = ollama_cfg.get("num_ctx")
        if not num_ctx:
            active_id = self.config.get("active_model_id")
            for m in self.config.get("models_list", []):
                if m.get("id") == active_id or m.get("model_name") == self.model_name:
                    if m.get("num_ctx"):
                        num_ctx = m.get("num_ctx")
                        break
        try:
            num_ctx = int(num_ctx) if num_ctx else 16384
        except Exception:
            num_ctx = 16384

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": 0.7,
                "num_ctx": num_ctx
            }
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=240.0, write=20.0, pool=10.0)) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        err_bytes = await response.aread()
                        yield f"⚠️ Ollama 服务返回异常 HTTP {response.status_code}: {err_bytes.decode('utf-8', errors='ignore')[:120]}"
                        return
                    in_think = False
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                msg = data.get("message", {})
                                # 提取 Ollama 推理思考内容
                                reasoning_chunk = ""
                                if isinstance(msg, dict):
                                    reasoning_chunk = msg.get("thinking") or msg.get("reasoning") or msg.get("reasoning_content") or ""
                                if reasoning_chunk:
                                    if not in_think:
                                        in_think = True
                                        yield "<think>\n"
                                    yield reasoning_chunk

                                chunk = msg.get("content", "") if isinstance(msg, dict) else ""
                                if not chunk:
                                    chunk = data.get("response", "")
                                if chunk:
                                    if in_think:
                                        in_think = False
                                        yield "\n</think>\n"
                                    yield chunk
                                if data.get("done", False):
                                    break
                            except Exception:
                                continue
                    if in_think:
                        yield "\n</think>\n"
        except httpx.ConnectTimeout:
            yield f"⚠️ **[连接超时]**：无法在 10 秒内连接到本地 Ollama 服务 (`{url}`)，请确认 Ollama 是否已启动。"
        except httpx.ReadTimeout:
            yield "⚠️ **[生成超时]**：本地模型推理耗时过长，建议切换较小尺寸的模型（如 7B/14B 量化版）。"
        except httpx.ConnectError as ce:
            yield f"⚠️ **[连接失败]**：无法连接到本地 Ollama 端点（`{url}`），请在终端运行 `ollama serve` 后重试。"
        except Exception as e:
            yield f"⚠️ **[Ollama 推理异常]**：{e}"

    async def _stream_openai_compatible_messages(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """向 OpenAI 兼容端点发送多轮消息列表并流式读取结果（支持 DeepSeek-R1 等大模型思维链捕获）"""
        base = self.api_base_url.strip().rstrip("/")
        if base.endswith("/chat/completions"):
            url = base
        elif base.endswith("/v1"):
            url = f"{base}/chat/completions"
        else:
            url = f"{base}/v1/chat/completions"

        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=180.0, write=20.0, pool=10.0)) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        err_bytes = await response.aread()
                        yield f"⚠️ API 服务返回异常 HTTP {response.status_code}: {err_bytes.decode('utf-8', errors='ignore')[:120]}"
                        return
                    in_think = False
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if not choices:
                                    continue
                                delta = choices[0].get("delta", {})

                                # 1. 提取推理/思考内容 (DeepSeek-R1 / Qwen-Thinking / OpenAI o1-o3 / SiliconFlow / OpenRouter / vLLM / OhMyGPT)
                                reasoning_chunk = delta.get("reasoning_content") or delta.get("reasoning") or delta.get("thought") or ""
                                if reasoning_chunk:
                                    if not in_think:
                                        in_think = True
                                        yield "<think>\n"
                                    yield reasoning_chunk

                                # 2. 提取正文内容
                                chunk = delta.get("content", "")
                                if chunk:
                                    if in_think:
                                        in_think = False
                                        yield "\n</think>\n"
                                    yield chunk
                            except Exception:
                                continue
                    if in_think:
                        yield "\n</think>\n"
        except httpx.ConnectTimeout:
            yield f"⚠️ **[连接超时]**：无法在 10 秒内连接到模型端点 `{url}`，请检查网络或代理配置。"
        except httpx.ReadTimeout:
            yield "⚠️ **[响应超时]**：大模型生成耗时超过限制，请稍后重试或切换其他模型。"
        except httpx.ConnectError as ce:
            yield f"⚠️ **[连接拒绝]**：无法连通目标服务端点（{ce}），请核对 Base URL 地址。"
        except Exception as e:
            yield f"⚠️ **[API 流式异常]**：{e}"
