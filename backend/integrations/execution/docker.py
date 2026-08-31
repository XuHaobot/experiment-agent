"""
Docker Execution Runner Adapter — 强物理容器隔离执行器接口与规范
"""
from __future__ import annotations

import logging
from typing import Any
from backend.integrations.execution.base import ExecutionRunner

logger = logging.getLogger(__name__)


class DockerRunner(ExecutionRunner):
    """
    Docker 强隔离执行器规范：
    - 禁用容器网络访问 (--network none)
    - 内存与 CPU 硬限制 (--memory 1g --cpus 1.5)
    - 临时只读文件系统与安全隔离工作区挂载
    """
    name: str = "docker"

    def __init__(
        self,
        base_image: str = "python:3.11-slim",
        memory_limit: str = "1g",
        cpu_limit: float = 1.5,
    ):
        self.base_image = base_image
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit

    def is_docker_available(self) -> bool:
        """检查 Docker daemon 是否运行中"""
        try:
            import subprocess
            res = subprocess.run(["docker", "info"], capture_output=True, timeout=3)
            return res.returncode == 0
        except Exception:
            return False

    def run_code(
        self,
        code: str,
        timeout: int = 15,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """在隔离 Docker 容器中执行 Python 代码"""
        if not self.is_docker_available():
            logger.warning("Docker daemon is not available, falling back to RestrictedPythonRunner")
            from backend.integrations.execution.base import RestrictedPythonRunner
            return RestrictedPythonRunner().run_code(code, timeout=timeout, context=context)

        # 实际调度 Docker 容器
        try:
            import subprocess
            import tempfile
            from pathlib import Path

            with tempfile.TemporaryDirectory() as tmp_dir:
                script_path = Path(tmp_dir) / "run.py"
                script_path.write_text(code, encoding="utf-8")

                cmd = [
                    "docker", "run", "--rm",
                    "--network", "none",
                    f"--memory={self.memory_limit}",
                    f"--cpus={self.cpu_limit}",
                    "-v", f"{tmp_dir}:/workspace:ro",
                    "-w", "/workspace",
                    self.base_image,
                    "python", "run.py"
                ]

                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                return {
                    "success": proc.returncode == 0,
                    "stdout": proc.stdout,
                    "error": proc.stderr if proc.returncode != 0 else None,
                    "charts": [],
                    "execution_time_ms": 0.0,
                }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "error": f"Docker container execution failed: {str(e)}",
                "charts": [],
                "execution_time_ms": 0.0,
            }
