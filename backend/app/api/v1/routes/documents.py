import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Response, UploadFile, File

from app.db.supabase import get_supabase_client
from app.models.document import DocumentCreate, DocumentResponse, DocumentStatus
from app.services.chunking_service import chunk_text
from app.services.embedding_service import generate_embeddings
from app.services.pdf_service import validate_and_parse_pdf
from app.services.storage_service import upload_pdf_to_storage
from app.services.vector_service import ensure_collection, store_chunks, delete_document_vectors, delete_all_vectors

logger = logging.getLogger(__name__)
router = APIRouter()

DOCUMENTS_TABLE = "documents"
VALID_PROVIDERS = {"gemini", "voyage_claude"}


async def _process_chunks(
    document_id: str,
    filename: str,
    extracted_text: str,
    provider: str = "gemini",
) -> None:
    """Background task: chunk → embed → store in Qdrant, then mark document ready."""
    client = get_supabase_client()
    try:
        chunks = chunk_text(extracted_text)
        if not chunks:
            logger.warning("No chunks produced for document_id=%s", document_id)
            return

        texts = [c.text for c in chunks]

        if provider == "voyage_claude":
            from app.services.voyage_embedding_service import generate_embeddings as voyage_embed
            from app.services.usage_service import log_usage as _log
            embeddings, voyage_tokens = await voyage_embed(texts)
            _log(model="voyage-3", input_tokens=voyage_tokens, output_tokens=0, document_id=document_id)
        else:
            embeddings = await generate_embeddings(texts)

        ensure_collection(provider)
        store_chunks(document_id, filename, chunks, embeddings, provider)

        client.table(DOCUMENTS_TABLE).update(
            {"status": DocumentStatus.ready.value}
        ).eq("id", document_id).execute()

        logger.info(
            "Pipeline complete: document_id=%s chunks=%d provider=%s",
            document_id, len(chunks), provider,
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
    provider: str = Form(default="gemini"),
):
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Invalid provider. Choose from: {VALID_PROVIDERS}")

    logger.info("Upload request received: %s provider=%s", file.filename, provider)

    parse_result = await validate_and_parse_pdf(file)
    storage_path, _ = await upload_pdf_to_storage(file)

    doc_data = DocumentCreate(
        filename=file.filename or "unnamed.pdf",
        file_size=parse_result.file_size,
        page_count=parse_result.page_count,
        storage_path=storage_path,
        extracted_text=parse_result.extracted_text,
    )

    db = get_supabase_client()
    try:
        result = (
            db.table(DOCUMENTS_TABLE)
            .insert({
                **doc_data.model_dump(),
                "status": DocumentStatus.processing.value,
                "provider": provider,
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
        provider=provider,
    )

    return record


@router.get("/", response_model=List[DocumentResponse])
async def list_documents():
    db = get_supabase_client()
    try:
        result = (
            db.table(DOCUMENTS_TABLE)
            .select("id, filename, file_size, page_count, storage_path, status, provider, created_at")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as e:
        logger.error("DB list failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch documents.")

    return result.data


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    db = get_supabase_client()
    try:
        result = (
            db.table(DOCUMENTS_TABLE)
            .select("id, filename, file_size, page_count, storage_path, status, provider, created_at")
            .eq("id", document_id)
            .single()
            .execute()
        )
    except Exception as e:
        logger.error("DB get failed: id=%s error=%s", document_id, e)
        raise HTTPException(status_code=404, detail="Document not found.")

    return result.data


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: str):
    db = get_supabase_client()
    try:
        result = (
            db.table(DOCUMENTS_TABLE)
            .select("storage_path, provider")
            .eq("id", document_id)
            .single()
            .execute()
        )
    except Exception as e:
        logger.error("DB get for delete failed: id=%s error=%s", document_id, e)
        raise HTTPException(status_code=404, detail="Document not found.")

    record = result.data
    provider = record.get("provider", "gemini")
    storage_path = record.get("storage_path", "")

    # Delete vectors from Qdrant
    try:
        delete_document_vectors(document_id, provider)
    except Exception as e:
        logger.warning("Vector delete failed for document_id=%s: %s", document_id, e)

    # Delete file from Supabase Storage
    try:
        db.storage.from_("pdf-documents").remove([storage_path])
    except Exception as e:
        logger.warning("Storage delete failed for document_id=%s: %s", document_id, e)

    # Delete DB record
    db.table(DOCUMENTS_TABLE).delete().eq("id", document_id).execute()
    logger.info("Deleted document_id=%s", document_id)

    return Response(status_code=204)


@router.delete("/", status_code=204)
async def delete_all_documents():
    db = get_supabase_client()

    # Fetch all documents to get storage paths and providers
    try:
        result = db.table(DOCUMENTS_TABLE).select("id, storage_path, provider").execute()
    except Exception as e:
        logger.error("DB list for delete-all failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch documents.")

    docs = result.data or []

    # Drop Qdrant collections for each provider
    for provider in {"gemini", "voyage_claude"}:
        try:
            delete_all_vectors(provider)
        except Exception as e:
            logger.warning("Vector delete-all failed for provider=%s: %s", provider, e)

    # Delete all files from Supabase Storage
    paths = [d["storage_path"] for d in docs if d.get("storage_path")]
    if paths:
        try:
            db.storage.from_("pdf-documents").remove(paths)
        except Exception as e:
            logger.warning("Storage delete-all failed: %s", e)

    # Delete all DB records
    db.table(DOCUMENTS_TABLE).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    logger.info("Deleted all %d documents", len(docs))

    return Response(status_code=204)
