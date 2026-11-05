import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from fastapi import HTTPException

from chat import router


class FakeCursor:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.queries = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, query, params):
        self.queries.append((query, params))

    async def fetchone(self):
        return next(self.rows)

    async def fetchall(self):
        return []


class FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = FakeCursor(rows)

    def cursor(self):
        return self.cursor_instance


class FakeFile:
    content_type = "application/pdf"
    filename = "sample.pdf"

    def __init__(self):
        self.consumed = False

    async def read(self, size):
        if not self.consumed:
            self.consumed = True
            return b"%PDF-1.7\ntext"
        return b""


def run(coroutine):
    return asyncio.run(coroutine)


def test_invalid_conversation_id_returns_bad_request():
    with pytest.raises(HTTPException) as error:
        router.validate_conversation_id("not-a-uuid")

    assert error.value.status_code == 400


def test_missing_chat_conversation_returns_not_found():
    connection = FakeConnection([None])

    with pytest.raises(HTTPException) as error:
        run(
            router.get_chat_history(
                str(uuid4()),
                conn=connection,
                user={"id": str(uuid4())},
            )
        )

    assert error.value.status_code == 404
    assert len(connection.cursor_instance.queries) == 1


def test_pdf_processing_holds_conversation_lock(monkeypatch):
    conversation_id = str(uuid4())
    connection = FakeConnection([{"id": conversation_id}])
    lock_states = []

    @asynccontextmanager
    async def fake_lock(value):
        lock_states.append(("entered", value))
        yield
        lock_states.append(("exited", value))

    async def fake_process_pdf(content, user_id, value, filename):
        lock_states.append(("processed", value, filename))
        return {"chunks_processed": 1, "pages_without_text": [2], "total_pages": 3}

    monkeypatch.setattr(router, "conversation_lock", fake_lock)
    monkeypatch.setattr(router, "process_pdf", fake_process_pdf)

    response = run(
        router.upload_file(
            request=None,
            conversation_id=conversation_id,
            file=FakeFile(),
            conn=connection,
            user={"id": str(uuid4())},
        )
    )

    assert response.chunks_processed == 1
    assert response.pages_without_text == [2]
    assert "page(s) skipped" in response.message
    assert lock_states == [
        ("entered", conversation_id),
        ("processed", conversation_id, "sample.pdf"),
        ("exited", conversation_id),
    ]


def test_pdf_provider_failure_is_not_reported_as_invalid_pdf(monkeypatch):
    conversation_id = str(uuid4())
    connection = FakeConnection([{"id": conversation_id}])

    @asynccontextmanager
    async def fake_lock(value):
        yield

    async def fake_process_pdf(content, user_id, value, filename):
        raise RuntimeError("embedding provider unavailable")

    monkeypatch.setattr(router, "conversation_lock", fake_lock)
    monkeypatch.setattr(router, "process_pdf", fake_process_pdf)

    with pytest.raises(HTTPException) as error:
        run(
            router.upload_file(
                request=None,
                conversation_id=conversation_id,
                file=FakeFile(),
                conn=connection,
                user={"id": str(uuid4())},
            )
        )

    assert error.value.status_code == 502
    assert "temporarily unavailable" in error.value.detail


def test_pdf_with_no_searchable_text_is_rejected(monkeypatch):
    conversation_id = str(uuid4())
    connection = FakeConnection([{"id": conversation_id}])

    @asynccontextmanager
    async def fake_lock(value):
        yield

    async def fake_process_pdf(content, user_id, value, filename):
        return {
            "chunks_processed": 0,
            "pages_without_text": [1, 2],
            "total_pages": 2,
        }

    monkeypatch.setattr(router, "conversation_lock", fake_lock)
    monkeypatch.setattr(router, "process_pdf", fake_process_pdf)

    with pytest.raises(HTTPException) as error:
        run(
            router.upload_file(
                request=None,
                conversation_id=conversation_id,
                file=FakeFile(),
                conn=connection,
                user={"id": str(uuid4())},
            )
        )

    assert error.value.status_code == 422
    assert "No searchable text" in error.value.detail


def test_password_protected_pdf_has_clear_error(monkeypatch):
    from pypdf.errors import FileNotDecryptedError

    conversation_id = str(uuid4())
    connection = FakeConnection([{"id": conversation_id}])

    @asynccontextmanager
    async def fake_lock(value):
        yield

    async def fake_process_pdf(content, user_id, value, filename):
        raise FileNotDecryptedError("PDF is encrypted")

    monkeypatch.setattr(router, "conversation_lock", fake_lock)
    monkeypatch.setattr(router, "process_pdf", fake_process_pdf)

    with pytest.raises(HTTPException) as error:
        run(
            router.upload_file(
                request=None,
                conversation_id=conversation_id,
                file=FakeFile(),
                conn=connection,
                user={"id": str(uuid4())},
            )
        )

    assert error.value.status_code == 422
    assert "password-protected" in error.value.detail
