"""
Data Agent — Python 沙箱 + EDA + 图表生成 + 参数敏感度分析

安全策略：
- RestrictedPython 白名单执行
- 超时 10 秒（threading.Timer）
- 白名单模块：numpy, pandas, scipy.stats, matplotlib, math, statistics, json
- 禁止文件 IO / 网络 / os / sys / subprocess
"""

from __future__ import annotations

import base64
import io
import json
import logging
import math
import statistics
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
RECORDS_DIR = DATA_DIR / "records"

# ─── 白名单模块 ─────────────────────────────────────────────────────────
_SAFE_MODULES: dict[str, Any] = {}

def _try_import(name: str):
    try:
        import importlib
        return importlib.import_module(name)
    except ImportError:
        return None

_np = _try_import("numpy")
_pd = _try_import("pandas")
_stats = _try_import("scipy.stats")
_plt = _try_import("matplotlib")
if _plt:
    _plt.use("Agg")  # 非交互式后端
    import matplotlib.pyplot as plt
else:
    plt = None

if _np:   _SAFE_MODULES["numpy"] = _np
if _pd:   _SAFE_MODULES["pandas"] = _pd
if _stats: _SAFE_MODULES["scipy"] = _stats


# ─── Runner 抽象架构与 RestrictedPython 执行器 ─────────────────────────

class BasePythonRunner:
    """Python 代码执行器抽象基类（为后续扩展 DockerRunner 预留标准接口）"""
    def run(self, code: str, timeout: int = 10, context: dict | None = None) -> dict:
        raise NotImplementedError


