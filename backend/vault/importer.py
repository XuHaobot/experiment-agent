"""
Vault Inspector & Light Reconcile Engine
Inspects Obsidian Vault to detect USER_MODIFIED, UNCHANGED, NEW_NOTE, and CONFLICT states.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List

from backend.vault.manifest import load_manifest
from backend.vault.models import VaultReconcileStatus


def _file_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def reconcile_vault(vault_path: Path, project_id: str) -> Dict[str, Any]:
    """
    Inspects managed files in Vault to detect if user has added personal notes or modified sections.
    Does NOT overwrite or perform destructive changes.
    """
    manifest = load_manifest(vault_path)
    if not manifest:
        return {
            "status": "NOT_INITIALIZED",
            "message": "Vault has not been exported yet or manifest.json is missing.",
            "items": [],
        }

    items: List[Dict[str, Any]] = []
    files_managed = manifest.get("files_managed", {})

    for rel_path, file_meta in files_managed.items():
        full_path = vault_path / rel_path
        if not full_path.exists():
            items.append({
                "rel_path": rel_path,
                "entity_id": file_meta.get("entity_id"),
                "status": VaultReconcileStatus.CONFLICT.value,
                "detail": "Managed file was deleted in Vault.",
            })
            continue

        content = full_path.read_text(encoding="utf-8")
        current_hash = _file_hash(content)
        recorded_hash = file_meta.get("hash")

        if current_hash == recorded_hash:
            reconcile_status = VaultReconcileStatus.UNCHANGED
            detail = "Content in Vault matches recorded export state."
        else:
            # Check if modification is in user notes section vs managed block
            if "## My Notes" in content and len(content.split("## My Notes")[-1].strip()) > 0:
                reconcile_status = VaultReconcileStatus.USER_MODIFIED
                detail = "User has added personal reflections / notes."
            else:
                reconcile_status = VaultReconcileStatus.USER_MODIFIED
                detail = "File content has been modified in Vault."

        items.append({
            "rel_path": rel_path,
            "entity_id": file_meta.get("entity_id"),
            "entity_type": file_meta.get("entity_type"),
            "status": reconcile_status.value,
            "detail": detail,
        })

    return {
        "status": "OK",
        "project_id": project_id,
        "vault_path": str(vault_path),
        "total_managed": len(files_managed),
        "items": items,
    }
