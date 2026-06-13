"""统计 API：成功率、失败原因分布、时间序列。"""
from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account
from ..security import verify_basic_auth

router = APIRouter(prefix="/api/stats", tags=["stats"])


class StatsOut(BaseModel):
    total: int
    success: int
    failed: int
    success_rate: float
    last_24h_total: int
    last_24h_success: int
    failure_reasons: list[dict]
    daily_trend: list[dict]


@router.get("", response_model=StatsOut)
async def get_stats(
    _user: str = Depends(verify_basic_auth),
    db: Session = Depends(get_db),
) -> StatsOut:
    """返回汇总统计。"""
    total = db.query(func.count(Account.id)).scalar() or 0
    success = db.query(func.count(Account.id)).filter(Account.status == "success").scalar() or 0
    failed = total - success

    cutoff = datetime.utcnow() - timedelta(hours=24)
    last_24h_total = db.query(func.count(Account.id)).filter(Account.created_at >= cutoff).scalar() or 0
    last_24h_success = (
        db.query(func.count(Account.id))
        .filter(Account.created_at >= cutoff, Account.status == "success")
        .scalar() or 0
    )

    # 失败原因 top 10
    fail_rows = (
        db.query(Account.error_msg)
        .filter(Account.status == "failed", Account.error_msg.isnot(None))
        .all()
    )
    fail_counter = Counter()
    for (msg,) in fail_rows:
        if not msg:
            continue
        # 截取前 80 字符归并
        key = msg[:80] if len(msg) > 80 else msg
        fail_counter[key] += 1
    failure_reasons = [{"reason": k, "count": v} for k, v in fail_counter.most_common(10)]

    # 最近 14 天每日趋势
    daily_rows = (
        db.query(
            func.date(Account.created_at).label("d"),
            Account.status,
            func.count(Account.id),
        )
        .filter(Account.created_at >= datetime.utcnow() - timedelta(days=14))
        .group_by("d", Account.status)
        .all()
    )
    by_date: dict[str, dict[str, int]] = {}
    for d, status, cnt in daily_rows:
        d_str = str(d)
        by_date.setdefault(d_str, {"success": 0, "failed": 0})
        by_date[d_str][status] = cnt
    daily_trend = [
        {"date": d, "success": v["success"], "failed": v["failed"]}
        for d, v in sorted(by_date.items())
    ]

    return StatsOut(
        total=total,
        success=success,
        failed=failed,
        success_rate=(success / total) if total else 0.0,
        last_24h_total=last_24h_total,
        last_24h_success=last_24h_success,
        failure_reasons=failure_reasons,
        daily_trend=daily_trend,
    )
