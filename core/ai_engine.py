"""
AI 引擎 - 支持真实工具调用与智能意图直连执行
"""
import json
import re
import os
import inspect
import asyncio
from typing import Optional, AsyncGenerator
from pathlib import Path
import httpx


class AIEngine:
    """多后端 AI 引擎与真实工具执行中心"""

    SYSTEM_PROMPT_TEMPLATE = """你是一个可爱的桌面AI桌宠助手，名字叫「{name}」。
你居住在用户的桌面上，性格活泼软萌、聪明体贴，有灵动的情感和丰富的知识。

【重要工具调用规则】：
如果你需要执行操作（例如写入文件、读取文件、整理桌面、打开程序、截图等），请输出工具调用指令：
```tool_call
{{"tool": "工具函数名", "args": {{"参数1": "值1", "参数2": "值2"}}}}
```
系统会真实执行并在你的电脑上完成操作。日常聊天问答直接亲切回答即可。"""

    def __init__(self, config: dict):
        self.config = config
        self.provider = config.get("ai", {}).get("provider", "ollama")
        self.pet_name = config.get("behavior", {}).get("pet_name", "小桃")
        self.system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(name=self.pet_name)
        self.conversation_history = []
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
        self.pet_name = config.get("behavior", {}).get("pet_name", "小桃")
        self.system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(name=self.pet_name)

    def _try_direct_tool_intent(self, message: str) -> Optional[str]:
        """对于极其明确的文件写入/读取/截图等操作，提供零延迟高可靠直连真实执行"""
        msg = message.strip()
        
        # 提取路径 (支持 file:/// 或 C:\... 或 E:\...)
        path_match = re.search(r'(?:file:///)?([a-zA-Z]:[\\/][^,\n\r"\'<>|]+(?:\.[a-zA-Z0-9]+)?)', msg)
        if not path_match:
            desktop_match = re.search(r'桌面[上的]*([^\s,，]+\.[a-zA-Z0-9]+)', msg)
            if desktop_match:
                desktop_path = str(Path.home() / "Desktop" / desktop_match.group(1))
                path_match = re.search(r'(.*)', desktop_path)

        if path_match:
            file_path = path_match.group(1).replace('/', '\\')
            
            # 判断写入意图
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

    async def chat_stream(self, message: str) -> AsyncGenerator[str, None]:
        """流式对话并自动执行真实工具"""
        if not message.strip():
            yield "主人，你还没跟我说话呢~ ฅ'ω'ฅ"
            return

        direct_result = self._try_direct_tool_intent(message)
        if direct_result:
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": direct_result})
            if self.memory:
                try:
                    await self.memory.save_conversation(message, direct_result)
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
            if self.provider == "ollama":
                async for chunk in self._stream_ollama(full_system):
                    raw_reply += chunk
            else:
                raw_reply = await self.chat(message)
        except Exception as e:
            raw_reply = f"⚠️ 对话异常: {str(e)}"

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
                async for chunk in self._stream_ollama(full_system):
                    final_reply += chunk
                cleaned_final = self._clean_text(final_reply)
                for char in cleaned_final:
                    yield char
                self.conversation_history.append({"role": "assistant", "content": cleaned_final})
                if self.memory:
                    await self.memory.save_conversation(message, cleaned_final)
                return
            except Exception as te:
                print(f"[Tool Exec Error]: {te}")

        cleaned = self._clean_text(raw_reply)
        for char in cleaned:
            yield char

        self.conversation_history.append({"role": "assistant", "content": cleaned})
        if self.memory:
            try:
                await self.memory.save_conversation(message, cleaned)
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
        cfg = self.config.get("ai", {}).get("ollama", {})
        base_url = cfg.get("base_url", "http://localhost:11434")
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
                        "num_predict": 500
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

    async def chat(self, message: str) -> str:
        chunks = []
        async for chunk in self.chat_stream(message):
            chunks.append(chunk)
        return "".join(chunks)

    def clear_history(self):
        self.conversation_history = []
