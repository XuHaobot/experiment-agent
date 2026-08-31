"""
Research Session Domain Module — 轻量工作会话管理、科研快速记录 (Quick Capture) 与外部 AI 提示词生成
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
SESSIONS_DIR = DATA_DIR / "sessions"


def _ensure_dir():
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sessions_path(project_id: str) -> Path:
    _ensure_dir()
    return SESSIONS_DIR / f"{project_id}.json"


def list_research_sessions(project_id: str) -> List[Dict[str, Any]]:
    """获取指定课题下的所有科研工作会话"""
    p = _sessions_path(project_id)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        sessions = data.get("sessions", [])
        sessions.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        return sessions
    except Exception as e:
        logger.error("Failed to load sessions for %s: %s", project_id, e)
        return []


def create_research_session(
    project_id: str,
    title: str,
    goal: str = "",
    actions_summary: Optional[List[str]] = None,
    visited_papers: Optional[List[str]] = None,
    executed_runs: Optional[List[str]] = None,
    updated_hypotheses: Optional[List[str]] = None,
    reached_conclusions: Optional[List[str]] = None,
    next_step: str = "",
    what_i_did: str = "",
    tools_used: Optional[List[str]] = None,
    what_happened: str = "",
    what_surprised_me: str = "",
    current_belief: str = "",
    ai_tool_used: str = "None",
    git_commit: Optional[str] = None,
) -> Dict[str, Any]:
    """创建并保存一次科研会话记录（支持 Quick Capture 与外部 AI 工具记录）"""
    _ensure_dir()
    sessions = list_research_sessions(project_id)
    
    session_id = f"session_{uuid.uuid4().hex[:10]}"
    now = _utcnow()

    session = {
        "id": session_id,
        "project_id": project_id,
        "title": title.strip(),
        "goal": goal.strip(),
        "what_i_did": what_i_did.strip(),
        "tools_used": tools_used or [],
        "what_happened": what_happened.strip(),
        "what_surprised_me": what_surprised_me.strip(),
        "current_belief": current_belief.strip(),
        "ai_tool_used": ai_tool_used.strip() or "None",
        "git_commit": git_commit,
        "actions_summary": actions_summary or [],
        "visited_papers": visited_papers or [],
        "executed_runs": executed_runs or [],
        "updated_hypotheses": updated_hypotheses or [],
        "reached_conclusions": reached_conclusions or [],
        "next_step": next_step.strip(),
        "epistemic_status": EpistemicStatus.USER_BELIEF.value,
        "started_at": now,
        "finished_at": now,
    }

    sessions.append(session)
    _sessions_path(project_id).write_text(
        json.dumps({"project_id": project_id, "sessions": sessions}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("Saved research session %s for project %s", session_id, project_id)
    return session


def generate_external_prompt(project_id: str, hypothesis_id: Optional[str] = None) -> Dict[str, Any]:
    """
    一键生成面向外部大模型（Codex / Claude Code / ChatGPT）的学术提示词 (Prompt Bridge)
    打包：当前课题、假说、历史最优运行参数、反面失败教训与下一轮探索建议
    """
    from backend.domain.project import get_project
    from backend.domain.hypothesis import get_hypothesis, list_hypotheses
    from backend.domain.run import list_runs
    from backend.domain.memory import discover_unexplored_space

    proj = get_project(project_id)
    if not proj:
        return {"success": False, "error": "Project not found"}

    # 1. 目标假说
    target_hyp = None
    if hypothesis_id:
        target_hyp = get_hypothesis(hypothesis_id)
    if not target_hyp:
        all_hyps = list_hypotheses(project_id)
        if all_hyps:
            target_hyp = all_hyps[0]

    hyp_title = target_hyp.get("title", "未指定假说") if target_hyp else "探索性实验"
    hyp_desc = target_hyp.get("description", "") if target_hyp else ""

    # 2. 扫描历史 Runs（最优与失败）
    exp_ids = proj.get("experiment_ids", [])
    all_runs = []
    for eid in exp_ids:
        all_runs.extend(list_runs(eid))

    best_run = None
    best_metric_val = -1.0
    failed_runs = []

    for r in all_runs:
        metrics = r.get("metrics", {})
        acc = metrics.get("val_accuracy", metrics.get("accuracy", None))
        if isinstance(acc, (int, float)) and acc > best_metric_val:
            best_metric_val = acc
            best_run = r
        if r.get("status") == "failed" or (isinstance(acc, (int, float)) and acc < 0.75):
            failed_runs.append(r)

    # 3. 未探索盲区
    unexplored = discover_unexplored_space(project_id)

    # 4. 构建结构化 Prompt
    lines = [
        f"# 科研任务背景：{proj.get('name', '未命名课题')}",
        f"**当前核心假说**：{hyp_title}",
    ]
    if hyp_desc:
        lines.append(f"**假说机理**：{hyp_desc}")
    
    lines.append("\n## 已验证实验实证 (Empirical Baseline):")
    if best_run:
        b_params = json.dumps(best_run.get("actual_parameters", {}), ensure_ascii=False)
        b_metrics = json.dumps(best_run.get("metrics", {}), ensure_ascii=False)
        lines.append(f"- **最优运行 ({best_run.get('id')})**：参数 `{b_params}` -> 指标 `{b_metrics}`")
    else:
        lines.append("- 暂无高分基线运行记录。")

    if failed_runs:
        lines.append("\n## 失败/性能回落教训 (Negative Lessons to Avoid):")
        for fr in failed_runs[:3]:
            f_params = json.dumps(fr.get("actual_parameters", {}), ensure_ascii=False)
            f_metrics = json.dumps(fr.get("metrics", {}), ensure_ascii=False)
            lines.append(f"- **回落运行 ({fr.get('id')})**：参数 `{f_params}` -> 指标 `{f_metrics}`")

    if unexplored:
        lines.append("\n## 参数空间未知盲区 (Unexplored Gap):")
        for u in unexplored[:3]:
            lines.append(f"- {u}")

    lines.append("\n## 任务请求 (Instruction for Codex / Claude Code):")
    lines.append("请根据以上实验基线与失败教训，为我编写/修改一份改进的 Python 实验脚本：")
    lines.append("1. 设计解耦验证方案，克服上述性能回落瓶颈；")
    lines.append("2. 明确自变量参数字典声明；")
    lines.append("3. 运行后将关键度量指标以 JSON 格式输出至 stdout。")

    prompt_text = "\n".join(lines)

    return {
        "success": True,
        "project_id": project_id,
        "target_hypothesis_id": target_hyp.get("id") if target_hyp else None,
        "prompt_text": prompt_text,
    }
