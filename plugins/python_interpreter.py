# -*- coding: utf-8 -*-
"""
Python 本地安全代码沙箱解释器 (Python Code Interpreter Plugin)
支持在独立子进程与受限安全命名空间中运行数学算法、数据分析与推演代码，
具备 AST 深度属性链审查、严格内置白名单、文件旁路封堵与进程级超时强杀防护。
"""
import ast
import sys
import json
import subprocess
from typing import Optional
from pathlib import Path
from core.plugin_manager import register_tool


def _inspect_ast_security(code_str: str) -> Optional[str]:
    """AST 语法树层级静态安全检查，深度阻断私有属性链与底层系统/文件 I/O 旁路"""
    blocked_file_methods = (
        "read_csv", "read_excel", "read_json", "read_table", "read_sql", "read_pickle",
        "read_parquet", "read_html", "read_feather", "read_stata", "read_sas", "read_clipboard",
        "read_fwf", "read_xml", "read_orc", "read_spss", "read_hdf", "ExcelFile", "ExcelWriter", "HDFStore",
        "to_csv", "to_excel", "to_json", "to_sql", "to_pickle", "to_parquet", "to_html", "to_feather",
        "to_stata", "to_hdf", "to_xml", "to_clipboard", "to_markdown",
        "loadtxt", "load", "fromfile", "save", "savez", "savez_compressed", "savetxt", "tofile", "memmap",
        "genfromtxt", "fromregex", "DataSource", "recfromcsv", "recfromtxt",
        "dump", "dumps", "open_memmap", "read_array", "write_array"
    )
    try:
        tree = ast.parse(code_str)
        for node in ast.walk(tree):
            # 禁止任意外部导包
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return "🛡️ **[安全沙箱拦截]**：沙箱内禁止执行 `import` 导包操作（常用数值计算库已在受限沙箱中安全预置）。"
            # 彻底阻断私有/底层属性链逃逸及外部文件读写
            if isinstance(node, ast.Attribute):
                if node.attr.startswith("__"):
                    return f"🛡️ **[安全沙箱拦截]**：禁止访问私有属性与反射底层链 `{node.attr}`。"
                if node.attr in blocked_file_methods or node.attr in ("dump", "dumps", "open_memmap", "read_array", "write_array", "tofile", "fromfile"):
                    return f"🛡️ **[安全沙箱拦截]**：禁止调用磁盘文件或底层 I/O 方法 `{node.attr}`。"
            # 禁止高危反射与代码动态生成函数
            if isinstance(node, ast.Name) and (node.id in (
                "eval", "exec", "__import__", "open", "compile", "globals", "locals",
                "system", "getattr", "setattr", "delattr", "breakpoint", "input", "file"
            ) or node.id in blocked_file_methods):
                return f"🛡️ **[安全沙箱拦截]**：禁止调用高危反射或系统函数 `{node.id}`。"
        return None
    except Exception as e:
        return f"❌ Python 语法解析错误：{e}"


