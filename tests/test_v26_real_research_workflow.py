"""
V2.6 Final Stabilization Test Suite — Real Researcher Workflow & AI-Agnostic Validation
Simulates the authentic 20-step end-to-end journey of a researcher using external AI (Codex/Claude),
local/remote GPU execution, Quick Capture, and offline data persistence without mandatory local LLMs.
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
from backend.domain.run import create_run, list_runs, import_runs_from_csv, compare_runs, get_run
from backend.domain.artifact import create_artifact, list_artifacts
from backend.domain.conclusion import create_conclusion, list_conclusions
from backend.domain.timeline import get_project_timeline
from backend.domain.diary import create_diary_entry, list_diary_entries
from backend.domain.session import create_research_session, list_research_sessions, generate_external_prompt
from backend.vault.exporter import export_project_to_vault
from backend.security.privacy_gateway import privacy_gateway
from src.storage import save_record, load_record, RECORDS_DIR

client = TestClient(app)


@pytest.fixture
def temp_vault_dir():
    temp_dir = tempfile.mkdtemp(prefix="obsidian_vault_final_v26_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_v26_real_research_workflow_full_journey(temp_vault_dir):
    # -------------------------------------------------------------------------
    # Step 1: Create Project
    # -------------------------------------------------------------------------
    proj = create_project("3D Point Cloud DGCNN Aggregation Study", "Exploring k-NN graph topological stability on single RTX 4090")
    pid = proj["id"]
    assert pid is not None

    # -------------------------------------------------------------------------
    # Step 2: Create Research Question
    # -------------------------------------------------------------------------
    q_rec = add_question(pid, "Does increasing k in Dynamic Graph CNN alleviate or aggravate over-smoothing?")
    qid = q_rec["id"]
    assert qid is not None

    # -------------------------------------------------------------------------
    # Step 3: Create Hypothesis (8-tier epistemic state)
    # -------------------------------------------------------------------------
    hyp = create_hypothesis(
        project_id=pid,
        title="Higher k causes node feature homogenization past k=20",
        description="Past k=20, Laplacian eigenvalues collapse leading to feature indistinguishability",
        question_id=qid
    )
    hid = hyp["id"]
    assert hid is not None
    assert hyp["status"] == "pending"

    # -------------------------------------------------------------------------
    # Step 4: Create Experiment Protocol
    # -------------------------------------------------------------------------
    exp_id = f"exp_dgcnn_{pid[:8]}"
    save_record({
        "id": exp_id,
        "task": "Neighbor k Sweep (k=10,20,25,30)",
        "project_id": pid,
        "params": {"original": {"k": 20, "lr": 1e-4, "arch": "DGCNN"}},
        "status": "completed",
    })
    add_experiment_to_project(pid, exp_id)

    # -------------------------------------------------------------------------
    # Step 5: Start Research Session (Quick Capture / AI Tool usage)
    # -------------------------------------------------------------------------
    sess = create_research_session(
        project_id=pid,
        title="Session #1 · DGCNN Aggregation Modification with Codex",
        goal="Test residual connections to break over-smoothing bottleneck",
        what_i_did="Used OpenAI Codex to modify aggregation layer with initial residual mapping",
        tools_used=["OpenAI Codex", "PyTorch 2.4", "NVIDIA RTX 4090"],
        what_happened="Model trained for 100 epochs, accuracy improved from 82.4% to 85.6%",
        what_surprised_me="Residual connection maintained high gradient norms at k=25",
        current_belief="Initial residual allows larger k without manifold collapse",
        ai_tool_used="Codex",
        git_commit="a82f31c",
        updated_hypotheses=[hid],
        next_step="Sweep k=25 with scaled learning rates",
    )
    assert sess["id"] is not None

    # -------------------------------------------------------------------------
    # Step 6: Record External AI Usage via API
    # -------------------------------------------------------------------------
    qc_res = client.post(f"/api/projects/{pid}/quick-capture", json={
        "title": "Codex Refactor of EdgeConv Layer",
        "what_i_did": "Asked Codex to implement dense skip connections",
        "what_happened": "Validation loss dropped by 18%",
        "what_surprised_me": "Memory overhead increased by only 4%",
        "ai_tool_used": "Codex",
        "git_commit": "b93e42d",
        "linked_hypothesis_id": hid
    })
    assert qc_res.status_code == 200
    assert qc_res.json()["success"]

    # -------------------------------------------------------------------------
    # Step 7: Import CSV Data from External 4090 Runs
    # -------------------------------------------------------------------------
    csv_data = "k,lr,val_accuracy,loss,runtime_sec\n10,0.0001,0.824,0.182,1420\n20,0.0001,0.856,0.138,1580\n30,0.0001,0.841,0.165,1890\n"
    import_res = import_runs_from_csv(exp_id, csv_data)
    assert import_res["success"]
    assert import_res["count"] == 3

    # -------------------------------------------------------------------------
    # Step 8: Create Experiment Run with execution_origin & Git lineage
    # -------------------------------------------------------------------------
    r_ext = create_run(
        experiment_id=exp_id,
        actual_parameters={"k": 25, "lr": 1e-4, "residual": True},
        metrics={"val_accuracy": 0.912, "loss": 0.098},
        status="completed",
        execution_origin="CODEX",
        git_commit="a82f31c",
        git_branch="feat/residual-dgcnn",
        repository="https://github.com/lab/dgcnn-topology",
        ai_tool_used="Codex",
        ai_task_description="Added Initial Residual Mapping to EdgeConv"
    )
    assert r_ext["id"] is not None
    assert r_ext["execution_origin"] == "CODEX"
    assert r_ext["git_commit"] == "a82f31c"

    # -------------------------------------------------------------------------
    # Step 9: Verify Run Comparison Matrix
    # -------------------------------------------------------------------------
    runs = list_runs(exp_id)
    r_ids = [r["id"] for r in runs]
    comp = compare_runs(r_ids)
    assert comp["runs_count"] >= 4
    assert comp["best_run_id"] == r_ext["id"]
    assert "k" in comp["param_keys"]
    assert "val_accuracy" in comp["metric_keys"]

    # -------------------------------------------------------------------------
    # Step 10: Generate Artifact with Lineage
    # -------------------------------------------------------------------------
    art = create_artifact(
        project_id=pid,
        name="accuracy_vs_k_curve.png",
        artifact_type="chart",
        content="mock_png_binary_data",
        source_experiment_id=exp_id,
    )
    assert art["id"] is not None

    # -------------------------------------------------------------------------
    # Step 11: Create Evidence bound to Hypothesis
    # -------------------------------------------------------------------------
    ev_pos = add_evidence(hid, source=r_ext["id"], text="Run k=25 with residual achieved peak 91.2% accuracy", supports=True)
    assert ev_pos is not None

    # -------------------------------------------------------------------------
    # Step 12: Update Conclusion backed by Empirical Evidence
    # -------------------------------------------------------------------------
    conc = create_conclusion(
        project_id=pid,
        text="残差连接有效抑制了高阶特征过平滑，将极值拐点从 k=20 成功推移至 k=25 (达到 91.2% 准确率)。",
        hypothesis_id=hid,
        confidence="high",
        evidence_refs=[
            {"type": "run", "id": r_ext["id"], "snippet": "Peak 91.2% at k=25 (Commit a82f31c)"}
        ]
    )
    assert conc["id"] is not None

    # -------------------------------------------------------------------------
    # Step 13: Record Research Diary (USER_BELIEF)
    # -------------------------------------------------------------------------
    diary_rec = create_diary_entry(
        project_id=pid,
        title="关于残差缓解拉普拉斯退化的直觉记录",
        content="残差直接保留了未被平滑的初始流形特征，这说明过平滑本质是谱能量向低频单极点聚集的问题。",
        tags=["intuition", "manifold", "laplacian"]
    )
    assert diary_rec["id"] is not None

    # -------------------------------------------------------------------------
    # Step 14: Generate External Prompt Bridge for Next Codex Session
    # -------------------------------------------------------------------------
    prompt_res = generate_external_prompt(pid, hid)
    assert prompt_res["success"]
    assert "a82f31c" in prompt_res["prompt_text"] or "k=25" in prompt_res["prompt_text"] or "最优运行" in prompt_res["prompt_text"]

    # -------------------------------------------------------------------------
    # Step 15: End Session / List Sessions
    # -------------------------------------------------------------------------
    sess_list = list_research_sessions(pid)
    assert len(sess_list) >= 2

    # -------------------------------------------------------------------------
    # Step 16: View Unified Research Timeline
    # -------------------------------------------------------------------------
    timeline_events = get_project_timeline(pid)
    assert len(timeline_events) >= 5
    evt_types = [e["event_type"] for e in timeline_events]
    assert "project_created" in evt_types
    assert "hypothesis_proposed" in evt_types
    assert "session_recorded" in evt_types
    assert "diary_logged" in evt_types

    # -------------------------------------------------------------------------
    # Step 17: Export to Obsidian Vault (Segregation Test)
    # -------------------------------------------------------------------------
    export_project_to_vault(pid, temp_vault_dir)
    assert (temp_vault_dir / "02_Hypotheses").exists()
    assert (temp_vault_dir / "05_Conclusions").exists()

    # -------------------------------------------------------------------------
    # Step 18 & 19: Verify All Data Persists across Reload
    # -------------------------------------------------------------------------
    persisted_proj = get_project(pid)
    assert persisted_proj["name"] == "3D Point Cloud DGCNN Aggregation Study"
    persisted_hyps = list_hypotheses(pid)
    assert len(persisted_hyps) >= 1
    persisted_runs = list_runs(exp_id)
    assert len(persisted_runs) >= 4
    persisted_concs = list_conclusions(pid)
    assert len(persisted_concs) >= 1
    persisted_diary = list_diary_entries(pid)
    assert len(persisted_diary) >= 1

    # -------------------------------------------------------------------------
    # Step 20: Verify Privacy Gateway Blocks Sensitive & Restricted Secrets
    # -------------------------------------------------------------------------
    priv_eval = privacy_gateway.evaluate_text("api_key = 'sk-live-secret-lab-access-key-99999'", is_local_llm=False)
    assert priv_eval.decision.value == "DENY"
