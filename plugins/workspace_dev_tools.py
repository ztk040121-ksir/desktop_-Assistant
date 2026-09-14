# -*- coding: utf-8 -*-
"""
工作空间开发与代码文件管理工具 (Workspace Dev Tools)
- 赋能 AI 从 0 到 1 在工作空间中直接创建、编写、修改与安全审查项目代码
- 深度联动 FileDiffTracker，自动捕捉修改前 vs 修改后差异元数据
- 严格遵循 SecurityGuard 工作空间沙箱访问隔离
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from core.plugin_manager import register_tool
from core.security_guard import SecurityGuard
from core.file_diff_tracker import FileDiffTracker


def _resolve_workspace_path(file_path: str) -> Tuple[Path, str]:
    """将输入路径解析为合法的工作空间绝对路径与相对路径"""
    guard = SecurityGuard.get_instance()
    ws_root = Path(guard.workspace_root).resolve()

    p_str = (file_path or "").strip().strip('"').strip("'")
    if p_str.startswith("file:///"):
        p_str = p_str[8:]
    elif p_str.startswith("file://"):
        p_str = p_str[7:]

    target = Path(p_str)
    if not target.is_absolute():
        target = (ws_root / target).resolve()

    # 权限校验
    is_ok, err = guard.check_path_access(target)
    if not is_ok:
        raise PermissionError(f"沙箱拦截：无法在工作空间外操作路径 `{target}`（{err}）")

    try:
        rel = target.relative_to(ws_root).as_posix()
    except Exception:
        rel = target.name

    return target, rel


@register_tool(
    description="在当前选定工作空间中创建新文件或覆写已有代码/配置文件。参数：file_path(相对于工作空间的路径或文件名，如 'spider_demo.py' 或 'src/main.py')，content(完整的代码或文件内容)，description(可选的改动说明，如 '实现网页数据抓取逻辑')",
    name="write_workspace_file"
)
def write_workspace_file(file_path: str, content: str, description: str = "") -> str:
    """在工作空间中写入代码文件并实时记录 Diff 差异"""
    try:
        target_path, rel_path = _resolve_workspace_path(file_path)
    except Exception as e:
        return f"❌ 写入失败：{e}"

    # 读取写入前的原始文本（若原本不存在则为空）
    before_content = ""
    is_new = not target_path.exists()
    if not is_new:
        try:
            before_content = target_path.read_text(encoding="utf-8")
        except Exception:
            try:
                before_content = target_path.read_text(encoding="gbk", errors="ignore")
            except Exception:
                before_content = ""

    # 确保父级目录存在
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 写入新代码内容
    try:
        target_path.write_text(content, encoding="utf-8")
    except Exception as e:
        return f"❌ 保存文件 `{rel_path}` 失败：{e}"

    # 记录到差异追踪器
    tracker = FileDiffTracker.get_instance()
    rec = tracker.record_change(
        rel_path=rel_path,
        abs_path=str(target_path),
        before_content=before_content,
        after_content=content
    )

    action_name = "新建文件" if is_new else "修改文件"
    diff_tag = f"[[WORKSPACE_DIFF:{rec.rel_path}|{rec.abs_path}|{rec.status}|+{rec.added_lines}|-{rec.removed_lines}]]"
    desc_str = f" - 说明：{description}" if description else ""

    return (
        f"{diff_tag}\n"
        f"✅ 已在工作空间中成功{action_name} `{rec.rel_path}`{desc_str} "
        f"(+{rec.added_lines} -{rec.removed_lines} 行)\n"
        f"💡 可在界面中点击该文件对比查看详细代码变动。"
    )


@register_tool(
    description="读取工作空间中指定代码或文本文件的内容（支持指定起始和结束行号进行按需切片分析）。参数：file_path(相对于工作空间的文件路径，如 'app.py')，start_line(可选，起始行号，1-indexed)，end_line(可选，结束行号，1-indexed，0表示读到末尾)",
    name="read_workspace_file"
)
def read_workspace_file(file_path: str, start_line: int = 1, end_line: int = 0) -> str:
    """安全读取工作空间文件内容并发射探索时序标记"""
    try:
        target_path, rel_path = _resolve_workspace_path(file_path)
    except Exception as e:
        return f"❌ 读取失败：{e}"

    if not target_path.exists():
        return f"❌ 文件不存在：`{rel_path}`"

    try:
        content = target_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = target_path.read_text(encoding="gbk", errors="ignore")
        except Exception as e:
            return f"❌ 读取文件编码异常：{e}"
    except Exception as e:
        return f"❌ 读取文件失败：{e}"

    all_lines = content.splitlines()
    total_lines = len(all_lines)

    s_idx = max(1, int(start_line)) if start_line else 1
    e_idx = min(total_lines, int(end_line)) if (end_line and int(end_line) > 0) else total_lines
    if s_idx > total_lines:
        s_idx = total_lines

    selected_lines = all_lines[s_idx - 1:e_idx]
    line_label = f"#L{s_idx}-{e_idx}" if (s_idx > 1 or e_idx < total_lines) else f"#L1-{total_lines}"

    # 发射探索与深度分析标记
    explore_tag = f"[[WORKSPACE_EXPLORE:{rel_path}|{line_label}|file]]"

    # 带行号的精准格式化文本
    formatted_lines = []
    for idx, line_text in enumerate(selected_lines, start=s_idx):
        formatted_lines.append(f"{idx:4d}: {line_text}")

    result_text = "\n".join(formatted_lines)
    return (
        f"{explore_tag}\n"
        f"📄 **【已分析代码文件】：`{rel_path}` ({line_label} / 共 {total_lines} 行)**\n"
        f"```\n{result_text}\n```"
    )


@register_tool(
    description="列出当前工作空间目录下的项目文件与子文件夹树结构。参数：sub_dir(可选，指定子目录，默认根目录)",
    name="list_workspace_files"
)
def list_workspace_files(sub_dir: str = "") -> str:
    """列出工作空间文件列表并标明目录探测"""
    try:
        target_path, rel_path = _resolve_workspace_path(sub_dir)
    except Exception as e:
        return f"❌ 检索失败：{e}"

    if not target_path.exists() or not target_path.is_dir():
        return f"❌ 目录不存在：`{rel_path}`"

    # 发射文件夹探索标记
    folder_name = rel_path if rel_path else Path(target_path).name
    explore_tag = f"[[WORKSPACE_EXPLORE:{folder_name}||folder]]"

    items = []
    try:
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", ".vscode", ".idea", "node_modules", "venv", ".venv"]]
            rel_root = Path(root).relative_to(target_path).as_posix()
            prefix = "" if rel_root == "." else f"{rel_root}/"
            for f in sorted(files):
                items.append(f"{prefix}{f}")
            if len(items) >= 80:
                break
    except Exception as e:
        return f"❌ 遍历工作空间目录异常：{e}"

    if not items:
        return f"{explore_tag}\n📁 工作空间目录 `{rel_path or '.'}` 当前为空。"

    file_list_str = "\n".join([f"  • `{f}`" for f in items[:60]])
    more_str = f"\n  • ... (共 {len(items)} 个文件)" if len(items) > 60 else ""
    return f"{explore_tag}\n📁 **【工作空间文件列表】** (`{rel_path or '.'}`):\n{file_list_str}{more_str}"


@register_tool(
    description="在当前工作空间根目录安全执行开发、测试、运行或语法编译命令（如 'python -m py_compile ui/dev_mode_view.py' 或 'pytest' 或 'python scratch/test.py'）。参数：command(待执行的命令行字符串)",
    name="run_workspace_command"
)
def run_workspace_command(command: str) -> str:
    """在工作空间中执行安全终端命令并实时返回输出与退出码"""
    import subprocess
    import sys
    import base64
    guard = SecurityGuard.get_instance()
    ws_root = str(Path(guard.workspace_root).resolve())

    cmd_str = (command or "").strip()
    if not cmd_str:
        return "❌ 命令不能为空"

    # 拦截危险指令
    forbidden = ["rmdir /s", "del /f /q C:", "format", "mkfs", "shutdown", "reboot"]
    if any(fb in cmd_str.lower() for fb in forbidden):
        return f"🛡️ 安全拦截：禁止在工作空间执行高危破坏命令 `{cmd_str}`"

    # 若使用 python 命令，优先绑定当前 python 解释器
    if cmd_str.startswith("python "):
        cmd_to_run = f'"{sys.executable}" ' + cmd_str[7:]
    else:
        cmd_to_run = cmd_str

    try:
        res = subprocess.run(
            cmd_to_run,
            cwd=ws_root,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace"
        )
        out = (res.stdout or "") + (res.stderr or "")
        out = out.strip()
        code = res.returncode
        # 编码部分输出用于前端直接还原终端卡片（避免管道字符断裂）
        out_b64 = base64.b64encode(out.encode("utf-8", errors="replace")).decode("ascii")
        tag = f"[[WORKSPACE_CMD:{cmd_str}|{code}|{out_b64}]]"
        return f"{tag}\n$ {cmd_str}\n{out}\n(退出码: {code})"
    except subprocess.TimeoutExpired:
        tag = f"[[WORKSPACE_CMD:{cmd_str}|-1|VEVPUg==]]"
        return f"{tag}\n$ {cmd_str}\n⚠️ 执行超时（超过30秒已被强行终止）"
    except Exception as e:
        return f"❌ 执行命令异常：{e}"

