"""
Research Diary Domain Module — 科研人员每日日记与主观反思记录 (USER_BELIEF / OBSERVATION)

核心学术原则：
1. 记录科研人员个人随手直觉、灵感与每日观察。
2. 严格标记为 EpistemicStatus.USER_BELIEF 或 EpistemicStatus.OBSERVATION。
3. AI 绝不得自动篡改、覆盖或伪造科研日记。
4. 提供历史日记检索与反思回顾。
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.domain.epistemic import EpistemicStatus

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DIARY_DIR = DATA_DIR / "diary"


def _ensure_dir():
    DIARY_DIR.mkdir(parents=True, exist_ok=True)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _diary_path(project_id: str) -> Path:
    _ensure_dir()
    return DIARY_DIR / f"{project_id}.json"


def list_diary_entries(project_id: str) -> List[Dict[str, Any]]:
    """获取指定 Project 下的所有科研日记列表（按时间倒序）"""
    p = _diary_path(project_id)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        entries = data.get("entries", [])
        entries.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return entries
    except Exception as e:
        logger.error("Failed to load diary for %s: %s", project_id, e)
        return []


def create_diary_entry(
    project_id: str,
    title: str,
    content: str,
    entry_date: Optional[str] = None,
    tags: Optional[List[str]] = None,
    linked_hypothesis_id: Optional[str] = None,
    linked_experiment_id: Optional[str] = None,
) -> Dict[str, Any]:
    """创建并保存一条新的科研日记条目"""
    _ensure_dir()
    entries = list_diary_entries(project_id)
    
    entry_id = f"diary_{uuid.uuid4().hex[:10]}"
    now = _utcnow()
    date_str = entry_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entry = {
        "id": entry_id,
        "project_id": project_id,
        "date": date_str,
        "title": title.strip(),
        "content": content.strip(),
        "tags": tags or [],
        "linked_hypothesis_id": linked_hypothesis_id,
        "linked_experiment_id": linked_experiment_id,
        "epistemic_status": EpistemicStatus.USER_BELIEF.value,
        "created_at": now,
        "updated_at": now,
    }

    entries.append(entry)
    _diary_path(project_id).write_text(
        json.dumps({"project_id": project_id, "entries": entries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("Saved diary entry %s for project %s", entry_id, project_id)
    return entry


def delete_diary_entry(project_id: str, entry_id: str) -> bool:
    """删除指定的日记条目"""
    entries = list_diary_entries(project_id)
    new_entries = [e for e in entries if e.get("id") != entry_id]
    if len(new_entries) == len(entries):
        return False
    
    _diary_path(project_id).write_text(
        json.dumps({"project_id": project_id, "entries": new_entries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return True
