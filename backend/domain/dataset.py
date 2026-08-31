"""
Dataset Domain Module — 结构化数据集实体与管理
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from backend.integrations.data.duckdb import duckdb_engine

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATASETS_DIR = DATA_DIR / "datasets"


def _ensure_dir():
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)


def _dataset_meta_path(dataset_id: str) -> Path:
    return DATASETS_DIR / f"{dataset_id}.json"


def _dataset_file_path(dataset_id: str, fmt: str = "csv") -> Path:
    return DATASETS_DIR / f"{dataset_id}.{fmt}"


def create_dataset_from_csv(
    project_id: str,
    name: str,
    csv_content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """创建并保存 CSV 数据集实体与数据文件"""
    _ensure_dir()
    from backend.domain.project import get_project, update_project

    proj = get_project(project_id)
    if not proj:
        raise ValueError(f"Project 不存在: {project_id}")

    dataset_id = f"ds_{uuid.uuid4().hex[:10]}"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    clean_content = csv_content.strip()
    if not clean_content:
        raise ValueError("CSV 内容不能为空")

    # 写入物理 CSV 文件
    csv_file = _dataset_file_path(dataset_id, "csv")
    csv_file.write_text(clean_content, encoding="utf-8")

    # 计算校验和与行列
    checksum = hashlib.md5(clean_content.encode("utf-8")).hexdigest()
    reader = csv.reader(io.StringIO(clean_content))
    headers = next(reader, [])
    row_count = sum(1 for _ in reader)

    record: dict[str, Any] = {
        "id": dataset_id,
        "dataset_id": dataset_id,
        "project_id": project_id,
        "name": name.strip() or "Untitled Dataset",
        "source": "upload",
        "format": "csv",
        "path": str(csv_file),
        "checksum": checksum,
        "columns": headers,
        "row_count": row_count,
        "metadata": metadata or {},
        "created_at": now,
    }

    _dataset_meta_path(dataset_id).write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 关联到项目
    current_datasets = list(proj.get("dataset_ids", []))
    if dataset_id not in current_datasets:
        current_datasets.append(dataset_id)
        update_project(project_id, {"dataset_ids": current_datasets})

    logger.info("Dataset %s created with %d rows", dataset_id, row_count)
    return record


def list_project_datasets(project_id: str) -> list[dict[str, Any]]:
    """获取 Project 下的所有 Dataset 列表"""
    _ensure_dir()
    results = []
    for f in sorted(DATASETS_DIR.glob("ds_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("project_id") == project_id:
                results.append(data)
        except Exception:
            pass
    return results


def get_dataset(dataset_id: str) -> dict[str, Any] | None:
    """获取单个 Dataset 详情"""
    p = _dataset_meta_path(dataset_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def query_dataset_sql(dataset_id: str, sql: str, limit: int = 50) -> dict[str, Any]:
    """通过 DuckDB / 本地引擎对 Dataset 执行 SQL 查询"""
    ds = get_dataset(dataset_id)
    if not ds:
        return {"success": False, "error": f"数据集不存在: {dataset_id}", "columns": [], "rows": []}

    csv_path = ds.get("path")
    if not csv_path or not Path(csv_path).exists():
        return {"success": False, "error": "数据源文件不存在", "columns": [], "rows": []}

    return duckdb_engine.query_csv_file(csv_path, sql, limit=limit)


def get_dataset_summary(dataset_id: str) -> dict[str, Any]:
    """获取数据集字段统计概览"""
    ds = get_dataset(dataset_id)
    if not ds:
        return {"success": False, "error": "数据集不存在"}

    csv_path = ds.get("path")
    if not csv_path or not Path(csv_path).exists():
        return {"success": False, "error": "数据源文件不存在"}

    return duckdb_engine.summarize_csv(csv_path)


def delete_dataset(dataset_id: str) -> bool:
    """删除 Dataset"""
    p = _dataset_meta_path(dataset_id)
    if not p.exists():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        csv_p = Path(data.get("path", ""))
        if csv_p.exists():
            csv_p.unlink()
        p.unlink()

        # 从 project 移除
        from backend.domain.project import get_project, update_project
        pid = data.get("project_id")
        if pid:
            proj = get_project(pid)
            if proj:
                d_ids = list(proj.get("dataset_ids", []))
                if dataset_id in d_ids:
                    d_ids.remove(dataset_id)
                    update_project(pid, {"dataset_ids": d_ids})
        return True
    except Exception as e:
        logger.error("Failed to delete dataset: %s", e)
        return False
