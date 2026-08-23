"""
管理中心 - 现代化卡片设计 (窗口始终置顶在最高层，绝不被遮挡)
"""
import json
import threading
import httpx
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QCheckBox, QSpinBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

MODERN_STYLE = """
QWidget {
    background: #121220;
    color: #e2e8f0;
    font-family: "Microsoft YaHei UI", sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid rgba(140, 130, 255, 0.2);
    border-radius: 12px;
    background: #18182c;
}
QTabBar::tab {
    background: #151528;
    color: #94a3b8;
    padding: 10px 22px;
    border-radius: 8px 8px 0 0;
    margin-right: 4px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background: #18182c;
    color: #a5b4fc;
    border-bottom: 2px solid #818cf8;
}
QTabBar::tab:hover {
    background: #1e1e36;
    color: #ffffff;
}
QGroupBox {
    border: 1px solid rgba(140, 130, 255, 0.2);
    border-radius: 10px;
    margin-top: 12px;
    padding: 14px;
    color: #a5b4fc;
    font-weight: bold;
    font-size: 13px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
}
QLineEdit, QComboBox, QSpinBox {
    background: #20203a;
    border: 1px solid rgba(140, 130, 255, 0.25);
    border-radius: 8px;
    padding: 6px 12px;
    color: #f1f5f9;
    min-height: 28px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #6366f1;
    background: #252544;
}
QPushButton {
    background: rgba(140, 120, 255, 0.15);
    color: #e2e8f0;
    border: 1px solid rgba(140, 120, 255, 0.3);
    border-radius: 8px;
    padding: 7px 18px;
    font-size: 12px;
    font-weight: 500;
}
QPushButton:hover {
    background: rgba(140, 120, 255, 0.3);
    color: #ffffff;
}
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
    color: #ffffff;
    border: none;
    font-weight: bold;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
}
QPushButton#danger {
    background: rgba(239, 68, 68, 0.2);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.4);
}
QPushButton#danger:hover {
    background: rgba(239, 68, 68, 0.4);
}
QTableWidget {
    background: #16162a;
    border: 1px solid rgba(140, 130, 255, 0.2);
    border-radius: 8px;
}
QHeaderView::section {
    background: #1e1e36;
    color: #94a3b8;
    padding: 8px;
    border: none;
    border-bottom: 1px solid rgba(140, 130, 255, 0.2);
}
"""


