import os
import requests
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("BACKEND_URL")


def signup(session, name: str, email: str, password: str):
    response = session.post(
        f"{BASE_URL}/auth/signup",
        json={"name": name, "email": email, "password": password}
    )
    return response

def login(session, email: str, password: str):
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    return response

def get_me(session):
    response = session.get(f"{BASE_URL}/auth/me")
    return response

def logout(session):
    response = session.get(f"{BASE_URL}/auth/logout")
    return response

def get_ans(session, message: str, conversation_id: str = None):
    response = session.post(
        f"{BASE_URL}/chat/ask",
        json={"message": message, "conversation_id": conversation_id}
    )
    return response

def get_chats(session, conversation_id: str):
    response = session.get(f"{BASE_URL}/chat/{conversation_id}")
    return response

def get_conversations(session):
    response = session.get(f"{BASE_URL}/conversations")
    return response
def delete_conversation(session, conversation_id: str):
    response = session.post(
        f"{BASE_URL}/conversations/delete", 
        params={"conversation_id": conversation_id}
    )
    return response
def upload_doc(session, file):
    files = {"file": (file.name, file, "application/pdf")}
    response = session.post(f"{BASE_URL}/chat/upload", files=files)
    return response