"""
RecoverFlow AI - Policy / Guardrail Engine
The AI can recommend; the policy decides what is permitted.
This is a critical safety layer — no financial action bypasses it.
"""
from typing import Tuple, Optional
from app.models.models import Policy, RecoveryActionType, PolicyStatus
from app.database.connection import get_db
import structlog

log = structlog.get_logger()

_default_policy = Policy()


class PolicyDecision:
    def __init__(
        self,
        status: PolicyStatus,
        reason: str,
        checks: list,
    ):
        self.status = status
        self.reason = reason
        self.checks = checks  # List of {"check": str, "passed": bool, "detail": str}

    @property
    def approved(self) -> bool:
        return self.status == PolicyStatus.APPROVED

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "checks": self.checks,
            "approved": self.approved,
        }


async def get_active_policy() -> Policy:
    """Fetch the active policy from DB, fall back to defaults."""
    try:
        db = get_db()
        doc = await db.policies.find_one({"name": "default"})
        if doc:
            doc.pop("_id", None)
            return Policy(**doc)
    except Exception as e:
        log.warning("policy_fetch_failed", error=str(e))
    return _default_policy


async def check_policy(
    *,
    payment: dict,
    customer: dict,
    recovery_score: float,
    recommended_action: str,
    retry_attempts: int,
    policy: Optional[Policy] = None,
) -> PolicyDecision:
    """
    Evaluate whether the recommended recovery action is permitted by policy.

    Every rule is evaluated and reported transparently.
    """
    if policy is None:
        policy = await get_active_policy()

    checks = []
    denials = []

    amount_inr = payment.get("amount", 0) / 100

    # ── Check 1: Recovery score threshold ────────────────────────────────────
    score_ok = recovery_score >= policy.min_recovery_score
    checks.append({
        "check": "Score threshold",
        "passed": score_ok,
        "detail": f"Score {recovery_score:.0%} {'≥' if score_ok else '<'} min {policy.min_recovery_score:.0%}",
    })
    if not score_ok:
        denials.append(f"Recovery score {recovery_score:.2f} is below threshold {policy.min_recovery_score:.2f}")

    # ── Check 2: Retry limit ──────────────────────────────────────────────────
    retry_ok = retry_attempts < policy.max_retries
    checks.append({
        "check": "Retry limit",
        "passed": retry_ok,
        "detail": f"{retry_attempts} attempts < max {policy.max_retries}",
    })
    if not retry_ok:
        denials.append(f"Retry limit reached: {retry_attempts} ≥ {policy.max_retries}")

    # ── Check 3: Transaction amount limit ────────────────────────────────────
    amount_ok = amount_inr <= policy.max_transaction_amount
    checks.append({
        "check": "Amount limit",
        "passed": amount_ok,
        "detail": f"₹{amount_inr:,.0f} {'≤' if amount_ok else '>'} max ₹{policy.max_transaction_amount:,.0f}",
    })
    if not amount_ok:
        denials.append(f"Transaction amount ₹{amount_inr:,.0f} exceeds policy max ₹{policy.max_transaction_amount:,.0f}")

    # ── Check 4: Customer opt-out ─────────────────────────────────────────────
    opted_out = customer.get("opted_out", False)
    optout_ok = not (policy.stop_if_customer_optout and opted_out)
    checks.append({
        "check": "Customer eligibility",
        "passed": optout_ok,
        "detail": "Customer eligible" if optout_ok else "Customer opted out",
    })
    if not optout_ok:
        denials.append("Customer has opted out of recovery")

    # ── Check 5: Action allowed ───────────────────────────────────────────────
    action_ok = recommended_action in policy.allowed_actions or recommended_action == "STOP"
    checks.append({
        "check": "Action permitted",
        "passed": action_ok,
        "detail": f"'{recommended_action}' {'is' if action_ok else 'is not'} in allowed actions",
    })
    if not action_ok:
        denials.append(f"Action '{recommended_action}' is not permitted by policy")

    # ── Decision ──────────────────────────────────────────────────────────────
    if denials:
        status = PolicyStatus.DENIED
        reason = " | ".join(denials)
    else:
        status = PolicyStatus.APPROVED
        reason = "All policy checks passed"

    log.info(
        "policy_decision",
        payment_id=payment.get("payment_id"),
        status=status.value,
        checks_failed=len(denials),
        reason=reason,
    )

    return PolicyDecision(status=status, reason=reason, checks=checks)
