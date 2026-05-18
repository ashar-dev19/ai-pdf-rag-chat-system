from fastapi import APIRouter
from app.api.v1.routes import health, documents, retrieval, chat, usage

router = APIRouter(prefix="/api/v1")
router.include_router(health.router, tags=["health"])
router.include_router(documents.router, prefix="/documents", tags=["documents"])
router.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
router.include_router(chat.router, prefix="/chat", tags=["chat"])
router.include_router(usage.router, prefix="/usage", tags=["usage"])
