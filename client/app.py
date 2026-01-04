import streamlit as st
from api import get_me, login, logout, signup, get_ans, get_chats, get_conversations,delete_conversation, upload_doc
import requests
if "api_session" not in st.session_state:
    st.session_state.api_session = requests.Session()

if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

def load_user():
    try:
        res = get_me(st.session_state.api_session) 
        if res.status_code == 200:
            st.session_state.user = res.json()
    except Exception as e:
        print(f"Error loading user: {e}")

def load_chats(conv_id):
    res = get_chats(st.session_state.api_session, conv_id)
    if res.status_code == 200:
        st.session_state.messages = res.json()
        st.session_state.conversation_id = conv_id

def onsignup():
    res = signup(
        st.session_state.api_session, 
        st.session_state.signup_name,
        st.session_state.signup_email,
        st.session_state.signup_password
    )
    if res.status_code == 201:
        st.success("Account created! Please login.")
    else:
        st.error("Signup failed.")

def onlogin():
    res = login(
        st.session_state.api_session,
        st.session_state.login_email,
        st.session_state.login_password
    )
    if res.status_code == 200:
        load_user()
    else:
        st.error("Invalid credentials")

def onlogout():
    logout(st.session_state.api_session)
    st.session_state.api_session.cookies.clear()
    st.session_state.user = None
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.rerun()

def onchat():
    user_input = st.session_state.question
    if not user_input:
        return
    st.session_state.messages.append({"role": "user", "message": user_input})
    res = get_ans(
        st.session_state.api_session,
        user_input,
        st.session_state.conversation_id
    )
    
    if res.status_code == 200:
        data = res.json()
        st.session_state.conversation_id = data.get('conversation_id')
        st.session_state.messages.append({"role": "assistant", "message": data['message']})
    else:
        st.error("Failed to get response")
def on_delete(conv_id):
    res = delete_conversation(st.session_state.api_session, conv_id)
    if res.status_code == 202:
        if st.session_state.conversation_id == conv_id:
            st.session_state.conversation_id = None
            st.session_state.messages = []
        st.rerun()
    else:
        st.error("Could not delete.")
load_user()

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
        st.write(f"Logged in as: **{st.session_state.user.get('name', 'User')}**")
        
        if st.button("Logout"):
            onlogout()
        st.divider()
        if st.button("New Chat"):
            st.session_state.conversation_id = None
            st.session_state.messages = []
            st.rerun()
            
        uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])
        if uploaded_file is not None:
            if st.button("Process PDF"):
                with st.spinner("Reading and embedding..."):
                    res = upload_doc(st.session_state.api_session, uploaded_file)
                    if res.status_code == 200:
                        st.success("PDF Learned! You can now ask questions about it.")
                    else:
                        st.error("Failed to process PDF.")
        
        st.divider()
        st.subheader("History")
        
        conv_res = get_conversations(st.session_state.api_session)
        if conv_res.status_code == 200:
            conversations = conv_res.json()
            for convo in conversations:
                col1, col2 = st.columns([0.8, 0.2])
            
                with col1:
                    title_label = convo.get('title') or "Untitled Chat"
                    if st.button(f"{title_label}", key=f"btn_{convo['id']}", help="Open Chat"):
                        load_chats(convo['id'])
                        st.rerun()
                
                with col2:
                    if st.button("", icon=":material/delete:", key=f"del_{convo['id']}", help="Delete Chat"):
                        on_delete(convo['id'])

    if not st.session_state.messages:
        st.title("Get started with JoluMate")
    else:
        for message in st.session_state.messages:
            with st.chat_message(message['role']):
                st.write(message['message'])
    
    st.chat_input("Ask Your Question", key="question", on_submit=onchat)