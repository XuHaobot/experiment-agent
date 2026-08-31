"""
Security and Privacy Boundary Module
"""
from backend.security.classification import (
    DataClassification,
    DataClassifier,
    PrivacyDecision,
)
from backend.security.privacy_gateway import (
    PrivacyGateway,
    PrivacyViolationError,
    PrivacyCheckResult,
    privacy_gateway,
)
from backend.security.audit import (
    log_privacy_event,
    get_privacy_audit_logs,
)

__all__ = [
    "DataClassification",
    "DataClassifier",
    "PrivacyDecision",
    "PrivacyGateway",
    "PrivacyViolationError",
    "PrivacyCheckResult",
    "privacy_gateway",
    "log_privacy_event",
    "get_privacy_audit_logs",
]
