from src.interfaces.rest.routers.cv_router import (
    _apply_others_mappings,
    _merge_preview_into_canonical,
)


def test_apply_others_mapping_sets_field_and_removes_unmapped_entry():
    canonical_cv = {
        "candidate": {},
        "skills": {},
        "experience": {},
        "education": [],
        "certifications": [],
        "personalDetails": {},
        "audit": {"manualEdits": []},
        "unmappedData": {
            "audio": {
                "portal_id": "12345"
            }
        },
    }

    mappings = [
        {
            "source": "audio",
            "key": "portal_id",
            "target_path": "candidate.portalId",
            "value": "12345",
        }
    ]

    result = _apply_others_mappings(canonical_cv, mappings)

    assert result["applied"] == 1
    assert result["skipped"] == 0
    assert canonical_cv["candidate"]["portalId"] == "12345"
    assert "audio" not in canonical_cv["unmappedData"]
    assert len(canonical_cv["audit"]["manualEdits"]) == 1
    assert canonical_cv["audit"]["manualEdits"][0]["field"] == "candidate.portalId"


def test_apply_others_mapping_coerces_skill_lists_and_skips_invalid_roots():
    canonical_cv = {
        "candidate": {},
        "skills": {},
        "experience": {},
        "education": [],
        "certifications": [],
        "personalDetails": {},
        "audit": {"manualEdits": []},
        "unmappedData": {
            "document": {
                "stack": "Python, FastAPI, SQL"
            }
        },
    }

    mappings = [
        {
            "source": "document",
            "key": "stack",
            "target_path": "skills.primarySkills",
            "value": "Python, FastAPI, SQL",
        },
        {
            "source": "document",
            "key": "stack",
            "target_path": "unknown.field",
            "value": "should be skipped",
        },
    ]

    result = _apply_others_mappings(canonical_cv, mappings)

    assert result["applied"] == 1
    assert result["skipped"] == 1
    assert canonical_cv["skills"]["primarySkills"] == ["Python", "FastAPI", "SQL"]


def test_apply_others_mapping_marks_structured_attribute_as_reviewed():
    canonical_cv = {
        "candidate": {},
        "skills": {},
        "experience": {},
        "education": [],
        "certifications": [],
        "personalDetails": {},
        "audit": {"manualEdits": []},
        "unmappedData": {
            "attributes": [
                {
                    "attributeId": "attr-001",
                    "source": "document_upload",
                    "sourceSection": "top_level_fields",
                    "sourcePath": "top_level_fields.portal_id",
                    "originalLabel": "portal_id",
                    "extractedValue": "77777",
                    "mappingStatus": "unmapped",
                    "reviewStatus": "pending",
                }
            ]
        },
    }

    mappings = [
        {
            "attribute_id": "attr-001",
            "source": "document_upload",
            "sourceSection": "top_level_fields",
            "key": "portal_id",
            "target_path": "candidate.portalId",
            "value": "77777",
        }
    ]

    result = _apply_others_mappings(canonical_cv, mappings)

    assert result["applied"] == 1
    assert canonical_cv["candidate"]["portalId"] == "77777"
    attr = canonical_cv["unmappedData"]["attributes"][0]
    assert attr["mappingStatus"] == "mapped"
    assert attr["reviewStatus"] == "reviewed"


def test_review_merge_preserves_existing_education_details_when_form_is_sparse():
    existing_canonical = {
        "candidate": {},
        "skills": {},
        "experience": {"projects": [], "workHistory": []},
        "education": [
            {
                "degree": "B.Tech",
                "institution": "ABC Institute",
                "university": "State University",
                "specialization": "Computer Science",
                "yearOfPassing": "2015",
                "grade": "8.2",
                "board": "JNTU",
                "cgpa": "8.2",
                "location": "Chennai",
            }
        ],
    }
    cv_data = {
        "personal_details": {},
        "summary": {},
        "skills": {},
        "education": [
            {
                "degree": "B.Tech",
                "institution": "ABC Institute",
            }
        ],
    }

    merged = _merge_preview_into_canonical(cv_data, existing_canonical)
    education = merged.get("education") or []

    assert len(education) == 1
    assert education[0]["degree"] == "B.Tech"
    assert education[0]["institution"] == "ABC Institute"
    assert education[0]["yearOfPassing"] == "2015"
    assert education[0]["board"] == "JNTU"
    assert education[0]["cgpa"] == "8.2"
    assert education[0]["location"] == "Chennai"


def test_review_merge_preserves_existing_project_description_when_not_edited():
    existing_canonical = {
        "candidate": {},
        "skills": {},
        "experience": {
            "projects": [
                {
                    "projectName": "Alpha",
                    "role": "Developer",
                    "projectDescription": "Long extracted description from upload",
                    "responsibilities": ["Built APIs"],
                    "toolsUsed": ["Python", "FastAPI"],
                }
            ],
            "workHistory": [],
        },
        "education": [],
    }
    cv_data = {
        "personal_details": {},
        "summary": {},
        "skills": {},
        "project_experience": [
            {
                "project_name": "Alpha",
                "role": "Developer",
                "description": "",
            }
        ],
    }

    merged = _merge_preview_into_canonical(cv_data, existing_canonical)
    projects = (merged.get("experience") or {}).get("projects") or []

    assert len(projects) == 1
    assert projects[0]["projectDescription"] == "Long extracted description from upload"
    assert projects[0]["responsibilities"] == ["Built APIs"]
    assert projects[0]["toolsUsed"] == ["Python", "FastAPI"]


def test_review_merge_keeps_header_location_when_personal_details_location_is_empty():
    existing_canonical = {
        "candidate": {},
        "skills": {},
        "experience": {"projects": [], "workHistory": []},
        "education": [],
    }
    cv_data = {
        "header": {
            "location": "Chennai, India",
        },
        "personal_details": {
            "location": "",
        },
        "summary": {},
        "skills": {},
    }

    merged = _merge_preview_into_canonical(cv_data, existing_canonical)
    current_location = (merged.get("candidate") or {}).get("currentLocation") or {}

    assert current_location.get("fullAddress") == "Chennai, India"
    assert current_location.get("city") == "Chennai"
    assert current_location.get("country") == "India"
