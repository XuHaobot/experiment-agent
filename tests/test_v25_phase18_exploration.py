"""
Test Suite for ResearchOS V2.5 Phase 18 — Active Exploration Engine & Epistemic Pruning
Covers 17 comprehensive requirements:
1. Candidate Experiment Generation (Types A, B, C, D)
2. Candidate Ranking (Epistemic Value & Non-pseudo-exploration priority)
3. Information Gain
4. Uncertainty Reduction
5. Hypothesis Discrimination Matrix
6. Dynamic Explore / Exploit Balance
7. Duplicate Experiment & Pseudo-Exploration Detection
8. Epistemic Pruning Advisory
9. Failed Experiment Influence
10. Contradicting Evidence Influence
11. Human Approval Gate
12. Privacy Gateway verification
13. Research Graph Lineage
14. Artifact Lineage
15. Obsidian Export Compatibility
16. No Hallucinated Evidence Numbers
17. No Automatic Hypothesis Deletion
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
from backend.domain.project import create_project, add_question, add_experiment_to_project, get_project
from backend.domain.hypothesis import create_hypothesis, add_evidence, list_hypotheses, get_hypothesis
from backend.domain.run import create_run
from backend.domain.exploration import (
    CandidateType,
    detect_pseudo_exploration,
    generate_candidate_experiments,
    build_hypothesis_discrimination_matrix,
    analyze_epistemic_pruning,
    approve_candidate_experiment,
)
from backend.vault.exporter import export_project_to_vault
from backend.security.privacy_gateway import privacy_gateway
from src.storage import load_record, save_record, RECORDS_DIR

client = TestClient(app)


@pytest.fixture
def temp_vault_dir():
    temp_dir = tempfile.mkdtemp(prefix="obsidian_vault_test_p18_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def rich_exploration_project():
    """Setup project with diverse runs, hypotheses, evidence, and gaps"""
    proj = create_project("Active Exploration Graph Study", "Investigating topological graph limits.")
    pid = proj["id"]
    qid = add_question(pid, "What is the true mechanism behind topological performance degradation?")["id"]
    
    # Primary Hypothesis H1
    h1 = create_hypothesis(pid, "High-k graph convolution causes topological over-smoothing", "Over-smoothing hypothesis", question_id=qid)
    # Competing Hypothesis H2
    h2 = create_hypothesis(pid, "Performance drop is caused by fixed learning rate scaling mismatch", "LR mismatch hypothesis", question_id=qid)

    exp_id = "exp_active_01"
    save_record({
        "id": exp_id,
        "task": "Graph Topology Active Baseline",
        "project_id": pid,
        "params": {"original": {"k": 20, "lr": 1e-4}},
        "status": "completed",
    })
    add_experiment_to_project(pid, exp_id)

    # 1. High accuracy run at k=20
    r1 = create_run(exp_id, actual_parameters={"k": 20, "lr": 1e-4}, metrics={"val_accuracy": 0.92}, status="completed")
    # 2. Lower accuracy run at k=30
    r2 = create_run(exp_id, actual_parameters={"k": 30, "lr": 1e-4}, metrics={"val_accuracy": 0.78}, status="completed")
    # 3. Micro variations around k=20 to simulate saturated sampling
    r3 = create_run(exp_id, actual_parameters={"k": 19, "lr": 1e-4}, metrics={"val_accuracy": 0.91}, status="completed")
    r4 = create_run(exp_id, actual_parameters={"k": 21, "lr": 1e-4}, metrics={"val_accuracy": 0.915}, status="completed")
    # 4. Failed run
    r_fail = create_run(exp_id, actual_parameters={"k": 50, "lr": 1e-4}, metrics={}, status="failed")

    # Add contradicting evidence to H2
    add_evidence(h2["id"], source=r2["id"], text="k=30 dropped severely", supports=False)
    add_evidence(h2["id"], source=r_fail["id"], text="k=50 crashed execution", supports=False)

    return {
        "project_id": pid,
        "h1_id": h1["id"],
        "h2_id": h2["id"],
        "exp_id": exp_id,
        "run_ids": [r1["id"], r2["id"], r3["id"], r4["id"], r_fail["id"]],
    }


# =============================================================================
# TESTS
# =============================================================================

def test_01_candidate_experiment_generation_types(rich_exploration_project):
    pid = rich_exploration_project["project_id"]
    portfolio = generate_candidate_experiments(pid, max_candidates=4)
    
    assert portfolio["total_candidates"] >= 3
    types_found = {c["candidate_type"] for c in portfolio["candidates"]}
    
    # Must include at least EXPLOIT, DISCRIMINATE, EXPLORE, and/or REPLICATE
    assert CandidateType.EXPLORE.value in types_found
    assert CandidateType.DISCRIMINATE.value in types_found or CandidateType.EXPLOIT.value in types_found


def test_02_candidate_ranking_prioritizes_epistemic_value(rich_exploration_project):
    pid = rich_exploration_project["project_id"]
    portfolio = generate_candidate_experiments(pid)
    candidates = portfolio["candidates"]
    
    # Top ranked candidate should have HIGH or MEDIUM epistemic value
    assert candidates[0]["epistemic_value"] in ("HIGH", "MEDIUM")
    # Non-pseudo exploration should rank before pseudo exploration
    if len(candidates) > 1 and candidates[-1].get("is_pseudo_exploration"):
        assert not candidates[0].get("is_pseudo_exploration")


def test_03_information_gain_calculated(rich_exploration_project):
    pid = rich_exploration_project["project_id"]
    portfolio = generate_candidate_experiments(pid)
    for c in portfolio["candidates"]:
        assert c["expected_information_gain"] in ("HIGH", "MEDIUM", "LOW")


def test_04_uncertainty_reduction_stated(rich_exploration_project):
    pid = rich_exploration_project["project_id"]
    portfolio = generate_candidate_experiments(pid)
    for c in portfolio["candidates"]:
        assert len(c["uncertainty_reduction"]) > 10


def test_05_hypothesis_discrimination_matrix(rich_exploration_project):
    pid = rich_exploration_project["project_id"]
    res = build_hypothesis_discrimination_matrix(pid)
    
    assert len(res["hypotheses_evaluated"]) >= 2
    assert len(res["matrix"]) >= 1
    # Check that predictions exist for evaluated hypotheses
    first_row = res["matrix"][0]
    assert "predictions" in first_row
    assert "discrimination_power" in first_row


def test_06_dynamic_explore_exploit_balance(rich_exploration_project):
    pid = rich_exploration_project["project_id"]
    portfolio = generate_candidate_experiments(pid)
    bal = portfolio["recommended_balance"]
    
    # Because there are failed runs and contradicting runs, explore_weight should be elevated
    assert bal["explore_weight"] >= 0.50
    assert bal["exploit_weight"] <= 0.50
    assert "strategy" in bal


def test_07_duplicate_and_pseudo_exploration_detection():
    hist_runs = [
        {"id": "r1", "actual_parameters": {"k": 20, "lr": 1e-4}},
        {"id": "r2", "actual_parameters": {"k": 19, "lr": 1e-4}},
        {"id": "r3", "actual_parameters": {"k": 21, "lr": 1e-4}},
    ]
    
    # Exact duplicate
    is_p1, msg1 = detect_pseudo_exploration({"k": 20, "lr": 1e-4}, hist_runs)
    assert is_p1
    assert "完全一致" in msg1

    # Saturated neighborhood micro-variation (k=20.2 when 19, 20, 21 already exist)
    is_p2, msg2 = detect_pseudo_exploration({"k": 20.2, "lr": 1e-4}, hist_runs)
    assert is_p2
    assert "伪探索" in msg2

    # Genuinely unexplored space (k=45)
    is_p3, msg3 = detect_pseudo_exploration({"k": 45, "lr": 1e-4}, hist_runs)
    assert not is_p3


def test_08_epistemic_pruning_advisory(rich_exploration_project):
    pid = rich_exploration_project["project_id"]
    pruning = analyze_epistemic_pruning(pid)
    
    items = pruning["pruning_analysis"]
    assert len(items) >= 2
    
    h2_item = next(i for i in items if i["hypothesis_id"] == rich_exploration_project["h2_id"])
    # H2 has 2 contradicting evidence items
    assert h2_item["recommended_status"] == "WEAKENED"
    assert "建议降低" in h2_item["pruning_recommendation"] or "削弱" in h2_item["reason"]


def test_09_failed_experiment_influences_exploration(rich_exploration_project):
    pid = rich_exploration_project["project_id"]
    portfolio = generate_candidate_experiments(pid)
    
    # Exploration candidates should address or avoid the failed parameter region
    cand_params = [c["variables"] for c in portfolio["candidates"]]
    assert all(p.get("k") != 50 for p in cand_params)


def test_10_contradicting_evidence_influences_candidate_selection(rich_exploration_project):
    pid = rich_exploration_project["project_id"]
    portfolio = generate_candidate_experiments(pid)
    
    # Discriminate candidate exists to resolve contradiction
    types = [c["candidate_type"] for c in portfolio["candidates"]]
    assert CandidateType.DISCRIMINATE.value in types or CandidateType.EXPLORE.value in types


def test_11_human_approval_gate_creates_draft_experiment(rich_exploration_project):
    pid = rich_exploration_project["project_id"]
    portfolio = generate_candidate_experiments(pid)
    first_cand = portfolio["candidates"][0]
    
    res = approve_candidate_experiment(pid, first_cand["candidate_id"], first_cand)
    assert res["success"]
    exp_id = res["experiment_id"]
    
    # Verify experiment draft is saved on disk
    rec = load_record(RECORDS_DIR / f"{exp_id}.json")
    assert rec is not None
    assert rec["status"] == "draft"
    assert rec["project_id"] == pid
    assert rec["from_candidate_id"] == first_cand["candidate_id"]


def test_12_privacy_gateway_blocks_unauthorized_exploration_payloads():
    sensitive_payload = "confidential patient dna sequence patient_id: 10492"
    eval_res = privacy_gateway.evaluate_text(sensitive_payload, is_local_llm=True)
    assert eval_res.decision.value == "DENY"


def test_13_research_graph_lineage_of_approved_experiment(rich_exploration_project):
    pid = rich_exploration_project["project_id"]
    portfolio = generate_candidate_experiments(pid)
    cand = portfolio["candidates"][0]
    res = approve_candidate_experiment(pid, cand["candidate_id"], cand)
    exp_id = res["experiment_id"]
    
    proj = get_project(pid)
    assert exp_id in proj.get("experiment_ids", [])


def test_14_artifact_lineage_preserved(rich_exploration_project):
    pid = rich_exploration_project["project_id"]
    portfolio = generate_candidate_experiments(pid)
    cand = portfolio["candidates"][0]
    approve_candidate_experiment(pid, cand["candidate_id"], cand)
    
    # Check that portfolio metadata contains valid reasoning basis
    assert len(cand.get("reasoning_basis", [])) >= 1


def test_15_obsidian_export_with_exploration_candidates(rich_exploration_project, temp_vault_dir):
    pid = rich_exploration_project["project_id"]
    export_project_to_vault(pid, temp_vault_dir)
    
    # Obsidian vault manifests and folders must exist
    assert (temp_vault_dir / "02_Hypotheses").exists()
    assert (temp_vault_dir / "03_Experiments").exists()


def test_16_no_hallucinated_evidence_numbers():
    proj = create_project("Zero Baseline Study")
    portfolio = generate_candidate_experiments(proj["id"])
    
    # Must use qualitative HIGH/MEDIUM/LOW, never fabricated pseudo-exact probabilities like "94.82%"
    for c in portfolio["candidates"]:
        assert c["epistemic_value"] in ("HIGH", "MEDIUM", "LOW")
        assert c["expected_information_gain"] in ("HIGH", "MEDIUM", "LOW")


def test_17_no_automatic_hypothesis_deletion(rich_exploration_project):
    pid = rich_exploration_project["project_id"]
    pruning = analyze_epistemic_pruning(pid)
    
    for item in pruning["pruning_analysis"]:
        assert item["can_auto_delete"] is False
    
    # Ensure all hypotheses still exist in the database
    hyps_after = list_hypotheses(pid)
    assert len(hyps_after) >= 2
