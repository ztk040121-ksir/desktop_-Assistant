# desk_tools 全项目代码审计报告

> 审计日期：2026-09-01
> 审计方式：逐文件通读（main.py / core 全部 9 个模块 / ui 全部 6 个文件 / plugins 全部 21 个插件 / renderer.html / 配置与依赖清单），关键结论均经二次 grep 复核确认。
> 本次审计**未修改任何业务代码、未运行任何程序**。

---

## 一、总体结论

项目呈明显的"两极分化"：

- **真实能跑的主干（约 30%）**：Live2D 本地渲染（本地 HTTP 服务 + 本地 libs，无 CDN）、聊天发送与流式渲染、模型增删改/测试连接/切换、工作空间切换、附件读取、PPT/Excel/Word 文档生成（openpyxl / python-pptx / python-docx 真实产出文件）、系统控制类工具（截图/音量/锁屏）。
- **表面实现 / 造假的部分（约 70%）**：多会话记忆、自动化流水线、连接器生态、安全权限、情绪联动、语音输入、以及快递/12306/小红书/Chrome性能 等一大批假数据插件。

一句话画像：**一个高保真 UI 壳子，配上一套"关键词 → 硬编码假回复"的伪智能引擎**。文件头声称的"100% 真实执行"大量名不副实。

---

## 二、空架子 / 假实现清单（按危害排序）

### 2.1 记忆持久化：整个多会话体系是幻觉 【最严重】

- `core/memory_manager.py` 的 `add_message()`（第 96 行）**全项目零调用**（已 grep 复核）。
- `chat_window.py` 的 `_do_send`（5868-5886）只往 UI 加气泡并起线程调 `chat_stream`，从不写 SQLite。
- 后果链：`_load_session` 恢复历史（读 `get_session_messages`）、"导出 Markdown"、"保存到工作空间"、启动恢复上次会话——全部依赖的消息表**永远是空的**。重启后所有会话都是 0 条消息。
- README 宣称的"内存与持久化同步清理"无从谈起。

### 2.2 AI 引擎的假回复路由 `core/ai_engine.py::_fast_local_route`（345-838 行）

- 用户消息包含 "python" 一词 → 不问模型，直接返回**硬编码的斐波那契演示脚本**（703-722 行）。
- 包含 "ppt" → 硬编码"微积分数学总结"PPT（693-698 行）。
- "校园求职"、"毕业论文选题"、"前端+开发"、"测试用例+pytest" → 全部返回写死的演示文案（465-665 行），专家的 system_prompt 根本没参与。
- "历史上的今天"：只有 8 月 26/27 两天有真数据，其余任何日期返回"发生过人类科技与文明发展的重大里程碑事件"这种废话（372-374 行）。
- 每日英语单词 / 睡前故事 / 工作周报：**全是固定字符串**，与"自动化流水线真实执行"的注释完全相反。
- 异常兜底（876 行）：模型离线时返回"🤖 智能体已就绪，正在为你执行相应工作流"——**伪装成功，掩盖错误**。
- 天气默认城市广州、12306 默认广州→深圳、快递无单号时用假单号 SF188273928192 查询。

### 2.3 自动化流水线：表单是布景，执行是假的（chat_window.py 4574-4601 / 2665-2668）

- 保存时只读取名称、提示词、一个时间点；表单上的**频率模式（周期/间隔/单次）、每天/工作日/每周/每月、周一~周日按钮、单次日期、生效日期区间、连接器授权、两个推送开关、完全访问权限**——八类控件全部被忽略。
- 到点触发时**只写一条 "success" 日志 + 状态栏提示，从不把 prompt 交给 AIEngine 执行**。运行记录页显示"已成功执行"是伪造的。
- `PetScheduler` 的提醒列表纯内存，不持久化、不支持重复执行，重启全丢。
- `ai_engine.py:384` 的 `【自动化流水线立即触发:...】` 路由，全项目无任何调用点能拼出这个字符串——死逻辑。

### 2.4 连接器生态：30+ 连接器全是硬编码静态字典（chat_window.py 3884-3918）

