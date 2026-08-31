"""
Active Exploration Engine & Epistemic Pruning Domain Module (Phase 18)

核心能力：
1. 候选实验组合生成引擎 (Candidate Experiment Engine: Type A Exploit, Type B Discriminate, Type C Explore, Type D Replicate)
2. 认识论价值与信息增益评估 (Epistemic Value Formulation)
3. 竞争性假说区分度矩阵 (Hypothesis Discrimination Matrix)
4. 假说认知修剪与资源优化顾问 (Epistemic Pruning Advisor - 不自动物理删除，只提供科学建议)
5. 伪探索与微小变体重复检测 (Duplicate & Pseudo-Exploration Detection)
6. 动态探索-利用天平 (Explore / Exploit Dynamic Balance)
7. 人工确认门禁与因果血缘贯通 (Human Approval & Lineage)
"""
from __future__ import annotations

import json
import logging
import math
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.domain.epistemic import EpistemicStatus
from backend.domain.hypothesis import list_hypotheses, get_hypothesis, update_hypothesis
from backend.domain.memory import (
    build_evidence_balance,
    discover_unexplored_space,
    generate_alternative_hypotheses,
    get_project_research_memory,
)
from backend.domain.project import get_project, add_experiment_to_project
from backend.domain.run import list_runs
from src.storage import RECORDS_DIR, save_record

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class CandidateType(str, Enum):
    EXPLOIT = "EXPLOIT"            # Type A: 验证与优化当前主假说最佳参数邻域
    DISCRIMINATE = "DISCRIMINATE"  # Type B: 专门设计用于区分竞争性假说的判决性实验
    EXPLORE = "EXPLORE"            # Type C: 探索参数空间盲区与全新未知区间
    REPLICATE = "REPLICATE"        # Type D: 重复关键拐点实验以验证统计稳定性与复现度


@dataclass
class CandidateExperiment:
    candidate_id: str
    candidate_type: CandidateType
    title: str
    hypothesis_id: str
    variables: Dict[str, Any]
    expected_information_gain: str  # "HIGH" | "MEDIUM" | "LOW"
    uncertainty_reduction: str
    epistemic_value: str            # "HIGH" | "MEDIUM" | "LOW"
    estimated_cost: Dict[str, Any]
    risk_level: str                 # "LOW" | "MEDIUM" | "HIGH"
    novelty: str                    # "HIGH" | "MEDIUM" | "LOW"
    reasoning_basis: List[str] = field(default_factory=list)
    supporting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    contradicting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    unexplored_region: Dict[str, Any] = field(default_factory=dict)
    alternative_hypotheses_tested: List[str] = field(default_factory=list)
    why_this_experiment: str = ""
    why_not_other_experiments: str = ""
    is_pseudo_exploration: bool = False
    discrimination_scores: Dict[str, str] = field(default_factory=dict)
    epistemic_status: str = EpistemicStatus.AI_SUGGESTION.value

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["candidate_type"] = self.candidate_type.value
        return d


# =============================================================================
# 1. 伪探索与重复实验检测 (Pseudo-Exploration Detection)
# =============================================================================

