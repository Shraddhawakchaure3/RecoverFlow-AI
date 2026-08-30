"""
RecoverFlow AI - Core Recovery Workflow
Orchestrates the full DETECT → DIAGNOSE → SCORE → DECIDE → POLICY → EXECUTE → AUDIT loop.
"""
from datetime import datetime
from typing import Optional
import structlog

from app.database.connection import get_db
from app.models.models import (
    RecoveryAction, RecoveryActionStatus, PolicyStatus,
    RecoveryActionType, FailureType
)
from app.services.scoring import compute_recovery_score, get_priority, get_expected_recovery
from app.services.root_cause import analyze_failure
from app.services.payment_provider import get_payment_provider
from app.policies.engine import check_policy, get_active_policy
from app.agents.decision import make_recovery_decision
from app.services.audit import log_event

log = structlog.get_logger()


class StoppingRuleViolated(Exception):
    """Raised when a stopping rule prevents further recovery."""
    pass


async def _get_retry_count(payment_id: str) -> int:
    """Count previous recovery actions for this payment."""
    db = get_db()
    count = await db.recovery_actions.count_documents({
        "payment_id": payment_id,
        "status": {"$in": ["success", "failed", "stopped", "executing"]},
    })
    return count


async def check_stopping_rules(payment: dict, customer: dict) -> Optional[str]:
    """
    Check all stopping rules before starting recovery.
    Returns a stop reason string if recovery should stop, None if OK to proceed.
    """
    # Rule 1: Payment already successful
    if payment.get("status") == "captured":
        return "Payment already captured/successful"

    # Rule 2: Customer opted out
    if customer.get("opted_out", False):
        return "Customer opted out of recovery communications"

    # Rule 3: Duplicate successful recovery exists
    db = get_db()
    existing_success = await db.recovery_actions.find_one({
        "payment_id": payment.get("payment_id"),
        "status": "success",
    })
    if existing_success:
        return "Duplicate: successful recovery already exists for this payment"

    return None


