"""FastAPI 应用入口。

启动方式：uvicorn main:app --host 0.0.0.0 --port 8080
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import init_db

# 日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)5s | %(name)s | %(message)s",
)
logger = logging.getLogger("tiktokreg.frontend")


def create_app() -> FastAPI:
    settings = get_settings()
    init_db()
    logger.info("数据库初始化完成")

    app = FastAPI(
        title="TikTok Registrar - Control Panel",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API 路由
    from .routers import accounts, export, stats, webhook

    app.include_router(webhook.router)
    app.include_router(accounts.router)
    app.include_router(export.router)
    app.include_router(stats.router)

    # 健康检查（无需鉴权）
    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok"}

    # 静态前端文件（Vue 构建产物）
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        # 挂载 assets 目录
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        # SPA fallback：所有非 /api 路径返回 index.html
        @app.get("/{full_path:path}")
        async def spa(full_path: str) -> FileResponse | JSONResponse:
            if full_path.startswith("api"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            file_path = static_dir / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(static_dir / "index.html")
    else:
        logger.warning(f"静态目录不存在: {static_dir}，前端不会显示")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=False)
