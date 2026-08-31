"""
Literature Provider Base Architecture — 统一文献集成抽象基类
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Paper:
    """标准化学术论文数据实体"""
    def __init__(
        self,
        paper_id: str,
        title: str,
        authors: list[str] | None = None,
        abstract: str = "",
        year: int | None = None,
        doi: str | None = None,
        url: str | None = None,
        source: str = "unknown",
        citation_count: int = 0,
        venue: str = "",
        pdf_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.paper_id = paper_id
        self.title = title.strip()
        self.authors = authors or []
        self.abstract = abstract.strip()
        self.year = year
        self.doi = doi
        self.url = url
        self.source = source
        self.citation_count = citation_count
        self.venue = venue
        self.pdf_url = pdf_url
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "id": self.paper_id,  # 兼容前端字段
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "year": self.year,
            "doi": self.doi,
            "url": self.url,
            "source": self.source,
            "citation_count": self.citation_count,
            "venue": self.venue,
            "pdf_url": self.pdf_url,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Paper:
        return cls(
            paper_id=data.get("paper_id") or data.get("id") or "",
            title=data.get("title", ""),
            authors=data.get("authors", []),
            abstract=data.get("abstract", ""),
            year=data.get("year"),
            doi=data.get("doi"),
            url=data.get("url"),
            source=data.get("source", "unknown"),
            citation_count=data.get("citation_count", 0),
            venue=data.get("venue", ""),
            pdf_url=data.get("pdf_url"),
            metadata=data.get("metadata", {}),
        )


class SimpleCache:
    """轻量内存缓存，支持基于 TTL 的自动失效"""
    def __init__(self, default_ttl_sec: int = 3600):
        self._cache: Dict[str, tuple[float, Any]] = {}
        self.default_ttl_sec = default_ttl_sec

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            ts, val = self._cache[key]
            if time.time() - ts < self.default_ttl_sec:
                return val
            del self._cache[key]
        return None

    def set(self, key: str, val: Any) -> None:
        self._cache[key] = (time.time(), val)

    def clear(self) -> None:
        self._cache.clear()


class LiteratureProvider(ABC):
    """学术文献提供者统一接口"""
    name: str = "base"

    def __init__(self, timeout_sec: int = 12):
        self.timeout_sec = timeout_sec
        self.cache = SimpleCache(default_ttl_sec=1800)

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[Paper]:
        """按关键词检索学术文献"""
        pass

    @abstractmethod
    def get_paper(self, paper_id: str) -> Paper | None:
        """根据唯一标识获取论文详细元数据"""
        pass

    def find_related(self, paper_id: str, limit: int = 5) -> list[Paper]:
        """检索相关论文（默认根据标题/关键词启发式查找）"""
        target = self.get_paper(paper_id)
        if target and target.title:
            return self.search(target.title[:80], limit=limit)
        return []

    def get_citations(self, paper_id: str, limit: int = 5) -> list[Paper]:
        """获取引用该论文的工作"""
        return []