def detect_pseudo_exploration(
    proposed_params: Dict[str, Any],
    historical_runs: List[Dict[str, Any]],
    threshold_ratio: float = 0.05,
) -> Tuple[bool, str]:
    """
    检查候选参数是否只是历史已充分采样区域的微小增量变体（伪探索）
    """
    if not historical_runs:
        return False, "首组实验，无历史重复。"

    # 1. 完全相同参数检查
    for r in historical_runs:
        hist_p = r.get("actual_parameters", {})
        if hist_p and hist_p == proposed_params:
            return True, f"参数配置与历史运行 {r.get('id')} 完全一致，属于完全重复实验。"

    # 2. 局部饱和微扰检查：检查关键变化变量是否落入饱和区间
    # 只要存在至少一个核心探索参数（如 k）远离历史采样点，就不算伪探索
    saturated_params = []
    novel_params = []

    for p_name, p_val in proposed_params.items():
        if isinstance(p_val, (int, float)):
            tested_vals = []
            for r in historical_runs:
                h_val = r.get("actual_parameters", {}).get(p_name)
                if isinstance(h_val, (int, float)):
                    tested_vals.append(h_val)
            
            if len(tested_vals) >= 3:
                min_t, max_t = min(tested_vals), max(tested_vals)
                span = max_t - min_t
                # 如果所有历史测试点都在密集聚类中 (span <= 3.0)，且新点落入聚类扩展范围内
                if span <= 3.0 and (min_t - 1.5) <= p_val <= (max_t + 1.5):
                    saturated_params.append(p_name)
                elif any(abs(h - p_val) <= max(1.5, abs(h) * threshold_ratio) for h in tested_vals):
                    saturated_params.append(p_name)
                else:
                    novel_params.append(p_name)
            elif tested_vals:
                if any(abs(h - p_val) <= max(1.0, abs(h) * threshold_ratio) for h in tested_vals):
                    saturated_params.append(p_name)
                else:
                    novel_params.append(p_name)
            else:
                novel_params.append(p_name)

    if saturated_params and not novel_params:
        return True, f"参数配置 {saturated_params} 所在局部区间已存在充分采样，继续局部微调预期信息增益极低（伪探索）。"

    return False, "参数具有独立的探索价值。"


# =============================================================================
# 2. 候选实验组合生成引擎 (Candidate Generation Engine)
# =============================================================================

