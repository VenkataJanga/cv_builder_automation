from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict

from src.domain.session.enums import SessionStatus, SessionSourceType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceEvent(BaseModel):
    """Immutable event record for tracking source updates over session lifetime."""

    source_type: SessionSourceType
    event_at: datetime = Field(default_factory=utc_now)
    description: str = ""
    payload_metadata: Dict[str, Any] = Field(default_factory=dict)


class UploadedArtifactMetadata(BaseModel):
    """Metadata about temporary upload artifacts associated with a session."""

    artifact_id: str
    artifact_type: str
    file_name: str = ""
    content_type: str = ""
    size_bytes: int = 0
    storage_path: str = ""
    uploaded_at: datetime = Field(default_factory=utc_now)
    checksum: str = ""


class SessionMetadata(BaseModel):
    """Extensible metadata envelope for non-canonical operational details."""

    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    client_app: str = ""
    tags: Dict[str, str] = Field(default_factory=dict)


class CVSession(BaseModel):
    """
    Persisted session aggregate for CV Builder workflows.

    canonical_cv is the single operational source of truth.
    """

    model_config = ConfigDict(use_enum_values=False)

    session_id: str
    canonical_cv: Dict[str, Any] = Field(default_factory=dict)
    validation_results: Dict[str, Any] = Field(default_factory=dict)
    status: SessionStatus = SessionStatus.ACTIVE

    created_at: datetime = Field(default_factory=utc_now)
    last_updated_at: datetime = Field(default_factory=utc_now)
    exported_at: Optional[datetime] = None
    expires_at: datetime = Field(default_factory=lambda: utc_now() + timedelta(hours=24))

    source_history: list[SourceEvent] = Field(default_factory=list)
    uploaded_artifacts: list[UploadedArtifactMetadata] = Field(default_factory=list)
    metadata: SessionMetadata = Field(default_factory=SessionMetadata)
    workflow_state: Dict[str, Any] = Field(default_factory=dict)

    version: int = 1

    def touch(self, now: Optional[datetime] = None) -> None:
        self.last_updated_at = now or utc_now()
        self.version += 1

    def mark_exported(self, source_type: SessionSourceType, now: Optional[datetime] = None) -> None:
        export_time = now or utc_now()
        self.exported_at = export_time
        self.status = SessionStatus.EXPORTED
        self.add_source_event(source_type, description="Export completed", event_at=export_time)
        self.touch(export_time)

    def add_source_event(
        self,
        source_type: SessionSourceType,
        description: str = "",
        payload_metadata: Optional[Dict[str, Any]] = None,
        event_at: Optional[datetime] = None,
    ) -> None:
        self.source_history.append(
            SourceEvent(
                source_type=source_type,
                event_at=event_at or utc_now(),
                description=description,
                payload_metadata=payload_metadata or {},
            )
        )

    def add_uploaded_artifact(self, artifact: UploadedArtifactMetadata) -> None:
        self.uploaded_artifacts.append(artifact)
        self.touch()

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        current = now or utc_now()
        return current >= self.expires_at

    def should_cleanup(self, now: Optional[datetime] = None) -> bool:
        current = now or utc_now()
        if self.status == SessionStatus.DELETED:
            return True
        if self.status == SessionStatus.EXPORTED and self.expires_at <= current:
            return True
        return self.is_expired(current)
