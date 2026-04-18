from __future__ import annotations

from src.application.services.export_service import ExportService


def test_export_context_includes_target_role_from_summary() -> None:
    service = ExportService()

    cv_data = {
        "header": {
            "full_name": "Venkata Janga",
            "current_title": "System Intelligency Advisor",
        },
        "summary": {
            "professional_summary": "Experienced engineer.",
            "target_role": "Lead Data Engineer",
        },
        "certifications": [],
    }

    context = service._prepare_docx_context(cv_data)

    assert context["target_role"] == "Lead Data Engineer"


def test_export_context_drops_invalid_placeholder_certification_values() -> None:
    service = ExportService()

    cv_data = {
        "header": {
            "full_name": "Venkata Janga",
        },
        "summary": {
            "professional_summary": "Experienced engineer.",
        },
        "certifications": [
            {"name": "NameVenkata Janga"},
            "",
        ],
    }

    context = service._prepare_docx_context(cv_data)

    # Invalid extracted certification artifact should be filtered out.
    assert context["certifications"] == []
    assert context["certifications_section"] == ""
    assert context["certification"] == ""


def test_export_context_keeps_valid_certification_entries() -> None:
    service = ExportService()

    cv_data = {
        "header": {
            "full_name": "Venkata Janga",
        },
        "summary": {
            "professional_summary": "Experienced engineer.",
        },
        "certifications": [
            {
                "name": "AWS Certified Solutions Architect",
                "issuer": "Amazon",
                "year": "2024",
            }
        ],
    }

    context = service._prepare_docx_context(cv_data)

    assert len(context["certifications"]) == 1
    assert context["certifications"][0]["name"] == "AWS Certified Solutions Architect"
    assert "AWS Certified Solutions Architect" in context["certifications_section"]
    assert context["certification"] == "AWS Certified Solutions Architect"
