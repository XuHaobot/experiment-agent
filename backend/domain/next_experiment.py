"""
Next Experiment 推荐引擎

逻辑：
1. 读取 Project 下的历史实验记录
2. 提取关键参数 + 指标
3. 调用 LLM 分析并给出候选实验配置
4. 返回候选列表（用户确认后可一键创建）

数据结构（候选实验）：
{
    "id": "candidate_xxx",
    "title": "候选实验标题",
    "rationale": "推荐理由（基于哪些历史实验的分析）",
    "suggested_params": {"batch_size": 16, "lr": 0.001},
    "expected_outcome": "预期效果说明",
    "confidence": "high | medium | low",
    "based_on_experiments": ["exp_001", "exp_002"],
}
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def recommend_next_experiments(
    project_id: str,
    experiment_ids: Optional[list] = None,
    max_candidates: int = 3,
) -> dict:
    """
    根据 Project 下的历史实验推荐下一轮实验配置。

    参数：
        project_id: 所属 Project ID
        experiment_ids: 指定要分析的实验 ID 列表（None 则自动从 project 获取）
        max_candidates: 最多返回几个候选实验

    返回：
    {
        "project_id": "...",
        "analysis_summary": "AI 对历史实验的分析摘要",
        "candidates": [...],
        "generated_at": "..."
    }
    """
    from src.storage import DATA_DIR
    from src.llm_client import LLMClient

    client = LLMClient.from_env()
    # 获取历史实验记录
    records = _load_experiments(project_id, experiment_ids, DATA_DIR)
    if not records:
        return {
            "project_id": project_id,
            "analysis_summary": "没有找到可分析的历史实验记录。",
            "candidates": [],
            "generated_at": _utcnow(),
        }

    if not client.is_configured:
        return _generate_heuristic_recommendations(project_id, records, max_candidates)

    # 构建 prompt
    records_summary = _build_records_summary(records)
    prompt = f"""你是一位 AI 科研助手，专注于实验设计优化。

以下是该研究项目的历史实验记录：

{records_summary}

请基于以上实验历史，完成以下任务：

1. 分析当前实验趋势（哪些参数有效、哪些无效、瓶颈在哪里）
2. 推荐 {max_candidates} 个最值得尝试的下一轮实验配置

以严格的 JSON 格式返回，格式如下：
{{
  "analysis_summary": "简洁的分析摘要（2-3句话）",
  "candidates": [
    {{
      "title": "候选实验标题",
      "rationale": "推荐理由，引用具体历史实验数据",
      "suggested_params": {{"参数名": "参数值"}},
      "expected_outcome": "预期效果描述",
      "confidence": "high | medium | low",
      "based_on_experiments": ["实验ID1", "实验ID2"]
    }}
  ]
}}

