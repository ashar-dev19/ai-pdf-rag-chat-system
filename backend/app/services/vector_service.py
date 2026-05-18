import logging
import uuid
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, FilterSelector, MatchValue, PointStruct, VectorParams

from app.core.config import settings
from app.services.chunking_service import TextChunk

logger = logging.getLogger(__name__)

COLLECTION_GEMINI = "pdf-chunks-gemini"
COLLECTION_VOYAGE = "pdf-chunks-voyage"

_COLLECTION_CONFIG: dict[str, tuple[str, int]] = {
    "gemini": (COLLECTION_GEMINI, 768),
    "voyage_claude": (COLLECTION_VOYAGE, 1024),
}


def get_collection_name(provider: str) -> str:
    return _COLLECTION_CONFIG[provider][0]


def _get_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def ensure_collection(provider: str = "gemini") -> None:
    collection_name, dims = _COLLECTION_CONFIG[provider]
    client = _get_client()
    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=dims, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection: %s", collection_name)


def store_chunks(
    document_id: str,
    filename: str,
    chunks: List[TextChunk],
    embeddings: List[List[float]],
    provider: str = "gemini",
) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings lists must be the same length")

    collection_name = get_collection_name(provider)
    client = _get_client()
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "document_id": document_id,
                "filename": filename,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "token_count": chunk.token_count,
            },
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]

    client.upsert(collection_name=collection_name, points=points)
    logger.info(
        "Stored %d vectors for document_id=%s in %s", len(points), document_id, collection_name
    )


def delete_document_vectors(document_id: str, provider: str = "gemini") -> None:
    """Remove all vectors belonging to a document from the appropriate collection."""
    collection_name = get_collection_name(provider)
    client = _get_client()
    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        return
    client.delete(
        collection_name=collection_name,
        points_selector=FilterSelector(
            filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            )
        ),
    )
    logger.info("Deleted vectors for document_id=%s from %s", document_id, collection_name)


def delete_all_vectors(provider: str = "gemini") -> None:
    """Drop and recreate the collection for a given provider, clearing all vectors."""
    collection_name, dims = _COLLECTION_CONFIG[provider]
    client = _get_client()
    existing = [c.name for c in client.get_collections().collections]
    if collection_name in existing:
        client.delete_collection(collection_name)
        logger.info("Dropped Qdrant collection: %s", collection_name)
