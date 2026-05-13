from pydantic import BaseModel


class ChunkCreate(BaseModel):
    document_id: str
    chunk_index: int
    text: str
    token_count: int


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    text: str
    token_count: int
