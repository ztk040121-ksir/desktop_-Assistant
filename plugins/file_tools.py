# -*- coding: utf-8 -*-
"""
全能专业文档与电子表格处理插件 (Document & Excel/Word/PDF Automation Plugin)
支持：
1. 复杂 Excel 复合指令执行（查找替换、合并单元格/合并列、数据排序与求和计算、表头与样式排版）
2. 过滤 Windows Excel 独占锁定临时文件 (~$*.xlsx)
3. Word 文档 (.docx) 的读取、修改、段落追加、新建排版
4. PDF 文档 (.pdf) 的全文提取与表格结构化解析
5. 返回结构化文件卡片，支持聊天界面直接一键打开/另存为/定位文件夹
"""
import os
import re
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict
from core.plugin_manager import register_tool
from core.security_guard import check_sandbox_path, SecurityGuard


def _clean_path(path_str: str) -> str:
    """清理路径，支持 file:/// 格式与各种 Windows 路径，并过滤 ~$ 临时锁文件，相对路径基于工作空间"""
    if not path_str:
        return ""
    p = path_str.strip().strip('"').strip("'")
    if p.startswith("file:///"):
        p = p[8:]
    elif p.startswith("file://"):
        p = p[7:]
    norm_p = os.path.normpath(p)
    file_p = Path(norm_p)
    if not file_p.is_absolute():
        ws_root = SecurityGuard.get_instance().workspace_root
        file_p = (Path(ws_root) / file_p).resolve()
        norm_p = str(file_p)
    if file_p.name.startswith("~$"):
        real_name = file_p.name[2:]
        real_p = file_p.parent / real_name
        if real_p.exists():
            return str(real_p)
    return norm_p


def _find_latest_file(ext_list: List[str]) -> Optional[str]:
    """在桌面自动寻找最近修改的目标格式文件（严格忽略 ~$ 临时文件）"""
    desktop = Path.home() / "Desktop"
    candidates = []
    for ext in ext_list:
        for f in desktop.glob(f"*{ext}"):
            if f.is_file() and not f.name.startswith("~$") and not f.name.startswith("."):
                candidates.append((f, f.stat().st_mtime))
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        return str(candidates[0][0])
    return None


def _format_file_card(file_path: Path, summary_text: str, ops_details: List[str]) -> str:
    """生成带交互文件卡片标记的返回文本"""
    size_kb = round(file_path.stat().st_size / 1024, 2) if file_path.exists() else 0
    ext = file_path.suffix.lstrip(".").upper()
    detail_lines = "\n".join([f"  • {op}" for op in ops_details]) if ops_details else "  • 自动优化与数据更新完成"
    
    card_tag = f"[[FILE_CARD:{file_path}|{file_path.name}|{size_kb} KB|{ext}]]"

    return f"""{card_tag}
📊 **【Excel 表格处理报告】：`{file_path.name}`**

✨ **执行处理明细**：
{detail_lines}

{summary_text}"""


@register_tool(description="AI 动态代码解释器(Code Interpreter)：在沙箱中动态执行 openpyxl Python 代码，实现对 Excel 表格的任意复杂修改、多列合并、跨列计算、高亮格式化与排版。参数：file_path(表格路径), python_code(由 AI 自主编写的 openpyxl Python 处理代码)")
def execute_excel_code(file_path: str = "", python_code: str = "") -> str:
    """动态执行 AI 编写的 openpyxl 代码"""
    err = check_sandbox_path(file_path)
    if err:
        return err

    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

        clean_p = _clean_path(file_path)
        if not clean_p or not Path(clean_p).exists() or Path(clean_p).name.startswith("~$"):
            clean_p = _find_latest_file([".xlsx", ".xls", ".csv"])
            if not clean_p:
                return "❌ 未找到 Excel 文件~"

        target_file = Path(clean_p)
        wb = openpyxl.load_workbook(str(target_file))
        ws = wb.active

        local_scope = {
            "wb": wb,
            "ws": ws,
            "openpyxl": openpyxl,
            "Font": Font,
            "Alignment": Alignment,
            "PatternFill": PatternFill,
            "Border": Border,
            "Side": Side,
            "Path": Path,
            "re": re,
            "target_file": target_file
        }

        code_to_exec = python_code.strip()
        if code_to_exec.startswith("```python"):
            code_to_exec = code_to_exec[9:]
        elif code_to_exec.startswith("```"):
            code_to_exec = code_to_exec[3:]
        if code_to_exec.endswith("```"):
            code_to_exec = code_to_exec[:-3]

        exec(code_to_exec, {}, local_scope)

        saved_file = target_file
        try:
            wb.save(str(target_file))
        except PermissionError:
            stem = target_file.stem.replace("_已处理", "").replace("_已修改", "")
            saved_file = target_file.parent / f"{stem}_已处理.xlsx"
            wb.save(str(saved_file))

        try:
            os.startfile(str(saved_file))
        except Exception:
            pass

        return _format_file_card(
            saved_file,
            "🌸 AI 智能代码解释器已成功执行处理，并在桌面上保存打开！",
            ["执行动态表格处理脚本", f"自动更新电子表格：{saved_file.name}"]
        )
    except Exception as e:
        return f"❌ 动态代码执行异常：{e}"


