from fastapi import APIRouter, HTTPException, Depends, Response, Cookie, status
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone

from configs.db import get_conn
from auth.hash import hash_password, verify_password
from auth.auth import (
    create_token,
    create_refresh_token,
    store_refresh_token,
    get_user,
    refresh_token_expiry,
)
from logs.logging_config import logger

router = APIRouter(prefix="/auth", tags=["auth"])

class SignUpData(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginData(BaseModel):
    email: EmailStr
    password: str

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(data: SignUpData, conn=Depends(get_conn)):
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT 1 FROM users WHERE email=%s",
            (data.email,),
        )
        user = await cur.fetchone()

    if user:
        logger.warning(f"Signup failed: email exists {data.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    hashed = hash_password(data.password)

    try:
        await conn.execute(
            """
            INSERT INTO users (name, email, hashed_password)
            VALUES (%s, %s, %s)
            """,
            (data.name, data.email, hashed),
        )
        logger.info(f"User created successfully: {data.email}")
        return {"message": "User Created"}

    except Exception:
        logger.exception("Signup failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System error",
        )

@router.post("/login")
async def login(data: LoginData,response:Response, conn=Depends(get_conn)):
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT id, hashed_password FROM users WHERE email=%s",
            (data.email,),
        )
        user = await cur.fetchone()

    if not user or not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_token(str(user["id"]))
    refresh_token = create_refresh_token()

    await store_refresh_token(
        conn,
        str(user["id"]),
        refresh_token,
        refresh_token_expiry(),
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60,
    )
    response.set_cookie(
    "refresh_token",
    refresh_token,
    httponly=True,
    samesite="lax",
    max_age=60 * 60 * 24 * 30,
)

    return {
        "access_token": access_token
    }

@router.post("/refresh")
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    conn=Depends(get_conn),
):
    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")

    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT user_id, expires_at
            FROM refresh_tokens
            WHERE token=%s
            """,
            (refresh_token,),
        )
        data = await cur.fetchone()

    if not data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    if data["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expired")

    await conn.execute(
        "DELETE FROM refresh_tokens WHERE token=%s",
        (refresh_token,),
    )

    new_access = create_token(str(data["user_id"]))
    new_refresh = create_refresh_token()

    await store_refresh_token(
        conn,
        str(data["user_id"]),
        new_refresh,
        refresh_token_expiry(),
    )

    response.set_cookie(
        "access_token",
        new_access,
        httponly=True,
        samesite="lax",
        max_age=3600,
    )
    response.set_cookie(
        "refresh_token",
        new_refresh,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )

    return {"message": "Session refreshed"}

@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    conn=Depends(get_conn),
):
    if refresh_token:
        await conn.execute(
            "DELETE FROM refresh_tokens WHERE token=%s",
            (refresh_token,),
        )

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return {"message": "Logged out"}


@router.get("/me")
async def me(current_user=Depends(get_user)):
    return {
        "id": current_user["id"],
        "name": current_user["name"],
        "email": current_user["email"],
    }