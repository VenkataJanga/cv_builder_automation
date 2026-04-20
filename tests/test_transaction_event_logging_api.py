from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.api.main import app
from src.core.config.settings import settings
from src.infrastructure.persistence.mysql.database import SessionLocal
from src.interfaces.rest.routers import auth_router, export_router, speech_router


@pytest.fixture(scope="session", autouse=True)
def _ensure_rbac_disabled_for_tests() -> None:
    # Keep API tests deterministic and independent from seeded auth users.
    settings.ENABLE_RBAC = False


@pytest.fixture(scope="session", autouse=True)
def _ensure_db_and_log_table() -> None:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS transaction_event_logs (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(64) NULL,
                    actor_user_id BIGINT NULL,
                    actor_username VARCHAR(128) NULL,
                    module_name VARCHAR(64) NOT NULL,
                    operation VARCHAR(128) NOT NULL,
                    status VARCHAR(16) NOT NULL,
                    event_message TEXT NULL,
                    source_channel VARCHAR(64) NULL,
                    export_format VARCHAR(16) NULL,
                    http_status INT NULL,
                    error_code VARCHAR(64) NULL,
                    error_message TEXT NULL,
                    payload LONGTEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    INDEX ix_transaction_event_logs_session_id (session_id),
                    INDEX ix_transaction_event_logs_module_name (module_name),
                    INDEX ix_transaction_event_logs_status (status),
                    INDEX ix_transaction_event_logs_actor_user_id (actor_user_id),
                    INDEX ix_transaction_event_logs_actor_username (actor_username),
                    INDEX ix_transaction_event_logs_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        )

        # Ensure new columns exist even if table was created earlier by old schema.
        columns = set(
            db.execute(
                text(
                    """
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'transaction_event_logs'
                    """
                )
            ).scalars().all()
        )
        if "actor_user_id" not in columns:
            db.execute(text("ALTER TABLE transaction_event_logs ADD COLUMN actor_user_id BIGINT NULL"))
        if "actor_username" not in columns:
            db.execute(text("ALTER TABLE transaction_event_logs ADD COLUMN actor_username VARCHAR(128) NULL"))
        if "event_message" not in columns:
            db.execute(text("ALTER TABLE transaction_event_logs ADD COLUMN event_message TEXT NULL"))
        db.commit()
    except Exception as exc:
        pytest.skip(f"Skipping transaction logging API tests: DB unavailable ({exc})")
    finally:
        db.close()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _fetch_latest_log(*, session_id: str, operation: str) -> dict[str, Any] | None:
    db = SessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT
                    id,
                    actor_user_id,
                    actor_username,
                    module_name,
                    operation,
                    status,
                    event_message,
                    source_channel,
                    export_format,
                    http_status,
                    error_message,
                    payload,
                    created_at
                FROM transaction_event_logs
                WHERE session_id = :session_id
                  AND operation = :operation
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"session_id": session_id, "operation": operation},
        ).mappings().first()
        return dict(row) if row else None
    finally:
        db.close()


def _assert_log(
    *,
    session_id: str,
    operation: str,
    module_name: str,
    status: str,
    source_channel: str | None = None,
    export_format: str | None = None,
    expected_http_status: int | None = None,
    expected_actor_username: str | None = None,
) -> None:
    row = _fetch_latest_log(session_id=session_id, operation=operation)
    assert row is not None, f"No transaction log found for {operation=} {session_id=}"
    assert row["module_name"] == module_name
    assert row["status"] == status
    if source_channel is not None:
        assert row["source_channel"] == source_channel
    if export_format is not None:
        assert row["export_format"] == export_format
    if expected_http_status is not None:
        assert row["http_status"] == expected_http_status
    assert row["event_message"] and operation in row["event_message"]
    if expected_actor_username is not None:
        assert row["actor_username"] == expected_actor_username


def _latest_log_id() -> int:
    db = SessionLocal()
    try:
        value = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM transaction_event_logs")).scalar_one()
        return int(value or 0)
    finally:
        db.close()


def _fetch_log_after_id(
    *,
    min_id_exclusive: int,
    module_name: str,
    operation: str,
    status: str,
) -> dict[str, Any] | None:
    db = SessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT
                    id,
                    actor_user_id,
                    actor_username,
                    module_name,
                    operation,
                    status,
                    event_message,
                    source_channel,
                    export_format,
                    http_status,
                    error_message,
                    payload,
                    created_at
                FROM transaction_event_logs
                WHERE id > :min_id_exclusive
                  AND module_name = :module_name
                  AND operation = :operation
                  AND status = :status
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {
                "min_id_exclusive": min_id_exclusive,
                "module_name": module_name,
                "operation": operation,
                "status": status,
            },
        ).mappings().first()
        return dict(row) if row else None
    finally:
        db.close()


def _make_export_ready_session() -> str:
    session_id = export_router.conversation_service.start_session()["session_id"]
    session = export_router.conversation_service.get_session(session_id)
    session["canonical_cv"] = {
        "candidate": {"fullName": "Txn Test User"},
        "summary": "Export readiness test",
    }
    session["validation_results"] = {"can_export": True, "errors": [], "warnings": []}
    export_router.conversation_service.save_session(session_id, session)
    return session_id


