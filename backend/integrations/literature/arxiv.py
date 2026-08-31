"""
arXiv Literature Provider Adapter — 基于官方 Atom API 解析
"""
from __future__ import annotations

import logging
import urllib.parse
import xml.etree.ElementTree as ET
import requests

from backend.integrations.literature.base import LiteratureProvider, Paper

logger = logging.getLogger(__name__)

_ARXIV_API_BASE = "http://export.arxiv.org/api/query"
_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArxivProvider(LiteratureProvider):
    name: str = "arxiv"

    def _parse_entry(self, entry: ET.Element) -> Paper:
        id_elem = entry.find("atom:id", _ATOM_NS)
        raw_id = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
        paper_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id

        title_elem = entry.find("atom:title", _ATOM_NS)
        title = " ".join((title_elem.text or "").strip().split()) if title_elem is not None else "Untitled"

        summary_elem = entry.find("atom:summary", _ATOM_NS)
        abstract = " ".join((summary_elem.text or "").strip().split()) if summary_elem is not None else ""

        authors = []
        for a_elem in entry.findall("atom:author", _ATOM_NS):
            n_elem = a_elem.find("atom:name", _ATOM_NS)
            if n_elem is not None and n_elem.text:
                authors.append(n_elem.text.strip())

        pub_elem = entry.find("atom:published", _ATOM_NS)
        year = None
        if pub_elem is not None and pub_elem.text and len(pub_elem.text) >= 4:
            try:
                year = int(pub_elem.text[:4])
            except ValueError:
                pass

        pdf_url = None
        for link in entry.findall("atom:link", _ATOM_NS):
            if link.attrib.get("title") == "pdf":
                pdf_url = link.attrib.get("href")
                break

        doi_elem = entry.find("arxiv:doi", _ATOM_NS)
        doi = doi_elem.text.strip() if doi_elem is not None and doi_elem.text else None

        return Paper(
            paper_id=f"arxiv_{paper_id}",
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            doi=doi,
            url=raw_id or f"https://arxiv.org/abs/{paper_id}",
            source="arxiv",
            citation_count=0,
            venue="arXiv preprint",
            pdf_url=pdf_url,
            metadata={"arxiv_id": paper_id},
        )

    def search(self, query: str, limit: int = 5) -> list[Paper]:
        query = query.strip()
        if not query:
            return []

        cache_key = f"arxiv:search:{query}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # 格式化 query
        safe_q = urllib.parse.quote(query)
        url = f"{_ARXIV_API_BASE}?search_query=all:{safe_q}&start=0&max_results={min(max(1, limit), 20)}"

        try:
            resp = requests.get(url, timeout=self.timeout_sec)
            if resp.status_code != 200:
                logger.warning("arXiv API returned code %d", resp.status_code)
                return []

            root = ET.fromstring(resp.content)
            entries = root.findall("atom:entry", _ATOM_NS)
            results = [self._parse_entry(e) for e in entries]
            self.cache.set(cache_key, results)
            return results
        except Exception as e:
            logger.warning("arXiv search failed: %s", e)
            return []

    def get_paper(self, paper_id: str) -> Paper | None:
        clean_id = paper_id.replace("arxiv_", "").strip()
        if not clean_id:
            return None

        cache_key = f"arxiv:paper:{clean_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        url = f"{_ARXIV_API_BASE}?id_list={urllib.parse.quote(clean_id)}"
        try:
            resp = requests.get(url, timeout=self.timeout_sec)
            if resp.status_code != 200:
                return None
            root = ET.fromstring(resp.content)
            entries = root.findall("atom:entry", _ATOM_NS)
            if entries:
                paper = self._parse_entry(entries[0])
                self.cache.set(cache_key, paper)
                return paper
            return None
        except Exception as e:
            logger.warning("arXiv get_paper failed: %s", e)
            return None
