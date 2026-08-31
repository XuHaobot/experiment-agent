"""
Jupyter Notebook Adapter — 交互式 Notebook 产物解析与集成
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class NotebookAdapter:
    """Jupyter .ipynb 结构解析与 Artifact 适配器"""

    def parse_notebook(self, ipynb_json_or_str: str | dict) -> dict[str, Any]:
        """
        解析 .ipynb 内容，提取代码单元、输出图表与 Markdown 文本
        """
        if isinstance(ipynb_json_or_str, str):
            try:
                nb = json.loads(ipynb_json_or_str)
            except Exception as e:
                return {"success": False, "error": f"Invalid JSON in notebook: {e}"}
        else:
            nb = ipynb_json_or_str

        cells = nb.get("cells", [])
        code_cells = []
        markdown_cells = []
        extracted_charts = []
        total_exec_count = 0

        for idx, cell in enumerate(cells):
            cell_type = cell.get("cell_type", "")
            source = "".join(cell.get("source", []))
            
            if cell_type == "code":
                exec_count = cell.get("execution_count")
                if exec_count:
                    total_exec_count = max(total_exec_count, exec_count)
                
                outputs = []
                for out in cell.get("outputs", []):
                    out_type = out.get("output_type", "")
                    if out_type == "stream":
                        outputs.append("".join(out.get("text", [])))
                    elif out_type in ("display_data", "execute_result"):
                        data = out.get("data", {})
                        if "image/png" in data:
                            extracted_charts.append(data["image/png"])
                        if "text/plain" in data:
                            outputs.append("".join(data["text/plain"]))
                    elif out_type == "error":
                        outputs.append(f"Error: {out.get('ename')}: {out.get('evalue')}")

                code_cells.append({
                    "cell_index": idx,
                    "execution_count": exec_count,
                    "code": source,
                    "outputs": outputs,
                })
            elif cell_type == "markdown":
                markdown_cells.append({
                    "cell_index": idx,
                    "text": source,
                })

        kernel_spec = nb.get("metadata", {}).get("kernelspec", {})

        return {
            "success": True,
            "nbformat": nb.get("nbformat"),
            "kernel": kernel_spec.get("display_name", "Python 3"),
            "total_cells": len(cells),
            "code_cells_count": len(code_cells),
            "markdown_cells_count": len(markdown_cells),
            "extracted_charts_count": len(extracted_charts),
            "code_cells": code_cells,
            "markdown_cells": markdown_cells,
            "charts": extracted_charts,
        }

    def import_notebook_as_artifact(
        self,
        project_id: str,
        name: str,
        ipynb_str: str,
        source_record_id: str | None = None,
    ) -> dict[str, Any]:
        """将 Notebook 解析并沉淀为系统的标准化 Artifact"""
        from backend.domain.artifact import create_artifact
        parsed = self.parse_notebook(ipynb_str)
        if not parsed.get("success"):
            raise ValueError(parsed.get("error"))

        metadata = {
            "kernel": parsed.get("kernel"),
            "code_cells": parsed.get("code_cells_count"),
            "charts_extracted": parsed.get("extracted_charts_count"),
        }

        art = create_artifact(
            project_id=project_id,
            name=name,
            artifact_type="notebook",
            content=ipynb_str,
            metadata=metadata,
            source_record_id=source_record_id,
        )
        return art


notebook_adapter = NotebookAdapter()
