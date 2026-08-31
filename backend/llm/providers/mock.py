"""
Mock LLM Provider for Testing & Offline Fallback
"""
from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional

from backend.llm.base import (
    ChatMessage,
    ChatResponse,
    LLMProvider,
    ProviderCapabilities,
    ProviderType,
)


class MockProvider(LLMProvider):
    """Deterministic Mock Provider for unit testing and offline environments"""

    def __init__(
        self,
        name: str = "mock",
        default_model: str = "mock-model",
        custom_responses: Optional[Dict[str, str]] = None,
        is_local: bool = True,
    ):
        super().__init__(
            name=name,
            provider_type=ProviderType.LOCAL if is_local else ProviderType.CLOUD,
            endpoint="mock://localhost",
            default_model=default_model,
            api_key="mock-key",
            capabilities=ProviderCapabilities(
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                max_context_window=32768,
            ),
        )
        self.custom_responses = custom_responses or {}
        self.call_history: List[Dict[str, Any]] = []

    def health(self) -> Dict[str, Any]:
        return {
            "status": "connected",
            "provider": self.name,
            "is_local": self.is_local,
            "endpoint": self.endpoint,
            "version": "mock-1.0",
        }

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {"name": self.default_model, "is_local": self.is_local},
            {"name": "mock-fast", "is_local": self.is_local},
        ]

    def chat(
        self,
        messages: List[ChatMessage | Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatResponse:
        self.call_history.append({
            "messages": messages,
            "model": model or self.default_model,
            "temperature": temperature,
            "tools": tools,
        })
        last_msg = ""
        if messages:
            last = messages[-1]
            last_msg = last.content if isinstance(last, ChatMessage) else last.get("content", "")

        for pattern, response in self.custom_responses.items():
            if pattern.lower() in last_msg.lower():
                return ChatResponse(
                    content=response,
                    model=model or self.default_model,
                    provider_name=self.name,
                    finish_reason="stop",
                )

        default_reply = (
            f"[MOCK RESPONSE from {self.name}] Received {len(messages)} messages. "
            f"Last message snippet: '{last_msg[:60]}...'"
        )
        return ChatResponse(
            content=default_reply,
            model=model or self.default_model,
            provider_name=self.name,
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )

    def stream_chat(
        self,
        messages: List[ChatMessage | Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Generator[str, None, None]:
        res = self.chat(messages, model, temperature, max_tokens, tools)
        tokens = res.content.split(" ")
        for tok in tokens:
            yield tok + " "
