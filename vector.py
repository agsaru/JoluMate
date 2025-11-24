from langchain_huggingface import HuggingFaceEmbeddings
from langchain_classic.vectorstores import FAISS
def create_vectorstore(chunks):
    model=HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
    vectorstore=FAISS.from_documents(chunks,model)
    vectorstore.save_local("jolumate_vector")
    return vectorstore
    