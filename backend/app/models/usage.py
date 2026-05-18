from typing import List
from pydantic import BaseModel


class ModelUsage(BaseModel):
    model: str
    total_input_tokens: int
    total_output_tokens: int
    total_requests: int
    today_requests: int = 0
    last_minute_requests: int = 0


class UsageResponse(BaseModel):
    models: List[ModelUsage]
