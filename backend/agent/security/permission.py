"""Permission Definitions and Validation"""
from typing import Set

# 标准权限字符串
PERM_READ_PROJECT = "read_project"
PERM_READ_DATASET = "read_dataset"
PERM_READ_EXPERIMENT = "read_experiment"
PERM_WRITE_EXPERIMENT = "write_experiment"
PERM_EXECUTE_PYTHON = "execute_python"
PERM_EXECUTE_EXPERIMENT = "execute_experiment"
PERM_WRITE_ARTIFACT = "write_artifact"
PERM_WRITE_CONCLUSION = "write_conclusion"
PERM_SEARCH_LITERATURE = "search_literature"
PERM_READ_LITERATURE = "read_literature"
PERM_READ_PDF = "read_pdf"
PERM_ANALYZE_DATASET = "analyze_dataset"
PERM_GENERATE_CODE = "generate_code"

# 默认授予的基础权限集合（本地单机科研模式默认具备基础操作权限）
DEFAULT_PERMISSIONS: Set[str] = {
    PERM_READ_PROJECT,
    PERM_READ_DATASET,
    PERM_READ_EXPERIMENT,
    PERM_WRITE_EXPERIMENT,
    PERM_EXECUTE_PYTHON,
    PERM_EXECUTE_EXPERIMENT,
    PERM_WRITE_ARTIFACT,
    PERM_WRITE_CONCLUSION,
    PERM_SEARCH_LITERATURE,
    PERM_READ_LITERATURE,
    PERM_READ_PDF,
    PERM_ANALYZE_DATASET,
    PERM_GENERATE_CODE,
}


def has_permission(required_permissions: list[str], granted_permissions: Set[str] | None = None) -> bool:
    """检查是否满足所有声明的权限"""
    if not required_permissions:
        return True
    granted = granted_permissions if granted_permissions is not None else DEFAULT_PERMISSIONS
    return all(perm in granted for perm in required_permissions)
