from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from datetime import datetime
from configs.db import get_conn
from auth.auth import get_user
from logs.logging_config import logger

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationItem(BaseModel):
    id: str
    title: str
    created_at: datetime


class DeleteResponse(BaseModel):
    message: str


@router.get("", response_model=list[ConversationItem])
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn=Depends(get_conn),
    user=Depends(get_user),
):
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT id, title, created_at
            FROM conversations
            WHERE user_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            (user["id"], limit, offset),
        )
        conversations = await cur.fetchall()

    return [
        ConversationItem(
            id=str(convo["id"]),
            title=convo["title"] if convo["title"] else "New Chat",
            created_at=convo["created_at"],
        )
        for convo in conversations
    ]


@router.post(
    "/delete",
    status_code=status.HTTP_200_OK,
    response_model=DeleteResponse,
)
async def delete_conversation(
    conversation_id: str,
    conn=Depends(get_conn),
    user=Depends(get_user),
):
    try:
        async with conn.transaction():
            # Match the advisory lock used by /chat/ask. The transaction lock
            # waits for an active chat request and prevents a new one starting
            # until this deletion commits.
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (str(conversation_id),),
            )

            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id FROM conversations
                    WHERE id=%s AND user_id=%s
                    FOR UPDATE
                    """,
                    (conversation_id, user["id"]),
                )
                exists = await cur.fetchone()

                if not exists:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Conversation not found",
                    )

                await cur.execute(
                    "DELETE FROM documents WHERE conversation_id=%s",
                    (conversation_id,),
                )
                await cur.execute(
                    """
                    DELETE FROM conversations
                    WHERE id=%s AND user_id=%s
                    """,
                    (conversation_id, user["id"]),
                )

        logger.info(
            "Conversation %s deleted for user %s",
            conversation_id,
            user["id"],
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete conversation %s", conversation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Conversation deletion unsuccessful. Please try again.",
        )

    return DeleteResponse(message="Conversation deleted successfully")
