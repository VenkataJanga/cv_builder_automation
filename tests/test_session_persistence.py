"""
Comprehensive session persistence validation tests.

Ensures that session state is correctly persisted and restored across:
- Preview operations
- Save operations
- Validation operations
- Edit operations
- Export operations
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.domain.session import (
    CVSession,
    SessionMetadata,
    SessionService,
    SessionSourceType,
    SessionStatus,
    InMemorySessionRepository,
    DatabaseSessionRepository,
)
from src.domain.session.models import SourceEvent, UploadedArtifactMetadata


@pytest.fixture
def memory_repo():
    """In-memory repository for fast testing."""
    return InMemorySessionRepository()


@pytest.fixture
def session_service(memory_repo):
    """Session service with in-memory persistence."""
    return SessionService(repository=memory_repo)


class TestSessionInitialization:
    """Test session creation and initial state."""

    def test_initialize_session_creates_new_session(self, session_service):
        """Verify session is created with correct initial state."""
        session = session_service.initialize_session()
        
        assert session.session_id is not None
        assert session.canonical_cv == {}
        assert session.validation_results == {}
        assert session.status == SessionStatus.ACTIVE
        assert session.created_at is not None
        assert session.last_updated_at is not None
        assert session.expires_at > session.created_at

    def test_initialize_session_with_canonical_cv(self, session_service):
        """Verify canonical CV is preserved on initialization."""
        test_cv = {"candidate": {"fullName": "John Doe"}, "skills": {"technical": []}}
        session = session_service.initialize_session(canonical_cv=test_cv)
        
        assert session.canonical_cv == test_cv
        retrieved = session_service.get_latest(session.session_id)
        assert retrieved.canonical_cv == test_cv

    def test_initialize_session_with_workflow_state(self, session_service):
        """Verify workflow state is preserved on initialization."""
        workflow = {"step": "initial", "role": None, "answers": {}}
        session = session_service.initialize_session(workflow_state=workflow)
        
        assert session.workflow_state == workflow
        retrieved = session_service.get_latest(session.session_id)
        assert retrieved.workflow_state == workflow


class TestSessionPersistence:
    """Test persistence layer for canonical CV and validation results."""

    def test_save_and_retrieve_canonical_cv(self, session_service):
        """Verify canonical CV survives save and retrieve cycle."""
        session = session_service.initialize_session()
        session_id = session.session_id
        
        # Update canonical CV
        new_cv = {
            "candidate": {"fullName": "Jane Smith", "email": "jane@example.com"},
            "skills": {"technical": ["Python", "JavaScript"]},
        }
        session.canonical_cv = new_cv
        session.touch()
        session_service.repository.save_session(session)
        
        # Retrieve and verify
        retrieved = session_service.get_latest(session_id)
        assert retrieved.canonical_cv == new_cv

    def test_save_and_retrieve_validation_results(self, session_service):
        """Verify validation results survive save and retrieve cycle."""
        session = session_service.initialize_session()
        session_id = session.session_id
        
        # Update validation results
        validation = {
            "is_valid": True,
            "errors": [],
            "warnings": ["Missing LinkedIn profile"],
            "can_export": False,
        }
        session.validation_results = validation
        session.touch()
        session_service.repository.save_session(session)
        
        # Retrieve and verify
        retrieved = session_service.get_latest(session_id)
        assert retrieved.validation_results == validation

    def test_save_workflow_state(self, session_service):
        """Verify save_workflow_state preserves all components."""
        session = session_service.initialize_session()
        session_id = session.session_id
        
        # Save complex workflow state
        cv = {"candidate": {"fullName": "Test User"}}
        validation = {"can_export": True, "errors": []}
        workflow = {"step": "questions", "current_index": 3}
        
        updated = session_service.save_workflow_state(
            session_id=session_id,
            workflow_state=workflow,
            canonical_cv=cv,
            validation_results=validation,
            source_type=SessionSourceType.MANUAL_EDIT,
            description="Test workflow save",
        )
        
        assert updated.canonical_cv == cv
        assert updated.validation_results == validation
        assert updated.workflow_state == workflow
        
        # Verify persistence
        retrieved = session_service.get_latest(session_id)
        assert retrieved.canonical_cv == cv
        assert retrieved.validation_results == validation
        assert retrieved.workflow_state == workflow


class TestSessionSourceTracking:
    """Test source event tracking for audit trail."""

    def test_add_source_event(self, session_service):
        """Verify source events are recorded."""
        session = session_service.initialize_session()
        
        session.add_source_event(
            SessionSourceType.DOCUMENT_UPLOAD,
            description="Uploaded CV.pdf",
            payload_metadata={"filename": "CV.pdf", "size_bytes": 125000},
        )
        
        assert len(session.source_history) == 1
        event = session.source_history[0]
        assert event.source_type == SessionSourceType.DOCUMENT_UPLOAD
        assert event.description == "Uploaded CV.pdf"
        assert event.payload_metadata["filename"] == "CV.pdf"

    def test_source_events_persisted(self, session_service):
        """Verify source events survive persistence cycle."""
        session = session_service.initialize_session()
        session_id = session.session_id
        
        session.add_source_event(
            SessionSourceType.AUDIO_UPLOAD,
            description="Recorded audio",
        )
        session.add_source_event(
            SessionSourceType.MANUAL_EDIT,
            description="User edited CV",
        )
        session.touch()
        session_service.repository.save_session(session)
        
        # Verify persistence
        retrieved = session_service.get_latest(session_id)
        assert len(retrieved.source_history) == 2
        assert retrieved.source_history[0].source_type == SessionSourceType.AUDIO_UPLOAD
        assert retrieved.source_history[1].source_type == SessionSourceType.MANUAL_EDIT


class TestUploadedArtifactTracking:
    """Test artifact metadata tracking."""

    def test_add_uploaded_artifact(self, session_service):
        """Verify uploaded artifacts are recorded."""
        session = session_service.initialize_session()
        
        artifact = UploadedArtifactMetadata(
            artifact_id="upload_001",
            artifact_type="document",
            file_name="CV.pdf",
            content_type="application/pdf",
            size_bytes=125000,
            storage_path="s3://bucket/uploads/upload_001",
            checksum="sha256:abc123",
        )
        
        session.add_uploaded_artifact(artifact)
        assert len(session.uploaded_artifacts) == 1
        assert session.uploaded_artifacts[0].file_name == "CV.pdf"

    def test_artifacts_persisted(self, session_service):
        """Verify artifacts survive persistence cycle."""
        session = session_service.initialize_session()
        session_id = session.session_id
        
        artifact = UploadedArtifactMetadata(
            artifact_id="upload_001",
            artifact_type="document",
            file_name="CV.pdf",
            content_type="application/pdf",
            size_bytes=125000,
            storage_path="s3://bucket/uploads/upload_001",
        )
        
        session.add_uploaded_artifact(artifact)
        session.touch()
        session_service.repository.save_session(session)
        
        # Verify persistence
        retrieved = session_service.get_latest(session_id)
        assert len(retrieved.uploaded_artifacts) == 1
        assert retrieved.uploaded_artifacts[0].file_name == "CV.pdf"
        assert retrieved.uploaded_artifacts[0].storage_path == "s3://bucket/uploads/upload_001"


class TestSessionVersioning:
    """Test optimistic locking with versioning."""

    def test_version_increments_on_touch(self, session_service):
        """Verify version increments when session is modified."""
        session = session_service.initialize_session()
        initial_version = session.version
        
        session.touch()
        assert session.version == initial_version + 1

    def test_version_conflict_detection(self, session_service):
        """Verify version mismatch is detected on update."""
        session = session_service.initialize_session()
        session_id = session.session_id
        
        # Simulate concurrent update (version mismatch)
        from src.domain.session.repositories import SessionConflictError
        
        session.touch()
        session_service.repository.update_session(session, expected_version=session.version)
        
        # Attempt update with old version
        session.touch()  # Version is now current_version + 1
        with pytest.raises(SessionConflictError):
            session_service.repository.update_session(
                session, 
                expected_version=session.version - 1
            )


class TestSessionExpirationAndCleanup:
    """Test session expiration and cleanup logic."""

    def test_session_expiration_check(self, session_service):
        """Verify expiration check works correctly."""
        session = session_service.initialize_session()
        
        # Session should not be expired yet
        assert not session.is_expired()
        
        # Simulate expiration by setting past expires_at
        session.expires_at = datetime.now(timezone.utc)
        assert session.is_expired()

    def test_cleanup_flag_for_exported_sessions(self, session_service):
        """Verify exported sessions are marked for cleanup after retention."""
        session = session_service.initialize_session()
        
        session.mark_exported(SessionSourceType.EXPORT_PDF)
        assert session.status == SessionStatus.EXPORTED
        assert not session.should_cleanup()  # Still within retention period
        
        # Simulate expiration
        session.expires_at = datetime.now(timezone.utc)
        assert session.should_cleanup()


class TestSessionMetadata:
    """Test session metadata preservation."""

    def test_metadata_attached_to_session(self, session_service):
        """Verify metadata is attached and persisted."""
        metadata = SessionMetadata(
            user_id="user_123",
            tenant_id="tenant_001",
            client_app="cv-builder-ui",
            tags={"source": "voice", "region": "us-east-1"},
        )
        
        session = session_service.initialize_session(metadata=metadata)
        assert session.metadata.user_id == "user_123"
        assert session.metadata.tags["source"] == "voice"
        
        # Verify persistence
        session_id = session.session_id
        session.touch()
        session_service.repository.save_session(session)
        
        retrieved = session_service.get_latest(session_id)
        assert retrieved.metadata.user_id == "user_123"
        assert retrieved.metadata.tags["source"] == "voice"


class TestIntegrationFlows:
    """Test complete workflows combining multiple operations."""

    def test_full_cv_workflow_persistence(self, session_service):
        """Test complete CV workflow: initialize → upload → edit → validate → export."""
        # 1. Initialize session
        session = session_service.initialize_session(
            metadata=SessionMetadata(user_id="test_user", tenant_id="test_tenant")
        )
        session_id = session.session_id
        
        # 2. Simulate document upload
        initial_cv = {
            "candidate": {"fullName": "Jane Doe", "email": "jane@example.com"},
            "skills": {"technical": []},
        }
        session.canonical_cv = initial_cv
        session.add_source_event(
            SessionSourceType.DOCUMENT_UPLOAD,
            description="Uploaded CV.pdf",
        )
        session.touch()
        session_service.repository.save_session(session)
        
        # 3. Simulate manual edit
        session = session_service.get_latest(session_id)
        session.canonical_cv["skills"]["technical"] = ["Python", "JavaScript"]
        session.add_source_event(
            SessionSourceType.MANUAL_EDIT,
            description="Added skills",
        )
        session.touch()
        session_service.repository.save_session(session)
        
        # 4. Simulate validation
        session = session_service.get_latest(session_id)
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "can_export": True,
        }
        session.validation_results = validation_results
        session.touch()
        session_service.repository.save_session(session)
        
        # 5. Mark export completed
        session = session_service.get_latest(session_id)
        session.mark_exported(SessionSourceType.EXPORT_PDF)
        session.touch()
        session_service.repository.save_session(session)
        
        # Verify final state
        final = session_service.get_latest(session_id)
        assert final.canonical_cv["candidate"]["fullName"] == "Jane Doe"
        assert final.canonical_cv["skills"]["technical"] == ["Python", "JavaScript"]
        assert final.validation_results["can_export"] is True
        assert final.status == SessionStatus.EXPORTED
        assert len(final.source_history) >= 3  # upload, edit, export


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
