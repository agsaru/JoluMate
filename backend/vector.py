from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
import os
from dotenv import load_dotenv
load_dotenv()
def create_vectorstore(chunks):
    clean_chunks = [
        doc for doc in chunks
        if getattr(doc, "page_content", "") and doc.page_content.strip()
    ]

    if not clean_chunks:
        raise ValueError("NO_TEXT")

    embedding_model=ChatGoogleGenerativeAI(model="gemini-embedding-001",api_key=os.getenv("GOOGLE_API_KEY"))
    vectorstore = FAISS.from_documents(clean_chunks, embedding_model)
    return vectorstore
