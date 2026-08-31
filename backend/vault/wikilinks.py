"""
Wikilinks Helper & Reference Generator
"""
from __future__ import annotations

import re
from typing import List, Optional


WIKILINK_PATTERN = re.compile(r"\[\[([^\|\]]+)(?:\|([^\]]+))?\]\]")


def wikilink(entity_id: str, label: Optional[str] = None) -> str:
    """Format a stable entity ID into an Obsidian Wikilink"""
    if not entity_id:
        return ""
    if label and label.strip() and label.strip() != entity_id:
        return f"[[{entity_id}|{label.strip()}]]"
    return f"[[{entity_id}]]"


def extract_wikilinks(text: str) -> List[str]:
    """Extract all referenced entity IDs from wikilinks in text"""
    if not text:
        return []
    matches = WIKILINK_PATTERN.findall(text)
    return [m[0].strip() for m in matches if m[0].strip()]
