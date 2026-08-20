from jose import jwt, JWTError
import os
from datetime import datetime, timedelta, timezone
from fastapi import Cookie, HTTPException, Depends
import secrets
from dotenv import load_dotenv

load_dotenv()

from configs.db import get_conn
from logs.logging_config import logger

SECRET_KEY = os.getenv("JWT_SECRET")

ACCESS_TOKEN_MINUTES = 60
REFRESH_TOKEN_DAYS = 30
MAX_REFRESH_TOKENS_PER_USER = 5


def create_token(user_id: str):
    expiry = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    payload = {
        "sub": user_id,
        "exp": expiry,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


async def get_user(
    access_token: str | None = Cookie(default=None),
    conn=Depends(get_conn),
):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms="HS256")
        user_id = payload["sub"]
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT id, name, email FROM users WHERE id=%s",
            (user_id,),
        )
        user = await cur.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def store_refresh_token(
    conn,
    user_id: str,
    token: str,
    expires_at: datetime,
):
    """Store a new refresh token and clean up old/expired ones.

    - Deletes any expired tokens for this user.
    - If the user has MAX_REFRESH_TOKENS_PER_USER or more active tokens,
      deletes the oldest ones to stay within the limit.
    """
    # 1. Delete expired tokens
    await conn.execute(
        "DELETE FROM refresh_tokens WHERE user_id = %s AND expires_at < %s",
        (user_id, datetime.now(timezone.utc)),
    )

    # 2. Enforce per-user token limit — keep only the newest (limit - 1)
    #    so the new token we're about to insert makes it exactly at the limit.
    await conn.execute(
        """
        DELETE FROM refresh_tokens
        WHERE id IN (
            SELECT id FROM refresh_tokens
            WHERE user_id = %s
            ORDER BY created_at DESC
            OFFSET %s
        )
        """,
        (user_id, MAX_REFRESH_TOKENS_PER_USER - 1),
    )

    # 3. Insert the new token
    await conn.execute(
        """
        INSERT INTO refresh_tokens (user_id, token, expires_at)
        VALUES (%s, %s, %s)
        """,
        (user_id, token, expires_at),
    )

    logger.info(f"Refresh token stored for user {user_id}")


def refresh_token_expiry():
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)
