import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_generate_embeddings_empty_input():
    from app.services.embedding_service import generate_embeddings
    result = await generate_embeddings([])
    assert result == []


@pytest.mark.asyncio
async def test_generate_embeddings_returns_one_vector_per_text():
    fake_vector = [0.1] * 768

    mock_embedding = MagicMock()
    mock_embedding.values = fake_vector

    mock_response = MagicMock()
    mock_response.embeddings = [mock_embedding]

    mock_client = MagicMock()
    mock_client.models.embed_content.return_value = mock_response

    with patch("app.services.embedding_service._get_client", return_value=mock_client):
        from app.services.embedding_service import generate_embeddings
        result = await generate_embeddings(["a", "b", "c"])

    assert len(result) == 3
    assert all(len(v) == 768 for v in result)


@pytest.mark.asyncio
async def test_generate_embeddings_calls_once_per_text():
    fake_vector = [0.0] * 768

    mock_embedding = MagicMock()
    mock_embedding.values = fake_vector

    mock_response = MagicMock()
    mock_response.embeddings = [mock_embedding]

    mock_client = MagicMock()
    mock_client.models.embed_content.return_value = mock_response

    with patch("app.services.embedding_service._get_client", return_value=mock_client):
        from app.services.embedding_service import generate_embeddings
        result = await generate_embeddings(["text"] * 5)

    assert len(result) == 5
    assert mock_client.models.embed_content.call_count == 5
