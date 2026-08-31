"""
LLM Gateway — Orchestrates Providers with Privacy Boundary Enforcement
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from backend.llm.base import (
    ChatMessage,
    ChatResponse,
    LLMProvider,
    ProviderType,
    RoutingPolicy,
)
from backend.llm.context import ResearchContext
from backend.llm.providers.mock import MockProvider
from backend.llm.providers.ollama import OllamaProvider
from backend.llm.providers.openai_compatible import OpenAICompatibleProvider
from backend.security.audit import log_privacy_event
from backend.security.classification import DataClassification, PrivacyDecision
from backend.security.privacy_gateway import (
    PrivacyCheckResult,
    PrivacyViolationError,
    privacy_gateway,
)

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("data/config/llm_config.json")


class LLMGateway:
    """Central gateway for all LLM interactions in ResearchOS"""

    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.active_provider_name: str = "ollama"
        self.routing_policy: RoutingPolicy = RoutingPolicy.LOCAL_PREFERRED
        self._init_default_providers()
        self._load_config()

    def _init_default_providers(self):
        # 1. Local Ollama Provider
        ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.register_provider(OllamaProvider(endpoint=ollama_endpoint, default_model=ollama_model))

        # 2. OpenAI-Compatible Provider (Cloud / Remote)
        openai_endpoint = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        openai_key = os.getenv("LLM_API_KEY", "")
        openai_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.register_provider(
            OpenAICompatibleProvider(
                name="openai_compatible",
                endpoint=openai_endpoint,
                api_key=openai_key,
                default_model=openai_model,
                is_local=False,
            )
        )

        # 3. Deterministic Mock Provider (always available for tests/offline fallback)
        self.register_provider(MockProvider(name="mock", default_model="mock-v25", is_local=True))

    def _load_config(self):
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                if "active_provider" in data and data["active_provider"] in self.providers:
                    self.active_provider_name = data["active_provider"]
                if "routing_policy" in data and data["routing_policy"] in RoutingPolicy._value2member_map_:
                    self.routing_policy = RoutingPolicy(data["routing_policy"])
                    privacy_gateway.routing_policy = self.routing_policy
            except Exception as e:
                logger.debug(f"Failed to load LLM config: {e}")

    def save_config(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "active_provider": self.active_provider_name,
            "routing_policy": self.routing_policy.value,
        }
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def register_provider(self, provider: LLMProvider):
        self.providers[provider.name] = provider

    def get_provider(self, name: str) -> Optional[LLMProvider]:
        return self.providers.get(name)

    def get_active_provider(self) -> LLMProvider:
        prov = self.providers.get(self.active_provider_name)
        if not prov:
            prov = self.providers.get("mock") or list(self.providers.values())[0]
        return prov

    def set_active_provider(self, name: str):
        if name in self.providers:
            self.active_provider_name = name
            self.save_config()
        else:
            raise ValueError(f"Unknown provider name: '{name}'. Available: {list(self.providers.keys())}")

    def set_routing_policy(self, policy: RoutingPolicy):
        self.routing_policy = policy
        privacy_gateway.routing_policy = policy
        self.save_config()

    def list_providers(self) -> List[Dict[str, Any]]:
        result = []
        for name, p in self.providers.items():
            health_info = p.health()
            result.append({
                "name": name,
                "type": p.provider_type.value,
                "is_local": p.is_local,
                "endpoint": p.endpoint,
                "default_model": p.default_model,
                "is_active": (name == self.active_provider_name),
                "health": health_info,
            })
        return result

    def safe_chat(
        self,
        messages: List[ChatMessage | Dict[str, Any]] | str,
        project_id: Optional[str] = None,
        context: Optional[ResearchContext] = None,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        approved_ticket_id: Optional[str] = None,
    ) -> ChatResponse:
        """
        Execute chat completion after passing through Privacy Gateway checks.
        NEVER calls LLM if PrivacyDecision is DENY.
        """
        target_provider = self.get_provider(provider_name) if provider_name else self.get_active_provider()
        if not target_provider:
            raise RuntimeError("No active LLM provider available.")

        # Normalize messages
        norm_messages: List[ChatMessage] = []
        if isinstance(messages, str):
            norm_messages = [ChatMessage(role="user", content=messages)]
        else:
            for m in messages:
                if isinstance(m, ChatMessage):
                    norm_messages.append(m)
                elif isinstance(m, dict):
                    norm_messages.append(ChatMessage(role=m.get("role", "user"), content=m.get("content", "")))

        # 1. Privacy Boundary Check
        # If context is provided, check context items
        if context and context.items:
            items_dict = [it.to_dict() for it in context.items]
            check = privacy_gateway.evaluate_context_items(
                items=items_dict,
                is_local_llm=target_provider.is_local,
                project_id=project_id,
                approved_ticket_id=approved_ticket_id,
            )
        else:
            # Check prompt text
            all_text = " ".join([m.content for m in norm_messages])
            check = privacy_gateway.evaluate_text(
                text=all_text,
                is_local_llm=target_provider.is_local,
                project_id=project_id,
            )

        # 2. Hard Security Block on DENY
        if check.decision == PrivacyDecision.DENY:
            logger.warning(f"Privacy Gateway BLOCKED LLM call: {check.reason}")
            raise PrivacyViolationError(
                f"Privacy Gateway Hard Block: {check.reason}",
                blocked_items=check.blocked_items,
            )

        # 3. Human-in-the-loop Gate on ASK
        if check.decision == PrivacyDecision.ASK and not (approved_ticket_id and privacy_gateway.is_ticket_approved(approved_ticket_id)):
            return ChatResponse(
                content=f"[PRIVACY_GATE_REQUIRED: {check.reason} (Ticket: {check.ticket_id})]",
                model=model or target_provider.default_model,
                provider_name=target_provider.name,
                finish_reason="privacy_approval_required",
                raw_response={"ticket_id": check.ticket_id, "sensitive_items": check.sensitive_items},
            )

        # 4. Proceed with Execution
        # If text was sanitized, apply to user prompt
        if check.sanitized_text and norm_messages and len(norm_messages) == 1:
            norm_messages[0].content = check.sanitized_text

        # If context provided, inject prompt context block
        if context and context.items:
            ctx_block = context.render_prompt_block()
            norm_messages.insert(0, ChatMessage(role="system", content=f"Research Context:\n{ctx_block}"))

        res = target_provider.chat(
            messages=norm_messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
        )

        # Log audit record
        log_privacy_event(
            project_id=project_id,
            sources=[{"source": "safe_chat", "messages_count": len(norm_messages)}],
            highest_classification=check.highest_classification.value,
            decision=check.decision.value,
            provider_name=target_provider.name,
            model_name=res.model,
            user_approved=bool(approved_ticket_id),
        )

        return res

    def safe_stream_chat(
        self,
        messages: List[ChatMessage | Dict[str, Any]] | str,
        project_id: Optional[str] = None,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        approved_ticket_id: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Stream chat completion passing through Privacy Gateway"""
        target_provider = self.get_provider(provider_name) if provider_name else self.get_active_provider()
        if not target_provider:
            yield "LLM_ERROR: No active provider available."
            return

        all_text = messages if isinstance(messages, str) else " ".join([m.get("content", "") if isinstance(m, dict) else m.content for m in messages])
        check = privacy_gateway.evaluate_text(
            text=all_text,
            is_local_llm=target_provider.is_local,
            project_id=project_id,
        )

        if check.decision == PrivacyDecision.DENY:
            yield f"[PRIVACY_DENY_ERROR: {check.reason}]"
            return
        elif check.decision == PrivacyDecision.ASK and not (approved_ticket_id and privacy_gateway.is_ticket_approved(approved_ticket_id)):
            yield f"[PRIVACY_APPROVAL_REQUIRED: Ticket {check.ticket_id}]"
            return

        for chunk in target_provider.stream_chat(
            messages=messages if isinstance(messages, list) else [{"role": "user", "content": messages}],
            model=model,
            temperature=temperature,
        ):
            yield chunk


# Singleton LLM Gateway instance
llm_gateway = LLMGateway()
