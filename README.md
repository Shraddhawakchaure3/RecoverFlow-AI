# RecoverFlow AI

**Autonomous AI Revenue Recovery Agent** — Razorpay AI Buildathon 2026, Track 03

> "AI decides what to recommend. Policies decide what is allowed. Razorpay executes the permitted action. Webhooks tell us what happened. The audit trail records everything."

---

## What It Does

RecoverFlow AI detects revenue at risk (failed payments, checkout abandonment), diagnoses root causes, calculates a transparent recovery score, asks an AI agent (Gemini/OpenAI) for a recommendation, passes that recommendation through a deterministic policy/guardrail engine, executes only the permitted recovery actions via Razorpay Test Mode, and records a full audit trail.

**The AI never directly executes financial actions.** Every recommended action is validated by hardcoded policy rules before execution.

---

## Core Workflow

```
Revenue Event (Razorpay Webhook / Synthetic Data)
      ↓
Revenue Risk Detection (payment.failed / checkout.abandoned)
      ↓
Root Cause Diagnosis  (bank failure, timeout, method failure, etc.)
      ↓
Recovery Score        (transparent weighted 0–1 score)
      ↓
AI Decision Agent     (Gemini/OpenAI → structured JSON recommendation)
      ↓
Policy / Guardrail Engine  (MAX_RETRIES, MIN_SCORE, OPT-OUT, etc.)
      ↓
Allowed Recovery Action    (Razorpay Test Mode order/payment)
      ↓
Webhook Result Observer    (payment.captured / payment.failed)
      ↓
Audit Log                  (every step recorded with reasoning)
      ↓
Evaluation Dashboard       (baseline vs AI comparison)
```

---

## Architecture

```
                     Browser
                        │
                        ▼
              ┌──────────────────┐
              │  React + Vite    │
              │  :5173           │
              └────────┬─────────┘
                       │ /api → proxy
                       ▼
              ┌──────────────────┐
              │  FastAPI         │
              │  :8000           │
              └──┬───────────┬───┘
                 │           │
                 ▼           ▼
          MongoDB       Gemini API /
          :27017         Razorpay Test
```

---

## Recovery Score

Transparent weighted scoring (never random):

| Factor | Weight | Description |
|---|---|---|
| Customer History | 30% | Previous successful payments / total |
| Failure Type | 25% | Temporary failures score higher |
| Retry History | 20% | Fewer prior retries = better chances |
| Transaction Value | 15% | Mid-range amounts score highest |
| Recency | 10% | Recent payment activity |

Example output:
```json
{
  "score": 0.82,
  "probability": 0.78,
  "explanation": "Strong customer history (8/10 successful), temporary bank failure, first retry attempt",
  "feature_scores": {
    "customer_history": 0.85,
    "failure_type": 0.90,
    "retry_history": 1.00,
    "transaction_value": 0.85,
    "recency": 0.75
  }
}
```

---

## AI Decision Agent

Uses Gemini (via OpenAI-compatible endpoint) or any OpenAI-compatible LLM. Falls back to deterministic rules if the LLM is unavailable.

**Allowed actions the AI can recommend:**
- `RETRY_RECOVERY` — Immediate retry
- `DELAYED_RECOVERY` — Retry after N minutes
- `CHECKOUT_RECOVERY` — New checkout link
- `PAYMENT_REMINDER` — Customer reminder
- `ALTERNATE_PAYMENT_METHOD` — Suggest alternate method
- `ESCALATE` — Human review
- `STOP` — Do not attempt recovery

**The AI never directly executes financial actions.**

---

## Policy / Guardrail Engine

Hardcoded safety rules that gate every AI recommendation:

| Rule | Default | Description |
|---|---|---|
| `MAX_RETRIES` | 2 | Block if payment has been retried ≥ 2 times |
| `MAX_RECOVERY_ACTIONS` | 3 | Block if ≥ 3 recovery actions already attempted |
| `MIN_RECOVERY_SCORE` | 0.40 | Block if score below threshold |
| `MAX_TRANSACTION_AMOUNT` | ₹10,000 | Block recovery above this amount |
| Customer opt-out | — | Always stops |
| Already captured | — | Always stops |

When an AI recommendation is blocked:
```
AI recommends: RETRY_RECOVERY
Policy check: MAX_RETRIES exceeded (3 ≥ 2)
Policy decision: BLOCKED
Audit record: recorded
Financial action: NONE
```

