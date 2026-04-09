import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application.services.hybrid_extraction_service import HybridExtractionService
from src.application.services.speech_service import SpeechService


def test_speech_service_falls_back_to_hybrid_voice_extraction_for_unstructured_transcripts():
    enhanced_transcript = (
        "My first project is data pipeline migration, and client is Contoso. "
        "Project description is built a data ingestion pipeline to move data into Azure Data Lake, "
        "so coming to my roles and responsibilities: designed ETL patterns, implemented orchestration with ADF, "
        "and validated downstream reports. "
        "My second project name is analytics dashboard, client is Fabrikam. "
        "Project description is built Power BI dashboards to surface operational metrics, "
        "so coming to my roles and responsibilities: defined data models and developed interactive reports. "
        "Coming to my educational background I have completed Bachelor of Technology in Computer Science from XYZ University."
    )

    service = SpeechService.__new__(SpeechService)
    service.enhanced_parser = MagicMock()
    service.enhanced_parser.low_confidence.return_value = True
    service.hybrid_extraction_service = HybridExtractionService()

    extracted_data = service._extract_cv_data(enhanced_transcript)

    assert isinstance(extracted_data, dict)
    assert extracted_data["project_experience"], "Expected hybrid voice extraction to populate project_experience"
    assert len(extracted_data["project_experience"]) >= 1
    assert extracted_data["project_experience"][0]["project_name"] == "Data Pipeline Migration"


def test_transcribe_audio_creates_session_when_no_session_id(monkeypatch):
    import asyncio
    import io
    from fastapi import UploadFile
    from src.interfaces.rest.routers import speech_router

    dummy_data = {
        "raw_transcript": "My name is Test User.",
        "normalized_transcript": "My name is Test User.",
        "enhanced_transcript": "My name is Test User.",
        "requires_correction": False,
        "extracted_cv_data": {"personal_details": {"full_name": "Test User"}},
    }

    monkeypatch.setattr(speech_router.speech_service, "transcribe", MagicMock(return_value=dummy_data))

    upload_file = UploadFile(filename="test.webm", file=io.BytesIO(b"dummy audio content"))

    response = asyncio.run(speech_router.transcribe_audio(upload_file, None, None))

    assert response["session_id"], "Expected a new session_id to be created"
    assert response["cv_data"]["personal_details"]["full_name"] == "Test User"
    assert response.get("question") is not None


def test_upload_cv_creates_session_when_no_session_id(monkeypatch):
    import asyncio
    import io
    from fastapi import UploadFile
    from src.interfaces.rest.routers import cv_router

    parsed_data = {"personal_details": {"full_name": "Uploaded User"}}
    monkeypatch.setattr(cv_router.upload_cmd, "execute", MagicMock(return_value=parsed_data))

    upload_file = UploadFile(filename="resume.pdf", file=io.BytesIO(b"dummy pdf content"))

    response = asyncio.run(cv_router.upload_cv(upload_file, None))

    assert response["session_id"], "Expected a new session_id to be created"
    assert response["cv_data"]["personal_details"]["full_name"] == "Uploaded User"
    assert response.get("question") is not None