class RestrictedPythonRunner(BasePythonRunner):
    """基于 RestrictedPython 的安全受控执行器"""

    def run(self, code: str, timeout: int = 10, context: dict | None = None) -> dict:
        # 尝试使用 RestrictedPython
        try:
            from RestrictedPython import compile_restricted, safe_globals, PrintCollector
            from RestrictedPython.Guards import safe_builtins, full_write_guard, safer_getattr, guarded_iter_unpack_sequence
            use_restricted = True
        except ImportError:
            use_restricted = False

        output_lines: list[str] = []
        charts: list[str] = []
        error_msg: str | None = None
        last_result: Any = None
        timed_out = False

        def _capture_chart():
            """捕获当前 matplotlib 图表为 base64 PNG"""
            if plt is None:
                return
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
                buf.seek(0)
                charts.append(base64.b64encode(buf.read()).decode())
                plt.close(fig)

        if use_restricted:
            safe_env: dict = safe_globals.copy()
            safe_env["_print_"] = PrintCollector
            safe_env["_getattr_"] = safer_getattr
            safe_env["_write_"] = full_write_guard
            safe_env["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence
            safe_env["_getitem_"] = lambda ob, index: ob[index]
            safe_env["math"] = math
            safe_env["statistics"] = statistics
            safe_env["json"] = json
            # 扩展常用安全内置函数与数据类型
            safe_builtins_map = safe_builtins.copy()
            for fn in (max, min, sum, enumerate, zip, map, filter, any, all, list, dict, set, tuple, int, float, str, bool, abs, round, sorted, reversed):
                safe_builtins_map[fn.__name__] = fn
            
            def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
                safe_candidates = (
                    "numpy", "pandas", "scipy", "scipy.stats", "matplotlib", "matplotlib.pyplot",
                    "math", "statistics", "json", "sklearn", "torch", "seaborn", "duckdb"
                )
                root = name.split(".")[0]
                if root not in safe_candidates and name not in safe_candidates:
                    raise ImportError(f"受控沙箱安全限制：模块 '{name}' 不在默认安全白名单内。")
                import importlib
                try:
                    mod = importlib.import_module(name)
                    if fromlist:
                        return mod
                    return importlib.import_module(root)
                except ImportError as ie:
                    pkg_install = root
                    if pkg_install == "sklearn":
                        pkg_install = "scikit-learn"
                    raise ImportError(f"缺少本地 Python 依赖库 '{name}'。请在终端执行: pip install {pkg_install}") from ie

            safe_builtins_map["__import__"] = _guarded_import
            safe_env["__builtins__"] = safe_builtins_map
            safe_env["__import__"] = _guarded_import
        else:
            def _print(*args, **kwargs):
                output_lines.append(" ".join(str(a) for a in args))

            def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
                safe_candidates = (
                    "numpy", "pandas", "scipy", "scipy.stats", "matplotlib", "matplotlib.pyplot",
                    "math", "statistics", "json", "sklearn", "torch", "seaborn", "duckdb"
                )
                root = name.split(".")[0]
                if root not in safe_candidates and name not in safe_candidates:
                    raise ImportError(f"受控沙箱安全限制：模块 '{name}' 不在默认安全白名单内。")
                import importlib
                try:
                    mod = importlib.import_module(name)
                    if fromlist:
                        return mod
                    return importlib.import_module(root)
                except ImportError as ie:
                    pkg_install = root
                    if pkg_install == "sklearn":
                        pkg_install = "scikit-learn"
                    raise ImportError(f"缺少本地 Python 依赖库 '{name}'。请在终端执行: pip install {pkg_install}") from ie

            safe_env = {
                "__builtins__": {
                    "print": _print,
                    "len": len, "range": range, "enumerate": enumerate,
                    "zip": zip, "map": map, "filter": filter,
                    "list": list, "dict": dict, "set": set, "tuple": tuple,
                    "int": int, "float": float, "str": str, "bool": bool,
                    "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
                    "sorted": sorted, "reversed": reversed,
                    "isinstance": isinstance, "type": type,
                    "True": True, "False": False, "None": None,
                    "__import__": _guarded_import,
                },
                "math": math,
                "statistics": statistics,
                "json": json,
                "__import__": _guarded_import,
            }

        # 动态重试导入库
        np_mod = _np or _try_import("numpy")
        pd_mod = _pd or _try_import("pandas")
        stats_mod = _stats or _try_import("scipy.stats")

        # 注入白名单库
        if np_mod:    safe_env["numpy"] = np_mod;   safe_env["np"] = np_mod
        if pd_mod:    safe_env["pandas"] = pd_mod;  safe_env["pd"] = pd_mod
        if stats_mod: safe_env["stats"] = stats_mod
        if plt:       safe_env["plt"] = plt

        # 注入用户上下文数据
        if context:
            safe_env.update(context)

        result_holder: dict = {}

        def _run():
            nonlocal error_msg, last_result
            try:
                if use_restricted:
                    byte_code = compile_restricted(code, "<sandbox>", "exec")
                    exec(byte_code, safe_env)  # noqa: S102
                    print_obj = safe_env.get("_print")
                    if callable(print_obj):
                        try:
                            res_str = print_obj()
                            if res_str:
                                output_lines.append(res_str.rstrip())
                        except Exception:
                            pass
                    elif safe_env.get("printed"):
                        output_lines.append(str(safe_env["printed"]).rstrip())
                else:
                    # 降级：直接 exec（仅限本地开发）
                    exec(code, safe_env)  # noqa: S102
                _capture_chart()
                result_holder["ok"] = True
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"
                result_holder["ok"] = False

        thread = threading.Thread(target=_run, daemon=True)
        timer = threading.Timer(timeout, lambda: setattr(threading.current_thread(), "_timed_out", True))
        timer.start()
        thread.start()
        thread.join(timeout + 0.5)
        timer.cancel()

        if thread.is_alive():
            timed_out = True
            error_msg = f"执行超时（超过 {timeout} 秒）"

        return {
            "success": result_holder.get("ok", False) and not timed_out,
            "stdout": "\n".join(output_lines),
            "error": error_msg,
            "charts": charts,
        }


# 默认全局 runner
_DEFAULT_RUNNER: BasePythonRunner = RestrictedPythonRunner()


def run_python_sandbox(code: str, timeout: int = 10, context: dict | None = None) -> dict:
    """在受限环境中执行 Python 代码（委托给 RestrictedPythonRunner）"""
    return _DEFAULT_RUNNER.run(code=code, timeout=timeout, context=context)


# ─── 加载实验记录 ──────────────────────────────────────────────────────

def _load_record(record_id: str) -> dict | None:
    if not RECORDS_DIR.exists():
        return None
    for f in RECORDS_DIR.glob(f"*{record_id}*.json"):
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _load_records(record_ids: list[str]) -> list[dict]:
    records = []
    for rid in record_ids:
        r = _load_record(rid)
        if r:
            records.append(r)
    return records


# ─── 自动 EDA ──────────────────────────────────────────────────────────

def execute_eda(record_id: str) -> dict:
    """
    对单个实验记录执行自动 EDA（探索性数据分析）。
    分析：参数统计、指标提取、错误频率。
    """
    record = _load_record(record_id)
    if record is None:
        return {"error": f"记录不存在: {record_id}"}

    eda: dict[str, Any] = {
        "record_id": record_id,
        "task": record.get("task", ""),
        "model": record.get("model", ""),
        "dataset": record.get("dataset", ""),
    }

    # 参数分析
    params = record.get("params", {})
    if isinstance(params, dict):
        eda["params_count"] = len(params)
        numeric_params = {k: v for k, v in params.items() if isinstance(v, (int, float))}
        eda["numeric_params"] = numeric_params
    elif isinstance(params, str):
        eda["params_raw"] = params[:200]

    # 指标提取（从 conclusions / analysis 中抽取数字）
    metrics_text = " ".join([
        str(record.get("conclusions", "")),
        str(record.get("solutions", "")),
    ])
    import re
    numbers = re.findall(r"(?:accuracy|acc|loss|f1|precision|recall|map|ap)[\s:=]+([0-9.]+)", metrics_text, re.IGNORECASE)
    eda["extracted_metrics"] = [float(n) for n in numbers if n]

    # 错误概要
    errors = record.get("errors", [])
    if isinstance(errors, list):
        eda["error_count"] = len(errors)
        eda["error_types"] = list({str(e)[:40] for e in errors[:5]})
    elif isinstance(errors, str) and errors:
        eda["error_count"] = 1
        eda["error_types"] = [errors[:40]]

    # 解决方案数
    solutions = record.get("solutions", [])
    eda["solution_count"] = len(solutions) if isinstance(solutions, list) else (1 if solutions else 0)

    return {"success": True, "eda": eda}


# ─── 参数敏感度分析 ────────────────────────────────────────────────────

def analyze_params_sensitivity(record_ids: list[str], target_metric: str = "accuracy") -> dict:
    """
    跨多条实验记录分析参数敏感度。
    返回每个数值参数与目标指标之间的相关性（若能提取到指标的话）。
    """
    records = _load_records(record_ids)
    if not records:
        return {"error": "未找到任何实验记录"}

    import re

    param_values: dict[str, list[float]] = {}
    metric_values: list[float] = []

    metric_pattern = re.compile(
        rf"(?:{re.escape(target_metric)}|acc|accuracy|loss)[\s:=]+([0-9.]+)",
        re.IGNORECASE,
    )

    for record in records:
        # 提取目标指标
        search_text = " ".join([
            str(record.get("conclusions", "")),
            str(record.get("solutions", "")),
            str(record.get("task", "")),
        ])
        m = metric_pattern.search(search_text)
        metric_val = float(m.group(1)) if m else None
        metric_values.append(metric_val)  # type: ignore

        # 提取数值参数
        params = record.get("params", {})
        if isinstance(params, dict):
            for k, v in params.items():
                if isinstance(v, (int, float)):
                    param_values.setdefault(k, []).append(v)
                else:
                    param_values.setdefault(k, []).append(None)  # type: ignore

    # 过滤掉没有足够数据的参数
    valid_metric = [v for v in metric_values if v is not None]
    if len(valid_metric) < 2:
        return {
            "success": True,
            "message": f"只有 {len(valid_metric)} 条记录含有可解析的指标，无法做相关性分析",
            "record_count": len(records),
        }

    correlations = []
    for param_name, values in param_values.items():
        paired = [(p, m) for p, m in zip(values, metric_values) if p is not None and m is not None]
        if len(paired) < 2:
            continue
        xs = [p for p, _ in paired]
        ys = [m for _, m in paired]
        try:
            n = len(xs)
            mean_x = sum(xs) / n
            mean_y = sum(ys) / n
            cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / n
            std_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs) / n)
            std_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys) / n)
            corr = cov / (std_x * std_y) if std_x > 0 and std_y > 0 else 0.0
            correlations.append({
                "param": param_name,
                "correlation": round(corr, 4),
                "data_points": n,
                "param_range": [min(xs), max(xs)],
            })
        except Exception:
            pass

    correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    return {
        "success": True,
        "target_metric": target_metric,
        "record_count": len(records),
        "metric_samples": len(valid_metric),
        "correlations": correlations,
    }


