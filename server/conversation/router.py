from fastapi import APIRouter, Depends
from configs.db import get_conn
from auth.auth import get_user

router = APIRouter(prefix="/conversations", tags=["conversations"])
@router.post("/")
def create_conversation(
    conn=Depends(get_conn),
    user_id: str = Depends(get_user)
):
    row = conn.execute(
        """
        INSERT INTO conversations (user_id)
        VALUES (%s)
        RETURNING id
        """,
        (user_id,)
    ).fetchone()

    return {"conversation_id": row[0]}


@router.get("/")
def list_conversations(
    conn=Depends(get_conn),
    user_id: str = Depends(get_user)
):
    rows = conn.execute(
        """
        SELECT id, created_at
        FROM conversations
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (user_id,)
    ).fetchall()

    return [
        {"id": r[0], "created_at": r[1]}
        for r in rows
    ]
