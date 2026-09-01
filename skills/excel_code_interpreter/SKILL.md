---
name: excel_code_interpreter
description: "AI 动态 Excel 电子表格代码解释器技能。支持对 Excel (.xlsx/.xls/.csv) 执行任意复杂的数据分析、多列合并、条件格式化、公式计算、图表绘制、行列增删与格式排版。"
tools:
  - execute_excel_code
  - read_and_analyze_excel
  - create_excel_table
---

# Excel Code Interpreter Skill (智能电子表格代码解释器)

## 技能概述
当用户对 Excel 电子表格提出任意复杂的数据处理、修改、统计、合并或排版需求时，AI 代理不需要预置写死逻辑，而是通过动态生成标准的 `openpyxl` Python 处理代码，传递给 `execute_excel_code` 工具在安全沙箱中执行。

## 执行环境与内置对象
执行代码时，系统已自动预加载并提供以下变量：
- `wb`: 当前加载的 `openpyxl.Workbook` 实例
- `ws`: 当前活跃的 `openpyxl.worksheet.worksheet.Worksheet` 实例
- `openpyxl`: openpyxl 顶级模块
- `Font`, `Alignment`, `PatternFill`, `Border`, `Side`: 常用样式类
- `target_file`: 原始文件 Path 对象

## 常用操作范式

### 1. 查找替换单元格内容
```python
for row in ws.iter_rows():
    for cell in row:
        if cell.value and "旧文本" in str(cell.value):
            cell.value = str(cell.value).replace("旧文本", "新文本")
```

### 2. 合并指定两列并计算数值求和
```python
# 合并第 4 列与第 5 列
ws.merge_cells(start_row=2, start_column=4, end_row=2, end_column=5)
for r in range(3, ws.max_row + 1):
    v1 = ws.cell(row=r, column=4).value or 0
    v2 = ws.cell(row=r, column=5).value or 0
    ws.cell(row=r, column=4, value=float(v1) + float(v2))
    ws.cell(row=r, column=5, value="")
    ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=5)
```

### 3. 数据按某列排序
```python
data = []
for r in range(3, ws.max_row + 1):
    data.append([ws.cell(row=r, column=c).value for c in range(1, ws.max_column + 1)])
# 按第 6 列降序
data.sort(key=lambda x: float(x[5]) if isinstance(x[5], (int, float)) else 0, reverse=True)
for r_idx, row_vals in enumerate(data, start=3):
    for c_idx, val in enumerate(row_vals, start=1):
        ws.cell(row=r_idx, column=c_idx, value=val)
```
