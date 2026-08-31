"""
Execution Runner Base Interface — 代码与沙箱执行统一接口
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class ExecutionRunner(ABC):
    """代码执行器抽象基类"""
    name: str = "base"

    @abstractmethod
    def run_code(
        self,
        code: str,
        timeout: int = 15,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        执行代码并返回标准化结果：
        {
            "success": bool,
            "stdout": str,
            "error": str | None,
            "charts": list[str], # Base64 PNGs
            "execution_time_ms": float,
        }
        """
        pass


class RestrictedPythonRunner(ExecutionRunner):
    """当前默认使用的受控 Python AST 隔离执行器"""
    name: str = "restricted_python"

    def run_code(
        self,
        code: str,
        timeout: int = 15,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from backend.domain.data_agent import run_python_sandbox
        return run_python_sandbox(code, timeout=timeout, context=context)
