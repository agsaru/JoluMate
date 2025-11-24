import streamlit as st
import requests

st.title("JoluMate")

uploaded_files=st.file_uploader("Upload file",accept_multiple_files=True)


if uploaded_files:
    st.success(f"{len(uploaded_files) } file{"" if len(uploaded_files)==1 else "s"} seleacted")
if st.button("Process Files"):
    if not uploaded_files:
        st.warning("Please upload at least one file")
    else:
        with st.spinner("Unloading"):
            files=[
                ("files",(f.name,f.read(),f.type))
                for f in uploaded_files
            ]
            res=requests.post("http://127.0.0.1:8000/upload", files=files)
            st.success(res.json()["message"])

st.header("Ask Questions")
query=st.text_input("ask ")
if st.button("Get Answer"):
    res=requests.post("http://127.0.0.1:8000/ask",json={"question": query})
    st.write(res.json()["answer"])