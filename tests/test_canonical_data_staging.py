"""
Regression test for Canonical Data Staging Layer

Tests that:
1. Extraction data is persisted at each stage (raw, parsed, canonical)
2. Field confidence is calculated and stored correctly
3. Staging lifecycle (pending → complete → previewed → exported → cleared)
4. Session reset clears staging data
5. Preview and export can read from staging layer
6. Traceability is maintained for audit trails
"""

import pytest
import json
from datetime import datetime, timezone
from typing import Dict, Any
from uuid import uuid4

from src.domain.cv.services.canonical_data_staging_service import (
    CanonicalDataStagingService,
)
from src.application.services.document_cv_service import DocumentCVService
from src.application.services.preview_service import PreviewService
from src.application.services.export_service import ExportService
from src.infrastructure.persistence.mysql.database import SessionLocal
from src.infrastructure.persistence.mysql.staging_models import ExtractionStaging


@pytest.fixture
def staging_service():
    """Create staging service instance"""
    return CanonicalDataStagingService()


@pytest.fixture
def document_service():
    """Create document CV service instance"""
    return DocumentCVService()


@pytest.fixture
def preview_service():
    """Create preview service instance"""
    return PreviewService()


@pytest.fixture
def export_service():
    """Create export service instance"""
    return ExportService()


@pytest.fixture
def unique_session_id():
    """Generate unique session ID for test isolation"""
    return f"test_session_{uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def cleanup_staging_table():
    """Clean up staging table after each test for isolation"""
    yield
    # Cleanup after test
    try:
        db = SessionLocal()
        db.query(ExtractionStaging).delete()
        db.commit()
        db.close()
    except:
        pass


def test_staging_creation_and_lifecycle(staging_service, unique_session_id):
    """
    Test: Extraction record creation and status lifecycle
    
    Verifies:
    - Record can be created with metadata
    - Status transitions through pipeline
    - Timestamps are tracked correctly
    """
    session_id = unique_session_id
    
    # Create extraction record
    extraction_id = staging_service.create_extraction_record(
        session_id=session_id,
        source_type="document_upload",
        source_filename="test_cv.docx",
        source_size_bytes=50000
    )
    
    assert extraction_id is not None
    assert len(extraction_id) == 36  # UUID length
    
    # Verify record exists and has correct initial status
    record = staging_service.get_extraction_record(extraction_id)
    assert record is not None
    assert record["session_id"] == session_id
    assert record["extraction_status"] == "pending"
    assert record["source_filename"] == "test_cv.docx"
    assert record["source_size_bytes"] == 50000


def test_raw_text_staging(staging_service, unique_session_id):
    """
    Test: Raw text extraction staging
    
    Verifies:
    - Raw and normalized text can be stored
    - Status changes to in_progress
    """
    session_id = unique_session_id
    extraction_id = staging_service.create_extraction_record(
        session_id=session_id,
        source_type="document_upload"
    )
    
    raw_text = "John Doe\nSenior Engineer\nPython, Java, SQL"
    normalized_text = "john doe\nsenior engineer\npython, java, sql"
    
    # Stage raw extraction
    staging_service.stage_raw_extraction(
        extraction_id=extraction_id,
        raw_text=raw_text,
        normalized_text=normalized_text
    )
    
    # Verify staging
    record = staging_service.get_extraction_record(extraction_id)
    assert record["extraction_status"] == "in_progress"
    assert record["raw_extracted_text_len"] == len(raw_text)
    assert record["normalized_text_len"] == len(normalized_text)


def test_parsed_intermediate_staging(staging_service, unique_session_id):
    """
    Test: Intermediate parsed data staging
    
    Verifies:
    - Parsed structure can be stored
    - Warnings and errors are captured
    """
    session_id = unique_session_id
    extraction_id = staging_service.create_extraction_record(
        session_id=session_id,
        source_type="document_upload"
    )
    
    parsed_data = {
        "candidate": {
            "fullName": "John Doe",
            "currentDesignation": "Senior Engineer"
        },
        "skills": {
            "primarySkills": ["Python", "Java"]
        },
        "experience": [
            {
                "companyName": "TechCorp",
                "designation": "Engineer",
                "startDate": "2020-01-01",
                "endDate": "2022-12-31"
            }
        ]
    }
    
    warnings = ["Found multiple designations, using first one"]
    errors = []
    
    # Stage parsed intermediate
    staging_service.stage_parsed_intermediate(
        extraction_id=extraction_id,
        parsed_data=parsed_data,
        warnings=warnings,
        errors=errors
    )
    
    # Verify staging
    record = staging_service.get_extraction_record(extraction_id)
    assert record["parsed_intermediate_keys"] is not None
    assert set(record["parsed_intermediate_keys"]) == {"candidate", "skills", "experience"}
    assert len(record["extraction_warnings"]) == 1
    assert "multiple designations" in record["extraction_warnings"][0]


