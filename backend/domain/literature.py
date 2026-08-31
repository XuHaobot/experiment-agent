"""
Literature Agent — 封装 OpenAlex 和 Semantic Scholar 公开 REST API。

两者均为免费无需 API Key 的学术数据源：
- OpenAlex: https://api.openalex.org  (mailto 参数可提高速率限制)
- Semantic Scholar: https://api.semanticscholar.org/graph/v1

用法：
    results = search_papers("transformer scaling law", source="openalex", limit=5)
    results = search_papers("transformer scaling law", source="semantic_scholar", limit=5)
    detail  = get_paper_by_doi("10.xxx/xxx", source="openalex")
"""

import re
import time
import os
from typing import Optional
import requests


_OPENALEX_BASE = "https://api.openalex.org"
_S2_BASE = "https://api.semanticscholar.org/graph/v1"

# 开发者 email（可选，OpenAlex polite pool 用）
_OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO", "")

_DEFAULT_TIMEOUT = 15


# ---------------------------------------------------------------------------
# 统一搜索入口
# ---------------------------------------------------------------------------

def search_papers(
    query: str,
    source: str = "openalex",
    limit: int = 8,
) -> list[dict]:
    """
    搜索论文，返回标准化 paper 列表。

    每条记录格式：
    {
        "id": "...",
        "title": "...",
        "abstract": "...",
        "year": 2024,
        "authors": ["Author A", "Author B"],
        "venue": "...",
        "doi": "...",
        "url": "...",
        "citation_count": 123,
        "source": "openalex" | "semantic_scholar",
    }
    """
    if not query.strip():
        return []

    if source == "semantic_scholar":
        return _search_s2(query, limit)
    else:
        return _search_openalex(query, limit)


def get_paper_detail(paper_id: str, source: str = "openalex") -> Optional[dict]:
    """
    根据 paper ID 获取详细信息。
    - OpenAlex: paper_id 为 W 开头的 ID
    - Semantic Scholar: paper_id 为 S2 论文 ID
    """
    if source == "semantic_scholar":
        return _get_s2_paper(paper_id)
    else:
        return _get_openalex_paper(paper_id)


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------

def _openalex_headers() -> dict:
    h = {"Accept": "application/json"}
    if _OPENALEX_MAILTO:
        h["User-Agent"] = f"ResearchOS/2.0 (mailto:{_OPENALEX_MAILTO})"
    return h


def _search_openalex(query: str, limit: int) -> list[dict]:
    params = {
        "search": query,
        "per-page": min(limit, 25),
        "select": "id,title,abstract_inverted_index,publication_year,authorships,primary_location,doi,cited_by_count,open_access",
    }
    if _OPENALEX_MAILTO:
        params["mailto"] = _OPENALEX_MAILTO

    try:
        resp = requests.get(
            f"{_OPENALEX_BASE}/works",
            params=params,
            headers=_openalex_headers(),
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("results", []):
            results.append(_normalize_openalex(item))
        return results
    except Exception as e:
        return [{"error": str(e), "source": "openalex"}]


def _normalize_openalex(item: dict) -> dict:
    authors = []
    for a in item.get("authorships", [])[:5]:
        name = a.get("author", {}).get("display_name", "")
        if name:
            authors.append(name)

    venue = ""
    loc = item.get("primary_location") or {}
    src = loc.get("source") or {}
    venue = src.get("display_name", "")

    oa_url = ""
    oa = item.get("open_access") or {}
    oa_url = oa.get("oa_url", "") or ""

    doi = item.get("doi", "") or ""
    if doi.startswith("https://doi.org/"):
        doi = doi[len("https://doi.org/"):]

    return {
        "id": item.get("id", "").replace("https://openalex.org/", ""),
        "title": item.get("title", ""),
        "abstract": _reconstruct_abstract(item.get("abstract_inverted_index")),
        "year": item.get("publication_year"),
        "authors": authors,
        "venue": venue,
        "doi": doi,
        "url": oa_url or (f"https://doi.org/{doi}" if doi else ""),
        "citation_count": item.get("cited_by_count", 0),
        "source": "openalex",
    }


def _reconstruct_abstract(inverted_index: Optional[dict]) -> str:
    """将 OpenAlex 倒排索引格式的摘要还原为纯文本。"""
    if not inverted_index:
        return ""
    try:
        positions = {}
        for word, pos_list in inverted_index.items():
            for pos in pos_list:
                positions[pos] = word
        words = [positions[i] for i in sorted(positions)]
        return " ".join(words)
    except Exception:
        return ""


def _get_openalex_paper(paper_id: str) -> Optional[dict]:
    oa_id = paper_id if paper_id.startswith("W") else f"W{paper_id}"
    params = {}
    if _OPENALEX_MAILTO:
        params["mailto"] = _OPENALEX_MAILTO
    try:
        resp = requests.get(
            f"{_OPENALEX_BASE}/works/{oa_id}",
            params=params,
            headers=_openalex_headers(),
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return _normalize_openalex(resp.json())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Semantic Scholar
# ---------------------------------------------------------------------------

_S2_FIELDS = "paperId,title,abstract,year,authors,venue,externalIds,citationCount,openAccessPdf,url"


def _search_s2(query: str, limit: int) -> list[dict]:
    params = {
        "query": query,
        "limit": min(limit, 20),
        "fields": _S2_FIELDS,
    }
    try:
        resp = requests.get(
            f"{_S2_BASE}/paper/search",
            params=params,
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return [_normalize_s2(p) for p in data.get("data", [])]
    except Exception as e:
        return [{"error": str(e), "source": "semantic_scholar"}]


def _normalize_s2(item: dict) -> dict:
    authors = [a.get("name", "") for a in item.get("authors", [])[:5]]
    doi = (item.get("externalIds") or {}).get("DOI", "")
    pdf_url = (item.get("openAccessPdf") or {}).get("url", "") or item.get("url", "") or ""
    return {
        "id": item.get("paperId", ""),
        "title": item.get("title", ""),
        "abstract": item.get("abstract", "") or "",
        "year": item.get("year"),
        "authors": authors,
        "venue": item.get("venue", "") or "",
        "doi": doi,
        "url": pdf_url or (f"https://doi.org/{doi}" if doi else f"https://www.semanticscholar.org/paper/{item.get('paperId', '')}"),
        "citation_count": item.get("citationCount", 0),
        "source": "semantic_scholar",
    }


def _get_s2_paper(paper_id: str) -> Optional[dict]:
    try:
        resp = requests.get(
            f"{_S2_BASE}/paper/{paper_id}",
            params={"fields": _S2_FIELDS},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return _normalize_s2(resp.json())
    except Exception:
        return None
