"""
Unit Tests for OpenBayesRunner (HyperAI / OpenBayes Cloud Execution)
"""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from backend.integrations.execution.openbayes_runner import OpenBayesRunner, openbayes_runner


def test_openbayes_runner_cli_status():
    status = openbayes_runner.check_cli_status()
    # openbayes-cli should be installed
    assert status["installed"] is True
    assert "service_url" in status
    assert status["service_url"] == "https://openbayes.com"


def test_openbayes_runner_unauthenticated_guard():
    # Without valid token, run_code should return clear guidance without crashing
    runner = OpenBayesRunner(token="")
    res = runner.run_code("print('hello')", timeout=5)
    assert res["auto_terminated"] is True
    assert "error" in res


def test_openbayes_runner_auth_empty_token():
    res = OpenBayesRunner.login_with_token("")
    assert res["success"] is False
    assert "Token 不能为空" in res["error"]