def generate_candidate_experiments(
    project_id: str,
    max_candidates: int = 4,
) -> Dict[str, Any]:
    """
    基于历史运行、假说状态、证据天平、未探索空间与备选解释，生成多范式候选实验组合并排序
    """
    proj = get_project(project_id)
    if not proj:
        raise ValueError(f"Project '{project_id}' not found.")

    hyps = list_hypotheses(project_id)
    all_runs = []
    for eid in proj.get("experiment_ids", []):
        all_runs.extend(list_runs(experiment_id=eid))

    balance = build_evidence_balance(project_id)
    unexplored = discover_unexplored_space(project_id)
    alternatives = generate_alternative_hypotheses(project_id)

    # 寻找最佳历史基准运行
    best_run = None
    best_acc = -1.0
    for r in all_runs:
        metrics = r.get("metrics", {})
        acc = metrics.get("val_accuracy", metrics.get("accuracy", 0))
        if isinstance(acc, (int, float)) and acc > best_acc:
            best_acc = acc
            best_run = r

    primary_hyp_id = hyps[0]["id"] if hyps else "hyp_primary"
    primary_hyp_title = hyps[0]["title"] if hyps else "Primary Research Hypothesis"

    candidates: List[CandidateExperiment] = []

    # -------------------------------------------------------------------------
    # Candidate A: EXPLOIT (主假说深挖与局部精调)
    # -------------------------------------------------------------------------
    if best_run and best_run.get("actual_parameters"):
        b_params = dict(best_run["actual_parameters"])
        base_k = b_params.get("k", 20)
        c_a_params = dict(b_params)
        if isinstance(base_k, (int, float)):
            c_a_params["k"] = base_k + 2
        
        is_pseudo, pseudo_reason = detect_pseudo_exploration(c_a_params, all_runs)
        
        cand_a = CandidateExperiment(
            candidate_id=f"cand_{uuid.uuid4().hex[:8]}",
            candidate_type=CandidateType.EXPLOIT,
            title=f"[Type A · Exploit] Fine-tune neighborhood k={c_a_params.get('k')} around peak {best_run.get('id')}",
            hypothesis_id=primary_hyp_id,
            variables=c_a_params,
            expected_information_gain="MEDIUM",
            uncertainty_reduction=f"在最优参数邻域 k ∈ [{base_k}, {c_a_params.get('k')}] 细化测量，锁定鲁棒性极值点。",
            epistemic_value="MEDIUM",
            estimated_cost={"gpu_hours": 1.0, "sample_size": 5000},
            risk_level="LOW",
            novelty="LOW",
            reasoning_basis=[
                f"历史最佳运行 {best_run.get('id')} 在 k={base_k} 取得最高准确率 ({best_acc*100:.1f}%)。",
                "局部精细插值有助于确认最优参数的具体极值坐标。",
            ],
            supporting_evidence=[
                {"id": best_run.get("id"), "snippet": f"Best run achieved {best_acc*100:.1f}% accuracy"}
            ],
            contradicting_evidence=[],
            why_this_experiment="通过在已知最佳邻域内微调，最大化实验收敛期望并巩固主假说证据。",
            why_not_other_experiments="如果优先追求全新机制发现，该实验的探索新颖性相对较低。",
            is_pseudo_exploration=is_pseudo,
        )
        candidates.append(cand_a)

    # -------------------------------------------------------------------------
    # Candidate B: DISCRIMINATE (竞争性假说判决性实验)
    # -------------------------------------------------------------------------
    if alternatives and best_run:
        b_params = dict(best_run.get("actual_parameters", {}))
        c_b_params = dict(b_params)
        base_k = b_params.get("k", 20)
        # 设计一个测试大 k + 衰减 lr 的解耦实验
        c_b_params["k"] = base_k + 10  # k=30
        c_b_params["lr"] = b_params.get("lr", 1e-4) * 0.2
        
        is_pseudo, _ = detect_pseudo_exploration(c_b_params, all_runs)
        alt_titles = [a.get("hypothesis") for a in alternatives[:2]]

        cand_b = CandidateExperiment(
            candidate_id=f"cand_{uuid.uuid4().hex[:8]}",
            candidate_type=CandidateType.DISCRIMINATE,
            title=f"[Type B · Discriminate] Decoupled Test: k={c_b_params.get('k')} with Scaled LR={c_b_params.get('lr'):.1e}",
            hypothesis_id=primary_hyp_id,
            variables=c_b_params,
            expected_information_gain="HIGH",
            uncertainty_reduction="判别大 k 下性能下降究竟是由「过平滑机制」还是「学习率与拓扑规模失配」导致。",
            epistemic_value="HIGH",
            estimated_cost={"gpu_hours": 1.5, "sample_size": 5000},
            risk_level="MEDIUM",
            novelty="HIGH",
            reasoning_basis=[
                "H1 认为 k=30 性能下降是不可避免的拓扑过平滑；H2 认为固定学习率导致未收敛。",
                "同时调整拓扑与学习率可直接判决 H1 与 H2 谁是主导机制。",
            ],
            alternative_hypotheses_tested=alt_titles,
            discrimination_scores={"H1_Oversmoothing": "HIGH", "H2_LR_Interaction": "HIGH"},
            why_this_experiment="具有最高的假说鉴别力 (Hypothesis Discrimination)，能一次性排除竞争解释。",
            why_not_other_experiments="参数变动幅度较大，存在一定实验失败风险。",
            is_pseudo_exploration=is_pseudo,
        )
        candidates.append(cand_b)

    # -------------------------------------------------------------------------
    # Candidate C: EXPLORE (未知参数盲区探测)
    # -------------------------------------------------------------------------
    if unexplored:
        target_gap = unexplored[0]
        c_c_params = dict(best_run.get("actual_parameters", {"k": 20, "lr": 1e-4})) if best_run else {"k": 25, "lr": 1e-4}
        
        param_name = target_gap.get("parameter", "k")
        if "unexplored_range" in target_gap and len(target_gap["unexplored_range"]) == 2:
            r0, r1 = target_gap["unexplored_range"]
            if isinstance(r0, int) and isinstance(r1, int):
                c_c_params[param_name] = (r0 + r1) // 2
            elif isinstance(r0, (int, float)) and isinstance(r1, (int, float)):
                c_c_params[param_name] = round((r0 + r1) / 2.0, 4)
        else:
            c_c_params[param_name] = 25

        is_pseudo, _ = detect_pseudo_exploration(c_c_params, all_runs)

        cand_c = CandidateExperiment(
            candidate_id=f"cand_{uuid.uuid4().hex[:8]}",
            candidate_type=CandidateType.EXPLORE,
            title=f"[Type C · Explore] Probe Uncharted Parameter Gap {param_name}={c_c_params.get(param_name)}",
            hypothesis_id=primary_hyp_id,
            variables=c_c_params,
            expected_information_gain="HIGH",
            uncertainty_reduction=f"填补参数空间中此前完全未采样的空白区 {target_gap.get('description', '')}。",
            epistemic_value="HIGH",
            estimated_cost={"gpu_hours": 1.2, "sample_size": 5000},
            risk_level="MEDIUM",
            novelty="HIGH",
            unexplored_region=target_gap,
            reasoning_basis=[
                f"参数 '{param_name}' 在当前取值附近尚未进行过任何实验采样。",
                "未知区域往往蕴含非线性拐点或未预料的物理现象。",
            ],
            why_this_experiment="针对参数空间最大盲区进行不确定性采样，最大化科学探索覆盖度。",
            why_not_other_experiments="并非围绕已知最优区域，短期指标回报不确定。",
            is_pseudo_exploration=is_pseudo,
        )
        candidates.append(cand_c)

    # -------------------------------------------------------------------------
    # Candidate D: REPLICATE (关键边界复现与稳定性排查)
    # -------------------------------------------------------------------------
    if best_run:
        c_d_params = dict(best_run.get("actual_parameters", {}))
        c_d_params["seed"] = 4242  # 变换随机种子
        
        cand_d = CandidateExperiment(
            candidate_id=f"cand_{uuid.uuid4().hex[:8]}",
            candidate_type=CandidateType.REPLICATE,
            title=f"[Type D · Replicate] Multi-seed Robustness Check on Best Configuration {best_run.get('id')}",
            hypothesis_id=primary_hyp_id,
            variables=c_d_params,
            expected_information_gain="LOW",
            uncertainty_reduction="排除随机初始化偶然性，确认最佳性能的可复现性与置信区间。",
            epistemic_value="MEDIUM",
            estimated_cost={"gpu_hours": 0.8, "sample_size": 5000},
            risk_level="LOW",
            novelty="LOW",
            reasoning_basis=[
                f"历史运行 {best_run.get('id')} 虽达到最高指标，但仅完成单次随机种子测试。",
                "重复实验能排查虚假峰值并提供可信的误差条 (Error Bars)。",
            ],
            why_this_experiment="验证科学结论的复现性与稳健度，杜绝过拟合与偶然波动。",
            why_not_other_experiments="无法拓展新的参数边界或提出新假说。",
            is_pseudo_exploration=False,
        )
        candidates.append(cand_d)

    # 兜底生成基线
    if not candidates:
        cand_base = CandidateExperiment(
            candidate_id=f"cand_{uuid.uuid4().hex[:8]}",
            candidate_type=CandidateType.EXPLORE,
            title="[Type C · Explore] Initial Baseline Parameter Mapping",
            hypothesis_id=primary_hyp_id,
            variables={"k": 20, "lr": 1e-4, "batch_size": 32},
            expected_information_gain="HIGH",
            uncertainty_reduction="建立首组实验遥测基线，开启课题科学闭环。",
            epistemic_value="HIGH",
            estimated_cost={"gpu_hours": 0.8, "sample_size": 3000},
            risk_level="LOW",
            novelty="HIGH",
            reasoning_basis=["课题尚无基准运行，需先获取首批客观物理遥测数据。"],
            why_this_experiment="建立所有后续实验的参照坐标系。",
            why_not_other_experiments="无。",
            is_pseudo_exploration=False,
        )
        candidates.append(cand_base)

    # -------------------------------------------------------------------------
    # 动态探索-利用天平权重计算 (Explore / Exploit Balance)
    # -------------------------------------------------------------------------
    total_runs = len(all_runs)
    contradicting_count = len(balance.get("contradicting", []))
    
    # 若存在较多反面证据或总运行数较少，提高 EXPLORE / DISCRIMINATE 权重
    if total_runs < 3 or contradicting_count > 0:
        recommended_balance = {"explore_weight": 0.65, "exploit_weight": 0.35, "strategy": "HIGH_UNCERTAINTY_EXPLORATION"}
    else:
        recommended_balance = {"explore_weight": 0.30, "exploit_weight": 0.70, "strategy": "EXPLOITATION_AND_FINE_TUNING"}

    # 排序：优先非伪探索、高认识论价值
    value_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    candidates.sort(
        key=lambda c: (
            not c.is_pseudo_exploration,
            value_rank.get(c.epistemic_value, 0),
            value_rank.get(c.expected_information_gain, 0),
        ),
        reverse=True,
    )

    return {
        "project_id": project_id,
        "total_candidates": len(candidates),
        "recommended_balance": recommended_balance,
        "candidates": [c.to_dict() for c in candidates[:max_candidates]],
        "generated_at": _utcnow(),
    }


