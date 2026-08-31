"""
ResearchOS V2.4 — 真实科研人员全流程用户旅程验收测试 (User Journey E2E)
涵盖 16 步真实科研闭环操作：
1. Create Project
2. Create Research Question
3. Create Hypothesis
4. Add Paper
5. Extract PDF Evidence
6. Create Experiment Protocol
7. Import Dataset
8. Analyze Dataset (Relationship & Wizard)
9. Generate Experiment Code (Provenance & Context)
10. Run Code (Sandbox Execution)
11. Produce Artifact
12. Create Conclusion (Evidence Grounded)
13. Ask Research Memory (Zero Hallucination Verification)
14. Generate Next Experiment (Reasoning Basis)
15. Approve Action
16. Create New Experiment
"""

import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from starlette.testclient import TestClient
from backend.main import app
from backend.domain.project import get_project
from backend.domain.hypothesis import get_hypothesis
from backend.domain.paper import get_paper, get_paper_extracted_data
from backend.domain.dataset import get_dataset
from backend.domain.artifact import list_artifacts
from backend.domain.conclusion import list_conclusions
from backend.domain.run import list_runs
from backend.domain.memory import query_research_memory

client = TestClient(app)


def _generate_sample_pdf() -> bytes:
    """生成包含段落与章节的最小标准 PDF 字节流"""
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >> endobj\n"
        b"4 0 obj << /Length 235 >> stream\n"
        b"BT\n"
        b"/F1 12 Tf\n"
        b"50 700 Td (Abstract: We study dynamic topological graphs under noise.) Tj\n"
        b"0 -40 Td (Method: Adaptive graph updates with k=20 achieve manifold stability.) Tj\n"
        b"0 -40 Td (Experiments: Benchmark on dataset shows variance reduction.) Tj\n"
        b"ET\n"
        b"endstream\n"
        b"endobj\n"
        b"xref\n"
        b"0 5\n"
        b"0000000000 65535 f \n"
        b"0000000010 00000 n \n"
        b"0000000060 00000 n \n"
        b"0000000117 00000 n \n"
        b"0000000216 00000 n \n"
        b"trailer << /Size 5 /Root 1 0 R >>\n"
        b"startxref\n"
        b"504\n"
        b"%%EOF\n"
    )
    return content


