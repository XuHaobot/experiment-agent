"""Tool 基类与定义规范"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

from backend.agent.security.risk import RiskLevel


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # OpenAI function-call schema (input_schema)
    handler: Callable[..., Any]
    tags: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    permissions: list[str] = field(default_factory=list)
    requires_approval: bool = False

    @property
    def input_schema(self) -> dict:
        """兼容 input_schema 命名"""
        return self.parameters

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
