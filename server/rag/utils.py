import io
import asyncio
import os

from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from configs.db import pool
from logs.logging_config import logger

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
DEFAULT_SEARCH_LIMIT = 5
EMBEDDING_BATCH_SIZE = 64

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)


async def process_pdf(file_bytes: bytes, user_id: str, conversation_id: str):
    """Extract, chunk, embed in bounded batches, and store a PDF atomically."""
    reader = PdfReader(io.BytesIO(file_bytes))
    docs = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            docs.append(Document(page_content=text, metadata={"page": i + 1}))

    if not docs:
        logger.warning("PDF contained no extractable text")
        return 0

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    splits = text_splitter.split_documents(docs)
    contents = [split.page_content for split in splits]

    # Batch embeddings to reduce per-chunk network overhead without launching
    # an unbounded number of concurrent provider requests.
    vectors = []
    for start in range(0, len(contents), EMBEDDING_BATCH_SIZE):
        batch = contents[start:start + EMBEDDING_BATCH_SIZE]
        batch_vectors = await asyncio.to_thread(embeddings.embed_documents, batch)
        vectors.extend(batch_vectors)

    # Store only after all embeddings succeeded, so provider failures cannot
    # leave a partially indexed document in the knowledge base.
    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                for content, vector in zip(contents, vectors):
                    await cur.execute(
                        """
                        INSERT INTO documents (user_id, conversation_id, content, embedding)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (user_id, conversation_id, content, vector),
                    )

    logger.info(
        "Processed PDF: %s chunks stored for user %s, conversation %s",
        len(splits),
        user_id,
        conversation_id,
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
