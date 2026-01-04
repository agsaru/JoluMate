from fastapi import APIRouter, UploadFile,status, File, Depends, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage 
from configs.db import get_conn
from auth.auth import get_user
from logs.logging_config import logger
from agent.graph import workflow
from rag.utils import process_pdf

router = APIRouter(
    prefix='/chat',
    tags=['chat']
)

class MessageData(BaseModel):
    message: str
    conversation_id: str | None = None

def generate_title(text: str):
    if len(text.strip()) <= 20:
        return text
    else:
        return text[:20]

@router.post('/ask')
async def get_ans(data: MessageData, conn=Depends(get_conn), user=Depends(get_user)):
    
    message = data.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Query cannot be empty",
        )
    
    title = None
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
            conversation_id = row['id']
            logger.info(f"Conversation created {conversation_id} for user {user['id']}")
    else:
        async with conn.cursor() as cur:
            await cur.execute(
                """ SELECT id FROM conversations
                WHERE id=%s AND user_id=%s      
                """,
                (conversation_id, user['id'])
            )
            row = await cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )

    async with conn.cursor() as cur:
        await cur.execute(
            """INSERT INTO chats (conversation_id, role, content)
            VALUES (%s, %s, %s)
            """,
            (conversation_id, 'user', message)
        )
    config = {
        "configurable": {
            "thread_id": conversation_id,
            "user_id": user['id'] 
        }
    }
    initial_state = HumanMessage(content=message)
    
    final_state = await workflow.ainvoke({"messages": [initial_state]}, config=config)
    ai_response = final_state['messages'][-1].content
    
    async with conn.cursor() as cur:
        await cur.execute(
            """INSERT INTO chats (conversation_id, role, content)
            VALUES (%s, %s, %s)
            """,
            (conversation_id, 'assistant', ai_response)
        )
        
    return {
        'conversation_id': conversation_id,
        'message': ai_response,
    }

@router.get("/{conversation_id}")
async def get_chat_history(conversation_id: str, conn=Depends(get_conn), user=Depends(get_user)):
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT role, content, created_at
            FROM chats
            WHERE conversation_id = %s
            ORDER BY created_at ASC
            """,
            (conversation_id,)
        )
        messages = await cur.fetchall()
        
    return [
        {
            "role": message["role"],
            "message": message["content"],
            "created_at": message["created_at"]
        } for message in messages
    ]

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), user=Depends(get_user)):
    try:
        file_content = await file.read()
        await process_pdf(file_content, user['id'])
        return {"message": "PDF processed successfully"}
        
    except Exception as e:
        print(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process PDF")