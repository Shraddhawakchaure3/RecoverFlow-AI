"""
RecoverFlow AI - Razorpay Webhook Handler
Processes incoming webhook events with signature verification,
idempotency protection, and async processing.
"""
import hashlib
import hmac
import json
from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.database.connection import get_db
from app.services.recovery import confirm_recovery_success
from app.services.audit import log_event

log = structlog.get_logger()
router = APIRouter()


def _verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify Razorpay webhook signature using HMAC-SHA256."""
    if not secret:
        log.warning("webhook_secret_not_configured")
        return True  # allow in dev mode without secret

    expected = hmac.new(
        key=secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _process_webhook_event(event_type: str, payload: dict):
    """
    Background task: Process a verified webhook event.
    Handles payment.failed, payment.captured, order.paid.
    """
    db = get_db()

    try:
        if event_type == "payment.captured":
            payment_entity = payload.get("payment", {}).get("entity", {})
            razorpay_payment_id = payment_entity.get("id")
            order_id = payment_entity.get("order_id")
            amount = payment_entity.get("amount", 0)

            # Find payment in our DB by order_id or razorpay_payment_id
            payment = await db.payments.find_one({
                "$or": [
                    {"razorpay_payment_id": razorpay_payment_id},
                    {"order_id": order_id},
                ]
            })

            if payment:
                payment_id = payment.get("payment_id")
                await confirm_recovery_success(payment_id, amount)
                log.info("webhook_payment_captured_processed", payment_id=payment_id)
            else:
                # Check if this is a recovery order
                order = await db.orders.find_one({"razorpay_order_id": order_id})
                if order:
                    recovery_action = await db.recovery_actions.find_one(
                        {"razorpay_order_id": order_id}
                    )
                    if recovery_action:
                        original_payment_id = recovery_action.get("payment_id")
                        await confirm_recovery_success(original_payment_id, amount)
                        log.info(
                            "recovery_order_payment_captured",
                            order_id=order_id,
                            original_payment_id=original_payment_id,
                        )

        elif event_type == "payment.failed":
            payment_entity = payload.get("payment", {}).get("entity", {})
            razorpay_payment_id = payment_entity.get("id")
            order_id = payment_entity.get("order_id")
            failure_reason = payment_entity.get("error_description", "unknown")
            error_code = payment_entity.get("error_code", "")

            # Check if this belongs to a recovery action
            recovery_action = await db.recovery_actions.find_one(
                {"razorpay_order_id": order_id}
            )
            if recovery_action:
                action_id = recovery_action.get("action_id")
                payment_id = recovery_action.get("payment_id")
                await db.recovery_actions.update_one(
                    {"action_id": action_id},
                    {"$set": {
                        "status": "failed",
                        "updated_at": datetime.utcnow(),
                    }}
                )
                await log_event(
                    event="RECOVERY_PAYMENT_FAILED",
                    payment_id=payment_id,
                    action_id=action_id,
                    result=failure_reason,
                    metadata={"error_code": error_code},
                )
                log.info("recovery_action_failed", action_id=action_id, reason=failure_reason)

        elif event_type == "order.paid":
            order_entity = payload.get("order", {}).get("entity", {})
            order_id = order_entity.get("id")
            amount_paid = order_entity.get("amount_paid", 0)

            recovery_action = await db.recovery_actions.find_one(
                {"razorpay_order_id": order_id}
            )
            if recovery_action:
                payment_id = recovery_action.get("payment_id")
                await confirm_recovery_success(payment_id, amount_paid)

        else:
            log.info("webhook_event_ignored", event_type=event_type)

    except Exception as e:
        log.error("webhook_processing_error", event_type=event_type, error=str(e))


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Razorpay webhook endpoint.
    - Verifies signature on raw body
    - Checks idempotency (deduplicates by event ID)
    - Responds immediately with 200
    - Processes event asynchronously in background
    """
    # Read raw body for signature verification
    raw_body = await request.body()

    signature = request.headers.get("X-Razorpay-Signature", "")
    event_id = request.headers.get("X-Razorpay-Event-Id", "")

    # Signature verification
    if not _verify_signature(raw_body, signature, settings.razorpay_webhook_secret):
        log.warning("webhook_invalid_signature", event_id=event_id)
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload: dict[str, Any] = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event", "")

    # Idempotency: check if we've already processed this event
    db = get_db()
    if event_id:
        existing = await db.webhook_events.find_one({"event_id": event_id})
        if existing and existing.get("processed"):
            log.info("webhook_duplicate_ignored", event_id=event_id, event_type=event_type)
            return JSONResponse({"status": "duplicate", "event_id": event_id})

        # Claim the event before scheduling work so concurrent duplicates cannot
        # both start recovery processing.
        try:
            insert_result = await db.webhook_events.update_one(
                {"event_id": event_id},
                {"$setOnInsert": {
                    "event_id": event_id,
                    "event_type": event_type,
                    "payload": payload,
                    "processed": False,
                    "created_at": datetime.utcnow(),
                }},
                upsert=True,
            )
            if not insert_result.upserted_id:
                log.info("webhook_duplicate_ignored", event_id=event_id, event_type=event_type)
                return JSONResponse({"status": "duplicate", "event_id": event_id})
        except DuplicateKeyError:
            log.info("webhook_duplicate_ignored", event_id=event_id, event_type=event_type)
            return JSONResponse({"status": "duplicate", "event_id": event_id})

    # Respond immediately (Razorpay expects fast response)
    background_tasks.add_task(_process_webhook_event_and_mark, event_id, event_type, payload, db)

    log.info("webhook_received", event_type=event_type, event_id=event_id)
    return JSONResponse({"status": "received"})


async def _process_webhook_event_and_mark(event_id: str, event_type: str, payload: dict, db):
    """Process event and mark as processed after completion."""
    await _process_webhook_event(event_type, payload)
    if event_id:
        try:
            await db.webhook_events.update_one(
                {"event_id": event_id},
                {"$set": {"processed": True, "processed_at": datetime.utcnow()}}
            )
        except Exception:
            pass
