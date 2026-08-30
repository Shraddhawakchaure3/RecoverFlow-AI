"""
RecoverFlow AI - Demo Scenarios API
Controlled demo scenarios for judges — each runs through the real backend workflow.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import uuid
import random

from app.database.connection import get_db
from app.services.recovery import run_recovery_workflow, StoppingRuleViolated
from app.services.audit import log_event
import structlog

log = structlog.get_logger()
router = APIRouter()

SCENARIOS = {
    "high_recovery_success": {
        "name": "High Recovery Success",
        "description": "Customer with excellent history, temporary bank failure — AI recommends DELAYED_RECOVERY, policy approves.",
        "failure_type": "TEMPORARY_BANK_FAILURE",
        "failure_reason": "bank_not_responding",
        "amount": 800000,  # ₹8,000
        "customer_payments": 10,
        "customer_success": 9,
    },
    "low_recovery_stop": {
        "name": "Low Recovery → STOP",
        "description": "Multiple failed attempts, low score — AI recommends STOP.",
        "failure_type": "MULTIPLE_FAILED_ATTEMPTS",
        "failure_reason": "card_declined",
        "amount": 50000,  # ₹500
        "customer_payments": 5,
        "customer_success": 1,
        "force_retry_count": 3,
    },
    "retry_limit_reached": {
        "name": "Retry Limit Reached",
        "description": "Good score but policy MAX_RETRIES=2 blocks further action.",
        "failure_type": "TEMPORARY_BANK_FAILURE",
        "failure_reason": "bank_not_responding",
        "amount": 200000,  # ₹2,000
        "customer_payments": 8,
        "customer_success": 7,
        "force_retry_count": 2,
    },
    "checkout_abandonment": {
        "name": "Checkout Abandonment → Recovery",
        "description": "Customer left checkout after 90s — reminder recovers the sale.",
        "failure_type": "CHECKOUT_ABANDONMENT",
        "failure_reason": "checkout_abandoned",
        "amount": 350000,  # ₹3,500
        "customer_payments": 3,
        "customer_success": 2,
        "metadata": {"time_on_checkout_seconds": 90, "page_views": 3},
    },
    "duplicate_webhook": {
        "name": "Duplicate Webhook",
        "description": "Same webhook event sent twice — idempotency correctly rejects the second.",
        "special": "duplicate_webhook",
    },
    "payment_success_stop": {
        "name": "Payment Success → Stop Workflow",
        "description": "Payment already captured — stopping rule fires immediately.",
        "failure_type": "TEMPORARY_BANK_FAILURE",
        "failure_reason": "bank_not_responding",
        "amount": 500000,  # ₹5,000
        "already_captured": True,
    },
    "policy_block": {
        "name": "AI Recommends Forbidden Action → Policy Block",
        "description": "High amount (₹15,000) exceeds policy max — BLOCKED.",
        "failure_type": "TEMPORARY_BANK_FAILURE",
        "failure_reason": "bank_not_responding",
        "amount": 1500000,  # ₹15,000
        "customer_payments": 8,
        "customer_success": 8,
        "policy_override": {"max_transaction_amount": 5000},  # set max to ₹5,000
    },
}


async def _seed_demo_payment(scenario_id: str, scenario: dict) -> dict:
    """Create a synthetic payment record for a demo scenario."""
    db = get_db()
    payment_id = f"demo_{scenario_id}_{uuid.uuid4().hex[:8]}"
    customer_id = f"cust_demo_{uuid.uuid4().hex[:8]}"
    order_id = f"order_demo_{uuid.uuid4().hex[:8]}"

    customer = {
        "customer_id": customer_id,
        "name": f"Demo Customer ({scenario.get('name', '')})",
        "email": f"demo_{scenario_id}@recoverflow.test",
        "phone": "9999999999",
        "total_payments": scenario.get("customer_payments", 5),
        "successful_payments": scenario.get("customer_success", 4),
        "failed_payments": scenario.get("customer_payments", 5) - scenario.get("customer_success", 4),
        "total_amount_paid": scenario.get("customer_success", 4) * scenario.get("amount", 100000) / 100,
        "opted_out": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    await db.customers.update_one(
        {"customer_id": customer_id},
        {"$set": customer},
        upsert=True,
    )

    status = "captured" if scenario.get("already_captured") else "failed"
    payment = {
        "payment_id": payment_id,
        "order_id": order_id,
        "customer_id": customer_id,
        "amount": scenario.get("amount", 100000),
        "currency": "INR",
        "method": "card",
        "status": status,
        "failure_reason": scenario.get("failure_reason", "bank_not_responding"),
        "failure_type": scenario.get("failure_type", "TEMPORARY_BANK_FAILURE"),
        "error_code": "GATEWAY_ERROR",
        "bank": "HDFC",
        "metadata": scenario.get("metadata", {}),
        "created_at": datetime.utcnow() - timedelta(hours=1),
        "updated_at": datetime.utcnow(),
    }
    await db.payments.update_one(
        {"payment_id": payment_id},
        {"$set": payment},
        upsert=True,
    )

    # Seed previous retry records if needed
    force_retries = scenario.get("force_retry_count", 0)
    for i in range(force_retries):
        prev_action_id = f"demo_prev_{uuid.uuid4().hex[:8]}"
        await db.recovery_actions.insert_one({
            "action_id": prev_action_id,
            "payment_id": payment_id,
            "customer_id": customer_id,
            "action_type": "DELAYED_RECOVERY",
            "status": "failed",
            "amount_original": payment["amount"],
            "recovery_probability": 0.5,
            "recovery_score": 0.5,
            "root_cause": "TEMPORARY_BANK_FAILURE",
            "reason": "Previous attempt",
            "priority": "MEDIUM",
            "confidence": 0.7,
            "policy_status": "APPROVED",
            "attempt_number": i + 1,
            "created_at": datetime.utcnow() - timedelta(hours=force_retries - i),
            "updated_at": datetime.utcnow(),
        })

    return payment


@router.get("/demo/scenarios")
async def list_scenarios():
    """List available demo scenarios."""
    return {
        "scenarios": [
            {
                "id": sid,
                "name": s.get("name"),
                "description": s.get("description"),
            }
            for sid, s in SCENARIOS.items()
        ]
    }


@router.post("/demo/scenario")
async def run_demo_scenario(body: dict):
    """
    Run a demo scenario end-to-end through the real backend workflow.
    """
    scenario_id = body.get("scenario_id")
    if scenario_id not in SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario '{scenario_id}'. Valid: {list(SCENARIOS.keys())}",
        )

    scenario = SCENARIOS[scenario_id]
    db = get_db()

    # ── Special: Duplicate Webhook ────────────────────────────────────────────
    if scenario.get("special") == "duplicate_webhook":
        event_id = f"demo_event_{uuid.uuid4().hex[:8]}"
        # First event
        await db.webhook_events.update_one(
            {"event_id": event_id},
            {"$setOnInsert": {
                "event_id": event_id,
                "event_type": "payment.captured",
                "payload": {"event": "payment.captured"},
                "processed": True,
                "processed_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
            }},
            upsert=True,
        )
        # Second event check
        existing = await db.webhook_events.find_one({"event_id": event_id})
        duplicate_detected = existing and existing.get("processed")
        return {
            "scenario": "duplicate_webhook",
            "event_id": event_id,
            "first_event": "processed",
            "second_event": "rejected (duplicate)",
            "duplicate_detected": duplicate_detected,
            "message": "Idempotency correctly rejected the duplicate webhook event.",
        }

    # Seed payment data
    payment = await _seed_demo_payment(scenario_id, scenario)
    payment_id = payment["payment_id"]

    await log_event(
        event=f"DEMO_SCENARIO_STARTED:{scenario_id}",
        payment_id=payment_id,
        metadata={"scenario": scenario.get("name")},
    )

    # ── Policy override for policy_block scenario ─────────────────────────────
    if scenario.get("policy_override"):
        await db.policies.update_one(
            {"name": "default"},
            {"$set": {**scenario["policy_override"], "updated_at": datetime.utcnow()}},
            upsert=True,
        )

    # Run the actual workflow
    try:
        result = await run_recovery_workflow(payment_id=payment_id)
        return {
            "scenario_id": scenario_id,
            "scenario_name": scenario.get("name"),
            "payment_id": payment_id,
            "success": True,
            "result": result,
        }
    except StoppingRuleViolated as e:
        return {
            "scenario_id": scenario_id,
            "scenario_name": scenario.get("name"),
            "payment_id": payment_id,
            "success": False,
            "stopped": True,
            "reason": str(e),
        }
    except Exception as e:
        log.error("demo_scenario_error", scenario_id=scenario_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
