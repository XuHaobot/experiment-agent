def generate_markdown_report(record: dict) -> str:
    params = _normalize_params(record.get("params") or {})
    sections = ["# 实验复盘报告"]

    sections.append(_overview_section(record))
    sections.append(_original_config_section(record, params))
    sections.append(_error_section(record))
    sections.append(_adjustment_section(record, params))
    sections.append(_conclusion_section(record))
    sections.append(_next_step_section(record, params))
    sections.append(_agent_trace_section(record))

    return "\n\n".join(section for section in sections if section.strip()) + "\n"


def _overview_section(record: dict) -> str:
    lines = ["## 1. 实验概述"]
    _append_value(lines, "实验任务", record.get("task"))
    _append_value(lines, "数据集", record.get("dataset"))
    _append_value(lines, "模型", record.get("model"))

    if len(lines) == 1:
        lines.append("本次记录尚未识别出明确的实验任务、数据集或模型。")

    return "\n".join(lines)


def _original_config_section(record: dict, params: dict) -> str:
    lines = ["## 2. 原始运行配置"]

    commands = record.get("commands") or record.get("command") or []
    if commands:
        lines.append("### 运行命令")
        lines.extend(f"- `{_item_text(command)}`" for command in commands)

    original_params = params.get("original", {})
    if original_params:
        lines.append("### 原始参数")
        lines.extend(_params_lines(original_params))

    if len(lines) == 1:
        lines.append("未识别到原始运行命令或原始参数。")

    return "\n".join(lines)


def _error_section(record: dict) -> str:
    lines = ["## 3. 报错与问题定位"]
    errors = record.get("errors") or []

    if errors:
        lines.append("### 报错信息")
        lines.extend(f"- {_error_text(error)}" for error in errors)

        reasons = [_possible_reason(error) for error in errors]
        reasons = [reason for reason in reasons if reason]
        if reasons:
            lines.append("### 可能原因")
            lines.extend(f"- {reason}" for reason in _unique_items(reasons))
    else:
        lines.append("未发现明显报错信息。")

    return "\n".join(lines)


def _adjustment_section(record: dict, params: dict) -> str:
    lines = ["## 4. 调整过程"]
    adjusted_params = params.get("adjusted", {})
    solutions = record.get("solutions") or []

    if adjusted_params:
        lines.append("### 调整了哪些参数")
        lines.extend(_params_lines(adjusted_params))
        lines.append("### 为什么调整")
        lines.append(_adjustment_reason(record))
        lines.append("### 调整后的配置")
        lines.extend(_params_lines(adjusted_params))

    if solutions:
        lines.append("### 解决方案记录")
        lines.extend(f"- {_item_text(solution)}" for solution in solutions)

    if len(lines) == 1:
        lines.append("未识别到明确的参数调整过程。")

    return "\n".join(lines)


def _conclusion_section(record: dict) -> str:
    lines = ["## 5. 当前结论"]
    conclusion = record.get("conclusion")

    if conclusion:
        lines.append(f"- 当前结果：{conclusion}")
        lines.append(f"- 是否跑通：{_run_status(conclusion)}")
        if _mentions_unfinished_comparison(conclusion):
            lines.append("- 尚未完成的对比：指标或模型对比仍需补充。")
    else:
        lines.append("当前记录中没有明确实验结论。")

    return "\n".join(lines)


def _next_step_section(record: dict, params: dict) -> str:
    lines = ["## 6. 下一步计划"]
    next_step = record.get("next_step")
    suggested_params = params.get("suggested", {})

    if next_step:
        lines.append(f"- 计划说明：{next_step}")

    if suggested_params:
        model = suggested_params.get("model")
        if model:
            lines.append(f"- 建议尝试的模型：`{model}`")

        comparable_params = {
            key: value for key, value in suggested_params.items() if key != "model"
        }
        if comparable_params:
            lines.append("- 建议比较的参数：")
            lines.extend(_params_lines(comparable_params))

    metrics = _suggested_metrics(record)
    if metrics:
        lines.append(f"- 后续评估指标：{metrics}")

    if len(lines) == 1:
        lines.append("当前记录中没有明确下一步计划。")

    return "\n".join(lines)