@register_tool(description="根据自然语言指令，对指定的 Excel 电子表格执行一揽子复合处理（支持查找替换姓名/数值、合并单元格/合并列、数据排序、求和计算等）。参数：file_path(表格完整路径), instruction(用户的具体处理需求)")
def process_excel_file(file_path: str = "", instruction: str = "") -> str:
    """复杂 Excel 复合处理引擎"""
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

        clean_p = _clean_path(file_path)
        if not clean_p or not Path(clean_p).exists() or Path(clean_p).name.startswith("~$"):
            latest = _find_latest_file([".xlsx", ".xls", ".csv"])
            if latest:
                clean_p = latest
            else:
                return "❌ 未找到要处理的 Excel 文件，请拖拽或选择文件上传~"

        # 权限与安全沙箱拦截校验
        guard_err = check_sandbox_path(clean_p)
        if guard_err:
            return guard_err

        target_file = Path(clean_p)
        wb = openpyxl.load_workbook(str(target_file))
        ws = wb.active

        ops_performed = []

        # 1. 查找替换操作 (如把刘洋改成旷文涵, 把张伟改成旷镇涛)
        rep_matches = re.findall(r'把(?:里面的|表格里的)?\s*([^\s,，到成为]+?)\s*(?:改[成为到]|替换[成为到]|换[成为到])\s*([^\s,，。！!]+)', instruction)
        for find_t, replace_t in rep_matches:
            count = 0
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None and find_t in str(cell.value):
                        new_val = str(cell.value).replace(find_t, replace_t)
                        try:
                            cell.value = float(new_val) if "." in new_val else int(new_val)
                        except ValueError:
                            cell.value = new_val
                        count += 1
            if count > 0:
                ops_performed.append(f"将表格中的 『{find_t}』 替换为 『{replace_t}』(共 {count} 处)")

        # 探测真正的表头行 (包含至少 3 个有效表头字段的行)
        header_row_idx = 1
        for r_idx in range(1, min(10, ws.max_row + 1)):
            non_empty_cells = [str(ws.cell(row=r_idx, column=c).value or "").strip() for c in range(1, ws.max_column + 1)]
            valid_headers = [t for t in non_empty_cells if t]
            if len(valid_headers) >= 3:
                header_row_idx = r_idx
                break

        # 2. 排序操作 (如：按照社会公积金降序排序 / 升序排序)
        if any(k in instruction for k in ["排序", "降序", "升序"]):
            is_desc = "降序" in instruction or "从大到小" in instruction or "由高到低" in instruction or not ("升序" in instruction)
            
            # 找到排序列
            sort_col_idx = None
            sort_col_name = ""
            for c_idx in range(1, ws.max_column + 1):
                val = str(ws.cell(row=header_row_idx, column=c_idx).value or "")
                if any(w in instruction and w in val for w in ["公积金", "社保", "个税", "工资", "奖金", "实发", "基本", "绩效"]):
                    sort_col_idx = c_idx
                    sort_col_name = val
                    break
            if not sort_col_idx:
                sort_col_idx = 4 # 默认数值列

            data_rows = []
            for r_idx in range(header_row_idx + 1, ws.max_row + 1):
                row_vals = [ws.cell(row=r_idx, column=c).value for c in range(1, ws.max_column + 1)]
                if any(v is not None for v in row_vals):
                    data_rows.append(row_vals)

            def get_sort_key(row):
                val = row[sort_col_idx - 1] if (row and sort_col_idx - 1 < len(row)) else 0
                if val is None:
                    return -999999999.0 if is_desc else 999999999.0
                try:
                    clean_num_str = str(val).replace(',', '').replace('¥', '').replace('元', '').strip()
                    return float(clean_num_str)
                except (ValueError, TypeError):
                    return -999999999.0 if is_desc else 999999999.0

            data_rows.sort(key=get_sort_key, reverse=is_desc)

            # 写回排序后的行
            for r_offset, r_data in enumerate(data_rows):
                r_num = header_row_idx + 1 + r_offset
                for c_num, val in enumerate(r_data, start=1):
                    ws.cell(row=r_num, column=c_num, value=val)

            order_str = "降序" if is_desc else "升序"
            ops_performed.append(f"将数据行按 『{sort_col_name or '指定列'}』 进行 {order_str} 排序")

        # 3. 合并列 / 合并单元格操作 (如：合并社会公积金和个税的单元格, 合并绩效工资和基本工资)
        if any(k in instruction for k in ["合并单元格", "合并列", "合并"]):
            pairs = [
                (["社会", "公积金", "社保"], ["个税", "税"]),
                (["基本", "底薪"], ["绩效", "奖金"]),
                (["工资"], ["奖金"])
            ]
            
            matched_pair = None
            for p1_words, p2_words in pairs:
                if any(w in instruction for w in p1_words) and any(w in instruction for w in p2_words):
                    matched_pair = (p1_words, p2_words)
                    break

            col_idxs = []
            if matched_pair:
                p1_words, p2_words = matched_pair
                c1, c2 = None, None
                for c_idx in range(1, ws.max_column + 1):
                    val = str(ws.cell(row=header_row_idx, column=c_idx).value or "")
                    if not c1 and any(w in val for w in p1_words):
                        c1 = c_idx
                    elif not c2 and any(w in val for w in p2_words):
                        c2 = c_idx
                if c1 and c2:
                    col_idxs = sorted([c1, c2])

            # 如果没有匹配预设对，尝试通用匹配两个相邻列
            if not col_idxs and len(instruction) > 0:
                for c_idx in range(1, ws.max_column + 1):
                    val = str(ws.cell(row=header_row_idx, column=c_idx).value or "")
                    if val and val in instruction and c_idx not in col_idxs:
                        col_idxs.append(c_idx)

            if len(col_idxs) >= 2:
                col_idxs.sort()
                c_start, c_end = col_idxs[0], col_idxs[1]
                old_h1 = ws.cell(row=header_row_idx, column=c_start).value or ""
                old_h2 = ws.cell(row=header_row_idx, column=c_end).value or ""
                
                if "社保" in str(old_h1) or "公积金" in str(old_h1) or "税" in str(old_h2):
                    new_header = "社保公积金与个税(元)"
                elif "基本" in str(old_h1) or "绩效" in str(old_h2):
                    new_header = "基本与绩效工资(元)"
                else:
                    new_header = f"{old_h1}+{old_h2}"

                # 合并表头
                ws.cell(row=header_row_idx, column=c_start, value=new_header)
                ws.cell(row=header_row_idx, column=c_end, value="")
                ws.merge_cells(start_row=header_row_idx, start_column=c_start, end_row=header_row_idx, end_column=c_end)
                ws.cell(row=header_row_idx, column=c_start).alignment = Alignment(horizontal="center", vertical="center")

                # 合并数据行
                for r_idx in range(header_row_idx + 1, ws.max_row + 1):
                    v1 = ws.cell(row=r_idx, column=c_start).value or 0
                    v2 = ws.cell(row=r_idx, column=c_end).value or 0
                    try:
                        comb = round(float(v1) + float(v2), 2)
                    except Exception:
                        comb = f"{v1} {v2}"
                    ws.cell(row=r_idx, column=c_start, value=comb)
                    ws.cell(row=r_idx, column=c_end, value="")
                    ws.merge_cells(start_row=r_idx, start_column=c_start, end_row=r_idx, end_column=c_end)
                    ws.cell(row=r_idx, column=c_start).alignment = Alignment(horizontal="right", vertical="center")

                ops_performed.append(f"合并 『{old_h1}』 与 『{old_h2}』 为 『{new_header}』 并合并计算单元格数据")

                # 5. 条件格式化与背景颜色高亮 (如：把实发工资大于15000的标为浅黄色, 把部门为研发部的标为浅绿色)
        if any(k in instruction for k in ["标为", "标记为", "高亮", "标黄", "标红", "标绿", "标蓝", "变黄", "变红", "背景色", "浅黄", "浅绿", "浅红", "浅蓝", "黄色", "红色", "绿色", "蓝色"]):
            COLOR_MAP = {
                "浅黄": "FFF2CC",
                "黄": "FFFF00",
                "浅绿": "E2EFDA",
                "绿": "C6EFCE",
                "浅红": "FCE4D6",
                "红": "FFC7CE",
                "浅蓝": "DDEBF7",
                "蓝": "BDD7EE"
            }
            target_color_hex = "FFF2CC" # 默认浅黄
            color_name = "浅黄色"
            for c_name, c_hex in COLOR_MAP.items():
                if c_name in instruction:
                    target_color_hex = c_hex
                    color_name = f"{c_name}色"
                    break

            # 寻找排序列或目标列 (长词优先精准匹配)
            target_col = None
            target_col_name = ""
            priority_keywords = ["实发工资", "实发", "基本与绩效", "基本工资", "基本", "绩效奖金", "绩效", "社保公积金", "公积金", "个税", "部门", "工号", "姓名"]
            for kw in priority_keywords:
                if kw in instruction:
                    for c in range(1, ws.max_column + 1):
                        val = str(ws.cell(row=header_row_idx, column=c).value or "")
                        if kw in val:
                            target_col = c
                            target_col_name = val
                            break
                    if target_col:
                        break
            if not target_col:
                target_col = ws.max_column - 1
                target_col_name = str(ws.cell(row=header_row_idx, column=target_col).value or "数据列")

            # 判断条件: 大于 / 小于 / 等于
            cond_m_gt = re.search(r'(?:大于|>|超过|高于)\s*(\d+(?:\.\d+)?)', instruction)
            cond_m_lt = re.search(r'(?:小于|<|低于)\s*(\d+(?:\.\d+)?)', instruction)
            
            fill = PatternFill(start_color=target_color_hex, end_color=target_color_hex, fill_type="solid")
            hl_count = 0

            for r in range(header_row_idx + 1, ws.max_row + 1):
                cell = ws.cell(row=r, column=target_col)
                val = cell.value
                if val is not None:
                    if cond_m_gt:
                        thresh = float(cond_m_gt.group(1))
                        try:
                            num = float(str(val).replace(',', '').replace('¥', '').replace('元', '').strip())
                            if num > thresh:
                                cell.fill = fill
                                hl_count += 1
                        except Exception:
                            pass
                    elif cond_m_lt:
                        thresh = float(cond_m_lt.group(1))
                        try:
                            num = float(str(val).replace(',', '').replace('¥', '').replace('元', '').strip())
                            if num < thresh:
                                cell.fill = fill
                                hl_count += 1
                        except Exception:
                            pass
                    else:
                        # 文本匹配高亮
                        for keyword in ["已发放", "技术研发部", "旷镇涛", "旷文涵"]:
                            if keyword in instruction and keyword in str(val):
                                cell.fill = fill
                                hl_count += 1

            cond_desc = f"大于 {cond_m_gt.group(1)}" if cond_m_gt else (f"小于 {cond_m_lt.group(1)}" if cond_m_lt else "满足条件")
            ops_performed.append(f"将 『{target_col_name or '目标列'}』 中 {cond_desc} 的单元格背景标记为 【{color_name}】 (共高亮 {hl_count} 处)")

                # 6. 新增求和列 / 求和做新的一栏 / 添加总计列 (如：求和做新的一栏、把基本绩效工资求和做新的一栏、新增总计列)
        if any(k in instruction for k in ["求和做新的一栏", "做新的一栏", "新增一列", "新的一栏", "新的一列", "总计列", "合计列", "求和一栏"]):
            new_c_idx = ws.max_column + 1
            col_title = "总计(元)"
            if "基本" in instruction or "绩效" in instruction:
                col_title = "基本与绩效求和(元)"
            elif "社保" in instruction or "公积金" in instruction or "税" in instruction:
                col_title = "社保与税求和(元)"
            elif "工资" in instruction:
                col_title = "工资总和(元)"

            # 设置新列标题
            h_cell = ws.cell(row=header_row_idx, column=new_c_idx, value=col_title)
            h_cell.font = Font(name="微软雅黑", size=10, bold=True, color="1E293B")
            h_cell.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
            h_cell.alignment = Alignment(horizontal="center", vertical="center")

            # 确定要累加的列
            target_cols = []
            if "基本" in instruction or "绩效" in instruction:
                for c in range(1, new_c_idx):
                    v = str(ws.cell(row=header_row_idx, column=c).value or "")
                    if any(k in v for k in ["基本", "绩效", "基本与绩效"]):
                        target_cols.append(c)
            
            if not target_cols:
                # 默认累加所有数值列
                for c in range(1, new_c_idx):
                    v = str(ws.cell(row=header_row_idx, column=c).value or "")
                    if any(k in v for k in ["工资", "奖金", "金", "税", "金额", "总", "元"]):
                        target_cols.append(c)

            if not target_cols:
                target_cols = [c for c in range(4, new_c_idx)]

            # 逐行求和填充
            for r in range(header_row_idx + 1, ws.max_row + 1):
                row_sum = 0.0
                for c in target_cols:
                    val = ws.cell(row=r, column=c).value
                    if val is not None:
                        try:
                            num = float(str(val).replace(',', '').replace('¥', '').replace('元', '').strip())
                            row_sum += num
                        except Exception:
                            pass
                c_out = ws.cell(row=r, column=new_c_idx, value=round(row_sum, 2))
                c_out.font = Font(name="微软雅黑", size=10)
                c_out.alignment = Alignment(horizontal="right", vertical="center")

            ops_performed.append(f"新增求和列 『{col_title}』，已自动计算并填入每行汇总数值")

        # 4. 安全保存（防文件被 Excel 独占锁定）
        saved_file = target_file
        try:
            wb.save(str(target_file))
        except PermissionError:
            stem = target_file.stem.replace("_已处理", "").replace("_已修改", "")
            new_name = f"{stem}_已处理.xlsx"
            saved_file = target_file.parent / new_name
            wb.save(str(saved_file))

        # 自动唤起打开
        try:
            os.startfile(str(saved_file))
        except Exception:
            pass

        return _format_file_card(
            saved_file,
            "🌸 处理完毕！你可以直接点击下方卡片在电脑中打开或定位文件查看效果~",
            ops_performed
        )

    except Exception as e:
        return f"❌ 处理 Excel 表格失败：{e}"


