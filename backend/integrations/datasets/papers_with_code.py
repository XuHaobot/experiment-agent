"""
Papers With Code Benchmark Datasets Provider
官方学术评测基准数据集检索接口 (https://paperswithcode.com/api/v1/datasets/)
"""
from __future__ import annotations

import logging
import requests

from .base import DatasetMeta, DatasetProvider

logger = logging.getLogger(__name__)


class PapersWithCodeDatasetsProvider(DatasetProvider):
    """Papers With Code Benchmark Datasets Provider"""
    name = "papers_with_code"
    BASE_URL = "https://paperswithcode.com/api/v1/datasets/"

    def search(self, query: str, limit: int = 10) -> list[DatasetMeta]:
        query = query.strip()
        if not query:
            return []

        results: list[DatasetMeta] = []
        try:
            params = {
                "q": query,
                "page": 1,
                "items_per_page": limit,
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
            items = data.get("results", [])
            for item in items:
                pwc_id = item.get("id") or item.get("name", "")
                name = item.get("name", pwc_id)
                description = item.get("description", "") or f"Benchmark dataset: {name}"
                url = item.get("url") or item.get("homepage") or f"https://paperswithcode.com/dataset/{pwc_id}"
                num_papers = item.get("num_papers", 0)
                modalities = item.get("modalities", [])
                tasks = [t.get("task", "") for t in item.get("tasks", []) if isinstance(t, dict)]

                results.append(DatasetMeta(
                    dataset_id=f"pwc:{pwc_id}",
                    name=name,
                    description=description,
                    source="papers_with_code",
                    url=url,
                    papers_count=num_papers,
                    tasks=tasks,
                    modalities=modalities,
                    viewer_url=url,
                    load_code=f"# Benchmark dataset: {name}\n# Homepage: {url}",
                    metadata={"homepage": item.get("homepage", ""), "variants": item.get("variants", [])},
                ))
        except Exception as e:
            logger.warning(f"PapersWithCode dataset search failed for '{query}': {e}")

        return results
