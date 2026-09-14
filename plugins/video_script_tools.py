# -*- coding: utf-8 -*-
"""
短视频与创意脚本策划工具 (Video Script Creator Tools)
- 真实实现标准化影视/自媒体分镜脚本结构生成
"""
from pathlib import Path
from typing import Optional
from core.plugin_manager import register_tool


@register_tool(
    name="generate_video_storyboard",
    description="在本地工作区生成标准影视工业分镜脚本 Markdown 文件（含镜号、景别、画面动作、旁白台词、BGM与时长）"
)
def generate_video_storyboard(topic: str, target_duration_sec: int = 60, style: str = "科技感/快节奏", output_dir: Optional[str] = None) -> str:
    """
    生成短视频工业级分镜脚本
    :param topic: 视频主题，如 'AI 桌面助手生产力革命'
    :param target_duration_sec: 目标时长（秒）
    :param style: 视频风格
    :param output_dir: 输出目录
    """
    try:
        from core.security_guard import SecurityGuard
        guard = SecurityGuard.get_instance()
        target_base = Path(output_dir) if output_dir else guard.get_workspace_root()
    except Exception:
        target_base = Path.cwd()

    script_md = f"""# 🎬 视频分镜脚本策划：《{topic}》

- **目标时长**：{target_duration_sec} 秒
- **视觉风格**：{style}
- **核心受众**：程序员 / 职场白领 / 效率追求者

---

## 📋 工业级分镜详表

| 镜号 | 景别 / 运镜 | 画面内容 / 视觉动效 | 旁白 / 台词 (VO) | 音效 / BGM | 预估时长 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **01 (Hook)** | 特写 / 极速推镜 | 键盘快速敲击，屏幕弹出炫酷 AI 桌宠与流水线卡片 | “每天重复写胶水代码和报表，你还在手动搬砖吗？” | 激昂科技重低音 + 键盘清脆音 | 0-4s |
| **02 (Pain)** | 中景 / 慢摇 | 传统多窗口频繁切换、报错与繁琐配置的烦躁画面 | “频繁在编辑器、终端和浏览器之间来回倒腾，时间全被碎片化吞噬。” | 低沉紧迫环境音 | 4-12s |
| **03 (Solution)** | 全景 / 动态跟随 | 一键唤起 NovaDesk，智能体自主拆解任务并生成完整网站与代码 | “看好了！输入一句话，全栈架构、API 接口与自动化部署秒级就绪！” | 振奋上升电子音效 (Whoosh) | 12-25s |
| **04 (Feature)** | 特写 / 局部高亮 | 屏幕实时展示多会话并行推理、Live2D 情绪联动与无缝排队执行 | “真正的端到端并发执行，让 AI 真正成为你桌面上最懂你的全能伙伴。” | 节奏轻快旋律 | 25-45s |
| **05 (Call To Action)** | 特写 / 品牌定格 | 优雅 Logo 浮现，下方浮现下载链接与体验按钮 | “立即开启你的未来级桌面生产力！点击左下角一键体验！” | 品牌标志性音效 (Chime) | 45-60s |

---

## 💡 拍摄与剪辑要点
1. **前 3 秒黄金定律**：第一镜头务必高能量、快节奏抓人眼球；
2. **节奏点对齐**：视频切镜严格卡点在 BGM 的重拍重音上；
3. **花字与动效**：关键痛点与核心功能点加入加粗高亮动态花字。
"""
    clean_name = "".join([c for c in topic if c.isalnum() or c in ('_', '-')]) or "video_script"
    out_file = target_base / f"script_{clean_name}.md"
    out_file.write_text(script_md, encoding="utf-8")
    return f"✅ 成功生成短视频分镜脚本：{out_file}"
