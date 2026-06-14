import json
from pathlib import Path

from src.utils import PROJECT_ROOT, make_record_id


DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RECORDS_DIR = DATA_DIR / "records"
REPORTS_DIR = DATA_DIR / "reports"


def ensure_storage_dirs() -> None:
    for path in (RAW_DIR, RECORDS_DIR, REPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def save_raw_text(filename: str, text: str) -> Path:
    ensure_storage_dirs()
    safe_name = Path(filename).name
    path = RAW_DIR / safe_name
    path.write_text(text, encoding="utf-8")
    return path


def save_record(record: dict) -> Path:
    ensure_storage_dirs()
    if not record.get("id"):
        record["id"] = make_record_id(record)

    path = RECORDS_DIR / f"{record['id']}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def save_report(record_id: str, markdown: str) -> Path:
    ensure_storage_dirs()
    path = REPORTS_DIR / f"{record_id}.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def load_record(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
