from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import os

# Import routers
from api.routers import auth

app = FastAPI(
    title="Real Estate OS API",
    description="API for Real Estate Operating System",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)

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
