"""
Vault Manifest Manager
Stores ResearchOS/manifest.json in the Obsidian Vault to track exported entities.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


MANIFEST_SUBDIR = "ResearchOS"
MANIFEST_FILENAME = "manifest.json"


def get_manifest_path(vault_path: Path) -> Path:
    return vault_path / MANIFEST_SUBDIR / MANIFEST_FILENAME


def load_manifest(vault_path: Path) -> Optional[Dict[str, Any]]:
    p = get_manifest_path(vault_path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_manifest(vault_path: Path, manifest_data: Dict[str, Any]):
    p = get_manifest_path(vault_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_initial_manifest(project_id: str) -> Dict[str, Any]:
    return {
        "version": "1.0",
        "generated_by": "ResearchOS",
        "project_id": project_id,
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "entities": {
            "project": [],
            "question": [],
            "hypothesis": [],
            "experiment": [],
            "evidence": [],
            "conclusion": [],
            "literature": [],
            "artifact": [],
        },
        "files_managed": {},
    }
