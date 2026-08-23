"""
用生成的图片制作角色 GIF 动画（更好看的版本）
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from PIL import Image, ImageFilter, ImageEnhance
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "characters" / "default"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 生成的图片路径
CHAR_IMG_PATH = r"C:\Users\31665\.gemini\antigravity-ide\brain\ad0fc5e7-a6a1-49d7-b07f-6f8ee4b497fb\pet_char_idle_1787502355161.png"


def make_animated_frames(base_img: Image.Image, anim_type: str) -> list:
    """从基础图片生成动画帧"""
    frames = []
    w, h = base_img.size

    if anim_type == "idle":
        # 轻微上下浮动
        offsets = [0, -3, -5, -3, 0, 2, 0]
        for off in offsets:
            frame = Image.new("RGBA", (w, h + 10), (0, 0, 0, 0))
            frame.paste(base_img, (0, off + 5))
            frames.append(frame)

    elif anim_type == "happy":
        # 较大幅度跳动 + 轻微缩放
        offsets = [0, -8, -14, -8, 0, -4, 0]
        for off in offsets:
            frame = Image.new("RGBA", (w, h + 20), (0, 0, 0, 0))
            frame.paste(base_img, (0, off + 10))
            frames.append(frame)

    elif anim_type == "sleepy":
        # 缓慢下沉 + 轻微变暗
        for i in range(6):
            en = ImageEnhance.Brightness(base_img)
            factor = 0.85 + 0.05 * abs(3 - i) / 3
            darkened = en.enhance(factor)
            frame = Image.new("RGBA", (w, h + 10), (0, 0, 0, 0))
            off = i % 2
            frame.paste(darkened, (0, off + 5))
            frames.append(frame)

    elif anim_type == "talking":
        # 轻微左右摇摆
        for i in range(6):
            off_x = [0, 1, 2, 1, 0, -1][i]
            off_y = [0, -2, 0, 2, 0, -1][i]
            frame = Image.new("RGBA", (w + 4, h + 10), (0, 0, 0, 0))
            frame.paste(base_img, (off_x + 2, off_y + 5))
            frames.append(frame)

    elif anim_type == "working":
        # 小幅专注点头
        offsets = [0, -2, -2, 0, 0, -1]
        for off in offsets:
            frame = Image.new("RGBA", (w, h + 10), (0, 0, 0, 0))
            frame.paste(base_img, (0, off + 5))
            frames.append(frame)

    else:
        # 默认：静止
        frame = Image.new("RGBA", (w, h + 10), (0, 0, 0, 0))
        frame.paste(base_img, (0, 5))
        frames = [frame] * 4

    return frames


def save_gif(frames: list, name: str, duration: int = 120):
    out_path = OUTPUT_DIR / f"{name}.gif"
    if frames:
        # 统一大小
        target_size = (120, 160)
        resized = []
        for f in frames:
            r = f.resize(target_size, Image.LANCZOS)
            resized.append(r.convert("RGBA"))

        resized[0].save(
            out_path,
            save_all=True,
            append_images=resized[1:],
            loop=0,
            duration=duration,
            disposal=2
        )
    print(f"OK: {name}.gif")


if __name__ == "__main__":
    # 尝试加载生成的图片
    import os
    if os.path.exists(CHAR_IMG_PATH):
        print("Loading generated character image...")
        base = Image.open(CHAR_IMG_PATH).convert("RGBA")
        # 调整到合适的尺寸
        base = base.resize((110, 150), Image.LANCZOS)

        for anim_name, dur in [
            ("idle", 150),
            ("talking", 100),
            ("happy", 80),
            ("sleepy", 250),
            ("working", 200),
            ("shy", 120),
            ("sad", 200),
        ]:
            frames = make_animated_frames(base, anim_name)
            save_gif(frames, anim_name, dur)

        print("\nDone! Character animations created from generated image.")
    else:
        print(f"Image not found: {CHAR_IMG_PATH}")
        print("Using fallback programmatic character...")
        # fallback: 还是用之前的代码生成
        exec(open("generate_character.py").read())
