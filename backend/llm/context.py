"""
Structured Research Context Package & Context Planner
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.security.classification import DataClassification


@dataclass
class ContextItem:
    """An individual atomic item in the scientific context"""
    source_type: str        # "hypothesis", "paper", "run", "artifact", "dataset_schema", "note"
    source_id: str          # e.g. "hyp_001", "paper_123", "run_456"
    content: str            # text summary or payload
    classification: DataClassification
    reason: str = ""        # why this classification was assigned
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "content": self.content,
            "classification": self.classification.value,
            "reason": self.reason,
            "metadata": self.metadata,
        }


@dataclass
class ResearchContext:
    """Curated package of research items planned for LLM consumption"""
    project_id: str
    items: List[ContextItem] = field(default_factory=list)
    query_intent: str = ""

    def add_item(
        self,
        source_type: str,
        source_id: str,
        content: str,
        classification: DataClassification,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.items.append(
            ContextItem(
                source_type=source_type,
                source_id=source_id,
                content=content,
                classification=classification,
                reason=reason,
                metadata=metadata or {},
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "query_intent": self.query_intent,
            "items": [item.to_dict() for item in self.items],
            "total_items": len(self.items),
        }

    def render_prompt_block(self) -> str:
        """Render a concise markdown context block for prompt injection"""
        lines = [f"### [Project Context: {self.project_id}]"]
        for idx, it in enumerate(self.items, 1):
            lines.append(f"{idx}. **[{it.source_type.upper()} - {it.source_id}]** ({it.classification.value})")
            lines.append(f"   {it.content.strip()}")
        return "\n".join(lines)


class ContextPlanner:
    """Assembles curated, minimally necessary context for tasks"""

    @classmethod
    def build_hypothesis_context(cls, project_id: str, hypothesis_data: Dict[str, Any]) -> ResearchContext:
        ctx = ResearchContext(project_id=project_id, query_intent="hypothesis_analysis")
        ctx.add_item(
            source_type="hypothesis",
            source_id=hypothesis_data.get("id", "hyp_draft"),
            content=f"Hypothesis Title: {hypothesis_data.get('title')}\nDescription: {hypothesis_data.get('description', '')}",
            classification=DataClassification.SENSITIVE,
            reason="Unpublished scientific hypothesis",
        )
        return ctx

    @classmethod
    def build_literature_context(cls, project_id: str, papers: List[Dict[str, Any]]) -> ResearchContext:
        ctx = ResearchContext(project_id=project_id, query_intent="literature_synthesis")
        for p in papers:
            ctx.add_item(
                source_type="paper",
                source_id=p.get("id", "paper"),
                content=f"Title: {p.get('title')}\nAuthors: {', '.join(p.get('authors', []))}\nYear: {p.get('year')}\nSnippet: {p.get('snippet', p.get('abstract', ''))}",
                classification=DataClassification.PUBLIC,
                reason="Public academic publication metadata",
            )
        return ctx

    @classmethod
    def build_dataset_schema_context(cls, project_id: str, dataset: Dict[str, Any]) -> ResearchContext:
        ctx = ResearchContext(project_id=project_id, query_intent="dataset_analysis_planning")
        # Only schema (columns, types, row_count), NOT raw data rows!
        schema_summary = f"Dataset: {dataset.get('name')}\nColumns: {json_columns(dataset)}\nRows: {dataset.get('row_count', 'unknown')}"
        ctx.add_item(
            source_type="dataset_schema",
            source_id=dataset.get("id", "ds"),
            content=schema_summary,
            classification=DataClassification.PUBLIC,
            reason="Abstract dataset structural schema (no row data)",
        )
        return ctx


def json_columns(dataset: Dict[str, Any]) -> str:
    cols = dataset.get("columns", [])
    if isinstance(cols, list):
        return ", ".join([str(c) for c in cols])
    return str(cols)
