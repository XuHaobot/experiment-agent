"""
BibTeX & Direct Literature Text Parser
支持将 BibTeX 文本代码或 RIS / DOI 片段无损解析为标准 Paper 实体
"""
from __future__ import annotations

import re
from typing import Any, Dict, List
from .base import Paper


def parse_bibtex(bibtex_text: str) -> list[Paper]:
    """
    解析 BibTeX 格式文本，提取论文元数据
    """
    papers: list[Paper] = []
    # 匹配 @article{key, ...} 或 @inproceedings{key, ...}
    pattern = re.compile(r'@(\w+)\s*\{\s*([^,]+),([^@]*)\}', re.DOTALL)
    
    for match in pattern.finditer(bibtex_text):
        entry_type = match.group(1).lower()
        key = match.group(2).strip()
        body = match.group(3)
        
        fields: dict[str, str] = {}
        # 匹配 field = {value} 或 field = "value" 或 field = value
        field_pattern = re.compile(r'(\w+)\s*=\s*[\{"]?(.*?)[\}"]?(?:,|\s*$)', re.DOTALL)
        for fmatch in field_pattern.finditer(body):
            fkey = fmatch.group(1).lower().strip()
            fval = fmatch.group(2).strip().rstrip('},')
            fields[fkey] = fval

        title = fields.get("title", key).strip('{}')
        author_raw = fields.get("author", "")
        authors = [a.strip().strip('{}') for a in author_raw.split(" and ") if a.strip()]
        
        year_str = fields.get("year", "")
        year = int(year_str) if year_str.isdigit() else None
        
        venue = fields.get("booktitle") or fields.get("journal") or fields.get("publisher", "")
        venue = venue.strip('{}')
        doi = fields.get("doi", "").strip('{}') or None
        url = fields.get("url", "").strip('{}') or (f"https://doi.org/{doi}" if doi else None)
        abstract = fields.get("abstract", "").strip('{}') or f"BibTeX entry ({entry_type}): {key}"

        papers.append(Paper(
            paper_id=f"bibtex:{key}",
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            doi=doi,
            url=url,
            source="bibtex",
            venue=venue,
            metadata={"bibtex_key": key, "entry_type": entry_type},
        ))

    return papers
