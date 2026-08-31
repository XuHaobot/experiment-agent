"""
MLflow Experiment Tracking Adapter — 外部实验运行数据同步适配器
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MLflowAdapter:
    """读取本地 mlruns 目录或 MLflow Tracking 服务的数据适配器"""

    def scan_local_mlruns(self, mlruns_dir: str | Path) -> list[dict[str, Any]]:
        """扫描本地 mlruns 目录下的实验列表"""
        p = Path(mlruns_dir).resolve()
        if not p.exists():
            return []

        experiments = []
        for exp_dir in p.iterdir():
            if exp_dir.is_dir() and not exp_dir.name.startswith("."):
                meta_file = exp_dir / "meta.yaml"
                exp_name = exp_dir.name
                if meta_file.exists():
                    try:
                        for line in meta_file.read_text(encoding="utf-8").splitlines():
                            if line.startswith("name:"):
                                exp_name = line.split(":", 1)[1].strip().strip("'\"")
                    except Exception:
                        pass
                
                # 统计 runs
                run_count = sum(1 for r in exp_dir.iterdir() if r.is_dir() and (r / "meta.yaml").exists() or (r / "params").exists())
                experiments.append({
                    "experiment_id": exp_dir.name,
                    "name": exp_name,
                    "path": str(exp_dir),
                    "runs_count": run_count,
                })
        return experiments

    def read_local_run(self, run_dir: str | Path) -> dict[str, Any]:
        """从本地 MLflow run 目录提取超参数与最新指标"""
        rp = Path(run_dir).resolve()
        params = {}
        metrics = {}

        params_dir = rp / "params"
        if params_dir.exists():
            for pf in params_dir.iterdir():
                if pf.is_file():
                    try:
                        v = pf.read_text(encoding="utf-8").strip()
                        try:
                            params[pf.name] = float(v) if "." in v else int(v)
                        except ValueError:
                            params[pf.name] = v
                    except Exception:
                        pass

        metrics_dir = rp / "metrics"
        if metrics_dir.exists():
            for mf in metrics_dir.iterdir():
                if mf.is_file():
                    try:
                        lines = mf.read_text(encoding="utf-8").strip().splitlines()
                        if lines:
                            # 格式为: timestamp value step
                            last_line = lines[-1].split()
                            if len(last_line) >= 2:
                                metrics[mf.name] = float(last_line[1])
                    except Exception:
                        pass

        return {
            "run_id": rp.name,
            "params": params,
            "metrics": metrics,
        }

    def sync_runs_to_experiment(
        self,
        mlflow_exp_dir: str | Path,
        target_experiment_id: str,
    ) -> dict[str, Any]:
        """将本地 MLflow 实验下的所有 Runs 批量同步至 ResearchOS Experiment"""
        from backend.domain.run import create_run
        exp_p = Path(mlflow_exp_dir).resolve()
        if not exp_p.exists():
            return {"success": False, "error": f"MLflow 目录不存在: {mlflow_exp_dir}", "synced": 0}

        created = []
        for r_dir in exp_p.iterdir():
            if r_dir.is_dir() and not r_dir.name.startswith("."):
                run_data = self.read_local_run(r_dir)
                if run_data["params"] or run_data["metrics"]:
                    new_run = create_run(
                        experiment_id=target_experiment_id,
                        actual_parameters=run_data["params"],
                        metrics=run_data["metrics"],
                        status="completed",
                        logs=[f"Synced from MLflow run {run_data['run_id']}"],
                    )
                    created.append(new_run)

        return {
            "success": True,
            "synced_count": len(created),
            "created_runs": created,
        }


mlflow_adapter = MLflowAdapter()
