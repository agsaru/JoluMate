import streamlit as st
from api import (
    get_me, login, logout, signup, get_ans, get_chats,
    get_conversations, delete_conversation, upload_doc,
)
import requests


if "api_session" not in st.session_state:
    st.session_state.api_session = requests.Session()

if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None


def response_error(res, fallback):
    try:
        detail = res.json().get("detail")
        if detail:
            return detail
    except (ValueError, requests.exceptions.RequestException):
        pass
    return fallback


def load_user():
    try:
        res = get_me(st.session_state.api_session)
        if res.status_code == 200:
            st.session_state.user = res.json()
        elif res.status_code == 401:
            st.session_state.user = None
    except requests.exceptions.RequestException:
        st.error("Couldn't connect to JoluMate. Check your connection and try again.")


def load_chats(conv_id):
    try:
        res = get_chats(st.session_state.api_session, conv_id)
        if res.status_code == 200:
            st.session_state.messages = res.json()
            st.session_state.conversation_id = conv_id
        else:
            st.error(response_error(res, "Couldn't load this conversation."))
    except requests.exceptions.Timeout:
        st.error("Loading this conversation took too long. Please try again.")
    except requests.exceptions.RequestException:
        st.error("Couldn't connect to JoluMate. Check your connection and try again.")


def onsignup():
    try:
        res = signup(
            st.session_state.api_session,
            st.session_state.signup_name,
            st.session_state.signup_email,
            st.session_state.signup_password,
        )
        if res.status_code == 201:
            st.success("Account created! Please login.")
        else:
            st.error(response_error(res, "Signup failed. Please try again."))
    except requests.exceptions.Timeout:
        st.error("Signup timed out. Please try again.")
    except requests.exceptions.RequestException:
        st.error("Couldn't connect to JoluMate. Check your connection and try again.")


def onlogin():
    try:
        res = login(
            st.session_state.api_session,
            st.session_state.login_email,
            st.session_state.login_password,
        )
        if res.status_code == 200:
            load_user()
        else:
            st.error(response_error(res, "Invalid email or password."))
    except requests.exceptions.Timeout:
        st.error("Login timed out. Please try again.")
    except requests.exceptions.RequestException:
        st.error("Couldn't connect to JoluMate. Check your connection and try again.")


def onlogout():
    try:
        logout(st.session_state.api_session)
    except requests.exceptions.RequestException:
        pass
    st.session_state.api_session.cookies.clear()
    st.session_state.user = None
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.rerun()


def onchat():
    user_input = st.session_state.question.strip()
    if not user_input:
        return

    user_message = {"role": "user", "message": user_input, "status": "pending"}
    st.session_state.messages.append(user_message)

    try:
        res = get_ans(
            st.session_state.api_session,
            user_input,
            st.session_state.conversation_id,
        )

        if res.status_code == 200:
            data = res.json()
            st.session_state.conversation_id = data["conversation_id"]
            user_message["status"] = "completed"
            st.session_state.messages.append(
                {"role": "assistant", "message": data["message"]}
            )
        else:
            user_message["status"] = "failed"
            st.error(response_error(res, "JoluMate couldn't generate a response. Your message is saved; you can send it again."))
    except requests.exceptions.Timeout:
        user_message["status"] = "failed"
        st.error("JoluMate is taking longer than expected. Your message may have been saved; check the chat before retrying.")
    except requests.exceptions.RequestException:
        user_message["status"] = "failed"
        st.error("Couldn't connect to JoluMate. Your message may have been saved; check the chat before retrying.")


def on_delete(conv_id):
    try:
        res = delete_conversation(st.session_state.api_session, conv_id)
        if res.status_code == 200:
            if st.session_state.conversation_id == conv_id:
                st.session_state.conversation_id = None
                st.session_state.messages = []
            st.rerun()
        else:
            st.error(response_error(res, "Could not delete this conversation."))
    except requests.exceptions.RequestException:
        st.error("Couldn't connect to JoluMate. Please try again.")


if st.session_state.user is None:
    load_user()

if st.session_state.user is None:
    st.title("Welcome to JoluMate")
    tab1, tab2 = st.tabs(["Login", "Signup"])

    with tab1:
        st.subheader("Login")
        st.text_input("Email", key="login_email")
        st.text_input("Password", type="password", key="login_password")
        st.button("Login", on_click=onlogin)

    with tab2:
        st.subheader("Create Account")
        st.text_input("Name", key="signup_name")
        st.text_input("Email", key="signup_email")
        st.text_input("Password", type="password", key="signup_password")
        st.button("Signup", on_click=onsignup)

else:
    with st.sidebar:
        st.write(f"Logged in as: **{st.session_state.user.get('name', 'User')}**")

        if st.button("Logout"):
            onlogout()
        st.divider()

        if st.button("New Chat"):
            st.session_state.conversation_id = None
            st.session_state.messages = []
            st.rerun()

        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
        if st.session_state.conversation_id is None:
            st.warning("Start a chat before uploading a PDF")
        elif uploaded_file is not None:
            if st.button("Process PDF"):
                with st.spinner("Reading and embedding..."):
                    try:
                        res = upload_doc(
                            st.session_state.api_session,
                            uploaded_file,
                            st.session_state.conversation_id,
                        )
                        if res.status_code == 200:
                            data = res.json()
                            st.success(
                                f"PDF processed. {data['chunks_processed']} searchable sections added."
                            )
                        else:
                            st.error(response_error(res, "Failed to process this PDF."))
                    except requests.exceptions.Timeout:
                        st.error("PDF processing is taking longer than expected. Check the chat's documents before retrying.")
                    except requests.exceptions.RequestException:
                        st.error("Couldn't connect to JoluMate. Please try again.")

        st.divider()
        st.subheader("History")

        try:
            conv_res = get_conversations(st.session_state.api_session)
            if conv_res.status_code == 200:
                for convo in conv_res.json():
                    col1, col2 = st.columns([0.8, 0.2])
                    with col1:
                        title_label = convo.get("title") or "Untitled Chat"
                        if st.button(title_label, key=f"btn_{convo['id']}", help="Open Chat"):
                            load_chats(convo["id"])
                            st.rerun()
                    with col2:
                        if st.button("", icon=":material/delete:", key=f"del_{convo['id']}", help="Delete Chat"):
                            on_delete(convo["id"])
        except requests.exceptions.RequestException:
            st.caption("Couldn't load conversation history.")

    if not st.session_state.messages:
        st.title("Get started with JoluMate")
    else:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["message"])
                if message.get("status") == "failed":
                    st.caption("This message did not receive an AI response. You can send it again.")

    st.chat_input("Ask Your Question", key="question", on_submit=onchat)