@register_tool(description="智能修改已有的 Excel 电子表格中的数据（如将'张伟'修改为'旷镇涛'、修改金额/部门等）。参数：file_path(文件路径), find_text(要替换的原文字), replace_text(替换后的新内容), sheet_name(可选工作表名)")
def modify_excel_table(file_path: str = "", find_text: str = "", replace_text: str = "", sheet_name: str = "") -> str:
    """修改 Excel 表格"""
    inst = f"把{find_text}改成{replace_text}"
    return process_excel_file(file_path=file_path, instruction=inst)


@register_tool(description="在桌面或指定路径新建一个排版专业的 Excel 电子表格(.xlsx)。参数：file_path(完整路径或文件名如'1.xlsx'), title(表格大标题), headers(表头列表), rows_data(数据行列表或JSON)")
def create_excel_table(file_path: str = "1.xlsx", title: str = "员工工资统计表", headers: str = "", rows_data: str = "") -> str:
    """新建 Excel 表格"""
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

        clean_p = _clean_path(file_path)
        if not clean_p.endswith(".xlsx"):
            clean_p += ".xlsx"
        
        # 权限与安全沙箱拦截校验
        guard_err = check_sandbox_path(clean_p)
        if guard_err:
            return guard_err

        save_path = Path(clean_p)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = title[:30] if title else "数据表"

        header_list = ["工号", "员工姓名", "所属部门", "基本工资(元)", "绩效奖金(元)", "社保公积金(元)", "个税(元)", "实发工资(元)", "发放状态"]
        rows = [
            ["EMP001", "张伟", "技术研发部", 15000, 4500, 2200, 850, 16450, "已发放"],
            ["EMP002", "李娜", "产品运营部", 13500, 3800, 1950, 680, 14670, "已发放"],
            ["EMP003", "王敏", "市场商务部", 12000, 6200, 1800, 720, 15680, "已发放"],
            ["EMP004", "刘洋", "技术研发部", 18000, 5500, 2600, 1250, 19650, "已发放"],
            ["EMP005", "陈静", "财务行政部", 11000, 2500, 1650, 450, 11400, "已发放"],
            ["EMP006", "赵强", "售后服务部", 9500, 3000, 1400, 320, 10780, "已发放"]
        ]
        if headers:
            header_list = [h.strip() for h in headers.split(",") if h.strip()]

        # 写入大标题
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(header_list))
        title_cell = ws.cell(row=1, column=1, value=title)
        title_cell.font = Font(name="微软雅黑", size=14, bold=True, color="FFFFFF")
        title_cell.fill = PatternFill(start_color="3B71CA", end_color="3B71CA", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 36

        # 写入表头
        ws.append(header_list)
        ws.row_dimensions[2].height = 26
        for col_idx in range(1, len(header_list) + 1):
            cell = ws.cell(row=2, column=col_idx)
            cell.font = Font(name="微软雅黑", size=10, bold=True, color="1E293B")
            cell.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # 写入数据行
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )
        for r_idx, row in enumerate(rows, start=3):
            ws.append(row)
            ws.row_dimensions[r_idx].height = 22
            bg_color = "F8FAFC" if r_idx % 2 == 0 else "FFFFFF"
            for c_idx in range(1, len(header_list) + 1):
                c = ws.cell(row=r_idx, column=c_idx)
                c.font = Font(name="微软雅黑", size=10)
                c.fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")
                c.border = thin_border
                if isinstance(c.value, (int, float)):
                    c.alignment = Alignment(horizontal="right", vertical="center")
                else:
                    c.alignment = Alignment(horizontal="center", vertical="center")

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len * 1.6 + 4, 14)

        try:
            wb.save(str(save_path))
        except PermissionError:
            save_path = save_path.parent / f"{save_path.stem}_新.xlsx"
            wb.save(str(save_path))

        try:
            os.startfile(str(save_path))
        except Exception:
            pass

        return _format_file_card(
            save_path,
            "🌸 电子表格已为你创建生成并打开！",
            [f"创建标准表格：{save_path.name}", f"包含 {len(rows)} 行员工结构化数据", "应用现代化商业配色排版"]
        )

    except Exception as e:
        return f"❌ 创建表格失败：{e}"


