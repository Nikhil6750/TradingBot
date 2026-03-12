from __future__ import annotations

import os
import sys
from pydantic import BaseModel
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# Ensure repository root is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

app = FastAPI(title="AlgoTradeX API", version="2.0.0")

# ── CORS Middleware ─────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup: initialise DB tables ─────────────────────────────────────────────
from backend.database.database import init_db
@app.on_event("startup")
def on_startup():
    init_db()

# ── Routers ───────────────────────────────────────────────────────────────────
from backend.api.replay_routes import router as replay_router
from backend.api.backtest_routes import router as backtest_router
from backend.api.setup_routes import router as setup_router

app.include_router(replay_router)
app.include_router(backtest_router)
app.include_router(setup_router)

# ── Exception Handlers ────────────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid input", "details": exc.errors()},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    detail = exc.detail
    msg = detail if isinstance(detail, str) else str(detail)
    return JSONResponse(status_code=exc.status_code, content={"error": msg})

@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": str(exc)})

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

from backend.api.strategy_routes import router as strategy_router
from backend.api.market_data_routes import router as market_data_router
from backend.api.session_routes import router as session_router
# from backend.api.symbol_routes import router as symbol_router

app.include_router(strategy_router)
app.include_router(market_data_router)
from backend.api.dataset_routes import router as dataset_router
app.include_router(dataset_router)
app.include_router(session_router)
# app.include_router(symbol_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.server:app", host="127.0.0.1", port=8000, reload=True)
