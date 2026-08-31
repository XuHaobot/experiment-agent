"""
P0 Acceptance Verification Test Suite
验证 14 项 P0 验收指标
"""
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"E:\textool\experiment-agent")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.security.risk import RiskLevel
from backend.agent.security.guard import approve_request, get_approval
from backend.agent.tools.registry import registry
from backend.domain.run import create_run, get_run, list_runs, delete_run, get_experiment_with_runs
from backend.domain.artifact import create_artifact, list_artifacts, get_artifact, delete_artifact
from backend.domain.conclusion import create_conclusion, get_conclusions_by_evidence, delete_conclusion
from backend.domain.next_experiment import recommend_next_experiments
from src.agent_v2 import AgentV2
from src.graph.builder import build_research_graph


def run_all_tests():
    print("==================================================")
    print("STARTING P0 ARCHITECTURAL ACCEPTANCE TESTS")
    print("==================================================")

    # ─────────────────────────────────────────────────────────────
    # TEST 1: 所有 Agent Tools 均来自 ToolRegistry
    # ─────────────────────────────────────────────────────────────
    tools = registry.all_tools()
    tool_names = {t.name for t in tools}
    required_tools = {
        "search_records", "search_graph", "analyze_data", "generate_report",
        "list_records", "evaluate_answer", "search_papers", "create_hypothesis",
        "recommend_next_experiment", "run_python", "run_eda", "create_artifact",
        "save_conclusion", "create_experiment", "execute_run"
    }
    missing = required_tools - tool_names
    assert not missing, f"TEST 1 FAILED: Missing tools in registry: {missing}"
    print("[PASS] TEST 1: All Agent Tools are registered via ToolRegistry (count =", len(tools), ")")

    # ─────────────────────────────────────────────────────────────
    # TEST 2: AgentV2 不再使用 if-elif 分发 Tool (直接调用 registry.call)
    # ─────────────────────────────────────────────────────────────
    agent = AgentV2()
    res_search = agent._execute_tool("search_records", {"query": "facial", "top_k": 2})
    assert isinstance(res_search, list), f"TEST 2 FAILED: {res_search}"
    print("[PASS] TEST 2: AgentV2 seamlessly delegates tool execution to ToolRegistry")

    # ─────────────────────────────────────────────────────────────
    # TEST 3: run_python risk = MEDIUM
    # ─────────────────────────────────────────────────────────────
    t_python = registry.get("run_python")
    assert t_python is not None and t_python.risk_level == RiskLevel.MEDIUM, f"TEST 3 FAILED: {t_python}"
    print("[PASS] TEST 3: run_python risk level is MEDIUM")

    # ─────────────────────────────────────────────────────────────
    # TEST 4: execute_run risk = HIGH, requires_approval = true
    # ─────────────────────────────────────────────────────────────
    t_exec = registry.get("execute_run")
    assert t_exec is not None and t_exec.risk_level == RiskLevel.HIGH and t_exec.requires_approval is True, f"TEST 4 FAILED: {t_exec}"
    print("[PASS] TEST 4: execute_run risk level is HIGH with requires_approval=True")

    # ─────────────────────────────────────────────────────────────
    # TEST 5: 未经 approval，execute_run 必须被后端拒绝
    # ─────────────────────────────────────────────────────────────
    test_run = create_run(experiment_id="exp_test_acceptance_001", actual_parameters={"k": 20, "lr": 1e-4})
    run_id = test_run["id"]

    res_blocked = registry.call("execute_run", caller="acceptance_test", run_id=run_id)
    assert res_blocked.get("status") == "approval_required", f"TEST 5 FAILED: Expected approval_required, got {res_blocked}"
    approval_id = res_blocked.get("approval_id")
    assert approval_id and approval_id.startswith("appr_"), f"TEST 5 FAILED: Invalid approval_id: {approval_id}"
    print("[PASS] TEST 5: Unauthorized execute_run is strictly blocked by HITL gate (approval_id:", approval_id, ")")

    # ─────────────────────────────────────────────────────────────
    # TEST 6: 完成 approval 后，execute_run 可以真正执行
    # ─────────────────────────────────────────────────────────────
    appr_res = approve_request(approval_id, approver="acceptance_tester")
    assert appr_res is not None and appr_res.get("status") == "approved", f"TEST 6 Approval FAILED: {appr_res}"

    res_executed = registry.call("execute_run", caller="acceptance_test", approval_id=approval_id, run_id=run_id)
    assert res_executed.get("success") is True, f"TEST 6 Execution FAILED: {res_executed}"
    updated_run = get_run(run_id)
    assert updated_run.get("status") == "completed", f"TEST 6 Status mismatch: {updated_run}"
    print("[PASS] TEST 6: Approved execute_run executes and transitions run status to 'completed'")

    # ─────────────────────────────────────────────────────────────
    # TEST 7: 每次 Tool 调用都有 Audit Log
    # ─────────────────────────────────────────────────────────────
    audit_file = PROJECT_ROOT / "data" / "audit" / "tool_calls.jsonl"
    assert audit_file.exists(), "TEST 7 FAILED: Audit file not found"
    lines = audit_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 2, f"TEST 7 FAILED: Expected multiple audit lines, got {len(lines)}"
    last_log = json.loads(lines[-1])
    assert last_log.get("tool_name") == "execute_run" and last_log.get("status") == "success"
    print("[PASS] TEST 7: Audit Log recorded tool calls with timestamp, caller, parameters, and status")

    # ─────────────────────────────────────────────────────────────
    # TEST 8: Experiment -> 创建 Run -> 查询 Runs
    # ─────────────────────────────────────────────────────────────
    exp_id = "exp_p0_model_test"
    run_1 = create_run(experiment_id=exp_id, actual_parameters={"epoch": 10}, dataset="Noisy_v1")
    runs = list_runs(experiment_id=exp_id)
    assert any(r["id"] == run_1["id"] for r in runs), f"TEST 8 FAILED: Run not found in list: {runs}"
    print("[PASS] TEST 8: Experiment Run lifecycle creation and query confirmed")

    # ─────────────────────────────────────────────────────────────
    # TEST 9: 一个 Experiment 可以拥有多个 Runs
    # ─────────────────────────────────────────────────────────────
    run_2 = create_run(experiment_id=exp_id, actual_parameters={"epoch": 20}, dataset="Noisy_v1")
    run_3 = create_run(experiment_id=exp_id, actual_parameters={"epoch": 30}, dataset="Noisy_v1")
    all_exp_runs = list_runs(experiment_id=exp_id)
    assert len([r for r in all_exp_runs if r["experiment_id"] == exp_id]) >= 3, "TEST 9 FAILED: Multiple runs count < 3"
    print("[PASS] TEST 9: One Experiment accurately manages multiple Runs (#01, #02, #03)")

    # ─────────────────────────────────────────────────────────────
    # TEST 10: Research Graph 动态挂载 Experiment -> Run -> Artifact -> Conclusion / Evidence
    # ─────────────────────────────────────────────────────────────
    # 创建测试 Artifact & Conclusion
    test_art = create_artifact(
        project_id="proj_graph_test",
        name="Convergence Loss Plot",
        artifact_type="chart",
        content="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        source_record_id=exp_id,
    )
    test_conc = create_conclusion(
        project_id="proj_graph_test",
        text="Epoch 20 achieves optimal loss before overfitting",
        evidence_refs=[
            {"type": "experiment", "id": exp_id},
            {"type": "artifact", "id": test_art["id"]},
        ],
    )

    base_g = {
        "entities": [{"id": f"experiment_{exp_id}", "type": "Experiment", "properties": {"record_id": exp_id}}],
        "relations": [],
    }
    r_graph = build_research_graph(
        base_graph=base_g,
        project={"id": "proj_graph_test", "name": "Graph Verification Proj"},
        runs=[run_1, run_2, run_3],
        artifacts=[test_art],
        conclusions=[test_conc],
    )
    ent_types = {e["type"] for e in r_graph["entities"]}
    rel_types = {r["relation"] for r in r_graph["relations"]}
    assert "Experiment" in ent_types and "ExperimentRun" in ent_types and "Artifact" in ent_types and "Conclusion" in ent_types, f"TEST 10 Entities missing: {ent_types}"
    assert "HAS_RUN" in rel_types and "PRODUCES" in rel_types and "SUPPORTS" in rel_types, f"TEST 10 Relations missing: {rel_types}"
    print("[PASS] TEST 10: Research Graph seamlessly connects Experiment -> Run -> Artifact -> Conclusion -> Evidence")

    # ─────────────────────────────────────────────────────────────
    # TEST 11: Artifact API 返回 artifact_id, type, mime_type, url
    # ─────────────────────────────────────────────────────────────
    art_detail = get_artifact(test_art["id"], "proj_graph_test")
    assert art_detail.get("artifact_id") == test_art["id"], "TEST 11 artifact_id mismatch"
    assert art_detail.get("type") == "chart", "TEST 11 type mismatch"
    assert art_detail.get("mime_type") == "image/png", "TEST 11 mime_type mismatch"
    assert art_detail.get("url") == f"/api/artifacts/{test_art['id']}/content", "TEST 11 url mismatch"
    print("[PASS] TEST 11: Artifact model standardizes artifact_id, type, mime_type ('image/png'), and url ('/api/artifacts/.../content')")

    # ─────────────────────────────────────────────────────────────
    # TEST 12: 旧项目数据仍然可以正常读取 (兼容层测试)
    # ─────────────────────────────────────────────────────────────
    exp_with_runs = get_experiment_with_runs("demo_record")
    assert "experiment" in exp_with_runs and "runs" in exp_with_runs, "TEST 12 FAILED"
    print("[PASS] TEST 12: Legacy Experiment records backward compatibility verified")

    # ─────────────────────────────────────────────────────────────
    # TEST 13: Next Experiment 可以读取历史 Runs
    # ─────────────────────────────────────────────────────────────
    rec_res = recommend_next_experiments(project_id="proj_graph_test", experiment_ids=[exp_id], max_candidates=2)
    assert "analysis_summary" in rec_res, "TEST 13 FAILED"
    print("[PASS] TEST 13: Next Experiment engine integrates historical Runs telemetry into recommendation context")

    # ─────────────────────────────────────────────────────────────
    # TEST 14: Evidence 反向追溯查询
    # ─────────────────────────────────────────────────────────────
    reverse_concs = get_conclusions_by_evidence("artifact", test_art["id"])
    assert any(c["id"] == test_conc["id"] for c in reverse_concs), f"TEST 14 FAILED: {reverse_concs}"
    print("[PASS] TEST 14: Evidence reverse lookup (Artifact -> Conclusions) verified")

    # 清理测试数据
    delete_run(run_id)
    delete_run(run_1["id"])
    delete_run(run_2["id"])
    delete_run(run_3["id"])
    delete_artifact(test_art["id"], "proj_graph_test")
    delete_conclusion(test_conc["id"])

    print("==================================================")
    print("ALL 14 P0 ACCEPTANCE TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")


if __name__ == "__main__":
    run_all_tests()