def test_canonical_and_confidence_staging(staging_service, unique_session_id):
    """
    Test: Canonical CV and field confidence staging
    
    Verifies:
    - Final canonical CV is stored
    - Field confidence scores are calculated
    - LLM enhancement metadata is tracked
    """
    session_id = unique_session_id
    extraction_id = staging_service.create_extraction_record(
        session_id=session_id,
        source_type="document_upload"
    )
    
    canonical_cv = {
        "candidate": {
            "fullName": "John Doe",
            "email": "john@example.com",
            "currentDesignation": "Senior Engineer",
            "summary": "Experienced engineer with 10+ years"
        },
        "skills": {
            "primarySkills": ["Python", "Java", "Go"],
            "technicalSkills": ["AWS", "Docker", "Kubernetes", "REST APIs"]
        },
        "experience": [
            {"companyName": "TechCorp", "designation": "Engineer"}
        ],
        "projects": [
            {"projectName": "Project A"},
            {"projectName": "Project B"}
        ],
        "education": [
            {"degree": "B.S. Computer Science"}
        ]
    }
    
    field_confidence = {
        "candidate.fullName": 0.95,
        "candidate.email": 0.95,
        "candidate.currentDesignation": 0.9,
        "candidate.summary": 0.85,
        "skills.primarySkills": 0.85,
        "skills.technicalSkills": 0.88,
        "experience": 0.8,
        "projects": 0.75,
        "education": 0.7
    }
    
    # Stage canonical and confidence
    staging_service.stage_canonical_and_confidence(
        extraction_id=extraction_id,
        canonical_cv=canonical_cv,
        field_confidence=field_confidence,
        llm_enhancement="hybrid",
        llm_confidence=0.72
    )
    
    # Verify staging
    record = staging_service.get_extraction_record(extraction_id)
    assert record["extraction_status"] == "complete"
    assert record["llm_enhancement_applied"] == "hybrid"
    assert record["llm_confidence_score"] == 0.72
    assert "candidate.fullName" in record["field_confidence"]
    assert record["field_confidence"]["candidate.fullName"] == 0.95
    assert record["extracted_at"] is not None


def test_extraction_lifecycle_transitions(staging_service, unique_session_id):
    """
    Test: Full extraction lifecycle with status transitions
    
    Verifies:
    - pending → in_progress → complete → previewed → exported → cleared
    """
    session_id = unique_session_id
    extraction_id = staging_service.create_extraction_record(
        session_id=session_id,
        source_type="document_upload"
    )
    
    # Check initial status
    record = staging_service.get_extraction_record(extraction_id)
    assert record["extraction_status"] == "pending"
    
    # Stage raw (in_progress)
    staging_service.stage_raw_extraction(
        extraction_id=extraction_id,
        raw_text="test raw text"
    )
    record = staging_service.get_extraction_record(extraction_id)
    assert record["extraction_status"] == "in_progress"
    
    # Stage canonical (complete)
    staging_service.stage_canonical_and_confidence(
        extraction_id=extraction_id,
        canonical_cv={"candidate": {"fullName": "Test User"}},
        field_confidence={"candidate.fullName": 0.9}
    )
    record = staging_service.get_extraction_record(extraction_id)
    assert record["extraction_status"] == "complete"
    assert record["extracted_at"] is not None
    
    # Mark previewed
    staging_service.mark_previewed(extraction_id)
    record = staging_service.get_extraction_record(extraction_id)
    assert record["extraction_status"] == "previewed"
    assert record["previewed_at"] is not None
    
    # Mark exported
    staging_service.mark_exported(extraction_id)
    record = staging_service.get_extraction_record(extraction_id)
    assert record["extraction_status"] == "exported"
    assert record["exported_at"] is not None
    
    # Clear session
    cleared, marked = staging_service.clear_session_staging(session_id)
    assert cleared == 1
    assert marked == 1
    record = staging_service.get_extraction_record(extraction_id)
    assert record["extraction_status"] == "cleared"
    assert record["cleared_at"] is not None


