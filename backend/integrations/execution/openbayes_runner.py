"""
OpenBayes / HyperAI Cloud Container Runner
支持通过官方 openbayes-cli (bayes) 调度云端算力容器（支持免费 CPU 实例），
并在代码执行完毕后自动终止容器释放资源。
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from backend.integrations.execution.base import ExecutionRunner

logger = logging.getLogger(__name__)


class OpenBayesRunner(ExecutionRunner):
    """OpenBayes / HyperAI 云端容器执行器"""
    name: str = "openbayes_cloud"

    def __init__(self, token: str | None = None, default_resource: str = "cpu", default_env: str = "pytorch-2.0"):
        self.token = token or os.environ.get("OPENBAYES_TOKEN")
        self.default_resource = default_resource
        self.default_env = default_env

    @staticmethod
    def check_cli_status() -> dict[str, Any]:
        """检查 openbayes-cli (bayes) 是否就绪以及当前登录状态"""
        bayes_bin = shutil.which("bayes")
        if not bayes_bin:
            return {
                "installed": False,
                "logged_in": False,
                "username": None,
                "error": "openbayes-cli 未安装或未加入 PATH",
            }

        try:
            res = subprocess.run(
                [bayes_bin, "status"],
                capture_output=True,
                text=True,
                timeout=8,
                encoding="utf-8",
                errors="replace",
            )
            stdout = res.stdout.strip()
            # 常见输出形式："用户未登入" 或 "用户: xxxx / 组织: xxxx"
            is_logged_in = "用户未登入" not in stdout and "未登入" not in stdout and res.returncode == 0
            username = None
            if is_logged_in:
                for line in stdout.splitlines():
                    if "用户:" in line or "username:" in line.lower():
                        username = line.split(":")[-1].strip()
                        break
                if not username and stdout:
                    username = stdout.split()[0] if stdout else "Active User"

            return {
                "installed": True,
                "logged_in": is_logged_in,
                "username": username,
                "raw_status": stdout,
                "service_url": "https://openbayes.com",
            }
        except Exception as e:
            return {
                "installed": True,
                "logged_in": False,
                "username": None,
                "error": str(e),
            }

    @staticmethod
    def login_with_token(token: str) -> dict[str, Any]:
        """通过 API Token 登录 OpenBayes（直接调用 SDK 校验，秒级响应，避免 CLI 阻塞）"""
        token = token.strip()
        if not token:
            return {"success": False, "error": "Token 不能为空"}

        # 友好区分：如果用户误填了 HyperAI 的大模型 API Key (sk-...)
        if token.startswith("sk-"):
            return {
                "success": False,
                "error": "您填写的凭证以 'sk-' 开头，这是 HyperAI 的「大模型推理 API Key」（用于对话模型），并非「算力容器调度令牌」。\n\n请前往 OpenBayes 控制台「个人设置 -> 访问令牌」(https://openbayes.com/console/settings/tokens) 创建并复制容器访问令牌。",
            }

        try:
            from bayes.model.file.settings import BayesSettings
            from bayes.client.base import BayesGQLClient
            from bayes.client import user_client

            bayes_settings = BayesSettings()
            default_env = bayes_settings.default_env
            if not default_env:
                return {"success": False, "error": "OpenBayes 配置文件未就绪"}

            gql_client = BayesGQLClient(default_env.graphQL, token)
            result = user_client.login_with_token(gql_client, token)
            bayes_settings.login(result.username, token)
            return {
                "success": True,
                "message": f"成功登入 OpenBayes (用户: {result.username})",
                "username": result.username,
            }
        except Exception as e:
            err_str = str(e)
            if "UNAUTHENTICATED" in err_str or "没有登录" in err_str:
                err_str = "Token 认证失败：密钥无效或已过期。请前往 https://openbayes.com/console/settings/tokens 创建并复制「访问令牌 (Access Token)」。"
            return {"success": False, "error": err_str}

    def run_code(
        self,
        code: str,
        timeout: int = 300,
        context: dict[str, Any] | None = None,
        resource: str | None = None,
        env_name: str | None = None,
    ) -> dict[str, Any]:
        """
        在 OpenBayes 云端容器（默认免费 CPU）中执行代码。
        执行完毕后 task 容器自动销毁释放，停止计费。
        """
        bayes_bin = shutil.which("bayes")
        if not bayes_bin:
            return {
                "success": False,
                "stdout": "",
                "error": "openbayes-cli 未安装，无法调度云端容器",
                "charts": [],
                "execution_time_ms": 0.0,
                "auto_terminated": True,
            }

        cli_status = self.check_cli_status()
        if not cli_status.get("logged_in") and not self.token:
            return {
                "success": False,
                "stdout": "",
                "error": "未检测到 OpenBayes 登录凭据，请先在环境配置中输入 API Token 并绑定",
                "charts": [],
                "execution_time_ms": 0.0,
                "auto_terminated": True,
            }

        res_type = resource or self.default_resource or "cpu"
        target_env = env_name or self.default_env or "pytorch-2.0"

        # 创建独立的临时作业目录
        temp_dir = Path(tempfile.mkdtemp(prefix="bayes_job_"))
        try:
            # 1. 写入待执行代码
            script_path = temp_dir / "run_script.py"
            script_path.write_text(code, encoding="utf-8")

            # 2. 准备环境变量
            exec_env = os.environ.copy()
            if self.token:
                exec_env["OPENBAYES_TOKEN"] = self.token

            start_t = time.time()
            # 3. 调度一次性 task 作业：--follow 实时流式输出，执行完平台自动关停
            cmd = [
                bayes_bin,
                "gear",
                "run",
                "task",
                "--resource",
                res_type,
                "--env",
                target_env,
                "--follow",
                "--",
                "python run_script.py",
            ]
            logger.info(f"Dispatching OpenBayes task: {' '.join(cmd)}")

            proc = subprocess.run(
                cmd,
                cwd=str(temp_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                env=exec_env,
            )
            elapsed_ms = (time.time() - start_t) * 1000

            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            is_success = proc.returncode == 0

            return {
                "success": is_success,
                "stdout": stdout,
                "error": None if is_success else (stderr or stdout),
                "charts": [],
                "execution_time_ms": elapsed_ms,
                "auto_terminated": True,
                "resource_used": res_type,
                "env_used": target_env,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "任务在设定的时间内未完成，本地看门狗已强制终止",
                "error": f"执行超时 ({timeout}s)，已触发自动关停",
                "charts": [],
                "execution_time_ms": timeout * 1000,
                "auto_terminated": True,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "error": str(e),
                "charts": [],
                "execution_time_ms": 0.0,
                "auto_terminated": True,
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# 全局单例
openbayes_runner = OpenBayesRunner()
