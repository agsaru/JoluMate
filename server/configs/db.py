from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

pool =AsyncConnectionPool(
    DATABASE_URL,
    min_size=1,
    max_size=10,
    open=False,
    kwargs={
        "row_factory": dict_row,
        "autocommit": True,
        "prepare_threshold": None, 
    }
)

async def get_conn():
   async with pool.connection() as conn:
        yield conn