- 通达信、腾讯自选股、QQ邮箱、腾讯会议、飞书、钉钉、百度网盘、GitHub、Notion、天眼查……全部是 UI 内硬编码，不联网、不读 `mcp_config.json`。
- 点"连接"只做 `connected_set.add(cid)` + 写一个**没有任何消费者**的 config 键（已 grep 复核 `connected_connectors` 只在 chat_window 自身出现）。
- "自定义连接器"按钮只弹一句状态栏提示，什么都不做。

### 2.5 安全权限切换：placebo（chat_window.py 5322-5332）

- 调用 `SecurityGuard.get_instance().set_mode(mode)` —— **该方法不存在**（实际是 `update_config`），抛 AttributeError 被 `except: pass` 吞掉（已复核）。
- 权限值三处不一致：UI 第二版发 `"full"`，旧版死代码发 `"full_auto"`，`is_full_access()` 判断 `"full_auto"`。
- 切换工作空间也不更新沙箱根目录，`SecurityGuard` 的 workspace_root 永远停在启动时的 `Path.cwd()`。

### 2.6 情绪系统 → Live2D 联动：双重死链（已复核）

- `core/emotion_system.py` 的 `update_by_text()` / `reset_to_idle()` **全项目零调用**——情绪永远是 IDLE。
- `characters/default/renderer.html` 513-514 行：`window.triggerAction = function(a,d) {};` `window.triggerEmotion = function(e) {};` —— **空桩**。renderer 内部其实有 17 个程序化动作，但没接到这两个入口上。
- `desktop_pet.py` 226-228 注册的情绪回调链从头到尾不会触发。README 宣传的"情绪联动表情"不存在。

### 2.7 语音输入：实例创建了、参数传了、界面没有按钮

- `main.py` 创建了 `VoiceInput`/`VoiceOutput`，但 `desktop_pet._open_chat` 创建 ChatWindow 时**不传**，ChatWindow 收了 `voice_input` 形参也不保存（grep 证实全文件唯一命中是形参声明行）。
- 聊天页输入框没有麦克风按钮；`push_to_talk_key: ctrl` 配置无人消费。

### 2.8 纯假数据插件（会向用户输出编造的"事实"）

| 插件 | 造假方式 |
|---|---|
| `kuaidi100_tools.py` | **无任何网络请求**，用 `datetime.now()-timedelta` 伪造 4 条物流轨迹，编造快递员"李师傅 13800138000"（已亲自复核全文 63 行） |
| `ticket_12306_tools.py` | 车次/票价/余票/时刻表全部硬编码 5 条；`import httpx` 和 `CITY_TO_TELECODE` 是死代码伪装 |
| `xiaohongshu_mcp_tools.py` | 搜索结果、"甜桃小可 1.8 万赞"等笔记、评论池——全编造；`xhs_post_smart_comment` 从未向小红书发请求却返回"已成功推送" |
| `amap_life_tools.py` | 路线规划 try 块里 import httpx 后**直接 pass**（55-60 行，已复核）；任意两点距离兜底 **32.5 公里**；POI 永远是同三家咖啡店；天气失败时静默返回假"28°C 多云" |
| `chrome_devtools_tools.py` | 任意 URL 的"性能洞察报告"永远是同一份 98 分硬编码数据 |
| `health_calculator_tools.py` | 无论结果多糟固定输出"整体处于良好水平" |
| `web_search_news.py` | 真 API（网易/DuckDuckGo）失败时静默混入硬编码假新闻 |

### 2.9 名不副实 / 半假

- `firecrawl_tools.py`：与 Firecrawl 官方 API 无关（无 key、无请求），自研抓取冒用品牌，失败时静默降级。
- `wechat_tools.py`：pyautogui 模拟键鼠，**盲点固定坐标** `(screen_w//2, screen_h-150)`——微信窗口不在预期位置就把消息/剪贴板内容发到任意前台窗口；"读消息"只截图存临时文件，返回"需要配置视觉模型"，功能实际不可用。
- `xhs_publisher_tools.py`：只做"打开发布页+复制文案"，返回文案却宣称"发布流程已完成"。
- `knowledge_base_tools.py`：关键词重合度冒充"RAG 向量检索"，无 embedding；知识库路径硬编码 `E:\Demo\desk_tools\data\knowledge_base`。
- `creative_article_tools.py`：f-string 模板冒充"AI 生成"。
- `file_tools.py::create_excel_table`：`rows_data` 参数被完全忽略，无条件写入 6 行硬编码员工演示数据（张伟/李娜/王敏…），返回时还宣称"包含用户提供的 6 行结构化数据"。

