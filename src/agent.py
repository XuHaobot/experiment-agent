from datetime import datetime
from typing import Any

from src.llm_client import call_llm, parse_json_response
from src.parser import guess_core_fields
from src.tools.command_tool import extract_commands
from src.tools.error_tool import analyze_errors
from src.tools.params_tool import empty_param_layers, extract_params, extract_suggested_params
from src.tools.report_tool import generate_markdown_report
from src.tools.solution_tool import extract_adjusted_params, extract_solutions
from src.utils import PROJECT_ROOT


EXTRACT_PROMPT_PATH = PROJECT_ROOT / "prompts" / "extract_prompt.txt"

TOOL_KEYWORDS = {
    "command_tool": [
        "python",
        "bash",
        "train.py",
        "cuda_visible_devices",
    ],
    "params_tool": [
        "--lr",
        "--lr0",
        "--batch",
        "--batch_size",
        "--epochs",
        "--dataset",
        "--data",
        "--model",
        "--imgsz",
    ],
    "error_tool": [
        "error",
        "traceback",
        "exception",
        "cuda out of memory",
        "modulenotfounderror",
        "filenotfounderror",
    ],
    "solution_tool": [
        "解决",
        "调整",
        "建议",
        "降低",
        "修改",
        "安装",
        "检查",
        "排查",
        "改成",
        "修复",
        "尝试",
        "fix",
        "solved",
    ],
}

TOOL_ORDER = [
    "command_tool",
    "params_tool",
    "error_tool",
    "solution_tool",
    "report_tool",
]


class ExperimentAgent:
    """A lightweight agent that decides which tools to call for each input."""

    def analyze(self, text: str, source_name: str = "uploaded") -> dict:
        selected_tools = self.decide_tools(text)
        trace = {
            "selected_tools": selected_tools,
            "steps": [
                {
                    "tool": "tool_router",
                    "status": "success",
                    "detail": f"Selected tools: {', '.join(selected_tools)}",
                }
            ],
        }

        tool_results = self.run_tools(text, selected_tools)
        trace["steps"].extend(tool_results.pop("_steps", []))

        llm_record, llm_error = self._extract_with_llm(text)
        tool_results["llm_client"] = llm_record or {}
        trace["steps"].append(
            {
                "tool": "llm_client",
                "status": "success" if llm_error is None else "skipped_or_failed",
                "detail": "LLM JSON extraction completed." if llm_error is None else llm_error,
            }
        )

        merged_record = self.merge_results(tool_results)

        if "report_tool" in selected_tools:
            report_markdown = generate_markdown_report(merged_record)
            tool_results["report_tool"] = report_markdown
            trace["steps"].append(
                {
                    "tool": "report_tool",
                    "status": "success",
                    "detail": "Generated Markdown report from merged record.",
                }
            )

        tools_called = [tool for tool in selected_tools if tool != "report_tool"]
        tools_called.extend(["llm_client", "report_tool"])

        return {
            "id": "",
            "source": source_name,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            **merged_record,
            "agent_trace": trace,
            "metadata": {
                "agent_version": "0.4.0",
                "tools_called": tools_called,
                "llm_used": llm_record is not None and llm_error is None,
                "llm_error": llm_error,
            },
        }

    def decide_tools(self, text: str) -> list[str]:
        lowered = text.lower()
        selected_tools = []

        for tool_name in TOOL_ORDER:
            if tool_name == "report_tool":
                continue

            keywords = TOOL_KEYWORDS.get(tool_name, [])
            if any(keyword.lower() in lowered for keyword in keywords):
                selected_tools.append(tool_name)

        selected_tools.append("report_tool")
        return selected_tools

    def run_tools(self, text: str, selected_tools: list[str]) -> dict:
        results: dict[str, Any] = {
            "core_fields": guess_core_fields(text),
            "_steps": [
                {
                    "tool": "core_parser",
                    "status": "success",
                    "detail": "Guessed task, dataset, model, conclusion, and next_step fields.",
                }
            ],
        }

        for tool_name in selected_tools:
            if tool_name == "command_tool":
                results[tool_name] = extract_commands(text)
                results["_steps"].append(_tool_step(tool_name, results[tool_name]))
            elif tool_name == "params_tool":
                results[tool_name] = extract_params(text)
                results["_steps"].append(_tool_step(tool_name, results[tool_name]))
            elif tool_name == "error_tool":
                results[tool_name] = analyze_errors(text)
                results["_steps"].append(_tool_step(tool_name, results[tool_name]))
            elif tool_name == "solution_tool":
                results[tool_name] = extract_solutions(text)
                results["adjusted_params"] = extract_adjusted_params(text)
                results["_steps"].append(_tool_step(tool_name, results[tool_name]))
            elif tool_name == "report_tool":
                results["_steps"].append(
                    {
                        "tool": "report_tool",
                        "status": "deferred",
                        "detail": "Report generation runs after merge_results.",
                    }
                )

        return results

    def merge_results(self, results: dict) -> dict:
        core_fields = results.get("core_fields", {})
        suggested_params = extract_suggested_params(core_fields.get("next_step", ""))
        if not suggested_params:
            suggested_params = extract_suggested_params(" ".join(str(value) for value in core_fields.values()))

        params = _normalize_params(results.get("params_tool", empty_param_layers()))
        params["adjusted"] = _merge_dicts(params.get("adjusted"), results.get("adjusted_params", {}))
        params["suggested"] = _merge_dicts(params.get("suggested"), suggested_params)

        rule_record = {
            "task": core_fields.get("task", ""),
            "dataset": core_fields.get("dataset", ""),
            "model": core_fields.get("model", ""),
            "commands": results.get("command_tool", []),
            "params": params,
            "errors": results.get("error_tool", []),
            "solutions": results.get("solution_tool", []),
            "conclusion": core_fields.get("conclusion", ""),
            "next_step": core_fields.get("next_step", ""),
            "raw_summary": "",
        }

        return _merge_records(rule_record, results.get("llm_client", {}))

    def _extract_with_llm(self, text: str) -> tuple[dict | None, str | None]:
        prompt = f"{_load_extract_prompt()}\n\n{text}"
        response = call_llm(prompt)
        return parse_json_response(response)


