import re
from typing import Any

from src.tools.command_tool import extract_commands


VALUE_PATTERN = r"[^\s,，。；;]+"
PARAM_NAME_PATTERN = (
    r"batch_size|batch size|batch|lr0|learning_rate|learning rate|lr|epochs|epoch|"
    r"imgsz|image_size|image size|optimizer|scheduler|seed|model|dataset|data"
)
CLI_PARAM_PATTERN = re.compile(
    rf"--(?P<key>[\w-]+)(?:[=\s]+(?P<value>{VALUE_PATTERN}))?",
    flags=re.IGNORECASE,
)
NAMED_PARAM_PATTERNS = [
    re.compile(
        rf"(?P<key>{PARAM_NAME_PATTERN})\s*(?:=|:|：|到|为|改成|调整为|修改为|降低到|降到|设置为|设为)\s*(?P<value>{VALUE_PATTERN})",
        flags=re.IGNORECASE,
    ),
    re.compile(
        rf"(?:改成|调整为|修改为|降低到|降到|设置为|设为|尝试)\s*(?P<key>{PARAM_NAME_PATTERN})\s*(?:=|:|：|到|为)?\s*(?P<value>{VALUE_PATTERN})",
        flags=re.IGNORECASE,
    ),
]
MODEL_SUGGESTION_PATTERN = re.compile(
    r"(?:尝试|try|改用|换成|使用)\s+(?P<model>[A-Za-z0-9_.-]+(?:\.pt|\.pth)?)",
    flags=re.IGNORECASE,
)

ADJUSTMENT_HINTS = [
    "解决",
    "调整",
    "降低",
    "降到",
    "修改",
    "改成",
    "修复",
    "fixed",
    "solved",
]
SUGGESTION_HINTS = [
    "下一步",
    "建议",
    "尝试",
    "比较",
    "对比",
    "next",
    "todo",
    "try",
]


def empty_param_layers() -> dict:
    return {
        "original": {},
        "adjusted": {},
        "suggested": {},
    }


def extract_params(text: str) -> dict:
    """Extract layered experiment parameters.

    The params tool is responsible for original params first. It only reads
    command-like lines for the original layer so later fix notes do not
    overwrite the parameters used by the first run.
    """
    params = empty_param_layers()
    params["original"] = extract_original_params(text)
    return params


def extract_original_params(text: str) -> dict:
    params = {}
    for command in extract_commands(text):
        params.update(extract_param_mentions(command.get("raw", "")))

    if params:
        return params

    for line in text.splitlines():
        if _has_any_hint(line, ADJUSTMENT_HINTS + SUGGESTION_HINTS):
            continue
        params.update(extract_param_mentions(line))

    return params


def extract_suggested_params(text: str) -> dict:
    params = {}
    for line in _candidate_lines(text, SUGGESTION_HINTS):
        line_params = extract_param_mentions(line)
        model = _extract_model_suggestion(line)
        if model:
            line_params["model"] = model
        if _mentions_batch_comparison(line) and "batch" not in line_params:
            line_params["batch"] = "to_compare"
        params.update(line_params)
    return params


def extract_param_mentions(text: str) -> dict:
    params: dict[str, Any] = {}

    for match in CLI_PARAM_PATTERN.finditer(text):
        key = _normalize_key(match.group("key"))
        value = _clean_value(match.group("value") or True)
        if key:
            params[key] = value

    for pattern in NAMED_PARAM_PATTERNS:
        for match in pattern.finditer(text):
            key = _normalize_key(match.group("key"))
            value = _clean_value(match.group("value"))
            if key and _looks_like_value(value):
                params[key] = value

    return params


def _candidate_lines(text: str, hints: list[str]) -> list[str]:
    if not text:
        return []
    lines = text.splitlines() or [text]
    candidates = [line.strip() for line in lines if _has_any_hint(line, hints)]
    if not candidates and _has_any_hint(text, hints):
        candidates = [text.strip()]
    return [line for line in candidates if line]


def _has_any_hint(text: str, hints: list[str]) -> bool:
    lowered = text.lower()
    return any(hint.lower() in lowered for hint in hints)


def _normalize_key(key: str | None) -> str:
    if not key:
        return ""

    normalized = key.strip().lower().lstrip("-").replace("-", "_").replace(" ", "_")
    aliases = {
        "batch_size": "batch",
        "learning_rate": "lr",
        "image_size": "imgsz",
        "epoch": "epochs",
    }
    return aliases.get(normalized, normalized)


def _clean_value(value: Any) -> Any:
    if value is True:
        return True
    if value is None:
        return ""
    return str(value).strip().strip("`'\"，。；;")


def _looks_like_value(value: Any) -> bool:
    if value in ("", None):
        return False
    return str(value).strip() not in {"到", "为", "改成", "调整为", "修改为"}


def _extract_model_suggestion(line: str) -> str:
    match = MODEL_SUGGESTION_PATTERN.search(line)
    if not match:
        return ""
    model = _clean_value(match.group("model"))
    return model if isinstance(model, str) else ""


def _mentions_batch_comparison(line: str) -> bool:
    lowered = line.lower()
    return (
        ("比较" in line or "对比" in line or "不同" in line or "compare" in lowered)
        and ("batch size" in lowered or "batch_size" in lowered or "batch" in lowered)
    )
