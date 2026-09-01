# -*- coding: utf-8 -*-
"""
GitHub 交互与开发运维工具集 (GitHub Agent Tools Plugin)
基于 ModelScope @steipete/github Skill 规范
支持通过 gh CLI 与 GitHub REST API 处理 Issues、Pull Requests、Actions 工作流运行、代码仓库查询与热榜搜索。
"""
import subprocess
import shutil
import json
import httpx
from typing import Optional
from core.plugin_manager import register_tool


def _run_gh_cmd(args: list) -> str:
    """安全执行 gh 命令行指令"""
    gh_path = shutil.which("gh")
    if not gh_path:
        return "⚠️ 未检测到系统安装 GitHub CLI (gh)。你可以通过 `winget install --id GitHub.cli` 安装，或使用内置的 GitHub API 工具进行免安装查询。"
    try:
        res = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=15.0, encoding='utf-8', errors='ignore')
        if res.returncode == 0:
            return res.stdout.strip() if res.stdout.strip() else "✅ GitHub 指令执行成功（无输出内容）。"
        else:
            return f"❌ GitHub CLI 执行返回错误：{res.stderr.strip()}"
    except Exception as e:
        return f"❌ 执行 gh 指令异常：{e}"


@register_tool(description="使用 GitHub CLI 查询或管理 GitHub 仓库的 Issues（议题）。参数：repo(如'owner/repo'), action(可选: 'list'列表, 'view'查看), issue_number(issue编号)")
def github_issue_manager(repo: str = "", action: str = "list", issue_number: str = "") -> str:
    """管理 GitHub Issues"""
    clean_repo = repo.strip()
    if not clean_repo:
        return "请提供要查询的 GitHub 仓库，例如：`torvalds/linux` 或 `facebook/react`"
    
    if shutil.which("gh"):
        cmd = ["issue", action]
        if issue_number:
            cmd.append(str(issue_number))
        cmd.extend(["--repo", clean_repo])
        out = _run_gh_cmd(cmd)
        return f"🐙 **【GitHub Issues 查询】(`{clean_repo}`)**：\n```\n{out}\n```"

    try:
        url = f"https://api.github.com/repos/{clean_repo}/issues"
        headers = {"User-Agent": "Desktop-AI-Assistant", "Accept": "application/vnd.github.v3+json"}
        resp = httpx.get(url, headers=headers, timeout=8.0)
        if resp.status_code == 200:
            issues = resp.json()[:8]
            lines = [f"🐙 **【GitHub Issues 列表】(`{clean_repo}`)**："]
            for it in issues:
                num = it.get("number")
                title = it.get("title", "")
                user = it.get("user", {}).get("login", "")
                state = it.get("state", "open")
                lines.append(f"• **#{num}** [{state.upper()}] {title} (@{user})")
            return "\n".join(lines) if issues else f"ℹ️ 仓库 `{clean_repo}` 当前无开启的 Issues。"
        else:
            return f"❌ 查询 GitHub Issues 失败 (HTTP {resp.status_code})"
    except Exception as e:
        return f"❌ 联网请求异常: {e}"


@register_tool(description="查询或检查 GitHub 仓库的 Pull Requests (PR) 及 CI 状态。参数：repo(如'owner/repo'), pr_number(PR编号)")
def github_pr_manager(repo: str = "", pr_number: str = "") -> str:
    """管理 GitHub PR"""
    clean_repo = repo.strip()
    if not clean_repo:
        return "请提供仓库名称，例如：`owner/repo`"

    if shutil.which("gh"):
        cmd = ["pr", "list", "--repo", clean_repo, "--limit", "8"]
        if pr_number:
            cmd = ["pr", "checks", str(pr_number), "--repo", clean_repo]
        out = _run_gh_cmd(cmd)
        return f"🐙 **【GitHub PR 状态】(`{clean_repo}`)**：\n```\n{out}\n```"

    try:
        url = f"https://api.github.com/repos/{clean_repo}/pulls"
        headers = {"User-Agent": "Desktop-AI-Assistant", "Accept": "application/vnd.github.v3+json"}
        resp = httpx.get(url, headers=headers, timeout=8.0)
        if resp.status_code == 200:
            prs = resp.json()[:8]
            lines = [f"🐙 **【GitHub Pull Requests】(`{clean_repo}`)**："]
            for pr in prs:
                num = pr.get("number")
                title = pr.get("title", "")
                user = pr.get("user", {}).get("login", "")
                lines.append(f"• **PR #{num}** {title} (@{user})")
            return "\n".join(lines) if prs else f"ℹ️ 仓库 `{clean_repo}` 当前无开启的 PR。"
    except Exception as e:
        return f"❌ 请求异常: {e}"
    return f"ℹ️ 仓库 `{clean_repo}` PR 检索完成。"


@register_tool(description="查询 GitHub 上的开源热门项目或搜索指定主题的开源仓库。参数：query(搜索关键词，如'deepseek'、'live2d'、'agent')")
def github_search_repos(query: str = "") -> str:
    """搜索 GitHub 开源项目"""
    q = query.strip()
    if not q:
        q = "stars:>1000"
    try:
        url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc"
        headers = {"User-Agent": "Desktop-AI-Assistant", "Accept": "application/vnd.github.v3+json"}
        resp = httpx.get(url, headers=headers, timeout=8.0)
        if resp.status_code == 200:
            items = resp.json().get("items", [])[:6]
            lines = [f"⭐ **【GitHub 开源热门检索】(`{q}`)**："]
            for it in items:
                name = it.get("full_name", "")
                desc = it.get("description", "无描述") or "无描述"
                stars = it.get("stargazers_count", 0)
                lang = it.get("language", "Unknown")
                html_url = it.get("html_url", "")
                lines.append(f"• **[{name}]({html_url})**  ★ `{stars:,}` | `{lang}`\n  👉 {desc[:60]}...")
            return "\n\n".join(lines)
    except Exception as e:
        return f"❌ 搜索 GitHub 失败: {e}"
    return "搜索完成。"
