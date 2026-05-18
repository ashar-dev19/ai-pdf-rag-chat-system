import logging
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.config import settings
from app.models.retrieval import ChunkResult
from app.services.embedding_service import generate_embeddings
from app.services.vector_service import get_collection_name

logger = logging.getLogger(__name__)


def _get_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


async def retrieve_chunks(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.5,
    document_id: Optional[str] = None,
    provider: str = "gemini",
) -> List[ChunkResult]:
    """Embed query and search the correct Qdrant collection for the given provider."""
    if provider == "voyage_claude":
        from app.services.voyage_embedding_service import generate_query_embedding
        from app.services.usage_service import log_usage
        query_vector, voyage_tokens = await generate_query_embedding(query)
        log_usage(model="voyage-3", input_tokens=voyage_tokens, output_tokens=0, document_id=document_id)
    else:
        query_vectors = await generate_embeddings([query])
        query_vector = query_vectors[0]

    collection_name = get_collection_name(provider)

    search_filter = None
    if document_id:
        search_filter = Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        )

    client = _get_client()
    hits = client.search(
        collection_name=collection_name,
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
        "Retrieval: query=%r top_k=%d threshold=%.2f document_id=%s provider=%s → %d results",
        query[:60], top_k, score_threshold, document_id, provider, len(results),
    )
    return results