def test_conversation_logging_success_and_failure(client: TestClient) -> None:
    # Success path: create conversation session
    create_resp = client.post("/chat/conversations/session", json={})
    assert create_resp.status_code == 200
    created = create_resp.json()
    session_id = created["session_id"]

    _assert_log(
        session_id=session_id,
        operation="conversation_create_session",
        module_name="conversation",
        status="success",
        source_channel="bot_conversation",
        expected_http_status=200,
    )

    # Failure path: request a missing conversation session
    missing_session_id = f"missing-conv-{uuid.uuid4().hex[:20]}"
    fail_resp = client.get(f"/chat/conversations/{missing_session_id}")
    assert fail_resp.status_code == 200
    fail_body = fail_resp.json()
    assert fail_body["status"] == "error"

    _assert_log(
        session_id=missing_session_id,
        operation="conversation_get_session",
        module_name="conversation",
        status="failed",
        source_channel="bot_conversation",
        expected_http_status=404,
    )


def test_audio_upload_logging_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    session_id = speech_router.conversation_service.start_session()["session_id"]

    def _fake_transcribe(file_path: str, language: str | None = None) -> dict[str, Any]:
        return {
            "raw_transcript": "I am a software engineer.",
            "enhanced_transcript": "I am a software engineer with 5 years experience.",
            "extracted_cv_data": {"personal_details": {"full_name": "Audio User"}},
        }

    def _fake_process(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "canonical_cv": {"candidate": {"fullName": "Audio User"}},
            "validation": {"can_export": False, "errors": ["incomplete"]},
            "can_save": True,
            "can_export": False,
            "audio_quality_warning": None,
        }

    monkeypatch.setattr(speech_router.speech_service, "transcribe", _fake_transcribe)
    monkeypatch.setattr(speech_router.audio_cv_service, "process_audio_transcript", _fake_process)

    resp = client.post(
        "/speech/transcribe",
        data={"session_id": session_id},
        files={"file": ("sample.webm", b"fake-audio-bytes", "audio/webm")},
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["session_id"] == session_id

    _assert_log(
        session_id=session_id,
        operation="audio_upload_transcribe",
        module_name="speech",
        status="success",
        source_channel="audio_upload",
        expected_http_status=200,
    )


def test_audio_upload_logging_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    session_id = f"audio-fail-{uuid.uuid4().hex[:18]}"

    def _raise_transcribe(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("forced transcribe failure")

    monkeypatch.setattr(speech_router.speech_service, "transcribe", _raise_transcribe)

    resp = client.post(
        "/speech/transcribe",
        data={"session_id": session_id},
        files={"file": ("sample.webm", b"bad-audio", "audio/webm")},
    )

    assert resp.status_code == 502

    _assert_log(
        session_id=session_id,
        operation="audio_upload_transcribe",
        module_name="speech",
        status="failed",
        source_channel="audio_upload",
        expected_http_status=502,
    )


def test_start_recording_logging_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    session_id = speech_router.conversation_service.start_session()["session_id"]

    def _fake_correct(transcript: str, corrected_text: str | None = None) -> dict[str, Any]:
        return {
            "raw_transcript": transcript,
            "enhanced_transcript": corrected_text or transcript,
            "extracted_cv_data": {"summary": {"professional_summary": "Test summary"}},
        }

    def _fake_process(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "canonical_cv": {"candidate": {"fullName": "Record User"}},
            "validation": {"can_export": False, "errors": []},
            "can_save": True,
            "can_export": False,
            "audio_quality_warning": None,
        }

    monkeypatch.setattr(speech_router.speech_service, "correct_transcript", _fake_correct)
    monkeypatch.setattr(speech_router.audio_cv_service, "process_audio_transcript", _fake_process)

    resp = client.post(
        "/speech/correct",
        data={
            "session_id": session_id,
            "transcript": "hello",
            "corrected_text": "hello corrected",
        },
    )

    assert resp.status_code == 200

    _assert_log(
        session_id=session_id,
        operation="start_recording_correct_transcript",
        module_name="speech",
        status="success",
        source_channel="start_recording",
        expected_http_status=200,
    )


def test_start_recording_logging_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    session_id = f"record-fail-{uuid.uuid4().hex[:17]}"

    def _raise_correct(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("forced correction failure")

    monkeypatch.setattr(speech_router.speech_service, "correct_transcript", _raise_correct)

    resp = client.post(
        "/speech/correct",
        data={"session_id": session_id, "transcript": "hello"},
    )

    assert resp.status_code == 502

    _assert_log(
        session_id=session_id,
        operation="start_recording_correct_transcript",
        module_name="speech",
        status="failed",
        source_channel="start_recording",
        expected_http_status=502,
    )


@pytest.mark.parametrize(
    "route_template,operation,export_format,needs_docx_patch",
    [
        ("/export/doc/{session_id}", "export_doc_get", "doc", True),
        ("/export/docx/{session_id}", "export_docx_get", "docx", True),
        ("/export/pdf/{session_id}", "export_pdf_get", "pdf", False),
    ],
)
def test_export_logging_success_by_format(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    route_template: str,
    operation: str,
    export_format: str,
    needs_docx_patch: bool,
) -> None:
    session_id = _make_export_ready_session()

    if needs_docx_patch:
        monkeypatch.setattr(export_router.export_service, "export_docx", lambda *a, **k: b"docx-bytes")
    else:
        monkeypatch.setattr(export_router.export_service, "export_pdf", lambda *a, **k: b"pdf-bytes")

    route = route_template.format(session_id=session_id)
    resp = client.get(route)
    assert resp.status_code == 200

    _assert_log(
        session_id=session_id,
        operation=operation,
        module_name="export",
        status="success",
        source_channel="export",
        export_format=export_format,
        expected_http_status=200,
    )


@pytest.mark.parametrize(
    "route_template,operation,export_format",
    [
        ("/export/doc/{session_id}", "export_doc_get", "doc"),
        ("/export/docx/{session_id}", "export_docx_get", "docx"),
        ("/export/pdf/{session_id}", "export_pdf_get", "pdf"),
    ],
)
def test_export_logging_failure_by_format(
    client: TestClient,
    route_template: str,
    operation: str,
    export_format: str,
) -> None:
    missing_session_id = f"missing-export-{uuid.uuid4().hex[:14]}"
    route = route_template.format(session_id=missing_session_id)

    resp = client.get(route)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("error") == "Invalid session_id"

    _assert_log(
        session_id=missing_session_id,
        operation=operation,
        module_name="export",
        status="failed",
        source_channel="export",
        export_format=export_format,
        expected_http_status=404,
    )


def test_auth_login_failed_writes_transaction_log(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    before_id = _latest_log_id()

    class _NoUserRepo:
        def __init__(self, db: Any) -> None:
            self.db = db

        def get_by_username(self, username: str) -> None:
            return None

    monkeypatch.setattr(auth_router, "AuthRepository", _NoUserRepo)

    response = client.post(
        "/auth/token",
        data={"username": "unknown.user", "password": "bad-password"},
    )

    assert response.status_code == 401

    row = _fetch_log_after_id(
        min_id_exclusive=before_id,
        module_name="auth",
        operation="login",
        status="failed",
    )
    assert row is not None
    assert row["http_status"] == 401
    assert row["source_channel"] == "auth"
    assert row["error_message"] == "Incorrect username or password"

    payload = json.loads(row["payload"])
    assert payload["username"] == "unknown.user"
    assert payload["auth_method"] == "password"


def test_auth_login_success_writes_transaction_log(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    before_id = _latest_log_id()

    class _User:
        id = 777
        username = "audit.success"
        role = type("RoleValue", (), {"value": "admin"})()
        email = "audit.success@example.com"
        full_name = "Audit Success"
        preferred_locale = "en"
        is_active = True
        hashed_password = "stored-hash"

    class _Repo:
        def __init__(self, db: Any) -> None:
            self.db = db

        def get_by_username(self, username: str) -> _User | None:
            return _User() if username == "audit.success" else None

    monkeypatch.setattr(auth_router, "AuthRepository", _Repo)
    monkeypatch.setattr(auth_router, "verify_password", lambda provided, stored: provided == "good-password")
    monkeypatch.setattr(auth_router, "create_access_token", lambda payload: "token-for-test")

    response = client.post(
        "/auth/token",
        data={"username": "audit.success", "password": "good-password"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "token-for-test"

    row = _fetch_log_after_id(
        min_id_exclusive=before_id,
        module_name="auth",
        operation="login",
        status="success",
    )
    assert row is not None
    assert row["http_status"] == 200
    assert row["source_channel"] == "auth"
    assert row["actor_user_id"] == 777
    assert row["actor_username"] == "audit.success"

    payload = json.loads(row["payload"])
    assert payload["username"] == "audit.success"
    assert payload["auth_method"] == "password"


def test_audit_events_endpoint_filters_rows(client: TestClient) -> None:
    operation = f"audit_filter_{uuid.uuid4().hex[:10]}"

    from src.application.services.transaction_logging_service import get_transaction_logging_service

    service = get_transaction_logging_service()
    service.log_transaction(
        module_name="auth",
        operation=operation,
        status="failed",
        source_channel="auth",
        actor_user_id=9001,
        actor_username="audit.filter.user",
        http_status=401,
        payload={"reason": "invalid_credentials"},
    )
    service.log_transaction(
        module_name="speech",
        operation=operation,
        status="success",
        source_channel="audio_upload",
        actor_user_id=9002,
        actor_username="other.user",
        http_status=200,
        payload={"note": "control-row"},
    )

    response = client.get(
        "/audit/events",
        params={
            "operation": operation,
            "module_name": "auth",
            "status": "failed",
            "actor_username": "audit.filter.user",
            "limit": 20,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    items = body["items"]
    assert isinstance(items, list)
    assert len(items) >= 1
    assert all(item["operation"] == operation for item in items)
    assert all(item["module_name"] == "auth" for item in items)
    assert all(item["status"] == "failed" for item in items)
    assert all(item["actor_username"] == "audit.filter.user" for item in items)
