from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.api.main import app
from src.application.services.conversation_service import ConversationService
from src.core.config.settings import settings
from src.infrastructure.persistence.mysql.database import SessionLocal
from src.interfaces.rest.routers import export_router


@pytest.fixture(scope="session", autouse=True)
def _disable_rbac_for_regression() -> None:
    settings.ENABLE_RBAC = False


@pytest.fixture(scope="session", autouse=True)
def _require_db() -> None:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Skipping workflow persistence regression tests: DB unavailable ({exc})")
    finally:
        db.close()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def conversation_service() -> ConversationService:
    return ConversationService()


def _fetch_cv_session_row(session_id: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT session_id, canonical_cv, validation_results, workflow_state, version, status
                FROM cv_sessions
                WHERE session_id = :session_id
                """
            ),
            {"session_id": session_id},
        ).mappings().first()

        if row is None:
            raise AssertionError(f"Session row not found in DB for session_id={session_id}")

        out = dict(row)
        out["canonical_cv"] = json.loads(out["canonical_cv"])
        out["validation_results"] = json.loads(out["validation_results"])
        out["workflow_state"] = json.loads(out["workflow_state"])
        return out
    finally:
        db.close()


def _extract_preview_name(preview_payload: dict[str, Any]) -> str | None:
    preview = preview_payload.get("preview", {})
    return (
        (preview.get("header") or {}).get("full_name")
        or (preview.get("personal_details") or {}).get("full_name")
    )


def test_name_persists_across_review_preview_save_export(
    client: TestClient,
    conversation_service: ConversationService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(export_router.export_service, "export_docx", lambda *a, **k: b"docx-bytes")

    # 1) Start session
    start_response = client.post("/session/start")
    assert start_response.status_code == 200
    session_id = start_response.json()["session_id"]

    row_after_start = _fetch_cv_session_row(session_id)
    assert row_after_start["session_id"] == session_id

    # 2) Save & Validate style review payload
    review_payload = {
        "cv_data": {
            "personal_details": {
                "full_name": "Venkata Janga",
                "current_title": "Senior Data Engineer",
                "location": "Hyderabad, India",
                "total_experience": 12,
                "current_organization": "NTT DATA",
                "email": "venkata.janga@example.com",
                "phone": "+91-9000000000",
            },
            "summary": {
                "professional_summary": "Data engineer with extensive Azure and Python experience.",
                "target_role": "Lead Data Engineer",
            },
            "skills": {
                "primary_skills": ["Python", "Azure Data Factory", "Databricks"],
                "secondary_skills": ["SQL", "Power BI"],
            },
            "education": [
                {
                    "degree": "B.Tech",
                    "institution": "JNTU",
                    "year": 2010,
                    "grade": "8.2",
                }
            ],
            "project_experience": [
                {
                    "project_name": "Enterprise Data Platform",
                    "client": "Global Bank",
                    "role": "Lead Engineer",
                    "duration": "2023 to 2025",
                    "technologies": ["Python", "Azure"],
                    "description": "Built scalable ingestion and curation pipelines.",
                    "responsibilities": ["Designed ETL", "Led team of 6"],
                }
            ],
        }
    }

    review_response = client.put(f"/cv/review/{session_id}", json=review_payload)
    assert review_response.status_code == 200

    row_after_review = _fetch_cv_session_row(session_id)
    assert row_after_review["canonical_cv"].get("candidate", {}).get("fullName") == "Venkata Janga"

    # 3) Preview should return the persisted name
    preview_response = client.get(f"/preview/{session_id}")
    assert preview_response.status_code == 200
    assert _extract_preview_name(preview_response.json()) == "Venkata Janga"

    # 4) Save Changes path: update name via /cv/save
    edited_canonical = row_after_review["canonical_cv"]
    edited_canonical.setdefault("candidate", {})["fullName"] = "Venkata Janga Updated"

    save_response = client.post(
        "/cv/save",
        json={
            "session_id": session_id,
            "canonical_cv": edited_canonical,
        },
    )
    assert save_response.status_code == 200

    row_after_save = _fetch_cv_session_row(session_id)
    assert row_after_save["canonical_cv"].get("candidate", {}).get("fullName") == "Venkata Janga Updated"

    preview_after_save = client.get(f"/preview/{session_id}")
    assert preview_after_save.status_code == 200
    assert _extract_preview_name(preview_after_save.json()) == "Venkata Janga Updated"

    # 5) Export should not mutate/remove canonical name
    session_payload = conversation_service.get_session(session_id)
    session_payload["validation_results"] = {"can_export": True, "errors": [], "warnings": []}
    conversation_service.save_session(session_id, session_payload)

    export_response = client.get(f"/export/docx/{session_id}")
    assert export_response.status_code == 200

    row_after_export = _fetch_cv_session_row(session_id)
    assert row_after_export["canonical_cv"].get("candidate", {}).get("fullName") == "Venkata Janga Updated"


def test_name_is_not_lost_when_later_review_payload_omits_full_name(client: TestClient) -> None:
    start_response = client.post("/session/start")
    assert start_response.status_code == 200
    session_id = start_response.json()["session_id"]

    first_review = client.put(
        f"/cv/review/{session_id}",
        json={
            "cv_data": {
                "personal_details": {
                    "full_name": "Name Preserve Check",
                    "current_title": "Engineer",
                    "location": "Hyderabad, India",
                },
                "summary": {"professional_summary": "Initial summary"},
                "skills": {"primary_skills": ["Python"]},
            }
        },
    )
    assert first_review.status_code == 200

    # Intentionally omit full_name in second review payload.
    second_review = client.put(
        f"/cv/review/{session_id}",
        json={
            "cv_data": {
                "personal_details": {
                    "current_title": "Engineer II",
                    "location": "Hyderabad, India",
                },
                "summary": {"professional_summary": "Updated summary"},
                "skills": {"primary_skills": ["Python", "SQL"]},
            }
        },
    )
    assert second_review.status_code == 200

    preview_response = client.get(f"/preview/{session_id}")
    assert preview_response.status_code == 200
    assert _extract_preview_name(preview_response.json()) == "Name Preserve Check"

    row = _fetch_cv_session_row(session_id)
    assert row["canonical_cv"].get("candidate", {}).get("fullName") == "Name Preserve Check"
