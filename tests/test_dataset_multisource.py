"""
Unit Tests for Online Dataset Exploration & Integration
"""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from backend.integrations.datasets import search_online_datasets, get_dataset_provider
from backend.domain.dataset import (
    create_dataset_from_csv,
    save_online_dataset_to_project,
    list_project_datasets,
    query_dataset_sql,
    delete_dataset,
)
from backend.domain.project import create_project, delete_project


def test_dataset_providers_registration():
    for name in ["huggingface", "papers_with_code"]:
        prov = get_dataset_provider(name)
        assert prov is not None
        assert prov.name == name


def test_online_dataset_save_and_query_flow():
    proj = create_project("Dataset Integration Test Project", "Test Description")
    pid = proj["id"]
    try:
        # 1. 保存模拟的在线数据集实体
        online_ds = {
            "dataset_id": "hf:glue",
            "name": "glue",
            "description": "General Language Understanding Evaluation benchmark",
            "source": "huggingface",
            "downloads": 100000,
            "likes": 500,
            "tasks": ["text-classification"],
            "url": "https://huggingface.co/datasets/glue",
            "load_code": "from datasets import load_dataset\ndataset = load_dataset('glue')",
        }
        saved = save_online_dataset_to_project(pid, online_ds)
        assert saved["project_id"] == pid
        assert saved["source"] == "huggingface"

        # 2. 创建本地结构化 CSV 数据集并执行 DuckDB SQL
        csv_data = "epoch,lr,accuracy,loss\n1,0.001,0.75,0.55\n2,0.001,0.85,0.35\n3,0.0005,0.89,0.22"
        local_ds = create_dataset_from_csv(pid, "test_train_metrics.csv", csv_data)
        assert local_ds["row_count"] == 3

        # 3. 列出项目下数据集
        all_ds = list_project_datasets(pid)
        assert len(all_ds) >= 2

        # 4. DuckDB 查询
        res = query_dataset_sql(local_ds["id"], "SELECT MAX(accuracy) as best_acc, AVG(loss) as avg_loss FROM dataset")
        assert res["success"] is True
        assert len(res["rows"]) == 1
        assert float(res["rows"][0][0]) == 0.89

        # 5. 清理本地测试数据集
        delete_dataset(local_ds["id"])
        delete_dataset(saved["id"])
    finally:
        delete_project(pid)
