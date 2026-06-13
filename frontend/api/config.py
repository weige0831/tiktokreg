"""配置项：环境变量加载。"""
import os
import secrets
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Webhook 鉴权
    webhook_secret: str = ""

    # Basic Auth
    admin_user: str = "admin"
    admin_password: str = ""

    # 数据库
    database_url: str = f"sqlite:///./data/accounts.db"

    # 服务器
    host: str = "0.0.0.0"
    port: int = 8080

    # 数据目录
    data_dir: Path = Path("./data")

    # CORS（前端同源不用，预留）
    cors_origins: list[str] = ["*"]


def get_settings() -> Settings:
    s = Settings()
    # 自动生成 admin 密码（如果未设置）
    if not s.admin_password:
        s.admin_password = secrets.token_urlsafe(16)
        # 输出到 stderr（避免 uvicorn 日志淹没），方便用户首次部署时获取
        print("=" * 60, file=sys.stderr)
        print(f"[初始启动] ADMIN_USER={s.admin_user}", file=sys.stderr)
        print(f"[初始启动] ADMIN_PASSWORD={s.admin_password}", file=sys.stderr)
        print("请妥善保存！如需自定义，设置 ADMIN_PASSWORD 环境变量", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
    if not s.webhook_secret:
        s.webhook_secret = secrets.token_urlsafe(32)
        print(f"[初始启动] WEBHOOK_SECRET={s.webhook_secret}", file=sys.stderr)
        print("请将此值同步到 GitHub Actions Secrets", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
    # 确保数据目录存在
    s.data_dir.mkdir(parents=True, exist_ok=True)
    (s.data_dir / "accounts").mkdir(parents=True, exist_ok=True)
    return s
