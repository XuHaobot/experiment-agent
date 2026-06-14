import re
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def slugify(value: str, fallback: str = "experiment") -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    value = value.strip("-")
    return value[:60] or fallback


def make_record_id(record: dict) -> str:
    name = record.get("task") or record.get("model") or record.get("dataset") or "experiment"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{slugify(str(name))}"
