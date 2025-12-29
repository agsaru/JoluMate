import sys
import asyncio

# if sys.platform.startswith("win"):
#     asyncio.set_event_loop_policy(
#         asyncio.WindowsSelectorEventLoopPolicy()
#     )


from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from chat.router import router as chat_router
from auth.router import router as auth_router
from logs.logging_config import logger
from middlewares.log_requests import log_requests
from configs.db import pool
from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    await pool.open()
    yield
    await pool.close()
    logger.info("Database pool closed")
app = FastAPI(lifespan=lifespan)
app.middleware("http")(log_requests)
app.include_router(chat_router)
app.include_router(auth_router)

@app.get("/")
def hello():
    logger.info("Root endpoint hit")
    return {"message": "Hello guys"}
