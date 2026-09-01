"""
CrossRef Literature Provider — 全球 DOI 权威元数据官方接口 (https://api.crossref.org)
遵循 Polite Pool 规范 (mailto: User-Agent)
"""
from __future__ import annotations

import logging
import urllib.parse
import requests

from .base import LiteratureProvider, Paper

logger = logging.getLogger(__name__)


class CrossRefProvider(LiteratureProvider):
    """CrossRef Official REST API Provider"""
    name = "crossref"
    BASE_URL = "https://api.crossref.org/works"

    def search(self, query: str, limit: int = 5) -> list[Paper]:
        query = query.strip()
        if not query:
            return []

        # 如果输入直接是 DOI (e.g. 10.1145/3305367)
        if query.startswith("10.") or "doi.org/10." in query:
            clean_doi = query.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
            p = self.get_paper(clean_doi)
            return [p] if p else []

        cached = self.cache.get(f"crossref:search:{query}:{limit}")
        if cached:
            return cached

        papers: list[Paper] = []
        try:
            params = {
                "query": query,
                "rows": limit,
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
            items = data.get("message", {}).get("items", [])
            for item in items:
                title_list = item.get("title", [])
                title = title_list[0].strip() if title_list else "Untitled"
                
                authors: list[str] = []
                for a in item.get("author", []):
                    given = a.get("given", "")
                    family = a.get("family", "")
                    name = f"{given} {family}".strip()
                    if name:
                        authors.append(name)

                year = None
                published = item.get("published") or item.get("created") or {}
                date_parts = published.get("date-parts", [[]])[0]
                if date_parts:
                    year = date_parts[0]

                container_title = item.get("container-title", [])
                venue = container_title[0] if container_title else item.get("publisher", "")
                doi = item.get("DOI")
                url = item.get("URL") or (f"https://doi.org/{doi}" if doi else None)
                abstract = item.get("abstract", "") or f"CrossRef indexed work. Publisher: {item.get('publisher', 'N/A')}"
                is_referenced_by_count = item.get("is-referenced-by-count", 0)

                papers.append(Paper(
                    paper_id=f"doi:{doi}" if doi else f"cr:{item.get('prefix', '')}",
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    year=year,
                    doi=doi,
                    url=url,
                    source="crossref",
                    citation_count=is_referenced_by_count,
                    venue=venue,
                ))

            self.cache.set(f"crossref:search:{query}:{limit}", papers)
        except Exception as e:
            logger.warning(f"CrossRef search failed for '{query}': {e}")

        return papers

    def get_paper(self, paper_id: str) -> Paper | None:
        doi = paper_id.replace("doi:", "").strip()
        encoded_doi = urllib.parse.quote(doi, safe="")
        url = f"{self.BASE_URL}/{encoded_doi}"
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": "ResearchOS/2.6 (mailto:researchos@lab.org)"},
                timeout=self.timeout_sec,
            )
            if not resp.ok:
                return None
            
            item = resp.json().get("message", {})
            title_list = item.get("title", [])
            title = title_list[0].strip() if title_list else "Untitled"
            
            authors: list[str] = []
            for a in item.get("author", []):
                given = a.get("given", "")
                family = a.get("family", "")
                name = f"{given} {family}".strip()
                if name:
                    authors.append(name)

            year = None
            published = item.get("published") or item.get("created") or {}
            date_parts = published.get("date-parts", [[]])[0]
            if date_parts:
                year = date_parts[0]

            container_title = item.get("container-title", [])
            venue = container_title[0] if container_title else item.get("publisher", "")
            abstract = item.get("abstract", "") or f"CrossRef DOI: {doi}"

            return Paper(
                paper_id=f"doi:{doi}",
                title=title,
                authors=authors,
                abstract=abstract,
                year=year,
                doi=doi,
                url=f"https://doi.org/{doi}",
                source="crossref",
                citation_count=item.get("is-referenced-by-count", 0),
                venue=venue,
            )
        except Exception as e:
            logger.warning(f"CrossRef get_paper failed for DOI '{doi}': {e}")
            return None
