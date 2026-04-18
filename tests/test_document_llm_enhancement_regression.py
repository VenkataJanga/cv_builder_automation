from __future__ import annotations

from typing import Any

import pytest

from src.application.services.document_cv_service import DocumentCVService
from src.core.config.settings import settings


class _ValidationResult:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload


class _FakeValidationService:
    def validate_for_save_and_validate(self, canonical_cv: dict[str, Any]) -> _ValidationResult:
        return _ValidationResult(
            {
                "can_save": True,
                "can_export": True,
                "errors": [],
                "warnings": [],
                "completeness_score": 1.0,
            }
        )


class _FakeMergeService:
    def merge_canonical_cvs(
        self,
        existing_cv: dict[str, Any],
        new_data: dict[str, Any],
        source_type: Any,
        operation: str,
    ) -> dict[str, Any]:
        merged = dict(existing_cv or {})
        merged.update(new_data or {})
        return merged


class _FakeDocumentParser:
    def __init__(self, canonical_cv: dict[str, Any], extracted_text: str = "raw document text") -> None:
        self._canonical_cv = canonical_cv
        self._extracted_text = extracted_text

    def parse_document_to_canonical(self, file_path: str, session_id: str | None = None, file_metadata: dict | None = None) -> dict[str, Any]:
        return dict(self._canonical_cv)

    def extract_text(self, file_path: str) -> str:
        return self._extracted_text


class _FakeExtractionService:
    def __init__(self, result: dict[str, Any]) -> None:
        self._result = result
        self.called = False

    def extract_and_merge(self, raw_text: str, existing_cv_data: dict[str, Any], context: dict[str, Any], merge_strategy: str) -> dict[str, Any]:
        self.called = True
        return self._result


@pytest.fixture()
def _reset_flags() -> None:
    old_extract = settings.ENABLE_LLM_EXTRACTION
    old_normalize = settings.ENABLE_LLM_NORMALIZATION
    try:
        yield
    finally:
        settings.ENABLE_LLM_EXTRACTION = old_extract
        settings.ENABLE_LLM_NORMALIZATION = old_normalize


def test_document_upload_llm_enhancement_fills_missing_but_preserves_deterministic(_reset_flags: None) -> None:
    settings.ENABLE_LLM_EXTRACTION = True
    settings.ENABLE_LLM_NORMALIZATION = True

    session_store = {"s1": {"session_id": "s1"}}
    deterministic_canonical = {
        "candidate": {
            "fullName": "Deterministic Name",
            "email": "deterministic@example.com",
            "currentDesignation": "Data Engineer",
        },
        "skills": {},
        "experience": {},
        "education": [],
    }

    extraction_result = {
        "success": True,
        "source": "llm",
        "normalized_text": "Professionally normalized content",
        "warnings": [],
        "extracted_fields": {
            "personal_details": {
                "full_name": "LLM Name Should Not Override",
                "phone": "+91-9000000000",
                "current_title": "LLM Title Should Not Override",
            },
            "skills": {
                "primary_skills": ["Python", "SQL"],
            },
        },
    }

    service = DocumentCVService(
        session_store=session_store,
        merge_service=_FakeMergeService(),
        validation_service=_FakeValidationService(),
    )
    service.document_parser = _FakeDocumentParser(deterministic_canonical)
    fake_extractor = _FakeExtractionService(extraction_result)
    service.extraction_service = fake_extractor

    result = service.process_document_upload(session_id="s1", file_path="resume.docx", file_metadata={"filename": "resume.docx"})

    assert fake_extractor.called is True
    candidate = result["canonical_cv"]["candidate"]
    assert candidate["fullName"] == "Deterministic Name"
    assert candidate["currentDesignation"] == "Data Engineer"
    assert candidate["phoneNumber"] == "+91-9000000000"
    assert result["canonical_cv"]["skills"]["primarySkills"] == ["Python", "SQL"]
    assert result["canonical_cv"]["metadata"]["llmEnhancement"]["applied"] is True


def test_document_upload_skips_llm_when_flags_disabled(_reset_flags: None) -> None:
    settings.ENABLE_LLM_EXTRACTION = False
    settings.ENABLE_LLM_NORMALIZATION = False

    session_store = {"s1": {"session_id": "s1"}}
    deterministic_canonical = {
        "candidate": {"fullName": "Deterministic Name"},
        "skills": {},
        "experience": {},
        "education": [],
    }

    service = DocumentCVService(
        session_store=session_store,
        merge_service=_FakeMergeService(),
        validation_service=_FakeValidationService(),
    )
    service.document_parser = _FakeDocumentParser(deterministic_canonical)
    fake_extractor = _FakeExtractionService({"success": True, "extracted_fields": {}})
    service.extraction_service = fake_extractor

    result = service.process_document_upload(session_id="s1", file_path="resume.docx", file_metadata={"filename": "resume.docx"})

    assert fake_extractor.called is False
    assert result["canonical_cv"]["candidate"]["fullName"] == "Deterministic Name"
    assert "metadata" not in result["canonical_cv"] or "llmEnhancement" not in result["canonical_cv"].get("metadata", {})
