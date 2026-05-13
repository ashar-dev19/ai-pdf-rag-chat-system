import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File

from app.db.supabase import get_supabase_client
from app.models.document import DocumentCreate, DocumentResponse, DocumentStatus
from app.services.chunking_service import chunk_text
from app.services.embedding_service import generate_embeddings
from app.services.pdf_service import validate_and_parse_pdf
from app.services.storage_service import upload_pdf_to_storage
from app.services.vector_service import ensure_collection, store_chunks

logger = logging.getLogger(__name__)
router = APIRouter()

DOCUMENTS_TABLE = "documents"


async def _process_chunks(document_id: str, filename: str, extracted_text: str) -> None:
    """Background task: chunk → embed → store in Qdrant, then mark document ready."""
    client = get_supabase_client()
    try:
        chunks = chunk_text(extracted_text)
        if not chunks:
            logger.warning("No chunks produced for document_id=%s", document_id)
            return

        texts = [c.text for c in chunks]
        embeddings = await generate_embeddings(texts)

        ensure_collection()
        store_chunks(document_id, filename, chunks, embeddings)

        client.table(DOCUMENTS_TABLE).update(
            {"status": DocumentStatus.ready.value}
        ).eq("id", document_id).execute()

        logger.info(
            "Pipeline complete: document_id=%s chunks=%d", document_id, len(chunks)
        )
    except Exception as e:
        logger.error("Pipeline failed for document_id=%s: %s", document_id, e)
        client.table(DOCUMENTS_TABLE).update(
            {"status": DocumentStatus.failed.value}
        ).eq("id", document_id).execute()


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
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

    background_tasks.add_task(
        _process_chunks,
        document_id=record["id"],
        filename=record["filename"],
        extracted_text=parse_result.extracted_text,
    )

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
