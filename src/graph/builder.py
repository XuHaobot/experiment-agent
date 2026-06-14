import hashlib
import re
from typing import Any

from src.graph import schema

# 图谱质量限制
_MAX_ENTITIES = 35          # 总实体上限
_MAX_SOLUTIONS = 3          # Solution 实体上限
_MAX_COMMANDS = 3           # Command 实体上限
_MAX_ERRORS = 3             # Error 实体上限
_MAX_PARAMS = 8             # Parameter 实体上限
_MAX_NAME_LEN = 50          # 实体名称最大长度
_MIN_NAME_LEN = 2           # 实体名称最小长度（过滤噪声）


def build_graph_from_record(record: dict) -> dict:
    entities = []
    relations = []
    entity_ids = set()
    _seen_names = set()  # 用于按名称去重

    experiment_id = _entity_id(schema.ENTITY_EXPERIMENT, record.get("id") or record.get("source") or "experiment")
    _add_entity(
        entities,
        entity_ids,
        _seen_names,
        experiment_id,
        schema.ENTITY_EXPERIMENT,
        _clean_name(record.get("task") or record.get("id") or "Experiment"),
        {
            "record_id": record.get("id", ""),
            "source": record.get("source", ""),
            "created_at": record.get("created_at", ""),
            "task": record.get("task", ""),
        },
    )

    dataset = record.get("dataset")
    if dataset and _is_valid_name(dataset):
        dataset_id = _entity_id(schema.ENTITY_DATASET, dataset)
        _add_entity(entities, entity_ids, _seen_names, dataset_id, schema.ENTITY_DATASET, _clean_name(dataset), {})
        _add_relation(relations, experiment_id, dataset_id, schema.REL_USES_DATASET)

    model = record.get("model")
    if model and _is_valid_name(model):
        model_id = _entity_id(schema.ENTITY_MODEL, model)
        _add_entity(entities, entity_ids, _seen_names, model_id, schema.ENTITY_MODEL, _clean_name(model), {})
        _add_relation(relations, experiment_id, model_id, schema.REL_USES_MODEL)

    command_texts = []
    for index, command in enumerate(record.get("commands") or record.get("command") or [], start=1):
        command_text = _item_text(command)
        if not command_text or not _is_valid_name(command_text):
            continue
        command_texts.append((index, command_text, command))

    for index, command_text, command in (command_texts[:_MAX_COMMANDS]):
        short_text = _trim(command_text, _MAX_NAME_LEN)
        command_id = _entity_id(schema.ENTITY_COMMAND, f"{experiment_id}:{index}:{short_text}")
        _add_entity(
            entities, entity_ids, _seen_names, command_id, schema.ENTITY_COMMAND, short_text,
            {"index": index, "command_type": command.get("type", "") if isinstance(command, dict) else ""},
        )
        _add_relation(relations, experiment_id, command_id, schema.REL_RUNS_COMMAND)

    params = _normalize_params(record.get("params", {}))
    adjusted_parameter_ids = []
    param_count = 0
    for layer, relation_type in [
        ("original", schema.REL_HAS_ORIGINAL_PARAMETER),
        ("adjusted", schema.REL_HAS_ADJUSTED_PARAMETER),
        ("suggested", schema.REL_HAS_SUGGESTED_PARAMETER),
    ]:
        for key, value in params.get(layer, {}).items():
            if param_count >= _MAX_PARAMS:
                break
            name = f"{key}={value}"
            if not _is_valid_name(name):
                continue
            parameter_id = _parameter_id(experiment_id, layer, key, value)
            _add_entity(
                entities,
                entity_ids,
                _seen_names,
                parameter_id,
                schema.ENTITY_PARAMETER,
                name,
                {"name": key, "value": value, "layer": layer},
            )
            _add_relation(relations, experiment_id, parameter_id, relation_type, {"layer": layer})
            param_count += 1
            if layer == "adjusted":
                adjusted_parameter_ids.append((parameter_id, key, value))

    error_ids = []
    errors_list = []
    for index, error in enumerate(record.get("errors") or [], start=1):
        error_text = _item_text(error)
        if not error_text or not _is_valid_name(error_text):
            continue
        errors_list.append((index, error_text, error))

    for index, error_text, error in (errors_list[:_MAX_ERRORS]):
        short_text = _trim(error_text, _MAX_NAME_LEN)
        error_id = _entity_id(schema.ENTITY_ERROR, f"{experiment_id}:{index}:{short_text}")
        _add_entity(
            entities, entity_ids, _seen_names, error_id, schema.ENTITY_ERROR, short_text,
            {"index": index, "error_type": error.get("type", "") if isinstance(error, dict) else "", "stage": error.get("stage", "") if isinstance(error, dict) else ""},
        )
        _add_relation(relations, experiment_id, error_id, schema.REL_HAS_ERROR)
        error_ids.append(error_id)

    solution_ids = []
    sol_count = 0
    for index, solution in enumerate(record.get("solutions") or [], start=1):
        if sol_count >= _MAX_SOLUTIONS:
            break
        solution_text = _item_text(solution)
        if not solution_text or not _is_valid_name(solution_text):
            continue
        short_text = _trim(solution_text, _MAX_NAME_LEN)
        solution_id = _entity_id(schema.ENTITY_SOLUTION, f"{experiment_id}:{index}:{short_text}")
        if _add_entity(entities, entity_ids, _seen_names, solution_id, schema.ENTITY_SOLUTION, short_text, {"index": index}):
            solution_ids.append((solution_id, solution_text))
            sol_count += 1

    for error_id in (error_ids[:2]):
        for solution_id, solution_text in solution_ids:
            if _solution_likely_solves_error(solution_text):
                _add_relation(relations, error_id, solution_id, schema.REL_SOLVED_BY)

    for solution_id, solution_text in solution_ids:
        for parameter_id, key, value in (adjusted_parameter_ids[:3]):
            if _solution_mentions_parameter(solution_text, key, value):
                _add_relation(relations, solution_id, parameter_id, schema.REL_ADJUSTS_PARAMETER, {"parameter": key, "value": value})

    conclusion = record.get("conclusion")
    if conclusion and _is_valid_name(conclusion):
        short = _trim(str(conclusion), _MAX_NAME_LEN)
        conclusion_id = _entity_id(schema.ENTITY_CONCLUSION, f"{experiment_id}:{short}")
        _add_entity(entities, entity_ids, _seen_names, conclusion_id, schema.ENTITY_CONCLUSION, short, {})
        _add_relation(relations, experiment_id, conclusion_id, schema.REL_PRODUCES_CONCLUSION)

    next_step = record.get("next_step")
    if next_step and _is_valid_name(next_step):
        short = _trim(str(next_step), _MAX_NAME_LEN)
        next_step_id = _entity_id(schema.ENTITY_NEXT_STEP, f"{experiment_id}:{short}")
        _add_entity(entities, entity_ids, _seen_names, next_step_id, schema.ENTITY_NEXT_STEP, short, {})
        _add_relation(relations, experiment_id, next_step_id, schema.REL_SUGGESTS_NEXT_STEP)

    # 最终实体数量限制
    if len(entities) > _MAX_ENTITIES:
        kept_ids = {e["id"] for e in entities[:_MAX_ENTITIES]}
        entities = entities[:_MAX_ENTITIES]
        relations = [r for r in relations if r["source"] in kept_ids and r["target"] in kept_ids]

    return {
        "entities": entities,
        "relations": relations,
    }


