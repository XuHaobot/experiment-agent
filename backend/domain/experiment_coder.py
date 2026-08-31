"""
Experiment Coder Domain Module — 实验代码生成、受控执行与调试历史管理
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from backend.domain.run import create_run
from backend.domain.artifact import create_artifact
from backend.integrations.execution.base import RestrictedPythonRunner
from backend.integrations.execution.generator import experiment_code_generator
from backend.integrations.execution.debugger import experiment_debugger

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEBUG_LOGS_DIR = DATA_DIR / "debug_logs"


def _ensure_dir():
    DEBUG_LOGS_DIR.mkdir(parents=True, exist_ok=True)


def generate_experiment_code(
    project_id: str,
    experiment_id: str,
    hypothesis_id: str | None = None,
    dataset_id: str | None = None,
    custom_instructions: str | None = None,
) -> dict[str, Any]:
    """根据科研上下文生成实验方案的 Python 脚本"""
    return experiment_code_generator.generate_experiment_code(
        project_id=project_id,
        experiment_id=experiment_id,
        hypothesis_id=hypothesis_id,
        dataset_id=dataset_id,
        custom_instructions=custom_instructions,
    )


def execute_experiment_code_safely(
    project_id: str,
    experiment_id: str,
    code: str,
    timeout: int = 30,
) -> dict[str, Any]:
    """在项目配置的 Python 虚拟环境与工作空间中执行实验脚本，并自动生成 Run 实例与产物"""
    from backend.domain.project import get_project
    from backend.integrations.execution.env_manager import env_manager

    proj = get_project(project_id)
    proj_env = (proj.get("environment") or {}) if proj else {}
    custom_exe = proj_env.get("python_executable")
    custom_cwd = proj_env.get("working_directory")

    if custom_exe:
        # 使用项目绑定的虚拟环境与工作目录执行
        res = env_manager.execute_code(
            code=code,
            python_executable=custom_exe,
            working_dir=custom_cwd,
            timeout=timeout,
        )
    else:
        # 默认使用内置受控执行器
        runner = RestrictedPythonRunner()
        res = runner.run_code(code, timeout=timeout)

    is_success = res.get("success", False) and not res.get("error")
    status = "completed" if is_success else "failed"

    # 提取指标
    metrics = {"execution_success": 1.0 if is_success else 0.0}
    stdout = res.get("stdout", "")
    error_msg = res.get("error")

    # 创建物理 Run
    new_run = create_run(
        experiment_id=experiment_id,
        actual_parameters={"script_executed": True, "code_len": len(code)},
        metrics=metrics,
        status=status,
        logs=[stdout] if is_success else [f"Execution error: {error_msg}"],
    )

    art = None
    if is_success:
        art = create_artifact(
            project_id=project_id,
            name=f"experiment_execution_{new_run['id']}",
            artifact_type="analysis",
            content=json.dumps({
                "code": code,
                "stdout": stdout,
                "charts": res.get("charts", []),
                "run_id": new_run["id"],
            }, ensure_ascii=False, indent=2),
            source_record_id=new_run["id"],
        )

    return {
        "success": is_success,
        "run": new_run,
        "artifact": art,
        "stdout": stdout,
        "error": error_msg,
        "charts": res.get("charts", []),
    }


def debug_experiment_code(
    project_id: str,
    experiment_id: str,
    code: str,
    error_traceback: str,
    retry_count: int = 1,
) -> dict[str, Any]:
    """针对执行报错进行诊断并生成修复补丁"""
    _ensure_dir()
    debug_res = experiment_debugger.debug_code(
        original_code=code,
        error_message=error_traceback,
        retry_count=retry_count,
    )

    # 记录调试日志
    log_record = {
        "project_id": project_id,
        "experiment_id": experiment_id,
        "retry_count": retry_count,
        "error": error_traceback[:200],
        "fix_reason": debug_res.get("fix_reason"),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    log_file = DEBUG_LOGS_DIR / f"debug_{experiment_id}_{int(time.time()*1000)}.json"
    log_file.write_text(json.dumps(log_record, ensure_ascii=False, indent=2), encoding="utf-8")

    return debug_res
