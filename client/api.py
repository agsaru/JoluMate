import os
import requests
from dotenv import load_dotenv
load_dotenv()
BASE_URL=os.getenv("BACKEND_URL")
session=requests.Session()
def signup(name:str,email:str,password:str):
    response=session.post(
        f"{BASE_URL}/auth/signup",
        json={
            "name":name,
            "email":email,
            "password":password
        }
        
        )
    return response

def login(email:str,password:str):
    response=session.post(
        f"{BASE_URL}/auth/login",
        json={
            "email":email,
            "password":password
        }
        )
    return response

def get_me():
    response=session.get(
        f"{BASE_URL}/auth/me"
    )
    return response

def logout():
    response=session.get(
        f"{BASE_URL}/auth/logout"
    )
    return response


def get_ans(message:str,conversation_id:str=None):
    response=session.post(
        f"{BASE_URL}/chat/ask",
        json={
            "message":message,
            "conversation_id":conversation_id
        }
    )
    return response

def get_chats(conversation_id:str):
    response=session.get(
    f"{BASE_URL}/chat/{conversation_id}"
    )
    return response