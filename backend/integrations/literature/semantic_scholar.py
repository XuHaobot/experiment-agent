"""
Semantic Scholar Literature Provider Adapter
"""
from __future__ import annotations

import logging
import requests
from typing import Any

from backend.integrations.literature.base import LiteratureProvider, Paper

logger = logging.getLogger(__name__)

_S2_API_BASE = "https://api.semanticscholar.org/graph/v1"


class SemanticScholarProvider(LiteratureProvider):
    name: str = "semantic_scholar"

    def _parse_paper(self, item: dict[str, Any]) -> Paper:
        paper_id = item.get("paperId") or ""
        title = item.get("title") or "Untitled"
        abstract = item.get("abstract") or ""

        authors = [a.get("name") for a in item.get("authors", []) if a.get("name")]
        year = item.get("year")
        ext_ids = item.get("externalIds") or {}
        doi = ext_ids.get("DOI")

        url = item.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}"
        oa_pdf = item.get("openAccessPdf") or {}
        pdf_url = oa_pdf.get("url")

        return Paper(
            paper_id=f"s2_{paper_id}",
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            doi=doi,
            url=url,
            source="semantic_scholar",
            citation_count=item.get("citationCount", 0),
            venue=item.get("venue") or "",
            pdf_url=pdf_url,
            metadata={"s2_paper_id": paper_id, "external_ids": ext_ids},
        )

    def search(self, query: str, limit: int = 5) -> list[Paper]:
        query = query.strip()
        if not query:
            return []

        cache_key = f"s2:search:{query}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        params = {
            "query": query,
            "limit": min(max(1, limit), 20),
            "fields": "paperId,title,abstract,year,authors,venue,citationCount,openAccessPdf,externalIds,url",
        }
        try:
            resp = requests.get(
                f"{_S2_API_BASE}/paper/search",
                params=params,
                timeout=self.timeout_sec,
            )
            if resp.status_code != 200:
                logger.warning("Semantic Scholar API status %d", resp.status_code)
                return []
            data = resp.json()
            results = [self._parse_paper(p) for p in data.get("data", [])]
            self.cache.set(cache_key, results)
            return results
        except Exception as e:
            logger.warning("Semantic Scholar search failed: %s", e)
            return []

    def get_paper(self, paper_id: str) -> Paper | None:
        clean_id = paper_id.replace("s2_", "").strip()
        if not clean_id:
            return None

        cache_key = f"s2:paper:{clean_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        params = {"fields": "paperId,title,abstract,year,authors,venue,citationCount,openAccessPdf,externalIds,url"}
        try:
            resp = requests.get(
                f"{_S2_API_BASE}/paper/{clean_id}",
                params=params,
                timeout=self.timeout_sec,
            )
            if resp.status_code != 200:
                return None
            paper = self._parse_paper(resp.json())
            self.cache.set(cache_key, paper)
            return paper
        except Exception as e:
            logger.warning("Semantic Scholar get_paper failed: %s", e)
            return None
