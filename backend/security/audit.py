"""
Privacy Audit Logger for AI Data Transmission
Stores records locally in data/audit/privacy_audit.jsonl without recording raw sensitive payloads.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

AUDIT_DIR = Path("data/audit")
AUDIT_FILE = AUDIT_DIR / "privacy_audit.jsonl"


def _ensure_dir():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def log_privacy_event(
    project_id: Optional[str],
    sources: List[Dict[str, Any]],
    highest_classification: str,
    decision: str,
    provider_name: str,
    model_name: str,
    user_approved: bool = False,
    blocked_reasons: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Record an audit log entry for privacy decisions"""
    _ensure_dir()
    event = {
        "id": f"priv_evt_{int(time.time()*1000)}",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "project_id": project_id or "global",
        "sources": sources,
        "highest_classification": highest_classification,
        "decision": decision,
        "provider_name": provider_name,
        "model_name": model_name,
        "user_approved": user_approved,
        "blocked_reasons": blocked_reasons or [],
    }
    try:
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return event


def get_privacy_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent privacy audit entries"""
    if not AUDIT_FILE.exists():
        return []
    logs = []
    try:
        with open(AUDIT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line.strip()))
    except Exception:
        return []
    return logs[-limit:][::-1]
