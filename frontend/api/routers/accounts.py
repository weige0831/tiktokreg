"""账号 CRUD API。"""
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account
from ..security import verify_basic_auth

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AccountOut(BaseModel):
    id: int
    email: str
    username: str | None
    birth_date: str | None
    session_id: str | None
    tt_target_idc: str | None
    ms_token: str | None
    user_agent: str | None
    proxy_used: str | None
    fingerprint_hash: str | None
    timezone: str | None
    locale: str | None
    viewport: Any | None
    status: str
    error_msg: str | None
    batch_id: str | None
    registered_at: datetime | None
    created_at: datetime | None
    last_checked_at: datetime | None

    class Config:
        from_attributes = True


class AccountDetail(AccountOut):
    cookies_json: str | None
    important_cookies: Any | None
    password: str


class PaginatedAccounts(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[AccountOut]


@router.get("", response_model=PaginatedAccounts)
async def list_accounts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = None,
    _user: str = Depends(verify_basic_auth),
    db: Session = Depends(get_db),
) -> PaginatedAccounts:
    """列出账号（分页 + 筛选 + 搜索）。"""
    q = db.query(Account)
    if status_filter:
        q = q.filter(Account.status == status_filter)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (Account.email.like(like)) | (Account.username.like(like))
        )
    total = q.count()
    items = (
        q.order_by(desc(Account.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return PaginatedAccounts(
        total=total,
        page=page,
        per_page=per_page,
        items=[AccountOut.model_validate(i) for i in items],
    )


@router.get("/{account_id}", response_model=AccountDetail)
async def get_account(
    account_id: int,
    _user: str = Depends(verify_basic_auth),
    db: Session = Depends(get_db),
) -> AccountDetail:
    """获取账号详情。"""
    acct = db.get(Account, account_id)
    if not acct:
        raise HTTPException(404, "Account not found")
    # important_cookies JSON 解码
    data = AccountDetail.model_validate(acct)
    if acct.important_cookies:
        try:
            data.important_cookies = json.loads(acct.important_cookies)
        except Exception:
            data.important_cookies = {}
    if acct.viewport:
        try:
            data.viewport = json.loads(acct.viewport)
        except Exception:
            data.viewport = None
    return data


@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    _user: str = Depends(verify_basic_auth),
    db: Session = Depends(get_db),
) -> dict:
    """删除账号。"""
    acct = db.get(Account, account_id)
    if not acct:
        raise HTTPException(404, "Account not found")
    email = acct.email
    db.delete(acct)
    db.commit()
    # 同时删除文件
    from ..config import get_settings
    import shutil

    acct_dir = get_settings().data_dir / "accounts" / email
    if acct_dir.exists():
        shutil.rmtree(acct_dir, ignore_errors=True)
    return {"deleted": account_id}


@router.post("/{account_id}/check")
async def mark_checked(
    account_id: int,
    _user: str = Depends(verify_basic_auth),
    db: Session = Depends(get_db),
) -> dict:
    """更新最后检查时间。"""
    acct = db.get(Account, account_id)
    if not acct:
        raise HTTPException(404, "Account not found")
    acct.last_checked_at = datetime.utcnow()
    db.commit()
    return {"id": account_id, "last_checked_at": acct.last_checked_at.isoformat()}
