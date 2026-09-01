"""
Unit Tests for Local Literature Upload & AI Deep Reading
"""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from backend.domain.paper_reader import extract_text_from_file, read_and_analyze_paper
from backend.domain.paper import save_paper_to_project, get_paper, delete_paper_from_project
from backend.domain.project import create_project, delete_project
from backend.domain.hypothesis import list_hypotheses


def test_text_extraction_from_file():
    txt_content = b"Title: Dynamic Graph Robustness\nAbstract: We present an adaptive edge pruning method."
    text, meta = extract_text_from_file(txt_content, "paper_draft.txt")
    assert "Dynamic Graph" in text
    assert meta["filename"] == "paper_draft.txt"


def test_ai_deep_reading_and_hypothesis_extraction():
    sample_text = """
    Dynamic Graph CNN for Learning on Point Clouds
    Yue Wang, Justin Solomon

    Abstract: Point clouds lack topological information. We propose EdgeConv, an operation that acts on graphs dynamically computed in each layer.
    
    1. Introduction
    Recent works focus on static graphs. However, static topology fails under noise.

    2. Methodology
    We compute k-NN graphs in latent feature space dynamically at each layer.

    3. Experiments
    Results demonstrate that dynamic graph updates boost robustness under 15% noise jitter, achieving 83.2% accuracy on ModelNet40.
    
    4. Conclusion
    Dynamic edge updates significantly improve local manifold smoothness.
    """
    res = read_and_analyze_paper(sample_text, title="Dynamic Graph CNN")
    assert res["success"] is True
    analysis = res["analysis"]
    assert "core_question" in analysis
    assert "methodology" in analysis
    assert len(analysis["key_findings"]) >= 1
    assert len(analysis["candidate_hypotheses"]) >= 1
    assert "statement" in analysis["candidate_hypotheses"][0]


def test_paper_upload_and_hypothesis_adoption_flow():
    proj = create_project("Literature AI Reading Test", "Test Description")
    pid = proj["id"]
    try:
        # 1. 模拟上传文献实体
        paper_data = {
            "paper_id": "local_test_p1",
            "title": "Adaptive Topology in GNNs",
            "abstract": "We study adaptive graph topology learning.",
            "full_text": "We discover that dynamic edge updates outperform static k-NN by 12% accuracy.",
            "source": "local_upload",
        }
        saved = save_paper_to_project(pid, paper_data)
        assert saved["id"] == "local_test_p1"

        # 2. 深度研读
        analysis_res = read_and_analyze_paper(saved["full_text"], title=saved["title"])
        assert analysis_res["success"] is True
        candidate_hyp = analysis_res["analysis"]["candidate_hypotheses"][0]

        # 3. 采纳为课题假说
        from backend.domain.hypothesis import create_hypothesis
        created_hyp = create_hypothesis(
            project_id=pid,
            title=candidate_hyp["title"],
            description=candidate_hyp["statement"],
            source_paper_id=saved["id"],
        )
        assert created_hyp["project_id"] == pid

        hyps = list_hypotheses(pid)
        assert any(h["id"] == created_hyp["id"] for h in hyps)

        # 4. 清理文献
        delete_paper_from_project(pid, saved["id"])
    finally:
        delete_project(pid)
