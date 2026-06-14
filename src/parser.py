import re


def _first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def guess_core_fields(text: str) -> dict:
    """Guess high-level fields with lightweight patterns."""
    return {
        "task": _first_match(
            text,
            [
                r"(?:任务|实验任务|目标|task)[:：]\s*(.+)",
                r"今天想(?:用|做)\s*(.+)",
            ],
        ),
        "dataset": _first_match(
            text,
            [
                r"(?:数据集|dataset|data)[:：]\s*(.+)",
                r"(?:数据集路径|dataset path)[:：]\s*(.+)",
            ],
        ),
        "model": _first_match(
            text,
            [
                r"(?:模型|model)[:：]\s*(.+)",
                r"(?:--model)\s+([^\s]+)",
            ],
        ),
        "conclusion": _first_match(
            text,
            [
                r"(?:结论|conclusion)[:：]\s*(.+)",
                r"(?:最终结果|实验结果)[:：]\s*(.+)",
            ],
        ),
        "next_step": _first_match(
            text,
            [
                r"(?:下一步|next step|todo)[:：]\s*(.+)",
                r"(?:后续计划)[:：]\s*(.+)",
            ],
        ),
    }
