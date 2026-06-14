import json
import re
from pathlib import Path
from typing import Any


SEARCH_FIELDS = [
    "task",
    "dataset",
    "model",
    "commands",
    "params",
    "errors",
    "solutions",
    "conclusion",
    "next_step",
]

LEGACY_FIELDS = ["command"]
MAX_SNIPPET_LENGTH = 180

KEYWORD_ALIASES = {
    "batch_size": ["batch_size", "batch size", "batch", "--batch"],
    "batch-size": ["batch_size", "batch size", "batch", "--batch"],
    "learning_rate": ["learning_rate", "learning rate", "lr", "lr0", "--lr", "--lr0"],
    "lr": ["learning_rate", "learning rate", "lr", "lr0", "--lr", "--lr0"],
    "cuda": ["cuda", "cuda_visible_devices", "cuda out of memory"],
}


def search_records(keyword: str, records_dir: str | Path) -> list[dict]:
    """Search local JSON records with simple keyword matching."""
    keyword = keyword.strip()
    if not keyword:
        return []

    terms = _search_terms(keyword)
    results = []

    for path, record in _iter_records(records_dir):
        matched_fields = []
        snippets = []
        score = 0

        for field in SEARCH_FIELDS + LEGACY_FIELDS:
            value = record.get(field, "")
            field_text = _field_to_text(value)
            if not field_text or not _matches(field_text, terms):
                continue

            display_field = "commands" if field == "command" else field
            if display_field not in matched_fields:
                matched_fields.append(display_field)

            snippets.append(f"{display_field}: {_excerpt(field_text, terms)}")
            score += _field_score(display_field)

        if _matches(path.name, terms):
            matched_fields.append("filename")
            snippets.insert(0, f"filename: {path.name}")
            score += 3

        if matched_fields:
            results.append(
                {
                    "id": record.get("id", path.stem),
                    "filename": path.name,
                    "path": path,
                    "dataset": record.get("dataset", ""),
                    "model": record.get("model", ""),
                    "matched_fields": matched_fields,
                    "snippet": " | ".join(snippets[:3]),
                    "snippets": snippets,
                    "score": score,
                }
            )

    return sorted(results, key=lambda item: (item["score"], item["filename"]), reverse=True)


def _iter_records(records_dir: str | Path):
    directory = Path(records_dir)
    if not directory.exists():
        return

    for path in sorted(directory.glob("*.json"), reverse=True):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        if isinstance(record, dict):
            yield path, record


def _search_terms(keyword: str) -> list[str]:
    lowered = keyword.lower()
    terms = [keyword]
    terms.extend(KEYWORD_ALIASES.get(lowered, []))

    seen = set()
    unique_terms = []
    for term in terms:
        normalized = term.strip()
        if not normalized:
            continue
        marker = normalized.lower()
        if marker in seen:
            continue
        seen.add(marker)
        unique_terms.append(normalized)
    return unique_terms


def _matches(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    normalized_text = _normalize_for_match(text)
    return any(
        term.lower() in lowered or _normalize_for_match(term) in normalized_text
        for term in terms
    )


def _field_to_text(value: Any) -> str:
    if value in ("", None, [], {}):
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _excerpt(text: str, terms: list[str]) -> str:
    compact_text = re.sub(r"\s+", " ", text).strip()
    lowered = compact_text.lower()

    match_index = -1
    matched_term = ""
    for term in terms:
        index = lowered.find(term.lower())
        if index != -1:
            match_index = index
            matched_term = term
            break

    if match_index == -1:
        return compact_text[:MAX_SNIPPET_LENGTH]

    start = max(match_index - 50, 0)
    end = min(match_index + len(matched_term) + 90, len(compact_text))
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(compact_text) else ""
    return f"{prefix}{compact_text[start:end]}{suffix}"


def _field_score(field: str) -> int:
    if field in {"task", "dataset", "model"}:
        return 3
    if field in {"commands", "params", "errors", "solutions"}:
        return 2
    return 1


def _normalize_for_match(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.lower())


# ---------------------------------------------------------------------------
# 语义搜索 (Vector Search)
# ---------------------------------------------------------------------------

def semantic_search(query: str, top_k: int = 5) -> list[dict]:
    """通过向量语义相似度搜索实验记录。

    需要先 pip install chromadb，并配置 DASHSCOPE_API_KEY。
    如果向量库不可用则返回空列表并附带错误信息。
    """
    try:
        from src.vector_store import get_vector_store
    except ImportError:
        return [{"error": "vector_store 模块不可用"}]

    store = get_vector_store()
    if not store.is_ready:
        return [{"error": "向量搜索未就绪: DASHSCOPE_API_KEY 未配置或 chromadb 未安装"}]

    try:
        return store.semantic_search(query, top_k=top_k)
    except Exception as exc:
        return [{"error": f"语义搜索失败: {exc}"}]


# ---------------------------------------------------------------------------
# 混合搜索 (Hybrid Search)
# ---------------------------------------------------------------------------

def hybrid_search(
    keyword: str,
    records_dir: str | Path,
    top_k: int = 5,
    keyword_weight: float = 0.4,
    semantic_weight: float = 0.6,
) -> list[dict]:
    """融合关键词搜索 + 向量语义搜索的混合检索。

    返回合并后的排序结果列表，每条包含:
    - id, filename, matched_fields, snippet, score, source
    """
    # 1. 关键词搜索
    kw_results = search_records(keyword, records_dir)

    # 2. 语义搜索
    sem_results = semantic_search(keyword, top_k=top_k)

    # 如果语义搜索不可用，退化为纯关键词搜索
    if sem_results and isinstance(sem_results[0], dict) and sem_results[0].get("error"):
        return kw_results

    # 3. 合并 & 加权排序
    merged: dict[str, dict] = {}

    # 关键词结果归一化分数 (0~1)
    max_kw_score = max((r.get("score", 0) for r in kw_results), default=1) or 1
    for r in kw_results:
        rid = r.get("id", r.get("filename", ""))
        norm_score = (r.get("score", 0) / max_kw_score) * keyword_weight
        merged[rid] = {
            **r,
            "score": norm_score,
            "source": "keyword",
        }

    # 语义结果归一化
    for r in sem_results:
        rid = r.get("record_id", r.get("id", ""))
        sem_score = r.get("score", 0) * semantic_weight

        if rid in merged:
            # 两者都命中，分数叠加
            merged[rid]["score"] += sem_score
            merged[rid]["source"] = "hybrid"
            merged[rid]["semantic_score"] = r.get("score", 0)
        else:
            merged[rid] = {
                "id": rid,
                "filename": "",
                "path": None,
                "task": r.get("task", ""),
                "dataset": r.get("dataset", ""),
                "model": r.get("model", ""),
                "matched_fields": ["semantic"],
                "snippet": r.get("document", "")[:180],
                "snippets": [r.get("document", "")[:180]],
                "score": sem_score,
                "source": "semantic",
                "semantic_score": r.get("score", 0),
            }

    # 按综合分数排序
    return sorted(merged.values(), key=lambda item: item.get("score", 0), reverse=True)[:top_k]
