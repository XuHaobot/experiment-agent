"""
Artifact 系统 — 科研产出资产追踪

每个 Artifact 代表实验产出中的一项可追踪资产：
- 图表 (chart)
- 报告 (report)
- 代码 (code)
- 数据集 (dataset)
- 模型权重 (model)
- 分析结果 (analysis)
- 协议/方案 (protocol)

特性：
- 版本管理（同 name+type 自动递增）
- 血缘追溯（Artifact → 实验 → 参数 → 数据集）
- 内容散列（SHA256 dedup）
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
ARTIFACTS_DIR = DATA_DIR / "artifacts"
RECORDS_DIR = DATA_DIR / "records"

VALID_TYPES = {"chart", "report", "code", "dataset", "model", "analysis", "protocol", "notebook", "other"}


def _ensure_dirs(project_id: str) -> Path:
    d = ARTIFACTS_DIR / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _compute_hash(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode()
    return hashlib.sha256(content).hexdigest()[:16]


def _next_version(project_id: str, name: str, artifact_type: str) -> int:
    """计算同 name+type 下的下一个版本号"""
    existing = list_artifacts(project_id, type_filter=artifact_type)
    max_ver = 0
    for a in existing:
        if a.get("name") == name:
            max_ver = max(max_ver, a.get("version", 1))
    return max_ver + 1


def _get_mime_type(artifact_type: str) -> str:
    mimes = {
        "chart": "image/png",
        "report": "text/markdown",
        "code": "text/x-python",
        "dataset": "application/json",
        "analysis": "application/json",
        "model": "application/octet-stream",
        "protocol": "text/markdown",
        "notebook": "application/x-ipynb+json",
    }
    return mimes.get(artifact_type, "text/plain")


# ─── CRUD ─────────────────────────────────────────────────────────────

def create_artifact(
    project_id: str,
    name: str,
    artifact_type: str,
    content: str | bytes,
    source_record_id: str | None = None,
    source_experiment_id: str | None = None,
    metadata: dict | None = None,
    content_encoding: str = "text",  # "text" | "base64"
    mime_type: str | None = None,
) -> dict:
    """创建并持久化 Artifact"""
    if artifact_type not in VALID_TYPES:
        artifact_type = "other"

    artifact_id = f"art_{uuid.uuid4().hex[:10]}"
    version = _next_version(project_id, name, artifact_type)
    content_str = content if isinstance(content, str) else content.decode()
    content_hash = _compute_hash(content_str)
    resolved_mime = mime_type or _get_mime_type(artifact_type)
    url = f"/api/artifacts/{artifact_id}/content"

    artifact: dict = {
        "id": artifact_id,
        "artifact_id": artifact_id,
        "project_id": project_id,
        "name": name,
        "type": artifact_type,
        "mime_type": resolved_mime,
        "url": url,
        "version": version,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_record_id": source_record_id,
        "source_experiment_id": source_experiment_id,
        "content_hash": content_hash,
        "content_encoding": content_encoding,
        "content": content_str,
        "metadata": metadata or {},
    }

    d = _ensure_dirs(project_id)
    (d / f"{artifact_id}.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Artifact created: %s (project=%s)", artifact_id, project_id)

    # 返回时不含大字段 content（避免过大），保留 metadata, mime_type, url
    return {k: v for k, v in artifact.items() if k != "content"}


def list_artifacts(project_id: str, type_filter: str | None = None) -> list[dict]:
    """列出 Project 下所有 Artifact（不含 content 字段）"""
    d = ARTIFACTS_DIR / project_id
    if not d.exists():
        return []
    arts = []
    for f in sorted(d.glob("art_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if type_filter and data.get("type") != type_filter:
                continue
            item = {k: v for k, v in data.items() if k != "content"}
            if "url" not in item:
                item["url"] = f"/api/artifacts/{item.get('id')}/content"
            if "mime_type" not in item:
                item["mime_type"] = _get_mime_type(item.get("type", "other"))
            if "artifact_id" not in item:
                item["artifact_id"] = item.get("id")
            arts.append(item)
        except Exception:
            pass
    return arts


def get_artifact(artifact_id: str, project_id: str | None = None) -> dict | None:
    """获取 Artifact 详情（含 content）"""
    art_data = None
    # 如果知道 project_id，直接找
    if project_id:
        f = ARTIFACTS_DIR / project_id / f"{artifact_id}.json"
        if f.exists():
            try:
                art_data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                pass

    # 全局搜索
    if not art_data and ARTIFACTS_DIR.exists():
        for proj_dir in ARTIFACTS_DIR.iterdir():
            if not proj_dir.is_dir():
                continue
            f = proj_dir / f"{artifact_id}.json"
            if f.exists():
                try:
                    art_data = json.loads(f.read_text(encoding="utf-8"))
                    break
                except Exception:
                    pass

    if art_data:
        if "url" not in art_data:
            art_data["url"] = f"/api/artifacts/{art_data.get('id')}/content"
        if "mime_type" not in art_data:
            art_data["mime_type"] = _get_mime_type(art_data.get("type", "other"))
        if "artifact_id" not in art_data:
            art_data["artifact_id"] = art_data.get("id")

    return art_data


def delete_artifact(artifact_id: str, project_id: str | None = None) -> bool:
    """删除 Artifact"""
    art = get_artifact(artifact_id, project_id)
    if art is None:
        return False
    proj_id = art.get("project_id", project_id)
    f = ARTIFACTS_DIR / proj_id / f"{artifact_id}.json"
    if f.exists():
        f.unlink()
        return True
    return False


# ─── 血缘追溯 ──────────────────────────────────────────────────────────

def get_artifact_lineage(artifact_id: str) -> dict:
    """
    追溯 Artifact 的来源血缘链：
    Artifact → 源实验记录 → 参数 → 模型 → 数据集
    """
    art = get_artifact(artifact_id)
    if art is None:
        return {"error": f"Artifact 不存在: {artifact_id}"}

    lineage: dict[str, Any] = {
        "artifact": {
            "id": art["id"],
            "name": art["name"],
            "type": art["type"],
            "version": art.get("version", 1),
            "created_at": art.get("created_at"),
        },
        "source_record": None,
        "params": None,
        "model": None,
        "dataset": None,
    }

    record_id = art.get("source_record_id")
    if record_id and RECORDS_DIR.exists():
        for f in RECORDS_DIR.glob(f"*{record_id}*.json"):
            try:
                record = json.loads(f.read_text(encoding="utf-8"))
                lineage["source_record"] = {
                    "id": record.get("id"),
                    "task": record.get("task", ""),
                    "created_at": record.get("created_at", ""),
                }
                lineage["params"] = record.get("params")
                lineage["model"] = record.get("model")
                lineage["dataset"] = record.get("dataset")
                break
            except Exception:
                pass

    return lineage
