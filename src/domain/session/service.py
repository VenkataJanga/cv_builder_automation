from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from src.domain.cv.enums import SourceType
from src.domain.cv.services.schema_merge_service import SchemaMergeService
from src.domain.cv.services.schema_validation_service import SchemaValidationService
from src.domain.session.enums import SessionSourceType, SessionStatus
from src.domain.session.models import CVSession, SessionMetadata, UploadedArtifactMetadata
from src.domain.session.repositories import SessionNotFoundError, SessionRepository


class SessionService:
    """Application service that owns session lifecycle and canonical CV persistence."""

    def __init__(
        self,
        repository: SessionRepository,
        merge_service: Optional[SchemaMergeService] = None,
        validation_service: Optional[SchemaValidationService] = None,
        default_ttl_hours: int = 24,
        exported_retention_hours: int = 6,
    ) -> None:
        self.repository = repository
        self.merge_service = merge_service or SchemaMergeService()
        self.validation_service = validation_service or SchemaValidationService()
        self.default_ttl = timedelta(hours=default_ttl_hours)
        self.exported_retention = timedelta(hours=exported_retention_hours)

    def initialize_session(
        self,
        session_id: Optional[str] = None,
        canonical_cv: Optional[Dict[str, Any]] = None,
        metadata: Optional[SessionMetadata] = None,
    ) -> CVSession:
        now = self._utc_now()
        sid = session_id or str(uuid4())
        session = CVSession(
            session_id=sid,
            canonical_cv=canonical_cv or {},
            validation_results={},
            status=SessionStatus.ACTIVE,
            created_at=now,
            last_updated_at=now,
            expires_at=now + self.default_ttl,
            metadata=metadata or SessionMetadata(),
        )
        return self.repository.create_session(session)

    def get_latest(self, session_id: str) -> CVSession:
        session = self.repository.get_session(session_id)
        if not session:
            raise SessionNotFoundError(f"Session {session_id} not found")
        return session

    def merge_source_update(
        self,
        session_id: str,
        incoming_canonical_cv: Dict[str, Any],
        source_type: SessionSourceType,
        operation: str = "merge",
        source_metadata: Optional[Dict[str, Any]] = None,
        artifact: Optional[UploadedArtifactMetadata] = None,
        expected_version: Optional[int] = None,
    ) -> CVSession:
        """
        Load existing session, merge incoming data into canonical_cv, validate, and persist.
        """
        session = self.get_latest(session_id)

        merged = self.merge_service.merge_canonical_cvs(
            existing_cv=session.canonical_cv,
            new_data=incoming_canonical_cv,
            source_type=self._to_cv_source_type(source_type),
            operation=operation,
        )

        validation = self.validation_service.validate_for_save_and_validate(merged)

        session.canonical_cv = merged
        session.validation_results = validation.to_dict()
        session.add_source_event(source_type, description=operation, payload_metadata=source_metadata)
        if artifact is not None:
            session.add_uploaded_artifact(artifact)
        session.status = SessionStatus.ACTIVE
        session.expires_at = self._utc_now() + self.default_ttl
        session.touch()

        return self.repository.update_session(session, expected_version=expected_version)

    def update_validation(
        self,
        session_id: str,
        validation_results: Dict[str, Any],
        expected_version: Optional[int] = None,
    ) -> CVSession:
        session = self.get_latest(session_id)
        session.validation_results = validation_results
        session.touch()
        return self.repository.update_session(session, expected_version=expected_version)

    def get_preview_payload(self, session_id: str) -> Dict[str, Any]:
        """Return the latest canonical_cv + validation metadata for preview/edit screens."""
        session = self.get_latest(session_id)
        return {
            "session_id": session.session_id,
            "canonical_cv": session.canonical_cv,
            "validation_results": session.validation_results,
            "status": session.status.value,
            "last_updated_at": session.last_updated_at.isoformat(),
        }

    def mark_export_completed(
        self,
        session_id: str,
        export_format: str,
        expected_version: Optional[int] = None,
    ) -> CVSession:
        session = self.get_latest(session_id)
        source = SessionSourceType.EXPORT_DOCX if export_format.lower() == "docx" else SessionSourceType.EXPORT_PDF
        session.mark_exported(source)
        session.expires_at = self._utc_now() + self.exported_retention
        return self.repository.update_session(session, expected_version=expected_version)

    def cleanup_expired_sessions(self, as_of: Optional[datetime] = None) -> int:
        now = as_of or self._utc_now()
        expired = self.repository.find_expired_sessions(now)
        deleted = 0
        for session in expired:
            if session.should_cleanup(now):
                self.repository.delete_session(session.session_id)
                deleted += 1
        return deleted

    def delete_session(self, session_id: str) -> None:
        self.repository.delete_session(session_id)

    def _to_cv_source_type(self, source_type: SessionSourceType) -> SourceType:
        mapping = {
            SessionSourceType.BOT_CONVERSATION: SourceType.BOT_CONVERSATION,
            SessionSourceType.AUDIO_UPLOAD: SourceType.AUDIO_UPLOAD,
            SessionSourceType.LIVE_VOICE_RECORDING: SourceType.AUDIO_RECORDING,
            SessionSourceType.DOCUMENT_UPLOAD: SourceType.DOCUMENT_UPLOAD,
            SessionSourceType.MANUAL_EDIT: SourceType.MANUAL_EDIT,
            SessionSourceType.EXPORT_DOCX: SourceType.MANUAL_EDIT,
            SessionSourceType.EXPORT_PDF: SourceType.MANUAL_EDIT,
        }
        return mapping[source_type]

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)
