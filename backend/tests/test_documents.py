import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    b"xref\n0 4\n0000000000 65535 f \n"
    b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n9\n%%EOF"
)


def _make_upload(content: bytes, filename: str = "test.pdf", content_type: str = "application/pdf"):
    return {"file": (filename, io.BytesIO(content), content_type)}


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_rejects_non_pdf():
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("doc.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_upload_rejects_oversized_file():
    big_content = b"%PDF-1.4" + b"x" * (21 * 1024 * 1024)
    response = client.post(
        "/api/v1/documents/upload",
        files=_make_upload(big_content),
    )
    assert response.status_code == 400
    assert "size limit" in response.json()["detail"]


def test_upload_rejects_corrupt_pdf():
    response = client.post(
        "/api/v1/documents/upload",
        files=_make_upload(b"%PDF-1.4 this is not real pdf content"),
    )
    assert response.status_code == 400


@patch("app.api.v1.routes.documents.upload_pdf_to_storage")
@patch("app.api.v1.routes.documents.get_supabase_client")
def test_upload_success(mock_client, mock_storage):
    mock_storage.return_value = ("path/to/file.pdf", "https://example.com/file.pdf")

    fake_record = {
        "id": "abc-123",
        "filename": "test.pdf",
        "file_size": len(MINIMAL_PDF),
        "page_count": 1,
        "storage_path": "path/to/file.pdf",
        "status": "processing",
        "created_at": "2026-05-12T00:00:00",
    }
    mock_db = MagicMock()
    mock_db.table.return_value.insert.return_value.execute.return_value.data = [fake_record]
    mock_client.return_value = mock_db

    response = client.post(
        "/api/v1/documents/upload",
        files=_make_upload(MINIMAL_PDF),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["status"] == "processing"


@patch("app.api.v1.routes.documents.get_supabase_client")
def test_list_documents(mock_client):
    fake_records = [
        {
            "id": "abc-123",
            "filename": "test.pdf",
            "file_size": 1024,
            "page_count": 2,
            "storage_path": "path/to/file.pdf",
            "status": "ready",
            "created_at": "2026-05-12T00:00:00",
        }
    ]
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.order.return_value.execute.return_value.data = fake_records
    mock_client.return_value = mock_db

    response = client.get("/api/v1/documents/")
    assert response.status_code == 200
    assert len(response.json()) == 1
