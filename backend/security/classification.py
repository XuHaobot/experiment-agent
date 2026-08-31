"""
Data Classification & Privacy Decisions
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
import re


class DataClassification(str, Enum):
    PUBLIC = "PUBLIC"            # Open papers, public datasets metadata, general science concepts
    INTERNAL = "INTERNAL"        # Project question, domain terminology, high-level workflow
    SENSITIVE = "SENSITIVE"      # Unpublished hypotheses, experiment params, analysis drafts, conclusion notes
    RESTRICTED = "RESTRICTED"    # Raw dataset rows, patient records, env secrets, API keys, absolute machine paths


class PrivacyDecision(str, Enum):
    ALLOW = "ALLOW"              # Safe to proceed without manual gate
    ASK = "ASK"                  # Requires user authorization before transmission
    DENY = "DENY"                # Hard blocked. Never transmit to LLM under any circumstance


class RoutingPolicy(str, Enum):
    LOCAL_ONLY = "LOCAL_ONLY"
    LOCAL_PREFERRED = "LOCAL_PREFERRED"
    CLOUD_ALLOWED = "CLOUD_ALLOWED"


# Sensitive regex patterns to automatically detect RESTRICTED items
RESTRICTED_PATTERNS = [
    re.compile(r"(?:api[_-]?key|secret|password|bearer\s+[a-zA-Z0-9_\-\.]{20,})", re.IGNORECASE),
    re.compile(r"(?:(?:[a-zA-Z]:\\(?:Users|Windows|Program\s*Files))|(?:\/(?:home|etc|root|var)\/))", re.IGNORECASE),
    re.compile(r"(?:patient[_-]?id|ssn|mrn|medical[_-]?record|subject[_-]?(?:name|dob))", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA|OPENSSH|PRIVATE) KEY-----"),
]

SENSITIVE_PATTERNS = [
    re.compile(r"(?:unpublished|draft\s*conclusion|proprietary|confidential)", re.IGNORECASE),
    re.compile(r"(?:hyp_\w+|exp_\w+|conc_\w+)"),
]


class DataClassifier:
    """Classifies content and context into privacy tiers"""

    @classmethod
    def classify_text(cls, text: str) -> tuple[DataClassification, str]:
        """Inspect text content and determine privacy classification"""
        if not text:
            return DataClassification.PUBLIC, "Empty content"

        # Check RESTRICTED triggers
        for p in RESTRICTED_PATTERNS:
            if p.search(text):
                return DataClassification.RESTRICTED, f"Matched restricted security pattern: {p.pattern}"

        # Check if text contains raw CSV/table data rows (many comma/tab-separated numbers)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) > 5:
            csv_like_lines = sum(1 for line in lines if line.count(",") >= 3 or line.count("\t") >= 3)
            if csv_like_lines / len(lines) > 0.6:
                return DataClassification.RESTRICTED, "Detected raw dataset row contents (CSV/TSV table rows)"

        # Check SENSITIVE triggers
        for p in SENSITIVE_PATTERNS:
            if p.search(text):
                return DataClassification.SENSITIVE, f"Matched sensitive research artifact pattern: {p.pattern}"

        return DataClassification.PUBLIC, "General scientific text or metadata"

    @classmethod
    def map_to_decision(cls, classification: DataClassification, is_local_llm: bool = True) -> PrivacyDecision:
        """Map data classification to privacy decision based on target destination"""
        if classification == DataClassification.RESTRICTED:
            return PrivacyDecision.DENY
        elif classification == DataClassification.SENSITIVE:
            return PrivacyDecision.ASK
        elif classification == DataClassification.INTERNAL:
            return PrivacyDecision.ALLOW if is_local_llm else PrivacyDecision.ASK
        else:
            return PrivacyDecision.ALLOW
