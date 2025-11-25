from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

def create_vectorstore(chunks):
    clean_chunks = [
        doc for doc in chunks
        if getattr(doc, "page_content", "") and doc.page_content.strip()
    ]

    if not clean_chunks:
        raise ValueError("NO_TEXT")

    embedding_model = HuggingFaceEmbeddings(
        model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    )

    vectorstore = FAISS.from_documents(clean_chunks, embedding_model)
    return vectorstore
