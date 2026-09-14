# -*- coding: utf-8 -*-
"""
代码模式扩展与技能管理中心 (Dev Extension & Skill Manager Dialog)
- 100% 真实实现 MCP 服务器添加、连通性测试、启停与动态挂载
- 100% 真实实现工作空间自定义 Skill 物理创建 (写入 skills/<id>/SKILL.md)、查看与启停
- 100% 真实支持 7 种开发者身份管理与自定义身份配置持久化
- 现代化极客暗黑主题 (对齐 Antigravity / Cursor IDE 视觉设计)
"""
import os
import sys
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QLineEdit, QTextEdit, QPlainTextEdit, QComboBox,
    QCheckBox, QScrollArea, QFrame, QSplitter, QMessageBox, QFileDialog,
    QSizePolicy, QApplication
)
from PyQt5.QtGui import QFont, QColor

from core.mcp_tool_bridge import MCPToolBridge
from core.mcp_stdio_client import MCPStdioClient

ROOT_DIR = Path(__file__).parent.parent
SKILLS_DIR = ROOT_DIR / "skills"
CONFIG_PATH = ROOT_DIR / "config.json"


# ─────────────────────────────────────────────────────────────
#  7 种专业开发者身份 (Developer Personas) 定义
# ─────────────────────────────────────────────────────────────
DEFAULT_DEV_PERSONAS = {
    "fullstack_architect": {
        "id": "fullstack_architect",
        "name": "🌟 全栈架构师",
        "title": "Principal Fullstack Software Architect",
        "desc": "专注于系统级宏观架构设计、模块解耦、DDD 领域建模、API 契约优先与高可用扩展性。",
        "prompt": (
            "【当前激活的开发者身份：🌟 全栈架构师 (Principal Fullstack Architect)】\n"
            "你的架构与编码准则：\n"
            "1. 宏观系统思维：优先考虑高内聚低耦合、模块化与分层清晰度（领域层/服务层/UI层），杜绝意大利面条式代码；\n"
            "2. 扩展性与容灾：代码必须具备良好的向前兼容性与配置解耦，预留合理的抽象接口与扩展插槽；\n"
            "3. 规范先于实现：接口契约、参数类型与数据流必须严谨，优先给出架构拓扑与关键设计选型Rationale；\n"
            "4. 拒绝技术债务：敏锐指出潜在的架构隐患并给出优雅的最佳实践解决方案。"
        )
    },
    "agile_hacker": {
        "id": "agile_hacker",
        "name": "⚡ 敏捷极客与重构先锋",
        "title": "Senior Agile Hacker & Refactoring Specialist",
        "desc": "专注于极简代码 (KISS)、DRY 原则、极限性能重构、消除 Bad Smells 与敏捷高质落地。",
        "prompt": (
            "【当前激活的开发者身份：⚡ 敏捷极客与重构先锋 (Agile Hacker & Refactoring Lead)】\n"
            "你的编码与重构准则：\n"
            "1. 极简与高内聚 (KISS & DRY)：消灭一切冗余与模板代码，用最干净纯粹的语句实现最高效率；\n"
            "2. 消除代码坏味道：嗅探过长函数、魔法数值与多层嵌套，坚决实施 Extract Method 与提前返回原则；\n"
            "3. 重构安全网：重构必须保持既有逻辑行为完全等价，步骤清晰，步步为营；\n"
            "4. 极客实用主义：不搞过度设计，快速产出最优雅精炼的可运行高质量代码。"
        )
    },
    "frontend_specialist": {
        "id": "frontend_specialist",
        "name": "🎨 UI/UX 前端交互专家",
        "title": "Lead UI/UX & Frontend Interaction Specialist",
        "desc": "专注于现代高级视觉美学、暗黑/浅色主题、丝滑微动效、自适应响应式布局与极佳用户交互体验。",
        "prompt": (
            "【当前激活的开发者身份：🎨 UI/UX 前端交互专家 (Lead Frontend Specialist)】\n"
            "你的设计与实现准则：\n"
            "1. 极致视觉质感：杜绝粗糙毛坯 UI，严格运用现代配色、边框微光、毛玻璃与精致内边距 (Padding/Margin)；\n"
            "2. 丝滑交互心流：关键操作提供即时状态反馈、悬停高亮 (Hover)、平滑过渡与微动效 (QPropertyAnimation)；\n"
            "3. 响应式与无障碍：界面元素自适应窗口伸缩，文本清晰防截断，层次排版主次分明；\n"
            "4. 组件封装美学：界面控件高度封装复用，样式表统一管理，逻辑与表现彻底分离。"
        )
    },
    "python_engineer": {
        "id": "python_engineer",
        "name": "🐍 Python 核心与算法工程师",
        "title": "Senior Python Core & Algorithm Engineer",
        "desc": "专注于 Pythonic 优雅范式、asyncio 异步高并发、严格类型注解 (Type Hints) 与时空复杂度优化。",
        "prompt": (
            "【当前激活的开发者身份：🐍 Python 核心与算法工程师 (Python Core & Algorithm Lead)】\n"
            "你的 Pythonic 编程准则：\n"
            "1. 严格 Pythonic 风格：遵循 PEP 8，善用推导式、生成器、装饰器、上下文管理器与 dataclass；\n"
            "2. 全面静态类型提示：所有函数入参与返回值必须标注精准的 Type Hinting (typing / collections.abc)；\n"
            "3. 高并发与时空优化：注重算法时间与空间复杂度 (O(n))，I/O 密集型任务坚决使用非阻塞 asyncio 或线程池；\n"
            "4. 健壮的防御性治理：精确捕获具体 Exception 类型，记录有价值的上下文堆栈，拒绝空 except: pass。"
        )
    },
    "qa_devops": {
        "id": "qa_devops",
        "name": "🧪 QA 自动化与 CI/CD 专家",
        "title": "Senior QA Automation & DevOps Specialist",
        "desc": "专注于单元测试金字塔、pytest 边界用例覆盖、Mock 外部依赖、自动化脚本与持续集成验证。",
        "prompt": (
            "【当前激活的开发者身份：🧪 QA 自动化与 CI/CD 专家 (QA & DevOps Specialist)】\n"
            "你的测试与质量准则：\n"
            "1. 质量第一准则：编写或修改代码的同时，必须配套编写详尽的自动化单元测试与边界断言；\n"
            "2. 边界用例全覆盖：重点覆盖边界值、空数据 (None/Empty)、超时异常、编码冲突与破坏性输入；\n"
            "3. 测试隔离与自动化：善用 pytest fixture 与 unittest.mock 隔离外部网络与硬件依赖；\n"
            "4. 自动化流水线保障：测试输出明确易读，支持无缝集成至持续集成与自动化构建系统。"
        )
    },
    "security_expert": {
        "id": "security_expert",
        "name": "🛡️ 安全审计与防御编程专家",
        "title": "Principal CyberSecurity & Code Auditor",
        "desc": "专注于 OWASP 漏洞防范、输入边界防御、防命令/SQL注入、敏感凭据脱敏与最小特权原则。",
        "prompt": (
            "【当前激活的开发者身份：🛡️ 安全审计与防御编程专家 (Security & Audit Specialist)】\n"
            "你的安全与防御准则：\n"
            "1. 零信任输入原则：一切外部输入（路径、参数、终端命令、网络Payload）皆不可信，必须进行白名单校验与过滤；\n"
            "2. 注入深度防范：严禁拼接 Shell 命令与 SQL 语句，必须使用参数化调用或沙箱隔离；\n"
            "3. 敏感凭据零泄露：密码、API Key、Token 绝对严禁明文硬编码于代码中，强制环境变量托管；\n"
            "4. 最小权限沙箱：文件操作严格限制在工作空间物理目录内，防范路径遍历 (Path Traversal) 越权。"
        )
    },
    "custom": {
        "id": "custom",
        "name": "⚙️ 自定义开发者身份",
        "title": "Custom Developer Persona",
        "desc": "由开发者自主设定的专属角色偏好、特定领域知识与个性化行为指南。",
        "prompt": (
            "【当前激活的开发者身份：⚙️ 自定义开发者角色】\n"
            "请严格遵循用户在扩展管理中心中设定的专属开发指引与规范回复。"
        )
    }
}