### 2.10 UI 层摆设控件汇总（chat_window.py）

- 每条 AI 消息固定显示 "⚡ 共消耗 ◇ 8.61"——**Token 统计是硬编码假数字**（1565-1566 行）。
- 👍/👎 按钮无任何 clicked 连接；"重试"信号 emit 的是 AI 回复原文（语义也错）。
- 会话右键"分享会话"只复制标题文案并谎称分享成功；"批量操作"只弹提示；"打开会话所在文件夹"永远打开程序根目录。
- 对话页"搜索会话内消息"按钮未连接任何槽——死按钮。
- 自动化页"Auto 模型"菜单硬编码 4 个模型名，与 config.models_list 无关。
- 专家大厅 18 张卡片中 10 个专家 ID 不存在于 `EXPERTS_MAP`，prompt 是 UI 内联演示文案。
- 场景芯片"数据分析"与映射表键 `"数据分析及可视化"` 不匹配，永远走兜底 prompt。
- `desktop_pet.py::_toggle_always_on_top`：只写 config 不调 `setWindowFlags`——置顶功能无效。
- "我安装的"技能卡片固定显示"套件"徽章；技能中心无任何联网拉取，纯本地静态展示。

### 2.11 死代码 / 遗留物

- `ui/control_panel.py`（21KB）整文件死代码，无人实例化（main.py 不 import；desktop_pet 里 `control_panel=None`）。
- `ui/hands_overlay.py` + `ui/patch_desktop_pet_hands.py`：失败实验残留；patch 脚本若再执行会往错误位置注入坏代码；renderer.html 根本不解析 `?mode=hands` 参数。
- `chat_window.py` 内 **8 个弹窗类 + 2 个方法整份定义了两遍**（约 1300 行重复），且两版行为不一致（权限值 full_auto vs full；新版 TaskFilterPopup 丢了状态筛选 UI）；`AddAutomationDialog` 整类 145 行僵尸。
- `generate_character.py` 生成的 7 个 GIF 与帧目录：桌宠早已改用 Live2D，全部无人引用（~遗留资产 80MB+，含两个 zip 63MB）。
- README 描述的 `core/web_server.py` 不存在；README 是 v2.0.0、config 是 v3.0、start.bat 标题还是"v2.0 (3D VRM)"——三个版本口径。

---

## 三、Bug 清单

### 【严重】

| # | 位置 | 问题 |
|---|---|---|
| B1 | chat_window.py 5366/5913-5928 | 生成期间切换会话 → `_stream_id` 失配 → `_is_generating` 永不复位 → **发送按钮永久锁死**，且后续消息被静默丢弃 |
| B2 | chat_window.py 5345-5414 / ai_engine.py | 切换/新建会话**不清理 `conversation_history`**；`chat_stream` 的 `session_id` 形参在引擎内零使用 → **A 会话内容泄漏进 B 会话上下文**；后台线程 append 与 UI 线程整表替换存在数据竞态 |
| B3 | voice_output.py 74-80 | edge-tts 输出 **MP3**，用 PowerShell `Media.SoundPlayer` 播放——**SoundPlayer 只支持 WAV**，PlaySync 必抛异常被吞 → **TTS 永远无声** |
| B4 | system_tray.py 105-107 | `hasattr(self.pet,'chat_window')` 对 None 返回 True → 聊天窗未打开时点托盘"控制与设置" → `None.open_settings()` AttributeError 崩溃 |
| B5 | memory_manager.py 19-28 | 每次操作 `sqlite3.connect` 新建连接，`with conn` 只提交不关闭 → **连接泄漏**（长期运行累积） |
| B6 | 依赖体系 | requirements.txt 缺 PyQt5 / PyQtWebEngine(或 PyQt6-WebEngine) / pyaudio / beautifulsoup4 / html2text / python-pptx / pypdf（列的却是 PyPDF2，装上也 import 不到）/ pdfplumber / pandas / pyperclip；`aiofiles`、`asyncio-mqtt` 零使用纯占位；install.bat 只装 PyQt6 与代码的 PyQt5 主路径矛盾 → **按文档全新安装根本跑不起来** |
| B7 | core/pet_scheduler.py:11 | 无条件 `import PyQt5.QtCore`；PyQt6-only 环境下调度器断裂、pet_controller 插件加载失败 |
| B8 | config.json | `plugins.enabled` 含 **不存在的插件** `amap_lbs`、`docx_master`（是 skills 目录名，两套体系混写）；**明文 API Key 入库 3 处**（sk-1FEAUBAdC...，config.json 被 git 跟踪，密钥已进版本历史，建议立即作废） |
| B9 | desktop_pet.py 477-493 vs 638-652 | `showEvent`/`hideEvent` 重复定义，前一组死代码（复制粘贴事故） |
| B10 | desktop_pet.py 607-622 | 提醒音**播放两遍**（daemon 线程一遍 + 主线程同步一遍），主线程 Beep 串行阻塞事件循环约 660ms，UI 冻结 |

