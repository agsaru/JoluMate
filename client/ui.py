import streamlit as st
import requests
import os
from dotenv import load_dotenv
load_dotenv()
BACKEND_URL=os.getenv("BACKEND_URL")

if "messages" not in st.session_state:
    st.session_state.messages = []

user_input = st.chat_input("Ask Your Question")
with st.sidebar:
    st.title("JoluMate")
    st.button("New Chat")
if user_input:
    st.session_state.messages.append({
        "role": "user",
        "message": user_input
    })

    response = requests.post(
            f"{BACKEND_URL}/chat/",
            json={"question": user_input}
        )

    data = response.json()

    st.session_state.messages.append({
        "role": "assistant",
        "message": data["message"]
    })

for me in st.session_state.messages:
    with st.chat_message(me["role"]):
        st.write(me["message"])
