# -*- coding: utf-8 -*-
"""
AI 核心引擎 - 支持本地 Ollama 模型扫描、外部云端 API (DeepSeek/OpenAI等)、工具调用与流式回复
"""
import json
import re
import os
import inspect
import asyncio
from typing import Optional, AsyncGenerator, List, Dict
from pathlib import Path
import httpx


def list_ollama_models(base_url: str = "http://localhost:11434") -> List[str]:
    """快速扫描本地 Ollama 已安装的模型列表"""
    try:
        url = base_url.rstrip("/") + "/api/tags"
        resp = httpx.get(url, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("models", [])
            names = [m.get("name") for m in models if m.get("name")]
            if names:
                return names
    except Exception as e:
        print(f"[Ollama Scan] Failed to scan {base_url}: {e}")
    return ["deepseek-r1:14b", "deepseek-r1:7b", "qwen2.5:7b", "llama3.1:8b"]


class AIEngine:
    """现代 AI 引擎，支持本地 Ollama 及外部 OpenAI 兼容服务"""

    SYSTEM_PROMPT_TEMPLATE = """你是一个可爱的桌面智能助理，名字叫“{name}”。
你拥有亲切、幽默、体贴的性格，乐于帮助主人解答问题、处理日常事务并提供情绪陪伴。

【需要工具调用时的规则】：
如果主人需要你执行本地文件写入、读取、打开程序、截图等操作，请按以下格式输出工具调用指令：
```tool_call
{{"tool": "工具函数名", "args": {{"参数1": "值1", "参数2": "值2"}}}}
```
系统会真实执行并将结果返回给你。日常闲聊与问答请直接用温暖自然的语气回答。"""

    def __init__(self, config: dict):
        self.config = config
        self.provider = config.get("ai", {}).get("provider", "ollama")
        self.pet_name = config.get("behavior", {}).get("pet_name", "桃濑日和")
        self.system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(name=self.pet_name)
        self.conversation_history: List[Dict[str, str]] = []
        self.memory = None
        self.emotion = None
        self.plugins = None

    def set_dependencies(self, memory, emotion, plugins):
        self.memory = memory
        self.emotion = emotion
        self.plugins = plugins

    def reload_config(self, config: dict):
        self.config = config
        self.provider = config.get("ai", {}).get("provider", "ollama")
        self.pet_name = config.get("behavior", {}).get("pet_name", "桃濑日和")
        self.system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(name=self.pet_name)

    def set_conversation_history(self, history: List[Dict[str, str]]):
        """设置当前会话的上下文历史"""
        self.conversation_history = history[-20:]

    def clear_history(self):
        """清空当前会话在内存中的上下文"""
        self.conversation_history = []

    def _try_direct_tool_intent(self, message: str) -> Optional[str]:
        """对直接文件操作提供极速直达支持"""
        msg = message.strip()
        path_match = re.search(r'(?:file:///)?([a-zA-Z]:[\\/][^,\n\r"\'<>|]+(?:\.[a-zA-Z0-9]+)?)', msg)
        if not path_match:
            desktop_match = re.search(r'桌面[上的]*([^\s,，]+\.[a-zA-Z0-9]+)', msg)
            if desktop_match:
                desktop_path = str(Path.home() / "Desktop" / desktop_match.group(1))
                path_match = re.search(r'(.*)', desktop_path)

        if path_match:
            file_path = path_match.group(1).replace('/', '\\')
            if any(k in msg for k in ["写入", "写进", "写到", "输入", "保存到", "新建并写"]):
                content = ""
                content_match = re.search(r'(?:写入|写进|写到|内容为|内容是|写入内容)[:：\s]*(?:["\']?)(.+?)(?:["\']?)(?:几个单词|这几个单词|这段话|内容|到文件|$)', msg)
                if content_match:
                    content = content_match.group(1).strip().strip('"').strip("'")
                else:
                    words = re.findall(r'[a-zA-Z0-9_]+', msg)
                    if words:
                        content = words[-1]

                if not content:
                    content = "Hello World"

                try:
                    p = Path(file_path)
                    p.parent.mkdir(parents=True, exist_ok=True)
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(content)
                    return f"✨ 搞定啦！我已经帮你将以下内容真实写入到了文件中：\n📁 **路径**：`{file_path}`\n📝 **写入内容**：\n```\n{content}\n```\n你可以打开桌面文件确认哦~ 🌸"
                except Exception as e:
                    return f"写入文件时出错啦：{str(e)}"

            elif any(k in msg for k in ["读取", "查看", "分析", "看下内容", "读一下"]):
                try:
                    p = Path(file_path)
                    if p.exists():
                        text = p.read_text(encoding="utf-8", errors="ignore")[:2000]
                        return f"📄 文件 `{p.name}` 的内容如下：\n```\n{text}\n```"
                except Exception as e:
                    return f"读取文件失败：{str(e)}"

        return None

    async def chat_stream(self, message: str, session_id: Optional[int] = None) -> AsyncGenerator[str, None]:
        """流式对话主入口"""
        if not message.strip():
            yield "主人，你还没跟我说话呢~ 🌸"
            return

        # 尝试快速意图识别
        direct_result = self._try_direct_tool_intent(message)
        if direct_result:
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": direct_result})
            if self.memory and session_id:
                try:
                    self.memory.add_message(session_id, "user", message)
                    self.memory.add_message(session_id, "assistant", direct_result)
                except Exception:
                    pass
            for char in direct_result:
                yield char
            return

        tool_desc = ""
        if self.plugins:
            tools = self.plugins.get_tool_descriptions()
            if tools:
                tool_desc = "\n\n【可用工具列表】\n" + tools

        full_system = self.system_prompt + tool_desc
        self.conversation_history.append({"role": "user", "content": message})
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        raw_reply = ""
        try:
            if self.provider == "custom" or self.provider == "openai":
                async for chunk in self._stream_openai_compatible(full_system):
                    raw_reply += chunk
            else:
                async for chunk in self._stream_ollama(full_system):
                    raw_reply += chunk
        except Exception as e:
            raw_reply = f"⚠️ 对话异常: {str(e)}"

        # 检查工具调用
        tool_call_match = re.search(r'```tool_call\s*(\{.*?\})\s*```', raw_reply, re.DOTALL)
        if tool_call_match:
            try:
                call_data = json.loads(tool_call_match.group(1))
                tool_name = call_data.get("tool")
                args = call_data.get("args", {})
                tool_result = self._execute_tool(tool_name, args)
                
                follow_up = f"【系统执行工具 {tool_name} 的真实结果】：\n{tool_result}\n请根据以上执行结果向主人汇报。"
                self.conversation_history.append({"role": "assistant", "content": raw_reply})
                self.conversation_history.append({"role": "user", "content": follow_up})
                
                final_reply = ""
                if self.provider == "custom" or self.provider == "openai":
                    async for chunk in self._stream_openai_compatible(full_system):
                        final_reply += chunk
                else:
                    async for chunk in self._stream_ollama(full_system):
                        final_reply += chunk

                cleaned_final = self._clean_text(final_reply)
                for char in cleaned_final:
                    yield char

                self.conversation_history.append({"role": "assistant", "content": cleaned_final})
                if self.memory and session_id:
                    self.memory.add_message(session_id, "user", message)
                    self.memory.add_message(session_id, "assistant", cleaned_final)
                return
            except Exception as te:
                print(f"[Tool Exec Error]: {te}")

        cleaned = self._clean_text(raw_reply)
        for char in cleaned:
            yield char

        self.conversation_history.append({"role": "assistant", "content": cleaned})
        if self.memory and session_id:
            try:
                self.memory.add_message(session_id, "user", message)
                self.memory.add_message(session_id, "assistant", cleaned)
            except Exception:
                pass

        if self.emotion:
            try:
                self.emotion.update_from_reply(cleaned)
            except Exception:
                pass

    def _clean_text(self, text: str) -> str:
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        cleaned = re.sub(r'<think>.*', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'```tool_call.*?```', '', cleaned, flags=re.DOTALL)
        return cleaned.strip()

    def _execute_tool(self, tool_name: str, args: dict) -> str:
        from core.plugin_manager import _TOOL_REGISTRY
        if tool_name not in _TOOL_REGISTRY:
            return f"未找到工具：{tool_name}"
        func = _TOOL_REGISTRY[tool_name]
        try:
            sig = inspect.signature(func)
            kwargs = {k: v for k, v in args.items() if k in sig.parameters}
            return str(func(**kwargs))
        except Exception as e:
            return f"执行失败：{e}"

    async def _stream_ollama(self, system_prompt: str) -> AsyncGenerator[str, None]:
        """流式请求本地 Ollama"""
        cfg = self.config.get("ai", {}).get("ollama", {})
        base_url = cfg.get("base_url", "http://localhost:11434").rstrip("/")
        model = cfg.get("chat_model", "deepseek-r1:14b")

        messages = [{"role": "system", "content": system_prompt}] + self.conversation_history

        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": 0.6,
                        "num_predict": 800
                    }
                }
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            chunk = data.get("message", {}).get("content", "")
                            if chunk:
                                yield chunk
                            if data.get("done", False):
                                break
                        except Exception:
                            continue

    async def _stream_openai_compatible(self, system_prompt: str) -> AsyncGenerator[str, None]:
        """流式请求 OpenAI 兼容接口（如 DeepSeek 官方 API / SiliconFlow 等）"""
        cfg = self.config.get("ai", {}).get("custom", {})
        base_url = cfg.get("api_base", "https://api.deepseek.com/v1").rstrip("/")
        api_key = cfg.get("api_key", "")
        model = cfg.get("chat_model", "deepseek-chat")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        messages = [{"role": "system", "content": system_prompt}] + self.conversation_history

        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "temperature": 0.6
                }
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        raw_json = line[6:].strip()
                        if raw_json == "[DONE]":
                            break
                        try:
                            data = json.loads(raw_json)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except Exception:
                            continue
