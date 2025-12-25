from fastapi import APIRouter,HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()
import os
from langchain_google_genai import ChatGoogleGenerativeAI

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)
class Que(BaseModel):
    question:str
@router.post('/')
def get_ans(que:Que):
    
    question=que.question
    if not question.strip():
        raise HTTPException(status_code=400,detail="Query cannot be empty")
    
    model=ChatGoogleGenerativeAI(model='gemini-2.5-flash',api_key=os.getenv("GOOGLE_API_KEY"))
    response = model.invoke(question)
    return {'message':response.content}