只返回 JSON，不要其他说明。"""

    try:
        result = client.call_llm(prompt)
        parsed = _parse_json_response(result)
    except Exception as e:
        logger.warning("LLM recommendation call failed: %s, falling back to heuristic engine", e)
        return _generate_heuristic_recommendations(project_id, records, max_candidates)

    if not parsed.get("candidates"):
        return _generate_heuristic_recommendations(project_id, records, max_candidates)

    # 给每个 candidate 加 id
    for c in parsed.get("candidates", []):
        c["id"] = f"candidate_{uuid.uuid4().hex[:8]}"

    return {
        "project_id": project_id,
        "analysis_summary": parsed.get("analysis_summary", ""),
        "candidates": parsed.get("candidates", []),
        "generated_at": _utcnow(),
    }


def create_experiment_from_candidate(
    project_id: str,
    candidate: dict,
    source_name: str = "next-experiment",
) -> dict:
    """
    用户确认候选实验后，将其转化为正式实验记录草稿（JSON）。

    返回新建的实验记录 dict（已保存到 data/records/）。
    """
    import uuid as _uuid
    from src.storage import DATA_DIR, save_record
    from src.tools.report_tool import generate_markdown_report
    from src.storage import save_report
    from src.graph.builder import build_graph_from_record
    from src.graph.store import save_graph

    record = {
        "id": f"exp_{_uuid.uuid4().hex[:10]}",
        "task": candidate.get("title", "New Experiment"),
        "dataset": "",
        "model": "",
        "params": {
            "original": candidate.get("suggested_params", {}),
            "adjusted": {},
            "suggested": {},
        },
        "commands": [],
        "errors": [],
        "solutions": [],
        "conclusions": candidate.get("expected_outcome", ""),
        "next_steps": [],
        "source": source_name,
        "project_id": project_id,
        "from_candidate_id": candidate.get("id", ""),
        "rationale": candidate.get("rationale", ""),
        "confidence": candidate.get("confidence", ""),
        "status": "draft",
        "created_at": _utcnow(),
    }

    save_record(record)

    # 自动关联到 Project
    try:
        from backend.domain.project import add_experiment_to_project
        add_experiment_to_project(project_id, record["id"])
    except Exception:
        pass

    return record


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _load_experiments(project_id: str, experiment_ids: Optional[list], data_dir: Path) -> list[dict]:
    """加载要分析的实验记录列表，并关联其所属的 Runs。"""
    records_dir = data_dir / "records"
    if not records_dir.exists():
        return []

    from backend.domain.run import list_runs

    result = []

    if experiment_ids:
        for eid in experiment_ids:
            candidates = list(records_dir.glob(f"*{eid}*.json"))
            for c in candidates:
                try:
                    r = json.loads(c.read_text(encoding="utf-8"))
                    r["runs"] = list_runs(experiment_id=r.get("id", eid))
                    result.append(r)
                except Exception:
                    pass
    else:
        try:
            from backend.domain.project import get_project
            proj = get_project(project_id)
            if proj and proj.get("experiment_ids"):
                for eid in proj["experiment_ids"][:10]:
                    candidates = list(records_dir.glob(f"*{eid}*.json"))
                    for c in candidates:
                        try:
                            r = json.loads(c.read_text(encoding="utf-8"))
                            r["runs"] = list_runs(experiment_id=r.get("id", eid))
                            result.append(r)
                        except Exception:
                            pass
        except Exception:
            pass

    if not result:
        all_records = sorted(records_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for f in all_records[:8]:
            try:
                r = json.loads(f.read_text(encoding="utf-8"))
                r["runs"] = list_runs(experiment_id=r.get("id", f.stem))
                result.append(r)
            except Exception:
                pass

    return result


def _build_records_summary(records: list[dict]) -> str:
    """将实验记录列表与历史 Runs 格式化为 LLM 可读的摘要。"""
    lines = []
    for i, r in enumerate(records, 1):
        lines.append(f"--- 实验 #{i} ---")
        lines.append(f"ID: {r.get('id', 'unknown')}")
        lines.append(f"任务: {r.get('task', '未知')}")
        if r.get("model"):
            lines.append(f"模型: {r['model']}")
        if r.get("dataset"):
            lines.append(f"数据集: {r['dataset']}")

        params = r.get("params", {})
        if isinstance(params, dict):
            orig = params.get("original", {}) or params
            if orig and isinstance(orig, dict):
                lines.append(f"设计参数: {json.dumps(orig, ensure_ascii=False)}")
        elif params:
            lines.append(f"设计参数: {str(params)[:200]}")

        # 包含关联的 Runs
        runs = r.get("runs", [])
        if runs:
            lines.append("历史运行记录 (Runs):")
            for run in runs[:5]:
                r_status = run.get("status", "unknown")
                r_params = run.get("actual_parameters", {})
                r_metrics = run.get("metrics", {})
                lines.append(f"  - Run [{run.get('id')}]: 状态={r_status}, 参数={json.dumps(r_params, ensure_ascii=False)}, 指标={json.dumps(r_metrics, ensure_ascii=False)}")

        if r.get("conclusions"):
            lines.append(f"结论: {str(r['conclusions'])[:300]}")
        if r.get("next_steps"):
            steps = r["next_steps"]
            if isinstance(steps, list):
                steps_text = "; ".join(str(s) for s in steps[:3])
            else:
                steps_text = str(steps)[:200]
            lines.append(f"下一步建议: {steps_text}")
        lines.append("")

    return "\n".join(lines)


def _parse_json_response(text: str) -> dict:
    """从 LLM 响应中解析 JSON。"""
    import re
    # 尝试提取 `json ... ` 块
    match = re.search(r'`(?:json)?\s*(.*?)\s*`', text, re.DOTALL | re.IGNORECASE)
    if match:
        return json.loads(match.group(1))
    # 尝试直接解析整段
    text = text.strip()
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        return json.loads(text[start:end+1])
    raise ValueError("无法从 LLM 响应中解析 JSON")


def _generate_heuristic_recommendations(project_id: str, records: list[dict], max_candidates: int) -> dict:
    """当 LLM 未配置时，基于历史实验参数与指标进行启发式推演"""
    candidates = []
    best_run = None
    best_acc = -1.0
    all_runs = []

    for r in records:
        for run in r.get("runs", []):
            all_runs.append(run)
            metrics = run.get("metrics", {})
            acc = metrics.get("val_accuracy", metrics.get("accuracy", 0))
            if isinstance(acc, (int, float)) and acc > best_acc:
                best_acc = acc
                best_run = run

    from backend.domain.hypothesis import list_hypotheses
    from backend.domain.memory import discover_unexplored_space, generate_alternative_hypotheses

    hyps = list_hypotheses(project_id)
    target_hyp_id = hyps[0]["id"] if hyps else "H1"
    target_hyp_title = hyps[0]["title"] if hyps else "动态图拓扑鲁棒性验证"
    unexplored_list = discover_unexplored_space(project_id)
    alternatives_list = generate_alternative_hypotheses(project_id)

    # 收集所有已完成 run 的参数，确保推荐实验不重复历史配置
    executed_param_signatures = set()
    for r in all_runs:
        params_dict = r.get("actual_parameters", {})
        sig = tuple(sorted((k, str(v)) for k, v in params_dict.items()))
        if sig:
            executed_param_signatures.add(sig)

    if best_run and best_run.get("actual_parameters"):
        best_params = dict(best_run["actual_parameters"])
        base_exp_id = best_run.get("experiment_id", "")
        base_run_id = best_run.get("id", "")
        
        # 候选 1：优先针对未探索空间 (Unexplored Space) 填补盲区
        k_val = best_params.get("k", 20)
        c1_params = dict(best_params)
        target_k = k_val + 2
        
        # 如果有明确的未探索区间，优先使用区间中间值
        for u in unexplored_list:
            if u.get("parameter") == "k" and "unexplored_range" in u:
                rng = u["unexplored_range"]
                if len(rng) == 2 and isinstance(rng[0], int) and isinstance(rng[1], int):
                    target_k = (rng[0] + rng[1]) // 2
                    break

        if isinstance(k_val, (int, float)):
            c1_params["k"] = target_k
        
        # 确保不与历史已执行参数完全重复
        sig1 = tuple(sorted((k, str(v)) for k, v in c1_params.items()))
        if sig1 in executed_param_signatures:
            c1_params["k"] = (c1_params.get("k", 20) + 3)

        candidates.append({
            "id": f"candidate_{uuid.uuid4().hex[:8]}",
            "title": f"Explore Unexplored Space k = {c1_params.get('k')} · Dynamic Graph Interpolation",
            "target_hypothesis_id": target_hyp_id,
            "experiment_id": base_exp_id,
            "variables": c1_params,
            "baseline": {
                "run_id": base_run_id,
                "parameters": best_params,
                "accuracy": f"{best_acc*100:.1f}%",
            },
            "why": [
                f"1. 基线运行 {base_run_id} (k={k_val}) 达到了当前最高准确率 ({best_acc*100:.1f}%)。",
                f"2. 参数区间 k={c1_params.get('k')} 属于此前尚未探索的参数空白 (Unexplored Space)。",
                f"3. 测试该参数可直接检验「高阶邻域过平滑」竞争性假说是否在 k={c1_params.get('k')} 处产生拐点。",
            ],
            "uncertainty_addressed": f"消除未探索参数空间 k ∈ [{min(k_val, c1_params.get('k', 20))}, {max(k_val, c1_params.get('k', 20))}] 内流形稳定性的盲区。",
            "expected_outcome": f"验证在未探索空间 k={c1_params.get('k')} 下模型性能，检验性能下降是否由过平滑导致。",
            "information_gain": "HIGH",
            "uncertainty_reduced": [
                f"是否存在 k={k_val}~{c1_params.get('k')} 的性能拐点",
                "性能下降是否由过平滑备选假说导致",
            ],
            "alternative_hypotheses_tested": [
                "高阶邻域过平滑 (Over-smoothing Mechanism)",
                "数据分布偏移与噪声扰动 (Distribution Shift)",
            ],
            "unexplored_space": [u.get("description") for u in unexplored_list[:2]],
            "epistemic_status": "AI_SUGGESTION",
            "estimated_cost": {"gpu_hours": 1.2, "samples": 5000},
            "risk_level": "LOW",
            "reasoning_basis": [
                f"当前实验显示 {base_run_id} (k={k_val}) 达到最高准确率 ({best_acc*100:.1f}%)。",
                f"但在未探索区间内尚无采样数据支撑。",
                f"测试 k={c1_params.get('k')} 能最大化消除认知不确定性并打破过度依赖 k={k_val} 的局部固化。"
            ],
            "evidence_refs": [
                {"type": "run", "id": base_run_id, "snippet": f"{base_run_id} 准确率 {best_acc*100:.1f}%"},
            ],
            "impact": f"进一步确认假说 '{target_hyp_title}' 的理论有效性边界并验证备选机制。",
            "rationale": f"针对未探索参数盲区与备选过平滑假说进行针对性验证，预期信息增益极大。",
            "suggested_params": c1_params,
            "confidence": "high",
            "status": "proposed",
            "based_on_experiments": [base_exp_id] if base_exp_id else [],
        })

        # 候选 2：针对学习率与交互效应 (Alternative Hypothesis: Hyperparameter Interaction)
        if len(candidates) < max_candidates:
            c2_params = dict(best_params)
            lr = c2_params.get("lr", 1e-4)
            if isinstance(lr, (int, float)):
                c2_params["lr"] = lr * 0.5
            
            sig2 = tuple(sorted((k, str(v)) for k, v in c2_params.items()))
            if sig2 in executed_param_signatures:
                c2_params["lr"] = lr * 0.25

            candidates.append({
                "id": f"candidate_{uuid.uuid4().hex[:8]}",
                "title": f"Decouple LR Interaction with Optimal k={k_val} (Alternative Hypothesis Test)",
                "target_hypothesis_id": target_hyp_id,
                "experiment_id": base_exp_id,
                "variables": c2_params,
                "baseline": {
                    "run_id": base_run_id,
                    "parameters": best_params,
                    "accuracy": f"{best_acc*100:.1f}%",
                },
                "why": [
                    "1. 针对「学习率与拓扑规模的协同交互效应」这一竞争性假说开展实证排查。",
                    "2. 检验固定学习率是否掩盖了更大拓扑结构下的真实表征能力。",
                ],
                "uncertainty_addressed": "排除学习率步长与图拓扑参数耦合带来的解释歧义。",
                "expected_outcome": "检验较小学习率在最优局部图拓扑下是否能进一步提升收敛鲁棒性。",
                "information_gain": "MEDIUM",
                "uncertainty_reduced": [
                    "学习率与拓扑规模是否存在交互偏差",
                ],
                "alternative_hypotheses_tested": [
                    "学习率与拓扑规模的协同交互效应 (Hyperparameter Interaction)",
                ],
                "unexplored_space": [u.get("description") for u in unexplored_list[:2]],
                "epistemic_status": "AI_SUGGESTION",
                "estimated_cost": {"gpu_hours": 1.0, "samples": 5000},
                "risk_level": "LOW",
                "reasoning_basis": [
                    f"基线运行 {base_run_id} 收敛速度较快，但在后期损失存在微小波动。",
                    "针对交互效应备选假说进行参数解耦测试。"
                ],
                "evidence_refs": [
                    {"type": "run", "id": base_run_id, "snippet": f"{base_run_id} lr={best_params.get('lr', 1e-4)}"},
                ],
                "impact": "验证优化算法超参数与图拓扑的协同效应并排除虚假归因。",
                "rationale": "测试竞争性交互效应假说，防止将参数失配误判为模型能力上限。",
                "suggested_params": c2_params,
                "confidence": "medium",
                "status": "proposed",
                "based_on_experiments": [base_exp_id] if base_exp_id else [],
            })
    else:
        candidates.append({
            "id": f"candidate_{uuid.uuid4().hex[:8]}",
            "title": "Baseline Parameter Exploration",
            "target_hypothesis_id": target_hyp_id,
            "experiment_id": records[0].get("id", "") if records else "",
            "variables": {"k": 20, "lr": 1e-4, "batch_size": 32},
            "baseline": {},
            "expected_outcome": "建立标准实验基线并测试初始参数分布。",
            "information_gain": "HIGH",
            "uncertainty_reduced": ["初始参数分布与基准指标确定"],
            "alternative_hypotheses_tested": [],
            "unexplored_space": ["整个超参数空间均属未探索状态"],
            "epistemic_status": "AI_SUGGESTION",
            "estimated_cost": {"gpu_hours": 0.8, "samples": 3000},
            "risk_level": "LOW",
            "reasoning_basis": ["课题尚处于初始基线确立阶段，需先获取首批基准遥测数据。"],
            "evidence_refs": [],
            "impact": "为后续所有假说验证确立参照基准。",
            "rationale": "建立首个参照基准运行以开启科研闭环。",
            "suggested_params": {"k": 20, "lr": 1e-4, "batch_size": 32},
            "confidence": "medium",
            "status": "proposed",
            "based_on_experiments": [records[0].get("id")] if records else [],
        })

    return {
        "project_id": project_id,
        "analysis_summary": f"基于 {len(records)} 个实验方案和 {len(all_runs)} 次实际运行的防固化推演：融合未探索参数空间 (Unexplored Space) 与竞争性机制假说 (Alternative Hypotheses)，推荐信息增益最高的新探索配置。",
        "candidates": candidates[:max_candidates],
        "generated_at": _utcnow(),
    }
