"""
RecoverFlow AI - Opportunities API
Lists revenue recovery opportunities and individual analysis.
"""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from app.database.connection import get_db
from app.services.scoring import compute_recovery_score, get_priority, get_expected_recovery
from app.services.root_cause import analyze_failure
import structlog

log = structlog.get_logger()
router = APIRouter()


@router.get("/opportunities")
async def list_opportunities(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0),
):
    """
    List all revenue recovery opportunities (failed payments + abandoned checkouts).
    Enriches each with scoring and root cause data.
    """
    db = get_db()

    # Build query for failed payments
    query = {"status": "failed"}
    if status:
        # Filter by recovery action status
        pass  # handled via join below

    payments = await db.payments.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    opportunities = []
    for payment in payments:
        payment.pop("_id", None)
        payment_id = payment.get("payment_id")

        # Get customer
        customer = await db.customers.find_one({"customer_id": payment.get("customer_id")}) or {}
        customer.pop("_id", None)

        # Get latest recovery action
        latest_action = await db.recovery_actions.find_one(
            {"payment_id": payment_id},
            sort=[("created_at", -1)],
        )
        if latest_action:
            latest_action.pop("_id", None)

        # Compute score
        retry_attempts = await db.recovery_actions.count_documents({"payment_id": payment_id})
        score_result = compute_recovery_score(payment, customer, retry_attempts)
        failure_type, failure_label, failure_explanation = analyze_failure(
            failure_reason=payment.get("failure_reason", ""),
            retry_attempts=retry_attempts,
            error_code=payment.get("error_code", ""),
        )

        opportunity = {
            "payment_id": payment_id,
            "order_id": payment.get("order_id"),
            "customer_id": payment.get("customer_id"),
            "customer_name": customer.get("name", "Unknown"),
            "customer_email": customer.get("email", ""),
            "amount_paise": payment.get("amount", 0),
            "amount_inr": payment.get("amount", 0) / 100,
            "currency": payment.get("currency", "INR"),
            "method": payment.get("method"),
            "failure_reason": payment.get("failure_reason"),
            "failure_type": failure_type.value,
            "failure_label": failure_label,
            "failure_explanation": failure_explanation,
            "recovery_score": score_result.score,
            "recovery_probability": score_result.probability,
            "expected_recovery_inr": get_expected_recovery(payment.get("amount", 0), score_result.probability) / 100,
            "priority": get_priority(score_result.score),
            "score_breakdown": score_result.to_dict(),
            "retry_attempts": retry_attempts,
            "latest_action": latest_action,
            "action_status": latest_action.get("status") if latest_action else "unactioned",
            "created_at": payment.get("created_at"),
        }
        opportunities.append(opportunity)

    # Apply priority filter
    if priority:
        opportunities = [o for o in opportunities if o["priority"] == priority.upper()]

    # Sort by recovery score desc
    opportunities.sort(key=lambda x: x["recovery_score"], reverse=True)

    total = await db.payments.count_documents({"status": "failed"})

    return {
        "opportunities": opportunities,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/opportunities/{payment_id}")
async def get_opportunity(payment_id: str):
    """Get detailed analysis for a specific payment opportunity."""
    db = get_db()

    payment = await db.payments.find_one({"payment_id": payment_id})
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    payment.pop("_id", None)

    customer = await db.customers.find_one({"customer_id": payment.get("customer_id")}) or {}
    customer.pop("_id", None)

    # All recovery actions for this payment
    actions_cursor = db.recovery_actions.find(
        {"payment_id": payment_id},
        sort=[("created_at", -1)],
    )
    actions = await actions_cursor.to_list(20)
    for a in actions:
        a.pop("_id", None)

    retry_attempts = len(actions)
    score_result = compute_recovery_score(payment, customer, retry_attempts)
    failure_type, failure_label, failure_explanation = analyze_failure(
        failure_reason=payment.get("failure_reason", ""),
        retry_attempts=retry_attempts,
        error_code=payment.get("error_code", ""),
    )

    # Audit trail for this payment
    audit_entries = await db.audit_logs.find(
        {"payment_id": payment_id},
        sort=[("timestamp", 1)],
    ).to_list(50)
    for a in audit_entries:
        a.pop("_id", None)

    return {
        "payment": payment,
        "customer": customer,
        "recovery_score": score_result.score,
        "recovery_probability": score_result.probability,
        "expected_recovery_inr": get_expected_recovery(payment.get("amount", 0), score_result.probability) / 100,
        "priority": get_priority(score_result.score),
        "score_breakdown": score_result.to_dict(),
        "failure_type": failure_type.value,
        "failure_label": failure_label,
        "failure_explanation": failure_explanation,
        "retry_attempts": retry_attempts,
        "recovery_actions": actions,
        "audit_trail": audit_entries,
    }
