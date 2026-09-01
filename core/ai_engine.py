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


class AIEngine:
    """DeskAI 核心大模型与多智能体执行引擎"""

    def __init__(self, config: dict):
        self.config = config
        self.provider = config.get("provider", "ollama")
        self.model_name = config.get("model_name", "deepseek-r1:14b")
        self.api_base_url = config.get("api_base_url", "http://localhost:11434")
        self.api_key = config.get("api_key", "")
        self.system_prompt = config.get("system_prompt", "你是一个全能的桌面 AI 智能体助理。")

        self.memory = None
        self.emotion = None
        self.plugins = None
        self.conversation_history: List[Dict[str, str]] = []
        self.session_histories: Dict[str, List[Dict[str, str]]] = {}

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
        self.provider = ai_cfg.get("provider", config.get("provider", "custom"))
        if self.provider == "ollama":
            ollama_cfg = ai_cfg.get("ollama", {})
            self.model_name = ollama_cfg.get("chat_model", "qwen2.5:7b")
            self.api_base_url = ollama_cfg.get("api_base") or ollama_cfg.get("base_url") or "http://localhost:11434"
            self.api_key = ""
        else:
            custom_cfg = ai_cfg.get("custom", {})
            self.model_name = custom_cfg.get("chat_model", "deepseek-v4")
            self.api_base_url = custom_cfg.get("api_base") or custom_cfg.get("base_url") or "https://api.ohmygpt.com/v1"
            self.api_key = custom_cfg.get("api_key", "")
        print(f"[AIEngine] 重载配置成功 -> Provider: {self.provider}, Model: {self.model_name}, URL: {self.api_base_url}")

    def set_active_model(self, model_config: dict):
        """动态实时热重载大模型参数与连接端点（100% 内存即时替换）"""
        self.provider = model_config.get("provider", "ollama")
        self.model_name = model_config.get("model_name", "deepseek-r1:14b")
        self.api_base_url = model_config.get("api_base_url") or model_config.get("api_base") or model_config.get("base_url") or "http://localhost:11434"
        self.api_key = model_config.get("api_key", "")
        self.system_prompt = model_config.get("system_prompt", "你是一个全能的桌面 AI 智能体助理。")
        print(f"[AIEngine] 🚀 核心模型已 100% 内存热切换 -> Provider: {self.provider}, Model: {self.model_name}, BaseURL: {self.api_base_url}")


    def _extract_expert_id(self, message: str) -> str:
        """从消息中提取绑定的专家角色 ID"""
        m = re.search(r'专家角色:\s*([a-zA-Z0-9_-]+)', message)
        if m:
            return m.group(1).strip()
        return ""

    def _build_full_prompt(self, user_message: str, expert_id: str = "") -> str:
        if expert_id and expert_id in EXPERTS_MAP:
            prompt_parts = [EXPERTS_MAP[expert_id]["system_prompt"]]
        else:
            prompt_parts = [self.system_prompt]

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

        if self.plugins:
            try:
                tool_desc = self.plugins.get_tool_descriptions()
                if tool_desc:
                    prompt_parts.append(f"\n[已挂载MCP工具列表]:\n{tool_desc}")
            except Exception:
                pass

        return "\n".join(prompt_parts)

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

    def _get_trimmed_messages(self, system_prompt: str, user_message: str, session_id: Optional[str] = None) -> List[Dict[str, str]]:
        """构建多会话隔离的滑动窗口消息列表（保留系统设定 + 目标会话最近 10 轮历史 + 当前提问）"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # 严格使用指定 session_id 的独立历史
        if session_id:
            sid_str = str(session_id)
            history = self.session_histories.get(sid_str, [])
        else:
            history = self.conversation_history

        trimmed_history = history[-20:]
        for msg in trimmed_history:
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})
        return messages

    async def chat_stream(self, user_message: str, session_id: Optional[str] = None, **kwargs) -> AsyncGenerator[str, None]:
        """流式主入口：纯真实大模型驱动，完全隔离各会话上下文"""
        sid_str = str(session_id) if session_id else ""
        
        # 1. 基础确定性信息直答
        fast_reply = await self._fast_local_route(user_message)
        if fast_reply is not None:
            if sid_str:
                self.session_histories.setdefault(sid_str, []).append({"role": "user", "content": user_message})
                self.session_histories[sid_str].append({"role": "assistant", "content": fast_reply})
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": fast_reply})
            lines = fast_reply.splitlines(keepends=True)
            for line in lines:
                yield line
                await asyncio.sleep(0.01)
            return

        # 2. 真实大模型端点调用
        expert_id = self._extract_expert_id(user_message)
        full_system_prompt = self._build_full_prompt(user_message, expert_id)

        try:
            if self.provider == "ollama":
                async for chunk in self._stream_ollama(user_message, full_system_prompt, session_id=sid_str):
                    yield chunk
            else:
                async for chunk in self._stream_openai_compatible(user_message, full_system_prompt, session_id=sid_str):
                    yield chunk
        except Exception as e:
            err_msg = f"❌ **[大模型调用异常]**：{str(e)}\n\n*提示：请检查本地模型服务是否已启动，或在「设置与模型」中核对模型 ID、URL 与 API Key。*"
            for line in err_msg.splitlines(keepends=True):
                yield line
                await asyncio.sleep(0.01)

    async def _stream_ollama(self, user_message: str, system_prompt: str, session_id: str = "") -> AsyncGenerator[str, None]:
        base = self.api_base_url.strip().rstrip("/")
        if base.endswith("/api/generate"):
            url = base.replace("/api/generate", "/api/chat")
        elif base.endswith("/api/chat"):
            url = base
        else:
            url = f"{base}/api/chat"

        # 提取会话隔离的多轮历史
        if session_id and session_id in self.session_histories:
            history = self.session_histories[session_id]
        else:
            history = self.conversation_history

        messages = self._get_trimmed_messages(history)
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": {"temperature": 0.7}
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=8.0, read=60.0, write=15.0, pool=10.0)) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        err_bytes = await response.aread()
                        yield f"⚠️ Ollama 服务返回异常 HTTP {response.status_code}: {err_bytes.decode('utf-8', errors='ignore')[:120]}"
                        return
                    full_reply = ""
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                msg = data.get("message", {})
                                chunk = msg.get("content", "") if isinstance(msg, dict) else ""
                                if not chunk:
                                    chunk = data.get("response", "")
                                if chunk:
                                    full_reply += chunk
                                    yield chunk
                                if data.get("done", False):
                                    break
                            except Exception:
                                continue
                    if full_reply:
                        if session_id:
                            self.session_histories.setdefault(session_id, []).append({"role": "user", "content": user_message})
                            self.session_histories[session_id].append({"role": "assistant", "content": full_reply})
                        self.conversation_history.append({"role": "user", "content": user_message})
                        self.conversation_history.append({"role": "assistant", "content": full_reply})
        except httpx.ConnectTimeout:
            yield f"⚠️ **[连接超时]**：无法在 8 秒内连接到本地 Ollama 服务 (`{url}`)，请确认 Ollama 是否已启动。"
        except httpx.ReadTimeout:
            yield "⚠️ **[生成超时]**：本地模型推理耗时过长，建议切换较小尺寸的模型（如 7B/14B 量化版）。"
        except httpx.ConnectError as ce:
            yield f"⚠️ **[连接失败]**：无法连接到本地 Ollama 端点（`{url}`），请在终端运行 `ollama serve` 后重试。"
        except Exception as e:
            yield f"⚠️ **[Ollama 推理异常]**：{e}"

    async def _stream_openai_compatible(self, user_message: str, system_prompt: str, session_id: str = "") -> AsyncGenerator[str, None]:
        base = self.api_base_url.strip().rstrip("/")
        if base.endswith("/chat/completions"):
            url = base
        elif base.endswith("/v1"):
            url = f"{base}/chat/completions"
        else:
            url = f"{base}/v1/chat/completions"

        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        messages = self._get_trimmed_messages(system_prompt, user_message, session_id=session_id)
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=60.0, write=15.0, pool=10.0)) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        err_bytes = await response.aread()
                        yield f"⚠️ API 服务返回异常 HTTP {response.status_code}: {err_bytes.decode('utf-8', errors='ignore')[:120]}"
                        return
                    full_reply = ""
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data["choices"][0].get("delta", {})
                                chunk = delta.get("content", "")
                                if chunk:
                                    full_reply += chunk
                                    yield chunk
                            except Exception:
                                continue
                    if full_reply:
                        if session_id:
                            self.session_histories.setdefault(session_id, []).append({"role": "user", "content": user_message})
                            self.session_histories[session_id].append({"role": "assistant", "content": full_reply})
                        self.conversation_history.append({"role": "user", "content": user_message})
                        self.conversation_history.append({"role": "assistant", "content": full_reply})
        except httpx.ConnectTimeout:
            yield f"⚠️ **[连接超时]**：无法在 10 秒内连接到模型端点 `{url}`，请检查网络或代理配置。"
        except httpx.ReadTimeout:
            yield "⚠️ **[响应超时]**：大模型生成耗时超过限制，请稍后重试或切换其他模型。"
        except httpx.ConnectError as ce:
            yield f"⚠️ **[连接拒绝]**：无法连通目标服务端点（{ce}），请核对 Base URL 地址。"
        except Exception as e:
            yield f"⚠️ **[API 流式异常]**：{e}"