# =============================================================================
# 3. 竞争性假说区分度矩阵 (Hypothesis Discrimination Matrix)
# =============================================================================

def build_hypothesis_discrimination_matrix(project_id: str) -> Dict[str, Any]:
    """
    计算各候选实验对所有活动与竞争性假说的区分鉴别能力
    """
    hyps = list_hypotheses(project_id)
    alts = generate_alternative_hypotheses(project_id)
    
    hyp_names = [f"{h.get('id')}: {h.get('title')}" for h in hyps]
    for alt in alts[:2]:
        hyp_names.append(f"AI_ALT: {alt.get('hypothesis')}")

    portfolio = generate_candidate_experiments(project_id, max_candidates=4)
    matrix_rows = []

    for cand in portfolio.get("candidates", []):
        row_predictions = {}
        cand_type = cand.get("candidate_type")

        for h_name in hyp_names:
            if "Oversmoothing" in h_name or "过平滑" in h_name:
                if cand_type == CandidateType.DISCRIMINATE.value:
                    row_predictions[h_name] = "预测准确率随 LR 降低仍无改善 (结构瓶颈)"
                else:
                    row_predictions[h_name] = "预测随 k 增加持续单调衰减"
            elif "Interaction" in h_name or "交互" in h_name:
                if cand_type == CandidateType.DISCRIMINATE.value:
                    row_predictions[h_name] = "预测准确率随 LR 减小大幅回升 (参数失配)"
                else:
                    row_predictions[h_name] = "预测与基准保持一致"
            else:
                row_predictions[h_name] = "预测稳步提升"

        matrix_rows.append({
            "candidate_id": cand.get("candidate_id"),
            "candidate_title": cand.get("title"),
            "candidate_type": cand_type,
            "predictions": row_predictions,
            "discrimination_power": "HIGH" if cand_type == CandidateType.DISCRIMINATE.value else "MEDIUM",
            "epistemic_value": cand.get("epistemic_value"),
        })

    return {
        "project_id": project_id,
        "hypotheses_evaluated": hyp_names,
        "matrix": matrix_rows,
    }


