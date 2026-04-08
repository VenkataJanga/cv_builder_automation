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
