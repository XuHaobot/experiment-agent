import json
from typing import Any

from src.graph.store import load_graphs


def search_graph(keyword: str) -> list[dict]:
    keyword = keyword.strip().lower()
    if not keyword:
        return []

    results = []
    for graph in load_graphs():
        path = graph.get("_path", "")
        for entity in graph.get("entities", []):
            text = _to_search_text(entity)
            if keyword in text.lower():
                results.append(
                    {
                        "kind": "entity",
                        "graph_path": path,
                        "id": entity.get("id", ""),
                        "type": entity.get("type", ""),
                        "name": entity.get("name", ""),
                        "summary": _summary(entity),
                    }
                )

        for relation in graph.get("relations", []):
            text = _to_search_text(relation)
            if keyword in text.lower():
                results.append(
                    {
                        "kind": "relation",
                        "graph_path": path,
                        "id": f"{relation.get('source', '')}->{relation.get('target', '')}",
                        "type": relation.get("type", ""),
                        "name": relation.get("type", ""),
                        "summary": _summary(relation),
                    }
                )

    return results


def _to_search_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _summary(value: dict) -> str:
    text = _to_search_text(value)
    return text[:240] + ("..." if len(text) > 240 else "")
