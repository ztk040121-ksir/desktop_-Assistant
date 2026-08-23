# 🌸 Desktop AI Assistant (智能桌面伴侣智能体)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://pypi.org/project/PyQt6/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20%7C%20DeepSeek--R1-orange.svg)](https://ollama.com/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

> 一款基于 **PyQt6 + 本地大语言模型 (DeepSeek-R1 / Qwen2.5) + ReAct 智能体工具执行引擎** 构建的高颜值、企业级多模态桌面 AI 伴侣与全能助理系统。

---

## 🌟 项目亮点与核心功能

### 1. 🎭 3D/2.5D 高清透明挂件与生动的肢体动作
* **零瑕疵透明渲染**：采用影视级 **绿幕色度键（Chroma Keying）与 32 位 ARGB 序列帧引擎**，彻底告别传统 GIF 256 色导致的黑色杂质、边缘噪点与白底残留。
* **多姿态真实肢体动作**：
  * 🌸 **Idle 待机**：浮空坐姿微笑呼吸，伴随周期性自然轻晃。
  * 🏃 **Walk 桌面小跑漫步**：**真正的双腿大步迈步奔跑、双手握拳前后摆动、双马尾向后飞扬**；待机时会在任务栏上方自主巡逻走动，碰撞屏幕边缘自动折返。
  * 🙌 **Happy 欢呼雀跃**：**真正举起双臂欢呼跳跃、双眼笑成可爱月牙、雀跃欢跳**，点击互动时触发。
  * 😴 **Sleep 抱枕安睡**：**真正抱着软绵绵的白色小枕头侧躺在桌面上安静呼噜睡觉**。
* **物理交互体系**：支持鼠标自由拖拽、位置记忆存储、桌面边缘吸附与全状态机自动复位。

### 2. 🧠 强大的本地/云端多模型大脑
* **本地旗舰推理模型驱动**：
  * 默认接入 **`DeepSeek-R1:14B`（140 亿参数深度推理模型）**，开启 `<think>` 深度慢思考思维链，具备极高智商，擅长复杂逻辑推理、算法解题与深度分析。
  * 智能显存/内存协同（RTX 3060 6GB 显存分配 4.3GB + 系统内存 4.8GB），兼顾极低待机功耗（待机 GPU 0%）与高效推理。
* **多服务商与多模型一键热切换**：
  * 支持 **Ollama 本地模型库**（`deepseek-r1:14b`, `deepseek-r1:7b`, `qwen2.5:7b`, `qwen2.5:3b` 等）。
  * 支持 **OpenAI / Claude / 自定义兼容 API**。
  * 内置 **配置热重载驱动（Config-Driven Hot-Reloading）**，在 UI 界面点击切换即可实时覆写 `config.json` 并动态热重载内存，无需重启程序。

### 3. 🛠️ 真正的 ReAct 智能体工具调用（Real Tool Calling）
不同于普通只会在对话框里产生“语言幻觉”的聊天机器人，本系统拥有**真正的操作系统级工具执行引擎**：
* 📝 **真实文件读写与修改**：精准识别文件路径，自动调用系统底层 I/O 将内容真实写入或追加至本地文件（如桌面文档、代码脚本），支持文本读取与格式解析。
* 📂 **桌面/文件夹自动化整理**：按图片、文档、表格、压缩包等分类自动归档混乱的文件夹。
* 🖥️ **系统控制与辅助**：支持屏幕截图保存至桌面、打开指定应用程序等能力。

### 4. 💎 现代化暗黑磨砂玻璃对话中心 (Modern Dark Glassmorphism)
* **SSE 实时流式打字机**：流式推送生成内容，首字响应极快，打字机式平滑输出。
* **自适应包裹气泡 (Adaptive Hug-Bubble)**：根据文本长短智能伸缩气泡宽度，消除空旷留白与前导多余换行符。
* **一键集成控制栏**：对话窗口顶部整合了「🌸 宠物信息」、「✨ 欢呼互动」、「⚙️ 管理中心」、「🗑️ 一键清空对话」等全部入口。
* **多轮记忆与智能搜索**：基于 SQLite 数据库持久化存储每一轮对话，支持管理中心关键词秒级检索与统计。

---

## 🏛️ 系统架构设计

