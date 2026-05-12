from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class DocumentStatus(str, Enum):
    processing = "processing"
    ready = "ready"
    failed = "failed"


class DocumentCreate(BaseModel):
    filename: str
    file_size: int
    page_count: int
    storage_path: str
    extracted_text: str


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    page_count: int
    storage_path: str
    status: DocumentStatus
    created_at: datetime

    class Config:
        from_attributes = True
