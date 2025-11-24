import streamlit as st
import requests
BACKEND_BASE_URL = st.secrets["BACKEND_BASE_URL"]

st.set_page_config(
    page_title="JoluMate",
    layout="centered",
)
st.title("JoluMate")
st.caption("Your AI-powered document assistant")

with st.container():
    st.subheader("Upload your documents")
    uploaded_files=st.file_uploader(
        "Select Files",
        accept_multiple_files=True
    )
    if uploaded_files:
        st.info(f"{len(uploaded_files) } file{"" if len(uploaded_files)==1 else "s"} seleacted")
    if st.button("Process Files"):
       if not uploaded_files:
          st.warning("Please upload at least one file")
       else:
          with st.spinner("Processing files..."):
             try:
               files=[
                ("files",(f.name,f.read(),f.type))
                for f in uploaded_files
            ]
               res=requests.post(f"{BACKEND_BASE_URL}/upload", files=files)
               res.raise_for_status()
               st.success(res.json()["message"])
                  
             except requests.exceptions.RequestException as e:
                st.error("Failed to Process Files")
                st.exception(e)

st.divider()

with st.container():
   st.header("Ask Questions")
   query=st.text_input("Ask any question from your uploaded files")
   if st.button("Get Answer"):
      if not query.strip():
         st.warning("Please type your question first")
      else:
         with st.spinner("Finding best possible answer for you..."):
            try:
               res=requests.post(f"{BACKEND_BASE_URL}/ask",json={"question": query},timeout=60)
               res.raise_for_status()
               st.write(res.json()["answer"])
            except requests.exceptions.Timeout:
               st.error("The request timed out")
            except Exception as e:
               st.error("Error while getting answer")
               st.exception(e)
      
     