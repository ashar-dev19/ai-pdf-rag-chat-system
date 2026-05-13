import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_qdrant_hit(score: float, document_id: str = "doc-1", chunk_index: int = 0):
    hit = MagicMock()
    hit.score = score
    hit.payload = {
        "document_id": document_id,
        "filename": "test.pdf",
        "chunk_index": chunk_index,
        "text": f"chunk {chunk_index} text",
        "token_count": 50,
    }
    return hit


@patch("app.services.retrieval_service._get_client")
@patch("app.services.retrieval_service.generate_embeddings", new_callable=AsyncMock)
def test_search_returns_results(mock_embed, mock_qdrant_client):
    mock_embed.return_value = [[0.1] * 768]

    mock_client = MagicMock()
    mock_client.search.return_value = [
        _make_qdrant_hit(score=0.92, chunk_index=0),
        _make_qdrant_hit(score=0.85, chunk_index=1),
    ]
    mock_qdrant_client.return_value = mock_client

    response = client.post("/api/v1/retrieval/search", json={"query": "what is RAG?"})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["query"] == "what is RAG?"
    assert data["results"][0]["score"] == 0.92


@patch("app.services.retrieval_service._get_client")
@patch("app.services.retrieval_service.generate_embeddings", new_callable=AsyncMock)
def test_search_returns_empty_when_no_hits(mock_embed, mock_qdrant_client):
    mock_embed.return_value = [[0.1] * 768]

    mock_client = MagicMock()
    mock_client.search.return_value = []
    mock_qdrant_client.return_value = mock_client

    response = client.post("/api/v1/retrieval/search", json={"query": "unrelated topic"})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["results"] == []


@patch("app.services.retrieval_service._get_client")
@patch("app.services.retrieval_service.generate_embeddings", new_callable=AsyncMock)
def test_search_passes_document_id_filter(mock_embed, mock_qdrant_client):
    mock_embed.return_value = [[0.1] * 768]

    mock_client = MagicMock()
    mock_client.search.return_value = [_make_qdrant_hit(score=0.88, document_id="doc-42")]
    mock_qdrant_client.return_value = mock_client

    response = client.post(
        "/api/v1/retrieval/search",
        json={"query": "explain chapter 1", "document_id": "doc-42"},
    )

    assert response.status_code == 200
    call_kwargs = mock_client.search.call_args.kwargs
    assert call_kwargs["query_filter"] is not None
    assert response.json()["results"][0]["document_id"] == "doc-42"


def test_search_rejects_empty_query():
    response = client.post("/api/v1/retrieval/search", json={"query": ""})
    assert response.status_code == 422


def test_search_rejects_top_k_out_of_range():
    response = client.post(
        "/api/v1/retrieval/search",
        json={"query": "test", "top_k": 50},
    )
    assert response.status_code == 422


@patch("app.services.retrieval_service._get_client")
@patch("app.services.retrieval_service.generate_embeddings", new_callable=AsyncMock)
def test_search_respects_custom_top_k(mock_embed, mock_qdrant_client):
    mock_embed.return_value = [[0.1] * 768]

    mock_client = MagicMock()
    mock_client.search.return_value = [_make_qdrant_hit(score=0.9)]
    mock_qdrant_client.return_value = mock_client

    client.post("/api/v1/retrieval/search", json={"query": "test", "top_k": 3})

    call_kwargs = mock_client.search.call_args.kwargs
    assert call_kwargs["limit"] == 3
