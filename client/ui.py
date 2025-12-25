import streamlit as st
st.title("JoluMate")

user_input=st.chat_input("Ask Your Question")

if user_input:
    st.write(user_input)