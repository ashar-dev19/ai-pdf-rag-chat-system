import uuid

from fastapi import HTTPException, UploadFile

from app.db.supabase import get_supabase_client

BUCKET_NAME = "pdf-documents"


async def upload_pdf_to_storage(file: UploadFile) -> tuple[str, str]:
    """Upload PDF to Supabase Storage. Returns (storage_path, public_url)."""
    contents = await file.read()
    await file.seek(0)

    unique_name = f"{uuid.uuid4()}/{file.filename}"

    client = get_supabase_client()
    try:
        client.storage.from_(BUCKET_NAME).upload(
            path=unique_name,
            file=contents,
            file_options={"content-type": "application/pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")

    public_url: str = client.storage.from_(BUCKET_NAME).get_public_url(unique_name)
    return unique_name, public_url