async def run_recovery_workflow(
    payment_id: str,
    force: bool = False,
) -> dict:
    """
    Execute the full recovery workflow for a given payment.

    Returns a summary dict with the outcome.
    Raises StoppingRuleViolated if recovery must stop.
    """
    db = get_db()

    # ── 1. DETECT: Fetch payment and customer ────────────────────────────────
    payment = await db.payments.find_one({"payment_id": payment_id})
    if not payment:
        raise ValueError(f"Payment {payment_id} not found")
    payment.pop("_id", None)

    customer = await db.customers.find_one({"customer_id": payment.get("customer_id")})
    if not customer:
        customer = {"customer_id": payment.get("customer_id"), "total_payments": 0,
                    "successful_payments": 0, "opted_out": False}
    customer.pop("_id", None)

    retry_attempts = await _get_retry_count(payment_id)

    await log_event(
        event="RECOVERY_WORKFLOW_STARTED",
        payment_id=payment_id,
        customer_id=customer.get("customer_id"),
        metadata={"retry_attempts": retry_attempts},
    )

    # ── 2. STOPPING RULES ────────────────────────────────────────────────────
    if not force:
        stop_reason = await check_stopping_rules(payment, customer)
        if stop_reason:
            await log_event(
                event="RECOVERY_STOPPED",
                payment_id=payment_id,
                result=stop_reason,
            )
            raise StoppingRuleViolated(stop_reason)

    # ── 3. DIAGNOSE: Root cause analysis ─────────────────────────────────────
    failure_type, failure_label, failure_explanation = analyze_failure(
        failure_reason=payment.get("failure_reason", ""),
        retry_attempts=retry_attempts,
        error_code=payment.get("error_code", ""),
    )

    await log_event(
        event="ROOT_CAUSE_ANALYZED",
        payment_id=payment_id,
        metadata={"failure_type": failure_type.value, "label": failure_label},
    )

    # ── 4. SCORE: Recovery scoring ────────────────────────────────────────────
    score_result = compute_recovery_score(
        payment=payment,
        customer=customer,
        retry_attempts=retry_attempts,
    )

    await log_event(
        event="RECOVERY_SCORE_COMPUTED",
        payment_id=payment_id,
        metadata=score_result.to_dict(),
    )

    # ── 5. AI DECISION ────────────────────────────────────────────────────────
    ai_decision, used_ai = await make_recovery_decision(
        payment=payment,
        customer=customer,
        recovery_score=score_result.score,
        failure_type=failure_type.value,
        failure_explanation=failure_explanation,
        retry_attempts=retry_attempts,
    )

    await log_event(
        event="AI_DECISION_GENERATED",
        payment_id=payment_id,
        ai_decision=ai_decision.to_dict(),
        metadata={"used_ai": used_ai},
    )

    # ── 6. POLICY CHECK ───────────────────────────────────────────────────────
    policy = await get_active_policy()
    policy_decision = await check_policy(
        payment=payment,
        customer=customer,
        recovery_score=score_result.score,
        recommended_action=ai_decision.recommended_action,
        retry_attempts=retry_attempts,
        policy=policy,
    )

    await log_event(
        event="POLICY_CHECKED",
        payment_id=payment_id,
        policy_result=policy_decision.status.value,
        metadata=policy_decision.to_dict(),
    )

    # ── 7. CREATE RECOVERY ACTION RECORD ─────────────────────────────────────
    action = RecoveryAction(
        payment_id=payment_id,
        customer_id=customer.get("customer_id", ""),
        action_type=RecoveryActionType(ai_decision.recommended_action),
        recovery_probability=ai_decision.recovery_probability,
        recovery_score=score_result.score,
        root_cause=failure_type,
        reason=ai_decision.reason,
        priority=ai_decision.priority,
        confidence=ai_decision.confidence,
        policy_status=policy_decision.status,
        policy_reason=policy_decision.reason,
        attempt_number=retry_attempts + 1,
        status=RecoveryActionStatus.PENDING,
        amount_original=payment.get("amount", 0),
        delay_minutes=ai_decision.delay_minutes,
        ai_decision=ai_decision.to_dict(),
    )
    action_dict = action.model_dump()
    action_dict["failure_type"] = failure_type.value
    action_dict["failure_label"] = failure_label
    action_dict["failure_explanation"] = failure_explanation
    action_dict["score_breakdown"] = score_result.to_dict()
    action_dict["policy_checks"] = policy_decision.checks
    action_dict["used_ai"] = used_ai

    await db.recovery_actions.insert_one(action_dict.copy())

    # ── 8. EXECUTE OR STOP ────────────────────────────────────────────────────
    if not policy_decision.approved:
        await db.recovery_actions.update_one(
            {"action_id": action.action_id},
            {"$set": {"status": RecoveryActionStatus.BLOCKED.value, "updated_at": datetime.utcnow()}}
        )
        await log_event(
            event="RECOVERY_BLOCKED_BY_POLICY",
            payment_id=payment_id,
            action_id=action.action_id,
            policy_result=policy_decision.status.value,
            result=policy_decision.reason,
        )
        action_dict["status"] = RecoveryActionStatus.BLOCKED.value
        return action_dict

    if ai_decision.recommended_action == RecoveryActionType.STOP.value:
        await db.recovery_actions.update_one(
            {"action_id": action.action_id},
            {"$set": {"status": RecoveryActionStatus.STOPPED.value, "updated_at": datetime.utcnow()}}
        )
        await log_event(
            event="RECOVERY_STOPPED_BY_AI",
            payment_id=payment_id,
            action_id=action.action_id,
            result="AI recommended STOP",
        )
        action_dict["status"] = RecoveryActionStatus.STOPPED.value
        return action_dict

    # Mark as executing
    await db.recovery_actions.update_one(
        {"action_id": action.action_id},
        {"$set": {"status": RecoveryActionStatus.EXECUTING.value, "updated_at": datetime.utcnow()}}
    )

    # Create Razorpay recovery order
    result = await _execute_recovery_action(
        action_id=action.action_id,
        action_type=ai_decision.recommended_action,
        payment=payment,
        customer=customer,
    )

    await log_event(
        event="RECOVERY_ACTION_EXECUTED",
        payment_id=payment_id,
        action_id=action.action_id,
        action=ai_decision.recommended_action,
        result=result.get("result"),
        metadata=result,
    )

    action_dict.update(result)
    return action_dict


