from src.domain.cv.enums import SourceType
from src.domain.cv.models.canonical_cv_schema import CanonicalCVSchema
from src.domain.cv.services.schema_merge_service import SchemaMergeService
from src.domain.cv.services.unmapped_data_service import UnmappedDataService


def test_canonical_schema_supports_unmapped_sections():
    cv = CanonicalCVSchema(
        sourceType="audio_upload",
        unmappedData={"audio": {"extra": "value"}},
        sourceSnapshots={"audio": {"entries": [{"kind": "raw", "text": "hello"}]}},
        mappingWarnings=[{"source": "audio", "warning": "missing date"}],
    )

    dumped = cv.model_dump()
    assert dumped["unmappedData"]["audio"]["extra"] == "value"
    assert dumped["sourceSnapshots"]["audio"]["entries"][0]["kind"] == "raw"
    assert dumped["mappingWarnings"][0]["warning"] == "missing date"


def test_schema_merge_preserves_unmapped_and_snapshots():
    merge_service = SchemaMergeService()

    existing = {
        "candidate": {},
        "skills": {},
        "experience": {},
        "education": [],
        "certifications": [],
        "achievements": [],
        "personalDetails": {},
        "attachmentsMetadata": {},
        "audit": {},
        "unmappedData": {"conversation": {"questionnaire_unmapped_answers": {"Q1": "A1"}}},
        "sourceSnapshots": {
            "conversation": {
                "entries": [{"kind": "question_answer", "question": "Q1", "answer": "A1"}]
            }
        },
        "mappingWarnings": [{"source": "conversation", "warning": "example"}],
    }

    new_data = {
        "candidate": {},
        "skills": {},
        "experience": {},
        "education": [],
        "certifications": [],
        "achievements": [],
        "personalDetails": {},
        "attachmentsMetadata": {},
        "audit": {},
        "unmappedData": {"audio_upload": {"top_level_fields": {"leadership": {"span": "global"}}}},
        "sourceSnapshots": {
            "audio_upload": {
                "entries": [{"kind": "enhanced_transcript", "text": "sample"}]
            }
        },
        "mappingWarnings": [{"source": "audio_upload", "warning": "another"}],
    }

    merged = merge_service.merge_canonical_cvs(
        existing_cv=existing,
        new_data=new_data,
        source_type=SourceType.AUDIO_UPLOAD,
        operation="test_merge",
    )

    assert "conversation" in merged["unmappedData"]
    assert "audio_upload" in merged["unmappedData"]
    assert merged["unmappedData"]["conversation"]["questionnaire_unmapped_answers"]["Q1"] == "A1"
    assert merged["unmappedData"]["audio_upload"]["top_level_fields"]["leadership"]["span"] == "global"

    assert len(merged["sourceSnapshots"]["conversation"]["entries"]) == 1
    assert len(merged["sourceSnapshots"]["audio_upload"]["entries"]) == 1

    warnings = merged["mappingWarnings"]
    assert any(w.get("source") == "conversation" for w in warnings)
    assert any(w.get("source") == "audio_upload" for w in warnings)


def test_unmapped_data_service_collects_unknown_top_level_keys():
    service = UnmappedDataService()
    payload = {
        "personal_details": {"full_name": "Jane"},
        "skills": {"primary_skills": ["Python"]},
        "other_notes": {"raw": "free-form"},
        "misc": "retained",
    }

    unmapped = service.collect_unmapped_top_level(
        payload,
        {"personal_details", "skills", "summary", "education"},
    )

    assert "other_notes" in unmapped
    assert "misc" in unmapped
    assert "personal_details" not in unmapped
