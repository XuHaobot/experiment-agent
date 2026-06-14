"""
向量语义搜索引擎 — 基于 ChromaDB + DashScope Text Embedding v2。

提供实验记录的向量化存储与语义相似度检索能力，
与现有关键词搜索 (search_tool.py) 组成混合检索。
"""

import json
import os
import re
from pathlib import Path
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from src.utils import PROJECT_ROOT

if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DASHSCOPE_EMBEDDING_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
)
EMBEDDING_MODEL = "text-embedding-v2"
EMBEDDING_DIMENSION = 1536  # text-embedding-v2 输出维度
CHUNK_MAX_LENGTH = 500       # 单段文本最大字符数
CHUNK_OVERLAP = 50           # 相邻段重叠字符数

CHROMA_DIR = PROJECT_ROOT / "data" / "chroma"


# ---------------------------------------------------------------------------
# Embedding Client
# ---------------------------------------------------------------------------

class DashScopeEmbedding:
    """DashScope text-embedding-v2 客户端。"""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """将一组文本转换为向量列表。

        DashScope 单次最多 25 条文本，超出时自动分批。
        """
        if not self.is_configured:
            raise RuntimeError(
                "DASHSCOPE_API_KEY 未配置。请在 .env 中设置。"
            )

        all_embeddings: list[list[float]] = []
        batch_size = 25

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            embeddings = self._request(batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    def embed_query(self, query: str) -> list[float]:
        """单条查询文本的向量。"""
        return self.embed([query])[0]

    def _request(self, texts: list[str]) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": EMBEDDING_MODEL,
            "input": {"texts": texts},
        }
        resp = requests.post(DASHSCOPE_EMBEDDING_URL, headers=headers, json=payload, timeout=30)

        if resp.status_code >= 400:
            raise RuntimeError(f"DashScope Embedding API 错误: HTTP {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        try:
            items = data["output"]["embeddings"]
        except (KeyError, TypeError):
            raise RuntimeError(f"DashScope 响应格式异常: {json.dumps(data, ensure_ascii=False)[:300]}")

        # 按 text_index 排序确保顺序正确
        items_sorted = sorted(items, key=lambda x: x.get("text_index", 0))
        return [item["embedding"] for item in items_sorted]


# ---------------------------------------------------------------------------
# Text Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, max_length: int = CHUNK_MAX_LENGTH, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """将长文本切分为带重叠的段落，用于向量化。

    优先按段落（\\n\\n）切分，超长段落再按句号/换行切分。
    """
    text = text.strip()
    if not text:
        return []

    # 先按双换行分大段
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        candidate = f"{current_chunk}\n\n{para}".strip() if current_chunk else para

        if len(candidate) <= max_length:
            current_chunk = candidate
        else:
            # 保存当前 chunk
            if current_chunk:
                chunks.append(current_chunk)

            # 如果单个段落就超长，按句子进一步切分
            if len(para) > max_length:
                sub_chunks = _split_long_paragraph(para, max_length, overlap)
                chunks.extend(sub_chunks[:-1])
                current_chunk = sub_chunks[-1] if sub_chunks else ""
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks or [text[:max_length]]


def _split_long_paragraph(text: str, max_length: int, overlap: int) -> list[str]:
    """按句子边界切分超长段落。"""
    sentences = re.split(r"(?<=[。！？\.\!\?])\s*", text)
    chunks: list[str] = []
    current = ""

    for sent in sentences:
        candidate = f"{current}{sent}" if current else sent
        if len(candidate) <= max_length:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # 重叠：取前一段尾部 overlap 个字符作为下一段开头
            if overlap > 0 and current:
                current = current[-overlap:] + sent
            else:
                current = sent

    if current:
        chunks.append(current)

    return chunks


# ---------------------------------------------------------------------------
# Record → 可索引文本
# ---------------------------------------------------------------------------

def record_to_text(record: dict) -> str:
    """将一条实验记录的关键字段拼接为可索引的自然语言文本。"""
    parts: list[str] = []

    if record.get("task"):
        parts.append(f"实验任务: {record['task']}")
    if record.get("dataset"):
        parts.append(f"数据集: {record['dataset']}")
    if record.get("model"):
        parts.append(f"模型: {record['model']}")

    # 参数
    params = record.get("params", {})
    if isinstance(params, dict):
        for layer in ("original", "adjusted", "suggested"):
            layer_params = params.get(layer, {})
            if layer_params:
                params_str = ", ".join(f"{k}={v}" for k, v in layer_params.items())
                parts.append(f"{layer}参数: {params_str}")

    # 命令
    commands = record.get("commands", [])
    if commands:
        cmd_text = "; ".join(str(c) for c in commands)
        parts.append(f"执行命令: {cmd_text}")

    # 错误 & 解决方案
    errors = record.get("errors", [])
    if errors:
        parts.append(f"错误: {'; '.join(str(e) for e in errors)}")

    solutions = record.get("solutions", [])
    if solutions:
        parts.append(f"解决方案: {'; '.join(str(s) for s in solutions)}")

    if record.get("conclusion"):
        parts.append(f"结论: {record['conclusion']}")
    if record.get("next_step"):
        parts.append(f"下一步: {record['next_step']}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# VectorStore
# ---------------------------------------------------------------------------

class VectorStore:
    """基于 ChromaDB 的向量语义搜索引擎。"""

    def __init__(
        self,
        persist_dir: str | Path | None = None,
        embedding: DashScopeEmbedding | None = None,
    ):
        self._persist_dir = str(persist_dir or CHROMA_DIR)
        self._embedding = embedding or DashScopeEmbedding()
        self._client = None
        self._collection = None

    @property
    def is_ready(self) -> bool:
        """ChromaDB 可用且 Embedding 已配置。"""
        return self._embedding.is_configured

    def _ensure_client(self):
        """延迟初始化 ChromaDB 客户端。"""
        if self._client is not None:
            return

        try:
            import chromadb
        except ImportError:
            raise RuntimeError("chromadb 未安装。请运行: pip install chromadb")

        self._client = chromadb.PersistentClient(path=self._persist_dir)
        self._collection = self._client.get_or_create_collection(
            name="experiment_records",
            metadata={"hnsw:space": "cosine"},
        )

    # --- 写入 ---

    def index_record(self, record: dict) -> int:
        """将一条实验记录向量化并存入 ChromaDB。

        返回写入的 chunk 数量。
        """
        self._ensure_client()

        record_id = record.get("id", "")
        if not record_id:
            return 0

        text = record_to_text(record)
        chunks = chunk_text(text)

        if not chunks:
            return 0

        embeddings = self._embedding.embed(chunks)

        metadata_base = {
            "record_id": record_id,
            "task": record.get("task", "")[:200],
            "dataset": record.get("dataset", "")[:200],
            "model": record.get("model", "")[:200],
        }

        ids = [f"{record_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{**metadata_base, "chunk_index": i} for i in range(len(chunks))]

        self._collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        return len(chunks)

    def index_records_batch(self, records: list[dict]) -> dict[str, int]:
        """批量索引多条记录。返回 {record_id: chunk_count}。"""
        results = {}
        for record in records:
            try:
                count = self.index_record(record)
                results[record.get("id", "?")] = count
            except Exception as exc:
                results[record.get("id", "?")] = -1
        return results

    # --- 搜索 ---

    def semantic_search(self, query: str, top_k: int = 5) -> list[dict]:
        """语义相似度搜索。

        返回 top_k 个最相关的记录片段，每个包含：
        - record_id, chunk_index, document, score (cosine similarity)
        """
        self._ensure_client()

        if self._collection.count() == 0:
            return []

        query_embedding = self._embedding.embed_query(query)

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict] = []
        if not results.get("ids"):
            return hits

        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for idx, doc_id in enumerate(ids):
            meta = metadatas[idx]
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # 转换为相似度分数：1 - distance/2
            similarity = 1.0 - distances[idx] / 2.0

            hits.append({
                "id": doc_id,
                "record_id": meta.get("record_id", ""),
                "chunk_index": meta.get("chunk_index", 0),
                "document": documents[idx],
                "score": round(similarity, 4),
                "task": meta.get("task", ""),
                "dataset": meta.get("dataset", ""),
                "model": meta.get("model", ""),
            })

        return hits

    # --- 管理 ---

    def delete_record(self, record_id: str) -> int:
        """删除指定记录的所有 chunk。返回删除数量。"""
        self._ensure_client()

        # 先查出该 record 的所有 chunk
        existing = self._collection.get(
            where={"record_id": record_id},
            include=[],
        )

        if not existing.get("ids"):
            return 0

        self._collection.delete(ids=existing["ids"])
        return len(existing["ids"])

    def stats(self) -> dict:
        """返回向量库统计信息。"""
        self._ensure_client()
        count = self._collection.count()
        return {
            "total_chunks": count,
            "collection_name": self._collection.name,
            "persist_dir": self._persist_dir,
            "embedding_model": EMBEDDING_MODEL,
            "embedding_configured": self._embedding.is_configured,
        }

    def rebuild_index(self, records_dir: str | Path) -> dict:
        """从 records 目录重建整个向量索引。"""
        self._ensure_client()

        # 清空现有数据
        if self._collection.count() > 0:
            # 获取所有 ID 然后删除
            all_ids = self._collection.get(include=[])
            if all_ids.get("ids"):
                self._collection.delete(ids=all_ids["ids"])

        records_path = Path(records_dir)
        if not records_path.exists():
            return {"indexed": 0, "errors": 0}

        indexed = 0
        errors = 0

        for f in sorted(records_path.glob("*.json")):
            try:
                record = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(record, dict):
                    self.index_record(record)
                    indexed += 1
            except Exception:
                errors += 1

        return {"indexed": indexed, "errors": errors}


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

_vector_store_instance: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """获取全局 VectorStore 单例，避免重复创建 ChromaDB 客户端。"""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
