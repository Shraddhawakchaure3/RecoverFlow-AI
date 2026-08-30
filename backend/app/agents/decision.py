"""
RecoverFlow AI - AI Decision Agent
The LLM produces structured JSON recommendations.
It cannot directly execute financial actions.
Falls back to deterministic rules on any failure.
"""
from typing import Optional, Tuple
from pydantic import BaseModel, Field, validator
import structlog
import json

from app.config import settings
from app.models.models import FailureType, RecoveryActionType, Priority

log = structlog.get_logger()


# ─── Structured Output Schema ─────────────────────────────────────────────────

class AIDecision(BaseModel):
    """Structured output from the AI agent."""
    recovery_probability: float = Field(ge=0.0, le=1.0)
    root_cause: str
    recommended_action: str
    delay_minutes: int = Field(default=0, ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    priority: str
    escalation_reason: Optional[str] = None

    @validator("recommended_action")
    def validate_action(cls, v):
        valid = {a.value for a in RecoveryActionType}
        if v not in valid:
            raise ValueError(f"Invalid action: {v}. Must be one of {valid}")
        return v

    @validator("priority")
    def validate_priority(cls, v):
        valid = {p.value for p in Priority}
        if v not in valid:
            raise ValueError(f"Invalid priority: {v}. Must be one of {valid}")
        return v

    def to_dict(self) -> dict:
        return self.model_dump()


# ─── Deterministic Fallback ───────────────────────────────────────────────────

def _deterministic_decision(
    payment: dict,
    customer: dict,
    recovery_score: float,
    failure_type: str,
    retry_attempts: int,
) -> AIDecision:
    """
    Rule-based fallback used when LLM is unavailable or returns invalid output.
    Produces a conservative but reasonable recommendation.
    """
    amount_inr = payment.get("amount", 0) / 100
    successful = customer.get("successful_payments", 0)
    total = customer.get("total_payments", 1)

    if recovery_score < 0.40:
        action = RecoveryActionType.STOP
        reason = f"Recovery score {recovery_score:.0%} is below threshold. Stopping to avoid unnecessary intervention."
        priority = Priority.LOW
        delay = 0

    elif failure_type in ("TEMPORARY_BANK_FAILURE", "NETWORK_TIMEOUT"):
        action = RecoveryActionType.DELAYED_RECOVERY
        delay = 30 if retry_attempts == 0 else 60
        reason = (
            f"Temporary failure with {successful}/{total} successful payment history. "
            "Delayed retry recommended to allow bank to recover."
        )
        priority = Priority.HIGH if recovery_score >= 0.75 else Priority.MEDIUM

    elif failure_type == "CHECKOUT_ABANDONMENT":
        action = RecoveryActionType.PAYMENT_REMINDER
        delay = 15
        reason = f"Checkout was abandoned. A payment reminder may recover ₹{amount_inr:,.0f}."
        priority = Priority.MEDIUM

    elif failure_type == "PAYMENT_METHOD_FAILURE":
        action = RecoveryActionType.ALTERNATE_PAYMENT_METHOD
        delay = 0
        reason = "Payment method failed. Offering alternate payment options improves recovery chance."
        priority = Priority.MEDIUM

    elif failure_type == "CUSTOMER_ACTION_REQUIRED":
        action = RecoveryActionType.CHECKOUT_RECOVERY
        delay = 10
        reason = "Customer did not complete authentication. A fresh checkout link may help."
        priority = Priority.MEDIUM

    elif failure_type == "MULTIPLE_FAILED_ATTEMPTS":
        action = RecoveryActionType.ESCALATE
        delay = 0
        reason = "Multiple attempts have failed. Escalating for manual review."
        priority = Priority.LOW

    else:
        action = RecoveryActionType.RETRY_RECOVERY
        delay = 15
        reason = "Unknown failure type. Attempting a cautious retry."
        priority = Priority.LOW

    return AIDecision(
        recovery_probability=recovery_score,
        root_cause=failure_type,
        recommended_action=action.value,
        delay_minutes=delay,
        confidence=0.70,  # deterministic fallback is less confident
        reason=reason,
        priority=priority.value,
    )


# ─── LLM Client ───────────────────────────────────────────────────────────────

async def _call_llm(prompt: str) -> Optional[dict]:
    """Call LLM via OpenAI-compatible API and return parsed JSON."""
    if not settings.is_ai_configured:
        return None

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=settings.ai_api_key,
            base_url=settings.ai_base_url,
        )
        response = await client.chat.completions.create(
            model=settings.ai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are RecoverFlow AI, an autonomous revenue recovery agent. "
                        "Analyze payment failures and produce structured JSON recommendations. "
                        "You MUST return ONLY valid JSON matching the specified schema. "
                        "Never recommend actions outside the allowed list."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        return json.loads(raw)
    except Exception as e:
        log.warning("llm_call_failed", error=str(e))
        return None


# ─── Main Agent ───────────────────────────────────────────────────────────────

async def make_recovery_decision(
    *,
    payment: dict,
    customer: dict,
    recovery_score: float,
    failure_type: str,
    failure_explanation: str,
    retry_attempts: int,
) -> tuple[AIDecision, bool]:
    """
    Main AI decision function.

    Returns:
        (AIDecision, used_ai: bool)
        used_ai is False when deterministic fallback was used
    """
    amount_inr = payment.get("amount", 0) / 100
    customer_name = customer.get("name", "Unknown")
    successful = customer.get("successful_payments", 0)
    total = customer.get("total_payments", 0)

    prompt = f"""Analyze this payment failure and recommend a recovery action.

PAYMENT DATA:
- Payment ID: {payment.get('payment_id')}
- Amount: ₹{amount_inr:,.2f}
- Method: {payment.get('method', 'unknown')}
- Failure Type: {failure_type}
- Failure Reason: {payment.get('failure_reason', 'unknown')}
- Failure Explanation: {failure_explanation}

CUSTOMER DATA:
- Customer: {customer_name}
- Payment History: {successful} successful / {total} total payments
- Success Rate: {(successful/total*100) if total > 0 else 0:.0f}%

RECOVERY CONTEXT:
- Recovery Score: {recovery_score:.2%}
- Previous Recovery Attempts: {retry_attempts}

ALLOWED ACTIONS (you must choose exactly one):
- RETRY_RECOVERY: Retry the payment immediately
- DELAYED_RECOVERY: Retry after a delay (specify delay_minutes)
- CHECKOUT_RECOVERY: Create a new checkout link for the customer
- PAYMENT_REMINDER: Send a payment reminder
- ALTERNATE_PAYMENT_METHOD: Suggest alternate payment method
- ESCALATE: Escalate for human review
- STOP: Do not attempt recovery (score too low, risk too high)

Return a JSON object with this EXACT schema:
{{
  "recovery_probability": <float 0-1>,
  "root_cause": "<failure type string>",
  "recommended_action": "<one of the allowed actions>",
  "delay_minutes": <int, 0 if not delayed>,
  "confidence": <float 0-1>,
  "reason": "<clear explanation of why this action was chosen>",
  "priority": "<HIGH|MEDIUM|LOW>"
}}"""

    # Try LLM first
    raw = await _call_llm(prompt)
    used_ai = False

    if raw:
        try:
            decision = AIDecision(**raw)
            used_ai = True
            log.info(
                "ai_decision_made",
                payment_id=payment.get("payment_id"),
                action=decision.recommended_action,
                confidence=decision.confidence,
                used_ai=True,
            )
            return decision, True
        except Exception as e:
            log.warning("ai_output_validation_failed", error=str(e), raw=raw)

    # Fallback to deterministic rules
    decision = _deterministic_decision(
        payment=payment,
        customer=customer,
        recovery_score=recovery_score,
        failure_type=failure_type,
        retry_attempts=retry_attempts,
    )
    log.info(
        "ai_decision_fallback",
        payment_id=payment.get("payment_id"),
        action=decision.recommended_action,
    )
    return decision, False