### 【中等】

| # | 位置 | 问题 |
|---|---|---|
| B11 | file_tools.py 115 | `execute_excel_code` 的 `exec(code, {}, local_scope)`——空 globals 会自动注入完整 `__builtins__`，可执行任意 Python（删文件/起进程），且该函数**无沙箱校验**（同文件其他函数有） |
| B12 | python_interpreter.py | `safe_globals` 变量名叫 safe，实际完整暴露 builtins——**全项目最大安全漏洞**，注释宣称"沙箱"是虚假安全 |
| B13 | 沙箱体系 | 21 个插件只有 file_tools.py 调了 2 次 `check_sandbox_path`，**其余全部裸奔**；SecurityGuard 形同虚设。computer_control 可 `os.startfile` 任意路径、`empty_recycle_bin` 无确认永久清空回收站 |
| B14 | pet_controller.py 79 | `runJavaScript(f"window.triggerAction('{motion}')")` motion 未转义 → JS 注入面 |
| B15 | wechat_tools.py | 盲坐标点击 + 剪贴板无清理，可能把消息发给错误对象 |
| B16 | file_tools.py 766 | `read_and_summarize_doc` 读 .docx 竟调**写函数** → 文档被无意义重存并弹出 Word 窗口 |
| B17 | file_tools/markdownify | `.xls` 旧格式走 openpyxl 必抛异常（承诺支持却不支持） |
| B18 | make_character_from_image.py 14 | 硬编码作者机器绝对路径（`C:\Users\31665\.gemini\...png`）；122 行 `exec(open(...).read())` 坏味道 |
| B19 | start.bat | 硬编码 `E:\Study_Cache\anaconda\python.exe`，换机必失效 |
| B20 | chat_window.py 5129-5166 | `active_model_id` 找不到时"保存为当前模型"会静默新建并激活新模型；API Key 明文落盘 |
| B21 | chat_window.py 5268 | `_on_ws_list_item_clicked` 读 `item.data(Qt.UserRole)` 但新版列表从不 setData → 恒 None 空转 |
| B22 | chat_window.py 96-126 | frontmatter 的 tools 列表解析终止条件 `stripped and not stripped.startswith(" ")` 恒 False，解析逻辑失效 |
| B23 | chat_window.py 5444 | "今天"筛选用 86400s 滑窗而非自然日 |
| B24 | xhs_publisher_tools.py | `subprocess.Popen(['clip'], shell=True)` 列表+shell=True 在 Windows 走 cmd 拼接，有注入面 |
| B25 | desktop_pet.py 65-80 | 本地端口 8789-8839 全占用时返回 8789 但服务没起来 → 页面白屏无提示 |

###【轻微】（择要）

- chat_window.py 23-42：PyQt5 ImportError 被 `except: pass` 吞掉，报错变成 NameError 难排障；全文件 20+ 处 `except Exception: pass` 系统性静默吞异常。
- MessageBlock 用 QLabel 纯文本渲染，docstring 却宣称"Markdown 优雅排版"。
- `_show_status` 固定 4 秒定时器互相覆盖；找不到激活模型兜底硬编码 "DeepSeek-R1"。
- desktop_pet.py：右键菜单 QMenu 不 deleteLater 累积；coding cookie 不在第 1-2 行；`_auto()` 的 'thinking'/'kneel' 动作名在 renderer 中不存在（启用也是 no-op）。
- plugin_manager.py：`install_or_pull_skill` 号称"真实拉取"，实际只是本地生成一个 SKILL.md 模板，没有任何远端来源。
- computer_control.py 硬编码私人路径 `E:\Study_Cache\...`。
- amap key 硬编码泄露（`6a4a0dbdc3b3bf705c935b674bfa564b`）。
- 桌宠右键"📜 历史对话记录"实际效果与"开启对话"完全相同（无历史页可跳）。

