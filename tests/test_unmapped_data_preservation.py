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


def test_preserve_unmapped_writes_structured_attributes_and_legacy_bucket():
    service = UnmappedDataService()
    canonical = {
        "unmappedData": {},
        "sourceSnapshots": {},
        "mappingWarnings": [],
    }

    service.preserve_unmapped(
        canonical_cv=canonical,
        source="document_upload",
        key="top_level_fields",
        value={
            "preferred_shift": "Night",
            "legacy_stack": ["COBOL", "Mainframe"],
        },
    )

    # Legacy source bucket remains available for existing consumers.
    assert canonical["unmappedData"]["document_upload"]["top_level_fields"]["preferred_shift"] == "Night"

    # Structured Others contract is also populated.
    attrs = canonical["unmappedData"].get("attributes") or []
    assert len(attrs) >= 3
    labels = {item.get("normalizedLabel") for item in attrs if isinstance(item, dict)}
    assert "preferred_shift" in labels
    assert "legacy_stack" in labels


def test_preserve_unmapped_attribute_upserts_occurrence_count():
    service = UnmappedDataService()
    canonical = {
        "unmappedData": {},
        "sourceSnapshots": {},
        "mappingWarnings": [],
    }

    service.preserve_unmapped_attribute(
        canonical_cv=canonical,
        source="audio_llm_extraction",
        original_label="Business Unit",
        extracted_value="Cloud Ops",
        source_section="summary",
        source_path="summary.business_unit",
    )
    service.preserve_unmapped_attribute(
        canonical_cv=canonical,
        source="audio_llm_extraction",
        original_label="Business Unit",
        extracted_value="Cloud Ops",
        source_section="summary",
        source_path="summary.business_unit",
    )

    attrs = canonical["unmappedData"].get("attributes") or []
    assert len(attrs) == 1
    assert attrs[0]["occurrenceCount"] == 2
    assert attrs[0]["mappingStatus"] == "unmapped"


def test_normalize_legacy_unmapped_data_backfills_attributes():
    service = UnmappedDataService()
    canonical = {
        "unmappedData": {
            "conversation": {
                "questionnaire_unmapped_answers": {
                    "preferred_work_mode": "Hybrid",
                    "citizenship_status": "OCI",
                }
            }
        },
        "sourceSnapshots": {},
        "mappingWarnings": [],
    }

    migrated = service.normalize_legacy_unmapped_data(canonical)
    attrs = canonical["unmappedData"].get("attributes") or []

    assert migrated >= 2
    assert len(attrs) >= 2
    assert any(item.get("normalizedLabel") == "preferred_work_mode" for item in attrs)
