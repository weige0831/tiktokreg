"""临时邮箱客户端：对接 mail.Minecraft-cn.net 的 tempmail-server。"""
import asyncio
import random
import re
import string

import httpx

from .config_loader import TempmailConfig
from .logger import logger

# TikTok 邮箱验证码正则：6 位数字
_TIKTOK_CODE_PATTERNS = [
    re.compile(r"\b(\d{6})\b"),
    re.compile(r"verification code[:\s]+(\d{6})", re.IGNORECASE),
    re.compile(r"code is[:\s]+(\d{6})", re.IGNORECASE),
]


class TempMailClient:
    def __init__(self, cfg: TempmailConfig):
        self.cfg = cfg
        self.base_url = cfg.base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "TempMailClient":
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._client:
            await self._client.aclose()

    def _gen_username(self) -> str:
        return "".join(
            random.choices(self.cfg.username_chars, k=self.cfg.username_length)
        )

    async def get_domains(self) -> list[str]:
        """获取可用域名列表。"""
        assert self._client is not None
        r = await self._client.get("/api/v1/domains")
        r.raise_for_status()
        data = r.json()
        return data.get("domains", [])

    async def create_address(self, username: str | None = None) -> tuple[str, str]:
        """创建临时邮箱。返回 (email, token)。"""
        assert self._client is not None
        uname = username or self._gen_username()
        logger.info(f"创建临时邮箱: {uname}")
        r = await self._client.post(
            "/api/v1/addresses",
            json={"username": uname},
        )
        r.raise_for_status()
        data = r.json()
        return data["email"], data["token"]

    async def poll_verification_code(self, token: str) -> str:
        """轮询邮箱直到收到 TikTok 验证码邮件。返回 6 位数字。"""
        assert self._client is not None
        deadline = asyncio.get_event_loop().time() + self.cfg.poll_timeout
        last_seen_ids: set[str] = set()
        while asyncio.get_event_loop().time() < deadline:
            try:
                r = await self._client.get(f"/api/v1/{token}/emails")
                r.raise_for_status()
                data = r.json()
                for mail in data.get("emails", []):
                    if mail["id"] in last_seen_ids:
                        continue
                    last_seen_ids.add(mail["id"])
                    code = await self._extract_code(mail["id"], token)
                    if code:
                        logger.info(f"收到验证码: {code}")
                        return code
            except Exception as e:
                logger.warning(f"轮询邮箱失败: {e}")
            await asyncio.sleep(self.cfg.poll_interval)
        raise TimeoutError(f"等待验证码超时 ({self.cfg.poll_timeout}s)")

    async def _extract_code(self, mail_id: str, token: str) -> str | None:
        """获取邮件详情，正则提取验证码。"""
        assert self._client is not None
        r = await self._client.get(f"/api/v1/{token}/emails/{mail_id}")
        r.raise_for_status()
        data = r.json()
        # 优先从 HTML body 提取
        body = data.get("html_body") or data.get("plain_text") or ""
        for pattern in _TIKTOK_CODE_PATTERNS:
            m = pattern.search(body)
            if m:
                # 简单过滤：4 位以下不算
                code = m.group(1)
                if len(code) == 6:
                    return code
        return None