def _agent_trace_section(record: dict) -> str:
    trace = record.get("agent_trace") or {}
    selected_tools = trace.get("selected_tools") or []
    steps = trace.get("steps") or []

    lines = ["## 7. Agent 分析过程"]
    if selected_tools:
        lines.append("- selected_tools：" + ", ".join(f"`{tool}`" for tool in selected_tools))

    if steps:
        lines.append("- steps 摘要：")
        for index, step in enumerate(steps, start=1):
            tool = step.get("tool", "unknown")
            status = step.get("status", "unknown")
            detail = step.get("detail", "")
            lines.append(f"  - {index}. `{tool}` [{status}] {detail}")

    if len(lines) == 1:
        lines.append("未记录 Agent trace。")

    return "\n".join(lines)


def _params_lines(params: dict) -> list[str]:
    return [f"- `{key}`: `{value}`" for key, value in params.items()]


def _append_value(lines: list[str], label: str, value) -> None:
    if value:
        lines.append(f"- {label}：{value}")


def _normalize_params(params: dict) -> dict:
    layers = {
        "original": {},
        "adjusted": {},
        "suggested": {},
    }
    if not isinstance(params, dict):
        return layers

    if any(layer in params for layer in layers):
        for layer in layers:
            value = params.get(layer, {})
            if isinstance(value, dict):
                layers[layer] = value
        return layers

    layers["original"] = params
    return layers


def _item_text(item) -> str:
    if isinstance(item, dict):
        return item.get("raw") or item.get("message") or str(item)
    return str(item)


def _error_text(item) -> str:
    if isinstance(item, dict):
        error_type = item.get("type", "unknown")
        message = item.get("message") or item.get("raw") or str(item)
        return f"[{error_type}] {message}"
    return str(item)


def _possible_reason(error) -> str:
    if isinstance(error, dict):
        error_type = error.get("type", "")
        message = (error.get("message") or "").lower()
    else:
        error_type = ""
        message = str(error).lower()

    if error_type == "cuda_oom" or "cuda out of memory" in message:
        return "显存不足，通常需要降低 batch size、减小输入尺寸或换用更小模型。"
    if error_type == "file_not_found":
        return "文件路径或数据集路径可能不正确。"
    if error_type == "dependency":
        return "运行环境中可能缺少依赖包或版本不匹配。"
    if error_type in {"runtime_error", "value_error"}:
        return "训练配置、输入数据或张量形状可能存在不匹配。"
    return ""


def _adjustment_reason(record: dict) -> str:
    errors_text = " ".join(_error_text(error).lower() for error in record.get("errors") or [])
    if "cuda out of memory" in errors_text or "cuda_oom" in errors_text:
        return "本次调整主要是为了解决显存不足问题。"
    if record.get("errors"):
        return "本次调整主要是为了解决运行过程中出现的报错。"
    return "记录中没有明确说明调整原因，建议后续补充调参动机。"


def _run_status(conclusion: str) -> str:
    if any(keyword in conclusion for keyword in ["跑通", "正常启动", "成功", "解决"]):
        return "从结论看，本次实验已经至少完成基础运行。"
    if any(keyword in conclusion for keyword in ["失败", "未解决", "没有跑通"]):
        return "从结论看，本次实验尚未跑通。"
    return "记录中没有明确说明是否完全跑通。"


def _mentions_unfinished_comparison(conclusion: str) -> bool:
    return any(keyword in conclusion for keyword in ["还没有", "尚未", "未比较", "没有比较"])


def _suggested_metrics(record: dict) -> str:
    text = " ".join(
        str(record.get(key, ""))
        for key in ("task", "conclusion", "next_step", "raw_summary")
    ).lower()
    metrics = []
    if "map" in text or "目标检测" in text:
        metrics.append("mAP")
    if "速度" in text or "time" in text or "latency" in text:
        metrics.append("训练速度/推理速度")
    if "loss" in text:
        metrics.append("loss")
    return "、".join(_unique_items(metrics))


def _unique_items(items: list[str]) -> list[str]:
    unique = []
    seen = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique
