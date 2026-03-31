"""
WealthOS FastAPI Backend
GET  /health    — health check / Render warm-up ping
POST /insights  — pandas analytics on user transactions
POST /chat      — Groq Llama 3.3 streaming finance assistant
"""
import os
import sys
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

# ── Startup env validation ─────────────────────────────────────────────────────
REQUIRED = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GROQ_API_KEY"]
missing  = [k for k in REQUIRED if not os.getenv(k)]
if missing:
    sys.exit(f"ERROR: missing env vars: {', '.join(missing)}")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from  import insights, chat
from app.routers import insights, chat
from app.core import config
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ WealthOS API ready")
    yield


app = FastAPI(
    title="WealthOS API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENVIRONMENT", "development") == "development" else None,
    redoc_url=None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [o.strip() for o in _origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(insights.router, prefix="/insights", tags=["insights"])
app.include_router(chat.router,     prefix="/chat",     tags=["chat"])


@app.get("/health", tags=["health"])
async def health():
    """Render health check and pre-warm endpoint. Call this before the first real request."""
    return {"status": "ok", "service": "wealthos-api"}


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "WealthOS API", "docs": "/docs"}