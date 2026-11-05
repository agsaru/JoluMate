from fastapi import APIRouter, UploadFile, status, File, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from langchain_core.messages import HumanMessage
from slowapi import Limiter
from slowapi.util import get_remote_address
from configs.db import get_conn
from auth.auth import get_user
from logs.logging_config import logger
from agent.graph import workflow
from rag.utils import process_pdf

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/chat", tags=["chat"])

# --- Constants ---
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
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
    """Generate a readable title from the first message.

    Truncates at word boundaries up to MAX_TITLE_LENGTH characters,
    appending an ellipsis when truncated.
    """
    text = text.strip()
    # Use first sentence if short enough
    for delimiter in (".", "?", "!"):
        idx = text.find(delimiter)
        if 0 < idx <= MAX_TITLE_LENGTH:
            return text[: idx + 1]

    if len(text) <= MAX_TITLE_LENGTH:
        return text

    # Truncate at last word boundary
    truncated = text[:MAX_TITLE_LENGTH]
    last_space = truncated.rfind(" ")
    if last_space > MAX_TITLE_LENGTH // 2:
        truncated = truncated[:last_space]
    return truncated.rstrip() + "…"


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

    async with conn.cursor() as cur:
        await cur.execute(
            """
            INSERT INTO chats (conversation_id, role, content)
            VALUES (%s, %s, %s)
            """,
            (conversation_id, "user", message),
        )

    config = {
        "configurable": {
            "thread_id": conversation_id,
            "user_id": user["id"],
            "conversation_id": conversation_id,
        }
    }

    initial_state = HumanMessage(content=message)

    final_state = await workflow.ainvoke(
        {"messages": [initial_state]}, config=config
    )
    ai_response = final_state["messages"][-1].content

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
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT chats.role, chats.content, chats.created_at
            FROM chats
            INNER JOIN conversations
                ON conversations.id = chats.conversation_id
            WHERE chats.conversation_id = %s
              AND conversations.user_id = %s
            ORDER BY chats.created_at ASC
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
    user=Depends(get_user),
):
    if not conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="conversation_id required",
        )

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

    # --- Validate file type ---
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported",
        )

    # --- Read and validate size ---
    file_content = await file.read()

    if len(file_content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB",
        )

    # --- Validate PDF magic bytes ---
    if not file_content[:4].startswith(PDF_MAGIC_BYTES):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File does not appear to be a valid PDF",
        )

    chunks = await process_pdf(file_content, user["id"], conversation_id)

    return UploadResponse(
        message="PDF processed successfully",
        chunks_processed=chunks or 0,
    )