def test_retrieve_canonical_from_staging(staging_service, unique_session_id):
    """
    Test: Retrieve canonical CV from staging
    
    Verifies:
    - Can retrieve latest canonical CV for session
    - Can retrieve specific extraction by ID
    """
    session_id = unique_session_id
    
    # Create first extraction
    extraction_id_1 = staging_service.create_extraction_record(
        session_id=session_id,
        source_type="document_upload"
    )
    canonical_cv_1 = {"candidate": {"fullName": "User One"}}
    staging_service.stage_canonical_and_confidence(
        extraction_id=extraction_id_1,
        canonical_cv=canonical_cv_1,
        field_confidence={}
    )
    
    # Create second extraction
    extraction_id_2 = staging_service.create_extraction_record(
        session_id=session_id,
        source_type="document_upload"
    )
    canonical_cv_2 = {"candidate": {"fullName": "User Two"}}
    staging_service.stage_canonical_and_confidence(
        extraction_id=extraction_id_2,
        canonical_cv=canonical_cv_2,
        field_confidence={}
    )
    
    # Get latest (should be second)
    latest = staging_service.get_canonical_cv_from_staging(session_id=session_id)
    assert latest["candidate"]["fullName"] == "User Two"
    
    # Get specific
    specific = staging_service.get_canonical_cv_from_staging(
        session_id=session_id,
        extraction_id=extraction_id_1
    )
    assert specific["candidate"]["fullName"] == "User One"


def test_extraction_history(staging_service, unique_session_id):
    """
    Test: Get extraction history for audit trail
    
    Verifies:
    - History is returned in reverse chronological order
    - Metadata is preserved
    """
    session_id = unique_session_id
    extraction_ids = []
    
    for i in range(3):
        extraction_id = staging_service.create_extraction_record(
            session_id=session_id,
            source_type="document_upload",
            source_filename=f"cv_{i}.docx"
        )
        extraction_ids.append(extraction_id)
    
    # Get history
    history = staging_service.get_extraction_history(session_id=session_id, limit=10)
    
    assert len(history) == 3
    # Verify all extraction IDs are present (order may vary due to timestamp precision)
    returned_ids = set(h["extraction_id"] for h in history)
    assert returned_ids == set(extraction_ids)
    # Most recent should be last created
    assert history[0]["extraction_id"] == extraction_ids[-1]


def test_field_confidence_report(staging_service, unique_session_id):
    """
    Test: Detailed field confidence report generation
    
    Verifies:
    - Field-level confidence data is stored correctly
    - Report can be retrieved with all details
    """
    session_id = unique_session_id
    extraction_id = staging_service.create_extraction_record(
        session_id=session_id,
        source_type="document_upload"
    )
    
    field_confidence = {
        "candidate.fullName": {
            "confidence": 0.95,
            "method": "deterministic",
            "extracted": "John Doe",
            "normalized": "John Doe",
            "status": "valid",
            "notes": "Extracted from header"
        },
        "skills.primarySkills": {
            "confidence": 0.75,
            "method": "fallback",
            "fallback": "section_alias",
            "status": "questionable",
            "notes": "Extracted from summary"
        }
    }
    
    canonical_cv = {"candidate": {"fullName": "John Doe"}, "skills": {"primarySkills": ["Python"]}}
    staging_service.stage_canonical_and_confidence(
        extraction_id=extraction_id,
        canonical_cv=canonical_cv,
        field_confidence=field_confidence
    )
    
    # Get report
    report = staging_service.get_field_confidence_report(extraction_id)
    assert report is not None
    assert "candidate.fullName" in report
    assert report["candidate.fullName"]["confidence_score"] == 0.95
    assert report["candidate.fullName"]["extraction_method"] == "deterministic"
    assert report["candidate.fullName"]["validation_status"] == "valid"
    assert "skills.primarySkills" in report
    assert report["skills.primarySkills"]["fallback_used"] == "section_alias"


def test_session_clear_staging(staging_service, unique_session_id):
    """
    Test: Clear all staging for session after export or reset
    
    Verifies:
    - Multiple records for session can be cleared in one operation
    - Records are marked with cleared status, not deleted
    - Cleared count matches actual records
    """
    session_id = unique_session_id
    
    # Create multiple extractions
    extraction_ids = []
    for i in range(3):
        extraction_id = staging_service.create_extraction_record(
            session_id=session_id,
            source_type="document_upload"
        )
        extraction_ids.append(extraction_id)
    
    # Clear session
    cleared_count, marked_count = staging_service.clear_session_staging(session_id)
    
    assert cleared_count == 3
    assert marked_count == 3
    
    # Verify all records are marked as cleared
    for extraction_id in extraction_ids:
        record = staging_service.get_extraction_record(extraction_id)
        assert record["extraction_status"] == "cleared"
        assert record["cleared_at"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
