"""
Obsidian Vault Data Models & Data Structures
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class VaultReconcileStatus(str, Enum):
    UNCHANGED = "UNCHANGED"
    USER_MODIFIED = "USER_MODIFIED"
    RESEARCHOS_MODIFIED = "RESEARCHOS_MODIFIED"
    CONFLICT = "CONFLICT"
    NEW_NOTE = "NEW_NOTE"


@dataclass
class VaultExportOptions:
    include_entities: List[str] = field(
        default_factory=lambda: [
            "project",
            "question",
            "hypothesis",
            "experiment",
            "evidence",
            "conclusion",
            "literature",
            "artifact",
        ]
    )
    folder_mapping: Dict[str, str] = field(
        default_factory=lambda: {
            "project": "00_Project",
            "question": "01_Questions",
            "hypothesis": "02_Hypotheses",
            "experiment": "03_Experiments",
            "evidence": "04_Evidence",
            "conclusion": "05_Conclusions",
            "literature": "06_Literature",
            "artifact": "07_Artifacts",
        }
    )


@dataclass
class VaultFileAction:
    rel_path: str
    action: str  # "create" | "update" | "skip"
    entity_type: str
    entity_id: str
    has_user_notes: bool = False
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rel_path": self.rel_path,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "has_user_notes": self.has_user_notes,
            "reason": self.reason,
        }


@dataclass
class VaultPreviewSummary:
    project_id: str
    vault_path: str
    total_files_to_create: int = 0
    total_files_to_update: int = 0
    total_files_skipped: int = 0
    total_conflicts: int = 0
    entities_breakdown: Dict[str, int] = field(default_factory=dict)
    file_actions: List[VaultFileAction] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "vault_path": self.vault_path,
            "total_files_to_create": self.total_files_to_create,
            "total_files_to_update": self.total_files_to_update,
            "total_files_skipped": self.total_files_skipped,
            "total_conflicts": self.total_conflicts,
            "entities_breakdown": self.entities_breakdown,
            "file_actions": [a.to_dict() for a in self.file_actions],
        }
