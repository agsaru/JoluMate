import os
import requests
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("BACKEND_URL")
REQUEST_TIMEOUT = (5, 120)


def _request(session, method, path, retry_auth=True, **kwargs):
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    response = session.request(method, f"{BASE_URL}{path}", **kwargs)

    if response.status_code == 401 and retry_auth and path not in (
        "/auth/login", "/auth/signup", "/auth/refresh", "/auth/logout"
    ):
        refresh_response = session.post(
            f"{BASE_URL}/auth/refresh",
            timeout=REQUEST_TIMEOUT,
        )
        if refresh_response.status_code == 200:
            response = session.request(
                method, f"{BASE_URL}{path}", **kwargs
            )

    return response


def signup(session, name: str, email: str, password: str):
    return _request(
        session,
        "POST",
        "/auth/signup",
        json={"name": name, "email": email, "password": password},
        retry_auth=False,
    )


def login(session, email: str, password: str):
    return _request(
        session,
        "POST",
        "/auth/login",
        json={"email": email, "password": password},
        retry_auth=False,
    )


def get_me(session):
    return _request(session, "GET", "/auth/me")


def logout(session):
    return _request(session, "POST", "/auth/logout", retry_auth=False)


def get_ans(session, message: str, conversation_id: str = None):
    return _request(
        session,
        "POST",
        "/chat/ask",
        json={"message": message, "conversation_id": conversation_id},
    )


def get_chats(session, conversation_id: str):
    return _request(session, "GET", f"/chat/{conversation_id}")


def get_conversations(session):
    return _request(session, "GET", "/conversations")


def delete_conversation(session, conversation_id: str):
    return _request(
        session,
        "POST",
        "/conversations/delete",
        params={"conversation_id": conversation_id},
    )


def upload_doc(session, file, conversation_id):
    files = {"file": (file.name, file, "application/pdf")}
    params = {"conversation_id": conversation_id}
    response = _request(
        session,
        "POST",
        "/chat/upload",
        files=files,
        params=params,
    )
    return response