---

## 四、不合理设计（架构层面）

1. **`_fast_local_route` 关键词劫持**：任何包含 "python"/"ppt"/"天气"/"新闻" 等词的正常问题都会被拦截并返回假回复，LLM 根本收不到。这层"快速路由"是整个项目真实性的最大敌人。
2. **单条全局 `conversation_history`** 配多会话 UI：引擎层没有会话概念，`session_id` 形参是装饰。
3. **UI 重复定义两套**：8 个弹窗类双版本，行为不一致（权限值分裂、筛选功能缩水），维护必踩坑。
4. **三套"插件/技能/连接器"体系**（plugins/ + skills/ + connected_connectors）互相不知道对方存在，config 里混写。
5. **enabled 语义混乱**：`python_interpreter.py` 不在 enabled 列表但工具照样加载注入 prompt；enabled 里的条目可以不存在。
6. **plugin_manager 在 main.py 里 `load_all()` 都没被调用**——插件加载发生在哪？（实测 desktop_pet.py 导入 plugins.pet_controller 触发部分注册；`PluginManager.load_all` 全项目无调用点，工具注册表实际靠零散 import 撑起来。）
7. **配置字段冗余漂移**：同一状态多处存（`sound_enabled` 顶层与 behavior 下双写；custom 段 base_url/api_base、model/chat_model 双键）。
8. **保存文件后一律 `os.startfile` 自动弹窗**（Excel/Word/PPT/封面），未经用户确认。
9. **硬编码个人环境**：E:\Study_Cache、C:\Users\31665\Desktop、广州默认城市、5 个个人工作区目录作为出厂默认。

---

## 五、修复优先级建议（未执行，仅供决策）

1. **P0 记忆落库**：`_do_send`/`_on_done` 补 `memory.add_message`；切会话时按会话缓存/恢复 `conversation_history` 并复位 `_is_generating`（同时解决 B1/B2）。
2. **P0 拆掉假回复路由**：删除或收缩 `_fast_local_route`，只保留时间/日期这类确定性问答；其余全部走真实模型调用，错误就报真实错误。
3. **P0 密钥与隐私**：作废并移除明文 API Key（3 处）、高德 key、假手机号；config.json 移出版本控制，提供 config.example.json。
4. **P0 安全**：`python_interpreter` 与 `execute_excel_code` 改子进程+受限 builtins+路径白名单，或直接禁用；全插件统一接 `check_sandbox_path`；修复 `set_mode` → `update_config` 并统一权限枚举。
5. **P1 假数据插件**：快递100/12306/小红书/Chrome性能——要么接真 API，要么在返回文案中明确标注"演示数据"，当前形态属于欺骗性输出。
6. **P1 依赖修复**：requirements.txt 与 install.bat 统一为 PyQt5 + PyQtWebEngine 一条路线，补齐 pyaudio/bs4/html2text/python-pptx/pypdf 等，删 aiofiles/asyncio-mqtt。
7. **P1 TTS**：edge-tts 输出改用支持 MP3 的播放方式（或转 wav），当前 SoundPlayer 播 MP3 必败。
8. **P2 清理**：删 control_panel.py / hands_overlay.py / patch_desktop_pet_hands.py / 8 组重复弹窗类 / 80MB 遗留资产；修 README 与版本口径；修 system_tray 空指针与提醒音双播。
9. **P2 情绪联动接线**：在 chat_window 发送/完成时调 `emotion.update_by_text` / `reset_to_idle`，在 renderer.html 把 `triggerAction/triggerEmotion` 接到已有的 17 个程序化动作上（注意：此项涉及 renderer.html，按红线需用户明确批准后才动）。

---

*报告完。审计过程未修改任何业务代码、未运行任何程序、未触碰动漫模型 UI。*
