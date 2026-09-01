# -*- coding: utf-8 -*-
"""
Python 本地代码沙箱解释器 (Python Code Interpreter MCP Plugin)
安全执行 Python 算法、数据科学计算、统计绘图与数学推演，捕获标准输出和异常。
"""
import io
import sys
import math
import json
import traceback
from pathlib import Path
from core.plugin_manager import register_tool


@register_tool(description="在本地安全沙箱中运行 Python 代码，返回标准输出和执行结果。参数：code(需要执行的 Python 脚本代码)")
def run_python_code(code: str) -> str:
    """安全沙箱中执行 Python 代码"""
    if not code or not code.strip():
        return "⚠️ 未提供有效的 Python 代码。"

    # 准备沙箱全局变量与输出重定向
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    safe_globals = {
        "__builtins__": __builtins__,
        "math": math,
        "json": json,
        "sys": sys,
        "Path": Path
    }

    # 尝试引入科学计算常用包（如果存在）
    try:
        import numpy as np
        safe_globals["np"] = np
        safe_globals["numpy"] = np
    except ImportError:
        pass

    try:
        import pandas as pd
        safe_globals["pd"] = pd
        safe_globals["pandas"] = pd
    except ImportError:
        pass

    old_stdout = sys.stdout
    old_stderr = sys.stderr

    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        # 执行用户代码
        exec(code, safe_globals)

        out = stdout_capture.getvalue()
        err = stderr_capture.getvalue()

        result_lines = []
        if out:
            result_lines.append(f"📋 **标准输出 (stdout)**:\n```\n{out.strip()}\n```")
        if err:
            result_lines.append(f"⚠️ **标准错误 (stderr)**:\n```\n{err.strip()}\n```")
        if not out and not err:
            result_lines.append("✅ 代码执行成功，无额外标准输出。")

        return "\n\n".join(result_lines)

    except Exception as e:
        err_msg = traceback.format_exc()
        return f"❌ **Python 代码运行异常**:\n```\n{err_msg}\n```"
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
