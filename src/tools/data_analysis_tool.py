"""
数据分析工具 — 供 AgentV2 (Function Calling) 调用。

支持三种分析类型:
- param_compare: 对比多条记录的参数差异
- trend:       按时间排列分析指标变化趋势
- summary:     对指定记录做综合摘要
- evaluate:    LLM-as-Judge 评估回答质量 (0-10 分)
"""

import json
from pathlib import Path
from typing import Any

from src.storage import DATA_DIR


RECORDS_DIR = DATA_DIR / "records"


def analyze_data(
    record_ids: list[str],
    analysis_type: str = "summary",
) -> dict:
    """主入口：根据 record_ids 加载记录并执行分析。

    Parameters
    ----------
    record_ids : list[str]
        需要分析的实验记录 ID 列表。
    analysis_type : str
        "param_compare" | "trend" | "summary"

    Returns
    -------
    dict  分析结果，可直接序列化为 JSON 返回给 LLM。
    """
    records = _load_records(record_ids)

    if not records:
        return {"error": "未找到匹配的实验记录", "record_ids": record_ids}

    if analysis_type == "param_compare":
        return _param_compare(records)
    elif analysis_type == "trend":
        return _trend_analysis(records)
    elif analysis_type == "summary":
        return _summary(records)
    elif analysis_type == "evaluate":
        return {"error": "evaluate 类型请使用 evaluate_answer() 函数"}
    else:
        return {"error": f"不支持的分析类型: {analysis_type}"}


# ---------------------------------------------------------------------------
# 参数对比
# ---------------------------------------------------------------------------

def _param_compare(records: list[dict]) -> dict:
    """对比多条记录的参数差异。"""
    comparison: list[dict] = []

    for rec in records:
        params = rec.get("params", {})
        all_params: dict[str, Any] = {}

        if isinstance(params, dict):
            for layer in ("original", "adjusted", "suggested"):
                layer_params = params.get(layer, {})
                if isinstance(layer_params, dict):
                    for k, v in layer_params.items():
                        all_params[f"{layer}.{k}"] = v

        comparison.append({
            "record_id": rec.get("id", ""),
            "task": rec.get("task", ""),
            "model": rec.get("model", ""),
            "dataset": rec.get("dataset", ""),
            "params": all_params,
        })

    # 提取所有唯一参数 key
    all_keys: set[str] = set()
    for item in comparison:
        all_keys.update(item["params"].keys())

    # 找出有差异的参数
    diff_params: dict[str, list] = {}
    for key in sorted(all_keys):
        values = [item["params"].get(key, "—") for item in comparison]
        # 如果所有值都一样，不算差异
        if len(set(str(v) for v in values)) > 1:
            diff_params[key] = values

    return {
        "analysis_type": "param_compare",
        "record_count": len(records),
        "records": comparison,
        "diff_params": diff_params,
        "total_diff_keys": len(diff_params),
    }


# ---------------------------------------------------------------------------
# 趋势分析
# ---------------------------------------------------------------------------

def _trend_analysis(records: list[dict]) -> dict:
    """按创建时间排列，分析指标变化趋势。"""
    # 按 created_at 排序
    sorted_records = sorted(records, key=lambda r: r.get("created_at", ""))

    timeline: list[dict] = []
    for rec in sorted_records:
        entry = {
            "record_id": rec.get("id", ""),
            "created_at": rec.get("created_at", ""),
            "task": rec.get("task", ""),
        }

        # 提取核心参数作为趋势指标
        params = rec.get("params", {})
        if isinstance(params, dict):
            original = params.get("original", {})
            if isinstance(original, dict):
                entry["params"] = original

        # 提取结论关键词
        conclusion = rec.get("conclusion", "")
        entry["conclusion"] = conclusion[:200] if conclusion else ""

        # 错误数量
        errors = rec.get("errors", [])
        entry["error_count"] = len(errors) if isinstance(errors, list) else 0

        timeline.append(entry)

    return {
        "analysis_type": "trend",
        "record_count": len(records),
        "timeline": timeline,
        "time_range": {
            "earliest": sorted_records[0].get("created_at", "") if sorted_records else "",
            "latest": sorted_records[-1].get("created_at", "") if sorted_records else "",
        },
    }


# ---------------------------------------------------------------------------
# 综合摘要
# ---------------------------------------------------------------------------

