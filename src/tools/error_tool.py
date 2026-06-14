ERROR_KEYWORDS = [
    "traceback",
    "error",
    "exception",
    "runtimeerror",
    "valueerror",
    "filenotfounderror",
    "modulenotfounderror",
    "cuda out of memory",
    "报错",
    "错误",
    "异常",
]


def analyze_errors(text: str) -> list[dict]:
    errors = []
    for line in text.splitlines():
        lowered = line.lower()
        if any(keyword in lowered for keyword in ERROR_KEYWORDS):
            errors.append(
                {
                    "message": line.strip(),
                    "type": _guess_error_type(line),
                    "stage": "unknown",
                }
            )
    return errors


def _guess_error_type(line: str) -> str:
    lowered = line.lower()
    if "cuda out of memory" in lowered:
        return "cuda_oom"
    if "filenotfounderror" in lowered or "no such file" in lowered:
        return "file_not_found"
    if "modulenotfounderror" in lowered or "importerror" in lowered:
        return "dependency"
    if "runtimeerror" in lowered:
        return "runtime_error"
    if "valueerror" in lowered:
        return "value_error"
    return "unknown"
