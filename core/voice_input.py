"""
语音输入 - faster-whisper GPU 加速语音识别
点击小人或按快捷键触发录音
"""
import asyncio
import tempfile
import wave
import os
from typing import Callable, Optional
import pyaudio
import struct


class VoiceInput:
    """基于 faster-whisper 的本地语音识别（GPU加速）"""

    def __init__(self, config: dict):
        self.config = config
        self.vc = config["voice"]
        self.model = None
        self._recording = False
        self._model_loaded = False

        # 音频参数
        self.SAMPLE_RATE = 16000
        self.CHANNELS = 1
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16

    def _load_model(self):
        """懒加载 Whisper 模型（首次使用时才加载，节省内存）"""
        if self._model_loaded:
            return
        try:
            from faster_whisper import WhisperModel
            model_size = self.vc.get("whisper_model", "small")
            device = self.vc.get("whisper_device", "cuda")
            compute_type = self.vc.get("whisper_compute_type", "float16")
            cache_dir = self.vc.get("model_cache_dir", "E:/Study_Cache/model/whisper")

            print(f"🎤 加载 Whisper {model_size} 模型 (设备: {device})...")
            self.model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=cache_dir
            )
            self._model_loaded = True
            print("✅ Whisper 模型加载完成")
        except Exception as e:
            print(f"⚠️ Whisper 加载失败，将禁用语音功能: {e}")
            self.model = None

    def is_available(self) -> bool:
        return self.vc.get("enabled", True)

    async def record_and_transcribe(
        self,
        duration_seconds: int = 10,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None
    ) -> str:
        """录音并识别为文字，支持静默自动停止"""
        if not self._model_loaded:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._load_model)

        if not self.model:
            return ""

        if on_start:
            on_start()

        self._recording = True
        audio_data = await asyncio.get_event_loop().run_in_executor(
            None, self._record_audio, duration_seconds
        )
        if on_stop:
            on_stop()

        if not audio_data:
            return ""

        text = await asyncio.get_event_loop().run_in_executor(
            None, self._transcribe, audio_data
        )
        return text.strip()

    def _record_audio(self, max_seconds: int = 10) -> Optional[bytes]:
        """录制音频，检测静默自动停止"""
        self._recording = True
        pa = pyaudio.PyAudio()
        frames = []

        try:
            stream = pa.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            print("🎙️ 开始录音...")
            silence_count = 0
            SILENCE_THRESHOLD = 500
            SILENCE_FRAMES = int(self.SAMPLE_RATE / self.CHUNK * 2)

            for _ in range(int(self.SAMPLE_RATE / self.CHUNK * max_seconds)):
                if not self._recording:
                    break
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                frames.append(data)
                samples = struct.unpack(f"{self.CHUNK}h", data)
                max_sample = max(abs(s) for s in samples)
                if max_sample < SILENCE_THRESHOLD:
                    silence_count += 1
                    if silence_count > SILENCE_FRAMES and len(frames) > SILENCE_FRAMES:
                        break
                else:
                    silence_count = 0
            stream.stop_stream()
            stream.close()
        finally:
            pa.terminate()

        print("⏹️ 录音结束")
        return b"".join(frames) if frames else None

    def _transcribe(self, audio_data: bytes) -> str:
        """将音频数据转写为文字"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(audio_data)
        try:
            segments, _ = self.model.transcribe(
                tmp_path,
                language="zh",
                beam_size=5,
                vad_filter=True
            )
            text = "".join(seg.text for seg in segments)
            print(f"📝 识别结果: {text}")
            return text
        except Exception as e:
            print(f"转写失败: {e}")
            return ""
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def stop_recording(self):
        self._recording = False

    def reload_config(self, config: dict):
        self.config = config
        self.vc = config["voice"]
        self.model = None
        self._model_loaded = False
