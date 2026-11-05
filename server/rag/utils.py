import io
import asyncio
import os
from threading import Lock

from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.retrievers import BaseRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from configs.db import pool
from logs.logging_config import logger

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
DEFAULT_SEARCH_LIMIT = 5
EMBEDDING_BATCH_SIZE = 64
VECTOR_SEARCH_WEIGHT = 0.7
BM25_SEARCH_WEIGHT = 0.3
RERANKING_ENABLED = os.getenv("RAG_RERANKING_ENABLED", "true").lower() == "true"
RERANKER_MODEL = "ms-marco-MiniLM-L-6-v2"
MIN_RELEVANCE_SCORE = os.getenv("RAG_MIN_RELEVANCE_SCORE")
if MIN_RELEVANCE_SCORE is not None:
    MIN_RELEVANCE_SCORE = float(MIN_RELEVANCE_SCORE)
    if not 0 <= MIN_RELEVANCE_SCORE <= 1:
        raise ValueError("RAG_MIN_RELEVANCE_SCORE must be between 0 and 1")
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768

document_embeddings = GoogleGenerativeAIEmbeddings(
    model=EMBEDDING_MODEL,
    task_type="RETRIEVAL_DOCUMENT",
    output_dimensionality=EMBEDDING_DIMENSIONS,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)
query_embeddings = GoogleGenerativeAIEmbeddings(
    model=EMBEDDING_MODEL,
    task_type="RETRIEVAL_QUERY",
    output_dimensionality=EMBEDDING_DIMENSIONS,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)
_rerankers = {}
_reranker_lock = Lock()


def _get_reranker(limit: int):
    from langchain_community.document_compressors import FlashrankRerank

    with _reranker_lock:
        if limit not in _rerankers:
            _rerankers[limit] = FlashrankRerank(
                model=RERANKER_MODEL,
                top_n=limit,
            )
        return _rerankers[limit]


def _rerank_documents(documents, query: str, limit: int):
    return _get_reranker(limit).compress_documents(documents, query)


async def process_pdf(
    file_bytes: bytes,
    user_id: str,
    conversation_id: str,
    filename: str = "uploaded.pdf",
):
    """Extract, chunk, embed in bounded batches, and store a PDF atomically."""
    reader = PdfReader(io.BytesIO(file_bytes))
    filename = os.path.basename(filename.replace("\\", "/")) or "uploaded.pdf"
    docs = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            docs.append(
                Document(
                    page_content=text,
                    metadata={"filename": filename, "page_number": i + 1},
                )
            )

    if not docs:
        logger.warning("PDF contained no extractable text")
        return 0

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True,
    )
    splits = text_splitter.split_documents(docs)
    contents = [split.page_content for split in splits]

    vectors = []
    for start in range(0, len(contents), EMBEDDING_BATCH_SIZE):
        batch = contents[start:start + EMBEDDING_BATCH_SIZE]
        batch_vectors = await asyncio.to_thread(
            document_embeddings.embed_documents,
            batch,
        )
        vectors.extend(batch_vectors)

    if len(vectors) != len(splits):
        raise RuntimeError("Embedding count does not match the number of document chunks")

    async with pool.connection() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                for chunk_index, (split, vector) in enumerate(zip(splits, vectors)):
                    await cur.execute(
                        """
                        INSERT INTO documents (
                            user_id,
                            conversation_id,
                            content,
                            embedding,
                            filename,
                            page_number,
                            chunk_index,
                            start_index,
                            embedding_model
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user_id,
                            conversation_id,
                            split.page_content,
                            vector,
                            split.metadata["filename"],
                            split.metadata["page_number"],
                            chunk_index,
                            split.metadata.get("start_index"),
                            EMBEDDING_MODEL,
                        ),
                    )

    logger.info(
        "Processed PDF: %s chunks stored for user %s, conversation %s",
        len(splits),
        user_id,
        conversation_id,
    )
    return len(splits)


async def retrieve_documents(
    query: str,
    user_id: str,
    conversation_id: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
):
    """Return hybrid-retrieved chunks with their source metadata."""
    candidate_limit = max(limit * 3, limit)
    query_vector = await asyncio.to_thread(query_embeddings.embed_query, query)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, content, filename, page_number, chunk_index, start_index
                FROM documents
                WHERE user_id = %s
                  AND conversation_id = %s
                  AND embedding_model = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (
                    user_id,
                    conversation_id,
                    EMBEDDING_MODEL,
                    str(query_vector),
                    candidate_limit,
                ),
            )
            vector_results = await cur.fetchall()

            await cur.execute(
                """
                SELECT id, content, filename, page_number, chunk_index, start_index
                FROM documents
                WHERE user_id = %s AND conversation_id = %s
                """,
                (user_id, conversation_id),
            )
            documents = await cur.fetchall()

    if not documents:
        return []

    vector_retriever = _VectorSearchRetriever(
        documents=[
            Document(
                page_content=row["content"],
                metadata={
                    "document_id": row["id"],
                    "filename": row["filename"],
                    "page_number": row["page_number"],
                    "chunk_index": row["chunk_index"],
                    "start_index": row["start_index"],
                },
            )
            for row in vector_results
        ]
    )
    bm25_retriever = BM25Retriever.from_documents(
        [
            Document(
                page_content=row["content"],
                metadata={
                    "document_id": row["id"],
                    "filename": row["filename"],
                    "page_number": row["page_number"],
                    "chunk_index": row["chunk_index"],
                    "start_index": row["start_index"],
                },
            )
            for row in documents
        ]
    )
    bm25_retriever.k = candidate_limit

    ensemble_retriever = EnsembleRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        weights=[VECTOR_SEARCH_WEIGHT, BM25_SEARCH_WEIGHT],
        id_key="document_id",
    )
    results = await asyncio.to_thread(ensemble_retriever.invoke, query)

    if RERANKING_ENABLED and results:
        try:
            reranked = await asyncio.to_thread(
                _rerank_documents,
                results,
                query,
                limit,
            )
            results = list(reranked)
        except Exception:
            logger.exception("Document reranking failed; using the hybrid ranking")

    if MIN_RELEVANCE_SCORE is not None:
        if results and any("relevance_score" in document.metadata for document in results):
            results = [
                document
                for document in results
                if document.metadata.get("relevance_score", 0.0) >= MIN_RELEVANCE_SCORE
            ]
        else:
            logger.warning(
                "RAG_MIN_RELEVANCE_SCORE is set, but reranker scores are unavailable; "
                "skipping relevance filtering"
            )

    return results[:limit]


async def search_documents(
    query: str,
    user_id: str,
    conversation_id: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
):
    """Return retrieved chunks with source labels for the answer model."""
    results = await retrieve_documents(query, user_id, conversation_id, limit)
    return "\n\n".join(
        f"[Source: {document.metadata.get('filename') or 'Uploaded PDF'}, "
        f"page {document.metadata.get('page_number') or 'unknown'}]\n"
        f"{document.page_content}"
        for document in results[:limit]
    )


class _VectorSearchRetriever(BaseRetriever):
    """Expose the PostgreSQL vector results through LangChain's retriever interface."""

    documents: list[Document]

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        return self.documents
