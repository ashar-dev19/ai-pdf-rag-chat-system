import logging
from typing import AsyncIterator, List, Optional

from anthropic import AsyncAnthropic

from app.core.config import settings
from app.models.chat import ChatResponse, SourceCitation, UsageInfo
from app.services.retrieval_service import retrieve_chunks

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
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
    context_blocks = [
        f"[{i}] Source: {c.filename} (chunk {c.chunk_index})\n{c.text}"
        for i, c in enumerate(chunks, start=1)
    ]
    context = "\n\n".join(context_blocks)
    return f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"


def _get_client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


async def claude_chat(
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
        provider="voyage_claude",
    )

    if not chunks:
        return ChatResponse(query=query, answer=NO_CONTEXT_REPLY, sources=[])

    prompt = _build_prompt(query, chunks)
    client = _get_client()

    message = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = message.content[0].text if message.content else NO_CONTEXT_REPLY
    usage = UsageInfo(
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
        model=CLAUDE_MODEL,
    )

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

    logger.info(
        "Claude chat: query=%r sources=%d in=%d out=%d",
        query[:60], len(sources), usage.input_tokens, usage.output_tokens,
    )
    return ChatResponse(query=query, answer=answer, sources=sources, usage=usage)


async def claude_chat_stream(
    query: str,
    document_id: Optional[str] = None,
    top_k: int = 5,
    score_threshold: float = 0.5,
) -> AsyncIterator[str]:
    chunks = await retrieve_chunks(
        query=query,
        top_k=top_k,
        score_threshold=score_threshold,
        document_id=document_id,
        provider="voyage_claude",
    )

    if not chunks:
        yield f"data: {NO_CONTEXT_REPLY}\n\n"
        yield "data: [DONE]\n\n"
        return

    prompt = _build_prompt(query, chunks)
    client = _get_client()

    async with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            escaped = text.replace("\n", "\\n")
            yield f"data: {escaped}\n\n"

    yield "data: [DONE]\n\n"
