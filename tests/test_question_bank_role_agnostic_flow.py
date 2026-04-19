import json

from src.application.services.cv_builder_service import CVBuilderService
from src.application.services.preview_service import PreviewService
from src.questionnaire.mappers.answer_to_cv_field_mapper import AnswerToCVFieldMapper


def test_mapper_uses_question_bank_for_existing_role_question() -> None:
    mapper = AnswerToCVFieldMapper()
    cv_data = {"leadership": {}}

    updated = mapper.apply_answer(
        cv_data,
        "What type of projects or delivery assignments have you led?",
        "Large enterprise modernization programs",
    )

    assert "project_types" in updated["leadership"]
    assert updated["leadership"]["project_types"] == [
        "Large enterprise modernization programs"
    ]


def test_preview_exposes_unmapped_role_fields_from_any_section() -> None:
    builder = CVBuilderService()
    preview = PreviewService()

    cv_data = {
        "personal_details": {
            "full_name": "Alex Example",
            "current_title": "Technical Manager",
            "location": "Berlin, Germany",
        },
        "summary": {"professional_summary": "Experienced engineering leader."},
        "skills": {
            "primary_skills": ["Python"],
            "primary_technical_domains": "Distributed Systems",
        },
        "leadership": {
            "architecture_experience": ["Designed event-driven platforms"],
        },
    }

    canonical = builder.build_partial_schema(cv_data)
    formatted = preview._convert_canonical_to_formatter_format(canonical)

    leadership = formatted.get("leadership", {})
    assert leadership.get("architecture_experience") == [
        "Designed event-driven platforms"
    ]
    assert leadership.get("skills_primary_technical_domains") == "Distributed Systems"


def test_canonical_preserves_full_questionnaire_payload_without_loss() -> None:
    builder = CVBuilderService()

    cv_data = {
        "personal_details": {
            "full_name": "Casey Example",
            "current_title": "Senior Team Lead",
            "location": "Munich, Germany",
            "custom_personal_flag": "internal-mobility",
        },
        "summary": {
            "professional_summary": "Delivery-focused engineering leader.",
            "custom_summary_note": "prefers platform roles",
        },
        "skills": {
            "primary_skills": ["Python", "Azure"],
            "custom_skill_bucket": ["Event-driven systems"],
        },
        "leadership": {
            "project_types": ["Cloud modernization"],
        },
        "senior_team_lead": {
            "additional_signal": "handled multi-region squads",
        },
    }

    canonical = builder.build_partial_schema(cv_data)

    assert canonical.unmappedData.get("personal_details", {}).get("custom_personal_flag") == "internal-mobility"
    assert canonical.unmappedData.get("summary", {}).get("custom_summary_note") == "prefers platform roles"
    assert canonical.unmappedData.get("skills", {}).get("custom_skill_bucket") == ["Event-driven systems"]
    assert canonical.unmappedData.get("senior_team_lead", {}).get("additional_signal") == "handled multi-region squads"
    assert canonical.sourceSnapshots.get("questionnaire_cv_data") == cv_data


def test_mapper_llm_fallback_maps_question_variation() -> None:
    class _FakeLLMService:
        def is_enabled(self) -> bool:
            return True

        def call(self, prompt: str, **kwargs) -> str:
            target = "what is your official email address?"
            for line in prompt.splitlines():
                if target in line:
                    idx_text = line.split(".", 1)[0].strip()
                    return json.dumps({"index": int(idx_text), "confidence": 0.95})
            return json.dumps({"index": 0, "confidence": 0.0})

    mapper = AnswerToCVFieldMapper()
    mapper._llm_service = _FakeLLMService()

    cv_data = {"personal_details": {}}
    updated = mapper.apply_answer(
        cv_data,
        "What is your official company email?",
        "venkata@nttdata.com",
    )

    assert updated["personal_details"]["email"] == "venkata@nttdata.com"
