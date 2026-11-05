import asyncio
import os

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from configs.db import pool
from logs.logging_config import logger

load_dotenv()

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768
BATCH_SIZE = 64

document_embeddings = GoogleGenerativeAIEmbeddings(
    model=EMBEDDING_MODEL,
    task_type="RETRIEVAL_DOCUMENT",
    output_dimensionality=EMBEDDING_DIMENSIONS,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)


async def reembed_documents():
    """Re-embed old chunks in small batches; safe to rerun after interruption."""
    await pool.open()
    last_id = 0
    processed = 0

    try:
        while True:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT id, content
                        FROM documents
                        WHERE embedding_model != %s AND id > %s
                        ORDER BY id
                        LIMIT %s
                        """,
                        (EMBEDDING_MODEL, last_id, BATCH_SIZE),
                    )
                    batch = await cur.fetchall()

            if not batch:
                break

            contents = [row["content"] for row in batch]
            vectors = await asyncio.to_thread(
                document_embeddings.embed_documents,
                contents,
            )

            if len(vectors) != len(batch):
                raise RuntimeError("Embedding count does not match the selected rows")

            async with pool.connection() as conn:
                async with conn.transaction():
                    async with conn.cursor() as cur:
                        for row, vector in zip(batch, vectors):
                            await cur.execute(
                                """
                                UPDATE documents
                                SET embedding = %s, embedding_model = %s
                                WHERE id = %s
                                """,
                                (vector, EMBEDDING_MODEL, row["id"]),
                            )

            last_id = batch[-1]["id"]
            processed += len(batch)
            logger.info("Re-embedded %s document chunks", processed)

        logger.info("Document re-embedding completed: %s chunks", processed)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(reembed_documents())
