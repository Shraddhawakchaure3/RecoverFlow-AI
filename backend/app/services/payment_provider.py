"""
RecoverFlow AI - Payment Provider Abstraction
Allows switching between Razorpay (test mode) and a local mock.
"""
from abc import ABC, abstractmethod
from typing import Optional
import structlog

log = structlog.get_logger()


class PaymentProviderBase(ABC):
    """Abstract interface for payment operations."""

    @abstractmethod
    async def create_order(
        self,
        amount: int,
        currency: str,
        notes: dict,
        receipt: str,
    ) -> dict:
        """Create a new payment order. Amount in paise."""
        ...

    @abstractmethod
    async def get_payment(self, payment_id: str) -> dict:
        """Fetch payment details."""
        ...

    @abstractmethod
    async def get_order(self, order_id: str) -> dict:
        """Fetch order details."""
        ...


# ─── Razorpay Provider ────────────────────────────────────────────────────────

class RazorpayProvider(PaymentProviderBase):
    """Razorpay Test Mode adapter."""

    def __init__(self, key_id: str, key_secret: str):
        import razorpay
        self._client = razorpay.Client(auth=(key_id, key_secret))
        log.info("razorpay_provider_initialized", mode="test")

    async def create_order(
        self,
        amount: int,
        currency: str = "INR",
        notes: dict = None,
        receipt: str = "",
    ) -> dict:
        import asyncio
        data = {
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
            "notes": notes or {},
        }
        # razorpay SDK is synchronous; run in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._client.order.create, data)

    async def get_payment(self, payment_id: str) -> dict:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._client.payment.fetch, payment_id)

    async def get_order(self, order_id: str) -> dict:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._client.order.fetch, order_id)


# ─── Mock Provider ────────────────────────────────────────────────────────────

class MockPaymentProvider(PaymentProviderBase):
    """
    Local mock for development without Razorpay credentials.
    Simulates Razorpay order/payment responses realistically.
    """
    import uuid as _uuid

    def __init__(self):
        log.info("mock_payment_provider_initialized")
        self._orders = {}
        self._payments = {}

    async def create_order(
        self,
        amount: int,
        currency: str = "INR",
        notes: dict = None,
        receipt: str = "",
    ) -> dict:
        import uuid
        order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
        order = {
            "id": order_id,
            "entity": "order",
            "amount": amount,
            "amount_paid": 0,
            "amount_due": amount,
            "currency": currency,
            "receipt": receipt,
            "offer_id": None,
            "status": "created",
            "attempts": 0,
            "notes": notes or {},
        }
        self._orders[order_id] = order
        log.info("mock_order_created", order_id=order_id, amount=amount)
        return order

    async def get_payment(self, payment_id: str) -> dict:
        return self._payments.get(payment_id, {
            "id": payment_id,
            "entity": "payment",
            "status": "failed",
            "error_code": "BAD_REQUEST_ERROR",
            "error_description": "Mock payment not found",
        })

    async def get_order(self, order_id: str) -> dict:
        return self._orders.get(order_id, {
            "id": order_id,
            "entity": "order",
            "status": "created",
        })


# ─── Provider Factory ─────────────────────────────────────────────────────────

_provider: Optional[PaymentProviderBase] = None


def get_payment_provider() -> PaymentProviderBase:
    global _provider
    if _provider is None:
        from app.config import settings
        if settings.is_razorpay_configured:
            _provider = RazorpayProvider(
                key_id=settings.razorpay_key_id,
                key_secret=settings.razorpay_key_secret,
            )
        else:
            log.warning("razorpay_not_configured_using_mock")
            _provider = MockPaymentProvider()
    return _provider
