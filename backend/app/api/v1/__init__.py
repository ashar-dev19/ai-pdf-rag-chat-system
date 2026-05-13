from fastapi import APIRouter
from app.api.v1.routes import health, documents, retrieval

router = APIRouter(prefix="/api/v1")
router.include_router(health.router, tags=["health"])
router.include_router(documents.router, prefix="/documents", tags=["documents"])
router.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
