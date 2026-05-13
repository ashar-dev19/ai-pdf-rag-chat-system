import logging
from typing import List

from google import genai

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "models/text-embedding-004"
EMBEDDING_DIMENSIONS = 768
BATCH_SIZE = 100


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Return one 768-dim embedding vector per input text, batched for API limits."""
    if not texts:
        return []

    client = _get_client()
    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        logger.info("Generating embeddings for batch %d-%d", i, i + len(batch) - 1)

        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch,
        )
        batch_embeddings = [e.values for e in response.embeddings]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings
