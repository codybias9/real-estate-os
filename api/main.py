from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, text
import os

app = FastAPI()

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
