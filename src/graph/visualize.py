from datetime import datetime

from src.graph.store import GRAPH_DIR, ensure_graph_dir


def generate_graph_html(graph: dict, filename: str = "graph.html") -> dict:
    try:
        import networkx as nx
        from pyvis.network import Network
    except ImportError as exc:
        return {
            "ok": False,
            "error": f"缺少可视化依赖：{exc}. 请先安装 networkx 和 pyvis。",
            "path": "",
        }

    ensure_graph_dir()
    graph_nx = nx.DiGraph()

    for entity in graph.get("entities", []):
        graph_nx.add_node(
            entity.get("id", ""),
            label=entity.get("name", ""),
            title=f"{entity.get('type', '')}: {entity.get('name', '')}",
            group=entity.get("type", ""),
        )

    for relation in graph.get("relations", []):
        graph_nx.add_edge(
            relation.get("source", ""),
            relation.get("target", ""),
            label=relation.get("type", ""),
            title=relation.get("type", ""),
        )

    network = Network(height="720px", width="100%", directed=True, notebook=False)
    network.from_nx(graph_nx)
    for edge in network.edges:
        edge["arrows"] = "to"

    output_name = filename or f"graph-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    output_path = GRAPH_DIR / output_name
    network.write_html(str(output_path), notebook=False)

    return {
        "ok": True,
        "error": "",
        "path": str(output_path),
    }