def _load_extract_prompt() -> str:
    return EXTRACT_PROMPT_PATH.read_text(encoding="utf-8")


def _tool_step(tool_name: str, result: Any) -> dict:
    return {
        "tool": tool_name,
        "status": "success",
        "detail": f"Extracted {_result_size(result)} item(s).",
    }


def _result_size(result: Any) -> int:
    if _is_layered_params(result):
        return sum(len(result.get(layer, {})) for layer in ("original", "adjusted", "suggested"))
    if isinstance(result, (list, dict)):
        return len(result)
    if result:
        return 1
    return 0


def _merge_records(rule_record: dict, llm_record: dict) -> dict:
    normalized_llm = _normalize_llm_record(llm_record)

    return {
        "task": _prefer_text(normalized_llm.get("task"), rule_record.get("task")),
        "dataset": _prefer_text(normalized_llm.get("dataset"), rule_record.get("dataset")),
        "model": _prefer_text(normalized_llm.get("model"), rule_record.get("model")),
        "commands": _merge_lists(rule_record.get("commands"), normalized_llm.get("commands")),
        "params": _merge_params(rule_record.get("params"), normalized_llm.get("params")),
        "errors": _merge_lists(rule_record.get("errors"), normalized_llm.get("errors")),
        "solutions": _merge_lists(rule_record.get("solutions"), normalized_llm.get("solutions")),
        "conclusion": _prefer_text(
            normalized_llm.get("conclusion"),
            rule_record.get("conclusion"),
        ),
        "next_step": _prefer_text(normalized_llm.get("next_step"), rule_record.get("next_step")),
        "raw_summary": _prefer_text(normalized_llm.get("raw_summary"), rule_record.get("raw_summary")),
    }


def _normalize_llm_record(record: dict) -> dict:
    normalized = {
        "task": "",
        "dataset": "",
        "model": "",
        "commands": [],
        "params": empty_param_layers(),
        "errors": [],
        "solutions": [],
        "conclusion": "",
        "next_step": "",
        "raw_summary": "",
    }

    for key in normalized:
        if key in record:
            normalized[key] = record[key]

    if "command" in record and not normalized["commands"]:
        normalized["commands"] = record["command"]

    normalized["commands"] = _as_list(normalized["commands"])
    normalized["errors"] = _as_list(normalized["errors"])
    normalized["solutions"] = _as_list(normalized["solutions"])
    normalized["params"] = _normalize_params(normalized["params"])

    return normalized


def _prefer_text(primary: Any, fallback: Any) -> str:
    if isinstance(primary, str) and primary.strip():
        return primary.strip()
    if isinstance(fallback, str) and fallback.strip():
        return fallback.strip()
    return ""


def _merge_lists(first: Any, second: Any) -> list:
    items = []
    seen = set()

    for item in _as_list(first) + _as_list(second):
        marker = repr(item)
        if marker in seen:
            continue
        seen.add(marker)
        items.append(item)

    return items


def _merge_dicts(first: Any, second: Any) -> dict:
    merged = {}
    if isinstance(first, dict):
        merged.update({key: value for key, value in first.items() if value not in ("", None, [], {})})
    if isinstance(second, dict):
        merged.update({key: value for key, value in second.items() if value not in ("", None, [], {})})
    return merged


def _merge_params(rule_params: Any, llm_params: Any) -> dict:
    rule_layers = _normalize_params(rule_params)
    llm_layers = _normalize_params(llm_params)

    return {
        "original": _merge_dicts(llm_layers.get("original"), rule_layers.get("original")),
        "adjusted": _merge_dicts(llm_layers.get("adjusted"), rule_layers.get("adjusted")),
        "suggested": _merge_dicts(llm_layers.get("suggested"), rule_layers.get("suggested")),
    }


def _normalize_params(params: Any) -> dict:
    layered = empty_param_layers()
    if not isinstance(params, dict):
        return layered

    if not _is_layered_params(params):
        layered["original"] = {
            key: value for key, value in params.items() if value not in ("", None, [], {})
        }
        return layered

    for layer in layered:
        value = params.get(layer, {})
        if isinstance(value, dict):
            layered[layer] = {
                key: item for key, item in value.items() if item not in ("", None, [], {})
            }

    return layered


def _is_layered_params(value: Any) -> bool:
    return isinstance(value, dict) and any(
        layer in value for layer in ("original", "adjusted", "suggested")
    )


def _as_list(value: Any) -> list:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]
