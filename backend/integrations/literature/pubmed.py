"""
PubMed / NCBI Entrez Literature Provider
官方生物医药与生命科学开放学术 API (NCBI E-utilities)
"""
from __future__ import annotations

import logging
import urllib.parse
import xml.etree.ElementTree as ET
import requests

from .base import LiteratureProvider, Paper

logger = logging.getLogger(__name__)


class PubMedProvider(LiteratureProvider):
    """PubMed NCBI Entrez API Provider"""
    name = "pubmed"
    BASE_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    BASE_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def search(self, query: str, limit: int = 5) -> list[Paper]:
        query = query.strip()
        if not query:
            return []
        
        cached = self.cache.get(f"pubmed:search:{query}:{limit}")
        if cached:
            return cached

        papers: list[Paper] = []
        try:
            # 1. 检索 ID 列表
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": limit,
                "retmode": "json",
            }
            resp = requests.get(
                self.BASE_SEARCH_URL,
                params=params,
                headers={"User-Agent": "ResearchOS/2.6 (mailto:researchos@lab.org)"},
                timeout=self.timeout_sec,
            )
            if not resp.ok:
                return []
            
            data = resp.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return []

            # 2. 批量获取概要信息
            summary_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json",
            }
            sum_resp = requests.get(
                self.BASE_SUMMARY_URL,
                params=summary_params,
                headers={"User-Agent": "ResearchOS/2.6 (mailto:researchos@lab.org)"},
                timeout=self.timeout_sec,
            )
            if sum_resp.ok:
                sum_data = sum_resp.json().get("result", {})
                for pmid in id_list:
                    p_info = sum_data.get(pmid)
                    if not p_info or not isinstance(p_info, dict):
                        continue
                    
                    title = p_info.get("title", "Untitled").rstrip(".")
                    authors = [a.get("name", "") for a in p_info.get("authors", []) if a.get("name")]
                    pub_date = p_info.get("pubdate", "")
                    year = None
                    if pub_date:
                        for part in pub_date.split():
                            if part.isdigit() and len(part) == 4:
                                year = int(part)
                                break
                    
                    venue = p_info.get("source", "")
                    article_ids = p_info.get("articleids", [])
                    doi = None
                    for aid in article_ids:
                        if aid.get("idtype") == "doi":
                            doi = aid.get("value")
                            break

                    papers.append(Paper(
                        paper_id=f"pmid:{pmid}",
                        title=title,
                        authors=authors,
                        abstract=f"PubMed PMID: {pmid}. Source: {venue}",
                        year=year,
                        doi=doi,
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        source="pubmed",
                        venue=venue,
                    ))

            self.cache.set(f"pubmed:search:{query}:{limit}", papers)
        except Exception as e:
            logger.warning(f"PubMed search failed for '{query}': {e}")

        return papers

    def get_paper(self, paper_id: str) -> Paper | None:
        pmid = paper_id.replace("pmid:", "").strip()
        results = self.search(pmid, limit=1)
        return results[0] if results else None
