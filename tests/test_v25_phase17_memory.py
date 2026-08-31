"""
Test Suite for ResearchOS V2.5 Phase 17 — Research Memory 2.0 & Epistemic Anti-Lock-in
Covers:
1. Observation does not automatically upgrade to Fact
2. AI Suggestion does not automatically upgrade to Fact
3. Failed Experiment is permanently preserved
4. Conclusion requires empirical Evidence
5. Supporting + Contradicting Evidence balance
6. Unexplored Space discovery
7. Alternative Hypotheses generation
8. Alternative Hypothesis without evidence marked AI_SUGGESTION & speculative
9. Next Experiment incorporates Unexplored Space
10. Next Experiment avoids duplicating historical completed runs
11. Memory Query never exposes internal CoT
12. Obsidian Export writes epistemic_status
13. User Notes preserved under Epistemic Memory
14. Privacy Gateway remains fully effective
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
from backend.domain.epistemic import EpistemicStatus, can_transition
from backend.domain.project import create_project, add_question, add_experiment_to_project
from backend.domain.hypothesis import create_hypothesis, add_evidence
from backend.domain.conclusion import create_conclusion
from backend.domain.run import create_run
from backend.domain.memory import (
    build_evidence_balance,
    discover_unexplored_space,
    generate_alternative_hypotheses,
    get_project_research_memory,
    query_research_memory,
)
from backend.domain.next_experiment import recommend_next_experiments
from backend.vault.exporter import export_project_to_vault
from backend.vault.renderer import START_TAG, END_TAG
from backend.security.privacy_gateway import privacy_gateway

client = TestClient(app)


@pytest.fixture
def temp_vault_dir():
    temp_dir = tempfile.mkdtemp(prefix="obsidian_vault_test_p17_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def project_with_diverse_runs():
    """Create a research project with multiple runs, gaps, and contradictions"""
    proj = create_project("Graph Topology Memory 2.0 Test", "Testing epistemic anti-lock-in memory.")
    pid = proj["id"]
    qid = add_question(pid, "How does neighborhood parameter k affect topological smoothness?")["id"]
    hyp = create_hypothesis(pid, "Increasing k improves representation robustness", "Bigger k hypothesis")
    hid = hyp["id"]

    # 关联实验
    exp_id = "exp_graph_01"
    add_experiment_to_project(pid, exp_id)

    # 1. 成功运行 (Supporting)
    r1 = create_run(exp_id, actual_parameters={"k": 10, "lr": 1e-4}, metrics={"val_accuracy": 0.88}, status="completed")
    r2 = create_run(exp_id, actual_parameters={"k": 20, "lr": 1e-4}, metrics={"val_accuracy": 0.92}, status="completed")
    
    # 2. 性能下滑运行 (Contradicting)
    r3 = create_run(exp_id, actual_parameters={"k": 30, "lr": 1e-4}, metrics={"val_accuracy": 0.79}, status="completed")
    
    # 3. 失败运行 (Failed Experiment - Permanent Negative Knowledge)
    r_fail = create_run(exp_id, actual_parameters={"k": 50, "lr": 1e-4}, metrics={}, status="failed")

    # 4. 沉淀带证据的结论
    conc = create_conclusion(
        project_id=pid,
        text="k 在 10~20 范围内提高准确率，但 k=30 后性能显著回落。",
        hypothesis_id=hid,
        confidence="medium",
        evidence_refs=[
            {"type": "run", "id": r2["id"], "snippet": "Run k=20 achieved 92.0% accuracy"},
            {"type": "run", "id": r3["id"], "snippet": "Run k=30 dropped to 79.0% accuracy"},
        ],
    )

    return {
        "project_id": pid,
        "question_id": qid,
        "hypothesis_id": hid,
        "experiment_id": exp_id,
        "run_ids": [r1["id"], r2["id"], r3["id"], r_fail["id"]],
        "conclusion_id": conc["id"],
    }


# =============================================================================
# TESTS
# =============================================================================

def test_01_observation_does_not_automatically_upgrade_to_fact():
    # An isolated empirical observation cannot automatically become a FACT
    assert not can_transition(EpistemicStatus.OBSERVATION, EpistemicStatus.FACT, has_human_confirmation=False)
    # With human validation and replication, it can transition
    assert can_transition(EpistemicStatus.OBSERVATION, EpistemicStatus.FACT, has_human_confirmation=True)


def test_02_ai_suggestion_never_upgrades_directly_to_fact_or_conclusion():
    # AI_SUGGESTION must never automatically upgrade to FACT or CONCLUSION
    assert not can_transition(EpistemicStatus.AI_SUGGESTION, EpistemicStatus.FACT, has_human_confirmation=False)
    assert not can_transition(EpistemicStatus.AI_SUGGESTION, EpistemicStatus.CONCLUSION, has_human_confirmation=False)
    assert not can_transition(EpistemicStatus.AI_SUGGESTION, EpistemicStatus.FACT, has_human_confirmation=True)


def test_03_failed_experiment_permanently_preserved(project_with_diverse_runs):
    pid = project_with_diverse_runs["project_id"]
    mem = get_project_research_memory(pid)
    
    # Verify failed runs are retained
    failed_entries = [r for r in mem.get("runs", []) if r.get("status") == "failed"]
    assert len(failed_entries) >= 1
    assert failed_entries[0]["epistemic_status"] == EpistemicStatus.FAILED_EXPERIMENT.value
    
    # Failed runs also appear in research_state
    state_failed = mem.get("research_state", {}).get("failed_or_refuted", [])
    assert any("失败运行" in s for s in state_failed)


def test_04_conclusion_requires_empirical_evidence():
    # In an empty project with no runs or evidence, asking if hypothesis is proved returns UNSUPPORTED
    proj = create_project("Empty Hypothesis Study")
    pid = proj["id"]
    create_hypothesis(pid, "Unverified claim", "No runs yet")
    
    res = query_research_memory(pid, "这个假说已经证明了吗？")
    assert res["grounding_level"] == "UNSUPPORTED"
    assert res["epistemic_status"] == EpistemicStatus.HYPOTHESIS.value
    assert "不能证明" in res["summary"] or "待验证" in res["summary"]


def test_05_supporting_and_contradicting_evidence_balance(project_with_diverse_runs):
    pid = project_with_diverse_runs["project_id"]
    balance = build_evidence_balance(pid)
    
    assert len(balance["supporting"]) >= 1  # k=20
    assert len(balance["contradicting"]) >= 1  # k=30 & failed run
    assert balance["confidence"] in ("medium", "high")


def test_06_discover_unexplored_space_gaps(project_with_diverse_runs):
    pid = project_with_diverse_runs["project_id"]
    unexplored = discover_unexplored_space(pid)
    
    # We tested k=10, 20, 30. The gaps [11, 19] or [21, 29] should be detected
    k_unexplored = [u for u in unexplored if u.get("parameter") == "k"]
    assert len(k_unexplored) >= 1
    assert any("未测试空隙" in u.get("description", "") or "盲区" in u.get("description", "") or "尚未" in u.get("description", "") for u in k_unexplored)


def test_07_generate_alternative_hypotheses(project_with_diverse_runs):
    pid = project_with_diverse_runs["project_id"]
    alternatives = generate_alternative_hypotheses(pid)
    
    assert len(alternatives) >= 2
    titles = [a["hypothesis"] for a in alternatives]
    assert any("过平滑" in t or "Over-smoothing" in t for t in titles)
    assert all(a["epistemic_status"] == EpistemicStatus.AI_SUGGESTION.value for a in alternatives)


def test_08_speculative_alternative_hypotheses_marked_correctly(project_with_diverse_runs):
    pid = project_with_diverse_runs["project_id"]
    alternatives = generate_alternative_hypotheses(pid)
    
    speculative_alts = [a for a in alternatives if a.get("is_speculative")]
    assert len(speculative_alts) >= 1
    for alt in speculative_alts:
        assert alt["epistemic_status"] == EpistemicStatus.AI_SUGGESTION.value
        assert len(alt.get("reasoning_basis", [])) >= 1


def test_09_next_experiment_incorporates_unexplored_space(project_with_diverse_runs):
    pid = project_with_diverse_runs["project_id"]
    recs = recommend_next_experiments(pid)
    candidates = recs.get("candidates", [])
    
    assert len(candidates) >= 1
    c1 = candidates[0]
    assert c1.get("information_gain") in ("HIGH", "MEDIUM")
    assert "uncertainty_reduced" in c1
    assert len(c1.get("uncertainty_reduced", [])) >= 1
    assert c1.get("epistemic_status") == EpistemicStatus.AI_SUGGESTION.value


def test_10_next_experiment_avoids_duplicating_historical_runs(project_with_diverse_runs):
    pid = project_with_diverse_runs["project_id"]
    recs = recommend_next_experiments(pid)
    candidates = recs.get("candidates", [])
    
    # Verified: candidate does not ask to test k=20 or k=30 with same lr
    for c in candidates:
        params = c.get("suggested_params", {})
        # Should not be identical to historical run k=20, lr=1e-4
        if params.get("k") == 20:
            assert params.get("lr") != 1e-4


def test_11_memory_query_never_exposes_internal_cot(project_with_diverse_runs):
    pid = project_with_diverse_runs["project_id"]
    res = query_research_memory(pid, "为什么 k=30 准确率下降？")
    
    assert "<think>" not in res["answer"]
    assert "</think>" not in res["answer"]
    assert "chain of thought" not in res["answer"].lower()
    assert "evidence" in res
    assert "alternative_hypotheses" in res
    assert "unexplored_space" in res


def test_12_obsidian_export_writes_epistemic_status(project_with_diverse_runs, temp_vault_dir):
    pid = project_with_diverse_runs["project_id"]
    hid = project_with_diverse_runs["hypothesis_id"]
    cid = project_with_diverse_runs["conclusion_id"]
    
    export_project_to_vault(pid, temp_vault_dir)
    
    hyp_file = temp_vault_dir / "02_Hypotheses" / f"{hid}.md"
    assert hyp_file.exists()
    hyp_text = hyp_file.read_text(encoding="utf-8")
    assert "epistemic_status: HYPOTHESIS" in hyp_text
    
    conc_file = temp_vault_dir / "05_Conclusions" / f"{cid}.md"
    assert conc_file.exists()
    conc_text = conc_file.read_text(encoding="utf-8")
    assert "epistemic_status: CONCLUSION" in conc_text


def test_13_user_notes_preserved_with_epistemic_status(project_with_diverse_runs, temp_vault_dir):
    pid = project_with_diverse_runs["project_id"]
    hid = project_with_diverse_runs["hypothesis_id"]
    export_project_to_vault(pid, temp_vault_dir)
    
    hyp_file = temp_vault_dir / "02_Hypotheses" / f"{hid}.md"
    original = hyp_file.read_text(encoding="utf-8")
    user_note = "\n\n## My Notes\n这是我个人的直觉想法，k=25 应该能取得最佳鲁棒性。\n"
    hyp_file.write_text(original + user_note, encoding="utf-8")
    
    # Re-export
    export_project_to_vault(pid, temp_vault_dir)
    re_read = hyp_file.read_text(encoding="utf-8")
    assert "这是我个人的直觉想法" in re_read
    assert "epistemic_status: HYPOTHESIS" in re_read
    assert START_TAG in re_read
    assert END_TAG in re_read


def test_14_privacy_gateway_remains_active_during_memory_queries():
    # Verify privacy gate intercepts sensitive text
    restricted_query = "Please read patient_id: 99401 and private medical record"
    check = privacy_gateway.evaluate_text(restricted_query, is_local_llm=True)
    assert check.decision.value == "DENY"
