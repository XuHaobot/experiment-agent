#!/bin/sh
# 容器启动入口：首次把种子数据放入持久化卷，再启动服务
set -e

mkdir -p /app/data

# 若持久化卷为空，从种子复制（不覆盖已有文件：-n）
if [ -z "$(ls -A /app/data 2>/dev/null)" ]; then
  echo "[entrypoint] 首次启动：初始化种子数据 -> /app/data"
  cp -rn /app/data_seed/. /app/data/ 2>/dev/null || true
fi

# 配置了 DashScope Key 时，启动时自动重建语义向量索引（仅当 collection 为空）
if [ "${AUTO_REBUILD_VECTORS:-true}" = "true" ] && [ -n "$DASHSCOPE_API_KEY" ]; then
  echo "[entrypoint] 检测到 DASHSCOPE_API_KEY，重建语义向量索引..."
  python -c "import sys; sys.path.insert(0,'/app'); from src.vector_store import VectorStore; from src.storage import RECORDS_DIR; VectorStore().index_if_empty(RECORDS_DIR); print('vector index ready')" \
    || echo "[entrypoint] 向量索引构建失败（不影响对话/关键词检索），请检查 DASHSCOPE_API_KEY"
fi

echo "[entrypoint] 启动 uvicorn :5001"
exec uvicorn backend.main:app --host 0.0.0.0 --port 5001
