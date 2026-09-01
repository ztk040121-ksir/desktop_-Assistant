"""
语音输出 - Edge-TTS 异步语音合成 (纯非阻塞、带超时保护)
"""
import asyncio
import tempfile
import os
import threading
from typing import Optional


VOICE_OPTIONS = {
    "晓晓-温柔": "zh-CN-XiaoxiaoNeural",
    "晓伊-活泼": "zh-CN-XiaoyiNeural",
    "云扬-男声": "zh-CN-YunyangNeural",
    "云希-温和": "zh-CN-YunxiNeural",
    "晓臻-清晰": "zh-CN-XiaozhenNeural",
}


class VoiceOutput:
    """基于 edge-tts 的极速异步语音合成"""

    def __init__(self, config: dict):
        self.config = config
        self.vc = config.get("voice", {})
        self._lock = threading.Lock()

    def get_voice_name(self) -> str:
        return self.vc.get("tts_voice", "zh-CN-XiaoxiaoNeural")

    def speak_nowait(self, text: str):
        """完全独立的后台守护线程播放，绝不阻塞任何主线程逻辑"""
        if not text.strip() or not self.config.get("sound_enabled", True) or not self.vc.get("enabled", True):
            return

        # 限制语音长度在 150 字以内，避免长文本朗读过久
        short_text = text[:150]
        # 去掉 Markdown 格式符号和表情符号
        import re
        clean_text = re.sub(r'[*_#`~>|]', '', short_text)
        clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_text).strip()
        if not clean_text:
            return

        t = threading.Thread(target=self._generate_and_play, args=(clean_text,), daemon=True)
        t.start()

    def _generate_and_play(self, text: str):
        if not self._lock.acquire(blocking=False):
            return  # 正在说话时跳过，避免声音重叠

        tmp_path = None
        try:
            import edge_tts
            voice = self.get_voice_name()
            rate = self.vc.get("tts_rate", "+0%")
            volume = self.vc.get("tts_volume", "+0%")

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name

            # 运行异步生成，5秒超时
            async def _gen():
                comm = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
                await comm.save(tmp_path)

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(asyncio.wait_for(_gen(), timeout=4.0))
            finally:
                loop.close()

            # 播放 MP3 (使用 Windows 原生 WMPlayer.OCX COM 播放器)
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                import subprocess
                ps_script = f"""
                $wmp = New-Object -ComObject WMPlayer.OCX
                $wmp.settings.volume = 100
                $wmp.URL = '{tmp_path}'
                $wmp.controls.play()
                $waited = 0
                while ($wmp.playState -eq 0 -or $wmp.playState -eq 1 -or $wmp.playState -eq 2) {{
                    if ($waited -gt 20) {{ break }}
                    Start-Sleep -Milliseconds 100
                    $waited++
                }}
                while ($wmp.playState -eq 3 -or $wmp.playState -eq 6 -or $wmp.playState -eq 7 -or $wmp.playState -eq 9) {{
                    Start-Sleep -Milliseconds 100
                }}
                """
                subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                    capture_output=True,
                    timeout=15
                )
        except Exception as e:
            print(f"[VoiceOutput Error] {e}")
        finally:
            self._lock.release()
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    async def speak(self, text: str):
        self.speak_nowait(text)

    def reload_config(self, config: dict):
        self.config = config
        self.vc = config.get("voice", {})