---

## Demo Scenarios

Available at `/demo` in the UI — each runs the full backend pipeline:

| Scenario | Description |
|---|---|
| High Recovery Success | Temporary bank failure → AI recommends retry → Policy approves → Razorpay order created |
| Low Recovery → STOP | Multiple failures → low score → AI recommends STOP → no action |
| Retry Limit Reached | Good score but `MAX_RETRIES` → policy blocks |
| Checkout Abandonment | Customer left checkout → reminder recovery |
| Duplicate Webhook | Same event twice → idempotency correctly rejects second |
| Payment Success → Stop | Already captured → recovery cancelled |
| Policy Block | High amount exceeds `MAX_TRANSACTION_AMOUNT` → blocked |

---

## Project Structure

```
RecoverFlow AI/
├── backend/
│   ├── app/
│   │   ├── agents/decision.py       # AI decision agent (Gemini/OpenAI + fallback)
│   │   ├── api/
│   │   │   ├── dashboard.py         # Command center metrics
│   │   │   ├── opportunities.py     # Failed payment list
│   │   │   ├── recovery.py          # Analyze + execute recovery
│   │   │   ├── audit.py             # Audit trail retrieval
│   │   │   ├── evaluation.py        # Batch evaluation (baseline vs AI)
│   │   │   ├── demo.py              # Controlled demo scenarios
│   │   │   └── policies.py          # Policy config management
│   │   ├── database/connection.py   # MongoDB async connection
│   │   ├── models/models.py         # Pydantic schemas
│   │   ├── policies/engine.py       # Guardrail policy engine
│   │   ├── services/
│   │   │   ├── recovery.py          # Main recovery workflow orchestrator
│   │   │   ├── scoring.py           # Transparent recovery scoring
│   │   │   ├── root_cause.py        # Failure root cause analysis
│   │   │   ├── audit.py             # Audit log writer
│   │   │   └── payment_provider.py  # Razorpay / Mock abstraction
│   │   ├── webhooks/razorpay.py     # Razorpay webhook handler
│   │   ├── config.py                # Pydantic settings
│   │   └── main.py                  # FastAPI entrypoint
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── .env                         # ← gitignored, never committed
│   └── .env.example                 # ← safe template to commit
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── CommandCenter.jsx    # Live dashboard
│   │   │   ├── Opportunities.jsx    # Failed payments table
│   │   │   ├── AIDecision.jsx       # Per-payment AI decision view
│   │   │   ├── AuditTrail.jsx       # Audit log timeline
│   │   │   ├── Evaluation.jsx       # Baseline vs AI comparison
│   │   │   ├── DemoScenarios.jsx    # One-click scenario runner
│   │   │   └── Policies.jsx         # Policy config editor
│   │   ├── components/
│   │   ├── services/api.js          # Axios API layer
│   │   └── utils/format.js          # INR formatting, badges
│   ├── Dockerfile
│   ├── .dockerignore
│   └── vite.config.js
├── data/
│   └── generate_dataset.py          # Synthetic 750-tx dataset generator
├── docker-compose.yml
├── .gitignore
└── LICENSE
```

---

## Quick Start — Local Development (No Docker)

**Prerequisites:** Python 3.11+, Node 20+, MongoDB running on localhost:27017

```bash
# 1. Clone and set up backend
cd backend
cp .env.example .env
# Edit .env — add your Gemini API key and Razorpay Test keys

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Seed the database (new terminal)
cd ../data
python generate_dataset.py --count 750

# 3. Start frontend (new terminal)
cd ../frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## Quick Start — Docker

**Prerequisites:** Docker Desktop

```bash
# 1. Set up environment
cp backend/.env.example backend/.env
# Edit backend/.env — add credentials

# 2. Build and start everything
docker compose up --build

# Or detached:
docker compose up -d --build
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- MongoDB: localhost:27017

```bash
# Useful commands
docker compose ps                    # check status
docker compose logs -f               # tail all logs
docker compose logs -f backend       # backend only
docker compose down                  # stop
docker compose down -v               # stop + remove volumes
```

**Seed the database inside Docker:**
```bash
docker compose exec backend python -c "
import asyncio, sys
sys.path.insert(0, '.')
"
# Or run the generator locally pointing to Docker's MongoDB:
python data/generate_dataset.py --mongo-uri mongodb://localhost:27017/recoverflow
```

