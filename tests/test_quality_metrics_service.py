from src.application.services.quality_metrics_service import QualityMetricsService


def test_quality_metrics_reports_supported_fields_and_low_hallucination() -> None:
    service = QualityMetricsService()

    canonical = {
        "candidate": {
            "fullName": "Alex Example",
            "currentDesignation": "AI Solution Architect",
            "summary": "Experienced in Python and cloud delivery",
        },
        "skills": {
            "primarySkills": ["Python", "FastAPI"],
        },
        "sourceSnapshots": {
            "questionnaire_cv_data": {
                "personal_details": {
                    "full_name": "Alex Example",
                    "current_title": "AI Solution Architect",
                },
                "summary": {
                    "professional_summary": "Experienced in Python and cloud delivery",
                },
                "skills": {
                    "primary_skills": ["Python", "FastAPI"],
                },
            }
        },
    }

    report = service.evaluate(canonical, {"can_export": True})
    metrics = report["metrics"]

    assert metrics["precision"] >= 0.8
    assert metrics["hallucination_rate"] <= 0.2
    assert metrics["validation_pass_rate"] == 1.0


def test_quality_metrics_flags_unsupported_generated_values() -> None:
    service = QualityMetricsService()

    canonical = {
        "candidate": {
            "fullName": "Casey Example",
            "currentDesignation": "Principal Architect",
        },
        "education": [
            {
                "degree": "MCA",
                "institution": "Unknown University",
                "yearOfPassing": "2099",
            }
        ],
        "sourceSnapshots": {
            "questionnaire_cv_data": {
                "personal_details": {
                    "full_name": "Casey Example",
                },
            }
        },
    }

    report = service.evaluate(canonical, {"can_export": False})
    metrics = report["metrics"]

    assert metrics["hallucination_rate"] > 0.0
    assert metrics["validation_pass_rate"] == 0.0
    assert any(item["support_status"] == "unsupported" for item in report["field_traceability"])
