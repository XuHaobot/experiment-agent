"""
Security Guard & Human-in-the-Loop (HITL) Approval Management
"""
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
APPROVALS_DIR = DATA_DIR / "approvals"


def _ensure_dir():
    APPROVALS_DIR.mkdir(parents=True, exist_ok=True)


def _approval_path(approval_id: str) -> Path:
    return APPROVALS_DIR / f"{approval_id}.json"


def create_approval_request(
    tool_name: str,
    parameters: dict[str, Any],
    caller: str = "agent",
    reason: str = "High-risk tool execution requires human authorization",
) -> dict:
    """创建并持久化审批申请"""
    _ensure_dir()
    approval_id = f"appr_{uuid.uuid4().hex[:10]}"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    record = {
        "id": approval_id,
        "tool_name": tool_name,
        "parameters": parameters,
        "caller": caller,
        "reason": reason,
        "status": "pending",  # "pending" | "approved" | "rejected"
        "created_at": now,
        "updated_at": now,
        "approver": None,
    }
    
    _approval_path(approval_id).write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Approval request created: %s for tool %s", approval_id, tool_name)
    return record


def get_approval(approval_id: str) -> dict | None:
    """获取审批详情"""
    p = _approval_path(approval_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def approve_request(approval_id: str, approver: str = "human") -> dict | None:
    """批准申请"""
    record = get_approval(approval_id)
    if not record:
        return None
    
    record["status"] = "approved"
    record["approver"] = approver
    record["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    _approval_path(approval_id).write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Approval %s APPROVED by %s", approval_id, approver)
    return record


def reject_request(approval_id: str, rejector: str = "human", reason: str = "") -> dict | None:
    """拒绝申请"""
    record = get_approval(approval_id)
    if not record:
        return None
    
    record["status"] = "rejected"
    record["approver"] = rejector
    record["rejection_reason"] = reason
    record["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    _approval_path(approval_id).write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Approval %s REJECTED by %s", approval_id, rejector)
    return record


def is_approved(approval_id: str | None, tool_name: str) -> bool:
    """验证指定工具调用的审批凭证是否合法且为 approved 状态"""
    if not approval_id:
        return False
    record = get_approval(approval_id)
    if not record:
        return False
    return record.get("status") == "approved" and record.get("tool_name") == tool_name
