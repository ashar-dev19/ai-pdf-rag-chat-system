from typing import List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    document_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class SourceCitation(BaseModel):
    filename: str
    document_id: str
    chunk_index: int
    excerpt: str   # first 200 chars of the chunk
    score: float


class ChatResponse(BaseModel):
    query: str
    answer: str
    sources: List[SourceCitation]
