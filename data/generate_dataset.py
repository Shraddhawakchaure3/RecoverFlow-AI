"""
RecoverFlow AI - Synthetic Dataset Generator
Generates 500-1000 realistic transactions with controlled variation.
Seeds the MongoDB database for evaluation and demo.

Usage:
    python generate_dataset.py [--count 750] [--seed 42] [--mongo-uri <uri>]
"""
import asyncio
import argparse
import random
import uuid
from datetime import datetime, timedelta
from typing import List
import structlog

log = structlog.get_logger()

# ─── Realistic Data Sets ─────────────────────────────────────────────────────

CUSTOMER_PROFILES = [
    {"name": "Ravi Sharma", "email": "ravi.sharma@example.com", "phone": "9876543210"},
    {"name": "Priya Patel", "email": "priya.patel@example.com", "phone": "9876543211"},
    {"name": "Arjun Singh", "email": "arjun.singh@example.com", "phone": "9876543212"},
    {"name": "Meera Gupta", "email": "meera.gupta@example.com", "phone": "9876543213"},
    {"name": "Vikram Nair", "email": "vikram.nair@example.com", "phone": "9876543214"},
    {"name": "Sunita Reddy", "email": "sunita.reddy@example.com", "phone": "9876543215"},
    {"name": "Ankit Joshi", "email": "ankit.joshi@example.com", "phone": "9876543216"},
    {"name": "Kavya Iyer", "email": "kavya.iyer@example.com", "phone": "9876543217"},
    {"name": "Rohit Kumar", "email": "rohit.kumar@example.com", "phone": "9876543218"},
    {"name": "Deepa Mehta", "email": "deepa.mehta@example.com", "phone": "9876543219"},
    {"name": "Tech Solutions Pvt Ltd", "email": "billing@techsolutions.in", "phone": "9900001111"},
    {"name": "Green Retail Co", "email": "accounts@greenretail.co.in", "phone": "9900001112"},
    {"name": "Apex Services Ltd", "email": "finance@apexservices.com", "phone": "9900001113"},
    {"name": "BlueSky Commerce", "email": "payments@bluesky.io", "phone": "9900001114"},
    {"name": "Nexus Enterprises", "email": "ops@nexusenterprise.in", "phone": "9900001115"},
]

FAILURE_TYPES = [
    ("TEMPORARY_BANK_FAILURE", "bank_not_responding", 0.25),
    ("NETWORK_TIMEOUT", "gateway_timeout", 0.15),
    ("PAYMENT_METHOD_FAILURE", "card_declined", 0.20),
    ("PAYMENT_METHOD_FAILURE", "insufficient_funds", 0.15),
    ("CUSTOMER_ACTION_REQUIRED", "payment_cancelled", 0.10),
    ("CUSTOMER_ACTION_REQUIRED", "otp_expired", 0.05),
    ("CHECKOUT_ABANDONMENT", "checkout_abandoned", 0.07),
    ("UNKNOWN", "unknown_error", 0.03),
]

PAYMENT_METHODS = ["card", "upi", "netbanking", "wallet", "emi"]
BANKS = ["HDFC", "SBI", "ICICI", "AXIS", "KOTAK", "YES", "FEDERAL", "INDUSIND"]
CURRENCIES = ["INR"]


def random_amount() -> int:
    """Return a random amount in paise with realistic distribution."""
    weights = [
        (50000, 200000, 0.30),    # ₹500–₹2,000 (small transactions)
        (200100, 1000000, 0.40),  # ₹2,001–₹10,000 (medium)
        (1000100, 5000000, 0.20), # ₹10,001–₹50,000 (large)
        (5000100, 20000000, 0.10),# ₹50,001–₹2,00,000 (enterprise)
    ]
    r = random.random()
    cumulative = 0
    for low, high, weight in weights:
        cumulative += weight
        if r <= cumulative:
            return random.randint(low, high)
    return random.randint(50000, 1000000)


def build_customer(profile: dict, idx: int) -> dict:
    """Generate a customer with realistic payment history."""
    total = random.randint(1, 25)
    success_rate = random.choices(
        [0.9, 0.7, 0.5, 0.3, 0.1],
        weights=[0.35, 0.30, 0.20, 0.10, 0.05],
    )[0]
    successful = max(0, min(total, round(total * success_rate)))

    return {
        "customer_id": f"cust_{idx:04d}",
        "name": profile["name"],
        "email": profile["email"],
        "phone": profile["phone"],
        "total_payments": total,
        "successful_payments": successful,
        "failed_payments": total - successful,
        "total_amount_paid": successful * random.randint(10000, 500000) / 100,
        "opted_out": random.random() < 0.03,  # 3% opt-out rate
        "created_at": datetime.utcnow() - timedelta(days=random.randint(30, 730)),
        "updated_at": datetime.utcnow(),
    }


