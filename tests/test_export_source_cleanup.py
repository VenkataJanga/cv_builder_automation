from pathlib import Path
import uuid

import pytest

from src.application.services.document_cv_service import DocumentCVService
from src.interfaces.rest.routers.export_router import _cleanup_export_source_files


def _unique_name(prefix: str, suffix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}{suffix}"


@pytest.fixture
def uploads_dir() -> Path:
    path = Path("data/storage/uploads")
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_invalid_session_upload_does_not_create_orphan_file(uploads_dir: Path):
    service = DocumentCVService(session_store={})

    session_id = _unique_name("missing-session", "")
    filename = _unique_name("resume", ".docx")
    expected_path = uploads_dir / f"{session_id}_{filename}"
    if expected_path.exists():
        expected_path.unlink()

    with pytest.raises(Exception):
        service.upload_cv_document(
            session_id=session_id,
            file_content=b"dummy-bytes",
            filename=filename,
        )

    assert not expected_path.exists(), "No upload file should be written for invalid sessions"


def test_cleanup_export_source_file_removes_uploaded_source(uploads_dir: Path):
    source_path = uploads_dir / _unique_name("session", "_resume.docx")
    source_path.write_bytes(b"test-doc")

    session = {
        "document_metadata": {
            "saved_path": str(source_path)
        }
    }

    _cleanup_export_source_files(session=session, session_id=_unique_name("s", ""))

    assert not source_path.exists(), "Uploaded source file should be removed after export"


def test_cleanup_export_source_file_does_not_delete_outside_uploads_root(tmp_path: Path):
    outside_path = tmp_path / _unique_name("outside", ".docx")
    outside_path.write_bytes(b"outside-doc")

    session = {
        "document_metadata": {
            "saved_path": str(outside_path)
        }
    }

    _cleanup_export_source_files(session=session, session_id=_unique_name("s", ""))

    assert outside_path.exists(), "Cleanup must not delete files outside uploads root"

    outside_path.unlink()
