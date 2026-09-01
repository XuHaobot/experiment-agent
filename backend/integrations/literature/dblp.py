"""
DBLP Computer Science & AI Literature Provider
官方计算机学术文献开放检索 API (https://dblp.org/search/publ/api)
"""
from __future__ import annotations

import logging
import requests

from .base import LiteratureProvider, Paper

logger = logging.getLogger(__name__)


class DBLPProvider(LiteratureProvider):
    """DBLP Computer Science Bibliography Provider"""
    name = "dblp"
    BASE_URL = "https://dblp.org/search/publ/api"

    def search(self, query: str, limit: int = 5) -> list[Paper]:
        query = query.strip()
        if not query:
            return []

        cached = self.cache.get(f"dblp:search:{query}:{limit}")
        if cached:
            return cached

        papers: list[Paper] = []
        try:
            params = {
                "q": query,
                "format": "json",
                "h": limit,
            }
            resp = requests.get(
                self.BASE_URL,
                params=params,
                headers={"User-Agent": "ResearchOS/2.6 (mailto:researchos@lab.org)"},
                timeout=self.timeout_sec,
            )
            if not resp.ok:
                return []

            data = resp.json()
            hits = data.get("result", {}).get("hits", {}).get("hit", [])
            for hit in hits:
                info = hit.get("info", {})
                title = info.get("title", "Untitled").rstrip(".")
                
                # 作者解析 (可能是 list 或 dict 或 string)
                authors_raw = info.get("authors", {}).get("author", [])
                authors: list[str] = []
                if isinstance(authors_raw, list):
                    for a in authors_raw:
                        if isinstance(a, dict):
                            authors.append(a.get("text", ""))
                        elif isinstance(a, str):
                            authors.append(a)
                elif isinstance(authors_raw, dict):
                    authors.append(authors_raw.get("text", ""))
                elif isinstance(authors_raw, str):
                    authors.append(authors_raw)

                year_str = info.get("year")
                year = int(year_str) if year_str and year_str.isdigit() else None
                venue = info.get("venue", "")
                doi = info.get("doi")
                url = info.get("url") or (f"https://doi.org/{doi}" if doi else None)
                dblp_key = info.get("key", "")

                papers.append(Paper(
                    paper_id=f"dblp:{dblp_key or hit.get('@id', '')}",
                    title=title,
                    authors=authors,
                    abstract=f"DBLP Computer Science Index. Venue: {venue} ({year or 'N/A'})",
                    year=year,
                    doi=doi,
                    url=url,
                    source="dblp",
                    venue=venue,
                ))

            self.cache.set(f"dblp:search:{query}:{limit}", papers)
        except Exception as e:
            logger.warning(f"DBLP search failed for '{query}': {e}")

        return papers

    def get_paper(self, paper_id: str) -> Paper | None:
        key = paper_id.replace("dblp:", "").strip()
        results = self.search(key, limit=1)
        return results[0] if results else None