def build_payment(idx: int, customer: dict) -> dict:
    """Generate a realistic failed payment record."""
    chosen = random.choices(
        FAILURE_TYPES,
        weights=[ft[2] for ft in FAILURE_TYPES],
    )[0]
    failure_type, failure_reason = chosen[0], chosen[1]

    # Some payments are captured (recovered previously)
    is_captured = random.random() < 0.20  # 20% already recovered

    created_at = datetime.utcnow() - timedelta(
        hours=random.randint(1, 720)
    )

    return {
        "payment_id": f"pay_{idx:05d}",
        "order_id": f"order_{idx:05d}",
        "customer_id": customer["customer_id"],
        "amount": random_amount(),
        "currency": "INR",
        "method": random.choice(PAYMENT_METHODS),
        "status": "captured" if is_captured else "failed",
        "failure_reason": failure_reason if not is_captured else None,
        "failure_type": failure_type if not is_captured else None,
        "error_code": "GATEWAY_ERROR",
        "bank": random.choice(BANKS) if random.random() > 0.3 else None,
        "metadata": {
            "time_on_checkout_seconds": random.randint(5, 300) if failure_type == "CHECKOUT_ABANDONMENT" else 0,
            "page_views": random.randint(1, 8) if failure_type == "CHECKOUT_ABANDONMENT" else 1,
        },
        "created_at": created_at,
        "updated_at": created_at + timedelta(minutes=random.randint(1, 30)),
    }


def _inline_score(payment: dict, customer: dict, retry_attempts: int) -> tuple:
    """Inline scoring — no app imports required."""
    total = customer.get("total_payments", 0)
    successful = customer.get("successful_payments", 0)
    ch = (successful / total + min(0.1, total / 100)) if total > 0 else 0.5
    FT_SCORES = {
        "TEMPORARY_BANK_FAILURE": 0.90, "NETWORK_TIMEOUT": 0.85,
        "PAYMENT_METHOD_FAILURE": 0.65, "CUSTOMER_ACTION_REQUIRED": 0.55,
        "MULTIPLE_FAILED_ATTEMPTS": 0.30, "CHECKOUT_ABANDONMENT": 0.60, "UNKNOWN": 0.40,
    }
    ft = FT_SCORES.get(payment.get("failure_type", "UNKNOWN"), 0.40)
    retry = max(0.1, 1.0 - retry_attempts * 0.35)
    amount_inr = payment.get("amount", 0) / 100
    tv = 0.85 if 500 <= amount_inr <= 50000 else (0.55 if amount_inr < 500 else 0.75)
    rec = 0.75
    raw = ch * 0.30 + ft * 0.25 + retry * 0.20 + tv * 0.15 + rec * 0.10
    if customer.get("opted_out"):
        raw = 0.0
    score = round(min(1.0, max(0.0, raw)), 4)
    return score, round(score * 0.95, 4)


def _get_priority(score: float) -> str:
    if score >= 0.75: return "HIGH"
    if score >= 0.50: return "MEDIUM"
    return "LOW"


def build_recovery_action(payment: dict, customer: dict) -> dict:
    """Generate a realistic recovery action result (self-contained)."""
    retry_attempts = random.randint(0, 2)
    score, prob = _inline_score(payment, customer, retry_attempts)
    failure_type = payment.get("failure_type", "UNKNOWN")
    if retry_attempts >= 2:
        failure_type = "MULTIPLE_FAILED_ATTEMPTS"

    if score < 0.40 or customer.get("opted_out"):
        action_type, status, amount_recovered = "STOP", "stopped", None
    elif failure_type in ("TEMPORARY_BANK_FAILURE", "NETWORK_TIMEOUT"):
        action_type = "DELAYED_RECOVERY"
        ok = random.random() < score
        status, amount_recovered = ("success", payment["amount"]) if ok else ("failed", None)
    elif failure_type == "CHECKOUT_ABANDONMENT":
        action_type = "PAYMENT_REMINDER"
        ok = random.random() < score * 0.8
        status, amount_recovered = ("success", payment["amount"]) if ok else ("failed", None)
    elif failure_type == "PAYMENT_METHOD_FAILURE":
        action_type = "ALTERNATE_PAYMENT_METHOD"
        ok = random.random() < score * 0.7
        status, amount_recovered = ("success", payment["amount"]) if ok else ("failed", None)
    elif failure_type == "MULTIPLE_FAILED_ATTEMPTS":
        action_type, status, amount_recovered = "ESCALATE", "stopped", None
    else:
        action_type = "RETRY_RECOVERY"
        ok = random.random() < score * 0.6
        status, amount_recovered = ("success", payment["amount"]) if ok else ("failed", None)

    policy_status = "APPROVED"
    if retry_attempts >= 2 and action_type not in ("STOP", "ESCALATE"):
        policy_status, status, amount_recovered = "DENIED", "blocked", None

    created_at = payment["created_at"] + timedelta(minutes=random.randint(5, 60))
    return {
        "action_id": f"act_{uuid.uuid4().hex[:12]}",
        "payment_id": payment["payment_id"],
        "customer_id": customer["customer_id"],
        "action_type": action_type,
        "recovery_probability": prob,
        "recovery_score": score,
        "root_cause": failure_type,
        "reason": f"Score {score:.2f} | {failure_type} | {retry_attempts} prior attempts",
        "priority": _get_priority(score),
        "confidence": round(0.70 + random.random() * 0.25, 4),
        "policy_status": policy_status,
        "policy_reason": "All checks passed" if policy_status == "APPROVED" else "Retry limit exceeded",
        "attempt_number": retry_attempts + 1,
        "status": status,
        "amount_original": payment["amount"],
        "amount_recovered": amount_recovered,
        "delay_minutes": 30 if action_type == "DELAYED_RECOVERY" else 0,
        "ai_decision": {"recommended_action": action_type, "recovery_probability": prob,
                        "confidence": 0.75, "reason": f"AI decision for {failure_type}"},
        "used_ai": random.random() > 0.1,
        "score_breakdown": {},
        "policy_checks": [],
        "created_at": created_at,
        "updated_at": created_at + timedelta(minutes=random.randint(1, 120)),
        "completed_at": created_at + timedelta(minutes=random.randint(30, 180)) if status in ("success", "failed") else None,
    }


