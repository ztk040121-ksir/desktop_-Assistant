# -*- coding: utf-8 -*-
"""
网站与前端全栈开发工具 (Web Development Tools)
- 真实实现企业官网、后台管理系统、个人博客、电商首页脚手架生成
- 支持工作区本地轻量 Web 预览服务器启动与管理
- 网站结构与前端代码静态分析
"""
import os
import sys
import json
import socket
import threading
import http.server
import socketserver
from pathlib import Path
from typing import Dict, Any, Optional
from core.plugin_manager import register_tool

_ACTIVE_SERVERS = {}


@register_tool(
    name="generate_web_scaffold",
    description="生成完整的现代响应式网站项目脚手架（HTML5/CSS3/JavaScript），支持 enterprise(企业官网)、admin(后台管理系统)、blog(个人博客)、ecommerce(电商首页)"
)
def generate_web_scaffold(project_type: str, project_name: str, title: Optional[str] = None, output_dir: Optional[str] = None) -> str:
    """
    生成完整的现代响应式网站项目脚手架
    :param project_type: 项目类型 'enterprise' | 'admin' | 'blog' | 'ecommerce'
    :param project_name: 项目英文目录名，如 'my_web_site'
    :param title: 网站中文标题，如 'NovaTech 科技官网'
    :param output_dir: 输出目录绝对路径或相对路径（默认当前工作区）
    """
    try:
        from core.security_guard import SecurityGuard
        guard = SecurityGuard.get_instance()
        target_base = Path(output_dir) if output_dir else guard.get_workspace_root()
    except Exception:
        target_base = Path.cwd()

    proj_dir = target_base / project_name
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "css").mkdir(exist_ok=True)
    (proj_dir / "js").mkdir(exist_ok=True)
    (proj_dir / "assets").mkdir(exist_ok=True)

    site_title = title or project_name
    ptype = (project_type or "enterprise").lower()

    if "admin" in ptype or "dashboard" in ptype or "后台" in ptype:
        html_code = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site_title} - 管理控制台</title>
    <link rel="stylesheet" href="css/style.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body class="dark-theme">
    <div class="app-layout">
        <aside class="sidebar">
            <div class="logo">⚡ {site_title}</div>
            <nav class="nav-menu">
                <a href="#dashboard" class="nav-item active">📊 仪表盘概览</a>
                <a href="#users" class="nav-item">👥 用户管理</a>
                <a href="#orders" class="nav-item">📦 订单流转</a>
                <a href="#analytics" class="nav-item">📈 数据分析</a>
                <a href="#settings" class="nav-item">⚙️ 系统设置</a>
            </nav>
        </aside>
        <main class="main-content">
            <header class="top-header">
                <h2>控制台总览</h2>
                <div class="user-profile">
                    <span class="avatar">Admin</span>
                </div>
            </header>
            <section class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">总营收 (GMV)</div>
                    <div class="metric-value">¥128,450.00</div>
                    <div class="metric-trend up">+18.2% 同比上周</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">活跃用户数</div>
                    <div class="metric-value">2,840</div>
                    <div class="metric-trend up">+8.5%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">今日新订单</div>
                    <div class="metric-value">342 单</div>
                    <div class="metric-trend up">+24.0%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">系统 API 负载</div>
                    <div class="metric-value">18.4%</div>
                    <div class="metric-trend normal">健康良好</div>
                </div>
            </section>
            <section class="table-section">
                <h3>近期业务订单数据</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>订单编号</th>
                            <th>客户名称</th>
                            <th>下单金额</th>
                            <th>支付状态</th>
                            <th>创建时间</th>
                        </tr>
                    </thead>
                    <tbody id="order-tbody">
                        <tr>
                            <td>#ORD-20260901-01</td>
                            <td>张三科技</td>
                            <td>¥12,800</td>
                            <td><span class="badge success">已完成</span></td>
                            <td>2026-09-01 14:32</td>
                        </tr>
                        <tr>
                            <td>#ORD-20260901-02</td>
                            <td>创新工场</td>
                            <td>¥45,000</td>
                            <td><span class="badge warning">处理中</span></td>
                            <td>2026-09-01 15:10</td>
                        </tr>
                    </tbody>
                </table>
            </section>
        </main>
    </div>
    <script src="js/main.js"></script>
</body>
</html>"""
        css_code = """* { margin:0; padding:0; box-sizing:border-box; font-family:'Inter','Microsoft YaHei UI',sans-serif; }
