import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat, chat_stream

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest):
    try:
        return await chat(
            query=body.query,
            document_id=body.document_id,
            top_k=body.top_k,
            score_threshold=body.score_threshold,
        )
    except Exception as e:
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
            ):
                yield chunk
        except Exception as e:
            logger.error("Stream failed: %s", e)
            yield "data: [ERROR]\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
