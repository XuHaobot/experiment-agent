"""
OpenAlex Literature Provider Adapter
"""
from __future__ import annotations

import logging
import os
import requests
from typing import Any

from backend.integrations.literature.base import LiteratureProvider, Paper

logger = logging.getLogger(__name__)

_OPENALEX_BASE = "https://api.openalex.org"
_OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO", "researcher@example.com")


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    """从 OpenAlex 的 abstract_inverted_index 还原完整摘要文本"""
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    pos_word = []
    for word, positions in inverted_index.items():
        if isinstance(positions, list):
            for p in positions:
                pos_word.append((p, word))
    pos_word.sort(key=lambda x: x[0])
    return " ".join(w for _, w in pos_word)


class OpenAlexProvider(LiteratureProvider):
    name: str = "openalex"

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if _OPENALEX_MAILTO:
            headers["User-Agent"] = f"ResearchOS/2.2 (mailto:{_OPENALEX_MAILTO})"
        return headers

    def _parse_work(self, item: dict[str, Any]) -> Paper:
        work_id = (item.get("id") or "").replace("https://openalex.org/", "")
        title = item.get("title") or "Untitled"
        abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))

        authors = []
        for a in item.get("authorships", []):
            author_obj = a.get("author", {})
            name = author_obj.get("display_name")
            if name:
                authors.append(name)

        year = item.get("publication_year")
        doi = item.get("doi")
        if doi and doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")

        primary_loc = item.get("primary_location") or {}
        source_obj = primary_loc.get("source") or {}
        venue = source_obj.get("display_name") or ""
        landing_url = primary_loc.get("landing_page_url") or item.get("doi") or f"https://openalex.org/{work_id}"

        open_access = item.get("open_access") or {}
        pdf_url = open_access.get("oa_url") or primary_loc.get("pdf_url")

        return Paper(
            paper_id=work_id,
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            doi=doi,
            url=landing_url,
            source="openalex",
            citation_count=item.get("cited_by_count", 0),
            venue=venue,
            pdf_url=pdf_url,
            metadata={"openalex_id": item.get("id"), "is_oa": open_access.get("is_oa", False)},
        )

    def search(self, query: str, limit: int = 5) -> list[Paper]:
        query = query.strip()
        if not query:
            return []

        cache_key = f"openalex:search:{query}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        params = {
            "search": query,
            "per-page": min(max(1, limit), 25),
            "select": "id,title,abstract_inverted_index,publication_year,authorships,primary_location,doi,cited_by_count,open_access",
        }
        if _OPENALEX_MAILTO:
            params["mailto"] = _OPENALEX_MAILTO

        try:
            resp = requests.get(
                f"{_OPENALEX_BASE}/works",
                params=params,
                headers=self._headers(),
                timeout=self.timeout_sec,
            )
            if resp.status_code != 200:
                logger.warning("OpenAlex API error status: %d", resp.status_code)
                return []
            data = resp.json()
            results = [self._parse_work(item) for item in data.get("results", [])]
            self.cache.set(cache_key, results)
            return results
        except Exception as e:
            logger.warning("OpenAlex search request failed: %s", e)
            return []

    def get_paper(self, paper_id: str) -> Paper | None:
        paper_id = paper_id.strip()
        if not paper_id:
            return None

        clean_id = paper_id.replace("https://openalex.org/", "")
        cache_key = f"openalex:paper:{clean_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            resp = requests.get(
                f"{_OPENALEX_BASE}/works/{clean_id}",
                headers=self._headers(),
                timeout=self.timeout_sec,
            )
            if resp.status_code != 200:
                return None
            paper = self._parse_work(resp.json())
            self.cache.set(cache_key, paper)
            return paper
        except Exception as e:
            logger.warning("OpenAlex get_paper failed: %s", e)
            return None