# =============================================================================
# 4. 假说认知修剪与资源优化顾问 (Epistemic Pruning Advisor)
# =============================================================================

def analyze_epistemic_pruning(project_id: str) -> Dict[str, Any]:
    """
    评估所有假说的证据充分度与反驳记录，提出非破坏性的修剪建议（永不自动物理删除假说）
    """
    hyps = list_hypotheses(project_id)
    all_runs = []
    proj = get_project(project_id) or {}
    for eid in proj.get("experiment_ids", []):
        all_runs.extend(list_runs(experiment_id=eid))

    pruning_items = []

    for hyp in hyps:
        hid = hyp.get("id")
        title = hyp.get("title", "")
        status = hyp.get("status", "pending")
        evidence_list = hyp.get("evidence", [])

        # 统计支持与反驳证据
        supp_count = sum(1 for e in evidence_list if isinstance(e, dict) and e.get("supports", True) and str(e.get("polarity", "")).upper() != "CONTRADICT")
        contra_count = sum(1 for e in evidence_list if isinstance(e, dict) and (not e.get("supports", True) or str(e.get("polarity", "")).upper() == "CONTRADICT"))

        # 关联 Run 检查
        failed_runs_count = sum(1 for r in all_runs if r.get("status") == "failed")
        drop_runs_count = sum(1 for r in all_runs if r.get("metrics", {}).get("val_accuracy", 1.0) < 0.80)

        # 状态判定
        if contra_count >= 2 or drop_runs_count >= 2:
            recommended_state = "WEAKENED"
            reason = f"受到 {contra_count} 条反面证据与 {drop_runs_count} 次性能回落运行的严重挑战，假说解释力被削弱。"
            action = "建议降低此假说的实验资源预算，将算力转向竞争性假说。"
        elif supp_count >= 2 and contra_count == 0:
            recommended_state = "SUPPORTED"
            reason = f"已有 {supp_count} 条多源独立证据支持且无反面证据，假说高度可信。"
            action = "主假说已初步成立，建议进入极值微调或撰写科研结论阶段。"
        elif not evidence_list and not all_runs:
            recommended_state = "NEEDS_MORE_EVIDENCE"
            reason = "尚未关联任何实证运行或文献切片数据。"
            action = "建议优先执行基准探索实验收集首批数据。"
        else:
            recommended_state = "ACTIVE"
            reason = f"当前处于积极验证中 (支持: {supp_count}, 反面: {contra_count})。"
            action = "保持正常实验探索进度。"

        pruning_items.append({
            "hypothesis_id": hid,
            "title": title,
            "current_status": status,
            "recommended_status": recommended_state,
            "supporting_evidence_count": supp_count,
            "contradicting_evidence_count": contra_count,
            "reason": reason,
            "pruning_recommendation": action,
            "can_auto_delete": False,  # 绝不允许自动物理删除
        })

    return {
        "project_id": project_id,
        "total_hypotheses": len(hyps),
        "pruning_analysis": pruning_items,
        "advisory_note": "ResearchOS 遵循学术严谨原则，所有修剪建议仅作资源优先级参考，系统绝不自动删除任何科研假说。",
    }


