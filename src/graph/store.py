import json
from datetime import datetime
from pathlib import Path

from src.utils import PROJECT_ROOT


GRAPH_DIR = PROJECT_ROOT / "data" / "graph"


def ensure_graph_dir() -> None:
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)


def save_graph(graph: dict) -> str:
    ensure_graph_dir()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = GRAPH_DIR / f"graph-{timestamp}.json"
    path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def load_graphs() -> list[dict]:
    ensure_graph_dir()
    graphs = []
    for path in sorted(GRAPH_DIR.glob("*.json"), reverse=True):
        try:
            graph = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(graph, dict):
            graph["_path"] = str(path)
            graphs.append(graph)
    return graphs
