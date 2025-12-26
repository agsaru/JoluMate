from fastapi import APIRouter,Depends,HTTPException
from configs.db import get_conn
from auth.auth import get_user
router=APIRouter(
    prefix='/chat',
    tags=['chat']
)

from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()
import os
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

class Que(BaseModel):
    question:str
    
@router.post('/')
def get_ans(que:Que):
    
    question=que.question
    if not question.strip():
        raise HTTPException(status_code=400,detail="Query cannot be empty")
    
    # model=ChatGoogleGenerativeAI(model='gemini-2.5-flash',api_key=os.getenv("GOOGLE_API_KEY"))
    model=ChatGroq(model='openai/gpt-oss-120b',api_key=os.getenv("GROQ_API_KEY"))
    response = model.invoke(question)
    return {'message':response.content}

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