class ControlPanel(QWidget):
    """桌宠管理中心"""

    def __init__(self, config: dict, ai_engine, save_config_fn, pet_window, plugin_manager=None):
        super().__init__()
        self.config = config
        self.ai_engine = ai_engine
        self.save_config_fn = save_config_fn
        self.pet_window = pet_window
        self.plugin_manager = plugin_manager

        self.setWindowTitle("⚙️ 桌宠管理中心")
        self.setMinimumSize(720, 600)
        # 始终置顶在最高层，确保弹出时永远在聊天窗口前面
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(MODERN_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        top_bar = QHBoxLayout()
        title = QLabel("🐱 桌宠管理中心")
        title.setStyleSheet("font-size: 19px; font-weight: bold; color: #c7d2fe;")
        top_bar.addWidget(title)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._build_model_tab()
        self._build_plugin_tab()
        self._build_behavior_tab()
        self._build_memory_tab()

    # ── 1. AI 模型 Tab ──
    def _build_model_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        provider_group = QGroupBox("选择 AI 服务商")
        pg_layout = QHBoxLayout(provider_group)
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Ollama (本地免费)", "OpenAI", "Claude", "Custom (自定义兼容API)"])
        provider_map = {"ollama": 0, "openai": 1, "claude": 2, "custom": 3}
        self.provider_combo.setCurrentIndex(provider_map.get(self.config.get("ai", {}).get("provider", "ollama"), 0))
        self.provider_combo.currentIndexChanged.connect(self._on_provider_change)
        pg_layout.addWidget(QLabel("服务提供商:"))
        pg_layout.addWidget(self.provider_combo, 1)
        layout.addWidget(provider_group)

        self.ollama_group = QGroupBox("Ollama 本地模型配置")
        og = QVBoxLayout(self.ollama_group)
        self.ollama_url = QLineEdit(self.config.get("ai", {}).get("ollama", {}).get("base_url", "http://localhost:11434"))
        self.ollama_chat_model = QComboBox()
        self.ollama_chat_model.setEditable(True)

        current_m = self.config.get("ai", {}).get("ollama", {}).get("chat_model", "deepseek-r1:14b")
        self.ollama_chat_model.addItem(current_m)
        self.ollama_chat_model.setCurrentText(current_m)

        refresh_btn = QPushButton("🔄 自动获取本地已安装模型")
        refresh_btn.clicked.connect(self._refresh_ollama_models)

        for label_text, widget in [
            ("Ollama 地址:", self.ollama_url),
            ("对话模型:", self.ollama_chat_model),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(80)
            row.addWidget(lbl)
            row.addWidget(widget)
            og.addLayout(row)
        og.addWidget(refresh_btn)
        layout.addWidget(self.ollama_group)

        self.api_group = QGroupBox("云端 API 配置")
        ag = QVBoxLayout(self.api_group)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_base_edit = QLineEdit()
        self.api_model_edit = QLineEdit()

        show_key_btn = QPushButton("👁 显示/隐藏 Key")
        show_key_btn.clicked.connect(
            lambda: self.api_key_edit.setEchoMode(
                QLineEdit.EchoMode.Normal
                if self.api_key_edit.echoMode() == QLineEdit.EchoMode.Password
                else QLineEdit.EchoMode.Password
            )
        )
        for label_text, widget in [
            ("API Key:", self.api_key_edit),
            ("Base URL:", self.api_base_edit),
            ("模型名称:", self.api_model_edit),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(80)
            row.addWidget(lbl)
            row.addWidget(widget)
            ag.addLayout(row)
        ag.addWidget(show_key_btn)
        layout.addWidget(self.api_group)

        btn_row = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #a5b4fc; font-size: 12px;")
        test_btn = QPushButton("🔌 测试连接")
        test_btn.clicked.connect(self._test_connection)
        save_btn = QPushButton("💾 保存配置")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save_model_config)
        btn_row.addWidget(self.status_label, 1)
        btn_row.addWidget(test_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)
        layout.addStretch()

        self._load_api_config()
        self._on_provider_change(self.provider_combo.currentIndex())
        self.tabs.addTab(tab, "🤖 AI 模型")

        threading.Thread(target=self._fetch_models_in_background, daemon=True).start()

    def _fetch_models_in_background(self):
        url = self.ollama_url.text().strip() or "http://localhost:11434"
        try:
            with httpx.Client(timeout=2.5) as client:
                r = client.get(f"{url}/api/tags")
                if r.status_code == 200:
                    models = [m["name"] for m in r.json().get("models", [])]
                    if models:
                        QTimer.singleShot(0, lambda: self._update_model_dropdown(models))
        except Exception:
            pass

    def _update_model_dropdown(self, models):
        current = self.ollama_chat_model.currentText()
        self.ollama_chat_model.clear()
        self.ollama_chat_model.addItems(models)
        if current in models:
            self.ollama_chat_model.setCurrentText(current)

    def _refresh_ollama_models(self):
        self.status_label.setText("正在扫描本地已安装模型...")
        url = self.ollama_url.text().strip() or "http://localhost:11434"
        try:
            with httpx.Client(timeout=3.0) as client:
                r = client.get(f"{url}/api/tags")
                if r.status_code == 200:
                    models = [m["name"] for m in r.json().get("models", [])]
                    if models:
                        self._update_model_dropdown(models)
                        self.status_label.setText(f"✅ 已成功获取 {len(models)} 个本地模型：{', '.join(models)}")
                        return
            self.status_label.setText("⚠️ 未检测到已运行的 Ollama 模型")
        except Exception as e:
            self.status_label.setText(f"❌ 获取失败: {e}")

    def _test_connection(self):
        self._save_model_config(silent=True)
        self.status_label.setText("🔌 测试连接中...")
        url = self.ollama_url.text().strip() or "http://localhost:11434"
        try:
            with httpx.Client(timeout=3.0) as client:
                r = client.get(f"{url}/api/tags")
                if r.status_code == 200:
                    self.status_label.setText("✅ Ollama 连通正常，服务就绪！")
                else:
                    self.status_label.setText(f"⚠️ 状态码: {r.status_code}")
        except Exception as e:
            self.status_label.setText(f"❌ 无法连接 Ollama: {e}")

    def _on_provider_change(self, idx: int):
        provider = ["ollama", "openai", "claude", "custom"][idx]
        is_ollama = (provider == "ollama")
        self.ollama_group.setVisible(is_ollama)
        self.api_group.setVisible(not is_ollama)
        self._load_api_config()

    def _load_api_config(self):
        idx = self.provider_combo.currentIndex()
        provider = ["ollama", "openai", "claude", "custom"][idx]
        cfg = self.config.get("ai", {}).get(provider, {})
        self.api_key_edit.setText(cfg.get("api_key", ""))
        self.api_base_edit.setText(cfg.get("base_url", ""))
        self.api_model_edit.setText(cfg.get("model", ""))

    def _save_model_config(self, silent=False):
        idx = self.provider_combo.currentIndex()
        provider = ["ollama", "openai", "claude", "custom"][idx]
        self.config.setdefault("ai", {})["provider"] = provider

        if provider == "ollama":
            self.config["ai"].setdefault("ollama", {})["base_url"] = self.ollama_url.text().strip()
            self.config["ai"]["ollama"]["chat_model"] = self.ollama_chat_model.currentText()
        elif provider == "openai":
            self.config["ai"].setdefault("openai", {})["api_key"] = self.api_key_edit.text().strip()
            self.config["ai"]["openai"]["base_url"] = self.api_base_edit.text().strip()
            self.config["ai"]["openai"]["model"] = self.api_model_edit.text().strip()
        elif provider == "claude":
            self.config["ai"].setdefault("claude", {})["api_key"] = self.api_key_edit.text().strip()
            self.config["ai"]["claude"]["model"] = self.api_model_edit.text().strip()
        elif provider == "custom":
            self.config["ai"].setdefault("custom", {})["api_key"] = self.api_key_edit.text().strip()
            self.config["ai"]["custom"]["base_url"] = self.api_base_edit.text().strip()
            self.config["ai"]["custom"]["model"] = self.api_model_edit.text().strip()

        # 真正持久化写入硬盘的 config.json
        self.save_config_fn(self.config)
        # 真正热重载内存中的 AIEngine 变量
        self.ai_engine.reload_config(self.config)
        if not silent:
            self.status_label.setText("✅ 配置已写入 config.json 并即时生效！")

    # ── 2. 插件管理 Tab ──
    def _build_plugin_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.plugin_table = QTableWidget(0, 4)
        self.plugin_table.setHorizontalHeaderLabels(["插件名称", "包含工具", "状态", "操作"])
        self.plugin_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.plugin_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.plugin_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.plugin_table)

        plugin_dir = str(Path(__file__).parent.parent / "plugins")
        dir_label = QLabel(f"📁 插件文件夹: {plugin_dir}")
        dir_label.setStyleSheet("font-size: 11px; color: #94a3b8; padding: 4px;")
        layout.addWidget(dir_label)

        btn_row = QHBoxLayout()
        open_dir_btn = QPushButton("📂 打开插件目录")
        open_dir_btn.clicked.connect(lambda: __import__("os").startfile(plugin_dir))
        reload_btn = QPushButton("🔄 重载所有插件")
        reload_btn.setObjectName("primary")
        reload_btn.clicked.connect(self._reload_plugins)
        btn_row.addWidget(open_dir_btn)
        btn_row.addStretch()
        btn_row.addWidget(reload_btn)
        layout.addLayout(btn_row)

        self.tabs.addTab(tab, "🔌 插件扩展")
        self._refresh_plugin_table()

    def _refresh_plugin_table(self):
        plugin_dir = Path(__file__).parent.parent / "plugins"
        plugins = [p for p in plugin_dir.glob("*.py") if not p.name.startswith("_")]

        pm = self.plugin_manager
        self.plugin_table.setRowCount(len(plugins))
        for row, py_file in enumerate(plugins):
            plugin_name = py_file.stem
            if pm and plugin_name in pm.loaded_plugins:
                tool_count = len(pm.loaded_plugins[plugin_name].get("tools", []))
                enabled = pm.loaded_plugins[plugin_name].get("enabled", True)
            else:
                tool_count = 0
                enabled = True

            name_item = QTableWidgetItem(plugin_name)
            count_item = QTableWidgetItem(f"{tool_count} 个能力")
            status_item = QTableWidgetItem("🟢 启用" if enabled else "⚪ 禁用")
            status_item.setForeground(QColor("#4ade80") if enabled else QColor("#94a3b8"))

            toggle_btn = QPushButton("禁用" if enabled else "启用")
            style_off = "background: rgba(239, 68, 68, 0.2); color: #f87171; font-size: 11px; padding: 3px 10px; border-radius: 4px;"
            style_on  = "background: rgba(34, 197, 94, 0.2); color: #4ade80; font-size: 11px; padding: 3px 10px; border-radius: 4px;"
            toggle_btn.setStyleSheet(style_off if enabled else style_on)
            toggle_btn.clicked.connect(
                lambda checked, n=plugin_name, e=enabled: self._toggle_plugin(n, not e)
            )

            self.plugin_table.setItem(row, 0, name_item)
            self.plugin_table.setItem(row, 1, count_item)
            self.plugin_table.setItem(row, 2, status_item)
            self.plugin_table.setCellWidget(row, 3, toggle_btn)

    def _toggle_plugin(self, plugin_name: str, enable: bool):
        if self.plugin_manager:
            self.plugin_manager.toggle_plugin(plugin_name, enable)
        self._refresh_plugin_table()

    def _reload_plugins(self):
        if self.plugin_manager:
            self.plugin_manager.reload_all()
            self._refresh_plugin_table()
            QMessageBox.information(self, "重载插件", "✅ 所有插件已重新扫描并加载！")

    # ── 3. 行为设置 Tab ──
    def _build_behavior_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)

        basic_group = QGroupBox("基础属性")
        bg = QVBoxLayout(basic_group)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("桌宠名字:"))
        self.pet_name_edit = QLineEdit(self.config.get("behavior", {}).get("pet_name", "小桃"))
        name_row.addWidget(self.pet_name_edit)
        bg.addLayout(name_row)

        self.emotion_cb = QCheckBox("启用情感状态机（根据对话情绪切换表情）")
        self.emotion_cb.setChecked(self.config.get("behavior", {}).get("emotion_system", True))
        bg.addWidget(self.emotion_cb)
        layout.addWidget(basic_group)

        layout.addStretch()
        save_btn = QPushButton("💾 保存行为设置")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save_behavior_config)
        layout.addWidget(save_btn)

        self.tabs.addTab(tab, "😊 行为偏好")

    def _save_behavior_config(self):
        self.config.setdefault("behavior", {})["pet_name"] = self.pet_name_edit.text().strip()
        self.config["behavior"]["emotion_system"] = self.emotion_cb.isChecked()
        self.save_config_fn(self.config)
        QMessageBox.information(self, "保存成功", "✅ 行为设置已更新！")

    # ── 4. 记忆管理 Tab ──
    def _build_memory_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        self.memory_stats = QLabel("加载中...")
        self.memory_stats.setStyleSheet("font-size: 13px; font-weight: bold; color: #a5b4fc;")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 输入关键词搜索历史对话...")
        self.search_edit.textChanged.connect(self._on_search_changed)

        top_row.addWidget(self.memory_stats)
        top_row.addStretch()
        top_row.addWidget(self.search_edit)
        layout.addLayout(top_row)

        self.memory_list = QListWidget()
        self.memory_list.setStyleSheet("""
            QListWidget {
                background: #16162a;
                border: 1px solid rgba(140, 130, 255, 0.2);
                border-radius: 10px;
                padding: 6px;
            }
            QListWidget::item {
                background: #1e1e36;
                border-radius: 8px;
                margin-bottom: 6px;
                padding: 10px;
            }
            QListWidget::item:hover {
                background: #252544;
            }
        """)
        layout.addWidget(self.memory_list)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新记录")
        refresh_btn.clicked.connect(self._load_memory)
        clear_btn = QPushButton("🗑️ 清空全部记忆")
        clear_btn.setObjectName("danger")
        clear_btn.clicked.connect(self._clear_memory)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

        self.tabs.addTab(tab, "🧠 记忆管理")
        self._load_memory()

    def _load_memory(self, records=None):
        self.memory_list.clear()
        if not (hasattr(self.ai_engine, 'memory') and self.ai_engine.memory):
            self.memory_stats.setText("记忆系统未就绪")
            return

        if records is None:
            records = self.ai_engine.memory.get_recent_conversations(100)
            total = self.ai_engine.memory.get_conversation_count()
            self.memory_stats.setText(f"📊 共记录 {total} 轮对话 (当前显示最近 {len(records)} 轮)")

        for r in reversed(records):
            time_str = r.get("time", "")[:19].replace("T", " ")
            item_text = f"⏰ [{time_str}]\n👤 用户: {r.get('user', '')}\n🌸 小桃: {r.get('ai', '')}"
            item = QListWidgetItem(item_text)
            self.memory_list.addItem(item)

    def _on_search_changed(self, text: str):
        kw = text.strip()
        if not kw:
            self._load_memory()
            return
        if hasattr(self.ai_engine, 'memory') and self.ai_engine.memory:
            results = self.ai_engine.memory.search_conversations(kw)
            self.memory_stats.setText(f"🔍 找到 {len(results)} 条包含「{kw}」的对话")
            self._load_memory(records=results)

    def _clear_memory(self):
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有本地对话记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self.ai_engine, 'memory') and self.ai_engine.memory:
                self.ai_engine.memory.clear_conversations()
                self.ai_engine.clear_history()
            self._load_memory()
            QMessageBox.information(self, "完成", "✅ 记忆数据库已重置！")