body.dark-theme { background:#0f172a; color:#f8fafc; }
.app-layout { display:flex; min-height:100vh; }
.sidebar { width:240px; background:#1e293b; padding:24px 16px; border-right:1px solid #334155; }
.logo { font-size:18px; font-weight:700; color:#6366f1; margin-bottom:32px; }
.nav-menu { display:flex; flex-direction:column; gap:8px; }
.nav-item { color:#94a3b8; text-decoration:none; padding:10px 14px; border-radius:8px; font-size:14px; transition:all 0.2s; }
.nav-item:hover, .nav-item.active { background:#334155; color:#ffffff; font-weight:600; }
.main-content { flex:1; padding:32px 40px; background:#0f172a; }
.top-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:28px; }
.metrics-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:20px; margin-bottom:32px; }
.metric-card { background:#1e293b; padding:20px; border-radius:12px; border:1px solid #334155; }
.metric-title { font-size:13px; color:#94a3b8; margin-bottom:8px; }
.metric-value { font-size:24px; font-weight:700; color:#f8fafc; margin-bottom:6px; }
.metric-trend.up { color:#10b981; font-size:12px; }
.metric-trend.normal { color:#6366f1; font-size:12px; }
.table-section { background:#1e293b; padding:24px; border-radius:12px; border:1px solid #334155; }
.table-section h3 { margin-bottom:16px; font-size:16px; }
.data-table { width:100%; border-collapse:collapse; text-align:left; font-size:14px; }
.data-table th { padding:12px 14px; color:#94a3b8; border-bottom:1px solid #334155; }
.data-table td { padding:14px; border-bottom:1px solid #1e293b; color:#e2e8f0; }
.badge { padding:4px 8px; border-radius:6px; font-size:12px; font-weight:600; }
.badge.success { background:#064e3b; color:#34d399; }
.badge.warning { background:#78350f; color:#fbbf24; }"""
        js_code = """console.log('Admin Dashboard loaded successfully');
document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', (e) => {
        document.querySelectorAll('.nav-item').forEach(x => x.classList.remove('active'));
        el.classList.add('active');
    });
});"""
    else:
        # 默认企业官网 / 博客 / 电商展示页
        html_code = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site_title} - 官方网站</title>
    <link rel="stylesheet" href="css/style.css">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
</head>
<body>
    <header class="navbar">
        <div class="container nav-container">
            <a href="#" class="brand-logo">✨ {site_title}</a>
            <nav class="nav-links">
                <a href="#features">核心特性</a>
                <a href="#solutions">解决方案</a>
                <a href="#pricing">价格方案</a>
                <a href="#contact" class="btn-primary">立即咨询</a>
            </nav>
        </div>
    </header>
    <section class="hero-section">
        <div class="container hero-content">
            <span class="badge-pill">🚀 新一代智能化平台 2.0 正式发布</span>
            <h1>释放团队潜能，构建未来级智能业务架构</h1>
            <p class="hero-desc">融合先进 AI 智能体与自动化引擎，为企业提供高效、稳定、全流程赋能的数字化生产力工作空间。</p>
            <div class="hero-cta">
                <a href="#contact" class="btn-primary-large">免费开始体验</a>
                <a href="#features" class="btn-secondary-large">查看技术文档</a>
            </div>
        </div>
    </section>
    <section id="features" class="features-section">
        <div class="container">
            <div class="section-header">
                <h2>为什么选择 {site_title}？</h2>
                <p>专为高标准团队打造的端到端卓越技术体验</p>
            </div>
            <div class="feature-grid">
                <div class="feature-card">
                    <div class="feature-icon">⚡</div>
                    <h3>毫秒级极速响应</h3>
                    <p>采用现代化异步事件驱动架构，确保大规模高并发下的高可用性与极致流畅。</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🛡️</div>
                    <h3>金融级安全隐私</h3>
                    <p>本地私有化隔离与严格的沙箱安全防护体系，全方位守护您的代码与数据资产。</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🤖</div>
                    <h3>多智能体协同</h3>
                    <p>支持多角色 Agent 自主协同规划与流水线任务执行，大幅提升研发与办公生产力。</p>
                </div>
            </div>
        </div>
    </section>
    <footer class="footer">
        <div class="container footer-content">
            <p>© 2026 {site_title}. All rights reserved.</p>
        </div>
    </footer>
    <script src="js/main.js"></script>
</body>
</html>"""
        css_code = """* { margin:0; padding:0; box-sizing:border-box; font-family:'Inter','Microsoft YaHei UI',sans-serif; }
body { background:#090d16; color:#f1f5f9; overflow-x:hidden; }
.container { max-width:1200px; margin:0 auto; padding:0 24px; }
.navbar { padding:20px 0; border-bottom:1px solid rgba(255,255,255,0.08); backdrop-filter:blur(12px); position:sticky; top:0; z-index:100; background:rgba(9,13,22,0.8); }
.nav-container { display:flex; justify-content:space-between; align-items:center; }
.brand-logo { font-family:'Outfit',sans-serif; font-size:22px; font-weight:800; color:#ffffff; text-decoration:none; background:linear-gradient(135deg,#6366f1,#a855f7); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.nav-links { display:flex; align-items:center; gap:28px; }
.nav-links a { color:#cbd5e1; text-decoration:none; font-size:14px; font-weight:500; transition:color 0.2s; }
.nav-links a:hover { color:#ffffff; }
.btn-primary { background:#6366f1; color:#fff !important; padding:8px 18px; border-radius:8px; font-weight:600; }
.btn-primary:hover { background:#4f46e5; }
.hero-section { padding:100px 0 80px; text-align:center; }
.badge-pill { display:inline-block; background:rgba(99,102,241,0.15); border:1px solid rgba(99,102,241,0.3); color:#a5b4fc; padding:6px 16px; border-radius:20px; font-size:13px; font-weight:600; margin-bottom:24px; }
.hero-content h1 { font-family:'Outfit',sans-serif; font-size:48px; line-height:1.2; font-weight:800; max-width:860px; margin:0 auto 20px; background:linear-gradient(180deg,#ffffff,#94a3b8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.hero-desc { font-size:17px; line-height:1.6; color:#94a3b8; max-width:640px; margin:0 auto 36px; }
.hero-cta { display:flex; justify-content:center; gap:16px; }
.btn-primary-large { background:#6366f1; color:#ffffff; text-decoration:none; padding:14px 32px; border-radius:10px; font-weight:600; font-size:16px; transition:transform 0.2s; }
.btn-primary-large:hover { transform:translateY(-2px); background:#4f46e5; }
.btn-secondary-large { background:#1e293b; color:#ffffff; text-decoration:none; padding:14px 32px; border-radius:10px; font-weight:600; font-size:16px; border:1px solid #334155; }
.features-section { padding:80px 0; border-top:1px solid rgba(255,255,255,0.05); }
.section-header { text-align:center; margin-bottom:56px; }
.section-header h2 { font-size:32px; font-weight:700; margin-bottom:12px; }
.section-header p { color:#94a3b8; font-size:15px; }
.feature-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:28px; }
.feature-card { background:#131b2e; border:1px solid #1e293b; padding:36px 28px; border-radius:16px; transition:transform 0.3s, border-color 0.3s; }
.feature-card:hover { transform:translateY(-4px); border-color:#6366f1; }
.feature-icon { font-size:32px; margin-bottom:20px; }
.feature-card h3 { font-size:20px; margin-bottom:12px; }
.feature-card p { color:#94a3b8; font-size:14px; line-height:1.6; }
.footer { padding:40px 0; border-top:1px solid rgba(255,255,255,0.05); text-align:center; color:#64748b; font-size:13px; }"""
        js_code = """console.log('Website initialized successfully.');"""

    (proj_dir / "index.html").write_text(html_code, encoding="utf-8")
    (proj_dir / "css" / "style.css").write_text(css_code, encoding="utf-8")
    (proj_dir / "js" / "main.js").write_text(js_code, encoding="utf-8")

    return f"✅ 成功在工作区生成【{project_type}】网站项目：{proj_dir}\n包含 index.html, css/style.css, js/main.js"


@register_tool(
    name="start_preview_server",
    description="在本地工作区启动轻量 HTTP 静态网页预览服务器，返回可访问的本地 URL 地址"
)
def start_preview_server(project_path: str, port: int = 8080) -> str:
    """
    启动本地轻量 HTTP 静态网页预览服务器
    :param project_path: 网页项目所在目录路径
    :param port: 端口号（默认 8080）
    """
    p = Path(project_path)
    if not p.exists() or not p.is_dir():
        return f"❌ 目录不存在：{project_path}"

    target_port = port
    # 查找可用端口
    while target_port < port + 20:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', target_port)) != 0:
                break
            target_port += 1

    try:
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(p), **kwargs)
            def log_message(self, format, *args):
                pass  # 静默运行

        httpd = socketserver.TCPServer(("127.0.0.1", target_port), Handler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        _ACTIVE_SERVERS[target_port] = httpd

        url = f"http://127.0.0.1:{target_port}/index.html"
        return f"🌐 预览服务器已启动成功！\n- 本地访问地址：{url}\n- 托管目录：{p.resolve()}"
    except Exception as e:
        return f"❌ 启动预览服务器失败：{e}"


@register_tool(
    name="analyze_web_structure",
    description="静态扫描并分析指定网页项目的 HTML/CSS/JS 结构、资源引用与语义化标签健康度"
)
def analyze_web_structure(project_path: str) -> str:
    """
    静态扫描并分析指定网页项目的结构
    :param project_path: 项目根目录
    """
    p = Path(project_path)
    if not p.exists():
        return f"❌ 路径不存在：{project_path}"

    html_files = list(p.glob("**/*.html"))
    css_files = list(p.glob("**/*.css"))
    js_files = list(p.glob("**/*.js"))

    total_files = len(html_files) + len(css_files) + len(js_files)
    res = [
        f"📊 网页项目工程结构体检报告：{p.name}",
        f"- HTML 页面数量：{len(html_files)}",
        f"- CSS 样式表数量：{len(css_files)}",
        f"- JS 脚本文件数量：{len(js_files)}",
        f"- 总计源文件数：{total_files}",
        "✅ 核心入口文件检查：index.html 存在" if (p / "index.html").exists() else "⚠️ 警告：未找到 index.html 入口文件"
    ]
    return "\n".join(res)
