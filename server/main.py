import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )


from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from chat.router import router as chat_router
from auth.router import router as auth_router
from configs.db import pool
from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    pool.close()
app = FastAPI(lifespan=lifespan)
app.include_router(chat_router)
app.include_router(auth_router)

@app.get("/")
def hello():
    return {"message": "Hello guys"}


