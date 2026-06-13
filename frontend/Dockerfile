# ============================================================
# 多阶段 Dockerfile：构建 Vue 前端 + 运行 FastAPI 后端
# 一体化部署：FastAPI 挂载 Vue 构建产物作为静态文件
# ============================================================

# ---- Stage 1: 构建 Vue 前端 ----
FROM node:20-alpine AS frontend-builder
WORKDIR /build
COPY web/package.json web/package-lock.json* ./
RUN npm config set registry https://registry.npmmirror.com && npm install
COPY web/ ./
RUN npm run build
# 产物会在 ../api/static/ 下（见 vite.config.ts 的 outDir）

# ---- Stage 2: Python 运行时 ----
FROM python:3.11-slim AS runtime
WORKDIR /app

# 系统依赖（OpenCV 需要 libGL 等）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制后端代码
COPY api/ /app/api/

# 复制前端构建产物（来自 Stage 1）
COPY --from=frontend-builder /build/../api/static /app/api/static
# 修正路径（vite outDir 设置为 ../api/static，相对 /build 解析为 /api/static）
RUN if [ ! -d /app/api/static ]; then \
        mkdir -p /app/api/static && \
        cp -r /build/../api/static/* /app/api/static/ 2>/dev/null || true; \
    fi

# 工作目录设置到 api（让 from .config import 能找到包）
WORKDIR /app/api

# 数据持久化
VOLUME ["/app/data"]

EXPOSE 8080

# 设置 PYTHONPATH 让 main.py 能正确 import
ENV PYTHONPATH=/app/api
ENV HOST=0.0.0.0
ENV PORT=8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3)" || exit 1

# 启动 FastAPI（前端已挂载到根路径）
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "/app/api"]
