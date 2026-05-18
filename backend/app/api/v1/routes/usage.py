import logging

from fastapi import APIRouter

from app.models.usage import ModelUsage, UsageResponse
from app.services.usage_service import get_overall_usage, get_document_usage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=UsageResponse)
def overall_usage():
    return UsageResponse(models=get_overall_usage())


@router.get("/{document_id}", response_model=UsageResponse)
def document_usage(document_id: str):
    return UsageResponse(models=get_document_usage(document_id))
