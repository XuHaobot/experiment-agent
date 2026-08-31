"""
Hypothesis 领域模型 + 本地 JSON 持久化

存储路径：data/hypotheses/<hypothesis_id>.json

Hypothesis 数据结构：
{
    "id": "hyp_xxx",
    "project_id": "proj_xxx",
    "question_id": "q_xxx",  // 可选，关联到某个 Research Question
    "title": "假设标题（简短）",
    "description": "详细描述",
    "status": "pending | testing | supported | refuted",
    "evidence": [],          // 支持/反驳证据列表
    "experiment_ids": [],    // 关联的实验 ID
    "created_at": "...",
    "updated_at": "..."
}
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


HYPOTHESIS_STATUSES = (
    "pending",
    "testing",
    "supported",
    "refuted",
    "active",
    "weakened",
    "stale",
    "needs_more_evidence",
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hypotheses_dir() -> Path:
    from src.storage import DATA_DIR
    d = DATA_DIR / "hypotheses"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Hypothesis CRUD
# ---------------------------------------------------------------------------

def create_hypothesis(
    project_id: str,
    title: str,
    description: str = "",
    question_id: Optional[str] = None,
) -> dict:
    """新建 Hypothesis，返回 hypothesis dict。"""
    hyp = {
        "id": f"hyp_{uuid.uuid4().hex[:10]}",
        "project_id": project_id,
        "question_id": question_id,
        "title": title.strip(),
        "description": description.strip(),
        "status": "pending",
        "evidence": [],
        "experiment_ids": [],
        "created_at": _utcnow(),
        "updated_at": _utcnow(),
    }
    _save_hypothesis(hyp)
    return hyp


def list_hypotheses(project_id: Optional[str] = None) -> list[dict]:
    """列出所有 Hypothesis，可按 project_id 过滤。"""
    d = _hypotheses_dir()
    hyps = []
    for f in d.glob("*.json"):
        try:
            h = json.loads(f.read_text(encoding="utf-8"))
            if project_id is None or h.get("project_id") == project_id:
                hyps.append(h)
        except Exception:
            pass
    hyps.sort(key=lambda h: h.get("updated_at", ""), reverse=True)
    return hyps


def get_hypothesis(hypothesis_id: str) -> Optional[dict]:
    """根据 ID 获取 Hypothesis。"""
    p = _hypotheses_dir() / f"{hypothesis_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def update_hypothesis(
    hypothesis_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[dict]:
    """更新 Hypothesis。status 必须是合法值。"""
    hyp = get_hypothesis(hypothesis_id)
    if hyp is None:
        return None
    if title is not None:
        hyp["title"] = title.strip()
    if description is not None:
        hyp["description"] = description.strip()
    if status is not None:
        if status not in HYPOTHESIS_STATUSES:
            raise ValueError(f"status 必须是 {HYPOTHESIS_STATUSES} 之一")
        hyp["status"] = status
    hyp["updated_at"] = _utcnow()
    _save_hypothesis(hyp)
    return hyp


def delete_hypothesis(hypothesis_id: str) -> bool:
    """删除 Hypothesis。"""
    p = _hypotheses_dir() / f"{hypothesis_id}.json"
    if p.exists():
        p.unlink()
        return True
    return False


def add_evidence(hypothesis_id: str, source: str, text: str, supports: bool = True) -> Optional[dict]:
    """向 Hypothesis 添加证据。supports=True 为支持证据，False 为反驳证据。"""
    hyp = get_hypothesis(hypothesis_id)
    if hyp is None:
        return None
    evidence_item = {
        "id": f"ev_{uuid.uuid4().hex[:8]}",
        "source": source,
        "text": text.strip(),
        "supports": supports,
        "created_at": _utcnow(),
    }
    hyp.setdefault("evidence", []).append(evidence_item)
    hyp["updated_at"] = _utcnow()
    _save_hypothesis(hyp)
    return evidence_item


def link_experiment(hypothesis_id: str, experiment_id: str) -> Optional[dict]:
    """将实验关联到 Hypothesis。"""
    hyp = get_hypothesis(hypothesis_id)
    if hyp is None:
        return None
    if experiment_id not in hyp["experiment_ids"]:
        hyp["experiment_ids"].append(experiment_id)
        hyp["updated_at"] = _utcnow()
        _save_hypothesis(hyp)
    return hyp


# ---------------------------------------------------------------------------
# AI 辅助：根据 Research Question 生成 Hypothesis 建议
# ---------------------------------------------------------------------------

def ai_suggest_hypotheses(question_text: str, project_context: str = "") -> list[str]:
    """
    调用 LLM 根据研究问题生成若干候选假设。
    返回建议假设标题列表（字符串列表）。
    """
    from src.llm_client import LLMClient
    client = LLMClient.from_env()
    if not client.is_configured:
        return []

    context_part = f"\n项目背景：{project_context}" if project_context else ""
    prompt = f"""你是一位科研助手。
    
研究问题：{question_text}{context_part}

请为该研究问题生成 3 个可测试的科学假设。
要求：
1. 每个假设应明确、可验证
2. 用简洁的一句话表达
3. 以 JSON 数组格式返回，例如：["假设1", "假设2", "假设3"]

只返回 JSON 数组，不要其他说明。"""

    try:
        result = client.call_llm(prompt)
        # 尝试从结果中解析 JSON 数组
        import re
        match = re.search(r'\[.*?\]', result, re.DOTALL)
        if match:
            import json as _json
            return _json.loads(match.group())
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _save_hypothesis(hyp: dict) -> None:
    path = _hypotheses_dir() / f"{hyp['id']}.json"
    path.write_text(json.dumps(hyp, ensure_ascii=False, indent=2), encoding="utf-8")
