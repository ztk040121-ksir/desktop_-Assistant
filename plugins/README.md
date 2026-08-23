# 🔌 插件开发指南

## 快速开始

在 `plugins/` 目录下新建一个 `.py` 文件，使用 `@register_tool` 装饰器注册工具：

```python
# plugins/my_tools.py
from core.plugin_manager import register_tool

@register_tool(description="打开我的 CRM 系统")
def open_crm() -> str:
    import subprocess
    subprocess.Popen("C:/Apps/MyCRM.exe")
    return "✅ CRM 已打开"

@register_tool(description="发送钉钉消息给指定人员，参数：人名、消息内容")
def send_dingtalk(person: str, message: str) -> str:
    # 你的钉钉 API 代码
    return f"✅ 已向 {person} 发送：{message}"
```

## 重载插件

保存文件后，在管理中心 → 插件管理 → 点击「重载所有插件」

## 使用工具

注册后，直接对小人说话即可调用：
- "帮我打开 CRM"
- "发钉钉给张三，说我今天请假"

## 注意事项

- 函数参数必须有类型注解（str、int、bool）
- description 要清晰描述功能，AI 根据它判断何时调用
- 返回值用中文描述执行结果
- 可以是同步函数或 async 异步函数，都支持

## 内置插件说明

| 插件文件 | 功能 |
|---------|------|
| `computer_control.py` | 截图、打开程序、搜索文件、鼠标操作 |
| `file_tools.py` | 读取Word/Excel/PDF、整理文件夹 |
| `wechat_tools.py` | 微信消息读取与发送 |
