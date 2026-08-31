"""
Privacy Gateway — Enforcing ALLOW / ASK / DENY boundaries before LLM invocations
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.security.classification import (
    DataClassification,
    DataClassifier,
    PrivacyDecision,
    RESTRICTED_PATTERNS,
    RoutingPolicy,
)
from backend.security.audit import log_privacy_event

TICKETS_DIR = Path("data/privacy_approvals")


class PrivacyViolationError(Exception):
    """Raised when RESTRICTED data transmission is attempted (Hard Block)"""
    def __init__(self, message: str, blocked_items: List[Dict[str, Any]] | None = None):
        super().__init__(message)
        self.blocked_items = blocked_items or []


@dataclass
class PrivacyCheckResult:
    allowed: bool
    decision: PrivacyDecision
    highest_classification: DataClassification
    reason: str
    ticket_id: Optional[str] = None
    sanitized_text: Optional[str] = None
    blocked_items: List[Dict[str, Any]] = field(default_factory=list)
    sensitive_items: List[Dict[str, Any]] = field(default_factory=list)


class PrivacyGateway:
    """Gateway checking data classifications and enforcing human-in-the-loop gates"""

    def __init__(self, routing_policy: RoutingPolicy = RoutingPolicy.LOCAL_PREFERRED):
        self.routing_policy = routing_policy
        self._approved_tickets: set[str] = set()
        TICKETS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Strip file system absolute paths and secrets before sending to LLM"""
        if not text:
            return ""
        # Mask Windows / Unix absolute paths
        sanitized = re.sub(
            r"(?:[a-zA-Z]:\\(?:Users|Windows|Program\s*Files)\\[^\s\)\"']+)",
            "[LOCAL_FILE_PATH]",
            text,
        )
        sanitized = re.sub(
            r"(?:\/(?:home|etc|root|var)\/[^\s\)\"']+)",
            "[LOCAL_FILE_PATH]",
            sanitized,
        )
        # Mask obvious API keys and tokens
        sanitized = re.sub(
            r"(?:(?:sk|api|key)[_-][a-zA-Z0-9_\-\.]{16,})",
            "[REDACTED_SECRET]",
            sanitized,
        )
        return sanitized

    def evaluate_text(
        self,
        text: str,
        is_local_llm: bool = True,
        project_id: Optional[str] = None,
        source_meta: Optional[Dict[str, Any]] = None,
    ) -> PrivacyCheckResult:
        """Evaluate a text string for privacy constraints"""
        classification, reason = DataClassifier.classify_text(text)
        decision = DataClassifier.map_to_decision(classification, is_local_llm=is_local_llm)

        # Enforce routing policy on cloud calls
        if not is_local_llm and self.routing_policy == RoutingPolicy.LOCAL_ONLY:
            return PrivacyCheckResult(
                allowed=False,
                decision=PrivacyDecision.DENY,
                highest_classification=classification,
                reason="Routing policy is strictly LOCAL_ONLY; transmission to cloud is prohibited.",
                blocked_items=[{"source": source_meta or "prompt", "reason": "Cloud transmission prohibited under LOCAL_ONLY"}],
            )

        if decision == PrivacyDecision.DENY:
            log_privacy_event(
                project_id=project_id,
                sources=[source_meta or {"type": "text", "snippet": text[:50]}],
                highest_classification=classification.value,
                decision=decision.value,
                provider_name="unknown",
                model_name="unknown",
                user_approved=False,
                blocked_reasons=[reason],
            )
            return PrivacyCheckResult(
                allowed=False,
                decision=decision,
                highest_classification=classification,
                reason=f"Hard security block: {reason}",
                blocked_items=[{"source": source_meta or "text", "reason": reason}],
            )

        elif decision == PrivacyDecision.ASK:
            ticket_id = self._create_ticket(
                project_id=project_id,
                items=[source_meta or {"type": "text", "snippet": text[:100]}],
                classification=classification,
                reason=reason,
            )
            log_privacy_event(
                project_id=project_id,
                sources=[source_meta or {"type": "text", "snippet": text[:50]}],
                highest_classification=classification.value,
                decision=decision.value,
                provider_name="unknown",
                model_name="unknown",
                user_approved=False,
                blocked_reasons=[f"Awaiting user authorization (Ticket {ticket_id})"],
            )
            return PrivacyCheckResult(
                allowed=False,
                decision=decision,
                highest_classification=classification,
                reason=f"Human-in-the-loop authorization required for sensitive context ({reason})",
                ticket_id=ticket_id,
                sensitive_items=[{"source": source_meta or "text", "reason": reason}],
            )

        # ALLOW
        sanitized = self.sanitize(text)
        return PrivacyCheckResult(
            allowed=True,
            decision=PrivacyDecision.ALLOW,
            highest_classification=classification,
            reason="Public or internal context allowed for transmission",
            sanitized_text=sanitized,
        )

    def evaluate_context_items(
        self,
        items: List[Dict[str, Any]],
        is_local_llm: bool = True,
        project_id: Optional[str] = None,
        approved_ticket_id: Optional[str] = None,
    ) -> PrivacyCheckResult:
        """Evaluate a structured bundle of ResearchContext items"""
        # If user provided a valid pre-approved ticket, bypass ASK gate
        if approved_ticket_id and self.is_ticket_approved(approved_ticket_id):
            return PrivacyCheckResult(
                allowed=True,
                decision=PrivacyDecision.ALLOW,
                highest_classification=DataClassification.SENSITIVE,
                reason=f"Pre-authorized via Ticket {approved_ticket_id}",
            )

        highest = DataClassification.PUBLIC
        blocked_items = []
        sensitive_items = []

        for item in items:
            c = item.get("classification")
            content = str(item.get("content", ""))
            
            # If item not explicitly classified, scan it
            if not c or c not in DataClassification._value2member_map_:
                c_enum, r_text = DataClassifier.classify_text(content)
            else:
                c_enum = DataClassification(c)
                r_text = item.get("reason", "Pre-classified item")

            if c_enum == DataClassification.RESTRICTED:
                highest = DataClassification.RESTRICTED
                blocked_items.append({"id": item.get("source_id"), "type": item.get("source_type"), "reason": r_text})
            elif c_enum == DataClassification.SENSITIVE:
                if highest != DataClassification.RESTRICTED:
                    highest = DataClassification.SENSITIVE
                sensitive_items.append({"id": item.get("source_id"), "type": item.get("source_type"), "reason": r_text})
            elif c_enum == DataClassification.INTERNAL:
                if highest == DataClassification.PUBLIC:
                    highest = DataClassification.INTERNAL

        # 1. Check RESTRICTED -> DENY
        if highest == DataClassification.RESTRICTED:
            log_privacy_event(
                project_id=project_id,
                sources=items,
                highest_classification=highest.value,
                decision=PrivacyDecision.DENY.value,
                provider_name="unknown",
                model_name="unknown",
                user_approved=False,
                blocked_reasons=[b["reason"] for b in blocked_items],
            )
            return PrivacyCheckResult(
                allowed=False,
                decision=PrivacyDecision.DENY,
                highest_classification=highest,
                reason="One or more context items contain RESTRICTED data (e.g. raw tabular data or credentials).",
                blocked_items=blocked_items,
            )

        # 2. Check SENSITIVE -> ASK
        if highest == DataClassification.SENSITIVE:
            ticket_id = self._create_ticket(
                project_id=project_id,
                items=sensitive_items,
                classification=highest,
                reason="Context includes sensitive unpublished hypotheses or analysis parameters.",
            )
            log_privacy_event(
                project_id=project_id,
                sources=items,
                highest_classification=highest.value,
                decision=PrivacyDecision.ASK.value,
                provider_name="unknown",
                model_name="unknown",
                user_approved=False,
                blocked_reasons=[f"Created authorization ticket: {ticket_id}"],
            )
            return PrivacyCheckResult(
                allowed=False,
                decision=PrivacyDecision.ASK,
                highest_classification=highest,
                reason="Context contains SENSITIVE research items. Requires user approval ticket.",
                ticket_id=ticket_id,
                sensitive_items=sensitive_items,
            )

        # 3. ALLOW
        return PrivacyCheckResult(
            allowed=True,
            decision=PrivacyDecision.ALLOW,
            highest_classification=highest,
            reason="All context items classified as safe for transmission.",
        )

    def _create_ticket(
        self,
        project_id: Optional[str],
        items: List[Dict[str, Any]],
        classification: DataClassification,
        reason: str,
    ) -> str:
        ticket_id = f"priv_tkt_{int(time.time()*1000)}"
        ticket_data = {
            "id": ticket_id,
            "project_id": project_id or "global",
            "classification": classification.value,
            "reason": reason,
            "items": items,
            "status": "pending",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        ticket_path = TICKETS_DIR / f"{ticket_id}.json"
        ticket_path.write_text(json.dumps(ticket_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return ticket_id

    def authorize_ticket(self, ticket_id: str, action: str = "allow_once") -> bool:
        """Approve or deny an existing privacy ticket"""
        ticket_path = TICKETS_DIR / f"{ticket_id}.json"
        if not ticket_path.exists():
            return False
        try:
            data = json.loads(ticket_path.read_text(encoding="utf-8"))
            if action in ("allow_once", "allow_task", "approve"):
                data["status"] = "approved"
                data["authorized_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self._approved_tickets.add(ticket_id)
            else:
                data["status"] = "denied"
            ticket_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return data["status"] == "approved"
        except Exception:
            return False

    def is_ticket_approved(self, ticket_id: str) -> bool:
        if ticket_id in self._approved_tickets:
            return True
        ticket_path = TICKETS_DIR / f"{ticket_id}.json"
        if not ticket_path.exists():
            return False
        try:
            data = json.loads(ticket_path.read_text(encoding="utf-8"))
            if data.get("status") == "approved":
                self._approved_tickets.add(ticket_id)
                return True
        except Exception:
            pass
        return False


# Singleton Privacy Gateway instance
privacy_gateway = PrivacyGateway()
