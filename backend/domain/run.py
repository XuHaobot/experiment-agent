"""
ExperimentRun Domain Module — 实验单次运行实例生命周期管理
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
RUNS_DIR = DATA_DIR / "runs"
RECORDS_DIR = DATA_DIR / "records"
PROJECTS_DIR = DATA_DIR / "projects"


def _ensure_dir():
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _run_path(run_id: str) -> Path:
    return RUNS_DIR / f"{run_id}.json"


def create_run(
    experiment_id: str,
    actual_parameters: dict | None = None,
    dataset: str = "",
    metrics: dict | None = None,
    logs: list[str] | str | None = None,
    artifacts: list[str] | None = None,
    status: str = "pending",
    execution_origin: str = "LOCAL_SANDBOX",  # "LOCAL_SANDBOX" | "EXTERNAL_LOCAL" | "REMOTE_SERVER" | "CODEX" | "CLAUDE_CODE" | "MANUAL" | "IMPORTED"
    git_commit: str | None = None,
    git_branch: str | None = None,
    repository: str | None = None,
    ai_tool_used: str | None = None,
    ai_task_description: str | None = None,
) -> dict:
    """创建并持久化一个 ExperimentRun 实例，支持本地/外部/Codex 执行模式与 Git 血缘"""
    _ensure_dir()
    run_id = f"run_{uuid.uuid4().hex[:10]}"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    run_record: dict[str, Any] = {
        "id": run_id,
        "experiment_id": experiment_id,
        "actual_parameters": actual_parameters or {},
        "dataset": dataset,
        "status": status,  # "pending" | "running" | "completed" | "failed"
        "execution_origin": execution_origin,
        "git_commit": git_commit,
        "git_branch": git_branch,
        "repository": repository,
        "ai_tool_used": ai_tool_used,
        "ai_task_description": ai_task_description,
        "started_at": now if status == "running" else None,
        "finished_at": now if status in ("completed", "failed") else None,
        "metrics": metrics or {},
        "logs": logs if isinstance(logs, list) else ([logs] if logs else []),
        "artifacts": artifacts or [],
        "error": None,
        "created_at": now,
        "updated_at": now,
    }

    _run_path(run_id).write_text(
        json.dumps(run_record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("ExperimentRun created: %s for experiment %s", run_id, experiment_id)
    return run_record


def get_run(run_id: str) -> dict | None:
    """获取 Run 详情"""
    p = _run_path(run_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_runs(experiment_id: str | None = None) -> list[dict]:
    """列出 Run，可选按 experiment_id 过滤"""
    if not RUNS_DIR.exists():
        return []
    runs = []
    for f in sorted(RUNS_DIR.glob("run_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if experiment_id and data.get("experiment_id") != experiment_id:
                continue
            runs.append(data)
        except Exception:
            pass
    return runs


def update_run(
    run_id: str,
    status: str | None = None,
    actual_parameters: dict | None = None,
    dataset: str | None = None,
    metrics: dict | None = None,
    logs: list[str] | str | None = None,
    artifacts: list[str] | None = None,
    error: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> dict | None:
    """更新 Run 状态或遥测数据"""
    run_data = get_run(run_id)
    if not run_data:
        return None

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if status is not None:
        run_data["status"] = status
        if status == "running" and not run_data.get("started_at"):
            run_data["started_at"] = now
        elif status in ("completed", "failed") and not run_data.get("finished_at"):
            run_data["finished_at"] = now
    if actual_parameters is not None:
        run_data["actual_parameters"] = actual_parameters
    if dataset is not None:
        run_data["dataset"] = dataset
    if metrics is not None:
        run_data["metrics"].update(metrics)
    if logs is not None:
        if isinstance(logs, list):
            run_data["logs"].extend(logs)
        else:
            run_data["logs"].append(logs)
    if artifacts is not None:
        run_data["artifacts"] = list(set(run_data.get("artifacts", []) + artifacts))
    if error is not None:
        run_data["error"] = error
    if started_at is not None:
        run_data["started_at"] = started_at
    if finished_at is not None:
        run_data["finished_at"] = finished_at

    run_data["updated_at"] = now
    _run_path(run_id).write_text(
        json.dumps(run_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return run_data


def delete_run(run_id: str) -> bool:
    """删除 Run"""
    p = _run_path(run_id)
    if not p.exists():
        return False
    p.unlink()
    return True


def execute_run_instance(
    run_id: str,
    execution_code: str | None = None,
    timeout: int = 15,
) -> dict:
    """
    执行 Run 实例（实际调度 Python 沙箱执行或参数记录更新）
    """
    run_data = get_run(run_id)
    if not run_data:
        return {"success": False, "error": f"Run 不存在: {run_id}"}

    update_run(run_id, status="running")

    # 如果有指定的执行代码，在沙箱中运行
    if execution_code:
        from backend.domain.data_agent import run_python_sandbox
        res = run_python_sandbox(execution_code, timeout=timeout, context={"run_id": run_id, "params": run_data.get("actual_parameters")})
        if res.get("success"):
            update_run(
                run_id,
                status="completed",
                logs=res.get("stdout", ""),
                metrics=run_data.get("metrics") or {"execution": "success"},
            )
            return {"success": True, "run": get_run(run_id), "output": res.get("stdout")}
        else:
            update_run(
                run_id,
                status="failed",
                error=res.get("error", "Execution failed"),
                logs=res.get("stdout", ""),
            )
            return {"success": False, "run": get_run(run_id), "error": res.get("error")}

    # 默认快速完成
    update_run(run_id, status="completed", metrics=run_data.get("metrics") or {"status": "executed"})
    return {"success": True, "run": get_run(run_id)}


def get_experiment_with_runs(experiment_id: str) -> dict:
    """
    兼容层：获取 Experiment（对应旧 record 或新实验）以及其关联的全部 Runs
    """
    exp_data = None
    if RECORDS_DIR.exists():
        for f in RECORDS_DIR.glob(f"*{experiment_id}*.json"):
            try:
                exp_data = json.loads(f.read_text(encoding="utf-8"))
                break
            except Exception:
                pass

    if not exp_data:
        exp_data = {"id": experiment_id, "name": experiment_id}

    runs = list_runs(experiment_id)
    # 如果没有显式 runs，但旧 record 自身包含参数/结论/错误，则自动合成一个基准 Run 展示
    if not runs and "params" in exp_data:
        runs = [{
            "id": f"run_base_{experiment_id[:8]}",
            "experiment_id": experiment_id,
            "actual_parameters": exp_data.get("params") if isinstance(exp_data.get("params"), dict) else {},
            "dataset": exp_data.get("dataset", ""),
            "status": "completed",
            "metrics": {},
            "logs": exp_data.get("errors", []),
            "artifacts": [],
            "created_at": exp_data.get("created_at", ""),
            "synthetic": True,
        }]

    return {
        "experiment": exp_data,
        "runs": runs,
    }


def import_runs_from_csv(experiment_id: str, csv_text: str) -> dict[str, Any]:
    """
    从 CSV 文本中自动解析并批量创建 Experiment Runs。
    - 自动识别表头中的参数列与指标列。
    - 智能转换浮点数与整数值。
    """
    import csv
    import io

    lines = [line.strip() for line in csv_text.strip().splitlines() if line.strip()]
    if not lines:
        return {"success": False, "error": "CSV 内容为空", "created_runs": []}

    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    if not reader.fieldnames:
        return {"success": False, "error": "无法解析 CSV 表头", "created_runs": []}

    known_metric_keys = {
        "acc", "accuracy", "val_acc", "val_accuracy", "test_acc", "test_accuracy",
        "loss", "val_loss", "test_loss", "f1", "macro_f1", "f1_score",
        "precision", "recall", "auc", "auroc", "score", "runtime", "time_sec",
    }

    created_runs = []
    for row in reader:
        params = {}
        metrics = {}
        for col_name, val_str in row.items():
            if col_name is None:
                continue
            k_clean = col_name.strip()
            v_clean = val_str.strip() if isinstance(val_str, str) else val_str
            # 尝试转数字
            parsed_val = v_clean
            try:
                if "." in str(v_clean):
                    parsed_val = float(v_clean)
                else:
                    parsed_val = int(v_clean)
            except (ValueError, TypeError):
                parsed_val = v_clean

            if k_clean.lower() in known_metric_keys or any(m in k_clean.lower() for m in ["acc", "loss", "f1", "metric", "score"]):
                metrics[k_clean] = parsed_val
            else:
                params[k_clean] = parsed_val

        run_rec = create_run(
            experiment_id=experiment_id,
            actual_parameters=params,
            metrics=metrics,
            status="completed" if metrics else "pending",
            logs=[f"Imported from CSV row: {json.dumps(row, ensure_ascii=False)}"],
        )
        created_runs.append(run_rec)

    logger.info("Imported %d runs from CSV into experiment %s", len(created_runs), experiment_id)
    return {
        "success": True,
        "count": len(created_runs),
        "created_runs": created_runs,
    }


def compare_runs(run_ids: list[str]) -> dict[str, Any]:
    """
    横向多 Run 对比引擎，提取公共/差异参数、指标分布与最优表现
    """
    selected_runs: list[dict[str, Any]] = []
    for rid in run_ids:
        r = get_run(rid)
        if r:
            selected_runs.append(r)

    if not selected_runs:
        return {
            "runs": [],
            "param_keys": [],
            "metric_keys": [],
            "comparison_matrix": [],
            "best_run_id": None,
            "insights": "未选择有效的 Run 实例进行对比。",
        }

    param_keys_set = set()
    metric_keys_set = set()

    for r in selected_runs:
        for k in r.get("actual_parameters", {}).keys():
            param_keys_set.add(k)
        for k in r.get("metrics", {}).keys():
            metric_keys_set.add(k)

    param_keys = sorted(list(param_keys_set))
    metric_keys = sorted(list(metric_keys_set))

    matrix = []
    best_run = None
    best_acc = -1.0

    for r in selected_runs:
        rid = r.get("id")
        params = r.get("actual_parameters", {})
        metrics = r.get("metrics", {})
        status = r.get("status", "unknown")

        # 寻找主要 accuracy 指标
        acc = metrics.get("val_accuracy", metrics.get("accuracy", None))
        if isinstance(acc, (int, float)) and acc > best_acc:
            best_acc = acc
            best_run = rid

        matrix.append({
            "run_id": rid,
            "experiment_id": r.get("experiment_id"),
            "status": status,
            "parameters": {k: params.get(k, "-") for k in param_keys},
            "metrics": {k: metrics.get(k, "-") for k in metric_keys},
            "artifacts_count": len(r.get("artifacts", [])),
            "created_at": r.get("created_at"),
        })

    insight_lines = [f"已对比 {len(selected_runs)} 个运行实例。"]
    if best_run:
        insight_lines.append(f"最优表现为 {best_run} (最高指标: {best_acc*100:.1f}%)。")
    if param_keys:
        insight_lines.append(f"涉及自变量参数: {', '.join(param_keys)}。")

    return {
        "runs_count": len(selected_runs),
        "param_keys": param_keys,
        "metric_keys": metric_keys,
        "comparison_matrix": matrix,
        "best_run_id": best_run,
        "insights": " ".join(insight_lines),
    }

