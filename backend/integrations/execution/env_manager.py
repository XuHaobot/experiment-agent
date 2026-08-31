"""
Environment & Workspace Manager — 多课题组/多虚拟环境与工作目录管理适配器
支持：
- 自动扫描本机已有 Python 虚拟环境（venv, conda, 系统安装）
- 项目级自定义虚拟环境与工作空间绑定
- 跨环境依赖库与 CUDA/GPU 自动自检
- 隔离子进程受控执行（带图表自动捕获）
"""
from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class EnvironmentManager:
    """本地虚拟环境与工作空间管理器"""

    def scan_environments(self) -> list[dict[str, Any]]:
        """扫描本机所有可用 Python 虚拟环境"""
        found_envs: list[dict[str, Any]] = []
        seen_paths: set[str] = set()

        def _add_env(name: str, exe_path: Path, env_type: str):
            resolved = str(exe_path.resolve())
            if resolved in seen_paths or not exe_path.exists():
                return
            seen_paths.add(resolved)
            
            # 快速探测版本
            ver_str = ""
            try:
                out = subprocess.check_output(
                    [str(exe_path), "-c", "import sys; print(sys.version.split()[0])"],
                    timeout=2,
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
                ver_str = out.strip()
            except Exception:
                ver_str = "Python"

            found_envs.append({
                "name": name,
                "executable": resolved,
                "version": ver_str,
                "type": env_type,
                "is_current": (resolved == str(Path(sys.executable).resolve())),
            })

        # 1. 当前运行的 Python
        cur_exe = Path(sys.executable)
        _add_env("当前项目环境 (Default Venv)", cur_exe, "current_venv")

        # 2. 项目目录下的常见虚拟环境
        for venv_name in ["venv", ".venv", "env", ".env"]:
            if sys.platform == "win32":
                p = PROJECT_ROOT / venv_name / "Scripts" / "python.exe"
            else:
                p = PROJECT_ROOT / venv_name / "bin" / "python"
            if p.exists():
                _add_env(f"项目本地环境 ({venv_name})", p, "local_venv")

        # 3. 扫描 Conda 环境
        conda_bin = shutil.which("conda")
        if conda_bin:
            try:
                out = subprocess.check_output(
                    ["conda", "info", "--envs", "--json"],
                    timeout=3,
                    text=True,
                    stderr=subprocess.DEVNULL,
                )
                data = json.loads(out)
                for env_dir in data.get("envs", []):
                    p_env = Path(env_dir)
                    if sys.platform == "win32":
                        p_exe = p_env / "python.exe"
                    else:
                        p_exe = p_env / "bin" / "python"
                    if p_exe.exists():
                        env_label = f"Conda: {p_env.name}"
                        _add_env(env_label, p_exe, "conda")
            except Exception as e:
                logger.debug(f"Conda scan failed: {e}")

        # 4. 扫描 Conda 常见目录
        home = Path.home()
        conda_search_roots = [
            home / "anaconda3" / "envs",
            home / "miniconda3" / "envs",
            home / ".conda" / "envs",
            Path("C:/ProgramData/anaconda3/envs"),
            Path("C:/ProgramData/miniconda3/envs"),
            Path("/opt/anaconda3/envs"),
            Path("/opt/miniconda3/envs"),
        ]
        for root in conda_search_roots:
            if root.exists():
                for sub in root.iterdir():
                    if sub.is_dir():
                        if sys.platform == "win32":
                            p_exe = sub / "python.exe"
                        else:
                            p_exe = sub / "bin" / "python"
                        if p_exe.exists():
                            _add_env(f"Conda: {sub.name}", p_exe, "conda")

        # 5. 扫描系统全局 Python 安装 (Windows / Linux / macOS)
        if sys.platform == "win32":
            py_programs = home / "AppData" / "Local" / "Programs" / "Python"
            if py_programs.exists():
                for sub in py_programs.iterdir():
                    p_exe = sub / "python.exe"
                    if p_exe.exists():
                        _add_env(f"System: {sub.name}", p_exe, "system")
        else:
            for sys_p in ["/usr/bin/python3", "/usr/local/bin/python3", "/opt/homebrew/bin/python3"]:
                p_exe = Path(sys_p)
                if p_exe.exists():
                    _add_env(f"System: {p_exe.name}", p_exe, "system")

        return found_envs

    def inspect_environment(
        self,
        python_executable: str,
        working_dir: Optional[str] = None,
    ) -> dict[str, Any]:
        """深度自检指定 Python 环境的详细版本、已安装包与 GPU/CUDA 支持"""
        exe_path = Path(python_executable)
        if not exe_path.exists():
            return {
                "valid": False,
                "error": f"指定的 Python 解释器不存在: {python_executable}",
            }

        target_cwd = working_dir if (working_dir and Path(working_dir).exists()) else str(PROJECT_ROOT)

        probe_code = """
import sys, json

info = {
    "version": sys.version.split()[0],
    "executable": sys.executable,
    "packages": {},
    "cuda": {"available": False, "device_count": 0, "device_name": None}
}

# 探测常见科研库
packages_to_check = [
    ("numpy", "numpy"),
    ("pandas", "pandas"),
    ("scipy", "scipy"),
    ("matplotlib", "matplotlib"),
    ("duckdb", "duckdb"),
    ("scikit-learn", "sklearn"),
    ("torch", "torch"),
    ("torchvision", "torchvision"),
    ("tensorflow", "tensorflow"),
    ("transformers", "transformers"),
    ("seaborn", "seaborn"),
    ("pypdf", "pypdf")
]

for disp_name, mod_name in packages_to_check:
    try:
        mod = __import__(mod_name)
        ver = getattr(mod, "__version__", "installed")
        info["packages"][disp_name] = {"installed": True, "version": str(ver)}
    except ImportError:
        info["packages"][disp_name] = {"installed": False, "install_cmd": f"pip install {disp_name}"}

try:
    import torch
    if torch.cuda.is_available():
        info["cuda"] = {
            "available": True,
            "device_count": torch.cuda.device_count(),
            "device_name": torch.cuda.get_device_name(0),
            "version": torch.version.cuda
        }
except Exception:
    pass

print("___JSON_START___" + json.dumps(info) + "___JSON_END___")
"""

        try:
            res = subprocess.run(
                [str(exe_path), "-c", probe_code],
                cwd=target_cwd,
                capture_output=True,
                text=True,
                timeout=6,
            )
            stdout = res.stdout
            if "___JSON_START___" in stdout:
                json_str = stdout.split("___JSON_START___")[1].split("___JSON_END___")[0]
                data = json.loads(json_str)
                data["valid"] = True
                data["working_directory"] = target_cwd
                return data
            else:
                return {
                    "valid": False,
                    "error": f"自检输出解析失败: {res.stderr or stdout}",
                }
        except subprocess.TimeoutExpired:
            return {"valid": False, "error": "自检环境超时 (6s)"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def execute_code(
        self,
        code: str,
        python_executable: Optional[str] = None,
        working_dir: Optional[str] = None,
        timeout: int = 20,
    ) -> dict[str, Any]:
        """在指定的 Python 环境和工作目录中运行代码并自动捕获 stdout、错误与 Base64 图表"""
        start_time = time.time()
        exe = python_executable or sys.executable
        cwd = working_dir if (working_dir and Path(working_dir).exists()) else str(PROJECT_ROOT)

        # 封装执行脚本：自动注入 matplotlib Agg 后端与图表 base64 自动导出
        wrapper_code = f"""# -*- coding: utf-8 -*-
import sys, io, base64, os

# 设置图表非交互式捕获
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:
    plt = None

# 执行用户代码
__user_error__ = None
try:
{self._indent_code(code, 4)}
except Exception as __e__:
    import traceback
    __user_error__ = traceback.format_exc()

# 导出生成的图表
__charts__ = []
if plt is not None:
    try:
        for __fignum__ in plt.get_fignums():
            __fig__ = plt.figure(__fignum__)
            __buf__ = io.BytesIO()
            __fig__.savefig(__buf__, format="png", dpi=100, bbox_inches="tight")
            __buf__.seek(0)
            __charts__.append(base64.b64encode(__buf__.read()).decode())
            plt.close(__fig__)
    except Exception:
        pass

if __charts__:
    import json
    print("___RESEARCHOS_CHARTS___" + json.dumps(__charts__) + "___RESEARCHOS_CHARTS_END___")

if __user_error__:
    sys.stderr.write(__user_error__)
    sys.exit(1)
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tf:
            tf.write(wrapper_code)
            temp_script = tf.name

        try:
            res = subprocess.run(
                [exe, temp_script],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            duration_ms = round((time.time() - start_time) * 1000, 2)
            stdout = res.stdout or ""
            stderr = res.stderr or ""
            charts: list[str] = []

            if "___RESEARCHOS_CHARTS___" in stdout:
                parts = stdout.split("___RESEARCHOS_CHARTS___")
                clean_stdout = parts[0]
                rest = parts[1]
                if "___RESEARCHOS_CHARTS_END___" in rest:
                    chart_json_str = rest.split("___RESEARCHOS_CHARTS_END___")[0]
                    clean_stdout += rest.split("___RESEARCHOS_CHARTS_END___")[1]
                    try:
                        charts = json.loads(chart_json_str)
                    except Exception:
                        pass
                stdout = clean_stdout.strip()

            success = (res.returncode == 0)
            return {
                "success": success,
                "stdout": stdout,
                "error": stderr if not success else None,
                "charts": charts,
                "execution_time_ms": duration_ms,
                "executable_used": exe,
                "working_directory": cwd,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "error": f"运行超时熔断 ({timeout} 秒)",
                "charts": [],
                "execution_time_ms": round((time.time() - start_time) * 1000, 2),
                "executable_used": exe,
                "working_directory": cwd,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "error": str(e),
                "charts": [],
                "execution_time_ms": round((time.time() - start_time) * 1000, 2),
                "executable_used": exe,
                "working_directory": cwd,
            }
        finally:
            try:
                os.unlink(temp_script)
            except Exception:
                pass

    def _indent_code(self, code: str, spaces: int = 4) -> str:
        pad = " " * spaces
        return "\n".join(pad + line if line.strip() else line for line in code.splitlines())


env_manager = EnvironmentManager()