```
                            ┌────────────────────────────────────────┐
                            │          Desktop AI Assistant          │
                            └────────────────────┬───────────────────┘
                                                 │
                   ┌─────────────────────────────┼─────────────────────────────┐
                   │                             │                             │
                   ▼                             ▼                             ▼
        ┌──────────────────────┐      ┌──────────────────────┐      ┌──────────────────────┐
        │      UI 交互表现层    │      │    Core 核心智能中枢  │      │   Plugins 工具执行层  │
        ├──────────────────────┤      ├──────────────────────┤      ├──────────────────────┤
        │ • DesktopPet (小人)   │      │ • AIEngine (推理/流式)│      │ • file_tools (文件IO) │
        │ • ChatWindow (聊天窗)│ ◄──► │ • Memory (SQLite存储)│ ◄──► │ • comp_ctrl (系统控制)│
        │ • ControlPanel (面板)│      │ • Emotion (情感状态机)│      │ • wechat_tools (生态) │
        │ • SystemTray (托盘)  │      │ • PluginManager(插件)│      │ • Custom Plugins     │
        └──────────────────────┘      └──────────────────────┘      └──────────────────────┘
                   │                             │                             │
                   ▼                             ▼                             ▼
         [ PyQt6 / 32-bit ARGB ]      [ Ollama / DeepSeek-R1 ]         [ 本地 OS / 硬盘 / 应用 ]
```

---

## 🐞 开发实战与工程踩坑排错记录 (Engineering Pitfalls & Solutions)

在从零搭建与架构迭代过程中，团队遇到了多项极具代表性的底层工程难题，特此记录完整解决方案：

### 1. 对话切片丢失最新提问 Bug
* **问题现象**：AI 无法回答用户最新提出的问题，经常自言自语或回复前一句。
* **根因分析**：在 `ai_engine.py` 的上下文历史数组拼接中使用了 `messages[:-1]`，导致每次在发送给模型时硬生生切除了最新一条用户输入。
* **解决方案**：重构上下文管理逻辑，完整保留全生命周期的上下文列表，并引入 20 轮动态窗口滑动机制。

### 2. 图像抠图与 256 色调色板黑斑/白框缺陷
* **问题现象**：小人立绘身体出现黑色孔洞，或身体下方残留一大块白色矩形底座。
* **根因分析**：
  1. 传统 GIF 格式仅支持 1-bit 透明度，无法呈现半透明羽化过渡，量化后形成硬黑边与杂斑；
  2. 使用简单的颜色阈值抠图时，小人的白围裙、白发饰和脸部高光与白色背景重叠，被误抠穿透；
  3. 简单矩形保护区又导致两腿之间的白色地面阴影被完整保留。
* **解决方案**：全面升级为**影视级荧光绿幕色度键（Chroma Keying）+ 32 位 ARGB 真彩色 PNG 序列帧播放器**。绿色通道精准分离，实现 100% 纯净无孔洞、无白边的丝滑透明呈现。

### 3. 大语言模型“幻觉式应答”与真实工具落地
* **问题现象**：当要求 AI 写入文件时，AI 仅用文字礼貌回复“已为您写入完成”，而实际上桌面文件空空如也。
* **根因分析**：缺少 ReAct 智能体拦截与底层真实 Python 函数调用的执行桥梁。
* **解决方案**：在 `AIEngine` 中构建结构化 tool_call 拦截解析器与**智能意图直连执行路由**，在检测到文件操作意图时，直接由系统在本地真实执行 `open(file, 'w')` 写入文件，并将真实的执行状态反馈给用户。

### 4. PyQt 窗口最小化后双击唤醒失效
* **问题现象**：聊天窗口最小化到任务栏后，再次双击桌宠小人无法将其弹回屏幕前。
* **根因分析**：在 Windows + PyQt6 体系下，当窗口处于 `WindowMinimized` 状态时，单独调用 `raise_()` 或 `activateWindow()` 无法解除最小化状态。
* **解决方案**：在呼出逻辑中加入 `if window.isMinimized(): window.showNormal()`，确保任何状态下双击都能从任务栏瞬间复位并弹至最前。

### 5. 管理中心窗口层级遮挡
* **问题现象**：打开管理中心时，窗口被置顶的聊天窗口遮挡在后方。
* **根因分析**：聊天窗口设置了 `WindowStaysOnTopHint` 置顶属性，而管理中心此前为普通窗口。
* **解决方案**：为管理中心同步配置 `WindowStaysOnTopHint` 属性，并在打开时主动调用 `raise_()` 和 `activateWindow()` 保证其层级始终位于最前。

