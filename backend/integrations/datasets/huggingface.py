"""
Hugging Face Datasets Provider
官方开放数据集检索接口 (https://huggingface.co/api/datasets)
"""
from __future__ import annotations

import logging
import requests

from .base import DatasetMeta, DatasetProvider

logger = logging.getLogger(__name__)


class HuggingFaceDatasetsProvider(DatasetProvider):
    """Hugging Face Hub Open Datasets Provider"""
    name = "huggingface"
    BASE_URL = "https://huggingface.co/api/datasets"

    def search(self, query: str, limit: int = 10) -> list[DatasetMeta]:
        query = query.strip()
        if not query:
            return []

        results: list[DatasetMeta] = []
        try:
            params = {
                "search": query,
                "limit": limit,
                "full": "true",
            }
            resp = requests.get(
                self.BASE_URL,
                params=params,
                headers={"User-Agent": "ResearchOS/2.6 (mailto:researchos@lab.org)"},
                timeout=self.timeout_sec,
            )
            if not resp.ok:
                return []

            items = resp.json()
            if not isinstance(items, list):
                return []

            for item in items:
                ds_id = item.get("id") or item.get("_id") or ""
                description = item.get("description", "") or (f"Hugging Face dataset: {ds_id}")
                downloads = item.get("downloads", 0)
                likes = item.get("likes", 0)
                tags = item.get("tags", [])
                
                # 过滤出 task 与 modality 标签
                tasks = [t.replace("task_categories:", "") for t in tags if t.startswith("task_categories:")]
                modalities = [t.replace("modality:", "") for t in tags if t.startswith("modality:")]
                license_tag = next((t.replace("license:", "") for t in tags if t.startswith("license:")), "")

                url = f"https://huggingface.co/datasets/{ds_id}"
                load_code = f"from datasets import load_dataset\ndataset = load_dataset('{ds_id}')"

                results.append(DatasetMeta(
                    dataset_id=f"hf:{ds_id}",
                    name=ds_id,
                    description=description,
                    source="huggingface",
                    url=url,
                    downloads=downloads,
                    likes=likes,
                    tasks=tasks,
                    modalities=modalities,
                    license=license_tag,
                    viewer_url=f"https://huggingface.co/datasets/{ds_id}/viewer",
                    load_code=load_code,
                    metadata={"author": item.get("author", ""), "private": item.get("private", False)},
                ))
        except Exception as e:
            logger.warning(f"Hugging Face dataset search failed for '{query}': {e}")

        return results
