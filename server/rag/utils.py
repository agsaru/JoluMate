# FILE: server/rag/utils.py
import io
import asyncio

from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from configs.db import pool
from logs.logging_config import logger
import os

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
DEFAULT_SEARCH_LIMIT = 5

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)


async def process_pdf(file_bytes: bytes, user_id: str, conversation_id: str):
    """Extract text from PDF, chunk it, embed each chunk, and store in the database.

    All inserts are wrapped in a transaction so partial failures
    don't leave orphaned chunks.
    """
    pdf_stream = io.BytesIO(file_bytes)

    reader = PdfReader(pdf_stream)
    docs = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            docs.append(Document(page_content=text, metadata={"page": i + 1}))

    if not docs:
        logger.warning("PDF contained no extractable text")
        return 0

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    splits = text_splitter.split_documents(docs)

    # Use a transaction so all-or-nothing insertion
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                for split in splits:
                    # Run synchronous embedding call in a thread to avoid
                    # blocking the async event loop
                    vector = await asyncio.to_thread(
                        embeddings.embed_query, split.page_content
                    )
                    await cur.execute(
                        """
                        INSERT INTO documents (user_id, conversation_id, content, embedding)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (user_id, conversation_id, split.page_content, vector),
                    )

    logger.info(
        f"Processed PDF: {len(splits)} chunks stored for user {user_id}, "
        f"conversation {conversation_id}"
    )
    return len(splits)


async def search_documents(
    query: str,
    user_id: str,
    conversation_id: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
):
    """Perform cosine similarity search against stored document embeddings."""
    query_vector = await asyncio.to_thread(embeddings.embed_query, query)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT content
                FROM documents
                WHERE user_id = %s AND conversation_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (user_id, conversation_id, str(query_vector), limit),
            )
            results = await cur.fetchall()

    return "\n\n".join([row["content"] for row in results])