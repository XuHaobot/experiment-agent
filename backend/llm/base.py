"""
LLM Provider Base Interface & Dataclasses
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional


class ProviderType(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"
    MOCK = "mock"


from backend.security.classification import RoutingPolicy


@dataclass
class ProviderCapabilities:
    supports_streaming: bool = True
    supports_function_calling: bool = False
    supports_vision: bool = False
    max_context_window: int = 8192


@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class ChatResponse:
    content: str
    model: str
    provider_name: str
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class StreamChunk:
    delta: str
    finish_reason: Optional[str] = None


class LLMProvider(ABC):
    """Abstract Base Class for all LLM Providers (Local and Cloud)"""
    
    def __init__(
        self,
        name: str,
        provider_type: ProviderType,
        endpoint: str,
        default_model: str,
        api_key: Optional[str] = None,
        capabilities: Optional[ProviderCapabilities] = None,
    ):
        self.name = name
        self.provider_type = provider_type
        self.endpoint = endpoint
        self.default_model = default_model
        self.api_key = api_key or ""
        self.capabilities = capabilities or ProviderCapabilities()

    @property
    def is_local(self) -> bool:
        return self.provider_type == ProviderType.LOCAL

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Check provider connectivity and status"""
        pass

    @abstractmethod
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models for this provider"""
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[ChatMessage | Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatResponse:
        """Synchronous chat completion"""
        pass

    @abstractmethod
    def stream_chat(
        self,
        messages: List[ChatMessage | Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        """Generator yielding text chunks or StreamChunk"""
        pass
