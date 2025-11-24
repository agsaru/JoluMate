from loader import load_file
from chunker import text_splitter
from vector import create_vectorstore
from rag import create_rag, ask_question

from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    question: str

app.state.rag = None


@app.get("/")
def hello():
    return {"status": "Backend running"}


@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files received")

        os.makedirs("data", exist_ok=True)
        all_docs = []

        for file in files:
            filename = file.filename.replace(" ", "_")
            filepath = os.path.join("data", filename)

            try:
                with open(filepath, "wb") as f:
                    f.write(await file.read())
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
            try:
                docs = load_file(filepath)
                if not isinstance(docs, list):
                    raise ValueError("Loader did not return a list of Documents")
                all_docs.extend(docs)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error loading {filename}: {str(e)}")

        try:
            chunks = text_splitter(all_docs)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chunking failed: {str(e)}")

        try:
            vectorstore = create_vectorstore(chunks)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Vectorstore creation failed: {str(e)}")
        try:
            app.state.rag = create_rag(vectorstore)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"RAG creation failed: {str(e)}")

        return {"message": f"Loaded {len(files)} files successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask")
def ask(query: Query):
    try:
        rag = app.state.rag

        if rag is None:
            raise HTTPException(status_code=400, detail="No document uploaded yet")

        if not query.question.strip():
            raise HTTPException(status_code=400, detail="Empty question")

        try:
            answer = ask_question(rag, query.question)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"RAG failed to answer: {str(e)}")

        return {"answer": answer}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))









