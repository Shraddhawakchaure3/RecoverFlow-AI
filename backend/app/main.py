"""
RecoverFlow AI - FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.config import settings
from app.database.connection import connect_db, disconnect_db

# API Routers
from app.api.dashboard import router as dashboard_router
from app.api.opportunities import router as opportunities_router
from app.api.recovery import router as recovery_router
from app.api.audit import router as audit_router
from app.api.policies import router as policies_router
from app.api.evaluation import router as evaluation_router
from app.api.demo import router as demo_router
from app.webhooks.razorpay import router as webhook_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    log.info("recoverflow_starting", env=settings.app_env)
    await connect_db()
    log.info("recoverflow_ready")
    yield
    await disconnect_db()
    log.info("recoverflow_shutdown")


app = FastAPI(
    title="RecoverFlow AI",
    description="Autonomous AI Revenue Recovery Agent — Razorpay AI Buildathon 2026",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Global Error Handler ─────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc) if settings.app_env != "production" else "Contact support"},
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

app.include_router(dashboard_router, prefix="/api", tags=["Dashboard"])
app.include_router(opportunities_router, prefix="/api", tags=["Opportunities"])
app.include_router(recovery_router, prefix="/api", tags=["Recovery"])
app.include_router(audit_router, prefix="/api", tags=["Audit"])
app.include_router(policies_router, prefix="/api", tags=["Policies"])
app.include_router(evaluation_router, prefix="/api", tags=["Evaluation"])
app.include_router(demo_router, prefix="/api", tags=["Demo"])
app.include_router(webhook_router, prefix="/api", tags=["Webhooks"])


@app.get("/api/health", tags=["Health"])
async def health():
    """Health check endpoint."""
    from app.database.connection import get_db
    try:
        db = get_db()
        await db.command("ping")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok",
        "version": "1.0.0",
        "database": db_status,
        "razorpay": "configured" if settings.is_razorpay_configured else "mock_mode",
        "ai": "configured" if settings.is_ai_configured else "fallback_mode",
    }


@app.get("/", tags=["Root"])
async def root():
    return {"message": "RecoverFlow AI — Autonomous Revenue Recovery Agent", "docs": "/docs"}
