"""
生成默认小人占位 GIF 动画
运行此脚本可生成临时动画，之后可换成真实的 Live2D / 精灵图
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw
import os
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "characters" / "default"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def make_cat_frame(expression: str, color: tuple, offset_y: int = 0) -> Image.Image:
    """生成一帧简单的猫娘图像"""
    img = Image.new("RGBA", (120, 130), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 身体
    draw.ellipse([35, 55 + offset_y, 85, 120 + offset_y], fill=color)
    # 头部
    draw.ellipse([30, 15 + offset_y, 90, 65 + offset_y], fill=color)
    # 猫耳
    draw.polygon([(35, 20 + offset_y), (25, 5 + offset_y), (50, 18 + offset_y)], fill=color)
    draw.polygon([(85, 20 + offset_y), (95, 5 + offset_y), (70, 18 + offset_y)], fill=color)
    # 眼睛
    eye_color = (50, 50, 150)
    draw.ellipse([42, 32 + offset_y, 54, 44 + offset_y], fill=eye_color)
    draw.ellipse([66, 32 + offset_y, 78, 44 + offset_y], fill=eye_color)
    # 表情嘴巴
    if expression == "happy":
        draw.arc([52, 46 + offset_y, 68, 56 + offset_y], 0, 180, fill=(100, 60, 60), width=2)
    elif expression == "sleepy":
        draw.line([52, 52 + offset_y, 68, 52 + offset_y], fill=(100, 60, 60), width=2)
        # 半闭眼
        draw.line([42, 38 + offset_y, 54, 38 + offset_y], fill=(50, 50, 150), width=3)
        draw.line([66, 38 + offset_y, 78, 38 + offset_y], fill=(50, 50, 150), width=3)
    else:
        draw.arc([52, 46 + offset_y, 68, 56 + offset_y], 0, 180, fill=(100, 60, 60), width=2)

    # 腮红
    draw.ellipse([36, 44 + offset_y, 48, 52 + offset_y], fill=(255, 182, 193, 120))
    draw.ellipse([72, 44 + offset_y, 84, 52 + offset_y], fill=(255, 182, 193, 120))
    return img


def make_gif(name: str, expressions: list, colors: list, offsets: list):
    frames = []
    for expr, color, offset in zip(expressions, colors, offsets):
        frames.append(make_cat_frame(expr, color, offset))
    out_path = OUTPUT_DIR / f"{name}.gif"
    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=400,
        disposal=2
    )
    print(f"OK: {out_path}")


if __name__ == "__main__":
    pink = (255, 182, 193)
    light_pink = (255, 200, 210)

    # 待机动画：轻微上下浮动
    make_gif("idle",
             ["idle", "idle", "idle", "idle"],
             [pink, pink, light_pink, light_pink],
             [0, -2, -2, 0])

    # 说话动画：嘴巴变化
    make_gif("talking",
             ["happy", "idle", "happy", "idle"],
             [pink, light_pink, pink, light_pink],
             [0, 0, -1, -1])

    # 开心动画：跳动
    make_gif("happy",
             ["happy", "happy", "happy", "happy"],
             [pink, (255, 150, 180), pink, (255, 150, 180)],
             [0, -5, -8, -5])

    # 困倦动画：下沉
    make_gif("sleepy",
             ["sleepy", "sleepy", "sleepy", "sleepy"],
             [(200, 160, 170), (190, 150, 165), (200, 160, 170), (195, 155, 168)],
             [3, 5, 3, 4])

    # 工作动画：同 idle
    make_gif("working",
             ["idle", "idle", "idle", "idle"],
             [(170, 200, 255), (160, 190, 245), (170, 200, 255), (165, 195, 250)],
             [0, -1, -1, 0])

    # 害羞
    make_gif("shy",
             ["happy", "happy", "happy", "happy"],
             [(255, 160, 180), (255, 140, 170), (255, 160, 180), (255, 150, 175)],
             [0, 0, -1, -1])

    # 委屈
    make_gif("sad",
             ["sleepy", "sleepy", "sleepy", "sleepy"],
             [(180, 170, 200), (170, 160, 195), (180, 170, 200), (175, 165, 198)],
             [2, 3, 2, 3])

    print("\n完成！所有动画帧已生成，位于 characters/default/ 目录")
    print("提示：可以将此目录中的 GIF 文件替换为你喜欢的角色动画")
