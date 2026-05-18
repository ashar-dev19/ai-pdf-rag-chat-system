from typing import List, Optional
from pydantic import BaseModel, Field


class RetrievalQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    document_id: Optional[str] = None   # scope search to one document
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class ChunkResult(BaseModel):
    chunk_index: int
    text: str
    token_count: int
    document_id: str
    filename: str
    score: float


class RetrievalResponse(BaseModel):
    query: str
    results: List[ChunkResult]
    total: int
