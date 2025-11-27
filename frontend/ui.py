import streamlit as st
import requests

BACKEND_BASE_URL = st.secrets["BACKEND_BASE_URL"]

st.title("JoluMate - Study Assistant")

uploaded_files = st.file_uploader(
    "Upload study materials. Try to upload files with less than 80 pages",
    type=["pdf", "docx", "pptx", "txt"],
    accept_multiple_files=True
)

if st.button("Process Files"):
    if not uploaded_files:
        st.warning("Please upload files first")
    else:
        try:
            files = [
                ("files", (f.name, f.getvalue(), "application/octet-stream"))
                for f in uploaded_files
            ]

            res = requests.post(f"{BACKEND_BASE_URL}/upload", files=files)

            response_json = res.json()

            if "message" in response_json:
                st.success(response_json["message"])
            else:
                st.error(response_json.get("detail", "Something went wrong while processing."))

        except Exception as e:
            st.error("Error contacting backend.")
            st.exception(e)

query = st.text_input("Ask your question")

if st.button("Get Answer"):
    try:
        res = requests.post(f"{BACKEND_BASE_URL}/ask", json={"question": query})
        response_json = res.json()

        if "answer" in response_json:
            st.write(response_json["answer"])
        else:
            st.error(response_json.get("detail", "Could not retrieve answer."))

    except Exception as e:
        st.error("Error contacting backend.")
        st.exception(e)
