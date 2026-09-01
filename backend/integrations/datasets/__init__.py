"""
Dataset Integration Package — 在线与本地数据集检索与集成
"""
from __future__ import annotations

from typing import Dict, List, Optional
from backend.integrations.datasets.base import DatasetMeta, DatasetProvider
from backend.integrations.datasets.huggingface import HuggingFaceDatasetsProvider
from backend.integrations.datasets.papers_with_code import PapersWithCodeDatasetsProvider

_PROVIDERS: Dict[str, DatasetProvider] = {
    "huggingface": HuggingFaceDatasetsProvider(),
    "papers_with_code": PapersWithCodeDatasetsProvider(),
}


def get_dataset_provider(name: str = "huggingface") -> DatasetProvider:
    """获取指定数据集提供者，默认 Hugging Face"""
    return _PROVIDERS.get(name.lower(), _PROVIDERS["huggingface"])


def search_online_datasets(query: str, source: str = "huggingface", limit: int = 10) -> list[dict]:
    """统一在线数据集检索接口，返回标准化字典列表"""
    provider = get_dataset_provider(source)
    datasets = provider.search(query, limit=limit)
    return [d.to_dict() for d in datasets]
