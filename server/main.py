import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from chat.router import router as chat_router
from auth.router import router as auth_router
from conversation.router import router as conv_router
from logs.logging_config import logger
from middlewares.log_requests import log_requests
from configs.db import pool
from agent.graph import checkpointer

load_dotenv()

# --- Rate Limiter ---
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    await pool.open()
    await checkpointer.setup()
    logger.info("Database pool opened and checkpointer initialized")
    yield
    await pool.close()
    logger.info("Database pool closed")


app = FastAPI(lifespan=lifespan)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS ---
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Middleware & Routers ---
app.middleware("http")(log_requests)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(conv_router)


@app.get("/")
async def health_check():
    pool_status = "healthy" if pool._opened else "unavailable"
    logger.info("Health check endpoint hit")
    return {
        "status": "ok",
        "database": pool_status,
    }
