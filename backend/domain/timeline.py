"""
Research Timeline Domain Module — 动态构建真实科研演进时间线
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def get_project_timeline(project_id: str) -> list[dict[str, Any]]:
    """
    聚合 Project 下所有真实对象的生命周期事件，并按时间正序/倒序排列。
    包含事件类型：
    - question_created
    - hypothesis_proposed / hypothesis_updated
    - experiment_created
    - run_completed / run_failed
    - artifact_generated
    - conclusion_reached
    - next_action_proposed
    """
    events: list[dict[str, Any]] = []

    # 1. 加载 Project & Questions
    from backend.domain.project import get_project
    proj = get_project(project_id)
    if not proj:
        return []

    p_created = proj.get("created_at")
    if p_created:
        events.append({
            "id": f"evt_proj_{proj['id']}",
            "timestamp": p_created,
            "event_type": "project_created",
            "title": f"创建研究课题: {proj.get('name')}",
            "description": proj.get("description", ""),
            "entity_id": proj["id"],
            "badge_type": "info",
        })

    for q in proj.get("questions", []):
        events.append({
            "id": f"evt_q_{q['id']}",
            "timestamp": q.get("created_at", p_created),
            "event_type": "question_created",
            "title": f"确立核心科学问题",
            "description": q.get("text", ""),
            "entity_id": q["id"],
            "badge_type": "science",
        })

    # 2. 加载 Hypotheses
    from backend.domain.hypothesis import list_hypotheses
    for h in list_hypotheses(project_id):
        events.append({
            "id": f"evt_hyp_{h['id']}",
            "timestamp": h.get("created_at", p_created),
            "event_type": "hypothesis_proposed",
            "title": f"提出假说: {h.get('title')}",
            "description": h.get("description", ""),
            "entity_id": h["id"],
            "status": h.get("status", "pending"),
            "badge_type": "warning" if h.get("status") == "testing" else ("success" if h.get("status") == "supported" else "neutral"),
        })

    # 3. 加载 Experiments & Runs
    records_dir = DATA_DIR / "records"
    from backend.domain.run import list_runs
    exp_ids = proj.get("experiment_ids", [])
    
    for eid in exp_ids:
        # Load experiment
        exp_file = records_dir / f"{eid}.json"
        if not exp_file.exists():
            matches = list(records_dir.glob(f"*{eid}*.json"))
            if matches:
                exp_file = matches[0]
        
        if exp_file.exists():
            try:
                exp_data = json.loads(exp_file.read_text(encoding="utf-8"))
                e_created = exp_data.get("created_at", p_created)
                events.append({
                    "id": f"evt_exp_{eid}",
                    "timestamp": e_created,
                    "event_type": "experiment_created",
                    "title": f"设计实验方案: {exp_data.get('task', eid)}",
                    "description": f"模型: {exp_data.get('model', 'N/A')} | 数据集: {exp_data.get('dataset', 'N/A')}",
                    "entity_id": eid,
                    "badge_type": "science",
                })
            except Exception:
                pass

        # Load Runs under this experiment
        for r in list_runs(experiment_id=eid):
            r_status = r.get("status", "pending")
            r_metrics = r.get("metrics", {})
            r_params = r.get("actual_parameters", {})
            m_summary = ", ".join([f"{k}={v}" for k, v in r_metrics.items()]) if r_metrics else "无度量数据"
            p_summary = json.dumps(r_params, ensure_ascii=False)

            events.append({
                "id": f"evt_run_{r['id']}",
                "timestamp": r.get("finished_at") or r.get("started_at") or r.get("created_at", p_created),
                "event_type": "run_completed" if r_status == "completed" else "run_dispatched",
                "title": f"执行运行实例 {r['id']} ({r_status.upper()})",
                "description": f"参数: {p_summary} | 指标: {m_summary}",
                "entity_id": r["id"],
                "badge_type": "success" if r_status == "completed" else ("danger" if r_status == "failed" else "warning"),
                "metrics": r_metrics,
                "parameters": r_params,
            })

    # 4. 加载 Artifacts
    from backend.domain.artifact import list_artifacts
    for a in list_artifacts(project_id):
        events.append({
            "id": f"evt_art_{a['id']}",
            "timestamp": a.get("created_at", p_created),
            "event_type": "artifact_generated",
            "title": f"沉淀科研产物: {a.get('name')} (v{a.get('version', 1)})",
            "description": f"类型: {a.get('type')} | 来源: {a.get('source_record_id') or 'N/A'}",
            "entity_id": a["id"],
            "badge_type": "info",
        })

    # 5. 加载 Conclusions
    from backend.domain.conclusion import list_conclusions
    for c in list_conclusions(project_id):
        events.append({
            "id": f"evt_conc_{c['id']}",
            "timestamp": c.get("created_at", p_created),
            "event_type": "conclusion_reached",
            "title": f"沉淀科研结论 ({c.get('confidence', 'medium').upper()})",
            "description": c.get("text", ""),
            "entity_id": c["id"],
            "badge_type": "success" if c.get("confidence") == "high" else "warning",
            "evidence_count": len(c.get("evidence_refs", [])),
        })

    # 6. 加载 Research Sessions (含 Quick Capture 与 External AI 记录)
    from backend.domain.session import list_research_sessions
    for s in list_research_sessions(project_id):
        s_title = s.get("title", "科研工作会话")
        ai_tool = s.get("ai_tool_used", "None")
        desc_parts = []
        if s.get("what_i_did"):
            desc_parts.append(f"操作: {s['what_i_did']}")
        if s.get("what_happened"):
            desc_parts.append(f"结果: {s['what_happened']}")
        if s.get("what_surprised_me"):
            desc_parts.append(f"反思: {s['what_surprised_me']}")
        if ai_tool and ai_tool != "None":
            desc_parts.append(f"AI工具: {ai_tool}")
        if s.get("git_commit"):
            desc_parts.append(f"Commit: {s['git_commit'][:8]}")

        events.append({
            "id": f"evt_sess_{s['id']}",
            "timestamp": s.get("started_at", p_created),
            "event_type": "session_recorded",
            "title": f"科研会话记录: {s_title}",
            "description": " | ".join(desc_parts) if desc_parts else s.get("goal", ""),
            "entity_id": s["id"],
            "badge_type": "info",
        })

    # 7. 加载 Research Diary
    from backend.domain.diary import list_diary_entries
    for d in list_diary_entries(project_id):
        events.append({
            "id": f"evt_diary_{d['id']}",
            "timestamp": d.get("created_at", p_created),
            "event_type": "diary_logged",
            "title": f"科研手记: {d.get('title')}",
            "description": d.get("content", "")[:120],
            "entity_id": d["id"],
            "badge_type": "neutral",
        })

    # 按时间降序排序（最新事件排在最前）
    events.sort(key=lambda e: str(e.get("timestamp", "")), reverse=True)
    return events
