# -*- coding: utf-8 -*-
"""
文档工程与技术规范工具 (Doc Engineering Tools)
- 真实实现标准 README.md 架构与 API 接口参考文档生成
"""
import inspect
from pathlib import Path
from typing import Optional
from core.plugin_manager import register_tool


@register_tool(
    name="generate_project_readme",
    description="在本地工作区生成符合开源顶级规范的 Markdown 技术项目 README.md 文档"
)
def generate_project_readme(project_name: str, description: str, tech_stack: Optional[str] = None, output_dir: Optional[str] = None) -> str:
    """
    生成专业项目 README.md
    :param project_name: 项目名称
    :param description: 项目核心定位与描述
    :param tech_stack: 技术栈（如 'Python, PyQt5, SQLite, MCP'）
    :param output_dir: 输出目录
    """
    try:
        from core.security_guard import SecurityGuard
        guard = SecurityGuard.get_instance()
        target_base = Path(output_dir) if output_dir else guard.get_workspace_root()
    except Exception:
        target_base = Path.cwd()

    stack = tech_stack or "Python, Modern Architecture"
    readme_content = f"""# {project_name}

> {description}

---

## 🌟 核心特性 (Key Features)

- **⚡ 高性能架构**：异步事件流驱动，极致流畅响应
- **🛡️ 安全可控**：工作空间路径隔离与严格权限守护
- **🤖 智能协同**：多智能体编排与全生态工具扩展

## 🛠️ 技术栈 (Tech Stack)

`{stack}`

## 🚀 快速开始 (Quick Start)

### 1. 克隆与安装依赖
```bash
git clone https://github.com/your-org/{project_name.lower()}.git
cd {project_name.lower()}
pip install -r requirements.txt
```

### 2. 运行项目
```bash
python main.py
```

## 📁 目录结构 (Directory Structure)

```text
{project_name.lower()}/
├── core/         # 核心引擎与状态管理
├── plugins/      # 工具插件集
├── skills/       # 业务技能套件
├── ui/           # 现代化用户界面
└── main.py       # 程序主入口
```

## 📄 开源许可 (License)

本项目基于 MIT License 协议开源。
"""
    out_file = target_base / "README.md"
    out_file.write_text(readme_content, encoding="utf-8")
    return f"✅ 成功生成高质量 README 文档：{out_file}"
