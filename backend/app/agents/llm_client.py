"""Qwen2.5 / OpenAI 兼容 LLM 客户端 — 从 carModel agent/llm_client.py 迁移（TD-01）。

零强依赖：仅用标准库 urllib 调用 OpenAI 兼容 /v1/chat/completions。
支持两种模式：
  - compose 模式（默认）：规则选工具 + 本客户端仅做"忠实转述"
  - fc 模式：把 TOOL_SCHEMAS 交给模型做 function-calling 选工具

环境变量：
  CARSOUL_LLM_BASE_URL  兼容端点 base
  CARSOUL_LLM_API_KEY   访问密钥（本地 vLLM 可为任意非空串）
  CARSOUL_LLM_MODEL     模型名（为空则用端点默认）
  CARSOUL_LLM_MODE      compose（默认）| fc

客户端只负责"传输 + 解析"，不替模型决定是否编造；
幻觉围栏全部放在 system prompt 与离线评估。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional


class LLMClientError(RuntimeError):
    """LLM 端点不可用或调用失败。"""


@dataclass
class ChatMessage:
    role: str  # system / user / assistant / tool
    content: Optional[str] = None
    tool_calls: list = field(default_factory=list)
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


def _msg_to_dict(m: ChatMessage) -> dict:
    d: dict[str, Any] = {"role": m.role}
    if m.content is not None:
        d["content"] = m.content
    if m.tool_calls:
        d["tool_calls"] = m.tool_calls
    if m.name:
        d["name"] = m.name
    if m.tool_call_id:
        d["tool_call_id"] = m.tool_call_id
    return d


class LLMClient:
    """最小 OpenAI 兼容客户端，零额外依赖。"""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None,
                 model: Optional[str] = None, timeout: float = 60.0):
        self.base_url = (base_url or os.environ.get("CARSOUL_LLM_BASE_URL") or "").rstrip("/")
        self.api_key = api_key or os.environ.get("CARSOUL_LLM_API_KEY") or ""
        self.model = model or os.environ.get("CARSOUL_LLM_MODEL") or ""
        self.timeout = timeout
        self.available = bool(self.base_url) and bool(self.api_key)

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.3,
             max_tokens: int = 512, tools: Optional[list] = None,
             tool_choice: str = "auto", extra: Optional[dict] = None) -> dict:
        """调用 chat/completions，返回端点原始 JSON（含 choices[0].message）。"""
        if not self.available:
            raise LLMClientError(
                "LLM 端点未配置（需 CARSOUL_LLM_BASE_URL + CARSOUL_LLM_API_KEY）")
        url = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "messages": [_msg_to_dict(m) for m in messages],
            "temperature": temperature, "max_tokens": max_tokens,
        }
        if self.model:
            payload["model"] = self.model
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        if extra:
            payload.update(extra)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise LLMClientError(f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}")
        except urllib.error.URLError as e:
            raise LLMClientError(f"连接失败 {self.base_url}: {e.reason}")

    def generate(self, messages: list[ChatMessage], **kw) -> str:
        """便捷方法：返回 assistant 文本内容（忽略 tool_calls）。"""
        out = self.chat(messages, **kw)
        msg = out["choices"][0]["message"]
        return msg.get("content") or ""

    def select_tools(self, system: str, user: str, tool_schemas: list,
                     temperature: float = 0.2) -> list[str]:
        """fc 模式：让模型从 tool_schemas 中选工具，返回工具名列表。"""
        out = self.chat(
            [ChatMessage("system", system), ChatMessage("user", user)],
            temperature=temperature, max_tokens=256,
            tools=tool_schemas, tool_choice="auto",
        )
        msg = out["choices"][0]["message"]
        names: list[str] = []
        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            name = fn.get("name")
            if name:
                names.append(name)
        if not names and msg.get("content"):
            try:
                parsed = json.loads(msg["content"])
                if isinstance(parsed, list):
                    names = [str(x) for x in parsed]
            except (json.JSONDecodeError, TypeError):
                pass
        return names
