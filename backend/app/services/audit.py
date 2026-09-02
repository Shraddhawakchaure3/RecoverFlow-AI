"""
RecoverFlow AI - Audit Logger
Records every action in the recovery workflow to the audit_logs collection.
"""
from datetime import datetime
from typing import Optional
from app.database.connection import get_db
from app.models.models import AuditLog
import structlog

log = structlog.get_logger()


async def log_event(
    event: str,
    payment_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    action_id: Optional[str] = None,
    ai_decision: Optional[dict] = None,
    policy_result: Optional[str] = None,
    action: Optional[str] = None,
    result: Optional[str] = None,
    amount_recovered: Optional[float] = None,
    metadata: Optional[dict] = None,
) -> str:
    """
    Persist an audit log entry and return the log_id.
    Safe to call even if DB is unavailable (logs warning, doesn't crash).
    """
    entry = AuditLog(
        timestamp=datetime.utcnow(),
        event=event,
        payment_id=payment_id,
        customer_id=customer_id,
        action_id=action_id,
        ai_decision=ai_decision,
        policy_result=policy_result,
        action=action,
        result=result,
        amount_recovered=amount_recovered,
        metadata=metadata or {},
    )

    log.info(
        "audit_event",
        audit_event=event,
        payment_id=payment_id,
        action=action,
        result=result,
        amount_recovered=amount_recovered,
    )

    try:
        db = get_db()
        await db.audit_logs.insert_one(entry.model_dump())
    except Exception as e:
        log.error("audit_log_write_failed", error=str(e), event=event)

    return entry.log_id
