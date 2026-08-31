"""
Ollama Local LLM Provider
Default endpoint: http://localhost:11434
"""
from __future__ import annotations

import json
import logging
import urllib.parse
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


class OllamaProvider(LLMProvider):
    """Local Ollama Provider with health check, model discovery, and streaming"""

    def __init__(
        self,
        endpoint: str = "http://localhost:11434",
        default_model: str = "qwen2.5:7b",
        timeout: int = 60,
    ):
        super().__init__(
            name="ollama",
            provider_type=ProviderType.LOCAL,
            endpoint=endpoint.rstrip("/"),
            default_model=default_model,
            api_key="",
            capabilities=ProviderCapabilities(
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                max_context_window=32768,
            ),
        )
        self.timeout = timeout

    def health(self) -> Dict[str, Any]:
        """Check if Ollama server is running and reachable"""
        try:
            resp = requests.get(f"{self.endpoint}/api/version", timeout=3)
            if resp.status_code == 200:
                version = resp.json().get("version", "unknown")
                return {
                    "status": "connected",
                    "provider": "ollama",
                    "is_local": True,
                    "version": version,
                    "endpoint": self.endpoint,
                }
            return {
                "status": "error",
                "provider": "ollama",
                "is_local": True,
                "detail": f"HTTP {resp.status_code}",
                "endpoint": self.endpoint,
            }
        except Exception as e:
            return {
                "status": "disconnected",
                "provider": "ollama",
                "is_local": True,
                "detail": str(e),
                "endpoint": self.endpoint,
            }

    def list_models(self) -> List[Dict[str, Any]]:
        """Fetch locally pulled models from Ollama"""
        try:
            resp = requests.get(f"{self.endpoint}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [
                    {
                        "name": m.get("name"),
                        "size": m.get("size"),
                        "digest": m.get("digest"),
                        "modified_at": m.get("modified_at"),
                        "is_local": True,
                    }
                    for m in models
                ]
            return []
        except Exception as e:
            logger.debug(f"Failed to list Ollama models: {e}")
            return []

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
        url = f"{self.endpoint}/api/chat"
        norm_messages = self._normalize_messages(messages)
        
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": norm_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        if tools:
            payload["tools"] = tools

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            if resp.status_code != 200:
                return ChatResponse(
                    content=f"OLLAMA_ERROR: HTTP {resp.status_code}: {resp.text[:300]}",
                    model=target_model,
                    provider_name=self.name,
                    finish_reason="error",
                )
            data = resp.json()
            msg = data.get("message", {})
            return ChatResponse(
                content=msg.get("content", ""),
                model=target_model,
                provider_name=self.name,
                finish_reason=data.get("done_reason", "stop"),
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                },
                raw_response=data,
            )
        except Exception as e:
            return ChatResponse(
                content=f"OLLAMA_CONNECT_ERROR: {e}",
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
        url = f"{self.endpoint}/api/chat"
        norm_messages = self._normalize_messages(messages)

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": norm_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        if tools:
            payload["tools"] = tools

        try:
            with requests.post(url, json=payload, stream=True, timeout=self.timeout) as resp:
                if resp.status_code != 200:
                    yield f"OLLAMA_STREAM_ERROR: HTTP {resp.status_code}"
                    return
                for line in resp.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line.decode("utf-8"))
                            delta = chunk.get("message", {}).get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            continue
        except Exception as e:
            yield f"OLLAMA_STREAM_EXCEPTION: {e}"
