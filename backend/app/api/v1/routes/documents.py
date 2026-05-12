import logging
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.db.supabase import get_supabase_client
from app.models.document import DocumentCreate, DocumentResponse, DocumentStatus
from app.services.pdf_service import validate_and_parse_pdf
from app.services.storage_service import upload_pdf_to_storage

logger = logging.getLogger(__name__)
router = APIRouter()

DOCUMENTS_TABLE = "documents"


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(file: UploadFile = File(...)):
    logger.info("Upload request received: %s", file.filename)

    parse_result = await validate_and_parse_pdf(file)

    storage_path, _ = await upload_pdf_to_storage(file)

    doc_data = DocumentCreate(
        filename=file.filename or "unnamed.pdf",
        file_size=parse_result.file_size,
        page_count=parse_result.page_count,
        storage_path=storage_path,
        extracted_text=parse_result.extracted_text,
    )

    client = get_supabase_client()
    try:
        result = (
            client.table(DOCUMENTS_TABLE)
            .insert({
                **doc_data.model_dump(),
                "status": DocumentStatus.processing.value,
            })
            .execute()
        )
    except Exception as e:
        logger.error("DB insert failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save document metadata.")

    record = result.data[0]
    logger.info("Document saved: id=%s filename=%s", record["id"], record["filename"])
    return record


@router.get("/", response_model=List[DocumentResponse])
async def list_documents():
    client = get_supabase_client()
    try:
        result = (
            client.table(DOCUMENTS_TABLE)
            .select("id, filename, file_size, page_count, storage_path, status, created_at")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as e:
        logger.error("DB list failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch documents.")

    return result.data


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    client = get_supabase_client()
    try:
        result = (
            client.table(DOCUMENTS_TABLE)
            .select("id, filename, file_size, page_count, storage_path, status, created_at")
            .eq("id", document_id)
            .single()
            .execute()
        )
    except Exception as e:
        logger.error("DB get failed: id=%s error=%s", document_id, e)
        raise HTTPException(status_code=404, detail="Document not found.")

    return result.data
