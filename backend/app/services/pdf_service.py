import io
from dataclasses import dataclass

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


@dataclass
class PDFParseResult:
    page_count: int
    extracted_text: str
    file_size: int


async def validate_and_parse_pdf(file: UploadFile) -> PDFParseResult:
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    contents = await file.read()
    await file.seek(0)

    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds the {MAX_FILE_SIZE_MB}MB size limit.",
        )

    try:
        reader = PdfReader(io.BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse PDF — file may be corrupted.")

    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())

    return PDFParseResult(
        page_count=len(reader.pages),
        extracted_text="\n\n".join(pages),
        file_size=len(contents),
    )
