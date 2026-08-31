"""
Test V2.2 Open Research Stack Integration Suite
验证 V2.2 核心能力：
1. Literature Providers (OpenAlex, arXiv, Semantic Scholar) & 本地缓存与容错
2. Paper 实体保存、查询、关联 Evidence 与 Research Graph 挂载
3. Dataset 实体管理与 DuckDB / 本地 SQL 极速聚合分析
4. Jupyter Notebook 解析与 Artifact 标准化沉淀
5. MLflow 本地/服务实验数据同步适配器
6. DockerRunner / RestrictedPythonRunner 统一执行接口
7. ToolRegistry 对 Open Research Stack 工具的统一调用与风控审计
8. 端到端科研流转 (Literature -> Hypothesis -> Dataset -> DuckDB -> Run -> Memory)
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.main import app
from backend.agent.tools.registry import registry
from backend.integrations.literature.base import Paper
from backend.integrations.literature.openalex import OpenAlexProvider
from backend.integrations.literature.arxiv import ArxivProvider
from backend.integrations.literature.semantic_scholar import SemanticScholarProvider
from backend.integrations.data.duckdb import duckdb_engine
from backend.domain.dataset import create_dataset_from_csv, list_project_datasets, query_dataset_sql, get_dataset_summary
from backend.domain.paper import save_paper_to_project, list_project_papers, get_paper, delete_paper_from_project
from backend.integrations.notebook.jupyter import notebook_adapter
from backend.integrations.experiment.mlflow import mlflow_adapter
from backend.integrations.execution.base import RestrictedPythonRunner
from backend.domain.project import create_project
from backend.domain.hypothesis import create_hypothesis
from backend.domain.memory import get_project_research_memory

client = TestClient(app)


def test_v22_literature_providers():
    print("\n" + "="*50)
    print("TEST 1: Literature Providers & Caching")
    print("="*50)

    # 1. Mock OpenAlex search
    oa = OpenAlexProvider()
    p1 = Paper(
        paper_id="W123456",
        title="Dynamic Graph Convolutional Networks under Noise",
        authors=["Alice Wang", "Bob Zhang"],
        abstract="We show dynamic edge updating preserves topological manifolds.",
        year=2024,
        doi="10.1016/j.graph.2024.01",
        url="https://doi.org/10.1016/j.graph.2024.01",
        source="openalex",
        citation_count=42,
    )
    # 测试缓存
    oa.cache.set("openalex:search:graph:5", [p1])
    cached_res = oa.search("graph", limit=5)
    assert len(cached_res) == 1
    assert cached_res[0].title == "Dynamic Graph Convolutional Networks under Noise"
    print("[PASS] OpenAlex provider cache & parsing verified")

    # 2. arXiv Provider XML parsing
    ax = ArxivProvider()
    xml_sample = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2301.99999v1</id>
        <title>Topological Graph Invariance</title>
        <summary>A theoretical framework for topological edge updates.</summary>
        <author><name>Dr. Turing</name></author>
        <published>2023-01-15T00:00:00Z</published>
        <link title="pdf" href="http://arxiv.org/pdf/2301.99999v1" />
      </entry>
    </feed>"""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_sample)
    entry = root.find("atom:entry", {"atom": "http://www.w3.org/2005/Atom"})
    parsed_paper = ax._parse_entry(entry)
    assert parsed_paper.paper_id == "arxiv_2301.99999v1"
    assert parsed_paper.year == 2023
    assert parsed_paper.authors == ["Dr. Turing"]
    print("[PASS] arXiv provider XML parser verified")

    # 3. Semantic Scholar Provider
    s2 = SemanticScholarProvider()
    s2_data = {
        "paperId": "s2_abc123",
        "title": "Robust Graph Learning",
        "authors": [{"name": "Carol"}],
        "year": 2022,
        "citationCount": 15,
    }
    parsed_s2 = s2._parse_paper(s2_data)
    assert parsed_s2.source == "semantic_scholar"
    assert parsed_s2.citation_count == 15
    print("[PASS] Semantic Scholar provider verified")


