"""
Literature Integration Package — 统一学术文献集成入口
"""
from __future__ import annotations

from typing import Dict, List, Optional
from backend.integrations.literature.base import LiteratureProvider, Paper
from backend.integrations.literature.openalex import OpenAlexProvider
from backend.integrations.literature.arxiv import ArxivProvider
from backend.integrations.literature.semantic_scholar import SemanticScholarProvider

_PROVIDERS: Dict[str, LiteratureProvider] = {
    "openalex": OpenAlexProvider(),
    "arxiv": ArxivProvider(),
    "semantic_scholar": SemanticScholarProvider(),
}


def get_literature_provider(name: str = "openalex") -> LiteratureProvider:
    """获取指定文献提供者适配器，默认使用 OpenAlex"""
    return _PROVIDERS.get(name.lower(), _PROVIDERS["openalex"])


def search_literature(query: str, source: str = "openalex", limit: int = 5) -> list[dict]:
    """统一文献搜索接口，返回标准化字典列表"""
    provider = get_literature_provider(source)
    papers = provider.search(query, limit=limit)
    return [p.to_dict() for p in papers]


def get_literature_paper(paper_id: str, source: str = "openalex") -> Optional[dict]:
    """获取单篇文献详情"""
    provider = get_literature_provider(source)
    paper = provider.get_paper(paper_id)
    return paper.to_dict() if paper else None
