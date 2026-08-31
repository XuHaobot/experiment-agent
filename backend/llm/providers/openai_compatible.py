"""
OpenAI-Compatible Provider (Cloud / Local vLLM / LM Studio / DeepSeek)
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Generator, List, Optional
import requests

from backend.llm.base import (
    ChatMessage,
    ChatResponse,
    LLMProvider,
    ProviderCapabilities,
    ProviderType,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible Chat Completions Provider"""

    def __init__(
        self,
        name: str = "openai_compatible",
        endpoint: str = "https://api.openai.com/v1",
        api_key: str = "",
        default_model: str = "gpt-4o-mini",
        is_local: bool = False,
        timeout: int = 60,
    ):
        provider_type = ProviderType.LOCAL if is_local else ProviderType.CLOUD
        super().__init__(
            name=name,
            provider_type=provider_type,
            endpoint=endpoint.rstrip("/"),
            default_model=default_model,
            api_key=api_key,
            capabilities=ProviderCapabilities(
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                max_context_window=128000,
            ),
        )
        self.timeout = timeout

    def health(self) -> Dict[str, Any]:
        """Check provider status by querying models endpoint"""
        url = f"{self.endpoint}/models"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                return {
                    "status": "connected",
                    "provider": self.name,
                    "is_local": self.is_local,
                    "endpoint": self.endpoint,
                    "default_model": self.default_model,
                }
            return {
                "status": "error",
                "provider": self.name,
                "is_local": self.is_local,
                "detail": f"HTTP {resp.status_code}",
                "endpoint": self.endpoint,
            }
        except Exception as e:
            return {
                "status": "disconnected",
                "provider": self.name,
                "is_local": self.is_local,
                "detail": str(e),
                "endpoint": self.endpoint,
            }

    def list_models(self) -> List[Dict[str, Any]]:
        """Fetch available models from endpoint"""
        url = f"{self.endpoint}/models"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                return [
                    {
                        "name": m.get("id"),
                        "owned_by": m.get("owned_by"),
                        "is_local": self.is_local,
                    }
                    for m in models
                ]
            return [{"name": self.default_model, "is_local": self.is_local}]
        except Exception:
            return [{"name": self.default_model, "is_local": self.is_local}]

    def _normalize_messages(self, messages: List[ChatMessage | Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for m in messages:
            if isinstance(m, ChatMessage):
                d = {"role": m.role, "content": m.content}
                if m.tool_calls:
                    d["tool_calls"] = m.tool_calls
                normalized.append(d)
            elif isinstance(m, dict):
                normalized.append(m)
        return normalized

    def chat(
        self,
        messages: List[ChatMessage | Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatResponse:
        target_model = model or self.default_model
        url = f"{self.endpoint}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": self._normalize_messages(messages),
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            if resp.status_code >= 400:
                return ChatResponse(
                    content=f"OPENAI_COMPAT_ERROR: HTTP {resp.status_code}: {resp.text[:300]}",
                    model=target_model,
                    provider_name=self.name,
                    finish_reason="error",
                )
            data = resp.json()
            choice = data["choices"][0]
            msg = choice.get("message", {})
            return ChatResponse(
                content=msg.get("content") or "",
                model=target_model,
                provider_name=self.name,
                finish_reason=choice.get("finish_reason", "stop"),
                usage=data.get("usage", {}),
                raw_response=data,
            )
        except Exception as e:
            return ChatResponse(
                content=f"OPENAI_COMPAT_EXCEPTION: {e}",
                model=target_model,
                provider_name=self.name,
                finish_reason="error",
            )

    def stream_chat(
        self,
        messages: List[ChatMessage | Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Generator[str, None, None]:
        target_model = model or self.default_model
        url = f"{self.endpoint}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": self._normalize_messages(messages),
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools

        try:
            with requests.post(url, headers=headers, json=payload, stream=True, timeout=self.timeout) as resp:
                if resp.status_code >= 400:
                    yield f"OPENAI_STREAM_ERROR: HTTP {resp.status_code}"
                    return
                for line in resp.iter_lines():
                    if line:
                        line_str = line.decode("utf-8")
                        if line_str.startswith("data: "):
                            raw_data = line_str[6:].strip()
                            if raw_data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(raw_data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    yield delta
                            except Exception:
                                continue
        except Exception as e:
            yield f"OPENAI_STREAM_EXCEPTION: {e}"
