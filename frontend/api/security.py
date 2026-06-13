"""HMAC 签名验证 + Basic Auth 中间件。"""
import hashlib
import hmac
import secrets as secrets_mod

from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import get_settings

_security = HTTPBasic()


def verify_basic_auth(credentials: HTTPBasicCredentials = Security(_security)) -> str:
    """Basic Auth 校验。用于所有非 webhook 端点。"""
    settings = get_settings()
    is_user_ok = hmac.compare_digest(credentials.username.encode(), settings.admin_user.encode())
    is_pass_ok = hmac.compare_digest(credentials.password.encode(), settings.admin_password.encode())
    if not (is_user_ok and is_pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


async def verify_webhook_signature(request: Request) -> None:
    """Webhook 签名校验。读取 X-Signature header，用 HMAC-SHA256 验证。"""
    settings = get_settings()
    sig = request.headers.get("X-Signature")
    if not sig:
        raise HTTPException(status_code=401, detail="Missing X-Signature header")

    body = await request.body()
    expected = hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=401, detail="Invalid signature")
