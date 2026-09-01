"""
Dataset Integration Base Architecture — 统一数据集抽象基类与实体
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DatasetMeta:
    """标准化在线/本地数据集数据实体"""
    def __init__(
        self,
        dataset_id: str,
        name: str,
        description: str = "",
        source: str = "huggingface",
        url: str | None = None,
        downloads: int = 0,
        likes: int = 0,
        papers_count: int = 0,
        tasks: list[str] | None = None,
        modalities: list[str] | None = None,
        license: str = "",
        viewer_url: str | None = None,
        load_code: str = "",
        metadata: dict[str, Any] | None = None,
    ):
        self.dataset_id = dataset_id
        self.name = name.strip()
        self.description = description.strip()
        self.source = source
        self.url = url
        self.downloads = downloads
        self.likes = likes
        self.papers_count = papers_count
        self.tasks = tasks or []
        self.modalities = modalities or []
        self.license = license
        self.viewer_url = viewer_url
        self.load_code = load_code
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "id": self.dataset_id,
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "url": self.url,
            "downloads": self.downloads,
            "likes": self.likes,
            "papers_count": self.papers_count,
            "tasks": self.tasks,
            "modalities": self.modalities,
            "license": self.license,
            "viewer_url": self.viewer_url,
            "load_code": self.load_code,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetMeta:
        return cls(
            dataset_id=data.get("dataset_id") or data.get("id") or "",
            name=data.get("name", ""),
            description=data.get("description", ""),
            source=data.get("source", "unknown"),
            url=data.get("url"),
            downloads=data.get("downloads", 0),
            likes=data.get("likes", 0),
            papers_count=data.get("papers_count", 0),
            tasks=data.get("tasks", []),
            modalities=data.get("modalities", []),
            license=data.get("license", ""),
            viewer_url=data.get("viewer_url"),
            load_code=data.get("load_code", ""),
            metadata=data.get("metadata", {}),
        )


class DatasetProvider(ABC):
    """在线数据集提供者抽象接口"""
    name: str = "base"

    def __init__(self, timeout_sec: int = 12):
        self.timeout_sec = timeout_sec

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[DatasetMeta]:
        """检索公开数据集"""
        pass
