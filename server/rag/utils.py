# FILE: server/rag/utils.py
import io
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from configs.db import pool
import os

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

async def process_pdf(file_bytes: bytes, user_id: str):
    pdf_stream = io.BytesIO(file_bytes)
    
    reader = PdfReader(pdf_stream)
    docs = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            docs.append(Document(page_content=text, metadata={"page": i + 1}))

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            for split in splits:
                vector = embeddings.embed_query(split.page_content)
                await cur.execute(
                    "INSERT INTO documents (user_id, content, embedding) VALUES (%s, %s, %s)",
                    (user_id, split.page_content, vector)
                )
async def search_documents(query: str, user_id: str, limit: int = 5):
    query_vector = embeddings.embed_query(query)
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT content 
                FROM documents 
                WHERE user_id = %s 
                ORDER BY embedding <=> %s::vector 
                LIMIT %s
                """,
                (user_id, str(query_vector), limit)
            )
            results = await cur.fetchall()
            
    return "\n\n".join([row['content'] for row in results])