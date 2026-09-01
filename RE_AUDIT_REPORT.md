# 二次复核审计报告（Re-Audit）

**日期**：2026-09-01 23:30
**范围**：对照《核心改造与修复明细》逐条验证 + 全量新 bug 扫描
**方法**：静态彻查，未运行任何程序，未改动任何代码，未触碰桌宠 UI（renderer.html / characters/ / 桌宠外观零改动）
**审计对象**：core/ai_engine.py (520行)、core/security_guard.py、core/voice_output.py、core/memory_manager.py、plugins/ 4 个改造插件 + 抽查其余、ui/chat_window.py (6652行全文)

---

## 一、修复明细逐条核验结论

| # | 声称的修复 | 结论 | 证据 |
|---|-----------|------|------|
| 1 | 拆除 `_fast_local_route` 假路由 | ✅ **属实** | ai_engine.py 从 1500+ 行减到 520 行；残存路由只剩"精确匹配时间问句直答"（346-366）和"截图→真实调用 computer_control"两条确定性逻辑，合理保留；离线时返回真实错误诊断（460-467, 513-518），不再伪装成功 |
| 2 | 会话上下文隔离 `session_histories` | ✅ 结构存在，❌ **有一个致命接线错位** | 见新发现 N2：`_load_session` 把恢复的历史写进旧的 `conversation_history`，而发送走 `session_histories[sid]`，重启后恢复的历史到不了模型 |
| 3 | 透明错误诊断 | ✅ 属实 | ConnectTimeout/ReadTimeout/ConnectError 分别给出真实指引，无假成功字符串 |
| 4 | `set_mode` / `set_workspace_root` 补全 | ✅ 属实 | security_guard.py 27/31 行定义；chat_window.py 5565（权限切换）、6005（切工作空间）真实调用，config 同步保存 |
| 5 | `execute_excel_code` 前置沙箱校验 | ✅ 属实 | file_tools.py 79 行 `check_sandbox_path(file_path)`；159/479 亦有 | 
| 6 | TTS 换 WMPlayer.OCX | ✅ 属实 | voice_output.py 76-88，PowerShell 起 WMPlayer 播 MP3；但有竞态隐患（见 N8） |
| 7 | 快递100 移除假派件员/假轨迹 | ✅ 不再造假 | 现为承运商前缀识别 + 官方查询链接；但运费估算仍是与距离无关的硬编码价目表（66行，同城和跨省同价） |
| 8 | 12306 移除假车次 | ⚠️ 半属实 | 确实不再编车次，但 `import httpx` 后**一次请求都没发**（42行文件零网络调用），只返回 12306 官网首页链接。"真实区间方案检索"并未实现 |
| 9 | 高德移除假路线/假网点 | ⚠️ 半属实 | 不再造假，但路线/POI 只生成跳转链接；且 **bug：`from=` 参数是空的**（29行 `from=&to=...`，`encoded_from` 算了没用，起点丢失）。天气走 wttr.in 真实 API（74行）✅，但那不是高德数据源，插件描述有水分 |
| 10 | `read_and_summarize_doc` 修复 | ✅ 属实 | file_tools.py 769-779，python-docx 真实提取段落 |
| 11 | `_load_session` 防锁死 | ✅ 属实 | 5603-5608：`_stream_id += 1` + 复位 `_is_generating` + 恢复按钮 |
| 12 | 消息实时落库 | ✅ 属实 | 用户消息 6158 行、AI 回复 6201 行均 `add_message` 入 SQLite；重启加载（5637-5652）真实 |
| 13 | Token 动态精确估算 | ⚠️ 名不副实 | 1619-1629 只是"汉字数×1.45 + 其他字符×0.35"的本地字数估算，不是真实 usage，离线 API 不返回消耗时这样标"精确"有误导 |
| 14 | 赞踩状态机 / 复制动画 / 重新生成 | ⚠️ 存在但有 bug | 复制动画 ✅真实；赞踩取消时误调 `_reset_copy_btn()`（1655/1667）且不持久化；重试有重复入库 + 答非所问问题（见 N6） |

**总评：聊天主链路（发送→流式→落库→重启恢复→切换会话）本轮确实修通了，这是真进步。但"修复明细"里 12306/高德的"真实化"实为"砍掉造假后降级为链接跳转"，语音朗读、自动化流水线两条支线仍是空壳，且引入了两个新的回归 bug（见下）。**

---

## 二、新发现的 Bug（按严重度）

### 【严重】

