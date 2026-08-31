"""
Epistemic Status Engine — 认识论分级与认知防固化核心定义
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional


class EpistemicStatus(str, Enum):
    OBSERVATION = "OBSERVATION"          # 来自实验、日志、遥测的直接客观观测 (k=20 时 acc=0.91)
    FACT = "FACT"                        # 经多重或可靠来源充分支持的研究事实
    EVIDENCE = "EVIDENCE"                # 支撑或反驳具体假说的证据切片/运行
    INTERPRETATION = "INTERPRETATION"    # 对证据/现象的归因解释 (非既定事实)
    HYPOTHESIS = "HYPOTHESIS"            # 待验证的研究假说
    CONCLUSION = "CONCLUSION"            # 基于证据天平汇总形成的阶段性结论
    FAILED_EXPERIMENT = "FAILED_EXPERIMENT"  # 失败/异常中断的实验，作为永久负知识留存
    ASSUMPTION = "ASSUMPTION"            # 当前默认接受但未系统检验的先验前提
    USER_BELIEF = "USER_BELIEF"          # 用户个人的主观反思与直觉观点 (不可自动升级为事实)
    AI_SUGGESTION = "AI_SUGGESTION"      # AI 提供的推测性假说或建议 (严禁自动升级为事实)


# 严格禁止的状态跃迁规则
FORBIDDEN_AUTOMATIC_UPGRADES = {
    EpistemicStatus.AI_SUGGESTION: {EpistemicStatus.FACT, EpistemicStatus.CONCLUSION, EpistemicStatus.EVIDENCE},
    EpistemicStatus.USER_BELIEF: {EpistemicStatus.FACT, EpistemicStatus.CONCLUSION, EpistemicStatus.EVIDENCE},
    EpistemicStatus.OBSERVATION: {EpistemicStatus.FACT},  # 单一观察必须经过独立重复或证据沉淀方可成为 FACT
}


def can_transition(from_status: EpistemicStatus, to_status: EpistemicStatus, has_human_confirmation: bool = False) -> bool:
    """检查认识论状态是否允许自动或人工升级"""
    if from_status == to_status:
        return True
    
    forbidden_targets = FORBIDDEN_AUTOMATIC_UPGRADES.get(from_status, set())
    if to_status in forbidden_targets:
        # 即使有人工确认，AI_SUGGESTION 也必须先转化为 HYPOTHESIS 并经实验成为 EVIDENCE 后方可形成 CONCLUSION/FACT
        if from_status == EpistemicStatus.AI_SUGGESTION and to_status in (EpistemicStatus.FACT, EpistemicStatus.CONCLUSION):
            return False
        return has_human_confirmation
    return True
