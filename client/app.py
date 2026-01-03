import streamlit as st

from api import (
    get_me, login, logout, signup, get_ans, get_chats, 
    get_user_conversations, delete_user_conversation
)
if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

def load_user():
    try:
        res = get_me()
        if res.status_code == 200:
            st.session_state.user = res.json()
    except Exception as e:
        print(f"Error loading user: {e}")

def load_chats():
    if st.session_state.conversation_id:
        res = get_chats(st.session_state.conversation_id)
        if res.status_code == 200:
            st.session_state.messages = res.json()

def onsignup():
    res = signup(
        st.session_state.signup_name,
        st.session_state.signup_email,
        st.session_state.signup_password
    )
    if res.status_code == 200:
        st.success("Account created! Please login.")
    else:
        st.error("Signup failed.")

def onlogin():
    res = login(
        st.session_state.login_email,
        st.session_state.login_password
    )
    if res.status_code == 200:
        st.success("Login Successful")
        load_user()
    else:
        st.error("Invalid credentials")

def onchat():
    user_input = st.session_state.question
    
    res = get_ans(
        user_input,
        st.session_state.conversation_id
    )
    
    if res.status_code == 200:
        data = res.json()
        
        if st.session_state.conversation_id is None:
            st.session_state.conversation_id = data.get('conversation_id')
        
        st.session_state.messages.append({"role": "user", "message": user_input})
        st.session_state.messages.append({"role": "assistant", "message": data['message']})
    else:
        st.error("Failed to get response")

load_user()

if st.session_state.user and st.session_state.conversation_id and not st.session_state.messages:
    load_chats()

if st.session_state.user is None:
    st.title("Welcome to JoluMate")
    tab1, tab2 = st.tabs(['Login', "Signup"])
    
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
        st.write(f" **{st.session_state.user.get('name', 'User')}**")
        
        if st.button(" New Chat", use_container_width=True):
            st.session_state.conversation_id = None
            st.session_state.messages = []
            st.rerun()

        st.divider()
        st.subheader("History")

        try:
            res = get_user_conversations()
            if res.status_code == 200:
                conversations = res.json()
                
                if not conversations:
                    st.caption("No recent chats")

                for convo in conversations:
                    col1, col2 = st.columns([0.8, 0.2])
                    
                    with col1:
                        is_active = st.session_state.conversation_id == convo['id']
                        btn_type = "primary" if is_active else "secondary"
                        
                        title_label = convo['title'][:18] + "..." if len(convo['title']) > 18 else convo['title']
                        
                        if st.button(title_label, key=f"load_{convo['id']}", help=convo['title'], type=btn_type):
                            st.session_state.conversation_id = convo['id']
                            st.session_state.messages = [] 
                            st.rerun()

                    with col2:
                        if st.button("Delete", key=f"del_{convo['id']}"):
                            del_res = delete_user_conversation(convo['id'])
                            if del_res.status_code == 202:
                                if st.session_state.conversation_id == convo['id']:
                                    st.session_state.conversation_id = None
                                    st.session_state.messages = []
                                st.rerun()
            else:
                st.error("Could not load history")
        except Exception as e:
            st.error(f"Connection Error: {e}")

        st.divider()
        if st.button("Logout", use_container_width=True):
            logout()
            st.session_state.user = None
            st.session_state.messages = []
            st.session_state.conversation_id = None
            st.rerun()

    if st.session_state.conversation_id and not st.session_state.messages:
        load_chats()

    if not st.session_state.messages and not st.session_state.conversation_id:
        st.title("👋 JoluMate")
        st.markdown("Start a new conversation using the sidebar!")
    else:
        for message in st.session_state.messages:
            with st.chat_message(message['role']):
                st.write(message['message'])

    st.chat_input("Ask Your Question", key="question", on_submit=onchat)