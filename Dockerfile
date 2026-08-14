# ============================================================
# experiment-agent 部署镜像（单容器同时跑前后端）
# 构建上下文：项目根目录
# ============================================================

# ---------- 阶段 1：构建前端 ----------
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---------- 阶段 2：运行环境 ----------
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=5001

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端 + 业务代码
COPY backend/ ./backend/
COPY src/ ./src/
COPY prompts/ ./prompts/

# 复制数据作为「种子」（不含 chroma 索引与 memory.db，运行时重建）
COPY data/ ./data_seed/

# 前端构建产物
COPY --from=frontend /build/dist ./frontend/dist

# 启动脚本
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

EXPOSE 5001
ENTRYPOINT ["./entrypoint.sh"]
