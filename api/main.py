from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import os

# Import auth configuration and middleware
from app.auth.config import CORS_ORIGINS, ENABLE_HSTS, RATE_LIMIT_PER_MINUTE, RATE_LIMIT_PER_TENANT_MINUTE
from app.middleware import RateLimitMiddleware, SecurityHeadersMiddleware

# Import observability (PR#4)
from app.observability import setup_tracing, setup_metrics, setup_logging, setup_sentry

app = FastAPI(
    title="Real Estate OS API",
    description="RESTful API for Real Estate Operating System",
    version="1.0.0"
)

# Setup observability (PR#4)
setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
setup_tracing(app)
setup_metrics(app)
setup_sentry(app)

# Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware, enable_hsts=ENABLE_HSTS)

# Rate Limiting Middleware
app.add_middleware(
    RateLimitMiddleware,
    per_ip_limit=RATE_LIMIT_PER_MINUTE,
    per_tenant_limit=RATE_LIMIT_PER_TENANT_MINUTE
)

# CORS middleware (production-ready with allowlist)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # Production allowlist from env
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit-IP", "X-RateLimit-Remaining-IP"],
)

# Include routers
from app.routers import properties, outreach, auth

app.include_router(auth.router)  # Auth endpoints (no auth required)
app.include_router(properties.router)
app.include_router(outreach.router)

# Health endpoint
@app.get("/healthz")
def health():
    return {"status": "ok"}

# Ping endpoint that uses DB_DSN
@app.get("/ping")
def ping():
    dsn = os.getenv("DB_DSN")
    if not dsn:
        raise HTTPException(500, "DB_DSN not set")
    engine = create_engine(dsn)
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS ping (id serial PRIMARY KEY, ts timestamptz DEFAULT now())"
        ))
        conn.execute(text("INSERT INTO ping DEFAULT VALUES"))
        count = conn.execute(text("SELECT count(*) FROM ping")).scalar()
    return {"ping_count": count}