---

## Environment Variables

All env vars go in `backend/.env` (copy from `backend/.env.example`).

| Variable | Required | Description |
|---|---|---|
| `RAZORPAY_KEY_ID` | For live Razorpay | Test mode key from dashboard |
| `RAZORPAY_KEY_SECRET` | For live Razorpay | Test mode secret |
| `RAZORPAY_WEBHOOK_SECRET` | For webhooks | Webhook signature verification |
| `AI_API_KEY` | For AI agent | Gemini or OpenAI API key |
| `AI_BASE_URL` | Optional | Defaults to Gemini endpoint |
| `AI_MODEL` | Optional | Defaults to `gemini-1.5-flash` |
| `MONGODB_URI` | Yes | MongoDB connection string |
| `FRONTEND_URL` | Yes | CORS origin for frontend |
| `MAX_RETRIES` | Optional | Policy: max retry attempts (default 2) |
| `MIN_RECOVERY_SCORE` | Optional | Policy: minimum score (default 0.40) |

**Without any credentials**, the system runs in:
- **Mock payment mode** — simulates Razorpay orders locally
- **Deterministic AI mode** — rule-based fallback instead of LLM

---

## Gemini Setup

1. Get API key from [Google AI Studio](https://aistudio.google.com/apikey)
2. In `backend/.env`:
```
AI_API_KEY=your-gemini-api-key
AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
AI_MODEL=gemini-1.5-flash
```

The backend uses the OpenAI SDK pointed at Gemini's OpenAI-compatible endpoint.

---

## Razorpay Test Mode Setup

1. Create account at [razorpay.com](https://razorpay.com) (free)
2. Go to Dashboard → Settings → API Keys → **Test Mode**
3. Copy Key ID and Key Secret to `backend/.env`
4. For webhooks, use [ngrok](https://ngrok.com) to expose local port 8000:
   ```bash
   ngrok http 8000
   # Set webhook URL in Razorpay dashboard:
   # https://your-ngrok-url.ngrok.io/api/webhooks/razorpay
   ```
5. Copy Webhook Secret from Razorpay dashboard to `backend/.env`

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/dashboard/summary` | Command center metrics |
| GET | `/api/opportunities` | Failed payment opportunities |
| GET | `/api/opportunities/{id}` | Single opportunity with audit trail |
| POST | `/api/recovery/{id}/analyze` | Run AI analysis on a payment |
| POST | `/api/recovery/{id}/execute` | Execute recovery action |
| GET | `/api/audit` | Audit log with filtering |
| GET | `/api/evaluation` | Batch evaluation results |
| GET | `/api/policies` | Current policy config |
| PUT | `/api/policies` | Update policy config |
| GET | `/api/demo/scenarios` | List demo scenarios |
| POST | `/api/demo/scenario` | Run a demo scenario |
| POST | `/api/webhooks/razorpay` | Razorpay webhook endpoint |

Full docs: http://localhost:8000/docs

---

## Evaluation

The evaluation compares two strategies on the same dataset:

**Baseline:** Fixed retry for all failed payments (no intelligence)  
**RecoverFlow AI:** Score → AI decision → Policy gate → Selective action

Metrics reported:
- Revenue recovered (INR)
- Recovery rate (%)
- Successful recovery count
- Policy blocks (unsafe actions prevented)
- Stopped cases (AI chose not to intervene)
- Unnecessary interventions avoided

Results are computed from real seeded data — not hardcoded.

---

## Security

- `backend/.env` is gitignored and never committed
- `RAZORPAY_KEY_SECRET` never reaches the frontend
- Webhook signatures validated with HMAC-SHA256 before any processing
- Webhook idempotency prevents duplicate recovery actions
- AI output is validated with Pydantic before the policy engine sees it
- The policy engine is deterministic and cannot be overridden by LLM output

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + Vite 8 + Tailwind CSS v4 |
| Charts | Recharts |
| Backend | FastAPI 0.115 + Python 3.11 |
| Database | MongoDB 8 (Motor async driver) |
| AI | Gemini 1.5 Flash (via OpenAI-compatible SDK) |
| Payments | Razorpay Test Mode |
| Container | Docker + Docker Compose |

---

*RecoverFlow AI — Track 03, Razorpay AI Buildathon 2026*
