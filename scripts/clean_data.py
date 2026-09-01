"""
Clean Data Script — 清空所有历史测试与示例数据，还原纯净空白工作区
"""
import shutil
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SUBDIRS_TO_CLEAR = [
    "projects",
    "records",
    "papers",
    "datasets",
    "runs",
    "artifacts",
    "conclusions",
    "hypotheses",
    "debug_logs",
    "analyses",
    "experiments",
    "approvals",
    "reports",
    "audit",
    "diary",
    "sessions",
    "privacy_approvals",
]


def clean_all_data():
    print(f"Cleaning all data from: {DATA_DIR}")
    for sub in SUBDIRS_TO_CLEAR:
        p = DATA_DIR / sub
        if p.exists():
            for item in p.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    print(f"Failed to delete {item}: {e}")
        else:
            p.mkdir(parents=True, exist_ok=True)
        print(f"[CLEANED] {sub}/")

    print("\nAll mock and test data successfully deleted! System is now clean.")


if __name__ == "__main__":
    clean_all_data()
