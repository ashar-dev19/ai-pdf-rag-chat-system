import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.retrieval import ChunkResult

client = TestClient(app)


def _make_chunk(document_id="doc-1", filename="test.pdf", chunk_index=0, score=0.88):
    return ChunkResult(
        document_id=document_id,
        filename=filename,
        chunk_index=chunk_index,
        text="Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
        token_count=18,
        score=score,
    )


@patch("app.services.chat_service._get_client")
@patch("app.services.chat_service.retrieve_chunks", new_callable=AsyncMock)
def test_chat_returns_answer_with_sources(mock_retrieve, mock_gemini_client):
    mock_retrieve.return_value = [_make_chunk()]

    mock_response = MagicMock()
    mock_response.text = "Machine learning lets systems learn from data."
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_gemini_client.return_value = mock_client

    response = client.post("/api/v1/chat/", json={"query": "What is machine learning?"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Machine learning lets systems learn from data."
    assert len(data["sources"]) == 1
    assert data["sources"][0]["filename"] == "test.pdf"
    assert data["sources"][0]["score"] == 0.88


@patch("app.services.chat_service.retrieve_chunks", new_callable=AsyncMock)
def test_chat_returns_fallback_when_no_chunks(mock_retrieve):
    mock_retrieve.return_value = []

    response = client.post("/api/v1/chat/", json={"query": "something not in any document"})

    assert response.status_code == 200
    data = response.json()
    assert "couldn't find" in data["answer"].lower()
    assert data["sources"] == []


@patch("app.services.chat_service._get_client")
@patch("app.services.chat_service.retrieve_chunks", new_callable=AsyncMock)
def test_chat_excerpt_is_truncated_to_200_chars(mock_retrieve, mock_gemini_client):
    long_chunk = _make_chunk()
    long_chunk.text = "A" * 500
    mock_retrieve.return_value = [long_chunk]

    mock_response = MagicMock()
    mock_response.text = "Answer based on long chunk."
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_gemini_client.return_value = mock_client

    response = client.post("/api/v1/chat/", json={"query": "test"})

    assert response.status_code == 200
    assert len(response.json()["sources"][0]["excerpt"]) == 200


def test_chat_rejects_empty_query():
    response = client.post("/api/v1/chat/", json={"query": ""})
    assert response.status_code == 422


@patch("app.services.chat_service._get_client")
@patch("app.services.chat_service.retrieve_chunks", new_callable=AsyncMock)
def test_chat_passes_document_id_to_retrieval(mock_retrieve, mock_gemini_client):
    mock_retrieve.return_value = [_make_chunk(document_id="doc-99")]

    mock_response = MagicMock()
    mock_response.text = "Scoped answer."
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_gemini_client.return_value = mock_client

    client.post(
        "/api/v1/chat/",
        json={"query": "summarize this doc", "document_id": "doc-99"},
    )

    call_kwargs = mock_retrieve.call_args.kwargs
    assert call_kwargs["document_id"] == "doc-99"
