from jose import jwt,JWTError
import os
from datetime import datetime,timedelta,timezone
from fastapi import Cookie,HTTPException,Depends
import secrets
from dotenv import load_dotenv
load_dotenv()
from configs.db import get_conn
SECRET_KEY = os.getenv("JWT_SECRET")

ACCESS_TOKEN_MINUTES = 60
REFRESH_TOKEN_DAYS = 30

def create_token(user_id:str):
    expiry=datetime.now(timezone.utc)+timedelta(minutes=ACCESS_TOKEN_MINUTES)
    payload = {
    "sub": user_id,
    "exp": expiry
}

    return jwt.encode(payload,SECRET_KEY,algorithm='HS256')

def create_refresh_token()->str:
    return secrets.token_urlsafe(48)

async def get_user( access_token: str | None = Cookie(default=None),conn=Depends(get_conn)):

    if not access_token:
        raise HTTPException(status_code=401,detail="Not authenticated")
   
    try:
        payload=jwt.decode(access_token,SECRET_KEY,algorithms='HS256')
        user_id=payload['sub']
        if not user_id:
            raise HTTPException(status_code=401,detail="Invalid token payload")
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
    expires_at: datetime
):
    await conn.execute(
        """
        INSERT INTO refresh_tokens (user_id, token, expires_at)
        VALUES (%s, %s, %s)
        """,
        (user_id, token, expires_at),
    )


def refresh_token_expiry():
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)

