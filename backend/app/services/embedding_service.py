import asyncio
import logging
from typing import List

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def _embed_texts_sync(texts: List[str]) -> List[List[float]]:
    """Synchronous embedding — runs in a thread to avoid blocking the event loop."""
    client = _get_client()
    embeddings: List[List[float]] = []

    for i, text in enumerate(texts):
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=EMBEDDING_DIMENSIONS,
            ),
        )
        embeddings.append(result.embeddings[0].values)
        logger.info("Embedded %d/%d chunks", i + 1, len(texts))

    return embeddings


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Return one 768-dim embedding vector per input text."""
    if not texts:
        return []

    return await asyncio.to_thread(_embed_texts_sync, texts)
