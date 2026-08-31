"""
Obsidian Vault Exporter & Preview Engine
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.domain.artifact import list_artifacts
from backend.domain.conclusion import list_conclusions
from backend.domain.hypothesis import list_hypotheses
from backend.domain.paper import list_project_papers
from backend.domain.project import get_project
from backend.domain.run import list_runs
from src.storage import RECORDS_DIR
from backend.vault.manifest import (
    create_initial_manifest,
    load_manifest,
    save_manifest,
)
from backend.vault.models import (
    VaultExportOptions,
    VaultFileAction,
    VaultPreviewSummary,
)
from backend.vault.renderer import (
    START_TAG,
    merge_with_existing,
    render_artifact,
    render_conclusion,
    render_evidence,
    render_experiment,
    render_hypothesis,
    render_paper,
    render_project,
    render_question,
)


def _file_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _load_experiment_record(eid: str) -> Optional[Dict[str, Any]]:
    p = RECORDS_DIR / f"{eid}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _collect_project_entities(project_id: str) -> Dict[str, Any]:
    """Collect all domain objects associated with the project"""
    project = get_project(project_id)
    if not project:
        raise ValueError(f"Project '{project_id}' not found.")

    questions = project.get("questions", [])
    hypotheses = list_hypotheses(project_id)
    
    experiment_ids = project.get("experiment_ids", [])
    experiments = []
    runs_by_exp = {}
    for eid in experiment_ids:
        exp = _load_experiment_record(eid)
        if exp:
            experiments.append(exp)
            runs_by_exp[eid] = list_runs(experiment_id=eid)

    papers = list_project_papers(project_id) or []
    conclusions = list_conclusions(project_id) or []
    artifacts = list_artifacts(project_id) or []

    # Collect all evidence items from hypotheses and papers
    evidence_items = []
    seen_ids = set()
    for hyp in hypotheses:
        for ev in hyp.get("evidence", []):
            if isinstance(ev, dict) and ev.get("id"):
                eid = ev.get("id")
                if eid not in seen_ids:
                    seen_ids.add(eid)
                    ev_copy = dict(ev)
                    ev_copy["hypothesis_id"] = hyp.get("id")
                    evidence_items.append(ev_copy)

    for p in papers:
        for ev in p.get("evidence_slices", []):
            if isinstance(ev, dict) and ev.get("id"):
                eid = ev.get("id")
                if eid not in seen_ids:
                    seen_ids.add(eid)
                    evidence_items.append(ev)

    for conc in conclusions:
        for ref in conc.get("evidence_refs", []):
            if isinstance(ref, dict) and ref.get("id"):
                eid = ref.get("id")
                if eid not in seen_ids:
                    seen_ids.add(eid)
                    evidence_items.append({
                        "id": eid,
                        "type": ref.get("type", "evidence"),
                        "source_type": ref.get("type", "evidence"),
                        "source_id": eid,
                        "snippet": ref.get("snippet", ""),
                        "hypothesis_id": conc.get("hypothesis_id"),
                        "created_at": conc.get("created_at"),
                    })

    return {
        "project": project,
        "questions": questions,
        "hypotheses": hypotheses,
        "experiments": experiments,
        "runs_by_exp": runs_by_exp,
        "papers": papers,
        "evidence": evidence_items,
        "conclusions": conclusions,
        "artifacts": artifacts,
    }


def _plan_markdown_files(
    entities: Dict[str, Any],
    options: VaultExportOptions,
) -> List[Tuple[str, str, Dict[str, Any], str]]:
    """
    Generate list of (rel_path, entity_type, frontmatter_meta, managed_body)
    """
    plans = []
    proj = entities["project"]
    pid = proj["id"]
    fm = options.folder_mapping

    # 1. Project
    if "project" in options.include_entities:
        meta, body = render_project(proj)
        rel_path = f"{fm['project']}/{pid}.md"
        plans.append((rel_path, "project", meta, body))

    # 2. Questions
    if "question" in options.include_entities:
        for q in entities["questions"]:
            qid = q.get("id")
            meta, body = render_question(q, pid)
            rel_path = f"{fm['question']}/{qid}.md"
            plans.append((rel_path, "question", meta, body))

    # 3. Hypotheses
    if "hypothesis" in options.include_entities:
        for hyp in entities["hypotheses"]:
            hid = hyp.get("id")
            linked_ev = [ev for ev in entities["evidence"] if ev.get("hypothesis_id") == hid]
            linked_exp = [exp for exp in entities["experiments"] if hid in exp.get("hypothesis_ids", []) or hid == exp.get("hypothesis_id")]
            meta, body = render_hypothesis(hyp, linked_ev, linked_exp)
            rel_path = f"{fm['hypothesis']}/{hid}.md"
            plans.append((rel_path, "hypothesis", meta, body))

    # 4. Experiments
    if "experiment" in options.include_entities:
        for exp in entities["experiments"]:
            eid = exp.get("id")
            runs = entities["runs_by_exp"].get(eid, [])
            meta, body = render_experiment(exp, runs)
            rel_path = f"{fm['experiment']}/{eid}.md"
            plans.append((rel_path, "experiment", meta, body))

    # 5. Evidence
    if "evidence" in options.include_entities:
        seen_ev_ids = set()
        for ev in entities["evidence"]:
            ev_id = ev.get("id")
            if not ev_id or ev_id in seen_ev_ids:
                continue
            seen_ev_ids.add(ev_id)
            meta, body = render_evidence(ev)
            rel_path = f"{fm['evidence']}/{ev_id}.md"
            plans.append((rel_path, "evidence", meta, body))

    # 6. Conclusions
    if "conclusion" in options.include_entities:
        for conc in entities["conclusions"]:
            cid = conc.get("id")
            meta, body = render_conclusion(conc)
            rel_path = f"{fm['conclusion']}/{cid}.md"
            plans.append((rel_path, "conclusion", meta, body))

    # 7. Literature
    if "literature" in options.include_entities:
        for paper in entities["papers"]:
            paper_id = paper.get("id")
            p_ev = [ev for ev in entities["evidence"] if ev.get("paper_id") == paper_id or ev.get("source_id") == paper_id]
            meta, body = render_paper(paper, p_ev)
            safe_p_id = paper_id.replace("/", "_").replace(":", "_")
            rel_path = f"{fm['literature']}/{safe_p_id}.md"
            plans.append((rel_path, "literature", meta, body))

    # 8. Artifacts
    if "artifact" in options.include_entities:
        for art in entities["artifacts"]:
            aid = art.get("id")
            meta, body = render_artifact(art)
            rel_path = f"{fm['artifact']}/{aid}.md"
            plans.append((rel_path, "artifact", meta, body))

    return plans


def preview_vault_export(
    project_id: str,
    vault_path: Path,
    options: Optional[VaultExportOptions] = None,
) -> VaultPreviewSummary:
    """Preview actions without modifying the filesystem"""
    opts = options or VaultExportOptions()
    entities = _collect_project_entities(project_id)
    plans = _plan_markdown_files(entities, opts)

    summary = VaultPreviewSummary(
        project_id=project_id,
        vault_path=str(vault_path),
    )

    for rel_path, entity_type, meta, body in plans:
        summary.entities_breakdown[entity_type] = summary.entities_breakdown.get(entity_type, 0) + 1
        full_path = vault_path / rel_path

        if not full_path.exists():
            action = "create"
            has_user_notes = False
            summary.total_files_to_create += 1
            reason = "New entity markdown file to be generated."
        else:
            existing_content = full_path.read_text(encoding="utf-8")
            has_user_notes = "## My Notes" in existing_content or not existing_content.endswith(f"{START_TAG}\n{body.strip()}\n{END_TAG}\n")
            action = "update"
            summary.total_files_to_update += 1
            reason = "File exists; ResearchOS managed section will be updated, user notes preserved."

        summary.file_actions.append(
            VaultFileAction(
                rel_path=rel_path,
                action=action,
                entity_type=entity_type,
                entity_id=meta.get("researchos_id", ""),
                has_user_notes=has_user_notes,
                reason=reason,
            )
        )

    return summary


def export_project_to_vault(
    project_id: str,
    vault_path: Path,
    options: Optional[VaultExportOptions] = None,
) -> Dict[str, Any]:
    """Execute safe export into target Obsidian Vault directory"""
    opts = options or VaultExportOptions()
    entities = _collect_project_entities(project_id)
    plans = _plan_markdown_files(entities, opts)

    vault_path.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(vault_path) or create_initial_manifest(project_id)

    files_created = 0
    files_updated = 0
    files_skipped = 0

    for rel_path, entity_type, meta, managed_body in plans:
        full_path = vault_path / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        existing_text = full_path.read_text(encoding="utf-8") if full_path.exists() else None
        merged_md = merge_with_existing(meta, managed_body, existing_text)

        # Check if content changed
        if existing_text is not None and existing_text == merged_md:
            files_skipped += 1
        else:
            full_path.write_text(merged_md, encoding="utf-8")
            if existing_text is None:
                files_created += 1
            else:
                files_updated += 1

        # Track in manifest
        eid = meta.get("researchos_id", "")
        if eid and eid not in manifest["entities"].get(entity_type, []):
            manifest["entities"].setdefault(entity_type, []).append(eid)
        manifest["files_managed"][rel_path] = {
            "entity_type": entity_type,
            "entity_id": eid,
            "hash": _file_hash(merged_md),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    manifest["exported_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_manifest(vault_path, manifest)

    return {
        "success": True,
        "project_id": project_id,
        "vault_path": str(vault_path),
        "files_created": files_created,
        "files_updated": files_updated,
        "files_skipped": files_skipped,
        "total_managed": len(manifest["files_managed"]),
        "exported_at": manifest["exported_at"],
    }
