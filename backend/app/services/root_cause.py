"""
RecoverFlow AI - Root Cause Analyzer
Categorizes payment failures into machine-readable types with human explanations.
"""
from typing import Tuple
from app.models.models import FailureType
import structlog

log = structlog.get_logger()

# Failure reason keyword mapping to FailureType
FAILURE_REASON_MAP = {
    # Temporary bank failures
    "bank_not_responding": FailureType.TEMPORARY_BANK_FAILURE,
    "bank_internal_error": FailureType.TEMPORARY_BANK_FAILURE,
    "bank_offline": FailureType.TEMPORARY_BANK_FAILURE,
    "gateway_timeout": FailureType.NETWORK_TIMEOUT,
    "connection_timeout": FailureType.NETWORK_TIMEOUT,
    "network_error": FailureType.NETWORK_TIMEOUT,
    "timeout": FailureType.NETWORK_TIMEOUT,
    # Card / method failures
    "card_declined": FailureType.PAYMENT_METHOD_FAILURE,
    "insufficient_funds": FailureType.PAYMENT_METHOD_FAILURE,
    "card_expired": FailureType.PAYMENT_METHOD_FAILURE,
    "invalid_card": FailureType.PAYMENT_METHOD_FAILURE,
    "card_blocked": FailureType.PAYMENT_METHOD_FAILURE,
    "upi_collect_request_expired": FailureType.PAYMENT_METHOD_FAILURE,
    "payment_cancelled": FailureType.CUSTOMER_ACTION_REQUIRED,
    "customer_cancelled": FailureType.CUSTOMER_ACTION_REQUIRED,
    "authentication_failed": FailureType.CUSTOMER_ACTION_REQUIRED,
    "otp_expired": FailureType.CUSTOMER_ACTION_REQUIRED,
    "checkout_abandoned": FailureType.CHECKOUT_ABANDONMENT,
    "abandoned": FailureType.CHECKOUT_ABANDONMENT,
}

EXPLANATIONS = {
    FailureType.TEMPORARY_BANK_FAILURE: (
        "Temporary payment failure",
        "This appears to be a transient bank error. The customer's bank may have been temporarily unavailable. "
        "These failures are typically resolved within 30–60 minutes and have high recovery rates."
    ),
    FailureType.NETWORK_TIMEOUT: (
        "Network timeout",
        "The payment timed out due to network issues. This is often a one-time connectivity problem "
        "and retrying usually succeeds."
    ),
    FailureType.PAYMENT_METHOD_FAILURE: (
        "Payment method issue",
        "The payment method itself has an issue (e.g., insufficient funds, expired card). "
        "Recovery may require the customer to use an alternate payment method."
    ),
    FailureType.CUSTOMER_ACTION_REQUIRED: (
        "Customer action required",
        "The customer cancelled or did not complete authentication. "
        "A reminder or a new checkout link may prompt them to complete the payment."
    ),
    FailureType.MULTIPLE_FAILED_ATTEMPTS: (
        "Repeated failure pattern",
        "Multiple recovery attempts have already failed. Further retries are unlikely to succeed "
        "without a different approach or customer intervention."
    ),
    FailureType.CHECKOUT_ABANDONMENT: (
        "Checkout abandoned",
        "The customer initiated checkout but did not complete it. "
        "A targeted reminder can often recover these customers."
    ),
    FailureType.UNKNOWN: (
        "Unknown failure",
        "The failure reason is unclear. A cautious recovery approach is recommended."
    ),
}


def analyze_failure(
    failure_reason: str,
    retry_attempts: int = 0,
    error_code: str = "",
) -> Tuple[FailureType, str, str]:
    """
    Analyze a payment failure and return:
    - FailureType enum
    - Short human-readable label
    - Detailed explanation

    Args:
        failure_reason: Raw failure_reason string from Razorpay or system
        retry_attempts: Number of previous recovery attempts
        error_code: Optional Razorpay error code

    Returns:
        Tuple of (FailureType, label, explanation)
    """
    if retry_attempts >= 3:
        failure_type = FailureType.MULTIPLE_FAILED_ATTEMPTS
    else:
        failure_type = _classify_reason(failure_reason or "", error_code or "")

    label, explanation = EXPLANATIONS.get(failure_type, ("Unknown", "No explanation available."))

    log.info(
        "failure_analyzed",
        failure_reason=failure_reason,
        failure_type=failure_type.value,
        retry_attempts=retry_attempts,
    )

    return failure_type, label, explanation


def _classify_reason(failure_reason: str, error_code: str) -> FailureType:
    """Map raw reason string to FailureType using keyword matching."""
    needle = (failure_reason + " " + error_code).lower().replace("-", "_")

    for keyword, ftype in FAILURE_REASON_MAP.items():
        if keyword in needle:
            return ftype

    # Heuristic fallbacks
    if any(k in needle for k in ["bank", "nbfc"]):
        return FailureType.TEMPORARY_BANK_FAILURE
    if any(k in needle for k in ["timeout", "network", "connection"]):
        return FailureType.NETWORK_TIMEOUT
    if any(k in needle for k in ["card", "upi", "wallet", "fund", "balance"]):
        return FailureType.PAYMENT_METHOD_FAILURE
    if any(k in needle for k in ["cancel", "otp", "auth"]):
        return FailureType.CUSTOMER_ACTION_REQUIRED

    return FailureType.UNKNOWN
