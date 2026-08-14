"""
评测集自动化回归（LLM-as-Judge + 字段覆盖率）。

用途（产品叙事）：
- 把一批「黄金样例」（输入日志 → 期望抽取的字段/结论）固化成评测集；
- 每次改动抽取模型或提示词后，自动跑一遍，得到 通过率 / 平均分；
- 若分数回退，说明改动引入了退化——这就是「迭代不降质」的工程保障。

评分方式：
- 字段覆盖率 field_score：期望的 task/dataset/model（以及 error_type）是否被正确抽中；
- 大模型裁判 judge_score：用已有的 LLM-as-Judge（evaluate_answer）对生成的复盘报告打分（0-10）；
- 综合分 combined = 0.5 × field_score + 0.5 × judge_norm；
- 单条通过 = combined ≥ 阈值（默认 0.7）。

LLM 未配置时 judge 自动退化为规则评分，因此离线也能跑通（CI 友好）。
"""

import json
from pathlib import Path

from src.storage import DATA_DIR
from src.agent import ExperimentAgent
from src.tools.report_tool import generate_markdown_report
from src.tools.data_analysis_tool import evaluate_answer


DEFAULT_DATASET = DATA_DIR / "eval_dataset.json"


def _field_hit(expected_sub: str, actual: str) -> bool:
    if not expected_sub:
        return True
    return expected_sub.strip().lower() in (actual or "").lower()


def _score_case(case: dict, record: dict, report: str) -> dict:
    expected = case.get("expected", {})

    # 1) 字段覆盖率
    required = []
    field_detail = {}
    for key in ("task", "dataset", "model"):
        exp = expected.get(key, "")
        if exp:
            required.append(key)
            field_detail[key] = _field_hit(exp, record.get(key, ""))

    error_ok = True
    if expected.get("error_type"):
        required.append("error_type")
        err_types = {e.get("type", "") for e in (record.get("errors") or [])}
        error_ok = expected["error_type"] in err_types and bool(record.get("errors"))
        field_detail["error_type"] = error_ok

    passed_fields = sum(1 for k in required if field_detail.get(k))
    field_score = (passed_fields / len(required)) if required else 1.0

    # 2) 大模型裁判（0-10）
    judge = evaluate_answer(
        question="请基于以下实验日志生成结构化复盘摘要",
        answer=report,
        ground_truth=expected.get("summary", ""),
    )
    judge_norm = (judge.get("total_score", 0) or 0) / 10.0

    # 3) 综合分
    combined = round(0.5 * field_score + 0.5 * judge_norm, 3)
    threshold = case.get("min_combined", 0.7)
    passed = combined >= threshold

    notes = []
    for k in required:
        if not field_detail.get(k):
            notes.append(f"字段未命中: {k}")
    if judge.get("method") == "rule_based":
        notes.append("裁判为规则退化评分（LLM 未配置）")
    elif judge.get("parse_error"):
        notes.append("裁判 JSON 解析失败，已退化为规则评分")

    return {
        "id": case.get("id", ""),
        "field_score": round(field_score, 3),
        "judge_score": judge.get("total_score", 0),
        "judge_method": judge.get("method", ""),
        "combined": combined,
        "passed": passed,
        "notes": notes,
    }


def run_eval(dataset_path: str | Path | None = None) -> dict:
    """运行评测集回归，返回聚合结果与逐条明细。"""
    dataset_path = Path(dataset_path) if dataset_path else DEFAULT_DATASET
    if not dataset_path.exists():
        raise FileNotFoundError(f"评测集不存在: {dataset_path}")

    cases = json.loads(dataset_path.read_text(encoding="utf-8"))
    if isinstance(cases, dict):
        cases = cases.get("cases", [])

    agent = ExperimentAgent()
    results = []
    for case in cases:
        input_text = case.get("input", "")
        try:
            record = agent.analyze(input_text, source_name=case.get("id", "eval"))
            report = generate_markdown_report(record)
            score = _score_case(case, record, report)
        except Exception as e:
            score = {
                "id": case.get("id", ""),
                "field_score": 0.0,
                "judge_score": 0,
                "judge_method": "error",
                "combined": 0.0,
                "passed": False,
                "notes": [f"分析异常: {e}"],
            }
        results.append(score)

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    avg_combined = round(sum(r["combined"] for r in results) / total, 3) if total else 0.0
    avg_judge = round(sum(r["judge_score"] for r in results) / total, 2) if total else 0.0

    return {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "avg_combined": avg_combined,
        "avg_judge": avg_judge,
        "threshold": 0.7,
        "cases": results,
    }


if __name__ == "__main__":
    out = run_eval()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("\n==== 评测摘要 ====")
    print(f"样例数: {out['total']}  通过: {out['passed']}  通过率: {out['pass_rate']*100:.1f}%")
    print(f"平均分(综合): {out['avg_combined']}  平均分(裁判): {out['avg_judge']}")
    failed = [c["id"] for c in out["cases"] if not c["passed"]]
    if failed:
        print(f"未通过: {', '.join(failed)}")
    else:
        print("全部通过 ✅")