**N1. `_filter_skill_cat` 未定义 —— 点击技能分类必崩整进程**
- chat_window.py 3897 调用，全文件无定义（已 grep 亲自验证：唯一出现处就是调用行）。
- 技能页点击任一分类胶囊 → `AttributeError` → PyQt5 槽内未捕获异常 → qFatal 直接退出。
- 修复量：一个方法（或改调 `_rebuild_skills_grid` 带过滤参数），一行级。

**N2. `_load_session` 历史恢复进错容器 —— 重启后首轮失忆**
- 5655 行：`self.ai_engine.conversation_history = history`（旧的全局容器）
- 但发送走 `chat_stream(session_id=sid)`（6172），ai_engine 内只读 `session_histories[str(sid)]`（375 行），`conversation_history` 仅在 session_id 为空时使用。
- 后果：重启后加载会话，界面显示完整历史，**但模型收到的上下文是空的**——用户以为 AI 记得，实际第一句话就穿帮。
- 修复：`_load_session` 里改写 `ai_engine.session_histories[str(session_id)] = history`。

**N3. 生成中新建会话 → AI 回复写进错误的会话（SQLite 污染）**
- `_create_new_session_action`（5582-5600）和 `_create_new_session_in_workspace`（6086 附近）都**没有 `_stream_id += 1`**（已亲自 grep 验证：全文件仅 5635 和 6221 两处自增）。
- 在途流完成时 `sid == self._stream_id` 仍成立，`_on_done`（6200-6201）用**此刻**的 `_current_session_id` 落库 → A 会话的回答写进刚建的空会话 B。

**N4. Ollama 路径不带对话历史 —— 本地模型多轮失忆**
- `_stream_ollama`（420-459）payload 只有 `prompt + system`，从不调用 `_get_trimmed_messages`；只有 OpenAI 兼容路径（479）带历史。
- 用本地 Ollama 时每一轮都是单轮问答，`session_histories` 白存了。
- 修复：Ollama 改用 `/api/chat` + messages 数组，或在 prompt 里拼接历史。

**N5. 自动化流水线仍是布景（本轮未修，老问题原样）**
- 触发回调 `_on_scheduler_reminder_triggered`（2803-2806）**从不调用 ai_engine**，只写一条假 "success" 日志。
- 保存对话框 `_save_new_automation_from_view`（4778-4805）只读 3 个字段：名称、提示词、一个时间；频率/星期/间隔/单次/生效区间/连接器/权限/模型/推送开关**全部丢弃**。
- `PetScheduler._reminders` 纯内存（pet_scheduler.py 30），重启全丢——但运行日志 `auto_run_log.json` 真落盘，形成"日志说执行了、任务本体已消失"的矛盾。
- `add_reminder` 触发一次即 `fired`，"每天 08:00"实际只跑一次。

### 【中等】

**N6. 重试逻辑两处伤数据**（`_on_retry_message` 6224-6238）
- 重试会再次 `add_message("user", ...)` → 用户消息在 SQLite 重复累积；
- 点第 N 条历史消息的重试，实际重发的是**最新一条**用户消息（reversed 找第一个 user 块），答非所问；旧回答块也不清除。

**N7. 生成中发送：先清空输入再 guard，消息静默丢失**
- `_send_active_message` 6138-6142：先 `clear()` 再进 `_do_send`（6145 `if self._is_generating: return`）。连带 `_summon_with_prompt`、场景胶囊、专家引入、模板执行四个入口同样丢消息且无提示。

**N8. TTS 播放竞态**（voice_output.py 80-82）
- `$wmp.controls.play()` 后 playState 可能仍为 1(Stopped) 一瞬，while 条件立刻为假 → 循环体不进 → PowerShell 退出 → COM 对象销毁 → 播放被掐断。表现为偶发"只响半声或不响"。
- 另：整个 `_generate_and_play` 异常静默 `except Exception: pass`（89-90），坏了无任何日志。

**N9. 语音链路 0 接线**
- ChatWindow `__init__`（2739-2747）收了 `voice_input`/`voice_output` 形参但**从未存到 self**；desktop_pet.py 创建 ChatWindow 时根本不传；
- 主聊天界面没有任何语音输入按钮、没有朗读按钮（文件头注释宣称的"朗读"不存在）；
- 即 voice_output 修好了播放器，**前端没有入口调用它**（只有桌宠侧的独立调用，需另行确认）。

**N10. SQLite 连接泄漏依旧**（memory_manager.py 全文件）
- `with conn:` 只管事务提交，**不关闭连接**；每次操作新建连接靠 GC 回收。高频对话下句柄堆积。修复：用 `contextlib.closing` 或方法末 `conn.close()`。

