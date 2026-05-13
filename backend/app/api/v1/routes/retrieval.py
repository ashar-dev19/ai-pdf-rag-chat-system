import logging

from fastapi import APIRouter, HTTPException

from app.models.retrieval import RetrievalQuery, RetrievalResponse
from app.services.retrieval_service import retrieve_chunks

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/search", response_model=RetrievalResponse)
async def search(body: RetrievalQuery):
    try:
        results = await retrieve_chunks(
            query=body.query,
            top_k=body.top_k,
            score_threshold=body.score_threshold,
            document_id=body.document_id,
        )
    except Exception as e:
        logger.error("Retrieval failed: %s", e)
        raise HTTPException(status_code=500, detail="Retrieval failed. Check that Qdrant is running and the collection exists.")

    return RetrievalResponse(
        query=body.query,
        results=results,
        total=len(results),
    )