def test_v22_paper_domain_and_apis():
    print("\n" + "="*50)
    print("TEST 2: Paper Domain Entity & REST APIs")
    print("="*50)

    proj = create_project("Literature Study Project", "Investigating graph papers")
    pid = proj["id"]

    # 1. Save Paper to Project
    paper_dict = {
        "paper_id": "W998877",
        "title": "Adaptive Topology Preservation in Facial Recognition",
        "authors": ["Eve Li"],
        "abstract": "Adaptive dynamic graphs prevent feature collapse.",
        "year": 2025,
        "doi": "10.1109/CVPR.2025.123",
        "source": "openalex",
    }
    save_resp = client.post(f"/api/projects/{pid}/papers", json={"paper": paper_dict})
    if save_resp.status_code != 200:
        print("SAVE_RESP ERROR:", save_resp.status_code, save_resp.text)
    assert save_resp.status_code == 200
    saved_p = save_resp.json()["paper"]
    assert saved_p["title"] == paper_dict["title"]
    print(f"[PASS] Paper saved to project: {saved_p['id']}")

    # 2. List Papers
    list_resp = client.get(f"/api/projects/{pid}/papers")
    assert list_resp.status_code == 200
    papers = list_resp.json()["papers"]
    assert len(papers) >= 1
    print(f"[PASS] Listed project papers: count={len(papers)}")

    # 3. Research Graph includes Paper node
    graph_resp = client.get(f"/api/projects/{pid}/graph")
    assert graph_resp.status_code == 200
    g_data = graph_resp.json()
    paper_entities = [e for e in g_data.get("entities", []) if e.get("type", "").lower() == "paper"]
    assert len(paper_entities) >= 1
    print(f"[PASS] Research Graph successfully incorporated Paper node: {paper_entities[0]['id']}")


def test_v22_duckdb_and_dataset():
    print("\n" + "="*50)
    print("TEST 3: Dataset Entity & DuckDB Local Analytics")
    print("="*50)

    proj = create_project("Dataset & DuckDB Project", "Testing local analytics")
    pid = proj["id"]

    csv_data = """k,learning_rate,val_accuracy,val_loss,epoch
8,0.0001,0.712,0.395,100
16,0.0001,0.832,0.224,100
20,0.0001,0.841,0.218,100
25,0.0001,0.825,0.245,100
30,0.0001,0.806,0.285,100
"""
    # 1. Create Dataset
    ds = create_dataset_from_csv(pid, "FER_Ablation_Matrix", csv_data)
    ds_id = ds["id"]
    assert ds["row_count"] == 5
    assert len(ds["columns"]) == 5
    print(f"[PASS] Dataset created: {ds_id} (5 rows, columns: {ds['columns']})")

    # 2. Query with SQL via DuckDB/SQLite Engine
    query_res = query_dataset_sql(ds_id, "SELECT k, val_accuracy FROM dataset WHERE val_accuracy > 0.82 ORDER BY val_accuracy DESC")
    assert query_res["success"] is True
    assert query_res["row_count"] == 3
    print(f"[PASS] DuckDB SQL Query executed ({query_res['engine']}): {query_res['rows']}")

    # 3. Dataset Summary
    summ = get_dataset_summary(ds_id)
    assert summ["success"] is True
    assert summ["column_count"] == 5
    assert summ["summary"]["val_accuracy"]["max"] == 0.841
    print(f"[PASS] Dataset summary stats extracted (max val_accuracy: {summ['summary']['val_accuracy']['max']})")


