# -*- coding: utf-8 -*-
"""
专业代码编辑器组件 (Dev Code Editor)
- 带有行号侧边栏 (LineNumberArea)
- 代码小地图缩略图 (MinimapArea)：右侧展示全局代码缩略图、视口滑块指示器，支持点击/拖拽任意位置平滑跳转
- 快捷键搜索浮窗 (FindWidget - Ctrl+F)：支持区分大小写(Aa)、全字匹配(ab)、正则(.*)、全文档高亮、实时匹配计数(1 of 6)、上下项切换(Enter/Shift+Enter)与Esc退出
- 当前行高亮光标背景与搜索多重高亮 (ExtraSelections)
- 支持 Python 等常用语言基础语法高亮
- 快捷键支持：Ctrl+F 搜索、Ctrl+S 保存、Tab 缩进 4 空格、F3/Shift+F3 跳转
"""
import re
from PyQt5.QtCore import Qt, QRect, QSize, QEvent, QRegExp
from PyQt5.QtWidgets import (
    QWidget, QPlainTextEdit, QTextEdit, QFrame, QHBoxLayout,
    QLineEdit, QPushButton, QLabel
)
from PyQt5.QtGui import (
    QColor, QPainter, QTextFormat, QFont, QSyntaxHighlighter,
    QTextCharFormat, QKeyEvent, QTextCursor, QTextDocument
)