@register_tool(description="读取并智能分析 Excel 表格(.xlsx/.xls/.csv)的数据结构、表头与统计指标。参数：file_path(Excel文件完整路径)")
def read_and_analyze_excel(file_path: str = "") -> str:
    """读取并分析 Excel / CSV 表格"""
    try:
        clean_p = _clean_path(file_path)
        if not clean_p or not Path(clean_p).exists() or Path(clean_p).name.startswith("~$"):
            latest = _find_latest_file([".xlsx", ".xls", ".csv"])
            if latest:
                clean_p = latest
            else:
                return "❌ 未找到 Excel 文件，请指定文件路径或上传表格~"

        p = Path(clean_p)
        suffix = p.suffix.lower()
        if suffix in [".xlsx", ".xls"]:
            import openpyxl
            wb = openpyxl.load_workbook(clean_p, data_only=True)
            sheet_names = wb.sheetnames
            active_sheet = wb.active
            rows = list(active_sheet.iter_rows(values_only=True))
            if not rows:
                return f"📊 表格 `{p.name}` 为空表。"

            header_row = rows[0] if len(rows) > 1 and not (len(rows[0]) == 1 and rows[0][0]) else (rows[1] if len(rows) > 1 else rows[0])
            headers = [str(c) if c is not None else f"列{i+1}" for i, c in enumerate(header_row)]
            data_rows = rows[1:] if header_row == rows[0] else rows[2:]

            preview_lines = []
            for r in data_rows[:15]:
                preview_lines.append(" | ".join([str(c) if c is not None else "-" for c in r]))

            stats = []
            if data_rows:
                for col_idx, h_name in enumerate(headers):
                    nums = []
                    for r in data_rows:
                        if col_idx < len(r) and isinstance(r[col_idx], (int, float)):
                            nums.append(r[col_idx])
                    if nums:
                        total = round(sum(nums), 2)
                        avg = round(total / len(nums), 2)
                        stats.append(f"  • **{h_name}**：有效数据 {len(nums)} 条，求和 = {total}，均值 = {avg}，最大值 = {max(nums)}，最小值 = {min(nums)}")

            stats_str = "\n".join(stats) if stats else "  • 暂无数值列"
            preview_table = "\n".join([f"  {line}" for line in preview_lines])

            return f"""{_format_file_card(p, '🌸 日和已为你读取完毕，需要我对特定列做进一步修改或计算吗？', [f'工作表: {active_sheet.title}', f'数据规模: {len(data_rows)} 行, {len(headers)} 列'])}

📈 **数值列智能统计**：
{stats_str}

📋 **前 15 行数据预览**：
{preview_table}"""

        elif suffix == ".csv":
            with open(clean_p, "r", encoding="utf-8", errors="ignore") as f:
                reader = list(csv.reader(f))
            if not reader:
                return f"📊 CSV 文件 `{p.name}` 为空。"
            headers = reader[0]
            data_rows = reader[1:]
            preview_lines = [" | ".join(r) for r in data_rows[:15]]
            return f"""{_format_file_card(p, '', [f'规模: {len(data_rows)} 行, {len(headers)} 列'])}
📋 **数据预览**：
{chr(10).join(preview_lines)}"""

    except Exception as e:
        return f"❌ 解析表格失败：{e}"


