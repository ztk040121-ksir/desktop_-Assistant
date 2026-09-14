---
name: cicd_automation
description: CI/CD 持续集成、持续部署与容器化工程技能，支持自动化生成 GitHub Actions 流水线配置、生产级 Dockerfile 及环境语法检测。
---

# CI/CD 自动化构建与部署技能 (CI/CD Skill)

本技能为开发者提供现代软件交付生命周期的自动化流水线设计与容器化构建能力。

## 适用场景
1. **GitHub Actions 流水线生成**：自动测试、构建检查与 Lint 规范校验；
2. **容器化 Docker 封装**：多阶段轻量化镜像构建与 docker-compose 编排；
3. **环境检测**：校验语法与配置规范。

## 配套工具函数 (Tools)
- `generate_github_workflow(project_type, workflow_name)`: 生成 GitHub Actions CI 配置文件。
- `generate_dockerfile(project_type, port)`: 生成生产级多阶段 Dockerfile 与 docker-compose.yml。
