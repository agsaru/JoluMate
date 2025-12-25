from jose import jwt
import os
from datetime import datetime,timedelta,timezone
from fastapi import Cookie,HTTPException
import secrets
SECRET_KEY = os.getenv("JWT_SECRET")

ACCESS_TOKEN_MINUTES = 60
REFRESH_TOKEN_DAYS = 30

def create_token(user_id:str):
    expiry=datetime.now(timezone.utc)+timedelta(minutes=ACCESS_TOKEN_MINUTES)
    playload={
        'sub':user_id,
        'expiry':str(expiry)
    }
    return jwt.encode(playload,SECRET_KEY,algorithm='HS256')

def create_refresh_token()->str:
    return secrets.token_urlsafe(48)

def get_user( access_token: str | None = Cookie(default=None)):

    if not access_token:
        raise HTTPException(status_code=401,detail="Not authenticated")
   
    try:
        playload=jwt.decode(access_token,SECRET_KEY,algorithms='HS256')
        return playload['sub']
    except Exception:
        raise HTTPException(status_code=401,detail="Invalid or expired token")

def store_refresh_token(conn, user_id: str, token: str, expires_at:datetime):
    conn.execute(
        """
        INSERT INTO refresh_tokens (id, token, expires_at)
        VALUES (%s, %s, %s)
        """,
        (user_id, token, expires_at)
    )


def refresh_token_expiry():
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)