def _clean_name(name: str) -> str:
    """清理实体名称：去除多余空白和特殊字符"""
    if not name:
        return ""
    name = str(name).strip()
    # 合并连续空白
    name = re.sub(r'\s+', ' ', name)
    # 去掉 markdown 标记
    name = re.sub(r'[#*_`~>]', '', name)
    return name.strip()


def _is_valid_name(name: str) -> bool:
    """检查名称是否为有效实体名称（过滤噪声、乱码、过短/过长文本）"""
    if not name:
        return False
    text = str(name).strip()
    if len(text) < _MIN_NAME_LEN:
        return False
    # 过滤纯空白或纯符号
    if not re.search(r'[\w\u4e00-\u9fff]', text):
        return False
    # 过滤大量乱码（不可打印字符超过30%）
    printable = sum(1 for c in text if c.isprintable() or c in '\n\t')
    if printable / len(text) < 0.7:
        return False
    return True


def _add_entity(entities: list[dict], entity_ids: set[str], seen_names: set[str],
                entity_id: str, entity_type: str, name: str, properties: dict) -> bool:
    """添加实体，带去重。返回是否成功添加。"""
    if entity_id in entity_ids:
        return False
    # 按名称去重（同类型内）
    name_key = f"{entity_type}:{_clean_name(name).lower()}"
    if name_key in seen_names:
        return False
    entity_ids.add(entity_id)
    seen_names.add(name_key)
    entities.append(
        {
            "id": entity_id,
            "type": entity_type,
            "name": str(name),
            "properties": properties or {},
        }
    )
    return True


def _add_relation(relations: list[dict], source: str, target: str, relation_type: str, properties: dict | None = None) -> None:
    relation = {
        "source": source,
        "target": target,
        "type": relation_type,
        "properties": properties or {},
    }
    if relation not in relations:
        relations.append(relation)


def _entity_id(entity_type: str, value: Any) -> str:
    digest = hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:12]
    return f"{entity_type}:{digest}"


def _parameter_id(experiment_id: str, layer: str, key: str, value: Any) -> str:
    return _entity_id(schema.ENTITY_PARAMETER, f"{experiment_id}:{layer}:{key}:{value}")


def _item_text(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("message") or item.get("raw") or item.get("name") or item)
    return str(item)


def _normalize_params(params: dict) -> dict:
    layers = {"original": {}, "adjusted": {}, "suggested": {}}
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


def _solution_likely_solves_error(solution_text: str) -> bool:
    lowered = solution_text.lower()
    return any(
        keyword in lowered
        for keyword in ["解决", "修复", "改成", "调整", "降低", "降到", "fix", "fixed", "solved", "workaround"]
    )


def _solution_mentions_parameter(solution_text: str, key: str, value: Any) -> bool:
    lowered = solution_text.lower()
    normalized_key = key.lower().replace("_", " ")
    normalized_text = lowered.replace("_", " ")
    value_text = str(value).lower()
    if normalized_key in normalized_text and value_text in lowered:
        return True
    if key in {"batch", "batch_size"} and re.search(r"batch(?:\s+size)?", normalized_text) and value_text in lowered:
        return True
    if key in {"lr", "lr0", "learning_rate"} and ("lr" in normalized_text or "learning rate" in normalized_text) and value_text in lowered:
        return True
    return False


def _trim(text: str, max_len: int = 80) -> str:
    """截断过长文本，用于图谱节点名称精简"""
    if not text or len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."
