"""三合一存储：SQLite + JSON 文件 + Netscape cookies.txt。"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from .config import get_settings
from .models import Account


def _netscape_time() -> str:
    """生成 Netscape 格式时间戳。"""
    return str(int(datetime.utcnow().timestamp()))


def _write_netscape_cookies(cookies_json: str, file_path: Path) -> None:
    """将 Playwright cookies JSON 写为 Netscape 格式 .txt。"""
    cookies = json.loads(cookies_json) if cookies_json else []
    lines = ["# Netscape HTTP Cookie File", "# https://curl.se/docs/http-cookies.html", ""]
    for c in cookies:
        domain = c.get("domain", "")
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure") else "FALSE"
        expires = str(int(c.get("expires", 0)))
        if expires == "0" or expires == "-1":
            expires = str(int(datetime.utcnow().timestamp()) + 86400 * 30)  # 30天
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append("\t".join([domain, flag, path, secure, expires, name, value]))
    file_path.write_text("\n".join(lines), encoding="utf-8")


def store_account(db: Session, payload: dict[str, Any]) -> Account:
    """三合一存储一个账号。"""
    settings = get_settings()
    email = payload["email"]
    cookies_json = payload.get("cookies_json") or "[]"

    # 1. SQLite upsert
    account = db.query(Account).filter_by(email=email).first()
    if account is None:
        account = Account(email=email)
        db.add(account)

    account.password = payload.get("password", "")
    account.username = payload.get("username")
    account.birth_date = payload.get("birth_date")
    account.session_id = payload.get("session_id")
    account.tt_target_idc = payload.get("tt_target_idc")
    account.ms_token = payload.get("ms_token")
    account.cookies_json = cookies_json
    account.important_cookies = json.dumps(payload.get("important_cookies") or {}, ensure_ascii=False)
    account.user_agent = payload.get("user_agent")
    account.proxy_used = payload.get("proxy_used")
    account.fingerprint_hash = payload.get("fingerprint_hash")
    account.timezone = payload.get("timezone")
    account.locale = payload.get("locale")
    account.viewport = json.dumps(payload.get("viewport")) if payload.get("viewport") else None
    account.status = payload.get("status", "failed")
    account.error_msg = payload.get("error_msg")
    account.batch_id = payload.get("batch_id")
    if payload.get("registered_at"):
        try:
            account.registered_at = datetime.fromisoformat(
                payload["registered_at"].replace("Z", "+00:00")
            )
        except Exception:
            account.registered_at = datetime.utcnow()

    db.flush()  # 拿到 id

    # 2. JSON 文件（仅成功账号）
    if account.status == "success":
        account_dir = settings.data_dir / "accounts" / email
        account_dir.mkdir(parents=True, exist_ok=True)
        info = {
            "id": account.id,
            "email": email,
            "username": account.username,
            "password": account.password,
            "session_id": account.session_id,
            "tt_target_idc": account.tt_target_idc,
            "ms_token": account.ms_token,
            "important_cookies": payload.get("important_cookies") or {},
            "user_agent": account.user_agent,
            "proxy_used": account.proxy_used,
            "fingerprint_hash": account.fingerprint_hash,
            "timezone": account.timezone,
            "locale": account.locale,
            "viewport": payload.get("viewport"),
            "registered_at": payload.get("registered_at"),
        }
        (account_dir / "info.json").write_text(
            json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 3. Netscape cookies.txt
        _write_netscape_cookies(cookies_json, account_dir / "cookies.txt")

    return account
