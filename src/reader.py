import json
from pathlib import Path


def read_uploaded_file(uploaded_file) -> str:
    """Read a Streamlit uploaded file as text."""
    raw = uploaded_file.getvalue()
    text = raw.decode("utf-8", errors="replace")

    if Path(uploaded_file.name).suffix.lower() == ".json":
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return text

    return text


def read_text_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")
