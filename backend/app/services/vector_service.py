import logging
import uuid
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from app.core.config import settings
from app.services.chunking_service import TextChunk
from app.services.embedding_service import EMBEDDING_DIMENSIONS  # 768 for text-embedding-004

logger = logging.getLogger(__name__)

COLLECTION_NAME = "pdf-chunks"


def _get_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def ensure_collection() -> None:
    """Create the Qdrant collection if it doesn't already exist."""
    client = _get_client()
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSIONS,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Created Qdrant collection: %s", COLLECTION_NAME)


def store_chunks(
    document_id: str,
    filename: str,
    chunks: List[TextChunk],
    embeddings: List[List[float]],
) -> None:
    """Upsert chunk vectors into Qdrant with document metadata."""
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings lists must be the same length")

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

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    logger.info(
        "Stored %d vectors for document_id=%s in Qdrant", len(points), document_id
    )
