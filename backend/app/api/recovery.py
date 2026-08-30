"""
RecoverFlow AI - Recovery API
Analyze and execute recovery actions for payment opportunities.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.database.connection import get_db
from app.services.recovery import run_recovery_workflow, StoppingRuleViolated
from app.services.scoring import compute_recovery_score, get_priority
from app.services.root_cause import analyze_failure
from app.agents.decision import make_recovery_decision
from app.policies.engine import check_policy
import structlog

log = structlog.get_logger()
router = APIRouter()


class AnalyzeRequest(BaseModel):
    payment_id: str


@router.post("/recovery/{payment_id}/analyze")
async def analyze_payment(payment_id: str):
    """
    Run full analysis pipeline (score, root cause, AI decision, policy check)
    WITHOUT executing any action. Preview mode.
    """
    db = get_db()

    payment = await db.payments.find_one({"payment_id": payment_id})
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    payment.pop("_id", None)

    customer = await db.customers.find_one({"customer_id": payment.get("customer_id")}) or {}
    customer.pop("_id", None)

    retry_attempts = await db.recovery_actions.count_documents({"payment_id": payment_id})

    # Scoring
    score_result = compute_recovery_score(payment, customer, retry_attempts)

    # Root cause
    failure_type, failure_label, failure_explanation = analyze_failure(
        failure_reason=payment.get("failure_reason", ""),
        retry_attempts=retry_attempts,
        error_code=payment.get("error_code", ""),
    )

    # AI decision
    ai_decision, used_ai = await make_recovery_decision(
        payment=payment,
        customer=customer,
        recovery_score=score_result.score,
        failure_type=failure_type.value,
        failure_explanation=failure_explanation,
        retry_attempts=retry_attempts,
    )

    # Policy check
    policy_decision = await check_policy(
        payment=payment,
        customer=customer,
        recovery_score=score_result.score,
        recommended_action=ai_decision.recommended_action,
        retry_attempts=retry_attempts,
    )

    return {
        "payment_id": payment_id,
        "payment": payment,
        "customer": customer,
        "analysis": {
            "recovery_score": score_result.score,
            "recovery_probability": score_result.probability,
            "expected_recovery_inr": (payment.get("amount", 0) / 100) * score_result.probability,
            "priority": get_priority(score_result.score),
            "score_breakdown": score_result.to_dict(),
            "failure_type": failure_type.value,
            "failure_label": failure_label,
            "failure_explanation": failure_explanation,
            "retry_attempts": retry_attempts,
        },
        "ai_decision": ai_decision.to_dict(),
        "used_ai": used_ai,
        "policy_decision": policy_decision.to_dict(),
    }


@router.post("/recovery/{payment_id}/execute")
async def execute_recovery(payment_id: str, background_tasks: BackgroundTasks):
    """
    Execute the full recovery workflow for a payment.
    Runs through: Score → AI Decision → Policy → Execute → Audit
    """
    db = get_db()

    payment = await db.payments.find_one({"payment_id": payment_id})
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")

    if payment.get("status") == "captured":
        raise HTTPException(status_code=400, detail="Payment already captured. No recovery needed.")

    try:
        result = await run_recovery_workflow(payment_id=payment_id)
        return {
            "success": True,
            "payment_id": payment_id,
            "result": result,
        }
    except StoppingRuleViolated as e:
        return {
            "success": False,
            "payment_id": payment_id,
            "stopped": True,
            "reason": str(e),
        }
    except Exception as e:
        log.error("recovery_execute_error", payment_id=payment_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Recovery workflow error: {str(e)}")
