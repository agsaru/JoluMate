from fastapi import APIRouter,HTTPException,Depends,Response, Cookie
from configs.db import get_conn
from auth.hash import hash_password,verify_password
from auth.auth import create_token,create_refresh_token,store_refresh_token,refresh_token_expiry
from datetime import timezone,datetime
from pydantic import BaseModel
router=APIRouter(
    prefix='/auth',
    tags=["auth"]
)
class SignUpData(BaseModel):
    name:str
    email:str
    password:str

@router.post("/signup")
def signup( data:SignUpData,conn=Depends(get_conn)):
    hashed=hash_password(data.password)
    print("com")
    try:
        
        conn.execute(
            """
             INSERT INTO users (name,email,hashed_password) VALUES(%s, %s,%s)
            """,
            (data.name,data.email,hashed)
        )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500,detail="System error")
    return {"message":"User Created"}

@router.post('/login')
def login(email:str,password:str, conn=Depends(get_conn)):
    user = conn.execute(
    "SELECT id, hashed_password FROM users WHERE email=%s",
    (email,)
     ).fetchone()
    is_valid=verify_password(password,user["hashed_password"])
    if not user or not is_valid:
        raise HTTPException(401,"Invalid email or password")
    access_token=create_token(str(user['id']))
    refresh_token=create_refresh_token()
    store_refresh_token(
        conn,
        str(user['id']),
        refresh_token,
        refresh_token_expiry()
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }

@router.post('/refresh')
def refresh(response: Response,refresh_token: str | None = Cookie(default=None),conn=Depends(get_conn)):
    if not refresh_token:
        raise HTTPException(401, "Missing refresh token")
    data=conn.fetchrow(
        """
       SELECT user_id,expires_at
       FROM refresh_tokens
       WHERE token=%s
        """
        (refresh_token,)
    )
    if not data:
        raise HTTPException(401,"Invalid refresh token")
    if data['expires_at']<datetime.now(timezone.utc):
        raise HTTPException(401,"Refresh token expired")
    conn.execute(
        "DELETE FROM refresh_tokens WHERE token=%s",
        (refresh_token,)
    )

    new_access = create_token(str(data["user_id"]))
    new_refresh = create_refresh_token()

    store_refresh_token(
        conn,
        str(data["user_id"]),
        new_refresh,
        refresh_token_expiry()
    )

    response.set_cookie(
        "access_token",
        new_access,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60
    )

    response.set_cookie(
        "refresh_token",
        new_refresh,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 30
    )

    return {"message": "Session refreshed"}



router.post("/logout")
def logout( response: Response,
    refresh_token: str | None = Cookie(default=None),
    conn=Depends(get_conn)):
   if refresh_token:
        conn.execute( 
            "DELETE FROM refresh_tokens WHERE token =%s",
            (refresh_token,)
        )
   response.delete_cookie("access_token")
   response.delete_cookie("refresh_token")
   return {"message": "Logged out"}