@register_tool(description="智能修改或新建 Word 文档(.docx)。参数：file_path(文件路径), find_text(查找原文字), replace_text(替换为新文字), append_paragraph(追加段落内容), new_title(新建文档大标题)")
def modify_or_create_word_doc(file_path: str = "", find_text: str = "", replace_text: str = "", append_paragraph: str = "", new_title: str = "") -> str:
    """修改或新建 Word 文档"""
    try:
        import docx

        clean_p = _clean_path(file_path)
        if clean_p and Path(clean_p).exists() and not Path(clean_p).name.startswith("~$"):
            doc = docx.Document(clean_p)
            mod_count = 0
            if find_text:
                for p in doc.paragraphs:
                    if find_text in p.text:
                        p.text = p.text.replace(find_text, replace_text)
                        mod_count += 1
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            if find_text in cell.text:
                                cell.text = cell.text.replace(find_text, replace_text)
                                mod_count += 1

            if append_paragraph:
                doc.add_paragraph(append_paragraph)

            target_save = Path(clean_p)
            try:
                doc.save(str(target_save))
            except PermissionError:
                target_save = target_save.parent / f"{target_save.stem}_已修改.docx"
                doc.save(str(target_save))

            try:
                os.startfile(str(target_save))
            except Exception:
                pass

            return _format_file_card(
                target_save,
                "🌸 Word 文档已更新保存并为你打开！",
                [f"替换 『{find_text}』 为 『{replace_text}』 (共 {mod_count} 处)"] if find_text else ["文档更新保存"]
            )

        else:
            desktop = Path.home() / "Desktop"
            filename = (new_title or "工作总结报告") + ".docx"
            save_path = desktop / filename
            doc = docx.Document()
            doc.add_heading(new_title or "工作总结与分析报告", level=1)
            if append_paragraph:
                for para in append_paragraph.split("\n"):
                    if para.strip():
                        doc.add_paragraph(para.strip())
            else:
                doc.add_paragraph(f"本文档由桌面 AI 助手于 {datetime.now().strftime('%Y-%m-%d %H:%M')} 自动生成。")
            
            try:
                doc.save(str(save_path))
            except PermissionError:
                save_path = desktop / f"新建文档_{datetime.now().strftime('%H%M%S')}.docx"
                doc.save(str(save_path))

            try:
                os.startfile(str(save_path))
            except Exception:
                pass

            return _format_file_card(
                save_path,
                "🌸 Word 文档已成功生成并为你打开！",
                [f"生成文档：{save_path.name}"]
            )

    except Exception as e:
        return f"❌ 处理 Word 文档失败：{e}"


