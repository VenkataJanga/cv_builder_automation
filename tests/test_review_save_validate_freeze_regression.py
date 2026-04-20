from __future__ import annotations

from copy import deepcopy

from src.application.services.conversation_service import ConversationService
from src.interfaces.rest.routers.cv_router import ReviewCVRequest, review_cv


def test_save_and_validate_freezes_user_edited_canonical_not_stale_flow_stage() -> None:
    service = ConversationService()
    session_id = service.start_session()["session_id"]
    session = service.get_session(session_id)

    stale_document_canonical = {
        "schemaVersion": "1.1.0",
        "sourceType": "document_upload",
        "candidate": {
            "fullName": "Regression User",
            "currentDesignation": "Old Title",
            "currentLocation": {"fullAddress": "Old City, Old Country"},
            "summary": "Experienced engineer",
        },
        "skills": {"primarySkills": ["Python"]},
        "experience": {
            "projects": [
                {
                    "projectName": "Platform Revamp",
                    "role": "Old Role",
                    "projectDescription": "Initial upload description",
                }
            ],
            "workHistory": [],
        },
        "education": [],
        "certifications": [],
    }

    session["canonical_cv"] = deepcopy(stale_document_canonical)
    session["flow_stages"] = {
        ConversationService.FLOW_DOCUMENT_UPLOAD: {
            "canonical": deepcopy(stale_document_canonical),
            "written_at": "2099-01-01T00:00:00+00:00",
            "flow_type": ConversationService.FLOW_DOCUMENT_UPLOAD,
            "source_metadata": {"filename": "resume.docx"},
        }
    }
    session["active_flow"] = ConversationService.FLOW_DOCUMENT_UPLOAD
    service.save_session(session_id, session)

    review_payload = ReviewCVRequest(
        cv_data={
            "personal_details": {
                "full_name": "Regression User",
                "current_title": "New Title",
                "location": "New City, New Country",
            },
            "summary": {
                "professional_summary": "Experienced engineer with modern cloud and API delivery expertise.",
            },
            "skills": {"primary_skills": ["Python", "FastAPI"]},
            "project_experience": [
                {
                    "project_name": "Platform Revamp",
                    "role": "New Role",
                    "description": "Initial upload description",
                }
            ],
        }
    )

    response = review_cv(session_id, review_payload)
    assert response["canonical_cv"]["candidate"]["currentDesignation"] == "New Title"
    assert response["canonical_cv"]["candidate"]["currentLocation"]["fullAddress"] == "New City, New Country"

    persisted = service.get_session(session_id)
    resolved = persisted.get("resolved_canonical") or {}
    candidate = resolved.get("candidate") or {}
    projects = (resolved.get("experience") or {}).get("projects") or []

    assert candidate.get("currentDesignation") == "New Title"
    assert (candidate.get("currentLocation") or {}).get("fullAddress") == "New City, New Country"
    assert projects and projects[0].get("role") == "New Role"
