from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

pool = ConnectionPool(
    DATABASE_URL,
    min_size=1,
    max_size=10,
    kwargs={
        "row_factory": dict_row,
        "autocommit": True
    }
)

def get_conn():
    with pool.connection() as conn:
        yield conn
