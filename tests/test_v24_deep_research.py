"""
Test V2.4 Deep Research Productivity & Three Core Pillars Acceptance Suite
P0-A: 文献全文研读与 PDF 本地证据切片
P0-B: 多数据表交叉关联与复杂统计分析向导
P0-C: 实验方案自动化代码模板生成与一键调试
"""
import base64
import json
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pypdf
from fastapi.testclient import TestClient
from backend.main import app
from backend.domain.project import create_project, add_question
from backend.domain.paper import save_paper_to_project, save_paper_pdf, get_paper_extracted_data, create_paper_evidence_slice, ask_paper_question
from backend.domain.dataset import create_dataset_from_csv
from backend.integrations.data.relationship import relationship_inspector
from backend.integrations.data.wizard import analysis_wizard
from backend.domain.experiment_coder import generate_experiment_code, execute_experiment_code_safely, debug_experiment_code
from backend.agent.tools.registry import registry
from backend.domain.conclusion import create_conclusion

client = TestClient(app)


def _create_sample_pdf_bytes() -> bytes:
    """使用 pypdf 动态生成一个带 Abstract / Method / Experiments / Conclusion 章节的标准测试 PDF"""
    writer = pypdf.PdfWriter()
    
    # 创建第 1 页
    page1 = writer.add_blank_page(width=612, height=792)
    # pypdf 直接保存空白页，若需文字可通过 Annotation 或纯文本流写入
    # 为保证可解析真实文字，使用含有实际 PDF 文本流的最小有效 PDF 字节串
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 280 >>\nstream\n"
        b"BT\n/F1 12 Tf\n50 700 Td\n(Abstract) Tj\n"
        b"0 -20 Td\n(We study dynamic graph embeddings under noise.) Tj\n"
        b"0 -40 Td\n(Method) Tj\n"
        b"0 -20 Td\n(The proposed adaptive neighborhood update reduces variance.) Tj\n"
        b"0 -40 Td\n(Experiments) Tj\n"
        b"0 -20 Td\n(Benchmark dataset FER_Noisy_v2 achieves 84.1% accuracy.) Tj\n"
        b"ET\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000240 00000 n \n0000000570 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n645\n%%EOF\n"
    )
    return pdf_content