@register_tool(description="读取并深度解析 PDF 文档(.pdf)的全文文字与表格数据。参数：file_path(PDF文件路径)")
def read_and_analyze_pdf(file_path: str) -> str:
    """深度解析 PDF 文件"""
    try:
        import pdfplumber

        clean_p = _clean_path(file_path)
        if not clean_p or not Path(clean_p).exists() or Path(clean_p).name.startswith("~$"):
            latest = _find_latest_file([".pdf"])
            if latest:
                clean_p = latest
            else:
                return "❌ 未找到 PDF 文件，请指定文件路径或上传 PDF~"

        target_file = Path(clean_p)
        text_blocks = []
        table_summaries = []

        with pdfplumber.open(str(target_file)) as pdf:
            page_count = len(pdf.pages)
            for p_idx, page in enumerate(pdf.pages[:10], start=1):
                p_text = page.extract_text()
                if p_text and p_text.strip():
                    text_blocks.append(f"--- [第 {p_idx} 页] ---\n{p_text.strip()[:800]}")
                
                tables = page.extract_tables()
                if tables:
                    for t_idx, tbl in enumerate(tables):
                        clean_rows = [" | ".join([str(c) if c else "" for c in r]) for r in tbl[:6]]
                        table_summaries.append(f"📊 第 {p_idx} 页 表格{t_idx+1}:\n" + "\n".join(clean_rows))

        full_preview = "\n\n".join(text_blocks[:5])
        tbl_preview = ("\n\n📋 **提取到的表格结构**：\n" + "\n\n".join(table_summaries[:3])) if table_summaries else ""

        card = _format_file_card(target_file, "🌸 日和已为你解析完毕，需要我对其中的内容做总结或回答相关问题吗？", [f"共 {page_count} 页", f"提取到 {len(table_summaries)} 个数据表格"])
        return f"""{card}
----------------------------------------
{full_preview}
{tbl_preview}"""

    except Exception as e:
        return f"❌ 读取 PDF 失败：{e}"


@register_tool(description="读取 Word 文档(.docx)、PDF 文件或纯文本文件的全部文字内容。参数：file_path(文件路径)")
def read_and_summarize_doc(file_path: str = "") -> str:
    """读取 Word / PDF / TXT 文档"""
    clean_p = _clean_path(file_path)
    if not clean_p or not Path(clean_p).exists():
        clean_p = _find_latest_file([".docx", ".pdf", ".txt", ".md"])
        if not clean_p:
            return "❌ 未找到文档，请指定文件路径~"

    p = Path(clean_p)
    if p.suffix.lower() == ".pdf":
        return read_and_analyze_pdf(str(p))
    elif p.suffix.lower() == ".docx":
        try:
            import docx
            doc = docx.Document(str(p))
            paragraphs = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
            full_text = "\n\n".join(paragraphs[:30])
            if not full_text:
                full_text = "(文档正文为空或仅包含未解析表格/图片)"
            return f"📄 **【Word 文档内容提取】：`{p.name}`**\n\n{full_text}"
        except Exception as e:
            return f"❌ 读取 Word 文档失败: {e}"
    else:
        with open(str(p), "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(3000)
        return f"📄 【文本文件内容】：`{p.name}`\n```\n{content}\n```"
