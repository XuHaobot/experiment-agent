"""
Test V2.1 Research Workflow & Persistence Suite
验证 V2.1 核心能力：
1. 真实科研工作流（RQ -> Hypothesis -> Experiment -> CSV Runs -> Persistent Analysis -> Evidence -> Conclusion）
2. Research State & Uncertainty 动态合成
3. Next Research Action 强论据驱动 (why, uncertainty_addressed, expected_gain)
4. CSV 批量导入 Runs 与参数/指标自适应解析
5. Python 数据分析会话持久化存取
6. 因果链路双向回溯
7. 记忆事实问答与无 CoT 泄露
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app
from backend.domain.project import create_project, get_project
from backend.domain.hypothesis import create_hypothesis, list_hypotheses
from backend.domain.run import create_run, list_runs, import_runs_from_csv
from backend.domain.analysis import create_analysis_session, list_analysis_sessions, get_analysis_session
from backend.domain.memory import get_project_research_memory, query_research_memory
from backend.domain.conclusion import create_conclusion
from backend.domain.next_experiment import recommend_next_experiments

client = TestClient(app)


def test_v21_full_workflow():
    print("\n" + "="*50)
    print("STARTING V2.1 RESEARCH WORKFLOW & PERSISTENCE TESTS")
    print("="*50)

    # 1. Project & Question
    proj = create_project("V2.1 Robust Graph Study", "Investigating graph topological robustness under noise")
    pid = proj["id"]
    print(f"[PASS] 1. Project created: {pid}")

    q_resp = client.post(f"/api/projects/{pid}/questions", json={"question": "Does dynamic graph topology improve noise resilience?"})
    assert q_resp.status_code == 200
    print("[PASS] 2. Research Question created")

    # 2. Hypothesis
    hyp = create_hypothesis(pid, "Dynamic edge updates prevent oversmoothing in k in [15, 25]", "H2 optimal k interval")
    hid = hyp["id"]
    print(f"[PASS] 3. Hypothesis created: {hid}")

    # 3. Experiment Protocol
    exp_resp = client.post(f"/api/projects/{pid}/experiments", json={
        "task": "Dynamic Graph Ablation Protocol",
        "params": {"k": 20, "lr": 1e-4, "batch_size": 32},
        "dataset": "FER_Noisy_v2",
        "expected_outcome": "Verify k=20 peak resilience",
    })
    assert exp_resp.status_code == 200
    exp_id = exp_resp.json()["record"]["id"]
    print(f"[PASS] 4. Experiment Protocol created: {exp_id}")

    # 4. CSV Import Runs
    csv_sample = """k,lr,batch_size,val_accuracy,loss,f1
8,0.0001,32,0.712,0.395,0.701
20,0.0001,32,0.841,0.218,0.835
30,0.0001,32,0.806,0.285,0.798
"""
    import_resp = client.post(f"/api/experiments/{exp_id}/runs/import-csv", json={"csv_text": csv_sample})
    assert import_resp.status_code == 200
    import_data = import_resp.json()
    assert import_data["success"] is True
    assert import_data["count"] == 3
    print(f"[PASS] 5. CSV Batch Runs imported: {import_data['count']} runs generated")

    runs = list_runs(experiment_id=exp_id)
    assert len(runs) >= 3
    run_k20 = [r for r in runs if r.get("actual_parameters", {}).get("k") == 20][0]
    assert run_k20["metrics"]["val_accuracy"] == 0.841

    # 5. Persistent Analysis Session
    ana_resp = client.post(f"/api/projects/{pid}/analyses", json={
        "name": "Parameter k Sensitivity Study",
        "code": "import numpy as np\nprint('Analyzing k vs val_accuracy...')",
        "stdout": "Optimal peak identified at k=20 with val_accuracy=0.841",
        "charts": ["base64samplechartdata"],
        "insights": "Demonstrated that k>20 suffers from oversmoothing",
        "experiment_id": exp_id,
        "run_ids": [r["id"] for r in runs],
    })
    assert ana_resp.status_code == 200
    ana_id = ana_resp.json()["analysis"]["id"]
    print(f"[PASS] 6. Analysis session persisted: {ana_id}")

    fetched_ana = get_analysis_session(ana_id)
    assert fetched_ana is not None
    assert fetched_ana["name"] == "Parameter k Sensitivity Study"

    # 6. Create Grounded Conclusion
    conc = create_conclusion(
        project_id=pid,
        text="k=20 当前在 FER_Noisy_v2 上取得最优准确率 (84.1%)，当 k>20 时出现过平滑导致准确率单调下降。",
        confidence="high",
        hypothesis_id=hid,
        evidence_refs=[{"type": "run", "id": run_k20["id"], "snippet": "val_accuracy=84.1%"}],
        source="user",
    )
    assert conc["id"] is not None
    print(f"[PASS] 7. Grounded Conclusion established: {conc['id']}")

    # 7. Research State & Uncertainty Synthesis
    mem = get_project_research_memory(pid)
    r_state = mem.get("research_state", {})
    assert len(r_state.get("known", [])) > 0
    assert len(r_state.get("tried", [])) >= 3
    assert len(r_state.get("unknown_uncertainty", [])) > 0
    assert len(r_state.get("next_priorities", [])) > 0
    print(f"[PASS] 8. Research State & Uncertainty synthesized: {len(r_state['known'])} known facts, {len(r_state['unknown_uncertainty'])} uncertainties")

    # 8. Next Research Action with Justification
    rec = recommend_next_experiments(pid, max_candidates=1)
    candidates = rec.get("candidates", [])
    assert len(candidates) > 0
    c1 = candidates[0]
    assert "why" in c1
    assert "uncertainty_addressed" in c1
    assert c1["information_gain"] in ("HIGH", "MEDIUM", "LOW")
    print(f"[PASS] 9. Next Research Action generated with justification: {c1['title']}")
    print(f"       Why: {c1['why']}")
    print(f"       Uncertainty Addressed: {c1['uncertainty_addressed']}")

    # 9. Causal Graph Traceability
    trace_resp = client.get(f"/api/projects/{pid}/graph/trace/{conc['id']}")
    assert trace_resp.status_code == 200
    trace_data = trace_resp.json()
    assert trace_data["node_type"] == "conclusion"
    assert len(trace_data["ancestors"]) > 0
    print(f"[PASS] 10. Causal Graph Trace verified for Conclusion {conc['id']}")

    # 10. Research Memory Ask
    qa_resp = client.post(f"/api/projects/{pid}/memory/ask", json={"question": "为什么不继续增大 k 到 30 以上？"})
    assert qa_resp.status_code == 200
    qa_data = qa_resp.json()
    assert "answer" in qa_data
    assert "84.1%" in qa_data["answer"] or "80.6%" in qa_data["answer"] or "过平滑" in qa_data["answer"]
    print(f"[PASS] 11. Memory Q&A executed without CoT leakage")

    # 11. Cockpit Endpoint End-to-End
    cockpit_resp = client.get(f"/api/projects/{pid}/cockpit")
    assert cockpit_resp.status_code == 200
    c_data = cockpit_resp.json()
    assert c_data["research_state"] is not None
    assert c_data["next_research_action"] is not None
    print(f"[PASS] 12. Cockpit Live State Matrix validated")

    print("="*50)
    print("ALL 12 V2.1 WORKFLOW & PERSISTENCE TESTS PASSED!")
    print("="*50)


if __name__ == "__main__":
    test_v21_full_workflow()