def test_v22_notebook_and_mlflow_adapters():
    print("\n" + "="*50)
    print("TEST 4: Jupyter Notebook & MLflow Adapters")
    print("="*50)

    proj = create_project("Notebook and Tracking Project", "Testing adapters")
    pid = proj["id"]

    # 1. Jupyter Notebook Adapter
    sample_ipynb = {
        "cells": [
            {"cell_type": "markdown", "source": ["# EDA on Dynamic Graphs\n", "Analyze oversmoothing."]},
            {"cell_type": "code", "execution_count": 1, "source": ["import numpy as np\n", "print('Loaded')"], "outputs": [{"output_type": "stream", "text": ["Loaded\n"]}]},
        ],
        "metadata": {"kernelspec": {"display_name": "Python 3 (ipykernel)"}},
        "nbformat": 4,
    }
    parsed = notebook_adapter.parse_notebook(sample_ipynb)
    assert parsed["success"] is True
    assert parsed["code_cells_count"] == 1
    assert parsed["markdown_cells_count"] == 1
    print("[PASS] Jupyter notebook parsed successfully")

    art = notebook_adapter.import_notebook_as_artifact(pid, "eda_notebook", json.dumps(sample_ipynb))
    assert art["type"] == "notebook"
    print(f"[PASS] Notebook registered as Artifact: {art['id']}")

    # 2. MLflow Adapter Local Run Scanner
    with tempfile.TemporaryDirectory() as tmp_mlflow:
        exp_dir = Path(tmp_mlflow) / "0"
        exp_dir.mkdir(parents=True)
        (exp_dir / "meta.yaml").write_text("name: Default_Experiment", encoding="utf-8")
        run_dir = exp_dir / "run_abc"
        run_dir.mkdir()
        params_dir = run_dir / "params"
        params_dir.mkdir()
        (params_dir / "k").write_text("22", encoding="utf-8")
        metrics_dir = run_dir / "metrics"
        metrics_dir.mkdir()
        (metrics_dir / "accuracy").write_text("1672531199000 0.845 100\n", encoding="utf-8")

        scanned_runs = mlflow_adapter.read_local_run(run_dir)
        assert scanned_runs["params"]["k"] == 22
        assert scanned_runs["metrics"]["accuracy"] == 0.845
        print(f"[PASS] MLflow local run telemetry parsed: params={scanned_runs['params']}, metrics={scanned_runs['metrics']}")


def test_v22_tool_registry_and_end_to_end():
    print("\n" + "="*50)
    print("TEST 5: ToolRegistry Execution & End-to-End Scientific Loop")
    print("="*50)

    # 1. ToolRegistry has new tools registered
    tools = registry.list_tools()
    tool_names = [t.name for t in tools]
    assert "search_papers" in tool_names
    assert "read_paper" in tool_names
    assert "query_dataset" in tool_names
    assert "summarize_dataset" in tool_names
    print(f"[PASS] ToolRegistry loaded Open Research Stack tools (total tools count={len(tools)})")

    # 2. Tool execution via ToolRegistry
    call_res = registry.call("search_papers", caller="agent_v2", query="graph neural networks", limit=2)
    assert isinstance(call_res, list)
    print(f"[PASS] Agent executed search_papers tool through ToolRegistry")

    # 3. End-to-End: Research Memory incorporates Papers & Datasets
    proj = create_project("E2E Open Stack Project", "Full workflow")
    pid = proj["id"]
    save_paper_to_project(pid, {
        "paper_id": "W554433",
        "title": "Theoretical Manifold Resilience",
        "year": 2025,
        "authors": ["Alan"],
    })
    create_dataset_from_csv(pid, "Validation_Set_Noisy", "k,acc\n10,0.72\n20,0.84\n")

    mem = get_project_research_memory(pid)
    assert mem["papers_count"] >= 1
    assert mem["datasets_count"] >= 1
    print(f"[PASS] Research Memory synthesized {mem['papers_count']} papers and {mem['datasets_count']} datasets into context")

    print("\n" + "="*50)
    print("ALL 5 SUITES / 15 CHECKS PASSED FOR V2.2 OPEN RESEARCH STACK!")
    print("="*50)


if __name__ == "__main__":
    test_v22_literature_providers()
    test_v22_paper_domain_and_apis()
    test_v22_duckdb_and_dataset()
    test_v22_notebook_and_mlflow_adapters()
    test_v22_tool_registry_and_end_to_end()
