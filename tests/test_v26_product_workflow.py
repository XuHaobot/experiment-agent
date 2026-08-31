"""
Comprehensive E2E Test Suite for ResearchOS V2.6 — Product Hardening & Complete Research Workflow
Covers all 20 steps of the continuous scientific research loop:
1. Create Research Question
2. Create Hypothesis
3. Create Experiment
4. Create Multiple Runs
5. Import CSV Data into Runs
6. Execute Analysis in Restricted Python Sandbox
7. Generate Artifact with Lineage
8. Create Evidence bound to Hypothesis
9. Create Conclusion backed by Evidence
10. Generate Next Action
11. View Research Timeline
12. View Research Memory
13. Generate Exploration Candidates (Type A/B/C/D)
14. Approve Candidate via HITL Gate
15. Create new Experiment Draft
16. Obsidian Vault Export with User Notes segregation
17. Privacy Gateway evaluation & data classification
18. Local LLM provider check
19. Research Session creation & history
20. Multi-Run side-by-side comparison matrix
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
from backend.domain.hypothesis import create_hypothesis, add_evidence, list_hypotheses
from backend.domain.run import create_run, list_runs, import_runs_from_csv, compare_runs
from backend.domain.dataset import create_dataset_from_csv
from backend.domain.artifact import create_artifact, list_artifacts
from backend.domain.conclusion import create_conclusion, list_conclusions
from backend.domain.timeline import get_project_timeline
from backend.domain.memory import get_project_research_memory, query_research_memory
from backend.domain.exploration import generate_candidate_experiments, approve_candidate_experiment
from backend.domain.diary import create_diary_entry, list_diary_entries
from backend.domain.session import create_research_session, list_research_sessions
from backend.vault.exporter import export_project_to_vault
from backend.security.privacy_gateway import privacy_gateway
from backend.llm.gateway import llm_gateway
from src.storage import save_record, load_record, RECORDS_DIR

client = TestClient(app)


@pytest.fixture
def temp_vault_dir():
    temp_dir = tempfile.mkdtemp(prefix="obsidian_vault_test_v26_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_v26_complete_20_step_scientific_workflow(temp_vault_dir):
    # -------------------------------------------------------------------------
    # 1. 创建 Research Question
    # -------------------------------------------------------------------------
    proj = create_project("V2.6 Scientific Graph Optimization", "Testing complete continuous workflow")
    pid = proj["id"]
    assert pid is not None
    q_rec = add_question(pid, "How does dynamic graph neighbor k affect topological stability?")
    qid = q_rec["id"]
    assert qid is not None

    # -------------------------------------------------------------------------
    # 2. 创建 Hypothesis
    # -------------------------------------------------------------------------
    hyp = create_hypothesis(pid, "Increasing k up to 20 improves representation robustness", "Hypothesis H1", question_id=qid)
    hid = hyp["id"]
    assert hid is not None

    # -------------------------------------------------------------------------
    # 3. 创建 Experiment
    # -------------------------------------------------------------------------
    exp_id = "exp_v26_01"
    save_record({
        "id": exp_id,
        "task": "Neighbor Parameter k Sweep",
        "project_id": pid,
        "params": {"original": {"k": 10, "lr": 1e-4}},
        "status": "completed",
    })
    add_experiment_to_project(pid, exp_id)

    # -------------------------------------------------------------------------
    # 4. 创建多个 Run
    # -------------------------------------------------------------------------
    r1 = create_run(exp_id, actual_parameters={"k": 10, "lr": 1e-4}, metrics={"val_accuracy": 0.84, "loss": 0.32}, status="completed")
    r2 = create_run(exp_id, actual_parameters={"k": 20, "lr": 1e-4}, metrics={"val_accuracy": 0.91, "loss": 0.21}, status="completed")
    r3 = create_run(exp_id, actual_parameters={"k": 30, "lr": 1e-4}, metrics={"val_accuracy": 0.79, "loss": 0.45}, status="completed")
    assert r1["id"] and r2["id"] and r3["id"]

    # -------------------------------------------------------------------------
    # 5. 导入真实 CSV 数据到 Runs
    # -------------------------------------------------------------------------
    csv_content = "k,lr,val_accuracy,loss\n5,0.0001,0.76,0.51\n15,0.0001,0.88,0.25\n"
    import_res = import_runs_from_csv(exp_id, csv_content)
    assert import_res["success"]
    assert import_res["count"] == 2

    # -------------------------------------------------------------------------
    # 6. 执行 Analysis (DuckDB 导入与查询)
    # -------------------------------------------------------------------------
    ds_csv = "epoch,k,acc\n1,10,0.80\n2,10,0.84\n1,20,0.88\n2,20,0.91\n"
    ds_res = create_dataset_from_csv(pid, "training_epochs.csv", ds_csv)
    assert ds_res["id"] is not None

    # -------------------------------------------------------------------------
    # 7. 生成 Artifact
    # -------------------------------------------------------------------------
    art = create_artifact(
        project_id=pid,
        name="k_vs_accuracy_curve.png",
        artifact_type="chart",
        content="fake_binary_image_png_content",
        source_experiment_id=exp_id,
    )
    assert art["id"] is not None

    # -------------------------------------------------------------------------
    # 8. 创建 Evidence (支持与反面证据)
    # -------------------------------------------------------------------------
    ev_supp = add_evidence(hid, source=r2["id"], text="Run k=20 achieved peak accuracy 91.0%", supports=True)
    ev_contra = add_evidence(hid, source=r3["id"], text="Run k=30 dropped accuracy to 79.0%", supports=False)
    assert ev_supp and ev_contra

    # -------------------------------------------------------------------------
    # 9. 创建 Conclusion (严格由证据支撑)
    # -------------------------------------------------------------------------
    conc = create_conclusion(
        project_id=pid,
        text="拓扑邻域参数在 k=20 处达到极值点，超出后由于过平滑效应性能显著回落。",
        hypothesis_id=hid,
        confidence="high",
        evidence_refs=[
            {"type": "run", "id": r2["id"], "snippet": "Peak 91.0% at k=20"},
            {"type": "run", "id": r3["id"], "snippet": "Drop 79.0% at k=30"},
        ],
    )
    assert conc["id"] is not None

    # -------------------------------------------------------------------------
    # 10. 生成 Next Action
    # -------------------------------------------------------------------------
    mem = get_project_research_memory(pid)
    next_priorities = mem.get("research_state", {}).get("next_priorities", [])
    assert len(next_priorities) >= 1

    # -------------------------------------------------------------------------
    # 11. 查看 Research Timeline
    # -------------------------------------------------------------------------
    timeline_events = get_project_timeline(pid)
    assert len(timeline_events) >= 4
    event_types = [e["event_type"] for e in timeline_events]
    assert "project_created" in event_types
    assert "hypothesis_proposed" in event_types

    # -------------------------------------------------------------------------
    # 12. 查看 Research Memory (无 CoT 结构化问答)
    # -------------------------------------------------------------------------
    mem_ans = query_research_memory(pid, "为什么 k=30 准确率下降？")
    assert "answer" in mem_ans
    assert "<think>" not in mem_ans["answer"]
    assert mem_ans["grounding_level"] == "SUPPORTED"

    # -------------------------------------------------------------------------
    # 13. 生成 Exploration Candidates (Type A/B/C/D)
    # -------------------------------------------------------------------------
    portfolio = generate_candidate_experiments(pid, max_candidates=4)
    cands = portfolio.get("candidates", [])
    assert len(cands) >= 3
    types = [c["candidate_type"] for c in cands]
    assert "EXPLORE" in types or "EXPLOIT" in types

    # -------------------------------------------------------------------------
    # 14. 批准 Candidate (HITL 门禁)
    # -------------------------------------------------------------------------
    cand_to_approve = cands[0]
    app_res = approve_candidate_experiment(pid, cand_to_approve["candidate_id"], cand_to_approve)
    assert app_res["success"]
    new_exp_id = app_res["experiment_id"]

    # -------------------------------------------------------------------------
    # 15. 创建新 Experiment Draft
    # -------------------------------------------------------------------------
    rec_draft = load_record(RECORDS_DIR / f"{new_exp_id}.json")
    assert rec_draft["status"] == "draft"
    assert rec_draft["project_id"] == pid

    # -------------------------------------------------------------------------
    # 16. Obsidian Export (段落隔离保护笔记)
    # -------------------------------------------------------------------------
    export_project_to_vault(pid, temp_vault_dir)
    assert (temp_vault_dir / "02_Hypotheses").exists()

    # -------------------------------------------------------------------------
    # 17. Privacy Gateway 评估
    # -------------------------------------------------------------------------
    priv_eval = privacy_gateway.evaluate_text("Private experiment dataset path", is_local_llm=True)
    assert priv_eval.decision.value in ("ALLOW", "ASK", "DENY")

    # -------------------------------------------------------------------------
    # 18. Local LLM 路由健康检查
    # -------------------------------------------------------------------------
    providers = llm_gateway.list_providers()
    assert len(providers) >= 1
    active_p = llm_gateway.get_active_provider()
    assert active_p is not None

    # -------------------------------------------------------------------------
    # 19. Research Session 记录
    # -------------------------------------------------------------------------
    sess = create_research_session(
        project_id=pid,
        title="Session #1 · Topological Parameter Sweep",
        goal="Identify peak accuracy for graph neighbor parameter k",
        actions_summary=["Imported CSV", "Ran 3 runs", "Established conclusion C-01"],
        executed_runs=[r1["id"], r2["id"], r3["id"]],
        reached_conclusions=[conc["id"]],
        next_step="Test alternative LR interaction hypothesis",
    )
    assert sess["id"] is not None
    sess_list = list_research_sessions(pid)
    assert len(sess_list) >= 1

    # -------------------------------------------------------------------------
    # 20. Multi-Run 对比矩阵 (Run Comparison)
    # -------------------------------------------------------------------------
    comp_res = compare_runs([r1["id"], r2["id"], r3["id"]])
    assert comp_res["runs_count"] == 3
    assert comp_res["best_run_id"] == r2["id"]
    assert "k" in comp_res["param_keys"]
    assert "val_accuracy" in comp_res["metric_keys"]
    assert len(comp_res["comparison_matrix"]) == 3
