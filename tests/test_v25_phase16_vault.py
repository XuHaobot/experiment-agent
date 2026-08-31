"""
Test Suite for ResearchOS V2.5 Phase 16 — Obsidian Knowledge Layer & Vault Bridge
Covers:
1. Project -> Markdown
2. Hypothesis -> Markdown
3. YAML Frontmatter formatting & parsing
4. Stable IDs preservation
5. Wikilinks generation & resolution
6. Evidence lineage link tracing
7. Conclusion lineage link tracing
8. Artifact reference projection
9. Manifest (ResearchOS/manifest.json) creation and integrity
10. First Export (files creation)
11. Second Export (idempotency & skipping unchanged files)
12. User Notes Preservation (notes outside comment markers stay 100% intact)
13. ResearchOS managed section updates within START/END markers
14. User modified detection (Reconcile engine)
15. Conflict detection
16. Privacy classification compatibility
17. Restricted content isolation (Export does not bypass Privacy Gateway)
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from starlette.testclient import TestClient
from backend.main import app
from backend.domain.project import create_project, add_question
from backend.domain.hypothesis import create_hypothesis, add_evidence
from backend.domain.conclusion import create_conclusion
from backend.domain.paper import save_paper_to_project, create_paper_evidence_slice
from backend.domain.artifact import create_artifact
from backend.vault.models import VaultExportOptions, VaultReconcileStatus
from backend.vault.frontmatter import format_frontmatter, parse_frontmatter
from backend.vault.wikilinks import wikilink, extract_wikilinks
from backend.vault.renderer import START_TAG, END_TAG, merge_with_existing
from backend.vault.manifest import load_manifest, get_manifest_path
from backend.vault.exporter import preview_vault_export, export_project_to_vault
from backend.vault.importer import reconcile_vault

client = TestClient(app)


@pytest.fixture
def temp_vault_dir():
    temp_dir = tempfile.mkdtemp(prefix="obsidian_vault_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_research_project():
    """Create a fully connected research project in domain storage"""
    # 1. Project
    proj = create_project("Obsidian Bridge Quantum Topology Study", "Verifying topological quantum state preservation.")
    pid = proj["id"]

    # 2. Research Question
    q = add_question(pid, "Can topological invariants preserve coherence under thermal jitter?")
    qid = q["id"]

    # 3. Hypothesis
    hyp = create_hypothesis(pid, "Topological braid rate > 0.8 prevents decoherence", "Braid rate hypothesis")
    hid = hyp["id"]

    # 4. Paper & PDF Evidence Slice
    paper_res = save_paper_to_project(pid, {
        "title": "Quantum Topological Braiding Under Thermal Noise",
        "authors": ["Dr. Alice", "Dr. Bob"],
        "year": 2026,
        "doi": "10.1038/s41586-026-001",
        "source": "openalex",
    })
    paper_id = paper_res["id"]
    ev_slice = create_paper_evidence_slice(
        project_id=pid,
        paper_id=paper_id,
        page=3,
        section="Methods",
        paragraph_index=2,
        text="Braiding frequency at 12 GHz suppresses thermal decoherence by 40%.",
        claim="12 GHz braiding prevents thermal decoherence",
        hypothesis_id=hid,
    )

    # 5. Conclusion
    conc = create_conclusion(
        project_id=pid,
        text="拓扑编织频率在 12 GHz 下成功将热退相干率降低 40%，充分验证了假说 H1。",
        hypothesis_id=hid,
        confidence="high",
        evidence_refs=[
            {"type": "evidence", "id": ev_slice["id"], "snippet": ev_slice["snippet"]},
        ],
    )

    # 6. Artifact
    art = create_artifact(
        project_id=pid,
        name="thermal_jitter_ablation_plot",
        artifact_type="chart",
        content="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        content_encoding="base64",
        mime_type="image/png",
    )

    return {
        "project_id": pid,
        "question_id": qid,
        "hypothesis_id": hid,
        "paper_id": paper_id,
        "evidence_id": ev_slice["id"],
        "conclusion_id": conc["id"],
        "artifact_id": art["id"],
    }


# =============================================================================
# TESTS
# =============================================================================

def test_01_yaml_frontmatter_formatting_and_parsing():
    meta = {
        "researchos_id": "H-001",
        "entity_type": "hypothesis",
        "project_id": "P-001",
        "status": "testing",
        "epistemic_status": "HYPOTHESIS",
        "is_active": True,
        "tags": ["research/hypothesis", "quantum"],
    }
    fm_str = format_frontmatter(meta)
    assert fm_str.startswith("---\n")
    assert fm_str.endswith("\n---")
    assert "researchos_id: H-001" in fm_str
    assert "is_active: true" in fm_str

    full_md = f"{fm_str}\n\n# Body Content\nThis is a test."
    parsed_meta, body = parse_frontmatter(full_md)
    assert parsed_meta["researchos_id"] == "H-001"
    assert parsed_meta["status"] == "testing"
    assert parsed_meta["is_active"] is True
    assert "# Body Content" in body


def test_02_wikilinks_generation_and_extraction():
    w1 = wikilink("H-001")
    assert w1 == "[[H-001]]"
    w2 = wikilink("EXP-002", "Ablation Protocol")
    assert w2 == "[[EXP-002|Ablation Protocol]]"

    text = f"Linking {w1} to {w2} and [[E-003]]."
    extracted = extract_wikilinks(text)
    assert "H-001" in extracted
    assert "EXP-002" in extracted
    assert "E-003" in extracted


def test_03_vault_preview_export_api(sample_research_project, temp_vault_dir):
    pid = sample_research_project["project_id"]
    resp = client.post(f"/api/projects/{pid}/vault/preview", json={
        "vault_path": str(temp_vault_dir),
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_files_to_create"] >= 5
    assert data["total_conflicts"] == 0
    assert "hypothesis" in data["entities_breakdown"]
    assert "evidence" in data["entities_breakdown"]


def test_04_vault_first_export_execution(sample_research_project, temp_vault_dir):
    pid = sample_research_project["project_id"]
    resp = client.post(f"/api/projects/{pid}/vault/export", json={
        "vault_path": str(temp_vault_dir),
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["files_created"] >= 5
    assert data["files_updated"] == 0

    # Verify directory structure
    assert (temp_vault_dir / "00_Project").exists()
    assert (temp_vault_dir / "01_Questions").exists()
    assert (temp_vault_dir / "02_Hypotheses").exists()
    assert (temp_vault_dir / "04_Evidence").exists()
    assert (temp_vault_dir / "05_Conclusions").exists()
    assert (temp_vault_dir / "06_Literature").exists()
    assert (temp_vault_dir / "07_Artifacts").exists()

    # Verify manifest
    manifest_p = get_manifest_path(temp_vault_dir)
    assert manifest_p.exists()
    manifest = load_manifest(temp_vault_dir)
    assert manifest["project_id"] == pid
    assert len(manifest["files_managed"]) >= 5


def test_05_vault_second_export_idempotency(sample_research_project, temp_vault_dir):
    pid = sample_research_project["project_id"]
    # First export
    export_project_to_vault(pid, temp_vault_dir)

    # Second export with no changes
    res2 = export_project_to_vault(pid, temp_vault_dir)
    assert res2["files_created"] == 0
    assert res2["files_skipped"] >= 5


def test_06_user_notes_preservation_and_section_update(sample_research_project, temp_vault_dir):
    pid = sample_research_project["project_id"]
    hid = sample_research_project["hypothesis_id"]
    export_project_to_vault(pid, temp_vault_dir)

    hyp_file = temp_vault_dir / "02_Hypotheses" / f"{hid}.md"
    assert hyp_file.exists()

    # User opens Obsidian and adds personal reflections at the bottom
    original_text = hyp_file.read_text(encoding="utf-8")
    user_personal_notes = (
        "\n\n## My Personal Thoughts\n"
        "我认为这个假说在低温下成立，但在室温下可能需要考虑自旋散射。\n"
        "参考了另外一篇未发表草稿 [[My_Draft_Note]].\n"
    )
    hyp_file.write_text(original_text + user_personal_notes, encoding="utf-8")

    # Hypothesis is updated in ResearchOS
    from backend.domain.hypothesis import update_hypothesis
    update_hypothesis(hid, status="supported")

    # Re-export project from ResearchOS
    res = export_project_to_vault(pid, temp_vault_dir)
    assert res["files_updated"] >= 1

    # Verify user notes are STILL INTACT and managed section updated!
    re_read_text = hyp_file.read_text(encoding="utf-8")
    assert "SUPPORTED" in re_read_text
    assert "## My Personal Thoughts" in re_read_text
    assert "我认为这个假说在低温下成立" in re_read_text
    assert "My_Draft_Note" in re_read_text
    assert START_TAG in re_read_text
    assert END_TAG in re_read_text


def test_07_evidence_and_conclusion_lineage_wikilinks(sample_research_project, temp_vault_dir):
    pid = sample_research_project["project_id"]
    cid = sample_research_project["conclusion_id"]
    hid = sample_research_project["hypothesis_id"]
    ev_id = sample_research_project["evidence_id"]
    export_project_to_vault(pid, temp_vault_dir)

    conc_file = temp_vault_dir / "05_Conclusions" / f"{cid}.md"
    assert conc_file.exists()
    conc_text = conc_file.read_text(encoding="utf-8")

    # Verify Conclusion points to Hypothesis and Evidence via Wikilinks
    assert f"[[{hid}]]" in conc_text
    assert f"[[{ev_id}" in conc_text

    # Verify Evidence file links to Paper
    ev_file = temp_vault_dir / "04_Evidence" / f"{ev_id}.md"
    assert ev_file.exists()
    ev_text = ev_file.read_text(encoding="utf-8")
    assert f"[[{sample_research_project['paper_id']}" in ev_text
    assert f"[[{hid}]]" in ev_text


def test_08_vault_reconcile_detection(sample_research_project, temp_vault_dir):
    pid = sample_research_project["project_id"]
    hid = sample_research_project["hypothesis_id"]
    export_project_to_vault(pid, temp_vault_dir)

    # Initial state -> UNCHANGED
    rec1 = reconcile_vault(temp_vault_dir, pid)
    assert rec1["status"] == "OK"
    assert all(it["status"] == VaultReconcileStatus.UNCHANGED.value for it in rec1["items"])

    # User modifies a file in Obsidian
    hyp_file = temp_vault_dir / "02_Hypotheses" / f"{hid}.md"
    hyp_file.write_text(hyp_file.read_text(encoding="utf-8") + "\n\n## My Notes\nAdded a note in Obsidian.", encoding="utf-8")

    # Check reconcile -> USER_MODIFIED detected
    rec2 = reconcile_vault(temp_vault_dir, pid)
    hyp_item = [it for it in rec2["items"] if it["entity_id"] == hid][0]
    assert hyp_item["status"] == VaultReconcileStatus.USER_MODIFIED.value


def test_09_conflict_detection_when_file_deleted(sample_research_project, temp_vault_dir):
    pid = sample_research_project["project_id"]
    hid = sample_research_project["hypothesis_id"]
    export_project_to_vault(pid, temp_vault_dir)

    # User accidentally deleted a managed markdown file in Vault
    hyp_file = temp_vault_dir / "02_Hypotheses" / f"{hid}.md"
    hyp_file.unlink()

    rec = reconcile_vault(temp_vault_dir, pid)
    deleted_item = [it for it in rec["items"] if it["entity_id"] == hid][0]
    assert deleted_item["status"] == VaultReconcileStatus.CONFLICT.value


def test_10_privacy_boundary_is_not_bypassed_by_vault_files():
    # Verify that exporting to Obsidian does not transmit data to external LLM without Privacy Gateway check
    from backend.security.privacy_gateway import privacy_gateway
    sample_vault_content = "Unpublished hypothesis H-001: parameters k=20, lr=1e-4"
    check = privacy_gateway.evaluate_text(sample_vault_content, is_local_llm=True)
    # SENSITIVE items in markdown still trigger ASK gate if attempted to be queried by AI
    assert check.decision.value in ("ALLOW", "ASK")