# 独立子进程运行包装器脚本（剥离文件 I/O 能力的受限环境）
_SUBPROCESS_RUNNER = """
import sys
import io
import math
import json
import traceback

SAFE_BUILTINS = {
    'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool, 'bytearray': bytearray,
    'bytes': bytes, 'chr': chr, 'complex': complex, 'dict': dict, 'dir': dir,
    'divmod': divmod, 'enumerate': enumerate, 'filter': filter, 'float': float,
    'format': format, 'frozenset': frozenset, 'hex': hex, 'int': int, 'isinstance': isinstance,
    'issubclass': issubclass, 'iter': iter, 'len': len, 'list': list, 'map': map,
    'max': max, 'min': min, 'next': next, 'oct': oct, 'ord': ord, 'pow': pow,
    'print': print, 'range': range, 'repr': repr, 'reversed': reversed, 'round': round,
    'set': set, 'slice': slice, 'sorted': sorted, 'str': str, 'sum': sum, 'tuple': tuple,
    'type': type, 'zip': zip,
    'True': True, 'False': False, 'None': None,
    'Exception': Exception, 'ValueError': ValueError, 'TypeError': TypeError,
    'KeyError': KeyError, 'IndexError': IndexError, 'RuntimeError': RuntimeError, 'ZeroDivisionError': ZeroDivisionError
}

safe_env = {
    "__builtins__": SAFE_BUILTINS,
    "math": math,
    "json": json
}

try:
    import numpy as np
    # 彻底剥离 numpy 底层文件读写与外部数据源方法
    np_io_fns = [
        'loadtxt', 'load', 'fromfile', 'save', 'savez', 'savez_compressed', 'savetxt', 'tofile', 'memmap',
        'genfromtxt', 'fromregex', 'DataSource', 'recfromcsv', 'recfromtxt',
        'dump', 'dumps'
    ]
    for fn in np_io_fns:
        if hasattr(np, fn):
            try: delattr(np, fn)
            except Exception: pass
    if hasattr(np, 'lib'):
        try:
            if hasattr(np.lib, 'format'):
                delattr(np.lib, 'format')
        except Exception: pass
    # 剥离 ndarray 实例对象方法
    for nd_fn in ['dump', 'dumps', 'tofile']:
        if hasattr(np.ndarray, nd_fn):
            try: delattr(np.ndarray, nd_fn)
            except Exception: pass
    safe_env["np"] = np
    safe_env["numpy"] = np
except ImportError:
    pass

try:
    import pandas as pd
    # 彻底剥离 pandas 文件读取与输出操作
    pd_io_fns = [
        'read_csv', 'read_excel', 'read_json', 'read_table', 'read_sql', 'read_pickle', 'read_parquet', 'read_html',
        'read_clipboard', 'read_fwf', 'read_xml', 'read_orc', 'read_spss', 'read_hdf', 'read_feather', 'read_stata', 'read_sas',
        'ExcelFile', 'ExcelWriter', 'HDFStore'
    ]
    for fn in pd_io_fns:
        if hasattr(pd, fn):
            try: delattr(pd, fn)
            except Exception: pass
    df_io_fns = ['to_csv', 'to_excel', 'to_json', 'to_sql', 'to_pickle', 'to_parquet', 'to_html', 'to_feather', 'to_stata', 'to_hdf', 'to_xml', 'to_clipboard', 'to_markdown', 'to_feather', 'to_orc', 'to_spss', 'to_gbq']
    for fn in df_io_fns:
        if hasattr(pd.DataFrame, fn): 
            try: delattr(pd.DataFrame, fn)
            except Exception: pass
    safe_env["pd"] = pd
    safe_env["pandas"] = pd
except ImportError:
    pass

code_to_run = sys.stdin.read()
try:
    exec(code_to_run, safe_env)
except Exception:
    sys.stderr.write(traceback.format_exc())
"""


def _execute_in_isolated_process(code_str: str, timeout_sec: float = 3.0) -> str:
    """在独立 OS 子进程中运行用户代码，超时由 OS 彻底销毁进程，避免死循环占用主进程 CPU"""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _SUBPROCESS_RUNNER],
            input=code_str,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
            errors="replace"
        )
        out = proc.stdout.strip()
        err = proc.stderr.strip()

        result_lines = []
        if out:
            result_lines.append(f"📋 **标准输出 (stdout)**:\n```\n{out}\n```")
        if err:
            result_lines.append(f"⚠️ **标准错误 (stderr)**:\n```\n{err}\n```")
        if not out and not err:
            result_lines.append("✅ 代码执行成功，无额外输出。")

        return "\n\n".join(result_lines)
    except subprocess.TimeoutExpired:
        return f"⚠️ **[进程级超时强杀]**：代码运行时间超过 {timeout_sec} 秒限制，已通过底层操作系统强制终止该进程（彻底释放 CPU 资源）。"
    except Exception as e:
        return f"❌ 执行器子进程异常：{e}"


@register_tool(description="在本地独立隔离沙箱中运行 Python 代码，返回标准输出和执行结果。参数：code(需要执行的 Python 脚本代码)")
def run_python_code(code: str) -> str:
    """安全沙箱中执行 Python 代码（AST 过滤 + 隔离进程 + 超时强杀）"""
    code_clean = code.strip()
    if not code_clean:
        return "⚠️ 未提供有效的 Python 代码。"

    # 去除 Markdown 代码块标记
    if code_clean.startswith("```python"):
        code_clean = code_clean[9:]
    elif code_clean.startswith("```"):
        code_clean = code_clean[3:]
    if code_clean.endswith("```"):
        code_clean = code_clean[:-3]
    code_clean = code_clean.strip()

    # 1. AST 层级安全深度扫描
    ast_err = _inspect_ast_security(code_clean)
    if ast_err:
        return ast_err

    # 2. 独立子进程安全执行
    return _execute_in_isolated_process(code_clean, timeout_sec=3.0)
