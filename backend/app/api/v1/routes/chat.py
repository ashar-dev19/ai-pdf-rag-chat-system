import logging
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat, chat_stream
from app.services.usage_service import log_usage

logger = logging.getLogger(__name__)
router = APIRouter()

_RATE_LIMIT_PATTERNS = ("429", "RESOURCE_EXHAUSTED", "quota", "rate limit")
_OVERLOAD_PATTERNS = ("503", "UNAVAILABLE", "high demand", "try again later")


def _parse_retry_seconds(err_str: str) -> int:
    """Extract retry delay from Gemini/Anthropic error messages."""
    match = re.search(r"retry in\s+(\d+(?:\.\d+)?)\s*s", err_str, re.IGNORECASE)
    if match:
        return max(1, int(float(match.group(1))) + 1)
    return 60


def _is_rate_limit(err: Exception) -> bool:
    msg = str(err)
    return any(p in msg for p in _RATE_LIMIT_PATTERNS)


def _is_overloaded(err: Exception) -> bool:
    msg = str(err)
    return any(p in msg for p in _OVERLOAD_PATTERNS)


@router.post("/", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest):
    try:
        result = await chat(
            query=body.query,
            document_id=body.document_id,
            top_k=body.top_k,
            score_threshold=body.score_threshold,
            provider=body.provider,
        )
        if result.usage and body.document_id:
            log_usage(
                model=result.usage.model,
                input_tokens=result.usage.input_tokens,
                output_tokens=result.usage.output_tokens,
                document_id=body.document_id,
            )
        return result
    except Exception as e:
        if _is_rate_limit(e):
            retry = _parse_retry_seconds(str(e))
            logger.warning("Rate limit hit (provider=%s): retry in %ds", body.provider, retry)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit reached. Please wait {retry} seconds before trying again.",
                headers={"Retry-After": str(retry)},
            )
        if _is_overloaded(e):
            logger.warning("Model overloaded (provider=%s)", body.provider)
            raise HTTPException(
                status_code=503,
                detail="The AI model is experiencing high demand. Please wait 30 seconds and try again.",
                headers={"Retry-After": "30"},
            )
        logger.error("Chat failed: %s", e)
        raise HTTPException(status_code=500, detail="Chat request failed.")


@router.post("/stream")
async def chat_stream_endpoint(body: ChatRequest):
    async def generator():
        try:
            async for chunk in chat_stream(
                query=body.query,
                document_id=body.document_id,
                top_k=body.top_k,
                score_threshold=body.score_threshold,
                provider=body.provider,
            ):
                yield chunk
        except Exception as e:
            if _is_rate_limit(e):
                retry = _parse_retry_seconds(str(e))
                logger.warning("Stream rate limit hit: retry in %ds", retry)
                yield f"data: [RATE_LIMIT:{retry}]\n\n"
            elif _is_overloaded(e):
                logger.warning("Stream model overloaded")
                yield "data: [RATE_LIMIT:30]\n\n"
            else:
                logger.error("Stream failed: %s", e)
                yield "data: [ERROR]\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
