"""导出 API：JSON / Netscape / CSV 三格式。"""
import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account
from ..security import verify_basic_auth

router = APIRouter(prefix="/api/export", tags=["export"])


def _to_netscape(cookies_json: str) -> str:
    cookies = json.loads(cookies_json) if cookies_json else []
    lines = ["# Netscape HTTP Cookie File", ""]
    for c in cookies:
        domain = c.get("domain", "")
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure") else "FALSE"
        expires = str(int(c.get("expires", 0)) or (int(datetime.utcnow().timestamp()) + 86400 * 30))
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append("\t".join([domain, flag, path, secure, expires, name, value]))
    return "\n".join(lines)


@router.get("/accounts.json")
async def export_all_json(
    status_filter: str | None = Query(None, alias="status"),
    _user: str = Depends(verify_basic_auth),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """导出全部账号为 JSON 文件。"""
    q = db.query(Account)
    if status_filter:
        q = q.filter(Account.status == status_filter)
    items = q.order_by(Account.created_at.desc()).all()
    data = []
    for a in items:
        d = {
            "email": a.email,
            "username": a.username,
            "password": a.password,
            "session_id": a.session_id,
            "ms_token": a.ms_token,
            "tt_target_idc": a.tt_target_idc,
            "cookies": json.loads(a.cookies_json) if a.cookies_json else [],
            "user_agent": a.user_agent,
            "proxy_used": a.proxy_used,
            "registered_at": a.registered_at.isoformat() if a.registered_at else None,
        }
        data.append(d)
    content = json.dumps(data, ensure_ascii=False, indent=2)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=tiktok-accounts-{datetime.utcnow().strftime('%Y%m%d')}.json"},
    )


@router.get("/accounts.csv")
async def export_all_csv(
    status_filter: str | None = Query(None, alias="status"),
    _user: str = Depends(verify_basic_auth),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """导出全部账号为 CSV（适合导入表格工具）。"""
    q = db.query(Account)
    if status_filter:
        q = q.filter(Account.status == status_filter)
    items = q.order_by(Account.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "email", "password", "username", "session_id", "ms_token",
        "tt_target_idc", "status", "user_agent", "proxy_used",
        "registered_at", "error_msg",
    ])
    for a in items:
        writer.writerow([
            a.email, a.password, a.username or "", a.session_id or "",
            a.ms_token or "", a.tt_target_idc or "", a.status,
            a.user_agent or "", a.proxy_used or "",
            a.registered_at.isoformat() if a.registered_at else "",
            a.error_msg or "",
        ])

    content = output.getvalue().encode("utf-8-sig")  # BOM 帮 Excel 识别 UTF-8
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tiktok-accounts-{datetime.utcnow().strftime('%Y%m%d')}.csv"},
    )


@router.get("/accounts/{account_id}/cookies.txt")
async def export_account_cookies(
    account_id: int,
    _user: str = Depends(verify_basic_auth),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """导出单个账号的 Netscape cookies.txt（可导入 yt-dlp / 指纹浏览器）。"""
    acct = db.get(Account, account_id)
    if not acct:
        raise HTTPException(404, "Account not found")
    content = _to_netscape(acct.cookies_json or "[]")
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=cookies-{acct.email}.txt"},
    )


@router.get("/accounts/{account_id}/info.json")
async def export_account_json(
    account_id: int,
    _user: str = Depends(verify_basic_auth),
    db: Session = Depends(get_db),
) -> dict:
    """导出单个账号的完整 JSON。"""
    acct = db.get(Account, account_id)
    if not acct:
        raise HTTPException(404, "Account not found")
    return {
        "id": acct.id,
        "email": acct.email,
        "username": acct.username,
        "password": acct.password,
        "session_id": acct.session_id,
        "ms_token": acct.ms_token,
        "tt_target_idc": acct.tt_target_idc,
        "cookies": json.loads(acct.cookies_json) if acct.cookies_json else [],
        "user_agent": acct.user_agent,
        "proxy_used": acct.proxy_used,
        "registered_at": acct.registered_at.isoformat() if acct.registered_at else None,
    }