# =============================================================================
# 5. 候选实验审批与血缘绑定 (Human Approval Gate)
# =============================================================================

def approve_candidate_experiment(
    project_id: str,
    candidate_id: str,
    candidate_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    科研人员确认批准候选实验后，安全转化为正式实验记录草稿 (JSON) 并建立项目与假说因果血缘
    """
    proj = get_project(project_id)
    if not proj:
        raise ValueError(f"Project '{project_id}' not found.")

    data = candidate_data
    if not data:
        portfolio = generate_candidate_experiments(project_id, max_candidates=10)
        for c in portfolio.get("candidates", []):
            if c.get("candidate_id") == candidate_id:
                data = c
                break

    if not data:
        raise ValueError(f"Candidate '{candidate_id}' not found in active portfolio.")

    exp_id = f"exp_{uuid.uuid4().hex[:10]}"
    record = {
        "id": exp_id,
        "task": data.get("title", "New Approved Active Exploration Experiment"),
        "dataset": "",
        "model": "",
        "params": {
            "original": data.get("variables", {}),
            "adjusted": {},
            "suggested": {},
        },
        "commands": [],
        "errors": [],
        "solutions": [],
        "conclusions": data.get("expected_outcome", ""),
        "next_steps": [],
        "source": "active-exploration-engine",
        "project_id": project_id,
        "from_candidate_id": candidate_id,
        "candidate_type": data.get("candidate_type", "EXPLORE"),
        "rationale": data.get("why_this_experiment", ""),
        "information_gain": data.get("expected_information_gain", "HIGH"),
        "epistemic_value": data.get("epistemic_value", "HIGH"),
        "hypothesis_id": data.get("hypothesis_id", ""),
        "status": "draft",
        "created_at": _utcnow(),
    }

    save_record(record)
    add_experiment_to_project(project_id, exp_id)

    logger.info("Candidate %s approved by human -> created Experiment %s for project %s", candidate_id, exp_id, project_id)

    return {
        "success": True,
        "experiment_id": exp_id,
        "project_id": project_id,
        "candidate_id": candidate_id,
        "candidate_type": data.get("candidate_type", "EXPLORE"),
        "status": "draft",
        "created_at": record["created_at"],
    }