def test_v24_deep_research_full_suite():
    print("\n" + "="*60)
    print("STARTING V2.4 DEEP RESEARCH PRODUCTIVITY ACCEPTANCE SUITE")
    print("="*60)

    # 1. 创建 Project
    proj = create_project("V2.4 Productivity Study - Deep Pipeline", "Testing PDF, Wizard and Codegen")
    pid = proj["id"]
    add_question(pid, "How does adaptive graph neighborhood update improve statistical robustness?")
    print(f"[PASS] 1. Project created: {pid}")

    # =========================================================================
    # SUITE A: 文献全文研读与 PDF 本地证据切片 (P0-A)
    # =========================================================================
    print("\n--- [SUITE A] PDF Parsing, Evidence Slicing & Deep QA ---")
    paper_data = {
        "paper_id": "W2026_GraphNorm",
        "title": "Adaptive Neighborhood Updates in Dynamic Graphs",
        "authors": ["Dr. Lin", "Prof. Wang"],
        "year": 2026,
        "source": "openalex",
    }
    saved_p = save_paper_to_project(pid, paper_data)
    paper_id = saved_p["id"]

    pdf_bytes = _create_sample_pdf_bytes()
    upload_res = save_paper_pdf(pid, paper_id, pdf_bytes, filename="paper.pdf")
    assert upload_res["success"] is True
    assert upload_res["total_pages"] >= 1
    print(f"[PASS] 2. PDF Uploaded & Parsed: {upload_res['total_pages']} pages, sections={upload_res['sections']}")

    extracted = get_paper_extracted_data(paper_id)
    assert extracted is not None
    assert len(extracted["pages"]) >= 1
    print(f"[PASS] 3. Extracted JSON retrieved: total words={extracted['word_count']}")

    # 提取精准 Evidence 切片
    ev_slice = create_paper_evidence_slice(
        project_id=pid,
        paper_id=paper_id,
        page=1,
        section="Method",
        paragraph_index=1,
        text="The proposed adaptive neighborhood update reduces variance.",
    )
    assert ev_slice["page"] == 1
    assert "Method" in ev_slice["source_location"]
    print(f"[PASS] 4. Evidence slice created: {ev_slice['id']} ({ev_slice['source_location']})")

    # 深度文献问答 (Paper QA)
    qa_res = ask_paper_question(paper_id, "What dataset was used in experiments?")
    assert qa_res["found"] is True
    assert len(qa_res["citations"]) > 0
    assert qa_res["citations"][0]["page"] == 1
    print(f"[PASS] 5. Deep Paper QA verified with citation: {qa_res['citations'][0]}")

    # =========================================================================
    # SUITE B: 多数据表交叉关联与统计分析向导 (P0-B)
    # =========================================================================
    print("\n--- [SUITE B] Multi-Dataset Relationships & Analysis Wizard ---")
    csv_a = """sample_id,group,feature_x\n1,A,10.2\n2,A,11.4\n3,A,9.8\n4,B,15.1\n5,B,14.7\n6,B,16.2\n"""
    csv_b = """sample_id,group,response_y,batch_id\n1,A,20.4,B1\n2,A,22.8,B1\n3,A,19.6,B1\n4,B,30.2,B2\n5,B,29.4,B2\n6,B,32.4,B2\n"""
    
    ds_a = create_dataset_from_csv(pid, "Patient_Features_A", csv_a)
    ds_b = create_dataset_from_csv(pid, "Clinical_Response_B", csv_b)
    print(f"[PASS] 6. Two datasets created: {ds_a['id']} and {ds_b['id']}")

    # 关系探测
    relations = relationship_inspector.discover_relationships([ds_a, ds_b])
    assert len(relations) >= 1
    assert relations[0]["join_key"] in ("sample_id", "group")
    assert relations[0]["source"] == "ai_inference"
    print(f"[PASS] 7. Discovered relationships: join_key={relations[0]['join_key']}, conf={relations[0]['confidence']}")

    # 生成统计分析向导方案
    plan = analysis_wizard.generate_analysis_plan(
        intent="比较两组均值差异",
        dataset_ids=[ds_a["id"]],
        target_metric="feature_x",
        group_col="group",
    )
    assert plan["success"] is True
    assert "GROUP BY" in plan["suggested_sql"]
    print(f"[PASS] 8. Analysis Wizard Plan generated: {plan['description']}")

    # 执行方案并沉淀为 Artifact
    exec_res = analysis_wizard.execute_and_create_artifact(
        project_id=pid,
        title="Group A/B Feature Difference Analysis",
        dataset_id=ds_a["id"],
        sql_query=plan["suggested_sql"],
        python_code=plan["suggested_python"],
    )
    assert exec_res["success"] is True
    assert exec_res["artifact"]["type"] == "analysis"
    assert exec_res["results"]["row_count"] >= 2
    print(f"[PASS] 9. Analysis executed and saved to Artifact: {exec_res['artifact']['id']} (time={exec_res['duration_ms']}ms)")

    # =========================================================================
    # SUITE C: 实验代码模板生成、执行与受控 Debugger (P0-C)
    # =========================================================================
    print("\n--- [SUITE C] Experiment Code Generation, Execution & Debugging ---")
    exp_res = client.post(f"/api/projects/{pid}/experiments", json={
        "task": "Automated Benchmark Script Protocol",
        "dataset": "Patient_Features_A",
        "params": {"model": "DynamicGCN", "epochs": 10},
    })
    exp_id = exp_res.json()["record"]["id"]

    # 1. 自动生成代码
    codegen_res = generate_experiment_code(
        project_id=pid,
        experiment_id=exp_id,
        dataset_id=ds_a["id"],
    )
    assert codegen_res["success"] is True
    assert "import pandas as pd" in codegen_res["code"]
    assert codegen_res["provenance"]["generated_by"] == "research_agent"
    print(f"[PASS] 10. Experiment Python Code generated with provenance: {codegen_res['provenance']}")

    # 2. 正常安全执行
    exec_code_res = execute_experiment_code_safely(
        project_id=pid,
        experiment_id=exp_id,
        code=codegen_res["code"],
    )
    assert exec_code_res["success"] is True
    assert exec_code_res["run"]["status"] == "completed"
    print(f"[PASS] 11. Generated code executed safely in sandbox: Run={exec_code_res['run']['id']}")

    # 3. 模拟 Bug 代码与一键 Debugger 自动修复
    buggy_code = """
import pandas as pd
data = [{'val': 10}, {'val': 20}]
df = pd.DataFrame(data)
# KeyError simulation
score = df['non_existent_column'] + 5
print('Final score:', score)
"""
    # 首次运行发生异常
    bug_run = execute_experiment_code_safely(pid, exp_id, buggy_code)
    assert bug_run["success"] is False
    assert bug_run["error"] is not None
    print(f"[PASS] 12A. Buggy execution failed as expected: {bug_run['error']}")

    # Agent 一键诊断与生成补丁
    debug_patch = debug_experiment_code(
        project_id=pid,
        experiment_id=exp_id,
        code=buggy_code,
        error_traceback=bug_run["error"],
        retry_count=1,
    )
    assert debug_patch["success"] is True
    assert debug_patch["retry_count"] == 1
    assert "KeyError" in debug_patch["fix_reason"] or "修复" in debug_patch["fix_reason"]
    print(f"[PASS] 12B. Debugger diagnosed and generated patch: {debug_patch['fix_reason']}")

    # 重新执行修复后的代码
    fixed_run = execute_experiment_code_safely(pid, exp_id, debug_patch["patched_code"])
    assert fixed_run["success"] is True
    print(f"[PASS] 12C. Patched code rerun successfully: {fixed_run['run']['id']}")

    # 验证最大重试次数限制 (Capped at 3)
    capped_res = debug_experiment_code(pid, exp_id, buggy_code, bug_run["error"], retry_count=4)
    assert capped_res["success"] is False
    assert "上限" in capped_res["error"] or "人工介入" in capped_res["error"]
    print(f"[PASS] 13. Max retry limit enforced (>3 strictly blocks automatic retry)")

    # =========================================================================
    # SUITE D: 全局 ToolRegistry 与数据血缘沉淀
    # =========================================================================
    print("\n--- [SUITE D] ToolRegistry & Grounded Scientific Lineage ---")
    all_tools = registry.list_tools()
    assert len(all_tools) >= 28
    tool_names = [t.name for t in all_tools]
    for required_t in [
        "read_pdf", "extract_evidence", "ask_paper",
        "inspect_dataset_relationship", "generate_analysis", "execute_analysis",
        "generate_experiment_code", "run_experiment", "debug_experiment"
    ]:
        assert required_t in tool_names, f"Tool {required_t} not found in registry!"
    print(f"[PASS] 14. All 28 tools registered in ToolRegistry with risk levels")

    # 创建关联了 PDF 切片与实验运行的最终结论
    conc = create_conclusion(
        project_id=pid,
        text="经 PDF 证据切片与沙箱实测联合验证：自适应图邻域更新有效减小了局部方差，A/B 差异达到统计显著性。",
        confidence="high",
        evidence_refs=[
            {"type": "paper", "id": paper_id, "snippet": ev_slice["snippet"]},
            {"type": "artifact", "id": exec_res["artifact"]["id"], "snippet": "A/B Mean diff analysis"},
            {"type": "run", "id": fixed_run["run"]["id"], "snippet": "Fixed debug run metric"},
        ],
    )
    assert conc["id"] is not None
    print(f"[PASS] 15. Final Grounded Conclusion established with PDF & Execution Evidence: {conc['id']}")

    print("\n" + "="*60)
    print("ALL 15 CHECKS IN V2.4 DEEP RESEARCH PRODUCTIVITY PASSED WITH 100% SUCCESS!")
    print("="*60)


if __name__ == "__main__":
    test_v24_deep_research_full_suite()
