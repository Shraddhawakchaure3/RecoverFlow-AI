"""
RecoverFlow AI - Policies API
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from app.database.connection import get_db
from app.policies.engine import get_active_policy
from app.models.models import Policy
from datetime import datetime
import structlog

log = structlog.get_logger()
router = APIRouter()


class PolicyUpdateRequest(BaseModel):
    max_retries: Optional[int] = None
    max_recovery_actions: Optional[int] = None
    min_recovery_score: Optional[float] = None
    max_transaction_amount: Optional[float] = None
    stop_if_payment_success: Optional[bool] = None
    stop_if_customer_optout: Optional[bool] = None
    allowed_actions: Optional[List[str]] = None


@router.get("/policies")
async def get_policies():
    policy = await get_active_policy()
    return policy.model_dump()


@router.put("/policies")
async def update_policy(request: PolicyUpdateRequest):
    """Update the active policy configuration."""
    db = get_db()
    policy = await get_active_policy()
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()

    await db.policies.update_one(
        {"name": "default"},
        {"$set": update_data},
        upsert=True,
    )

    return {"success": True, "updated": update_data}