class DevExtensionManagerDialog(QDialog):
    """MCP 与 Skill 扩展管理中心主弹窗"""
    extension_changed_signal = pyqtSignal()

    def __init__(self, config: Optional[dict] = None, save_config_fn=None, is_dark: bool = True, parent=None):
        if isinstance(config, bool):
            parent = save_config_fn
            is_dark = config
            config = None
            save_config_fn = None
        elif isinstance(is_dark, QWidget):
            parent = is_dark
            is_dark = getattr(parent, "is_dark", True)

        super().__init__(parent)
        self.config = config or {}
        self.save_config_fn = save_config_fn
        self.is_dark = is_dark
        self.extensions_changed = self.extension_changed_signal
        self.setWindowTitle("🧩 扩展生态中心 - MCP 服务、Skill 技能与开发者身份")
        
        # 启用最大化与还原按钮，移除问号帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint | Qt.WindowMaximizeButtonHint)
        
        self.setMinimumSize(840, 540)
        self._setup_adaptive_geometry()
        
        self.bridge = MCPToolBridge.get_instance()
        self.current_personas = self._load_personas()

        self._init_ui()

    def _setup_adaptive_geometry(self):
        """根据当前屏幕物理可用分辨率和上一次用户记忆窗口尺寸，计算自适应窗口大小"""
        screen = None
        if self.parentWidget() and hasattr(self.parentWidget(), "screen"):
            screen = self.parentWidget().screen()
        if not screen:
            screen = QApplication.primaryScreen()

        avail = screen.availableGeometry() if screen else None
        
        # 优先读取上次用户记忆尺寸（如有且合法）
        saved_size = self.config.get("dev_extension_dialog_size")
        if saved_size and isinstance(saved_size, (list, tuple)) and len(saved_size) >= 2:
            sw, sh = saved_size[0], saved_size[1]
            if avail:
                target_w = max(860, min(int(avail.width() * 0.95), sw))
                target_h = max(540, min(int(avail.height() * 0.95), sh))
            else:
                target_w, target_h = max(860, sw), max(540, sh)
        else:
            if avail:
                # 自适应屏幕：宽约为屏幕 68%，且限制在 940px~1120px 黄金阅读区间；高限制在 600px~760px
                target_w = min(1080, max(920, int(avail.width() * 0.68)))
                target_h = min(760, max(600, int(avail.height() * 0.72)))
            else:
                target_w, target_h = 980, 660

        if avail:
            # 居中显示在父窗口或主屏幕
            if self.parentWidget() and self.parentWidget().isVisible():
                pw = self.parentWidget().window()
                p_geo = pw.geometry()
                target_x = max(avail.left() + 20, p_geo.x() + (p_geo.width() - target_w) // 2)
                target_y = max(avail.top() + 20, p_geo.y() + (p_geo.height() - target_h) // 2)
            else:
                target_x = avail.left() + (avail.width() - target_w) // 2
                target_y = avail.top() + (avail.height() - target_h) // 2
            self.setGeometry(target_x, target_y, target_w, target_h)
        else:
            self.resize(target_w, target_h)

    def _save_dialog_geometry(self):
        """保存用户调整后的窗口大小偏好"""
        try:
            if not self.isMaximized():
                self.config["dev_extension_dialog_size"] = [self.width(), self.height()]
                if callable(self.save_config_fn):
                    self.save_config_fn(self.config)
        except Exception:
            pass

    def closeEvent(self, event):
        self._save_dialog_geometry()
        super().closeEvent(event)

    def accept(self):
        self._save_dialog_geometry()
        super().accept()

    def reject(self):
        self._save_dialog_geometry()
        super().reject()

    def create_skill(self, skill_id: str, name: str = "", description: str = "", body: str = "", **kwargs) -> Path:
        """真实物理创建并落地 SKILL.md 文件"""
        name = name or kwargs.get("skill_name", skill_id)
        body = body or kwargs.get("markdown_content", "")
        target_folder = SKILLS_DIR / skill_id
        target_folder.mkdir(parents=True, exist_ok=True)
        content = (
            f"---\n"
            f"name: {name}\n"
            f"description: {description}\n"
            f"version: 1.0.0\n"
            f"---\n\n"
            f"{body}\n"
        )
        p = target_folder / "SKILL.md"
        p.write_text(content, encoding="utf-8")
        self._toggle_skill(skill_id, True)
        self._refresh_skills_list()
        self.extension_changed_signal.emit()
        return p

    def _init_ui(self):
        bg = "#1e1e1e" if self.is_dark else "#f3f4f6"
        fg = "#cccccc" if self.is_dark else "#1f2937"
        border = "#333333" if self.is_dark else "#e5e7eb"
        desc_color = "#858585" if self.is_dark else "#64748b"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
                font-family: 'Segoe UI', 'Microsoft YaHei UI';
            }}
            QTabWidget::pane {{
                border: 1px solid {border};
                background: {bg};
                border-radius: 6px;
            }}
            QTabBar::tab {{
                background: {'#252526' if self.is_dark else '#e5e7eb'};
                color: {fg};
                padding: 8px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                font-size: 12.5px;
                font-weight: 500;
            }}
            QTabBar::tab:selected {{
                background: {'#094771' if self.is_dark else '#2563eb'};
                color: #ffffff;
                font-weight: bold;
            }}
            QLineEdit, QPlainTextEdit, QTextEdit {{
                background-color: {'#252526' if self.is_dark else '#ffffff'};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }}
            QLineEdit:focus, QPlainTextEdit:focus {{
                border-color: #007acc;
            }}
            QPushButton {{
                background-color: {'#333333' if self.is_dark else '#e2e8f0'};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {'#3f3f46' if self.is_dark else '#cbd5e1'};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 头部标题卡片
        header = QHBoxLayout()
        title_icon = QLabel("🧩")
        title_icon.setStyleSheet("font-size: 24px;")
        header.addWidget(title_icon)

        title_vbox = QVBoxLayout()
        title_lbl = QLabel("开发者生态中心 (Developer Ecosystem Center)")
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {fg}; background: transparent; border: none;")
        desc_lbl = QLabel("在此真实添加与管理 MCP 服务连接器、工作空间技能 (Skill) 以及设定你的大模型开发者身份。")
        desc_lbl.setStyleSheet(f"font-size: 11.5px; color: {desc_color}; background: transparent; border: none;")
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(desc_lbl)
        header.addLayout(title_vbox)
        header.addStretch()
        layout.addLayout(header)

        # 核心 Tab 选项卡
        self.tabs = QTabWidget()
        self.tab_mcp = self._create_mcp_tab()
        self.tab_skills = self._create_skills_tab()
        self.tab_personas = self._create_personas_tab()

        self.tabs.addTab(self.tab_mcp, "🧩 MCP 连接器服务")
        self.tabs.addTab(self.tab_skills, "⚡ 工作空间技能 (Skill)")
        self.tabs.addTab(self.tab_personas, "👨‍💻 开发者身份设定")
        layout.addWidget(self.tabs, 1)

        # 底部按钮栏
        bot_bar = QHBoxLayout()
        self.status_lbl = QLabel("就绪")
        self.status_lbl.setStyleSheet("color: #7ee787; font-size: 11.5px;")
        bot_bar.addWidget(self.status_lbl)
        bot_bar.addStretch()

        close_btn = QPushButton("完成并退出")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c; color: white; font-weight: bold;
                border: none; padding: 6px 18px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #1177bb; }
        """)
        close_btn.clicked.connect(self.accept)
        bot_bar.addWidget(close_btn)
        layout.addLayout(bot_bar)

    # ══════════════════════════════════════════════════════════
    #  Tab 1: MCP 服务器管理
    # ══════════════════════════════════════════════════════════
    def _create_mcp_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        # 顶操作栏 (新增与预设添加)
        action_bar = QHBoxLayout()
        add_btn = QPushButton("➕ 添加自定义 MCP 服务")
        add_btn.setStyleSheet("background-color: #1e3a24; color: #7ee787; border: 1px solid #2e7d32; font-weight: bold;")
        add_btn.clicked.connect(self._show_add_mcp_dialog)
        action_bar.addWidget(add_btn)

        # 常用官方预设下拉一键安装
        preset_lbl = QLabel("常用精选预设:")
        preset_lbl.setStyleSheet("color: #858585; font-size: 11.5px;")
        action_bar.addWidget(preset_lbl)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "📦 SQLite MCP (本地高可用免安装)",
            "🐙 GitHub MCP (仓库与PR管理)",
            "📂 Filesystem MCP (全盘文件系统安全扩展)",
            "🌐 Fetch MCP (网页与数据高速提取)",
            "🐘 PostgreSQL MCP (生产数据库直连)"
        ])
        action_bar.addWidget(self.preset_combo)

        install_preset_btn = QPushButton("⚡ 一键挂载预设")
        install_preset_btn.clicked.connect(self._install_selected_preset)
        action_bar.addWidget(install_preset_btn)
        action_bar.addStretch()

        lay.addLayout(action_bar)

        # MCP 列表滚动区域 (禁止水平滚动条，启用弹性自适应)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.mcp_list_container = QWidget()
        self.mcp_list_container.setStyleSheet("background: transparent;")
        self.mcp_list_lay = QVBoxLayout(self.mcp_list_container)
        self.mcp_list_lay.setContentsMargins(0, 0, 0, 0)
        self.mcp_list_lay.setSpacing(8)

        scroll.setWidget(self.mcp_list_container)
        lay.addWidget(scroll, 1)

        self._refresh_mcp_list()
        return w

    def _refresh_mcp_list(self):
        # 清空现有列表
        while self.mcp_list_lay.count():
            item = self.mcp_list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cfg_data = self.bridge.load_mcp_config()
        servers = cfg_data.get("mcpServers", {})
        enabled_ids = self.bridge.get_enabled_server_ids()

        if not servers:
            empty_lbl = QLabel("暂无已配置的 MCP 服务器。点击上方「➕ 添加自定义 MCP」或从精选预设中一键添加！")
            empty_lbl.setStyleSheet("color: #858585; padding: 20px; font-size: 12px;")
            self.mcp_list_lay.addWidget(empty_lbl)
            self.mcp_list_lay.addStretch()
            return

        for srv_id, srv_info in servers.items():
            card = self._create_mcp_card(srv_id, srv_info, is_enabled=(srv_id in enabled_ids or not enabled_ids))
            self.mcp_list_lay.addWidget(card)

        self.mcp_list_lay.addStretch()

    def _create_mcp_card(self, srv_id: str, srv_info: dict, is_enabled: bool) -> QWidget:
        card = QFrame()
        d = getattr(self, 'is_dark', True)
        card_bg = '#252526' if d else '#f8fafc'
        card_border = '#333333' if d else '#cbd5e1'
        card_hover = '#444444' if d else '#94a3b8'
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QFrame:hover {{ border-color: {card_hover}; }}
        """)
        c_lay = QHBoxLayout(card)
        c_lay.setContentsMargins(12, 10, 12, 10)
        c_lay.setSpacing(12)

        # 状态指示点 (固定尺寸，绝不挤压)
        status_dot = QLabel("🟢" if is_enabled else "⚪")
        status_dot.setToolTip("已启用" if is_enabled else "已停用")
        status_dot.setFixedWidth(24)
        status_dot.setAlignment(Qt.AlignCenter)
        c_lay.addWidget(status_dot, 0, Qt.AlignVCenter)

        # 核心信息自适应区
        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(4)

        mcp_name_color = '#ffffff' if d else '#0f172a'
        mcp_cmd_color = '#4ec9b0' if d else '#0e7490'
        mcp_tools_color = '#666666' if d else '#64748b'
        name_row = QHBoxLayout()
        title = QLabel(f"<b>{srv_id}</b>")
        title.setStyleSheet(f"font-size: 13px; color: {mcp_name_color}; background: transparent; border: none;")
        title.setMinimumWidth(0)
        name_row.addWidget(title)

        cmd_tag = QLabel(f"`{srv_info.get('command', 'npx')} {' '.join(srv_info.get('args', []))[:36]}...`")
        cmd_tag.setStyleSheet(f"color: {mcp_cmd_color}; font-family: monospace; font-size: 11px; background: transparent; border: none;")
        cmd_tag.setMinimumWidth(0)
        name_row.addWidget(cmd_tag)
        name_row.addStretch()
        info_vbox.addLayout(name_row)

        desc = QLabel(srv_info.get("description", "标准 MCP 进程连接器服务"))
        desc_color = '#a1a1aa' if d else '#475569'
        desc.setStyleSheet(f"color: {desc_color}; font-size: 11.5px; background: transparent; border: none;")
        desc.setWordWrap(True)
        desc.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        desc.setMinimumWidth(0)
        info_vbox.addWidget(desc)

        tools_cnt = len(srv_info.get("tools", []))
        tools_lbl = QLabel(f"包含 {tools_cnt} 个工具导向" + (f": {', '.join([t.get('name') for t in srv_info.get('tools', [])[:3]])}..." if tools_cnt else ""))
        tools_lbl.setStyleSheet(f"color: {mcp_tools_color}; font-size: 10.5px; background: transparent; border: none;")
        tools_lbl.setWordWrap(True)
        tools_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        tools_lbl.setMinimumWidth(0)
        info_vbox.addWidget(tools_lbl)

        c_lay.addLayout(info_vbox, 1)

        # 右侧操作按钮固定区（永远不被挤出视野）
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        btn_box.setContentsMargins(0, 0, 0, 0)

        # 1. 连通性测试按钮
        test_btn = QPushButton("🧪 测试连接")
        test_btn.setToolTip("启动服务进程发送 JSON-RPC 握手，验证可用性")
        test_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        test_btn.setMinimumHeight(28)
        test_btn.setCursor(Qt.PointingHandCursor)
        test_btn.clicked.connect(lambda ch, s=srv_info, sid=srv_id: self._run_test_connection(sid, s))
        btn_box.addWidget(test_btn)

        # 2. 启用/停用开关
        toggle_btn = QPushButton("停用" if is_enabled else "启用")
        toggle_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        toggle_btn.setMinimumHeight(28)
        toggle_btn.setMinimumWidth(56)
        toggle_btn.setCursor(Qt.PointingHandCursor)
        if is_enabled:
            toggle_btn.setStyleSheet("color: #e5534b;")
        else:
            toggle_btn.setStyleSheet("color: #7ee787;")
        toggle_btn.clicked.connect(lambda ch, sid=srv_id, cur=is_enabled: self._toggle_mcp(sid, not cur))
        btn_box.addWidget(toggle_btn)

        # 3. 删除按钮
        del_btn = QPushButton("🗑️")
        del_btn.setToolTip("删除该 MCP 服务配置")
        del_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        del_btn.setFixedSize(28, 28)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet("color: #f85149; border: none; background: transparent; font-size: 13px;")
        del_btn.clicked.connect(lambda ch, sid=srv_id: self._delete_mcp(sid))
        btn_box.addWidget(del_btn)

        c_lay.addLayout(btn_box, 0)
        return card

    def _run_test_connection(self, srv_id: str, srv_info: dict):
        self.status_lbl.setText(f"正在对 [{srv_id}] 进行启动与握手测试...")
        self.status_lbl.setStyleSheet("color: #e3b341;")
        
        test_cfg = dict(srv_info)
        test_cfg["id"] = srv_id
        ok, msg, ms = self.bridge.test_mcp_connection(test_cfg)
        if ok:
            QMessageBox.information(self, "MCP 测试成功", f"🎉 服务 [{srv_id}] 握手成功！\n\n{msg}\n响应时间: {ms:.1f}ms")
            self.status_lbl.setText(f"✅ [{srv_id}] 连通测试通过 ({ms:.1f}ms)")
            self.status_lbl.setStyleSheet("color: #7ee787;")
        else:
            hint = "\n\n建议排查系统是否已安装对应命令环境。"
            if srv_info.get("command") == "npx" or any("npx" in str(a) for a in srv_info.get("args", [])):
                hint = "\n\n💡 提示：该服务使用远程 npx 包，启动需从 npm 下载依赖或配置 API Key。推荐体验列表顶部的「local-sqlite-mcp」等内置 Python MCP 服务，零网络依赖且毫秒级响应！"
            QMessageBox.warning(self, "MCP 测试失败", f"❌ 服务 [{srv_id}] 启动或握手异常：\n\n{msg}{hint}")
            self.status_lbl.setText(f"❌ [{srv_id}] 连通测试失败")
            self.status_lbl.setStyleSheet("color: #f85149;")

    def _toggle_mcp(self, srv_id: str, enable: bool):
        cfg_data = self.bridge.load_mcp_config()
        srv_info = cfg_data.get("mcpServers", {}).get(srv_id, {})
        self.bridge.add_or_update_server(srv_id, srv_info, enable=enable)
        self._refresh_mcp_list()
        self.extension_changed_signal.emit()

    def _delete_mcp(self, srv_id: str):
        ret = QMessageBox.question(self, "确认删除", f"确认彻底删除 MCP 服务 [{srv_id}] 的配置？", QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            self.bridge.delete_server(srv_id)
            self._refresh_mcp_list()
            self.extension_changed_signal.emit()

    def _install_selected_preset(self):
        idx = self.preset_combo.currentIndex()
        presets = [
            ("local-sqlite-mcp", {
                "command": "python",
                "args": ["-m", "core.local_sqlite_mcp"],
                "description": "本地高可用 SQLite 数据库查询与元数据分析 MCP 服务器（毫秒级响应、零网络依赖）",
                "tools": [
                    {"name": "sqlite_query", "description": "执行 SQLite SQL 查询语句（支持 SELECT、INSERT、UPDATE 等）并返回 JSON 结果"},
                    {"name": "sqlite_schema", "description": "获取 SQLite 数据库所有表结构、字段类型与建表 SQL 元信息"}
                ]
            }),
            ("github-mcp", {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "description": "GitHub 官方仓库管理、Issues、PR 交互 MCP 服务",
                "tools": [{"name": "github_search_repos", "description": "搜索开源项目与代码"}]
            }),
            ("filesystem-mcp", {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
                "description": "全盘文件系统高阶搜索、读写与目录监听扩展",
                "tools": [{"name": "fs_read_file", "description": "安全读取文件"}]
            }),
            ("fetch-mcp", {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-fetch"],
                "description": "高速网页内容抓取与外部 API 结构化提取",
                "tools": [{"name": "fetch_url", "description": "获取网页正文"}]
            }),
            ("postgres-mcp", {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-postgres"],
                "description": "PostgreSQL 生产级数据库直接交互与 Schema 反向工程",
                "tools": [{"name": "postgres_query", "description": "执行 Postgres SQL"}]
            })
        ]
        if 0 <= idx < len(presets):
            s_id, s_info = presets[idx]
            self.bridge.add_or_update_server(s_id, s_info, enable=True)
            self._refresh_mcp_list()
            self.status_lbl.setText(f"✅ 已成功挂载预设服务 [{s_id}]！")
            self.extension_changed_signal.emit()

    def _show_add_mcp_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("➕ 添加自定义 MCP 服务器")
        dlg.resize(500, 420)
        d_lay = QVBoxLayout(dlg)
        d_lay.setSpacing(8)

        d_lay.addWidget(QLabel("服务唯一标识 ID (如 my_local_mcp):"))
        id_edit = QLineEdit()
        id_edit.setPlaceholderText("例如: custom-sqlite-mcp")
        d_lay.addWidget(id_edit)

        d_lay.addWidget(QLabel("启动命令 (Command):"))
        cmd_edit = QLineEdit()
        cmd_edit.setPlaceholderText("例如: npx 或 python 或 uvx")
        d_lay.addWidget(cmd_edit)

        d_lay.addWidget(QLabel("启动参数 (Args, 空格分隔):"))
        args_edit = QLineEdit()
        args_edit.setPlaceholderText("例如: -y @modelcontextprotocol/server-sqlite")
        d_lay.addWidget(args_edit)

        d_lay.addWidget(QLabel("环境变量 (如 API_KEY=xxx, 每行一个):"))
        env_edit = QPlainTextEdit()
        env_edit.setFixedHeight(60)
        d_lay.addWidget(env_edit)

        d_lay.addWidget(QLabel("导出工具列表 (逗号分隔工具名，如 query_db, export_table):"))
        tools_edit = QLineEdit()
        tools_edit.setPlaceholderText("query_db, export_table")
        d_lay.addWidget(tools_edit)

        d_lay.addWidget(QLabel("功能说明描述:"))
        desc_edit = QLineEdit()
        desc_edit.setPlaceholderText("该 MCP 服务的主要能力与使用场景")
        d_lay.addWidget(desc_edit)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dlg.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("保存并启用")
        save_btn.setStyleSheet("background-color: #0e639c; color: white; font-weight: bold;")
        def _do_save():
            sid = id_edit.text().strip()
            cmd = cmd_edit.text().strip()
            if not sid or not cmd:
                QMessageBox.warning(dlg, "参数不全", "服务 ID 和启动命令必须填写！")
                return
            args = [a for a in args_edit.text().strip().split(" ") if a]
            env_map = {}
            for line in env_edit.toPlainText().splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    env_map[k.strip()] = v.strip()
            tools_list = []
            for t in tools_edit.text().split(","):
                t = t.strip()
                if t:
                    tools_list.append({"name": t, "description": f"MCP [{sid}] {t}"})
            
            srv_info = {
                "command": cmd,
                "args": args,
                "env": env_map,
                "description": desc_edit.text().strip() or f"自定义 {sid} 服务",
                "tools": tools_list
            }
            self.bridge.add_or_update_server(sid, srv_info, enable=True)
            dlg.accept()
            self._refresh_mcp_list()
            self.extension_changed_signal.emit()

        save_btn.clicked.connect(_do_save)
        btn_box.addWidget(save_btn)
        d_lay.addLayout(btn_box)
        dlg.exec_()

    # ══════════════════════════════════════════════════════════
    #  Tab 2: 工作空间技能 (Skill) 管理与物理创建
    # ══════════════════════════════════════════════════════════
    def _create_skills_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        # 顶操作栏
        action_bar = QHBoxLayout()
        add_skill_btn = QPushButton("➕ 创建新技能 (物理生成 SKILL.md)")
        add_skill_btn.setStyleSheet("background-color: #1e3a24; color: #7ee787; border: 1px solid #2e7d32; font-weight: bold;")
        add_skill_btn.clicked.connect(self._show_create_skill_dialog)
        action_bar.addWidget(add_skill_btn)

        action_bar.addStretch()
        refresh_btn = QPushButton("🔄 重新扫描")
        refresh_btn.clicked.connect(self._refresh_skills_list)
        action_bar.addWidget(refresh_btn)
        lay.addLayout(action_bar)

        # 技能列表 (禁止水平滚动条，弹性自适应)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.skills_list_container = QWidget()
        self.skills_list_container.setStyleSheet("background: transparent;")
        self.skills_list_lay = QVBoxLayout(self.skills_list_container)
        self.skills_list_lay.setContentsMargins(0, 0, 0, 0)
        self.skills_list_lay.setSpacing(8)

        scroll.setWidget(self.skills_list_container)
        lay.addWidget(scroll, 1)

        self._refresh_skills_list()
        return w

    def _refresh_skills_list(self):
        while self.skills_list_lay.count():
            item = self.skills_list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not SKILLS_DIR.exists():
            SKILLS_DIR.mkdir(parents=True, exist_ok=True)

        enabled_skills = self._get_enabled_skills()
        skill_folders = sorted([d for d in SKILLS_DIR.iterdir() if d.is_dir()])

        if not skill_folders:
            empty_lbl = QLabel("当前工作空间暂无技能。点击上方「➕ 创建新技能」立即在 skills/ 目录生成你的首个专业技能套件！")
            empty_lbl.setStyleSheet("color: #858585; padding: 20px; font-size: 12px;")
            self.skills_list_lay.addWidget(empty_lbl)
            self.skills_list_lay.addStretch()
            return

        for s_dir in skill_folders:
            card = self._create_skill_card(s_dir, is_enabled=(s_dir.name in enabled_skills or not enabled_skills))
            self.skills_list_lay.addWidget(card)

        self.skills_list_lay.addStretch()

    def _create_skill_card(self, skill_dir: Path, is_enabled: bool) -> QWidget:
        card = QFrame()
        d = getattr(self, 'is_dark', True)
        card_bg = '#252526' if d else '#f8fafc'
        card_border = '#333333' if d else '#cbd5e1'
        card_hover = '#444444' if d else '#94a3b8'
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QFrame:hover {{ border-color: {card_hover}; }}
        """)
        c_lay = QHBoxLayout(card)
        c_lay.setContentsMargins(12, 10, 12, 10)
        c_lay.setSpacing(12)

        # 图标与名称
        s_id = skill_dir.name
        meta = self._parse_skill_meta(skill_dir / "SKILL.md")

        icon_lbl = QLabel("⚡")
        icon_lbl.setFixedWidth(24)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 16px;")
        c_lay.addWidget(icon_lbl, 0, Qt.AlignVCenter)

        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(4)

        name_row = QHBoxLayout()
        sk_name_color = '#ffffff' if d else '#0f172a'
        sk_id_color = '#858585' if d else '#64748b'
        sk_sub_color = '#666666' if d else '#64748b'
        title = QLabel(f"<b>{meta.get('name', s_id)}</b>")
        title.setStyleSheet(f"font-size: 13px; color: {sk_name_color}; background: transparent; border: none;")
        title.setMinimumWidth(0)
        name_row.addWidget(title)

        id_lbl = QLabel(f"id: `{s_id}`")
        id_lbl.setStyleSheet(f"color: {sk_id_color}; font-size: 11px; background: transparent; border: none;")
        id_lbl.setMinimumWidth(0)
        name_row.addWidget(id_lbl)
        name_row.addStretch()
        info_vbox.addLayout(name_row)

        desc = QLabel(meta.get("description", "工作空间专用 Agent 技能工作流"))
        desc_color = '#a1a1aa' if d else '#475569'
        desc.setStyleSheet(f"color: {desc_color}; font-size: 11.5px; background: transparent; border: none;")
        desc.setWordWrap(True)
        desc.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        desc.setMinimumWidth(0)
        info_vbox.addWidget(desc)

        tools = meta.get("tools", [])
        tools_str = f"关联工具: {', '.join(tools)}" if tools else "纯提示词工作流引导"
        sub_lbl = QLabel(f"v{meta.get('version', '1.0')} • {tools_str}")
        sub_lbl.setStyleSheet(f"color: {sk_sub_color}; font-size: 10.5px; background: transparent; border: none;")
        sub_lbl.setWordWrap(True)
        sub_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        sub_lbl.setMinimumWidth(0)
        info_vbox.addWidget(sub_lbl)

        c_lay.addLayout(info_vbox, 1)

        # 右侧操作按钮固定区（永远不被挤出视野）
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        btn_box.setContentsMargins(0, 0, 0, 0)

        view_btn = QPushButton("👁️ 查看/编辑")
        view_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        view_btn.setMinimumHeight(28)
        view_btn.setCursor(Qt.PointingHandCursor)
        view_btn.clicked.connect(lambda ch, p=skill_dir / "SKILL.md": self._view_skill_md(p))
        btn_box.addWidget(view_btn)

        toggle_btn = QPushButton("停用" if is_enabled else "启用")
        toggle_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        toggle_btn.setMinimumHeight(28)
        toggle_btn.setMinimumWidth(56)
        toggle_btn.setCursor(Qt.PointingHandCursor)
        toggle_btn.setStyleSheet("color: #e5534b;" if is_enabled else "color: #7ee787;")
        toggle_btn.clicked.connect(lambda ch, sid=s_id, cur=is_enabled: self._toggle_skill(sid, not cur))
        btn_box.addWidget(toggle_btn)

        del_btn = QPushButton("🗑️")
        del_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        del_btn.setFixedSize(28, 28)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet("color: #f85149; border: none; background: transparent; font-size: 13px;")
        del_btn.clicked.connect(lambda ch, s=skill_dir: self._delete_skill(s))
        btn_box.addWidget(del_btn)

        c_lay.addLayout(btn_box, 0)
        return card

    def _parse_skill_meta(self, skill_md_path: Path) -> dict:
        meta = {}
        if not skill_md_path.exists():
            return meta
        try:
            text = skill_md_path.read_text(encoding="utf-8")
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    for line in parts[1].splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            meta[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass
        return meta

    def _get_enabled_skills(self) -> set:
        if not CONFIG_PATH.exists():
            return set()
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                c = json.load(f)
            return set(c.get("plugins", {}).get("enabled", []))
        except Exception:
            return set()

    def _toggle_skill(self, skill_id: str, enable: bool):
        if not CONFIG_PATH.exists():
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                c = json.load(f)
            enabled = set(c.get("plugins", {}).get("enabled", []))
            if enable:
                enabled.add(skill_id)
            else:
                enabled.discard(skill_id)
            c.setdefault("plugins", {})["enabled"] = list(enabled)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(c, f, ensure_ascii=False, indent=2)
            self._refresh_skills_list()
            self.extension_changed_signal.emit()
        except Exception as e:
            QMessageBox.warning(self, "切换失败", str(e))

    def _delete_skill(self, skill_dir: Path):
        ret = QMessageBox.question(self, "确认删除", f"确认删除技能文件夹 `{skill_dir.name}` 及其全部内容？", QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            import shutil
            try:
                shutil.rmtree(skill_dir)
                self._refresh_skills_list()
                self.extension_changed_signal.emit()
            except Exception as e:
                QMessageBox.warning(self, "删除失败", str(e))

    def _view_skill_md(self, skill_md: Path):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"编辑 {skill_md.parent.name} - SKILL.md")
        dlg.resize(650, 480)
        lay = QVBoxLayout(dlg)

        edit = QPlainTextEdit()
        if skill_md.exists():
            edit.setPlainText(skill_md.read_text(encoding="utf-8"))
        lay.addWidget(edit, 1)

        b_row = QHBoxLayout()
        b_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dlg.reject)
        b_row.addWidget(cancel_btn)

        save_btn = QPushButton("💾 保存修改")
        save_btn.setStyleSheet("background-color: #0e639c; color: white; font-weight: bold;")
        def _save():
            skill_md.write_text(edit.toPlainText(), encoding="utf-8")
            dlg.accept()
            self._refresh_skills_list()
        save_btn.clicked.connect(_save)
        b_row.addWidget(save_btn)
        lay.addLayout(b_row)
        dlg.exec_()

    def _show_create_skill_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("➕ 物理创建新技能 (Auto Create SKILL.md)")
        dlg.resize(580, 480)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(8)

        lay.addWidget(QLabel("技能英文目录 ID (如 api_doc_generator):"))
        id_edit = QLineEdit()
        id_edit.setPlaceholderText("例如: api_contract_master")
        lay.addWidget(id_edit)

        lay.addWidget(QLabel("技能中文显示名:"))
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("例如: RESTful API 契约设计大师")
        lay.addWidget(name_edit)

        lay.addWidget(QLabel("功能描述说明:"))
        desc_edit = QLineEdit()
        desc_edit.setPlaceholderText("简述该技能适用的场景与核心交付能力")
        lay.addWidget(desc_edit)

        lay.addWidget(QLabel("详细工作流指南与 Prompt 规范 (支持 Markdown):"))
        body_edit = QPlainTextEdit()
        body_edit.setPlainText(
            "# 角色定位与目标\n"
            "作为专业技能助手，在此场景下专注于...\n\n"
            "# 核心标准与步骤\n"
            "1. 分析输入的数据契约与结构；\n"
            "2. 生成符合 OpenAPI 3.0 标准的规范文档；\n"
            "3. 自动化校验字段完整性。"
        )
        lay.addWidget(body_edit, 1)

        b_row = QHBoxLayout()
        b_row.addStretch()
        c_btn = QPushButton("取消")
        c_btn.clicked.connect(dlg.reject)
        b_row.addWidget(c_btn)

        create_btn = QPushButton("🚀 真实物理落地生成")
        create_btn.setStyleSheet("background-color: #1e3a24; color: #7ee787; border: 1px solid #2e7d32; font-weight: bold;")
        def _do_create():
            sid = id_edit.text().strip()
            name = name_edit.text().strip() or sid
            desc = desc_edit.text().strip()
            if not sid:
                QMessageBox.warning(dlg, "缺少ID", "技能目录 ID 必须填写！")
                return

            target_folder = SKILLS_DIR / sid
            target_folder.mkdir(parents=True, exist_ok=True)
            content = (
                f"---\n"
                f"name: {name}\n"
                f"description: {desc}\n"
                f"version: 1.0.0\n"
                f"---\n\n"
                f"{body_edit.toPlainText()}\n"
            )
            (target_folder / "SKILL.md").write_text(content, encoding="utf-8")
            self._toggle_skill(sid, True)
            dlg.accept()
            self._refresh_skills_list()
            self.status_lbl.setText(f"🎉 技能 [{sid}] 已在 skills/ 目录物理落地并已启用！")
            self.extension_changed_signal.emit()

        create_btn.clicked.connect(_do_create)
        b_row.addWidget(create_btn)
        lay.addLayout(b_row)
        dlg.exec_()

    # ══════════════════════════════════════════════════════════
    #  Tab 3: 开发者身份配置 (Personas)
    # ══════════════════════════════════════════════════════════
    def _create_personas_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        intro = QLabel("选择或自定义大模型在代码开发模式下的核心开发者身份。不同身份直接决定了大模型的思维模型、技术选型倾向、代码风格与评审标尺：")
        intro.setStyleSheet("color: #858585; font-size: 12px;")
        intro.setWordWrap(True)
        lay.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        p_container = QWidget()
        p_container.setStyleSheet("background: transparent;")
        p_lay = QVBoxLayout(p_container)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.setSpacing(8)

        cur_p_id = self._get_active_persona_id()

        for pid, pdata in self.current_personas.items():
            card = self._create_persona_card(pid, pdata, is_active=(pid == cur_p_id))
            p_lay.addWidget(card)

        p_lay.addStretch()
        scroll.setWidget(p_container)
        lay.addWidget(scroll, 1)

        return w

    def _create_persona_card(self, pid: str, pdata: dict, is_active: bool) -> QWidget:
        card = QFrame()
        d = getattr(self, 'is_dark', True)
        if d:
            active_border = "border: 1px solid #007acc; background-color: #1a2733;"
            inactive_border = "border: 1px solid #333333; background-color: #252526;"
        else:
            active_border = "border: 1px solid #3b82f6; background-color: #dbeafe;"
            inactive_border = "border: 1px solid #cbd5e1; background-color: #f8fafc;"
        active_border_str = active_border if is_active else inactive_border
        card.setStyleSheet(f"""
            QFrame {{
                {active_border_str}
                border-radius: 6px;
                padding: 6px 10px;
            }}
        """)
        c_lay = QHBoxLayout(card)
        c_lay.setContentsMargins(12, 10, 12, 10)
        c_lay.setSpacing(12)

        vbox = QVBoxLayout()
        vbox.setSpacing(4)

        name_row = QHBoxLayout()
        t_lbl = QLabel(f"<b>{pdata.get('name', pid)}</b>")
        name_color = '#ffffff' if d else '#0f172a'
        t_lbl.setStyleSheet(f"font-size: 13.5px; color: {name_color}; background: transparent; border: none;")
        t_lbl.setMinimumWidth(0)
        name_row.addWidget(t_lbl)

        title_lbl = QLabel(pdata.get("title", ""))
        title_color = '#61afef' if d else '#1d4ed8'
        title_lbl.setStyleSheet(f"color: {title_color}; font-size: 11px; background: transparent; border: none;")
        title_lbl.setMinimumWidth(0)
        name_row.addWidget(title_lbl)

        active_color = '#7ee787' if d else '#15803d'
        if is_active:
            active_badge = QLabel("✓ 当前已激活")
            active_badge.setStyleSheet(f"color: {active_color}; font-weight: bold; font-size: 11px; background: transparent; border: none;")
            name_row.addWidget(active_badge)

        name_row.addStretch()
        vbox.addLayout(name_row)

        desc = QLabel(pdata.get("desc", ""))
        desc_color = '#a1a1aa' if d else '#475569'
        desc.setStyleSheet(f"color: {desc_color}; font-size: 11.5px; background: transparent; border: none;")
        desc.setWordWrap(True)
        desc.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        desc.setMinimumWidth(0)
        vbox.addWidget(desc)
        c_lay.addLayout(vbox, 1)

        # 切换使用按钮固定区（永远不被挤出视野）
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        btn_box.setContentsMargins(0, 0, 0, 0)

        if not is_active:
            use_btn = QPushButton("激活此身份")
            use_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            use_btn.setMinimumHeight(28)
            use_btn.setCursor(Qt.PointingHandCursor)
            use_btn.clicked.connect(lambda ch, p=pid: self._set_active_persona(p))
            btn_box.addWidget(use_btn)

        if pid == "custom":
            edit_btn = QPushButton("✏️ 编辑提示词")
            edit_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            edit_btn.setMinimumHeight(28)
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.clicked.connect(self._edit_custom_persona)
            btn_box.addWidget(edit_btn)

        c_lay.addLayout(btn_box, 0)
        return card

    def _load_personas(self) -> dict:
        personas = dict(DEFAULT_DEV_PERSONAS)
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                custom_p = cfg.get("custom_developer_personas", {})
                if custom_p:
                    personas.update(custom_p)
            except Exception:
                pass
        return personas

    def _get_active_persona_id(self) -> str:
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                return cfg.get("current_dev_persona", "fullstack_architect")
            except Exception:
                pass
        return "fullstack_architect"

    def _set_active_persona(self, pid: str):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                cfg["current_dev_persona"] = pid
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                self.status_lbl.setText(f"✅ 已激活开发者身份：{self.current_personas.get(pid, {}).get('name')}")
                self.extension_changed_signal.emit()
                self._rebuild_personas_tab()
            except Exception as e:
                QMessageBox.warning(self, "切换失败", str(e))

    def _rebuild_personas_tab(self):
        new_w = self._create_personas_tab()
        self.tabs.removeTab(2)
        self.tabs.insertTab(2, new_w, "👨‍💻 开发者身份设定")
        self.tabs.setCurrentIndex(2)

    def _edit_custom_persona(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("✏️ 编辑自定义开发者身份")
        dlg.resize(580, 420)
        lay = QVBoxLayout(dlg)

        cur_custom = self.current_personas.get("custom", {})

        lay.addWidget(QLabel("身份名称:"))
        name_edit = QLineEdit(cur_custom.get("name", "⚙️ 自定义开发者身份"))
        lay.addWidget(name_edit)

        lay.addWidget(QLabel("简要定位说明:"))
        desc_edit = QLineEdit(cur_custom.get("desc", ""))
        lay.addWidget(desc_edit)

        lay.addWidget(QLabel("专属系统级 System Prompt 指引与规范:"))
        prompt_edit = QPlainTextEdit()
        prompt_edit.setPlainText(cur_custom.get("prompt", ""))
        lay.addWidget(prompt_edit, 1)

        b_row = QHBoxLayout()
        b_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dlg.reject)
        b_row.addWidget(cancel_btn)

        save_btn = QPushButton("保存配置")
        save_btn.setStyleSheet("background-color: #0e639c; color: white; font-weight: bold;")
        def _save():
            new_p = {
                "id": "custom",
                "name": name_edit.text().strip() or "⚙️ 自定义开发者身份",
                "title": "Custom Developer",
                "desc": desc_edit.text().strip(),
                "prompt": prompt_edit.toPlainText().strip()
            }
            if CONFIG_PATH.exists():
                try:
                    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    cfg.setdefault("custom_developer_personas", {})["custom"] = new_p
                    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            self.current_personas["custom"] = new_p
            dlg.accept()
            self._rebuild_personas_tab()
            self.extension_changed_signal.emit()

        save_btn.clicked.connect(_save)
        b_row.addWidget(save_btn)
        lay.addLayout(b_row)
        dlg.exec_()
