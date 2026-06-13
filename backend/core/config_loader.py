"""配置加载器：合并 yaml 默认值与环境变量。"""
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class TempmailConfig(BaseModel):
    base_url: str = ""
    username_length: int = 10
    username_chars: str = "abcdefghijklmnopqrstuvwxyz0123456789"
    poll_interval: int = 3
    poll_timeout: int = 120


class ProxyConfig(BaseModel):
    enabled: bool = False
    proxy_file: str = "proxies.txt"
    max_uses_per_proxy: int = 3
    max_fails_per_proxy: int = 3


class WebhookConfig(BaseModel):
    url: str = ""
    secret: str = ""
    timeout: int = 30
    max_retries: int = 3


class HumanConfig(BaseModel):
    type_delay_min: int = 80
    type_delay_max: int = 220
    mouse_step_delay_min: int = 5
    mouse_step_delay_max: int = 25
    action_pause_min: float = 0.8
    action_pause_max: float = 2.5
    slider_drag_duration_min: float = 0.8
    slider_drag_duration_max: float = 1.6


class RegisterConfig(BaseModel):
    count: int = 5
    concurrency: int = 2
    single_account_timeout: int = 180
    captcha_max_retries: int = 3
    register_max_retries: int = 2


class BrowserConfig(BaseModel):
    viewports: list[dict] = []
    timezones: list[str] = []
    locales: list[str] = []


class CredentialsConfig(BaseModel):
    important_cookies: list[str] = []


class AppConfig(BaseModel):
    register: RegisterConfig
    human: HumanConfig
    tempmail: TempmailConfig
    proxy: ProxyConfig
    webhook: WebhookConfig
    browser: BrowserConfig
    credentials: CredentialsConfig


def load_config(config_path: str | Path = "config.yaml") -> AppConfig:
    p = Path(config_path)
    if not p.exists():
        # 兜底默认值
        raw: dict[str, Any] = {}
    else:
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    # 环境变量覆盖（优先级最高）
    tempmail_section = raw.get("tempmail", {})
    tempmail_section["base_url"] = os.environ.get(
        "TEMPMAIL_BASE_URL", tempmail_section.get("base_url", "")
    )

    webhook_section = raw.get("webhook", {})
    webhook_section["url"] = os.environ.get("WEBHOOK_URL", webhook_section.get("url", ""))
    webhook_section["secret"] = os.environ.get(
        "WEBHOOK_SECRET", webhook_section.get("secret", "")
    )

    raw["tempmail"] = tempmail_section
    raw["webhook"] = webhook_section

    return AppConfig(
        register=RegisterConfig(**raw.get("register", {})),
        human=HumanConfig(**raw.get("human", {})),
        tempmail=TempmailConfig(**tempmail_section),
        proxy=ProxyConfig(**raw.get("proxy", {})),
        webhook=WebhookConfig(**webhook_section),
        browser=BrowserConfig(**raw.get("browser", {})),
        credentials=CredentialsConfig(**raw.get("credentials", {})),
    )
