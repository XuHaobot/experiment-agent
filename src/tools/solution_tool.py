from src.tools.params_tool import extract_param_mentions


SOLUTION_KEYWORDS = [
    "解决",
    "解决方法",
    "最终",
    "改成",
    "调整",
    "降低",
    "降到",
    "修改",
    "修复",
    "安装",
    "检查",
    "fix",
    "fixed",
    "solved",
    "workaround",
]

ADJUSTMENT_KEYWORDS = [
    "改成",
    "调整",
    "调整为",
    "降低",
    "降低到",
    "降到",
    "修改",
    "修改为",
    "设为",
    "设置为",
    "fix",
    "fixed",
    "solved",
]


def extract_solutions(text: str) -> list[str]:
    solutions = []
    for line in text.splitlines():
        lowered = line.lower()
        if any(keyword.lower() in lowered for keyword in SOLUTION_KEYWORDS):
            cleaned = line.strip()
            if cleaned:
                solutions.append(cleaned)
    return solutions


def extract_adjusted_params(text: str) -> dict:
    adjusted = {}
    for line in text.splitlines():
        lowered = line.lower()
        if not any(keyword.lower() in lowered for keyword in ADJUSTMENT_KEYWORDS):
            continue
        adjusted.update(extract_param_mentions(line))
    return adjusted