class LineNumberArea(QWidget):
    """编辑器左侧行号绘制区域"""
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class MinimapArea(QWidget):
    """
    Antigravity / VS Code 风格的代码缩略小地图 (Minimap)
    - 位于编辑器右侧，缩略展示全局代码结构与行长/高亮
    - 半透明滑块 (Viewport Slider) 实时指示当前可视窗口区域
    - 点击或拖拽滑块即可快速定位与平滑跳转到对应代码区域
    - 支持显示搜索高亮标记
    """
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor
        self._is_dragging = False
        self._hovered = False
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    def sizeHint(self):
        return QSize(self.code_editor.minimap_width(), 0)

    def paintEvent(self, event):
        self.code_editor.minimap_paint_event(event)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self.code_editor.minimap_jump_to_y(event.y())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self.code_editor.minimap_jump_to_y(event.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            self.update()
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        # 滚轮事件透传给代码编辑器本体滚动
        self.code_editor.wheelEvent(event)


class FindWidget(QFrame):
    """
    Antigravity / VS Code 风格的编辑器内嵌搜索浮窗 (Ctrl+F Find Widget)
    - 支持实时高亮输入匹配的代码
    - 支持区分大小写 (Aa)、全字匹配 (ab)、正则表达式 (.*)
    - 结果计数 (如 1 of 6) 与上下项跳转 (Enter / Shift+Enter / 按钮)
    - Esc 或点击关闭按钮退出并清除高亮
    """
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor
        self.setObjectName("FindWidget")
        self.setFixedHeight(34)
        self.setFixedWidth(360)

        # 样式：深色现代极客浮窗，半透明阴影与边框
        self.setStyleSheet("""
            QFrame#FindWidget {
                background-color: #252526;
                border: 1px solid #454545;
                border-radius: 5px;
            }
            QLineEdit {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 12px;
                font-family: 'Cascadia Code', Consolas, 'Segoe UI', sans-serif;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QPushButton {
                background: transparent;
                color: #cccccc;
                border: none;
                border-radius: 3px;
                font-size: 11px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #094771;
                color: #ffffff;
                border: 1px solid #007acc;
            }
            QLabel {
                color: #858585;
                font-size: 11px;
                font-family: 'Segoe UI', sans-serif;
            }
        """)

        h_lay = QHBoxLayout(self)
        h_lay.setContentsMargins(6, 4, 6, 4)
        h_lay.setSpacing(4)

        self.icon_lbl = QLabel("›")
        self.icon_lbl.setStyleSheet("color: #858585; font-size: 13px; font-weight: bold; margin-right: 2px;")
        h_lay.addWidget(self.icon_lbl)

        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Find (查找)...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.installEventFilter(self)
        h_lay.addWidget(self.search_input, 1)

        # 选项 1: 区分大小写 (Match Case)
        self.btn_case = QPushButton("Aa")
        self.btn_case.setCheckable(True)
        self.btn_case.setFixedSize(22, 22)
        self.btn_case.setToolTip("区分大小写 (Match Case)")
        self.btn_case.toggled.connect(self._on_option_toggled)
        h_lay.addWidget(self.btn_case)

        # 选项 2: 全字匹配 (Match Whole Word)
        self.btn_word = QPushButton("ab")
        self.btn_word.setCheckable(True)
        self.btn_word.setFixedSize(22, 22)
        self.btn_word.setToolTip("全字匹配 (Match Whole Word)")
        self.btn_word.toggled.connect(self._on_option_toggled)
        h_lay.addWidget(self.btn_word)

        # 选项 3: 正则表达式 (Use Regular Expression)
        self.btn_regex = QPushButton(".*")
        self.btn_regex.setCheckable(True)
        self.btn_regex.setFixedSize(22, 22)
        self.btn_regex.setToolTip("使用正则表达式 (Use Regular Expression)")
        self.btn_regex.toggled.connect(self._on_option_toggled)
        h_lay.addWidget(self.btn_regex)

        # 匹配计数 (如 1 of 6)
        self.counter_lbl = QLabel("No results")
        self.counter_lbl.setStyleSheet("color: #858585; min-width: 50px; font-size: 11px;")
        h_lay.addWidget(self.counter_lbl)

        # 上一个匹配项 (Previous Match ↑)
        self.btn_prev = QPushButton("↑")
        self.btn_prev.setFixedSize(22, 22)
        self.btn_prev.setToolTip("上一个匹配项 (Shift+Enter)")
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.clicked.connect(self.code_editor.find_previous)
        h_lay.addWidget(self.btn_prev)

        # 下一个匹配项 (Next Match ↓)
        self.btn_next = QPushButton("↓")
        self.btn_next.setFixedSize(22, 22)
        self.btn_next.setToolTip("下一个匹配项 (Enter)")
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.clicked.connect(self.code_editor.find_next)
        h_lay.addWidget(self.btn_next)

        # 关闭按钮 (✕)
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setToolTip("关闭 (Escape)")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.hide_and_clear)
        h_lay.addWidget(self.btn_close)

        self.hide()

    def eventFilter(self, obj, event):
        if obj == self.search_input and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.ShiftModifier:
                    self.code_editor.find_previous()
                else:
                    self.code_editor.find_next()
                return True
            elif event.key() == Qt.Key_Escape:
                self.hide_and_clear()
                return True
        return super().eventFilter(obj, event)

    def _on_search_text_changed(self, text: str):
        self.code_editor.perform_search()

    def _on_option_toggled(self, checked: bool):
        self.code_editor.perform_search()

    def update_counter(self, current_idx: int, total: int):
        if total <= 0:
            self.counter_lbl.setText("No results")
            self.counter_lbl.setStyleSheet("color: #f85149; font-size: 11px;")
        else:
            self.counter_lbl.setText(f"{current_idx + 1} of {total}")
            self.counter_lbl.setStyleSheet("color: #858585; font-size: 11px;")

    def show_and_focus(self):
        self.show()
        self.search_input.setFocus()
        self.search_input.selectAll()
        self.code_editor.perform_search()

    def hide_and_clear(self):
        self.hide()
        self.code_editor.clear_search_highlights()
        self.code_editor.setFocus()


