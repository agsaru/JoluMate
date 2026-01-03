from fastapi import APIRouter, Depends, HTTPException, status
from configs.db import get_conn
from auth.auth import get_user

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.get("")
async def list_conversations(
    conn=Depends(get_conn),
    user=Depends(get_user)
):
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT id, title, created_at
            FROM conversations
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user['id'],)
        )
        conversations = await cur.fetchall()

    return [
        {
            "id": convo["id"], 
            "title": convo["title"] if convo["title"] else "New Chat",
            "created_at": convo["created_at"]
        }
        for convo in conversations
    ]

@router.post('/delete', status_code=status.HTTP_202_ACCEPTED)
async def delete_conversation(
    conversation_id: str,
    conn=Depends(get_conn),
    user=Depends(get_user)
):
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT id FROM conversations
            WHERE id=%s AND user_id=%s
            """,
            (conversation_id, user['id'])
        )
        exists = await cur.fetchone()
        
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
        
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                DELETE FROM conversations
                WHERE id=%s
                """,
                (conversation_id,)
            )
            await cur.execute(
                """
                DELETE FROM chats
                WHERE conversation_id=%s
                """,
                (conversation_id,)
            )
            
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Conversation deletion unsuccessful"
        )
    return {
        "message": "Conversation deleted successfully"
    }