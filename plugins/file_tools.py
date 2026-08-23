"""
文件处理工具集 - 读取、写入、分析、整理各类文件
支持 TXT、Word、Excel、PDF 等格式的真实读写
"""
import os
import shutil
import re
from pathlib import Path
from datetime import datetime
from core.plugin_manager import register_tool


def _clean_path(path_str: str) -> str:
    """清理路径，支持 file:/// 格式与各种 Windows 路径"""
    p = path_str.strip().strip('"').strip("'")
    if p.startswith("file:///"):
        p = p[8:]
    elif p.startswith("file://"):
        p = p[7:]
    return os.path.normpath(p)


@register_tool(description="将指定的文本内容写入到本地文件中（支持覆盖或新建）。参数：file_path (文件完整路径), content (要写入的文字内容)")
def write_text_file(file_path: str, content: str) -> str:
    """真实写入文件"""
    try:
        clean_p = _clean_path(file_path)
        p = Path(clean_p)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ 成功将内容写入文件：{clean_p} (共 {len(content)} 字符)"
    except Exception as e:
        return f"❌ 写入文件失败：{str(e)}"


@register_tool(description="向已有文件末尾追加写入内容。参数：file_path (文件路径), content (要追加的文字)")
def append_text_file(file_path: str, content: str) -> str:
    """追加写入文件"""
    try:
        clean_p = _clean_path(file_path)
        p = Path(clean_p)
        with open(p, "a", encoding="utf-8") as f:
            f.write("\n" + content)
        return f"✅ 已成功向文件追加内容：{clean_p}"
    except Exception as e:
        return f"❌ 追加失败：{str(e)}"


@register_tool(description="读取纯文本文件(.txt/.md/.log/.py等)的内容。参数：file_path (文件路径)")
def read_text_file(file_path: str) -> str:
    try:
        clean_p = _clean_path(file_path)
        with open(clean_p, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(5000)
        return f"📄 文件内容：\n{content}"
    except Exception as e:
        return f"读取失败：{str(e)}"


@register_tool(description="读取 Word 文档(.docx)的文字内容。参数：file_path (文件路径)")
def read_word(file_path: str) -> str:
    try:
        import docx
        clean_p = _clean_path(file_path)
        doc = docx.Document(clean_p)
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        if len(text) > 3000:
            text = text[:3000] + "\n...(内容过长，已截断)"
        return f"📄 Word 文档内容：\n{text}" if text else "文档内容为空"
    except Exception as e:
        return f"读取失败：{e}"


@register_tool(description="按文件类型自动整理文件夹。参数：folder_path (目标文件夹路径)")
def organize_folder(folder_path: str) -> str:
    try:
        folder = Path(_clean_path(folder_path))
        if not folder.exists():
            return f"文件夹不存在：{folder_path}"

        categories = {
            "图片": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
            "文档": [".doc", ".docx", ".pdf", ".txt", ".md", ".ppt", ".pptx"],
            "表格": [".xls", ".xlsx", ".csv"],
            "压缩包": [".zip", ".rar", ".7z", ".tar", ".gz"],
        }
        moved = 0
        for file in folder.iterdir():
            if not file.is_file():
                continue
            suffix = file.suffix.lower()
            for cat, exts in categories.items():
                if suffix in exts:
                    dest_dir = folder / cat
                    dest_dir.mkdir(exist_ok=True)
                    dest = dest_dir / file.name
                    if not dest.exists():
                        shutil.move(str(file), str(dest))
                        moved += 1
                    break
        return f"✅ 整理完成！共移动了 {moved} 个文件到对应分类文件夹"
    except Exception as e:
        return f"整理失败：{e}"
