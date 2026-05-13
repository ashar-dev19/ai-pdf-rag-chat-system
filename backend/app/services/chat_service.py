import logging
from typing import AsyncIterator, List, Optional

from google import genai

from app.core.config import settings
from app.models.chat import ChatResponse, SourceCitation
from app.services.retrieval_service import retrieve_chunks

logger = logging.getLogger(__name__)

CHAT_MODEL = "gemini-2.5-flash"
NO_CONTEXT_REPLY = (
    "I couldn't find relevant information in the uploaded documents to answer your question."
)

_SYSTEM_PROMPT = """\
You are a helpful AI assistant that answers questions strictly based on the document excerpts provided below.

Rules:
- Answer only using the context provided. Do not use outside knowledge.
- If the answer is not present in the context, respond with exactly: "{no_context}"
- Be concise and accurate.
- When relevant, mention which document the information comes from.
""".format(no_context=NO_CONTEXT_REPLY)


def _build_prompt(query: str, chunks: list) -> str:
    context_blocks = []
    for i, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[{i}] Source: {chunk.filename} (chunk {chunk.chunk_index})\n{chunk.text}"
        )
    context = "\n\n".join(context_blocks)
    return f"{_SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {query}\n\nAnswer:"


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


async def chat(
    query: str,
    document_id: Optional[str] = None,
    top_k: int = 5,
    score_threshold: float = 0.5,
) -> ChatResponse:
    chunks = await retrieve_chunks(
        query=query,
        top_k=top_k,
        score_threshold=score_threshold,
        document_id=document_id,
    )

    if not chunks:
        return ChatResponse(
            query=query,
            answer=NO_CONTEXT_REPLY,
            sources=[],
        )

    prompt = _build_prompt(query, chunks)
    client = _get_client()

    response = client.models.generate_content(model=CHAT_MODEL, contents=prompt)
    answer = response.text or NO_CONTEXT_REPLY

    sources = [
        SourceCitation(
            filename=c.filename,
            document_id=c.document_id,
            chunk_index=c.chunk_index,
            excerpt=c.text[:200],
            score=c.score,
        )
        for c in chunks
    ]

    logger.info("Chat: query=%r sources=%d", query[:60], len(sources))
    return ChatResponse(query=query, answer=answer, sources=sources)


async def chat_stream(
    query: str,
    document_id: Optional[str] = None,
    top_k: int = 5,
    score_threshold: float = 0.5,
) -> AsyncIterator[str]:
    """Yield SSE-formatted strings for streaming chat responses."""
    chunks = await retrieve_chunks(
        query=query,
        top_k=top_k,
        score_threshold=score_threshold,
        document_id=document_id,
    )

    if not chunks:
        yield f"data: {NO_CONTEXT_REPLY}\n\n"
        yield "data: [DONE]\n\n"
        return

    prompt = _build_prompt(query, chunks)
    client = _get_client()

    for part in client.models.generate_content_stream(model=CHAT_MODEL, contents=prompt):
        if part.text:
            # Escape newlines so each SSE message stays on one line
            escaped = part.text.replace("\n", "\\n")
            yield f"data: {escaped}\n\n"

    yield "data: [DONE]\n\n"
