"""
Conclusion 系统 — 科研结论沉淀与证据关联

每条 Conclusion 代表一个有证据支撑的科研结论：
- 关联 Hypothesis（验证/反驳）
- 关联 Evidence（实验/论文/数据集）
- 置信度（high / medium / low）
- 可从 AI 对话中一键沉淀
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
CONCLUSIONS_DIR = DATA_DIR / "conclusions"

VALID_CONFIDENCE = {"high", "medium", "low"}
VALID_EVIDENCE_TYPES = {"experiment", "run", "paper", "dataset", "analysis", "artifact", "evidence"}


def _ensure_dirs():
    CONCLUSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _conclusion_path(conclusion_id: str) -> Path:
    return CONCLUSIONS_DIR / f"{conclusion_id}.json"


# ─── CRUD ─────────────────────────────────────────────────────────────

def create_conclusion(
    project_id: str,
    text: str,
    hypothesis_id: str | None = None,
    evidence_refs: list[dict] | None = None,
    confidence: str = "medium",
    source: str = "user",  # "user" | "agent"
) -> dict:
    """
    创建一条科研结论。

    evidence_refs 格式：
    [
        {"type": "experiment", "id": "...", "snippet": "..."},
        {"type": "paper", "id": "...", "title": "..."}
    ]
    """
    _ensure_dirs()
    if confidence not in VALID_CONFIDENCE:
        confidence = "medium"

    conclusion_id = f"conc_{uuid.uuid4().hex[:10]}"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # 验证 evidence_refs
    clean_refs = []
    for ref in (evidence_refs or []):
        if isinstance(ref, dict) and ref.get("type") in VALID_EVIDENCE_TYPES:
            clean_refs.append(ref)

    strength_map = {"high": "strong", "medium": "moderate", "low": "weak"}

    conclusion: dict = {
        "id": conclusion_id,
        "project_id": project_id,
        "hypothesis_id": hypothesis_id,
        "text": text.strip(),
        "statement": text.strip(),
        "confidence": confidence,
        "evidence_strength": strength_map.get(confidence, "moderate"),
        "source": source,
        "evidence_refs": clean_refs,
        "supporting_evidence": [r for r in clean_refs if r.get("stance", "support") == "support"],
        "contradicting_evidence": [r for r in clean_refs if r.get("stance") == "contradict"],
        "affected_hypotheses": [hypothesis_id] if hypothesis_id else [],
        "affected_experiments": list(set([r["id"] for r in clean_refs if r.get("type") in ("experiment", "run")])),
        "next_action": f"围绕结论验证最优区间并规划下一步实验",
        "created_at": now,
        "updated_at": now,
    }

    _conclusion_path(conclusion_id).write_text(
        json.dumps(conclusion, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Conclusion created: %s (project=%s)", conclusion_id, project_id)
    return conclusion


def list_conclusions(project_id: str) -> list[dict]:
    """列出 Project 下所有 Conclusion"""
    if not CONCLUSIONS_DIR.exists():
        return []
    result = []
    for f in sorted(CONCLUSIONS_DIR.glob("conc_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("project_id") == project_id:
                result.append(data)
        except Exception:
            pass
    return result


def get_conclusion(conclusion_id: str) -> dict | None:
    f = _conclusion_path(conclusion_id)
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def add_evidence_to_conclusion(
    conclusion_id: str,
    evidence_type: str,
    evidence_id: str,
    snippet: str = "",
) -> dict | None:
    """向已有 Conclusion 追加一条证据引用"""
    conclusion = get_conclusion(conclusion_id)
    if conclusion is None:
        return None

    if evidence_type not in VALID_EVIDENCE_TYPES:
        return conclusion

    ref: dict = {"type": evidence_type, "id": evidence_id}
    if snippet:
        ref["snippet"] = snippet[:200]

    # 去重
    existing = [(r["type"], r["id"]) for r in conclusion.get("evidence_refs", [])]
    if (evidence_type, evidence_id) not in existing:
        conclusion.setdefault("evidence_refs", []).append(ref)
        conclusion["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _conclusion_path(conclusion_id).write_text(
            json.dumps(conclusion, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return conclusion


def delete_conclusion(conclusion_id: str) -> bool:
    f = _conclusion_path(conclusion_id)
    if not f.exists():
        return False
    f.unlink()
    return True


def update_conclusion(
    conclusion_id: str,
    text: str | None = None,
    confidence: str | None = None,
    hypothesis_id: str | None = None,
) -> dict | None:
    """更新 Conclusion 内容"""
    conclusion = get_conclusion(conclusion_id)
    if conclusion is None:
        return None
    if text is not None:
        conclusion["text"] = text.strip()
    if confidence in VALID_CONFIDENCE:
        conclusion["confidence"] = confidence
    if hypothesis_id is not None:
        conclusion["hypothesis_id"] = hypothesis_id
    conclusion["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _conclusion_path(conclusion_id).write_text(
        json.dumps(conclusion, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return conclusion


def get_conclusions_by_evidence(evidence_type: str, evidence_id: str) -> list[dict]:
    """反向追溯查询：查找所有引用了指定证据（实验/论文/数据集/Artifact）的科研结论"""
    if not CONCLUSIONS_DIR.exists():
        return []
    matched = []
    for f in sorted(CONCLUSIONS_DIR.glob("conc_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for ref in data.get("evidence_refs", []):
                if ref.get("type") == evidence_type and ref.get("id") == evidence_id:
                    matched.append(data)
                    break
        except Exception:
            pass
    return matched