class PythonHighlighter(QSyntaxHighlighter):
    """精简高效的 Python 语法高亮器"""
    def __init__(self, parent=None, is_dark=True):
        super().__init__(parent)
        self.is_dark = is_dark
        self.highlighting_rules = []

        kw_color = QColor("#c678dd") if is_dark else QColor("#a626a4")
        func_color = QColor("#61afef") if is_dark else QColor("#4078f2")
        class_color = QColor("#e5c07b") if is_dark else QColor("#c18401")
        str_color = QColor("#98c379") if is_dark else QColor("#50a14f")
        comment_color = QColor("#5c6370") if is_dark else QColor("#a0a1a7")
        num_color = QColor("#d19a66") if is_dark else QColor("#986801")
        decorator_color = QColor("#e5c07b") if is_dark else QColor("#b16286")

        # 关键字
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def",
            "del", "elif", "else", "except", "False", "finally", "for",
            "from", "global", "if", "import", "in", "is", "lambda",
            "None", "nonlocal", "not", "or", "pass", "raise", "return",
            "True", "try", "while", "with", "yield", "async", "await"
        ]
        kw_fmt = QTextCharFormat()
        kw_fmt.setForeground(kw_color)
        kw_fmt.setFontWeight(QFont.Bold)
        for word in keywords:
            pat = rf"\b{word}\b"
            self.highlighting_rules.append((re.compile(pat), kw_fmt))

        # 函数名与类名
        func_fmt = QTextCharFormat()
        func_fmt.setForeground(func_color)
        self.highlighting_rules.append((re.compile(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)"), func_fmt))
        self.highlighting_rules.append((re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)"), func_fmt))

        # 装饰器
        dec_fmt = QTextCharFormat()
        dec_fmt.setForeground(decorator_color)
        self.highlighting_rules.append((re.compile(r"@[A-Za-z0-9_\.]+"), dec_fmt))

        # 数字
        num_fmt = QTextCharFormat()
        num_fmt.setForeground(num_color)
        self.highlighting_rules.append((re.compile(r"\b[0-9]+(\.[0-9]+)?\b"), num_fmt))

        # 字符串 (单双引号)
        str_fmt = QTextCharFormat()
        str_fmt.setForeground(str_color)
        self.highlighting_rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), str_fmt))
        self.highlighting_rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), str_fmt))

        # 注释
        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(comment_color)
        comment_fmt.setFontItalic(True)
        self.highlighting_rules.append((re.compile(r"#[^\n]*"), comment_fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)


class CodeEditor(QPlainTextEdit):
    """
    专业代码编辑器 (对标 Antigravity / Cursor / VS Code)
    - 行号显示 (LineNumberArea)
    - 代码小地图与视口滑块 (MinimapArea)
    - Ctrl+F 搜索与全文档高亮 (FindWidget)
    """
    def __init__(self, parent=None, is_dark=True, show_minimap=False):
        if isinstance(parent, bool):
            is_dark = parent
            parent = None
        super().__init__(parent)
        self.is_dark = is_dark
        self.show_minimap = show_minimap
        self.current_file_path = ""
        self.is_modified = False

        # 搜索状态
        self._search_matches = []  # [(start, length, block_number)]
        self._current_match_index = -1

        # 1. 侧边行号栏
        self.line_number_area = LineNumberArea(self)

        # 2. 右侧小地图 (Minimap，默认关闭以提供全宽纯净代码编辑空间)
        self.minimap = MinimapArea(self)
        if not self.show_minimap:
            self.minimap.hide()

        # 3. 搜索浮窗 (FindWidget)
        self.find_widget = FindWidget(self)

        font = QFont("Cascadia Code", 10)
        if not font.exactMatch():
            font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

        self.blockCountChanged.connect(self._on_block_count_changed)
        self.updateRequest.connect(self._on_update_request)
        self.cursorPositionChanged.connect(self.update_extra_selections)
        self.textChanged.connect(self._on_text_changed)
        self.verticalScrollBar().valueChanged.connect(lambda _: self.minimap.update())

        self.highlighter = PythonHighlighter(self.document(), is_dark=is_dark)

        self.update_margins()
        self.apply_theme(is_dark)
        self.update_extra_selections()

    def _on_block_count_changed(self, _=0):
        self.update_margins()
        self.minimap.update()
        if hasattr(self, 'find_widget') and self.find_widget.isVisible():
            self.perform_search()

    def _on_update_request(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_margins()
        self.minimap.update()

    def _on_text_changed(self):
        self.is_modified = True
        self.minimap.update()
        if hasattr(self, 'find_widget') and self.find_widget.isVisible():
            self.perform_search()

    def apply_theme(self, is_dark: bool):
        self.is_dark = is_dark
        if is_dark:
            self.bg_color = "#1e1e1e"
            self.text_color = "#d4d4d4"
            self.line_num_bg = "#252526"
            self.line_num_fg = "#858585"
            self.cur_line_bg = "#2a2d2e"
            self.selection_bg = "#264f78"
        else:
            self.bg_color = "#ffffff"
            self.text_color = "#24292e"
            self.line_num_bg = "#f3f4f6"
            self.line_num_fg = "#9ca3af"
            self.cur_line_bg = "#f8fafc"
            self.selection_bg = "#cce2ff"

        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {self.bg_color};
                color: {self.text_color};
                border: none;
                selection-background-color: {self.selection_bg};
                font-family: 'Cascadia Code', Consolas, 'Courier New', monospace;
                font-size: 13px;
            }}
        """)
        # 关键：QPlainTextEdit 内部 viewport 是个独立 QWidget，QSS 不会穿透到它。
        # 必须显式给 viewport 调色，否则浅色主题下代码区还是深色。
        try:
            vp = self.viewport()
            if vp is not None:
                vp.setStyleSheet(
                    f"background-color: {self.bg_color}; color: {self.text_color};"
                )
        except Exception:
            pass
        if hasattr(self, 'highlighter') and self.highlighter:
            self.highlighter = PythonHighlighter(self.document(), is_dark=is_dark)
            self.highlighter.rehighlight()
        self.line_number_area.update()
        self.minimap.update()
        self.update_extra_selections()

    # ══════════════════════════════════════════════════════════
    #  行号与视口边距
    # ══════════════════════════════════════════════════════════
    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 18 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def minimap_width(self):
        return 78 if getattr(self, 'show_minimap', False) else 0

    def set_show_minimap(self, show: bool):
        self.show_minimap = bool(show)
        if hasattr(self, 'minimap'):
            self.minimap.setVisible(self.show_minimap)
        self.update_margins()
        self.update()

    def update_margins(self):
        self.setViewportMargins(self.line_number_area_width(), 0, self.minimap_width(), 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        ln_w = self.line_number_area_width()
        mm_w = self.minimap_width()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), ln_w, cr.height()))
        if mm_w > 0:
            self.minimap.setGeometry(QRect(cr.right() - mm_w + 1, cr.top(), mm_w, cr.height()))
            self.minimap.show()
        else:
            self.minimap.hide()
        self._update_find_widget_geometry()

    def _update_find_widget_geometry(self):
        if not hasattr(self, 'find_widget'):
            return
        fw_w = self.find_widget.width()
        fw_h = self.find_widget.height()
        mm_w = self.minimap_width()
        pos_x = max(10, self.width() - mm_w - fw_w - 12)
        pos_y = 8
        self.find_widget.setGeometry(QRect(pos_x, pos_y, fw_w, fw_h))
        self.find_widget.raise_()

    # ══════════════════════════════════════════════════════════
    #  ExtraSelections: 当前行高亮 + 搜索多重高亮
    # ══════════════════════════════════════════════════════════
    def highlight_current_line(self):
        self.update_extra_selections()

    def update_extra_selections(self):
        extra_selections = []

        # 1. 当前行光标行背景高亮
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor(self.cur_line_bg))
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        # 2. 搜索结果多重高亮 (所有匹配项暖黄高亮，当前激活项明亮高亮)
        if self._search_matches and hasattr(self, 'find_widget') and self.find_widget.isVisible():
            doc = self.document()
            for idx, (m_start, m_len, _) in enumerate(self._search_matches):
                match_sel = QTextEdit.ExtraSelection()
                cur = QTextCursor(doc)
                cur.setPosition(m_start)
                cur.setPosition(m_start + m_len, QTextCursor.KeepAnchor)
                match_sel.cursor = cur

                if idx == self._current_match_index:
                    # 当前激活的搜索匹配项：明亮黄底 + 黑字
                    match_sel.format.setBackground(QColor("#f59e0b" if self.is_dark else "#facc15"))
                    match_sel.format.setForeground(QColor("#000000"))
                else:
                    # 其他所有匹配项：半透明琥珀色背景 (对齐截图 3)
                    match_sel.format.setBackground(
                        QColor(234, 179, 8, 85) if self.is_dark else QColor(254, 240, 138, 190)
                    )
                    if not self.is_dark:
                        match_sel.format.setForeground(QColor("#1e293b"))
                extra_selections.append(match_sel)

        self.setExtraSelections(extra_selections)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(self.line_num_bg))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        painter.setFont(self.font())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                is_cur_line = (block_number == self.textCursor().blockNumber())
                painter.setPen(QColor("#60a5fa" if is_cur_line else self.line_num_fg))
                painter.drawText(
                    0, top, self.line_number_area.width() - 8,
                    self.fontMetrics().height(),
                    Qt.AlignRight, number
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    # ══════════════════════════════════════════════════════════
    #  代码小地图 (Minimap) 绘制与平滑跳转
    # ══════════════════════════════════════════════════════════
    def minimap_jump_to_y(self, y: int):
        """点击或拖拽小地图，将主屏幕代码平滑滚动居中跳转到对应行"""
        total_blocks = max(1, self.document().blockCount())
        h = max(1, self.minimap.height())

        target_block = int((y / h) * total_blocks)
        target_block = max(0, min(total_blocks - 1, target_block))

        visible_lines = max(1, self.viewport().height() // max(1, self.fontMetrics().height()))
        scroll_val = max(0, target_block - (visible_lines // 2))
        self.verticalScrollBar().setValue(scroll_val)

    def minimap_paint_event(self, event):
        """绘制微缩代码全貌、搜索高亮标记与当前视口滑块"""
        if not getattr(self, 'show_minimap', False):
            return
        painter = QPainter(self.minimap)
        rect = self.minimap.rect()
        w = rect.width()
        h = rect.height()

        # 1. 绘制小地图背景与左边框
        bg_color = QColor("#181a1f") if self.is_dark else QColor("#f0f2f5")
        border_color = QColor("#282c34") if self.is_dark else QColor("#e5e7eb")
        painter.fillRect(rect, bg_color)
        painter.setPen(border_color)
        painter.drawLine(0, 0, 0, h)

        total_blocks = self.document().blockCount()
        if total_blocks <= 0:
            return

        # 2. 绘制微缩代码条纹
        block = self.document().begin()
        block_idx = 0
        line_step = h / total_blocks

        kw_color = QColor("#c678dd") if self.is_dark else QColor("#a626a4")
        func_color = QColor("#61afef") if self.is_dark else QColor("#4078f2")
        str_color = QColor("#98c379") if self.is_dark else QColor("#50a14f")
        comment_color = QColor("#5c6370") if self.is_dark else QColor("#a0a1a7")
        text_color = QColor(171, 178, 191, 130) if self.is_dark else QColor(56, 58, 66, 130)

        while block.isValid() and block_idx < total_blocks:
            line_y = int(block_idx * line_step)
            txt = block.text()
            if txt.strip():
                indent = len(txt) - len(txt.lstrip())
                indent_px = min(22, 3 + indent * 1.5)
                line_len_px = min(w - indent_px - 4, max(4, int(len(txt.strip()) * 0.75)))

                stripped = txt.strip()
                if stripped.startswith("#"):
                    line_col = comment_color
                elif stripped.startswith(("def ", "class ")):
                    line_col = func_color
                elif stripped.startswith(("import ", "from ", "return ", "if ", "for ", "while ")):
                    line_col = kw_color
                elif stripped.startswith(('"', "'")):
                    line_col = str_color
                else:
                    line_col = text_color

                painter.setPen(Qt.NoPen)
                painter.setBrush(line_col)
                draw_h = 2 if line_step >= 2.5 else 1
                painter.drawRect(int(indent_px), line_y, int(line_len_px), draw_h)

            block = block.next()
            block_idx += 1

        # 3. 绘制搜索结果标记 (Search Match Marks)
        if self._search_matches:
            painter.setBrush(QColor(234, 179, 8, 230))
            for m_start, m_len, m_block in self._search_matches:
                m_y = int(m_block * line_step)
                painter.drawRect(2, m_y, w - 4, 2)

        # 4. 绘制当前可视窗口滑块 (Viewport Slider)
        first_vis = self.firstVisibleBlock().blockNumber()
        line_h = max(1, self.fontMetrics().height())
        visible_lines = max(1, self.viewport().height() // line_h)

        slider_y = int((first_vis / total_blocks) * h)
        slider_h = max(20, int((visible_lines / total_blocks) * h))
        if slider_y + slider_h > h:
            slider_y = max(0, h - slider_h)

        is_hovered = getattr(self.minimap, '_hovered', False) or getattr(self.minimap, '_is_dragging', False)
        slider_fill = QColor(255, 255, 255, 42 if is_hovered else 25)
        slider_border = QColor(255, 255, 255, 80 if is_hovered else 45)

        painter.setBrush(slider_fill)
        painter.setPen(slider_border)
        painter.drawRect(1, slider_y, w - 2, slider_h)

    # ══════════════════════════════════════════════════════════
    #  Ctrl+F 搜索核心逻辑
    # ══════════════════════════════════════════════════════════
    def perform_search(self):
        """根据 FindWidget 设定的选项执行全文搜索并多重高亮匹配"""
        if not hasattr(self, 'find_widget') or not self.find_widget.isVisible():
            self.clear_search_highlights()
            return

        query = self.find_widget.search_input.text()
        if not query:
            self.clear_search_highlights()
            self.find_widget.update_counter(-1, 0)
            return

        is_case = self.find_widget.btn_case.isChecked()
        is_word = self.find_widget.btn_word.isChecked()
        is_regex = self.find_widget.btn_regex.isChecked()

        doc = self.document()
        self._search_matches = []

        try:
            if is_regex:
                rx_opts = QRegExp.CaseSensitive if is_case else QRegExp.CaseInsensitive
                rx = QRegExp(query, rx_opts)
                cursor = QTextCursor(doc)
                while True:
                    cursor = doc.find(rx, cursor)
                    if cursor.isNull():
                        break
                    start = cursor.selectionStart()
                    length = cursor.selectionEnd() - start
                    if length <= 0:
                        cursor.movePosition(QTextCursor.Right)
                        continue
                    self._search_matches.append((start, length, cursor.blockNumber()))
            else:
                flags = QTextDocument.FindFlags()
                if is_case:
                    flags |= QTextDocument.FindCaseSensitively
                if is_word:
                    flags |= QTextDocument.FindWholeWords

                cursor = QTextCursor(doc)
                while True:
                    cursor = doc.find(query, cursor, flags)
                    if cursor.isNull():
                        break
                    start = cursor.selectionStart()
                    length = cursor.selectionEnd() - start
                    self._search_matches.append((start, length, cursor.blockNumber()))
        except Exception as e:
            print(f"[CodeEditor] 搜索执行异常: {e}")
            self._search_matches = []

        total = len(self._search_matches)
        if total > 0:
            cur_pos = self.textCursor().position()
            best_idx = 0
            for idx, (m_start, _, _) in enumerate(self._search_matches):
                if m_start >= cur_pos:
                    best_idx = idx
                    break
            self._current_match_index = best_idx
            self.find_widget.update_counter(self._current_match_index, total)
            self.jump_to_match(self._current_match_index, scroll=True)
        else:
            self._current_match_index = -1
            self.find_widget.update_counter(-1, 0)
            self.update_extra_selections()
            self.minimap.update()

    def find_next(self):
        """跳转定位到下一个搜索匹配项"""
        if not self._search_matches:
            return
        next_idx = (self._current_match_index + 1) % len(self._search_matches)
        self.jump_to_match(next_idx, scroll=True)

    def find_previous(self):
        """跳转定位到上一个搜索匹配项"""
        if not self._search_matches:
            return
        prev_idx = (self._current_match_index - 1 + len(self._search_matches)) % len(self._search_matches)
        self.jump_to_match(prev_idx, scroll=True)

    def jump_to_match(self, match_idx: int, scroll: bool = True):
        """跳转定位到指定索引的匹配项"""
        if not self._search_matches or match_idx < 0 or match_idx >= len(self._search_matches):
            return
        self._current_match_index = match_idx
        m_start, m_len, _ = self._search_matches[self._current_match_index]

        if scroll:
            cur = QTextCursor(self.document())
            cur.setPosition(m_start)
            cur.setPosition(m_start + m_len, QTextCursor.KeepAnchor)
            self.setTextCursor(cur)
            self.centerCursor()

        self.update_extra_selections()
        self.minimap.update()
        if hasattr(self, 'find_widget'):
            self.find_widget.update_counter(self._current_match_index, len(self._search_matches))

    def clear_search_highlights(self):
        """清除全文档搜索高亮标记"""
        self._search_matches = []
        self._current_match_index = -1
        self.update_extra_selections()
        self.minimap.update()

    # ══════════════════════════════════════════════════════════
    #  键盘事件
    # ══════════════════════════════════════════════════════════
    def keyPressEvent(self, event: QKeyEvent):
        # 1. Ctrl+F: 呼出搜索浮窗并高亮匹配
        if (event.modifiers() & Qt.ControlModifier) and event.key() == Qt.Key_F:
            sel_text = self.textCursor().selectedText()
            if sel_text:
                self.find_widget.search_input.setText(sel_text)
            self._update_find_widget_geometry()
            self.find_widget.show_and_focus()
            event.accept()
            return

        # 2. Escape: 若搜索框可见则关闭搜索浮窗并清除高亮
        if event.key() == Qt.Key_Escape and hasattr(self, 'find_widget') and self.find_widget.isVisible():
            self.find_widget.hide_and_clear()
            event.accept()
            return

        # 3. F3 / Shift+F3: 搜索匹配项快速循环跳转
        if event.key() == Qt.Key_F3:
            if event.modifiers() & Qt.ShiftModifier:
                self.find_previous()
            else:
                self.find_next()
            event.accept()
            return

        # 4. Tab 键自动转换为 4 个空格缩进
        if event.key() == Qt.Key_Tab:
            self.insertPlainText("    ")
            event.accept()
            return

        super().keyPressEvent(event)

    def jump_to_line(self, line_no: int):
        """跳转并高亮定位到指定行（1-indexed）"""
        doc = self.document()
        if line_no < 1 or line_no > doc.blockCount():
            return
        block = doc.findBlockByLineNumber(line_no - 1)
        if block.isValid():
            cursor = self.textCursor()
            cursor.setPosition(block.position())
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
            self.centerCursor()
            self.update_extra_selections()
            self.minimap.update()
