"""
RecoverFlow AI - Recovery Scoring Service
Transparent, deterministic scoring with weighted features.
Modular design allows replacement with ML model later.
"""
from typing import Optional
from app.models.models import Payment, Customer, FailureType
import structlog

log = structlog.get_logger()

# ─── Feature Weights ─────────────────────────────────────────────────────────
WEIGHTS = {
    "customer_history": 0.30,
    "failure_type": 0.25,
    "retry_history": 0.20,
    "transaction_value": 0.15,
    "recency": 0.10,
}

# Failure type base recoverability (how recoverable each failure type is)
FAILURE_TYPE_SCORES = {
    FailureType.TEMPORARY_BANK_FAILURE: 0.90,
    FailureType.NETWORK_TIMEOUT: 0.85,
    FailureType.PAYMENT_METHOD_FAILURE: 0.65,
    FailureType.CUSTOMER_ACTION_REQUIRED: 0.55,
    FailureType.MULTIPLE_FAILED_ATTEMPTS: 0.30,
    FailureType.CHECKOUT_ABANDONMENT: 0.60,
    FailureType.UNKNOWN: 0.40,
}


class RecoveryScore:
    """Structured result from scoring."""
    def __init__(
        self,
        score: float,
        probability: float,
        feature_scores: dict,
        explanation: str,
    ):
        self.score = round(score, 4)
        self.probability = round(probability, 4)
        self.feature_scores = feature_scores
        self.explanation = explanation

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "probability": self.probability,
            "feature_scores": self.feature_scores,
            "explanation": self.explanation,
        }


def compute_recovery_score(
    payment: dict,
    customer: dict,
    retry_attempts: int = 0,
) -> RecoveryScore:
    """
    Compute a transparent recovery score using weighted deterministic features.

    Args:
        payment: Payment document dict
        customer: Customer document dict
        retry_attempts: Number of recovery attempts already made

    Returns:
        RecoveryScore with breakdown and explanation
    """
    feature_scores = {}
    explanations = []

    # ── 1. Customer payment history (30%) ────────────────────────────────────
    total = customer.get("total_payments", 0)
    successful = customer.get("successful_payments", 0)
    if total > 0:
        history_rate = successful / total
        # Boost for long history
        history_bonus = min(0.1, total / 100)
        ch_score = min(1.0, history_rate + history_bonus)
    else:
        ch_score = 0.5  # unknown customer, neutral
    feature_scores["customer_history"] = round(ch_score, 4)
    explanations.append(
        f"Customer has {successful}/{total} successful payments "
        f"(history score: {ch_score:.0%})"
    )

    # ── 2. Failure type (25%) ─────────────────────────────────────────────────
    failure_type_str = payment.get("failure_type", "UNKNOWN")
    try:
        ft = FailureType(failure_type_str)
    except ValueError:
        ft = FailureType.UNKNOWN
    ft_score = FAILURE_TYPE_SCORES.get(ft, 0.40)
    feature_scores["failure_type"] = round(ft_score, 4)
    explanations.append(
        f"Failure type '{ft.value}' has base recoverability of {ft_score:.0%}"
    )

    # ── 3. Retry history (20%) ────────────────────────────────────────────────
    max_retries = 2
    if retry_attempts == 0:
        retry_score = 1.0
    elif retry_attempts <= max_retries:
        retry_score = 1.0 - (retry_attempts * 0.35)
    else:
        retry_score = 0.1  # over limit
    feature_scores["retry_history"] = round(retry_score, 4)
    explanations.append(
        f"{retry_attempts} recovery attempts made "
        f"(retry score: {retry_score:.0%})"
    )

    # ── 4. Transaction value context (15%) ────────────────────────────────────
    amount_paise = payment.get("amount", 0)
    amount_inr = amount_paise / 100
    # Moderate transactions (₹500–₹50,000) are highest priority
    if 500 <= amount_inr <= 50_000:
        tv_score = 0.85
    elif amount_inr < 500:
        tv_score = 0.55  # low value, lower priority
    elif amount_inr <= 200_000:
        tv_score = 0.75  # high value, still worth it
    else:
        tv_score = 0.60  # very high value, more careful
    feature_scores["transaction_value"] = round(tv_score, 4)
    explanations.append(
        f"Transaction amount ₹{amount_inr:,.0f} "
        f"(value score: {tv_score:.0%})"
    )

    # ── 5. Recency / engagement (10%) ─────────────────────────────────────────
    # Checkout abandonment data: more time on page = more intent
    time_on_checkout = payment.get("metadata", {}).get("time_on_checkout_seconds", 0)
    page_views = payment.get("metadata", {}).get("page_views", 1)
    if ft == FailureType.CHECKOUT_ABANDONMENT:
        engagement = min(1.0, (time_on_checkout / 120) * 0.6 + (page_views / 5) * 0.4)
        recency_score = max(0.3, engagement)
    else:
        recency_score = 0.75  # default for payment failures
    feature_scores["recency"] = round(recency_score, 4)
    explanations.append(
        f"Engagement/recency score: {recency_score:.0%}"
    )

    # ── Weighted composite score ───────────────────────────────────────────────
    raw_score = (
        ch_score * WEIGHTS["customer_history"] +
        ft_score * WEIGHTS["failure_type"] +
        retry_score * WEIGHTS["retry_history"] +
        tv_score * WEIGHTS["transaction_value"] +
        recency_score * WEIGHTS["recency"]
    )

    # Hard override: if customer opted out, score = 0
    if customer.get("opted_out", False):
        raw_score = 0.0
        explanations = ["Customer has opted out of recovery communications."]

    score = round(min(1.0, max(0.0, raw_score)), 4)

    # Recovery probability is slightly more conservative than raw score
    probability = round(score * 0.95, 4)

    explanation = " | ".join(explanations)

    log.info(
        "recovery_score_computed",
        payment_id=payment.get("payment_id"),
        score=score,
        probability=probability,
        failure_type=failure_type_str,
    )

    return RecoveryScore(
        score=score,
        probability=probability,
        feature_scores=feature_scores,
        explanation=explanation,
    )


def get_priority(score: float) -> str:
    if score >= 0.75:
        return "HIGH"
    elif score >= 0.50:
        return "MEDIUM"
    return "LOW"


def get_expected_recovery(amount_paise: float, probability: float) -> float:
    """Expected recoverable amount in paise."""
    return round(amount_paise * probability, 2)
