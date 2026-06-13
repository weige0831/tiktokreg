"""Webhook 推送器：HMAC-SHA256 签名后 POST 到前端。"""
import asyncio
import hashlib
import hmac
import json
from typing import Any

import httpx

from .config_loader import WebhookConfig
from .logger import logger
from .retry import async_retry


class WebhookExporter:
    def __init__(self, cfg: WebhookConfig):
        self.cfg = cfg
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "WebhookExporter":
        self._client = httpx.AsyncClient(timeout=self.cfg.timeout)
        return self

    async def __aexit__(self, *exc) -> None:
        if self._client:
            await self._client.aclose()

    def _sign(self, payload: dict[str, Any]) -> str:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hmac.new(self.cfg.secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    @async_retry(max_retries=3, delay=2.0)
    async def post_batch(self, payload: dict[str, Any]) -> bool:
        """批量推送账号结果。"""
        if not self.cfg.url:
            logger.warning("WEBHOOK_URL 未配置，跳过推送")
            return False
        assert self._client is not None

        signature = self._sign(payload)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        logger.info(
            f"推送 webhook: url={self.cfg.url} "
            f"accounts={len(payload.get('accounts', []))}"
        )
        r = await self._client.post(
            self.cfg.url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature,
                "X-Signature-Alg": "HMAC-SHA256",
            },
        )
        if r.status_code >= 400:
            logger.error(f"webhook 推送失败: {r.status_code} {r.text[:200]}")
            r.raise_for_status()
        logger.info(f"webhook 推送成功: {r.status_code}")
        return True