### 6. DeepSeek-R1 思考标签与前导多余空行清洗
* **问题现象**：DeepSeek-R1 在输出 `<think>` 思考过程结束后，气泡顶部总是留有一大片刺眼的空白行。
* **根因分析**：模型生成思考闭合标签后会附带 `\n\n`，流式传输时渲染到了 UI 第一行。
* **解决方案**：在文本流清洗器中加入正则过滤器 `_clean_text` 与 `lstrip()`，自动去除前导多余换行符，让文字严密贴合气泡顶部内边距。

### 7. 大模型存储爆满 C 盘与全局迁移
* **问题现象**：Ollama 默认将数十 GB 的模型文件下载至 C 盘 AppData，导致系统盘红字告警。
* **解决方案**：设置 Windows 全局环境变量 `OLLAMA_MODELS=E:\\Study_Cache\\model\\ollama`，并编写迁移脚本将 Blobs 和 Manifests 完整移至 E 盘，在 `start.bat` 中强制注入环境变量，确保 C 盘空间 0 占用。

---

## 🚀 快速开始与部署指南

### 1. 环境准备
* 操作系统：Windows 10 / 11
* Python 版本：Python 3.10+ (推荐 Anaconda 环境)
* 本地推理环境：[Ollama 官方客户端](https://ollama.com/)

### 2. 下载并安装依赖
```bash
# 克隆仓库
git clone https://github.com/ztk040121-ksir/desktop_-Assistant.git
cd desktop_-Assistant

# 安装依赖
pip install -r requirements.txt
```

### 3. 模型拉取（以 DeepSeek-R1 14B 为例）
```bash
# 拉取 14B 深度推理模型（约 9.0GB，存放于 E 盘）
ollama pull deepseek-r1:14b

# 或拉取平衡型 7B 模型
ollama pull qwen2.5:7b
```

### 4. 一键启动
双击运行根目录下的 `start.bat` 即可一键启动桌宠：
```bat
start.bat
```

---

## 📁 目录结构说明

```
desktop_-Assistant/
├── assets/                     # UI 图标与全局静态资源
├── characters/                 # 桌宠角色资源库
│   └── default/                # 默认角色 (包含 idle, walk, happy, sleep 等动作序列)
├── core/                       # 核心引擎层
│   ├── ai_engine.py            # AI 多后端调度与 Tool Calling 执行引擎
│   ├── memory_manager.py       # SQLite 对话记忆数据库管理
│   ├── emotion_system.py       # 情绪状态机与表情切换
│   ├── plugin_manager.py       # 插件动态扫描与注册中心
│   ├── voice_input.py          # 语音识别输入模块
│   └── voice_output.py         # 异步非阻塞语音播报模块
├── plugins/                    # 扩展插件库
│   ├── file_tools.py           # 真实本地文件读写与整理工具
│   ├── computer_control.py     # 屏幕截图、应用启动等系统控制
│   └── wechat_tools.py         # 微信与社交通讯扩展支持
├── ui/                         # PyQt6 现代化界面层
│   ├── desktop_pet.py          # 桌面透明小人主窗体（动作/物理/漫步引擎）
│   ├── chat_window.py          # 现代化磨砂玻璃对话窗口（流式打字机）
│   ├── control_panel.py        # 桌宠管理中心（模型/插件/记忆/配置面板）
│   └── system_tray.py          # Windows 系统托盘与右键菜单
├── config.json                 # 全局运行配置文件
├── requirements.txt            # Python 依赖清单
├── start.bat                   # Windows 一键启动脚本
└── README.md                   # 项目综合使用与架构设计文档
```

---

## 🗺️ 版本演进规划 (Roadmap)

- [x] **v1.0.0 (当前版本)**：
  - [x] 32 位 ARGB 绿幕色度键无损透明小人与 4 大真实肢体动作序列
  - [x] DeepSeek-R1 14B / 7B 本地推理引擎与流式打字机
  - [x] 真实文件读写 (I/O Tool Calling) 智能体系统
  - [x] 现代化 Dark Glassmorphism 聊天面板与配置热重载管理中心
  - [x] 自主桌面巡逻漫步与物理重力体系
- [ ] **v1.5.0 (近期规划)**：
  - [ ] 接入 DuckDuckGo / Bing 联网搜索插件（实时获取互联网最新信息）
  - [ ] 个人本地知识库 (RAG) 向量数据库集成（支持本地 PDF/代码库深入问答）
- [ ] **v2.0.0 (远期规划)**：
  - [ ] Live2D / 3D Skeletal Mesh 模型实时渲染支持
  - [ ] 多 Agent 协作与自动化工作流（自动写代码并执行脚本）

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源许可证。欢迎提交 Issue 与 Pull Request！