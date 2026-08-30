"""
RecoverFlow AI - Audit Trail API
"""
from typing import Optional
from fastapi import APIRouter, Query
from app.database.connection import get_db
import structlog

log = structlog.get_logger()
router = APIRouter()


@router.get("/audit")
async def get_audit_log(
    payment_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    skip: int = Query(0),
):
    """Fetch audit log entries, optionally filtered by payment_id."""
    db = get_db()
    query = {}
    if payment_id:
        query["payment_id"] = payment_id

    entries = await db.audit_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)
    for e in entries:
        e.pop("_id", None)

    total = await db.audit_logs.count_documents(query)

    return {
        "entries": entries,
        "total": total,
        "skip": skip,
        "limit": limit,
    }
