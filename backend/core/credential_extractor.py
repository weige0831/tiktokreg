"""凭证提取器：从已注册的 BrowserContext 中抓取 cookie / localStorage / sessionid。"""
import json
from typing import Any

from playwright.async_api import BrowserContext

from .config_loader import AppConfig
from .fingerprint_gen import Fingerprint


async def extract_credentials(
    context: BrowserContext,
    cfg: AppConfig,
    fingerprint: Fingerprint,
    email: str,
    password: str,
    username: str | None,
    birth_date: str,
    proxy_used: str | None,
) -> dict[str, Any]:
    """从 BrowserContext 抓取所有凭证。"""
    cookies = await context.cookies()
    cookie_map = {c["name"]: c["value"] for c in cookies}

    # 抓 msToken（可能在 localStorage 里）
    # 由于我们抓不到具体的 page 对象，这里只能从 cookie 里拿
    important = {}
    for name in cfg.credentials.important_cookies:
        if name in cookie_map:
            important[name] = cookie_map[name]

    return {
        "email": email,
        "password": password,
        "username": username,
        "birth_date": birth_date,
        "session_id": cookie_map.get("sessionid") or cookie_map.get("sessionid_ss") or "",
        "tt_target_idc": cookie_map.get("tt-target-idc", ""),
        "ms_token": cookie_map.get("msToken", ""),
        "cookies_json": json.dumps(cookies, ensure_ascii=False),
        "important_cookies": important,
        "user_agent": fingerprint.user_agent,
        "proxy_used": proxy_used,
        "fingerprint_hash": fingerprint.hash,
        "timezone": fingerprint.timezone,
        "locale": fingerprint.locale,
        "viewport": fingerprint.viewport,
    }
