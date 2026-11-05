from fastapi import APIRouter, UploadFile, status, File, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager
from uuid import UUID
from langchain_core.messages import HumanMessage
from slowapi import Limiter
from slowapi.util import get_remote_address
from configs.db import get_conn, pool
from auth.auth import get_user
from logs.logging_config import logger
from agent.graph import workflow
from rag.utils import process_pdf

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/chat", tags=["chat"])

# --- Constants ---
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_MESSAGE_LENGTH = 4000
PDF_MAGIC_BYTES = b"%PDF"
MAX_TITLE_LENGTH = 40


# --- Request / Response Models ---
class MessageData(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class AskResponse(BaseModel):
    conversation_id: str
    message: str


class ChatMessage(BaseModel):
    role: str
    message: str
    created_at: datetime


class UploadResponse(BaseModel):
    message: str
    chunks_processed: int


# --- Helpers ---
def generate_title(text: str) -> str:
    """Generate a readable title from the first message."""
    text = text.strip()
    for delimiter in (".", "?", "!"):
        idx = text.find(delimiter)
        if 0 < idx <= MAX_TITLE_LENGTH:
            return text[: idx + 1]

    if len(text) <= MAX_TITLE_LENGTH:
        return text

    truncated = text[:MAX_TITLE_LENGTH]
    last_space = truncated.rfind(" ")
    if last_space > MAX_TITLE_LENGTH // 2:
        truncated = truncated[:last_space]
    return truncated.rstrip() + "…"


def validate_conversation_id(conversation_id: str) -> str:
    try:
        return str(UUID(conversation_id))
    except (AttributeError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation_id",
        )


@asynccontextmanager
async def conversation_lock(conversation_id: str):
    """Serialize operations on one conversation across API workers."""
    async with pool.connection() as lock_conn:
        await lock_conn.execute(
            "SELECT pg_advisory_lock(hashtextextended(%s, 0))",
            (str(conversation_id),),
        )
        try:
            yield
        finally:
            await lock_conn.execute(
                "SELECT pg_advisory_unlock(hashtextextended(%s, 0))",
                (str(conversation_id),),
            )


# --- Endpoints ---
@router.post("/ask", response_model=AskResponse)
@limiter.limit("10/minute")
async def get_ans(
    request: Request,
    data: MessageData,
    conn=Depends(get_conn),
    user=Depends(get_user),
):
    message = data.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query cannot be empty",
        )

    if len(message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Message too long. Maximum length is {MAX_MESSAGE_LENGTH} characters.",
        )

    conversation_id = data.conversation_id

    if conversation_id is None:
        title = generate_title(message)
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO conversations(user_id, title)
                VALUES(%s, %s)
                RETURNING id
                """,
                (user["id"], title),
            )
            row = await cur.fetchone()
            conversation_id = row["id"]
            logger.info(
                f"Conversation created {conversation_id} for user {user['id']}"
            )
    else:
        conversation_id = validate_conversation_id(conversation_id)

    async with conversation_lock(conversation_id):
        # Recheck ownership after acquiring the lock. The conversation may
        # have been deleted while this request was waiting.
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id FROM conversations
                WHERE id=%s AND user_id=%s
                """,
                (conversation_id, user["id"]),
            )
            row = await cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found",
                )

            await cur.execute(
                """
                INSERT INTO chats (conversation_id, role, content)
                VALUES (%s, %s, %s)
                """,
                (conversation_id, "user", message),
            )

        config = {
            "configurable": {
                "thread_id": str(conversation_id),
                "user_id": user["id"],
                "conversation_id": str(conversation_id),
            }
        }

        try:
            final_state = await workflow.ainvoke(
                {"messages": [HumanMessage(content=message)]},
                config=config,
            )
            ai_response = final_state["messages"][-1].content
            if not isinstance(ai_response, str):
                ai_response = str(ai_response)
        except Exception:
            logger.exception(
                "AI response generation failed for conversation %s",
                conversation_id,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="JoluMate couldn't generate a response. Your message was saved; please try again.",
            )

        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO chats (conversation_id, role, content)
                VALUES (%s, %s, %s)
                """,
                (conversation_id, "assistant", ai_response),
            )

    return AskResponse(
        conversation_id=str(conversation_id),
        message=ai_response,
    )


@router.get("/{conversation_id}", response_model=list[ChatMessage])
async def get_chat_history(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    conn=Depends(get_conn),
    user=Depends(get_user),
):
    conversation_id = validate_conversation_id(conversation_id)

    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT id FROM conversations
            WHERE id=%s AND user_id=%s
            """,
            (conversation_id, user["id"]),
        )
        conversation = await cur.fetchone()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        await cur.execute(
            """
            SELECT chats.role, chats.content, chats.created_at
            FROM chats
            INNER JOIN conversations
                ON conversations.id = chats.conversation_id
            WHERE chats.conversation_id = %s
              AND conversations.user_id = %s
            ORDER BY chats.created_at ASC, chats.id ASC
            LIMIT %s OFFSET %s
            """,
            (conversation_id, user["id"], limit, offset),
        )
        messages = await cur.fetchall()

    return [
        ChatMessage(
            role=msg["role"],
            message=msg["content"],
            created_at=msg["created_at"],
        )
        for msg in messages
    ]


@router.post("/upload", response_model=UploadResponse)
@limiter.limit("5/minute")
async def upload_file(
    request: Request,
    conversation_id: str,
    file: UploadFile = File(...),
    conn=Depends(get_conn),
    user=Depends(get_user),
):
    if not conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="conversation_id required",
        )

    conversation_id = validate_conversation_id(conversation_id)

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported",
        )

    # Read in bounded chunks so oversized uploads are rejected without
    # loading the entire file into memory.
    file_content = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        file_content.extend(chunk)
        if len(file_content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB",
            )

    if not bytes(file_content[:4]).startswith(PDF_MAGIC_BYTES):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File does not appear to be a valid PDF",
        )

    async with conversation_lock(conversation_id):
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id FROM conversations
                WHERE id=%s AND user_id=%s
                """,
                (conversation_id, user["id"]),
            )
            conversation = await cur.fetchone()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        try:
            chunks = await process_pdf(bytes(file_content), user["id"], conversation_id)
        except Exception:
            logger.exception(
                "PDF processing failed for conversation %s", conversation_id
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="We couldn't read this PDF. Please check that it is a valid, text-based PDF.",
            )

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No searchable text was found in this PDF. Scanned or image-only PDFs are not supported.",
        )

    return UploadResponse(
        message="PDF processed successfully",
        chunks_processed=chunks,
    )