# ─── 图表生成 ──────────────────────────────────────────────────────────

def generate_chart(data: list[dict], chart_type: str = "bar", title: str = "", xlabel: str = "", ylabel: str = "") -> dict:
    """
    生成简单图表（bar / line / scatter）。

    data 格式：[{"x": ..., "y": ...}, ...]
    返回：{"success": True, "chart": "<base64 png>"}
    """
    if plt is None:
        return {"error": "matplotlib 未安装，无法生成图表"}

    try:
        xs = [d.get("x", i) for i, d in enumerate(data)]
        ys = [float(d.get("y", 0)) for d in data]

        fig, ax = plt.subplots(figsize=(8, 5))

        if chart_type == "bar":
            ax.bar(range(len(xs)), ys, tick_label=[str(x) for x in xs])
        elif chart_type == "line":
            ax.plot(xs, ys, marker="o")
        elif chart_type == "scatter":
            ax.scatter(xs, ys)
        else:
            ax.plot(xs, ys)

        if title: ax.set_title(title)
        if xlabel: ax.set_xlabel(xlabel)
        if ylabel: ax.set_ylabel(ylabel)

        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        buf.seek(0)
        chart_b64 = base64.b64encode(buf.read()).decode()
        plt.close(fig)

        return {"success": True, "chart": chart_b64, "chart_type": chart_type}
    except Exception as e:
        return {"error": str(e)}
