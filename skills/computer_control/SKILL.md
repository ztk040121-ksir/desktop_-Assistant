---
name: computer_control
description: "桌面操作系统与计算机自动化控制。支持屏幕截屏多模态分析、打开本地应用程序与工作目录、执行安全 PowerShell 脚本。"
version: 2.0.0
tools:
  - take_screenshot_and_analyze
  - open_application_or_folder
  - run_powershell_cmd
---

# 桌面操作系统与计算机控制 Skill (Computer Control Skill)

## 技能概述
为智能体提供对宿主操作系统的交互与控制能力，包括截屏视觉理解、唤起应用程序与文件夹资源管理器、以及运行安全的系统指令。

## 核心功能
1. **屏幕截屏与多模态感知**：截取当前桌面图像供大模型进行视觉分析与报错定位。
2. **应用与文件管理**：打开记事本、计算器、终端或指定工作区目录。
3. **命令行沙箱执行**：运行指定的 PowerShell 脚本并获取标准输出。

## 触发意图示例
- "帮我截个图看看屏幕上有什么错误"
- "打开当前项目的工作文件夹"
