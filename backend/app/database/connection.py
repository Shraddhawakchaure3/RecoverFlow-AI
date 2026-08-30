"""
RecoverFlow AI - MongoDB Database Connection
Motor async driver for MongoDB.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings
import structlog

log = structlog.get_logger()

_client: AsyncIOMotorClient = None
_db: AsyncIOMotorDatabase = None


async def connect_db():
    global _client, _db
    try:
        _client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
        # Verify connection
        await _client.admin.command("ping")
        # Extract DB name from URI (e.g. mongodb://localhost:27017/recoverflow → recoverflow)
        uri_path = settings.mongodb_uri.split("/")[-1].split("?")[0].strip()
        db_name = uri_path if uri_path else "recoverflow"
        _db = _client[db_name]
        log.info("mongodb_connected", db=db_name)
        await _ensure_indexes()
    except Exception as e:
        log.error("mongodb_connection_failed", error=str(e))
        raise


async def disconnect_db():
    global _client
    if _client:
        _client.close()
        log.info("mongodb_disconnected")


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return _db


async def _ensure_indexes():
    """Create indexes for performance and uniqueness guarantees."""
    db = get_db()
    # payments
    await db.payments.create_index("payment_id", unique=True)
    await db.payments.create_index("order_id")
    await db.payments.create_index("customer_id")
    await db.payments.create_index("status")
    await db.payments.create_index("created_at")
    # orders
    await db.orders.create_index("order_id", unique=True)
    await db.orders.create_index("customer_id")
    # customers
    await db.customers.create_index("customer_id", unique=True)
    # recovery_events
    await db.recovery_events.create_index("payment_id")
    await db.recovery_events.create_index("event_type")
    await db.recovery_events.create_index("created_at")
    # recovery_actions
    await db.recovery_actions.create_index("action_id", unique=True)
    await db.recovery_actions.create_index("payment_id")
    await db.recovery_actions.create_index("status")
    # audit_logs
    await db.audit_logs.create_index("payment_id")
    await db.audit_logs.create_index("timestamp")
    # checkout_sessions
    await db.checkout_sessions.create_index("session_id", unique=True)
    await db.checkout_sessions.create_index("order_id")
    # webhook events (idempotency)
    await db.webhook_events.create_index("event_id", unique=True)
    log.info("mongodb_indexes_created")
