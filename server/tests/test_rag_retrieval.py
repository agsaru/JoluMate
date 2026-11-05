import asyncio
from contextlib import asynccontextmanager

from rag import utils


class FakeCursor:
    def __init__(self, result_sets):
        self.result_sets = iter(result_sets)
        self.queries = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, query, params):
        self.queries.append((query, params))

    async def fetchall(self):
        return next(self.result_sets)


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_instance = cursor

    def cursor(self):
        return self.cursor_instance


class FakePool:
    def __init__(self, connection):
        self.connection_instance = connection

    @asynccontextmanager
    async def connection(self):
        yield self.connection_instance


class FakeEmbeddings:
    def embed_query(self, query):
        return [0.0] * 768


def test_hybrid_retrieval_scopes_both_searches_to_user_and_conversation(monkeypatch):
    vector_rows = [
        {
            "id": 1,
            "content": "Annual leave policy details",
            "filename": "handbook.pdf",
            "page_number": 3,
            "chunk_index": 0,
            "start_index": 0,
        }
    ]
    all_rows = vector_rows + [
        {
            "id": 2,
            "content": "Employees can request sick leave",
            "filename": "handbook.pdf",
            "page_number": 5,
            "chunk_index": 1,
            "start_index": 1000,
        }
    ]
    cursor = FakeCursor([vector_rows, all_rows])
    monkeypatch.setattr(utils, "pool", FakePool(FakeConnection(cursor)))
    monkeypatch.setattr(utils, "query_embeddings", FakeEmbeddings())
    monkeypatch.setattr(utils, "RERANKING_ENABLED", False)

    results = asyncio.run(
        utils.retrieve_documents(
            "annual leave",
            "user-123",
            "conversation-456",
        )
    )

    assert results
    assert len(cursor.queries) == 2
    for query, params in cursor.queries:
        assert "WHERE user_id = %s AND conversation_id = %s" in query or (
            "WHERE user_id = %s" in query and "AND conversation_id = %s" in query
        )
        assert params[0:2] == ("user-123", "conversation-456")


def test_search_documents_includes_filename_and_page_citations(monkeypatch):
    from langchain_core.documents import Document

    async def fake_retrieve_documents(query, user_id, conversation_id, limit):
        return [
            Document(
                page_content="Employees receive annual leave.",
                metadata={"filename": "handbook.pdf", "page_number": 7},
            )
        ]

    monkeypatch.setattr(utils, "retrieve_documents", fake_retrieve_documents)

    result = asyncio.run(
        utils.search_documents("annual leave", "user-123", "conversation-456")
    )

    assert result == (
        "[Source: handbook.pdf, page 7]\n"
        "Employees receive annual leave."
    )
