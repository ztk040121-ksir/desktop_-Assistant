# 🌸 Desktop AI Assistant v4.0.0 (NovaDesk 桌面 AI 智能助理 & 全栈 IDE 工作台)

<div align="center">

![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-41CD52?style=flat-square&logo=qt&logoColor=white)
![Live2D](https://img.shields.io/badge/Live2D-Cubism%204-E6526F?style=flat-square)
![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek--R1%20%7C%20Qwen-007AFF?style=flat-square)
![Ollama](https://img.shields.io/badge/Local%20AI-Ollama%20(16K%20Ctx)-FF6800?style=flat-square)
![MCP](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol-black?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

<br/>

**基于 PyQt5 + Live2D 官方正版桃濑日和 (Hiyori) + 本地 Ollama (DeepSeek-R1 / Qwen) & 外部云端大模型的次世代桌面 AI 智能陪伴助理与全功能双模工作台**

[特性亮点](#-v400-核心重磅特性) • [系统架构](#️-项目工程架构) • [快速开始](#-快速开始) • [操作指南](#-模式与操作指南) • [开源声明](#-开源许可与声明)

</div>

---

## 📢 v4.0.0 版本重大发布声明 (Release v4.0.0)

我们非常自豪地正式发布 **Desktop AI Assistant v4.0.0 (NovaDesk 4.0)**！本次发布是项目诞生以来最具里程碑意义的跨越式重构。

在保留 v3.0 广受好评的灵动 Live2D 伴侣与全功能办公工作台基础之上，v4.0 深度融合 **Antigravity 现代智能体软件工程理念**，开创性地打造了 **「全能办公助理 (Office Mode)」与「专业 IDE 开发者工作区 (Dev Mode)」一键双模无缝切换架构**。从代码阅读、方案规划、工程编写、差异对比 (Diff)，到沙箱终端执行与报错自愈 (Auto-Healing)，再到原生 MCP (Model Context Protocol) 插件协议体系与移动端跨端推送，让 NovaDesk 真正成为集陪伴、办公与全栈开发于一体的终极桌面生产力中枢。

---

## 🌟 v4.0.0 核心重磅特性 (Features & Highlights)

### 1. 💻 双模式一键无缝切换 (Office Mode & Dev Mode)
- **极客双轨架构**：顶部导航栏一键在「办公」与「开发」工作模式间自由穿梭，状态独立隔离、丝滑无感。
- **办公模式 (Office Mode)**：专注日常陪伴、多会话知识库、头条热搜检索、旅行规划、PPT 生成与办公自动化。
- **开发模式 (Dev Mode)**：为严肃软件工程量身打造，深度绑定本地项目物理工作空间，提供媲美现代主流 IDE 的极客编程环境。

### 2. 🖋️ 像素级沉浸式 VSCode 风格代码编辑器
- **全功能现代 Tab 标签栏**：
  - 智能类型图标识别：Python🐍、Java☕、Markdown📝、JSON、HTML、CSS、JS、TS、Diff 及方案等文件各有专属彩色图标；
  - 便捷操作：支持每个小 Tab 专属关闭按钮、鼠标滚轮中键点击瞬间关闭 Tab、拖拽排列；
  - 样式与交互对齐 VSCode：暗黑磨砂质感、悬停微动效与高亮状态指示。
- **专业代码编辑体验**：集成语法高亮着色、精准行号展示、括号匹配、等宽字体与智能缩进。
- **文件差异可视化对比 (Diff Viewer)**：内置红绿双色代码变动对比视窗，一键审阅 AI 修改的每行代码并支持单项或全量批准合入。

### 3. 📋 方案规划先行体系 (Planning Mode: Plan-then-Execute)
- **杜绝 AI 盲目乱改代码**：面对复杂工程任务，系统自动进入专业方案规划模式，大模型自主进行工作区只读探测（`read_workspace_file`、`list_workspace_files`），并生成详尽的技术实施方案。
- **独立方案文档主屏渲染**：实施方案自动提取并在主屏幕代码区以独立方案文档形式打开预览。
- **审批门控卡片 (Proceed Gate)**：在用户审阅方案并点击【批准并执行 (Proceed)】之前，严禁向磁盘写入任何代码或执行写操作，将工程决策权牢牢掌控在开发者手中。

### 4. 🔄 终端沙箱执行与报错自愈闭环 (Auto-Healing)
- **真实沙箱命令执行**：内置 `run_workspace_command`，智能体可自主调度运行本地编译器、测试套件与脚本命令，执行状态以原生极客终端卡片实时流式反馈。
- **闭环报错自愈机制**：当编译或测试返回非 0 退出码或异常报错（如 `AssertionError`、`SyntaxError`、`ImportError`）时，智能体自动启动自愈逻辑：分析报错根因 ➔ 修改源码 ➔ 重新执行测试，直到所有测试绿灯通过！

### 5. 🧠 AI 核心引擎 7.0 (AI Engine 7.0) 全面升级
- **深度思维链捕获与时间戳统计**：
  - 原生支持 DeepSeek-R1、Qwen-Thinking、OpenAI o1/o3 的思维链推理过程；
  - 思考过程实时流式展开，任务完成后优雅折叠为 `Worked for Xs ›` 极简胶囊，正文输出干脆利落。
- **Ollama 16K 超长上下文（`num_ctx: 16384`）原生适配**：
  - 本地模型默认自动分配 16,384 tokens 显存上下文，彻底解决本地大模型长上下文 4096 溢出报错；
  - 内置多轮对话滑动窗口 Token 预算安全截断，长期长文本对话永远稳定流畅。
- **零延迟流式工具调用调度器**：
  - 创新性的预探测缓冲区机制，精准区分普通文字与工具代码块，彻底解决流式输出首字重复等历史瑕疵。

### 6. 🔌 Model Context Protocol (MCP) 深度集成生态
- **标准协议客户端**：内置 `mcp_stdio_client.py` 标准输入输出协议通信机制与 `mcp_tool_bridge.py` 工具桥接器。
- **第三方 MCP 服务热插拔**：完美兼容官方及社区任意标准 MCP 服务节点，无需重启应用即可动态挂载与卸载。
- **本地 SQLite MCP 支持**：打通工作区轻量化数据库检索与结构化数据交互。
- **扩展中心管理面板 (`dev_extension_manager.py`)**：可视化管理已装配的 MCP 连接器与插件。

### 7. 🧩 50+ 真实生产力工具与全场景专家矩阵
- **新增高级工程套件**：
  - 🤖 **智能体开发 (`agent_dev_tools`)**：自动化构建子 Agent 角色与逻辑流；
  - 🚀 **CI/CD 自动化 (`cicd_tools`)**：持续集成流水线配置与构建脚本编写；
  - 📚 **文档工程 (`doc_engineering_tools`)**：架构白皮书、API 契约文档规范生成；
  - 🎬 **视频脚本创作者 (`video_script_tools`)**：分镜头分段脚本与分镜头语言创作；
  - 🛠️ **技能创建器 (`skill_dev_tools`)**：零代码动态封装专属 SKILL.md 技能包。
- **经典实用工具生态全量保持**：
  - 高德生活出行导航、12306 车票、快递 100 追踪、小红书运营操盘、全网新闻热搜、Python 解释器、PPT 大师、多模态图文解析。

### 8. 📱 移动端推送通知 (Mobile Push)
- 支持通过跨平台推送通道（如 Server 酱、Bark、Webhook 等）将长时间运行的编译、构建测试、自动化任务执行进度与完成状态实时推送到开发者手机移动端，无需守在屏幕前。

### 9. 🌸 正版 Live2D 桃濑日和 (Hiyori) 灵动陪伴
- **高帧率 WebGL 渲染**：原汁原味官方日和模型，呼吸起伏与全身灵动姿态。
- **鼠标视线与打字键盘联动**：全局跟随鼠标视线移动，键盘敲击时角色桌面实时同步敲击交互。
- **极简悬浮与快捷交互**：左键拖拽随心摆放，左键双击瞬间唤醒工作台，右键托盘与快捷菜单自由掌控。

---

## 🛠️ 项目工程架构

```
desk_tools/
├── assets/                    # 图标与静态视觉资产
│   └── icons/                 # 应用程序各尺寸图标与 SVG 资源
├── characters/                # Live2D 角色资产
│   └── default/
│       ├── libs/              # PixiJS 与 Live2D Cubism Core 运行环境
│       ├── live2d_model/      # 桃濑日和 (Hiyori) 官方正版模型
│       └── renderer.html      # WebGL 高性能透明通道渲染页
├── core/                      # 核心系统与基础设施层
│   ├── ai_engine.py           # AI Engine 7.0 (Ollama 16K/云端双轨 + 思维链 + 工具自愈)
│   ├── memory_manager.py      # SQLite 多会话独立隔离持久化 (WAL 高并发)
│   ├── emotion_system.py      # 实时交互情绪状态计算引擎
│   ├── pet_scheduler.py       # 自动化流水线调度器与定时任务引擎
│   ├── security_guard.py      # 工作空间文件越界拦截与安全沙箱
│   ├── file_diff_tracker.py   # 代码文件变更捕获与统一 Diff 差异追踪器
│   ├── mcp_stdio_client.py    # 标准 MCP (Model Context Protocol) 进程客户端
│   ├── mcp_tool_bridge.py     # MCP 工具链桥接与协议动态挂载中心
│   ├── local_sqlite_mcp.py    # 工作空间本地 SQLite MCP 服务端
│   ├── mobile_push.py         # 移动端消息推送与跨端通知通道
│   ├── voice_input.py         # 语音输入录制与 Whisper 离线识别
│   ├── voice_output.py        # Edge-TTS 高拟真语音合成与原生音频播报
│   ├── plugin_manager.py      # 生产力插件生命周期与工具注册管理器
│   └── web_server.py          # 本地静态资源与模型桥接微服务
├── plugins/                   # 生产力插件生态 (50+ 真实技能工具)
│   ├── workspace_dev_tools.py # 工作空间文件读写与终端命令执行沙箱
│   ├── agent_dev_tools.py     # 智能体工作流设计与编排工具
│   ├── cicd_tools.py          # CI/CD 自动化与工程发布脚本工具
│   ├── doc_engineering_tools.py # 文档工程化与架构设计工具
│   ├── skill_dev_tools.py     # 动态技能套件创建器
│   ├── web_dev_tools.py       # 现代 Web 前端开发工具集
│   ├── video_script_tools.py  # 短视频分镜头脚本与文案策划
│   ├── amap_life_tools.py     # 高德生活与出行路径规划
│   ├── ticket_12306_tools.py  # 12306 列车时刻与余票检索
│   ├── kuaidi100_tools.py     # 快递物流单号实时追踪
│   ├── ppt_tools.py           # PPT 自动生成与排版工具
│   ├── file_tools.py          # 本地文件深度解析与格式转换
│   ├── python_interpreter.py  # Python 本地安全解释器
│   ├── web_search_news.py     # 实时头条新闻与全网搜索
│   └── ...                    # 更多场景化专业插件
├── skills/                    # 专业技能套件 (SKILL.md 标准规范定义)
│   ├── agent_development/     # 智能体开发规范
│   ├── cicd_automation/       # 自动化发布规范
│   ├── doc_engineering/       # 架构设计文档规范
│   ├── web_development/       # 现代 Web 工程规范
│   └── ...                    # 20+ 激活技能工作流
├── ui/                        # 现代桌面人机交互界面
│   ├── chat_window.py         # NovaDesk v4.0 全功能办公工作台 (双滑动视口/专家大厅/设置)
│   ├── dev_mode_view.py       # 开发者工作台主视窗 (多标签编辑器/执行轨迹卡片/Diff视窗)
│   ├── code_editor.py         # 现代暗黑高亮代码编辑器核心组件
│   ├── dev_extension_manager.py # MCP 扩展管理与连接器装配中心
│   ├── desktop_pet.py         # Live2D 桌面宠物透明悬浮窗与鼠标手势互动
│   ├── hands_overlay.py       # 键盘打字桌面同步敲击动画
│   └── system_tray.py         # Windows 系统托盘菜单
├── config.json                # 应用程序用户全局配置文件
├── main.py                    # 应用程序唯一起始主入口
├── requirements.txt           # Python 依赖清单
├── install.bat                # 一键自动化环境安装脚本
└── start.bat                  # 一键静默启动脚本
```

---

## 🚀 快速开始

### 1. 环境准备
推荐使用 **Python 3.10 或 3.11**。

```bash
# 克隆仓库
git clone https://github.com/ztk040121-ksir/desktop_-Assistant.git
cd desktop_-Assistant
```

### 2. 安装依赖
直接双击运行根目录的 `install.bat`，或在命令行执行：
```bash
pip install -r requirements.txt
```

### 3. 配置大模型 (任选一种或同时配置)

#### 选项 A：使用本地 Ollama (推荐，极佳的数据私密性)
1. 下载并安装 [Ollama](https://ollama.com/)；
2. 拉取你喜欢的开源大模型：
   ```bash
   ollama pull deepseek-r1:14b
   # 或
   ollama pull qwen2.5:7b
   ```
3. NovaDesk 已原生将本地模型上下文设置为 `16384` (16K)，可直接顺畅体验复杂编程与长文本对话。

#### 选项 B：使用云端大模型 API
在应用内点击右上角「设置」➔「模型与端点」，支持一键填入 DeepSeek 官方 API、OpenAI 兼容格式接口、SiliconFlow、OhMyGPT 等，即填即用。

### 4. 一键启动
在项目根目录下双击：
```bash
start.bat
```
或在终端执行：
```bash
python main.py
```

---

## 🎮 模式与操作指南

### 1. 模式自由切换
- **办公模式**：在界面顶部导航栏点击 **「办公」** 按钮，畅享日常任务会话管理、多工作空间归类、多模态识图与日常工具。
- **开发模式**：在界面顶部导航栏点击 **「开发」** 按钮，瞬间进入全功能极客编程环境，左侧代码树、中间多标签编辑器、右侧智能体执行控制台与底端终端联动。

### 2. 开发者快捷指令
在开发模式右侧输入框中支持以下原生工程模式指令：
- **常规问答**：直接输入需求（如 `帮我写一个快速排序算法`），AI 将直接提供精炼技术解析；
- **`/plan [需求]`**：强制激活架构实施方案规划模式，大模型只看不写，输出严谨方案文档并呈现在主屏幕待你审批；
- **`/review`**：对当前编辑器激活的代码文件进行五维综合健康度体检（规范、健壮、性能、安全、可维护）；
- **`+ 按钮`**：一键将本地工程文件或图片附件引用送入对话上下文。

### 3. 伴侣交互手势
| 交互动作 | 响应效果 |
| :--- | :--- |
| **双击人物** | 瞬间平滑淡入唤醒 NovaDesk v4.0 全功能工作台 |
| **右键人物** | 唤出快捷控制菜单（💬 对话 / ⚙️ 设置 / 💻 切换模式 / 👁️ 最小化 / ❌ 退出） |
| **拖拽身体** | 鼠标左键长按可在桌面上任意拖动摆放桌宠位置 |
| **敲击键盘** | 开发者打字时光标处角色同步出现敲键盘动作，伴随专注音效 |

---

## 📄 开源许可与声明

- 本项目所有源码遵循 **[MIT License](LICENSE)** 协议开源。
- Live2D 模型版权归原作者及 Live2D Inc. 所有，仅供个人学习、技术研究与非商业交流使用。
- 欢迎通过 Issue 与 Pull Request 为本项目提交宝贵的改进建议与功能扩展！
