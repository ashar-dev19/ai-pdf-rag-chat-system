import asyncio
import logging
from typing import List

import voyageai

from app.core.config import settings

logger = logging.getLogger(__name__)

VOYAGE_MODEL = "voyage-3"
VOYAGE_DIMENSIONS = 1024


def _get_client() -> voyageai.Client:
    return voyageai.Client(api_key=settings.voyage_api_key)


def _embed_sync(texts: List[str], input_type: str) -> tuple[List[List[float]], int]:
    client = _get_client()
    result = client.embed(texts, model=VOYAGE_MODEL, input_type=input_type)
    return result.embeddings, result.total_tokens


async def generate_embeddings(texts: List[str]) -> tuple[List[List[float]], int]:
    """Embed document chunks. Returns (embeddings, total_tokens)."""
    if not texts:
        return [], 0
    return await asyncio.to_thread(_embed_sync, texts, "document")


async def generate_query_embedding(text: str) -> tuple[List[float], int]:
    """Embed a single query. Returns (embedding, total_tokens)."""
    embeddings, total_tokens = await asyncio.to_thread(_embed_sync, [text], "query")
    return embeddings[0], total_tokens
