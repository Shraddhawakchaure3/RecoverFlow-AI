"""
RecoverFlow AI - Dashboard API
Provides aggregated metrics for the command center.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter
from app.database.connection import get_db
import structlog

log = structlog.get_logger()
router = APIRouter()


@router.get("/dashboard/summary")
async def get_dashboard_summary():
    """Aggregate key revenue recovery metrics."""
    db = get_db()
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)

    # Total payments at risk (failed)
    pipeline_at_risk = [
        {"$match": {"status": "failed"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]
    at_risk_result = await db.payments.aggregate(pipeline_at_risk).to_list(1)
    at_risk = at_risk_result[0] if at_risk_result else {"total": 0, "count": 0}

    # Revenue recovered
    pipeline_recovered = [
        {"$match": {"status": "success"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount_recovered"}, "count": {"$sum": 1}}},
    ]
    recovered_result = await db.recovery_actions.aggregate(pipeline_recovered).to_list(1)
    recovered = recovered_result[0] if recovered_result else {"total": 0, "count": 0}

    # Expected recoverable: sum of amount_original × recovery_score for all non-blocked, non-stopped actions
    pipeline_expected = [
        {"$match": {"status": {"$in": ["success", "failed", "approved", "pending", "executing"]}}},
        {"$group": {
            "_id": None,
            "total": {"$sum": {"$multiply": ["$amount_original", "$recovery_probability"]}},
        }},
    ]
    expected_result = await db.recovery_actions.aggregate(pipeline_expected).to_list(1)
    expected = expected_result[0] if expected_result else {"total": 0}

    # Active recovery actions
    active_count = await db.recovery_actions.count_documents({
        "status": {"$in": ["approved", "executing", "pending"]}
    })

    # Policy blocked
    blocked_count = await db.recovery_actions.count_documents({"status": "blocked"})

    # Stopped
    stopped_count = await db.recovery_actions.count_documents({"status": "stopped"})

    # Checkout abandonment count
    abandoned_count = await db.checkout_sessions.count_documents({"status": "abandoned"})

    # Recovery rate
    total_attempts = await db.recovery_actions.count_documents({
        "status": {"$in": ["success", "failed", "stopped", "blocked"]}
    })
    successful_recoveries = recovered["count"]
    recovery_rate = (successful_recoveries / total_attempts) if total_attempts > 0 else 0

    # Revenue trend (last 30 days, daily buckets)
    trend_pipeline = [
        {"$match": {"status": "failed", "created_at": {"$gte": thirty_days_ago}}},
        {"$group": {
            "_id": {
                "year": {"$year": "$created_at"},
                "month": {"$month": "$created_at"},
                "day": {"$dayOfMonth": "$created_at"},
            },
            "at_risk": {"$sum": "$amount"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}},
    ]
    trend_raw = await db.payments.aggregate(trend_pipeline).to_list(30)
    trend = [
        {
            "date": f"{r['_id']['year']}-{r['_id']['month']:02d}-{r['_id']['day']:02d}",
            "at_risk": r["at_risk"] / 100,
            "count": r["count"],
        }
        for r in trend_raw
    ]

    # Failure type breakdown
    failure_breakdown_pipeline = [
        {"$match": {"status": "failed"}},
        {"$group": {"_id": "$failure_type", "count": {"$sum": 1}, "amount": {"$sum": "$amount"}}},
    ]
    failure_breakdown = await db.payments.aggregate(failure_breakdown_pipeline).to_list(10)

    return {
        "revenue_at_risk_paise": at_risk["total"],
        "revenue_at_risk_inr": at_risk["total"] / 100,
        "payments_at_risk": at_risk["count"],
        "revenue_recovered_paise": recovered["total"] or 0,
        "revenue_recovered_inr": (recovered["total"] or 0) / 100,
        "successful_recoveries": successful_recoveries,
        "expected_recoverable_inr": expected["total"] / 100,
        "active_recovery_actions": active_count,
        "policy_blocked_actions": blocked_count,
        "stopped_actions": stopped_count,
        "checkout_abandonments": abandoned_count,
        "recovery_rate": round(recovery_rate, 4),
        "revenue_trend": trend,
        "failure_type_breakdown": [
            {
                "type": r["_id"] or "UNKNOWN",
                "count": r["count"],
                "amount_inr": r["amount"] / 100,
            }
            for r in failure_breakdown
        ],
    }
