import logging
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.config import settings
from app.models.retrieval import ChunkResult
from app.services.embedding_service import generate_embeddings
from app.services.vector_service import COLLECTION_NAME

logger = logging.getLogger(__name__)


def _get_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


async def retrieve_chunks(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.5,
    document_id: Optional[str] = None,
) -> List[ChunkResult]:
    """Embed query, search Qdrant, return top-k chunks above score threshold."""
    query_vectors = await generate_embeddings([query])
    query_vector = query_vectors[0]

    search_filter = None
    if document_id:
        search_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        )

    client = _get_client()
    hits = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k,
        score_threshold=score_threshold,
        query_filter=search_filter,
        with_payload=True,
    )

    results: List[ChunkResult] = []
    for hit in hits:
        payload = hit.payload or {}
        results.append(
            ChunkResult(
                chunk_index=payload.get("chunk_index", 0),
                text=payload.get("text", ""),
                token_count=payload.get("token_count", 0),
                document_id=payload.get("document_id", ""),
                filename=payload.get("filename", ""),
                score=round(hit.score, 4),
            )
        )

    logger.info(
        "Retrieval: query=%r top_k=%d threshold=%.2f document_id=%s → %d results",
        query[:60],
        top_k,
        score_threshold,
        document_id,
        len(results),
    )
    return results
