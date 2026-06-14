import re


COMMAND_PATTERN = re.compile(
    r"(?P<command>(?:CUDA_VISIBLE_DEVICES=\S+\s+)?(?:python|python3|torchrun|bash|sh)\s+[^\n\r]+)",
    flags=re.IGNORECASE,
)


def extract_commands(text: str) -> list[dict]:
    commands = []
    for match in COMMAND_PATTERN.finditer(text):
        command = match.group("command").strip()
        commands.append(
            {
                "raw": command,
                "type": _guess_command_type(command),
            }
        )
    return commands


def _guess_command_type(command: str) -> str:
    lowered = command.lower()
    if "train" in lowered:
        return "train"
    if "test" in lowered:
        return "test"
    if "eval" in lowered or "val" in lowered:
        return "eval"
    if "infer" in lowered or "predict" in lowered:
        return "infer"
    return "unknown"
