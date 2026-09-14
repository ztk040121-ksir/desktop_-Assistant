# -*- coding: utf-8 -*-
"""
CI/CD 自动化构建与部署工具 (CI/CD Tools)
- 真实实现 GitHub Actions 工作流 yml 生成
- 生产级多阶段 Dockerfile 与 docker-compose.yml 生成
"""
from pathlib import Path
from typing import Optional
from core.plugin_manager import register_tool


@register_tool(
    name="generate_github_workflow",
    description="在本地工作区生成符合生产标准的 GitHub Actions 自动化 CI/CD 工作流文件 (.github/workflows/ci.yml)"
)
def generate_github_workflow(project_type: str = "python", workflow_name: str = "CI Pipeline", output_dir: Optional[str] = None) -> str:
    """
    生成 GitHub Actions 工作流文件
    :param project_type: 项目类型 'python' | 'node' | 'go' | 'docker'
    :param workflow_name: 工作流显示名称
    :param output_dir: 输出目录
    """
    try:
        from core.security_guard import SecurityGuard
        guard = SecurityGuard.get_instance()
        target_base = Path(output_dir) if output_dir else guard.get_workspace_root()
    except Exception:
        target_base = Path.cwd()

    wf_dir = target_base / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)

    pt = project_type.lower()
    if "node" in pt or "js" in pt or "web" in pt:
        content = f"""name: {workflow_name}

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - name: Install dependencies
        run: npm ci || npm install
      - name: Run build
        run: npm run build --if-present
      - name: Run tests
        run: npm test --if-present
"""
    else:
        content = f"""name: {workflow_name}

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{{{ matrix.python-version }}}}
        uses: actions/setup-python@v5
        with:
          python-version: ${{{{ matrix.python-version }}}}
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          pip install pytest flake8
      - name: Lint with flake8
        run: |
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
      - name: Test with pytest
        run: |
          pytest
"""
    out_file = wf_dir / "ci.yml"
    out_file.write_text(content, encoding="utf-8")
    return f"✅ 成功生成 GitHub Actions 工作流文件：{out_file}"


@register_tool(
    name="generate_dockerfile",
    description="在本地工作区生成生产级多阶段构建 Dockerfile 与 docker-compose.yml"
)
def generate_dockerfile(project_type: str = "python", port: int = 8000, output_dir: Optional[str] = None) -> str:
    """
    生成 Dockerfile 和 docker-compose.yml
    :param project_type: 'python' | 'node'
    :param port: 容器暴露端口
    :param output_dir: 输出目录
    """
    try:
        from core.security_guard import SecurityGuard
        guard = SecurityGuard.get_instance()
        target_base = Path(output_dir) if output_dir else guard.get_workspace_root()
    except Exception:
        target_base = Path.cwd()

    pt = project_type.lower()
    if "node" in pt or "web" in pt:
        dockerfile = f"""# Multi-stage build for Node.js
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build --if-present

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app ./
EXPOSE {port}
CMD ["npm", "start"]
"""
    else:
        dockerfile = f"""# Multi-stage build for Python
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim AS runner
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
EXPOSE {port}
CMD ["python", "main.py"]
"""
    compose = f"""version: '3.8'

services:
  app:
    build: .
    ports:
      - "{port}:{port}"
    environment:
      - ENV=production
    restart: unless-stopped
"""
    (target_base / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    (target_base / "docker-compose.yml").write_text(compose, encoding="utf-8")
    return f"✅ 成功在工作区生成 Docker 部署文件：\n- {target_base / 'Dockerfile'}\n- {target_base / 'docker-compose.yml'}"
