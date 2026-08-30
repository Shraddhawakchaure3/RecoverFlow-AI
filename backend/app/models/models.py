"""
RecoverFlow AI - MongoDB Models
Pydantic models for all database collections.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


def gen_id() -> str:
    return str(uuid.uuid4())


# ─── Enums ────────────────────────────────────────────────────────────────────

class PaymentStatus(str, Enum):
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"


class FailureType(str, Enum):
    TEMPORARY_BANK_FAILURE = "TEMPORARY_BANK_FAILURE"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    PAYMENT_METHOD_FAILURE = "PAYMENT_METHOD_FAILURE"
    CUSTOMER_ACTION_REQUIRED = "CUSTOMER_ACTION_REQUIRED"
    MULTIPLE_FAILED_ATTEMPTS = "MULTIPLE_FAILED_ATTEMPTS"
    CHECKOUT_ABANDONMENT = "CHECKOUT_ABANDONMENT"
    UNKNOWN = "UNKNOWN"


class RecoveryActionType(str, Enum):
    RETRY_RECOVERY = "RETRY_RECOVERY"
    DELAYED_RECOVERY = "DELAYED_RECOVERY"
    CHECKOUT_RECOVERY = "CHECKOUT_RECOVERY"
    PAYMENT_REMINDER = "PAYMENT_REMINDER"
    ALTERNATE_PAYMENT_METHOD = "ALTERNATE_PAYMENT_METHOD"
    ESCALATE = "ESCALATE"
    STOP = "STOP"


class RecoveryActionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    BLOCKED = "blocked"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    STOPPED = "stopped"


class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PolicyStatus(str, Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"


# ─── Customer ─────────────────────────────────────────────────────────────────

class Customer(BaseModel):
    customer_id: str = Field(default_factory=gen_id)
    name: str
    email: str
    phone: Optional[str] = None
    total_payments: int = 0
    successful_payments: int = 0
    failed_payments: int = 0
    total_amount_paid: float = 0.0
    opted_out: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        if self.total_payments == 0:
            return 0.0
        return self.successful_payments / self.total_payments


# ─── Order ────────────────────────────────────────────────────────────────────

class Order(BaseModel):
    order_id: str
    customer_id: str
    amount: float  # in paise (Razorpay convention)
    currency: str = "INR"
    status: str = "created"
    razorpay_order_id: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Payment ──────────────────────────────────────────────────────────────────

class Payment(BaseModel):
    payment_id: str
    order_id: str
    customer_id: str
    amount: float  # in paise
    currency: str = "INR"
    method: Optional[str] = None
    status: PaymentStatus
    failure_reason: Optional[str] = None
    failure_type: Optional[FailureType] = None
    error_code: Optional[str] = None
    bank: Optional[str] = None
    wallet: Optional[str] = None
    vpa: Optional[str] = None
    description: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def amount_inr(self) -> float:
        return self.amount / 100


# ─── Checkout Session ─────────────────────────────────────────────────────────

class CheckoutSession(BaseModel):
    session_id: str = Field(default_factory=gen_id)
    order_id: str
    customer_id: str
    amount: float
    currency: str = "INR"
    initiated_at: datetime = Field(default_factory=datetime.utcnow)
    abandoned_at: Optional[datetime] = None
    recovered_at: Optional[datetime] = None
    time_on_checkout_seconds: Optional[int] = None
    page_views: int = 1
    status: str = "initiated"  # initiated | abandoned | completed
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ─── Recovery Event ───────────────────────────────────────────────────────────

class RecoveryEvent(BaseModel):
    event_id: str = Field(default_factory=gen_id)
    payment_id: str
    event_type: str  # payment_failed | checkout_abandoned | recovery_started etc.
    data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Recovery Action ──────────────────────────────────────────────────────────

class RecoveryAction(BaseModel):
    action_id: str = Field(default_factory=gen_id)
    payment_id: str
    customer_id: str
    action_type: RecoveryActionType
    recovery_probability: float
    recovery_score: float
    root_cause: FailureType
    reason: str
    priority: Priority
    confidence: float
    policy_status: PolicyStatus
    policy_reason: Optional[str] = None
    attempt_number: int = 1
    status: RecoveryActionStatus = RecoveryActionStatus.PENDING
    amount_original: float
    amount_recovered: Optional[float] = None
    delay_minutes: int = 0
    ai_decision: Optional[Dict[str, Any]] = None
    razorpay_order_id: Optional[str] = None
    recovery_link: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# ─── Policy ───────────────────────────────────────────────────────────────────

class Policy(BaseModel):
    policy_id: str = Field(default_factory=gen_id)
    name: str = "default"
    max_retries: int = 2
    max_recovery_actions: int = 3
    min_recovery_score: float = 0.40
    max_transaction_amount: float = 1_000_000
    stop_if_payment_success: bool = True
    stop_if_customer_optout: bool = True
    allowed_actions: List[str] = Field(default_factory=lambda: [
        "RETRY_RECOVERY", "DELAYED_RECOVERY", "CHECKOUT_RECOVERY",
        "PAYMENT_REMINDER", "ALTERNATE_PAYMENT_METHOD"
    ])
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Audit Log ────────────────────────────────────────────────────────────────

class AuditLog(BaseModel):
    log_id: str = Field(default_factory=gen_id)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event: str
    payment_id: Optional[str] = None
    customer_id: Optional[str] = None
    action_id: Optional[str] = None
    ai_decision: Optional[Dict[str, Any]] = None
    policy_result: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
    amount_recovered: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ─── Webhook Event ────────────────────────────────────────────────────────────

class WebhookEvent(BaseModel):
    event_id: str  # from Razorpay X-Razorpay-Event-Id header
    event_type: str
    payload: Dict[str, Any]
    processed: bool = False
    processed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
