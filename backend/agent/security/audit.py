"""
Audit Logger — 记录所有 Tool 调用的审计日志（JSON Lines 文件持久化）
"""
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
AUDIT_DIR = DATA_DIR / "audit"
AUDIT_FILE = AUDIT_DIR / "tool_calls.jsonl"


def _sanitize_value(val: Any, max_str_len: int = 200) -> Any:
    """对敏感或超长参数（如 base64 图片、巨型 dataset）进行安全截断"""
    if isinstance(val, str):
        if len(val) > max_str_len:
            return val[:max_str_len] + f"... [truncated, total {len(val)} chars]"
        return val
    elif isinstance(val, dict):
        return {k: _sanitize_value(v, max_str_len) for k, v in val.items()}
    elif isinstance(val, list):
        if len(val) > 20:
            return [_sanitize_value(item, max_str_len) for item in val[:20]] + [f"... [truncated, total {len(val)} items]"]
        return [_sanitize_value(item, max_str_len) for item in val]
    return val


def log_tool_call(
    caller: str,
    tool_name: str,
    risk_level: str,
    parameters: dict[str, Any],
    status: str,  # "success" | "failed" | "approval_required" | "blocked"
    approval_required: bool = False,
    approval_id: str | None = None,
    result_or_error: Any = None,
) -> None:
    """记录一条工具调用审计日志"""
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "caller": caller or "agent",
            "tool_name": tool_name,
            "risk_level": str(risk_level),
            "parameters": _sanitize_value(parameters),
            "status": status,
            "approval_required": approval_required,
            "approval_id": approval_id,
            "result_summary": _sanitize_value(result_or_error, max_str_len=300),
        }
        
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Failed to write audit log: %s", e)
