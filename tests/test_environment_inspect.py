"""
Unit Test for Environment Inspection API & Domain
"""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from backend.integrations.execution.env_manager import env_manager


def test_inspect_current_python_environment():
    res = env_manager.inspect_environment(
        python_executable=sys.executable,
        working_directory=str(PROJECT_ROOT),
    )
    assert res["valid"] is True
    assert "version" in res
    assert "packages" in res
    assert "numpy" in res["packages"]
    assert "cuda" in res
