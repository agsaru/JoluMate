from fastapi import APIRouter,Depends,HTTPException
from configs.db import get_conn
from auth.auth import get_user
router=APIRouter(
    prefix='/chat',
    tags=['chat']
)

from typing import TypedDict
from dotenv import load_dotenv
load_dotenv()
import os
from langchain_google_genai import ChatGoogleGenerativeAI

class Que(TypedDict):
    question:str
    
@router.post('/')
def get_ans(que:Que):
    
    question=que.question
    if not question.strip():
        raise HTTPException(status_code=400,detail="Query cannot be empty")
    
    model=ChatGoogleGenerativeAI(model='gemini-2.5-flash',api_key=os.getenv("GOOGLE_API_KEY"))
    response = model.invoke(question)
    return {'message':response.content}

@router.post("/")
def send_message(conversation_id:str,message:str,conn=Depends(get_conn),user_id:str=Depends(get_user)):
    if not message.strip():
        raise HTTPException(400,"Message cannot be empty")
    conn.execute(
        """
        INSERT INTO chat(user_id,conversation_id,role,message)
        VALUES(%s,%s,%s,%s)
        """,
        (user_id,conversation_id,"user",message)
    )
    return {'message':"Message saved"}

@router.get("/history")
def get_chat_history(conversation_id: str,conn=Depends(get_conn),user_id:str=Depends(get_user)):
    rows=conn.fecth(
        """
        SELECT role, content, created_at
        FROM chats
        WHERE user_id = %s
        ORDER BY created_at ASC
        """,
        (user_id,conversation_id)
    )
    return [
        {
            "role":row["role"],
            "message": row["message"],
            "created_at": row["created_at"]
        } for row in rows
    ]
