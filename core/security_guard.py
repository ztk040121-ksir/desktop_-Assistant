# -*- coding: utf-8 -*-
"""
安全沙箱与权限管理中枢 (Security Guard & Workspace Sandbox Manager)
负责：
1. 默认权限 (standard): 严格将文件创建、读取、修改、目录操作与脚本执行限制在当前激活的工作空间目录下；
2. 完全访问权限 (full_auto): 允许超出当前工作空间，在全盘任意路径执行操作；
3. 为所有插件工具与代码解释器提供即时沙箱校验拦截。
"""
import os
from pathlib import Path
from typing import Tuple, Union, Optional


class SecurityGuard:
    _instance = None

    def __init__(self):
        self.workspace_root = str(Path.cwd().resolve())
        self.permission_mode = "standard"  # "standard" | "full_auto"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SecurityGuard()
        return cls._instance

    def set_mode(self, mode: str):
        """设置权限模式"""
        self.permission_mode = "full_auto" if mode in ["full", "full_auto", "all"] else "standard"

    def set_workspace_root(self, root_path: str):
        """设置沙箱根目录"""
        if root_path:
            self.workspace_root = str(Path(root_path).resolve())

    def update_config(self, workspace_root: Optional[str] = None, permission_mode: Optional[str] = None):
        """动态更新当前工作空间根目录与权限模式"""
        if workspace_root:
            self.set_workspace_root(workspace_root)
        if permission_mode:
            self.set_mode(permission_mode)

    def is_full_access(self) -> bool:
        """是否处于完全访问模式"""
        return self.permission_mode in ["full_auto", "full", "all"]

    def check_path_access(self, target_path: Union[str, Path]) -> Tuple[bool, str]:
        """
        校验目标路径是否允许访问
        :return: (is_allowed, error_reason)
        """
        # 1. 完全访问模式：直接放行
        if self.is_full_access():
            return True, ""

        if not target_path:
            return True, ""

        try:
            p_str = str(target_path).strip().strip('"').strip("'")
            if p_str.startswith("file:///"):
                p_str = p_str[8:]
            elif p_str.startswith("file://"):
                p_str = p_str[7:]

            target = Path(p_str)
            ws_root = Path(self.workspace_root).resolve()

            # 如果是相对路径，默认基于工作空间解析
            if not target.is_absolute():
                target = (ws_root / target).resolve()
            else:
                target = target.resolve()

            # 检查是否在工作空间内部
            try:
                target.relative_to(ws_root)
                return True, ""
            except ValueError:
                # 越界超出当前工作空间
                err = (
                    f"⚠️ **【安全沙箱拦截】**\n\n"
                    f"当前系统处于 **「🛡️ 默认权限」** 模式，AI 智能体的所有文件创建、修改与执行操作均被**严格限制在当前工作空间沙箱内**：\n"
                    f"- **当前工作空间**：`{ws_root}`\n"
                    f"- **试图操作越界路径**：`{target}`\n\n"
                    f"💡 **如需在当前工作空间以外的电脑外部路径操作或创建目录，请在底部操作栏将权限模式切换为「🚀 允许完全访问」后再试！**"
                )
                return False, err

        except Exception as e:
            return False, f"⚠️ 路径安全校验异常: {e}"

    def guard_path(self, target_path: Union[str, Path]) -> Optional[str]:
        """如果越界返回错误提示字符串，否则返回 None"""
        allowed, err = self.check_path_access(target_path)
        if not allowed:
            return err
        return None


# 全局便捷单例函数
def check_sandbox_path(target_path: Union[str, Path]) -> Optional[str]:
    """返回拦截信息或 None"""
    return SecurityGuard.get_instance().guard_path(target_path)