async def generate_and_seed(
    count: int = 750,
    seed: int = 42,
    mongo_uri: str = "mongodb://localhost:27017/recoverflow",
):
    """Generate synthetic dataset and seed MongoDB."""
    random.seed(seed)
    import sys
    sys.path.insert(0, ".")

    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(mongo_uri)
    db_name = mongo_uri.split("/")[-1].split("?")[0] or "recoverflow"
    db = client[db_name]

    log.info("generating_dataset", count=count, seed=seed)

    # Build customer pool (15 profiles repeated)
    customers = []
    for i in range(count):
        profile = CUSTOMER_PROFILES[i % len(CUSTOMER_PROFILES)]
        customers.append(build_customer(profile, i))

    # Deduplicate customers by customer_id
    seen_customers = {}
    for c in customers:
        seen_customers[c["customer_id"]] = c
    unique_customers = list(seen_customers.values())

    # Upsert customers
    log.info("seeding_customers", count=len(unique_customers))
    for c in unique_customers:
        await db.customers.update_one(
            {"customer_id": c["customer_id"]},
            {"$set": c},
            upsert=True,
        )

    # Build payments
    payments = []
    for i in range(count):
        customer = customers[i]
        payment = build_payment(i, customer)
        payments.append((payment, customer))

    log.info("seeding_payments", count=len(payments))
    for payment, _ in payments:
        await db.payments.update_one(
            {"payment_id": payment["payment_id"]},
            {"$set": payment},
            upsert=True,
        )

    # Build recovery actions for failed payments
    recovery_actions = []
    for payment, customer in payments:
        if payment["status"] == "failed" and random.random() > 0.15:  # 85% have recovery actions
            action = build_recovery_action(payment, customer)
            recovery_actions.append(action)

    log.info("seeding_recovery_actions", count=len(recovery_actions))
    for action in recovery_actions:
        await db.recovery_actions.update_one(
            {"action_id": action["action_id"]},
            {"$set": action},
            upsert=True,
        )

    # Summary stats
    failed = sum(1 for p, _ in payments if p["status"] == "failed")
    captured = sum(1 for p, _ in payments if p["status"] == "captured")
    successful_recoveries = sum(1 for a in recovery_actions if a["status"] == "success")
    total_at_risk = sum(p["amount"] for p, _ in payments if p["status"] == "failed")
    total_recovered = sum(a.get("amount_recovered", 0) or 0 for a in recovery_actions if a["status"] == "success")

    print(f"\n{'='*60}")
    print(f"RecoverFlow AI -- Synthetic Dataset Generated")
    print(f"{'='*60}")
    print(f"Total transactions:    {count}")
    print(f"Failed payments:       {failed}")
    print(f"Captured payments:     {captured}")
    print(f"Revenue at risk:       Rs.{total_at_risk/100:,.2f}")
    print(f"Recovery actions:      {len(recovery_actions)}")
    print(f"Successful recoveries: {successful_recoveries}")
    print(f"Revenue recovered:     Rs.{total_recovered/100:,.2f}")
    print(f"Recovery rate:         {successful_recoveries/max(1,failed)*100:.1f}%")
    print(f"{'='*60}\n")

    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate RecoverFlow AI synthetic dataset")
    parser.add_argument("--count", type=int, default=750, help="Number of transactions (default: 750)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--mongo-uri", type=str, default="mongodb://localhost:27017/recoverflow", help="MongoDB URI")
    args = parser.parse_args()

    asyncio.run(generate_and_seed(
        count=args.count,
        seed=args.seed,
        mongo_uri=args.mongo_uri,
    ))