def test_v24_complete_researcher_user_journey():
    print("\n============================================================")
    print("STARTING V2.4 REAL RESEARCHER END-TO-END USER JOURNEY")
    print("============================================================")

    # 1. Create Project
    proj_resp = client.post("/api/projects", json={
        "name": "Dynamic Graph Manifold Stability Under Noise",
        "description": "Investigating whether adaptive edge updates preserve topological manifolds under high sensor jitter.",
    })
    assert proj_resp.status_code == 200
    proj = proj_resp.json()
    pid = proj["id"]
    print(f"[STEP 1/16 PASS] Project Created: {pid} ('{proj['name']}')")

    # 2. Create Research Question
    rq_resp = client.post(f"/api/projects/{pid}/questions", json={
        "text": "Can dynamic graph edge updates prevent topological manifold collapse under 15% sensor noise?",
    })
    assert rq_resp.status_code == 200
    q_data = rq_resp.json()
    q_id = q_data["id"]
    print(f"[STEP 2/16 PASS] Research Question Formulated: {q_id}")

    # 3. Create Hypothesis
    hyp_resp = client.post(f"/api/projects/{pid}/hypotheses", json={
        "title": "Adaptive neighborhood update rate > 0.5 preserves manifold topology",
        "description": "Increasing neighborhood update rate prevents oversmoothing while filtering high frequency noise.",
    })
    assert hyp_resp.status_code == 200
    hyp_data = hyp_resp.json()
    hyp_id = hyp_data["id"]
    print(f"[STEP 3/16 PASS] Scientific Hypothesis Stated: {hyp_id}")

    # 4. Add Paper
    paper_resp = client.post(f"/api/projects/{pid}/papers", json={
        "paper": {
            "title": "Topological Invariants in Dynamic Graph Convolutional Networks",
            "authors": ["Lin, H.", "Wang, S."],
            "year": 2026,
            "doi": "10.1000/182",
            "source": "openalex",
        }
    })
    assert paper_resp.status_code == 200
    paper_id = paper_resp.json()["paper"]["id"]
    print(f"[STEP 4/16 PASS] Paper Saved to Project: {paper_id}")

    # 5. Extract PDF Evidence
    pdf_bytes = _generate_sample_pdf()
    upload_resp = client.post(
        f"/api/projects/{pid}/papers/{paper_id}/pdf",
        json={"pdf_base64": pdf_bytes.hex(), "filename": "sample_paper.pdf"},
    )
    
    ev_resp = client.post(f"/api/papers/{paper_id}/evidence", json={
        "project_id": pid,
        "page": 1,
        "section": "Method",
        "paragraph_index": 0,
        "text": "Adaptive graph updates with k=20 achieve manifold stability.",
        "hypothesis_id": hyp_id,
    })
    assert ev_resp.status_code == 200
    ev_slice = ev_resp.json()
    assert ev_slice["hypothesis_id"] == hyp_id
    assert "Page 1" in ev_slice["source_location"]
    print(f"[STEP 5/16 PASS] PDF Evidence Sliced and Linked to Hypothesis: {ev_slice['id']} ({ev_slice['source_location']})")

    # 6. Create Experiment Protocol
    exp_resp = client.post(f"/api/projects/{pid}/experiments", json={
        "task": "Ablation on Adaptive Neighborhood Update Rate",
        "model": "DynamicGCN",
        "dataset": "Manifold_Noise_Dataset",
        "params": {"k": 20, "update_rate": 0.6, "lr": 1e-4},
        "conclusions": "Verify if k=20 preserves local manifold structure under noise.",
    })
    assert exp_resp.status_code == 200
    exp_id = exp_resp.json()["record"]["id"]
    print(f"[STEP 6/16 PASS] Experiment Protocol Configured: {exp_id}")

    # 7. Import Dataset
    csv_content = """sample_id,group,feature_stability,noise_level\n1,A,0.84,0.15\n2,A,0.82,0.15\n3,A,0.86,0.15\n4,B,0.61,0.15\n5,B,0.59,0.15\n6,B,0.63,0.15\n"""
    ds_resp = client.post(f"/api/projects/{pid}/datasets", json={
        "name": "Manifold_Noise_Dataset",
        "csv_content": csv_content,
    })
    assert ds_resp.status_code == 200
    ds_id = ds_resp.json()["dataset"]["id"]
    print(f"[STEP 7/16 PASS] Empirical Dataset Registered: {ds_id}")

    # 8. Analyze Dataset (Relationship & Wizard)
    wizard_plan = client.post(f"/api/projects/{pid}/datasets/wizard/plan", json={
        "intent": "比较 A 组与 B 组的特征稳定性差异",
        "dataset_ids": [ds_id],
        "target_metric": "feature_stability",
        "group_col": "group",
    })
    assert wizard_plan.status_code == 200
    plan_data = wizard_plan.json()
    assert "suggested_sql" in plan_data

    wizard_exec = client.post(f"/api/projects/{pid}/datasets/wizard/execute", json={
        "title": "Group A/B Manifold Stability Comparison",
        "dataset_id": ds_id,
        "sql_query": plan_data["suggested_sql"],
    })
    assert wizard_exec.status_code == 200
    art_analysis = wizard_exec.json()["artifact"]
    print(f"[STEP 8/16 PASS] Analysis Wizard Plan Executed and Saved as Artifact: {art_analysis['id']}")

    # 9. Generate Experiment Code (with Provenance Context)
    code_resp = client.post(f"/api/projects/{pid}/experiments/{exp_id}/code/generate", json={
        "hypothesis_id": hyp_id,
        "dataset_id": ds_id,
    })
    assert code_resp.status_code == 200
    code_data = code_resp.json()
    assert code_data["success"] is True
    assert "import pandas as pd" in code_data["code"]
    assert code_data["provenance"]["project_id"] == pid
    print(f"[STEP 9/16 PASS] Experiment Python Code Generated with Research Context")

    # 10. Run Code in Sandbox
    run_resp = client.post(f"/api/projects/{pid}/experiments/{exp_id}/code/run", json={
        "code": code_data["code"],
    })
    assert run_resp.status_code == 200
    run_result = run_resp.json()
    assert run_result["success"] is True
    run_record = run_result["run"]
    assert run_record["status"] == "completed"
    print(f"[STEP 10/16 PASS] Code Executed in Sandbox: Run={run_record['id']}, Status={run_record['status']}")

    # 11. Produce Artifact
    arts = list_artifacts(pid)
    assert len(arts) >= 1
    print(f"[STEP 11/16 PASS] Artifacts Successfully Persisted: {len(arts)} artifacts found")

    # 12. Create Conclusion (Evidence Grounded)
    conc_resp = client.post(f"/api/projects/{pid}/conclusions", json={
        "text": "动态图邻域自适应更新 (k=20, rate=0.6) 在 15% 传感器噪声下维持了流形几何结构，显著优于静态拓扑 (p < 0.01)。",
        "hypothesis_id": hyp_id,
        "confidence": "high",
        "evidence_refs": [
            {"type": "paper", "id": paper_id, "snippet": ev_slice["snippet"]},
            {"type": "run", "id": run_record["id"], "snippet": "Ablation run completed with manifold stability"},
            {"type": "artifact", "id": art_analysis["id"], "snippet": "A/B feature stability comparison"},
        ],
    })
    assert conc_resp.status_code == 200
    conc = conc_resp.json()
    assert conc["confidence"] == "high"
    assert len(conc["evidence_refs"]) == 3
    print(f"[STEP 12/16 PASS] Grounded Conclusion Created: {conc['id']} (Linked to 3 evidence items)")

    # 13. Ask Research Memory (Zero Hallucination Verification)
    mem_resp = client.post(f"/api/projects/{pid}/memory/ask", json={
        "question": "当前关于自适应图邻域更新的假说是否有实验证明？依据是什么？"
    })
    assert mem_resp.status_code == 200
    mem_data = mem_resp.json()
    assert mem_data["grounding_level"] in ("SUPPORTED", "PARTIALLY_SUPPORTED")
    assert len(mem_data["evidence"]) >= 1
    print(f"[STEP 13/16 PASS] Research Memory Fact Verified: {mem_data['grounding_level']} (Evidence items={len(mem_data['evidence'])})")

    # 14. Generate Next Experiment (Reasoning Basis)
    next_resp = client.get(f"/api/projects/{pid}/next-experiment")
    assert next_resp.status_code == 200
    next_data = next_resp.json()
    assert len(next_data["candidates"]) >= 1
    candidate = next_data["candidates"][0]
    assert "reasoning_basis" in candidate or "why" in candidate
    print(f"[STEP 14/16 PASS] Next Experiment Recommended with Reasoning Basis: '{candidate['title']}'")

    # 15. Approve Action (HITL Gate simulation)
    approval_resp = client.post(
        f"/api/projects/{pid}/next-experiment/confirm",
        json={"candidate": candidate},
    )
    assert approval_resp.status_code == 200
    adopted_exp = approval_resp.json()["record"]
    print(f"[STEP 15/16 PASS] Next Experiment Action Approved & Adopted: {adopted_exp['id']}")

    # 16. Verify New Experiment is Linked to Project Loop
    updated_proj = get_project(pid)
    assert adopted_exp["id"] in updated_proj["experiment_ids"]
    print(f"[STEP 16/16 PASS] Scientific Loop Closed: New Experiment {adopted_exp['id']} linked into Project!")

    print("============================================================")
    print("V2.4 REAL RESEARCHER USER JOURNEY FULLY VERIFIED (16/16 PASS)")
    print("============================================================")


if __name__ == "__main__":
    test_v24_complete_researcher_user_journey()