def _summary(records: list[dict]) -> dict:
    """对指定记录做综合摘要。"""
    tasks: list[str] = []
    models: list[str] = []
    datasets: list[str] = []
    all_errors: list[str] = []
    all_solutions: list[str] = []
    conclusions: list[str] = []

    for rec in records:
        if rec.get("task"):
            tasks.append(rec["task"])
        if rec.get("model"):
            models.append(rec["model"])
        if rec.get("dataset"):
            datasets.append(rec["dataset"])

        errors = rec.get("errors", [])
        if isinstance(errors, list):
            all_errors.extend(str(e) for e in errors)

        solutions = rec.get("solutions", [])
        if isinstance(solutions, list):
            all_solutions.extend(str(s) for s in solutions)

        if rec.get("conclusion"):
            conclusions.append(rec["conclusion"])

    return {
        "analysis_type": "summary",
        "record_count": len(records),
        "tasks": _unique(tasks),
        "models": _unique(models),
        "datasets": _unique(datasets),
        "total_errors": len(all_errors),
        "errors": _unique(all_errors)[:10],
        "total_solutions": len(all_solutions),
        "solutions": _unique(all_solutions)[:10],
        "conclusions": conclusions[:5],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_records(record_ids: list[str]) -> list[dict]:
    """根据 ID 列表加载记录文件。"""
    records: list[dict] = []

    for rid in record_ids:
        # 支持精确 ID 和前缀匹配
        candidates = list(RECORDS_DIR.glob(f"*{rid}*.json")) if RECORDS_DIR.exists() else []
        if not candidates:
            continue

        for path in candidates[:1]:  # 只取第一个匹配
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    records.append(data)
            except (json.JSONDecodeError, OSError):
                continue

    return records


def _unique(items: list[str]) -> list[str]:
    """去重并保持顺序。"""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(item.strip())
    return result


# ---------------------------------------------------------------------------
# LLM-as-Judge 效果评测
# ---------------------------------------------------------------------------

_EVALUATE_PROMPT = """\
你是一个专业的 AI 回答质量评估专家。请根据以下维度对回答进行 0-10 分评分：

## 评估维度
1. **准确性 (0-3分)**：回答是否基于提供的实验数据，有无编造信息
2. **完整性 (0-3分)**：是否覆盖了用户问题的核心要点
3. **实用性 (0-2分)**：回答对用户的实际工作是否有帮助
4. **表达质量 (0-2分)**：是否清晰、专业、有条理

## 用户问题
{question}

## AI 回答
{answer}

{ground_truth_section}

请严格按照以下 JSON 格式输出评分结果（不要输出其他内容）：
```json
{{
  "total_score": <0-10>,
  "accuracy": <0-3>,
  "completeness": <0-3>,
  "usefulness": <0-2>,
  "expression": <0-2>,
  "reason": "<50字以内的评分理由>"
}}
```"""


def evaluate_answer(
    question: str,
    answer: str,
    ground_truth: str | None = None,
) -> dict:
    """用 LLM-as-Judge 评估回答质量，返回 0-10 分评分。

    Parameters
    ----------
    question : str
        用户提出的问题。
    answer : str
        AI 生成的回答。
    ground_truth : str | None
        可选的标准答案或参考信息，用于对比评分。

    Returns
    -------
    dict
        包含 total_score、各维度分数和评分理由。
    """
    from src.llm_client import LLMClient, parse_json_response

    client = LLMClient.from_env()
    if not client.is_configured:
        return _rule_based_evaluate(question, answer)

    ground_truth_section = ""
    if ground_truth:
        ground_truth_section = f"## 参考答案\n{ground_truth}"

    prompt = _EVALUATE_PROMPT.format(
        question=question,
        answer=answer,
        ground_truth_section=ground_truth_section,
    )

    raw = client.call_llm(prompt)
    parsed, error = parse_json_response(raw)

    if parsed is not None:
        # 确保分数在合理范围内
        return {
            "total_score": _clamp(int(parsed.get("total_score", 0)), 0, 10),
            "accuracy": _clamp(int(parsed.get("accuracy", 0)), 0, 3),
            "completeness": _clamp(int(parsed.get("completeness", 0)), 0, 3),
            "usefulness": _clamp(int(parsed.get("usefulness", 0)), 0, 2),
            "expression": _clamp(int(parsed.get("expression", 0)), 0, 2),
            "reason": parsed.get("reason", ""),
            "method": "llm_judge",
        }

    # LLM 返回解析失败，退化为规则评分
    result = _rule_based_evaluate(question, answer)
    result["parse_error"] = error
    return result


def _rule_based_evaluate(question: str, answer: str) -> dict:
    """基于规则的简单评分（LLM 不可用时的退化方案）。"""
    score = 0
    reasons = []

    # 回答长度：太短可能不完整
    if len(answer) < 20:
        reasons.append("回答过短")
    elif len(answer) >= 50:
        score += 2
    elif len(answer) >= 100:
        score += 3

    # 是否包含错误标记
    if answer.startswith(("LLM_CONFIG_ERROR:", "LLM_API_ERROR:", "ERROR")):
        reasons.append("包含错误信息")
        score = max(score - 3, 0)

    # 是否包含"找不到"等消极回复
    negative_phrases = ["找不到相关", "无法回答", "没有相关数据", "抱歉"]
    if any(p in answer for p in negative_phrases):
        score = max(score - 1, 0)
        reasons.append("包含消极回复")

    # 是否有结构化内容（编号列表、分段）
    if any(marker in answer for marker in ["1.", "1）", "- ", "##"]):
        score += 2
        reasons.append("有结构化表达")

    # 是否提及具体实验数据
    data_indicators = ["batch", "lr", "loss", "epoch", "accuracy", "模型", "数据集", "参数"]
    hits = sum(1 for ind in data_indicators if ind.lower() in answer.lower())
    if hits >= 2:
        score += 2
        reasons.append("引用了具体数据")
    elif hits >= 1:
        score += 1

    score = _clamp(score, 0, 10)
    if not reasons:
        reasons.append("基础评分")

    return {
        "total_score": score,
        "accuracy": min(score // 3, 3),
        "completeness": min(score // 3, 3),
        "usefulness": min(score // 4, 2),
        "expression": min(score // 4, 2),
        "reason": "；".join(reasons),
        "method": "rule_based",
    }


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))
