from loader import load_file
from chunker import text_splitter
from vector import create_vectorstore
from rag import create_rag,ask_question

from typing import List
from fastapi import FastAPI,UploadFile,File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app=FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Query(BaseModel):
    question: str


rag=None
@app.get("/")
def hello():
    return "hello"
@app.post("/upload")
async def upload_files(files:List[UploadFile]=File(...)):
    global rag
    all_docs=[]
    for file in files:
        filepath=f"data/{file.filename}"
        with open(filepath,"wb") as f:
            f.write(await file.read())
        docs=load_file(filepath)
        all_docs.extend(docs)
    chunks=text_splitter(all_docs)
    vectorstore=create_vectorstore(chunks)
    rag=create_rag(vectorstore)
    return {"message":f"Loaded {len(files)} files successfully"}


@app.post("/ask")
def ask(query: Query):
    global rag

    if rag is None:
        return {"answer": "No document uploaded"}

    answer = ask_question(rag, query.question)
    return {"answer": answer}