async def _execute_recovery_action(
    action_id: str,
    action_type: str,
    payment: dict,
    customer: dict,
) -> dict:
    """
    Execute the approved recovery action.
    For most cases: create a new Razorpay order and return the checkout link.
    """
    db = get_db()
    provider = get_payment_provider()
    amount = int(payment.get("amount", 0))
    currency = payment.get("currency", "INR")

    try:
        razorpay_order = await provider.create_order(
            amount=amount,
            currency=currency,
            notes={
                "recovery_action_id": action_id,
                "original_payment_id": payment.get("payment_id"),
                "customer_id": payment.get("customer_id"),
                "action_type": action_type,
            },
            receipt=f"recovery_{action_id[:8]}",
        )

        razorpay_order_id = razorpay_order.get("id")
        recovery_link = f"/checkout/{razorpay_order_id}"  # frontend route

        await db.recovery_actions.update_one(
            {"action_id": action_id},
            {"$set": {
                "status": RecoveryActionStatus.APPROVED.value,
                "razorpay_order_id": razorpay_order_id,
                "recovery_link": recovery_link,
                "updated_at": datetime.utcnow(),
            }}
        )

        # Persist recovery order to orders collection
        await db.orders.update_one(
            {"order_id": razorpay_order_id},
            {"$set": {
                "order_id": razorpay_order_id,
                "customer_id": payment.get("customer_id"),
                "amount": amount,
                "currency": currency,
                "status": "created",
                "razorpay_order_id": razorpay_order_id,
                "description": f"Recovery for {payment.get('payment_id')}",
                "metadata": {"recovery_action_id": action_id},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }},
            upsert=True,
        )

        return {
            "result": "recovery_order_created",
            "razorpay_order_id": razorpay_order_id,
            "recovery_link": recovery_link,
            "status": RecoveryActionStatus.APPROVED.value,
        }

    except Exception as e:
        log.error("recovery_execution_failed", action_id=action_id, error=str(e))
        await db.recovery_actions.update_one(
            {"action_id": action_id},
            {"$set": {
                "status": RecoveryActionStatus.FAILED.value,
                "updated_at": datetime.utcnow(),
            }}
        )
        return {
            "result": "recovery_order_failed",
            "error": str(e),
            "status": RecoveryActionStatus.FAILED.value,
        }


async def confirm_recovery_success(payment_id: str, recovered_amount: float):
    """
    Called when webhook confirms a successful payment.
    Closes all open recovery actions for this payment.
    """
    db = get_db()
    now = datetime.utcnow()

    await db.recovery_actions.update_many(
        {"payment_id": payment_id, "status": {"$in": ["approved", "executing", "pending"]}},
        {"$set": {
            "status": RecoveryActionStatus.SUCCESS.value,
            "amount_recovered": recovered_amount,
            "completed_at": now,
            "updated_at": now,
        }}
    )

    # Update payment status
    await db.payments.update_one(
        {"payment_id": payment_id},
        {"$set": {"status": "captured", "updated_at": now}}
    )

    await log_event(
        event="RECOVERY_SUCCESS",
        payment_id=payment_id,
        amount_recovered=recovered_amount,
        result="Payment captured",
    )

    log.info("recovery_confirmed_success", payment_id=payment_id, amount=recovered_amount)