**N11. requirements.txt 仍装不起来**
- 列了 **PyQt6**，代码全是 **PyQt5**（含 QtWebEngine）；
- 列了 **PyPDF2**，代码 `import pypdf`（chat_window 6107）；
- **缺**：bs4、html2text、python-pptx、pyaudio（PyQt5-WebEngine 也缺）；
- 按 requirements 全新安装依然跑不起来——上轮老问题未修。

**N12. config 仍启用不存在的插件**
- `plugins.enabled` 含 `amap_lbs`、`docx_master`，plugins/ 下无对应文件（亲自验证）。

**N13. httpx 缺失时模型测试线程死亡、按钮永久卡"⏳ 校验中"**
- `_test_api_connection` 5316-5380：`import httpx` 抛 ImportError 后，匹配 `except httpx.ConnectTimeout` 触发 NameError，线程无声死亡。

**N14. 未修复的老假插件（上轮已报，本轮确认原样）**
- `chrome_devtools_tools.py`：任何 URL 都返回写死的 FCP 0.68s / LCP 1.12s / 98分假报告（26-36 行）；
- `xiaohongshu_mcp_tools.py`：写死的爆款标题、虚构博主/点赞/评论池，`xhs_post_smart_comment` 假装已发布；
- `wechat_tools.py`：无任何网络调用，纯假；
- `web_search_news.py`：网易 API 是真的 ✅，但后面拼了 3 条**永远不变的"前沿科技要点"**，看起来像真实新闻，实为固定文案（49-51 行）。

**N15. 情绪系统死链未动**：`update_by_text` 依旧全项目零调用（已 grep 验证）。接线需动 renderer.html，涉及你的桌宠 UI 红线，仅列为建议，你批准才动。

### 【轻微】
- 赞/踩取消时误调 `_reset_copy_btn()`（1655/1667），高亮样式残留；状态不持久化。
- 删除会话不清理 `pinned_sessions`/`archived_sessions` 脏 id；归档会话仍出现在全局搜索结果；启动/删除后无条件加载 sessions[0]，可能把归档会话捞进主界面。
- 老存量空会话加载时把标题+伪造欢迎语永久写进 SQLite（5656-5667），污染数据。
- "今天"筛选按 24 小时算而非当日 0 点（5731）。
- 约 1450 行重复死代码：8 个弹窗类 + 2 个方法被第二份定义覆盖（如 PermissionPopupCard 两版分别发 "full_auto"/"full"，目前靠 set_mode 兼容才没出事），维护地雷。
- `_stream_worker` 异常路径不关 event loop；流式滚动 QTimer 泛洪 + QLabel 全量重绘性能差。
- 文件头注释宣称"纯净 Markdown 优雅排版"，实际 QLabel 纯文本无 Markdown 渲染（虚假宣传）。

---

## 三、改进建议（按优先级）

**P0（都是小改动，收益最大）**
1. 补 `_filter_skill_cat` 定义（防崩溃）。
2. `_create_new_session_action` / `_create_new_session_in_workspace` 各加一行 `_stream_id += 1`（防跨会话污染）。
3. `_load_session` 恢复历史改写入 `ai_engine.session_histories`（防重启失忆）。
4. `_stream_ollama` 改用 `/api/chat` 携带 messages（本地模型多轮记忆）。
5. requirements.txt 改为 PyQt5/PyQt5-WebEngine/pypdf/bs4/html2text/python-pptx/pyaudio；config 删掉 amap_lbs、docx_master。
6. 高德 `from=` 空 bug（用上 `encoded_from`）。

**P1（支线真实化或诚实降级）**
7. 自动化流水线端到端打通：保存全部字段 → 落盘 reminders → 到点真实调用 `chat_stream` → 写真实结果日志；做不到就先下架 UI，别留假 success。
8. 语音链路接线：ChatWindow 存 voice 依赖 + 底部工具条加语音按钮 + 消息条加朗读按钮；或删掉形参与注释。
9. 重试逻辑改为"删旧块 + 不重复落库 + 定位到该块对应的用户消息"。

**P2（债务清理）**
10. MemoryManager 连接复用或显式 close。
11. chrome/xiaohongshu/wechat 三假插件：要么接真实 API，要么在描述里明示"演示数据"并从默认启用里摘掉。
12. 删 8 个重复弹窗类 + AddAutomationDialog 约 1450 行死代码。
13. API Key 仍在 config.json 明文且此前已泄露给 git——若还没作废，**立即作废更换**。

---

*审计人：WorkBuddy · 全程静态彻查 · 未运行任何程序 · 桌宠 UI 零改动*
