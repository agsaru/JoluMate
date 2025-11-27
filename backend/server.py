from loader import load_file
from chunker import text_splitter
from vector import create_vectorstore
from rag import create_rag, ask_question

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class Query(BaseModel):
    question: str

app.state.rag = None

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(400, "No files uploaded")

    docs = []
    for file in files:
        filepath = os.path.join(DATA_DIR, file.filename.replace(" ", "_"))
        with open(filepath, "wb") as f:
            f.write(await file.read())
        docs.extend(load_file(filepath))

    chunks = text_splitter(docs)
    if len(chunks)>100:
        raise HTTPException(status_code=400,detail="Try to upload with maximum 100 pages If it has more words than 500 please try to upload maximum 50 to 60 words file")

    try:
        vectorstore = create_vectorstore(chunks)
    except ValueError as e:
        if str(e) == "NO_TEXT":

            raise HTTPException(
                status_code=400,
                detail="I couldn't read any text from the uploaded files. "
                       "If it's a scanned or image-only PDF, please try a different file."
            )
        raise HTTPException(status_code=500, detail=f"Vectorstore creation failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vectorstore creation failed: {str(e)}")

    app.state.rag = create_rag(vectorstore)

    return {"message": f"Processed {len(files)} files"}


@app.post("/ask")
async def ask(query: Query):
    if not app.state.rag:
        raise HTTPException(400, "Upload files first")

    return {"answer": ask_question(app.state.rag, query.question)}

