"""
Analysis Session Domain Module — 持久化 Python 数据分析会话
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
ANALYSES_DIR = DATA_DIR / "analyses"


def _ensure_dir():
    ANALYSES_DIR.mkdir(parents=True, exist_ok=True)


def _analysis_path(analysis_id: str) -> Path:
    return ANALYSES_DIR / f"{analysis_id}.json"


def create_analysis_session(
    project_id: str,
    name: str,
    code: str,
    stdout: str = "",
    charts: list[str] | None = None,
    insights: str = "",
    experiment_id: str | None = None,
    run_ids: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """创建并持久化一个分析会话"""
    _ensure_dir()
    analysis_id = f"ana_{uuid.uuid4().hex[:10]}"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    record: dict[str, Any] = {
        "id": analysis_id,
        "project_id": project_id,
        "experiment_id": experiment_id,
        "run_ids": run_ids or [],
        "name": name.strip() or "Untitled Analysis",
        "code": code,
        "stdout": stdout,
        "charts": charts or [],
        "insights": insights,
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
    }

    _analysis_path(analysis_id).write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Analysis session created: %s (%s)", analysis_id, record["name"])
    return record


def list_analysis_sessions(project_id: str | None = None) -> list[dict[str, Any]]:
    """列出分析会话，可按 project_id 过滤"""
    if not ANALYSES_DIR.exists():
        return []
    results = []
    for f in sorted(ANALYSES_DIR.glob("ana_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if project_id is None or data.get("project_id") == project_id:
                results.append(data)
        except Exception:
            pass
    return results


def get_analysis_session(analysis_id: str) -> dict[str, Any] | None:
    """获取单个分析会话详情"""
    p = _analysis_path(analysis_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def delete_analysis_session(analysis_id: str) -> bool:
    """删除分析会话"""
    p = _analysis_path(analysis_id)
    if p.exists():
        p.unlink()
        return True
    return False
