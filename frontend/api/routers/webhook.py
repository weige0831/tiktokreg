"""Webhook 接收端点：HMAC 验签 + 三合一存储。"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db, session_scope
from ..security import verify_webhook_signature
from ..storage import store_account

router = APIRouter(prefix="/api/webhook", tags=["webhook"])
logger = logging.getLogger(__name__)


class AccountPayload(BaseModel):
    email: str
    password: str
    username: str | None = None
    birth_date: str | None = None
    session_id: str | None = None
    tt_target_idc: str | None = None
    ms_token: str | None = None
    cookies_json: str | None = None
    important_cookies: dict[str, Any] | None = None
    user_agent: str | None = None
    proxy_used: str | None = None
    fingerprint_hash: str | None = None
    timezone: str | None = None
    locale: str | None = None
    viewport: dict | None = None
    status: str = "success"
    error_msg: str | None = None
    registered_at: str | None = None
    batch_id: str | None = None


class BatchPayload(BaseModel):
    batch_id: str | None = None
    registered_at: str | None = None
    total: int = 0
    success_count: int = 0
    failed_count: int = 0
    accounts: list[AccountPayload] = Field(default_factory=list)


class BatchResponse(BaseModel):
    received: int
    stored: int
    skipped: int


@router.post("/accounts", response_model=BatchResponse)
async def receive_accounts(
    request: Request,
    db: Session = Depends(get_db),
) -> BatchResponse:
    """接收来自后端注册机的批量账号推送。"""
    # 1. HMAC 验签
    await verify_webhook_signature(request)

    # 2. 解析 body（已经过验签）
    raw = await request.body()
    import json

    try:
        data = json.loads(raw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    payload = BatchPayload(**data)
    logger.info(f"收到 webhook 推送: batch={payload.batch_id} total={payload.total}")

    stored = 0
    skipped = 0
    # 用独立 session 写入，避免长事务
    with session_scope() as write_db:
        for acct in payload.accounts:
            try:
                # 注入 batch_id（如果账号没带）
                if not acct.batch_id:
                    acct.batch_id = payload.batch_id
                store_account(write_db, acct.model_dump())
                stored += 1
            except Exception as e:
                logger.exception(f"存储账号失败 {acct.email}: {e}")
                skipped += 1

    return BatchResponse(received=len(payload.accounts), stored=stored, skipped=skipped)
