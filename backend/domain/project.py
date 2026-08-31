"""
Research Project 领域模型 + 本地 JSON 持久化

存储路径：data/projects/<project_id>.json

Project 数据结构：
{
    "id": "proj_xxx",
    "name": "项目名称",
    "description": "项目描述",
    "questions": [
        {"id": "q_xxx", "text": "研究问题", "created_at": "..."}
    ],
    "experiment_ids": ["exp_001", "exp_002"],
    "created_at": "...",
    "updated_at": "..."
}
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _projects_dir() -> Path:
    from src.storage import DATA_DIR
    d = DATA_DIR / "projects"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

def create_project(name: str, description: str = "") -> dict:
    """新建 Research Project，返回 project dict。"""
    project = {
        "id": f"proj_{uuid.uuid4().hex[:10]}",
        "name": name.strip(),
        "description": description.strip(),
        "questions": [],
        "experiment_ids": [],
        "created_at": _utcnow(),
        "updated_at": _utcnow(),
    }
    _save_project(project)
    return project


def list_projects() -> list[dict]:
    """列出所有 Project，按 updated_at 降序排列。"""
    d = _projects_dir()
    projects = []
    for f in d.glob("*.json"):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
            projects.append(p)
        except Exception:
            pass
    projects.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    return projects


def get_project(project_id: str) -> Optional[dict]:
    """根据 ID 获取 Project，不存在返回 None。"""
    p = _projects_dir() / f"{project_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def update_project(
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    **kwargs,
) -> Optional[dict]:
    """更新 Project 基本信息及关联字段，返回更新后的 project dict。"""
    project = get_project(project_id)
    if project is None:
        return None
    if isinstance(name, dict):
        kwargs.update(name)
        name = None
    if name is not None:
        project["name"] = name.strip()
    if description is not None:
        project["description"] = description.strip()
    for k, v in kwargs.items():
        project[k] = v
    project["updated_at"] = _utcnow()
    _save_project(project)
    return project


def delete_project(project_id: str) -> bool:
    """删除 Project（只删除 project JSON，不删除关联的实验记录）。"""
    p = _projects_dir() / f"{project_id}.json"
    if p.exists():
        p.unlink()
        return True
    return False


# ---------------------------------------------------------------------------
# Experiment 关联
# ---------------------------------------------------------------------------

def add_experiment_to_project(project_id: str, experiment_id: str) -> Optional[dict]:
    """将实验 ID 关联到 Project。"""
    project = get_project(project_id)
    if project is None:
        return None
    if experiment_id not in project["experiment_ids"]:
        project["experiment_ids"].append(experiment_id)
        project["updated_at"] = _utcnow()
        _save_project(project)
    return project


def remove_experiment_from_project(project_id: str, experiment_id: str) -> Optional[dict]:
    """从 Project 中解除实验关联。"""
    project = get_project(project_id)
    if project is None:
        return None
    project["experiment_ids"] = [eid for eid in project["experiment_ids"] if eid != experiment_id]
    project["updated_at"] = _utcnow()
    _save_project(project)
    return project


# ---------------------------------------------------------------------------
# Research Question
# ---------------------------------------------------------------------------

def add_question(project_id: str, text: str) -> Optional[dict]:
    """向 Project 中添加 Research Question，返回新建的 question dict。"""
    project = get_project(project_id)
    if project is None:
        return None
    question = {
        "id": f"q_{uuid.uuid4().hex[:8]}",
        "text": text.strip(),
        "created_at": _utcnow(),
    }
    project.setdefault("questions", []).append(question)
    project["updated_at"] = _utcnow()
    _save_project(project)
    return question


def delete_question(project_id: str, question_id: str) -> bool:
    """删除 Project 中的 Research Question。"""
    project = get_project(project_id)
    if project is None:
        return False
    orig = len(project.get("questions", []))
    project["questions"] = [q for q in project.get("questions", []) if q["id"] != question_id]
    if len(project["questions"]) < orig:
        project["updated_at"] = _utcnow()
        _save_project(project)
        return True
    return False


# ---------------------------------------------------------------------------
# Default Project（迁移现有实验时使用）
# ---------------------------------------------------------------------------

def get_or_create_default_project() -> dict:
    """获取或创建默认 Project，用于容纳存量实验记录。"""
    projects = list_projects()
    for p in projects:
        if p.get("name") == "Default Project":
            return p
    return create_project("Default Project", "自动创建：用于容纳升级前的历史实验记录。")


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _save_project(project: dict) -> None:
    path = _projects_dir() / f"{project['id']}.json"
    path.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
