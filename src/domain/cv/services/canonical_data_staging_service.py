"""
Canonical Data Staging Service

Manages the lifecycle of extracted CV data from all sources (document, audio, conversation),
ensuring traceability and preventing data loss through persistent staging before preview/export.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from uuid import uuid4

from src.infrastructure.persistence.mysql.database import SessionLocal
from src.infrastructure.persistence.mysql.staging_models import (
    ExtractionStaging,
    ExtractionFieldConfidence,
)

logger = logging.getLogger(__name__)


class CanonicalDataStagingService:
    """
    Service for managing canonical CV extraction staging layer.
    
    Provides persistent storage for:
    - Raw extracted text from all sources
    - Normalized/parsed intermediate outputs
    - Final mapped canonical schema
    - Field-level confidence/status tracking
    """

    def __init__(self):
        self.db = SessionLocal()

    def __del__(self):
        if self.db:
            self.db.close()

    def create_extraction_record(
        self,
        session_id: str,
        source_type: str,
        source_filename: Optional[str] = None,
        source_size_bytes: Optional[int] = None,
    ) -> str:
        """
        Create a new extraction staging record.
        
        Args:
            session_id: User session ID
            source_type: document_upload, audio_upload, or conversation
            source_filename: Optional filename for document/audio uploads
            source_size_bytes: Optional file size
            
        Returns:
            extraction_id for tracking this extraction
        """
        extraction_id = str(uuid4())

        record = ExtractionStaging(
            session_id=session_id,
            extraction_id=extraction_id,
            source_type=source_type,
            source_filename=source_filename,
            source_size_bytes=source_size_bytes,
            extraction_status="pending",
        )

        try:
            self.db.add(record)
            self.db.commit()
            logger.info(
                f"Created extraction staging record: {extraction_id} for session {session_id}"
            )
            return extraction_id
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create extraction record: {str(e)}")
            raise

    def stage_raw_extraction(
        self,
        extraction_id: str,
        raw_text: str,
        normalized_text: Optional[str] = None,
    ) -> None:
        """
        Store raw extracted and normalized text.
        
        Args:
            extraction_id: Extraction record ID
            raw_text: Raw text before normalization
            normalized_text: Optional normalized text
        """
        try:
            record = self.db.query(ExtractionStaging).filter_by(
                extraction_id=extraction_id
            ).first()
            if not record:
                raise ValueError(f"Extraction record not found: {extraction_id}")

            record.raw_extracted_text = raw_text
            record.normalized_text = normalized_text or raw_text
            record.extraction_status = "in_progress"
            record.updated_at = datetime.now(timezone.utc)

            self.db.commit()
            logger.debug(
                f"Staged raw extraction for {extraction_id}: "
                f"{len(raw_text)} bytes raw, {len(normalized_text or '')} normalized"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to stage raw extraction: {str(e)}")
            raise

    def stage_parsed_intermediate(
        self,
        extraction_id: str,
        parsed_data: Dict[str, Any],
        warnings: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
    ) -> None:
        """
        Store intermediate parsed structure before schema mapping.
        
        Args:
            extraction_id: Extraction record ID
            parsed_data: Intermediate parsed structure from parser
            warnings: Optional extraction warnings
            errors: Optional recoverable extraction errors
        """
        try:
            record = self.db.query(ExtractionStaging).filter_by(
                extraction_id=extraction_id
            ).first()
            if not record:
                raise ValueError(f"Extraction record not found: {extraction_id}")

            record.parsed_intermediate = parsed_data
            record.extraction_warnings = warnings or []
            record.extraction_errors = errors or []
            record.updated_at = datetime.now(timezone.utc)

            self.db.commit()
            logger.debug(
                f"Staged parsed intermediate for {extraction_id}: "
                f"{len(parsed_data)} keys, {len(warnings or [])} warnings"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to stage parsed intermediate: {str(e)}")
            raise

    def stage_canonical_and_confidence(
        self,
        extraction_id: str,
        canonical_cv: Dict[str, Any],
        field_confidence: Optional[Dict[str, float]] = None,
        llm_enhancement: str = "none",
        llm_confidence: Optional[float] = None,
    ) -> None:
        """
        Store final canonical CV schema and field-level confidence scores.
        
        Args:
            extraction_id: Extraction record ID
            canonical_cv: Final canonical CV schema
            field_confidence: Field-level confidence map (0.0-1.0)
            llm_enhancement: none, hybrid, or full_llm
            llm_confidence: Overall LLM confidence score
        """
        try:
            record = self.db.query(ExtractionStaging).filter_by(
                extraction_id=extraction_id
            ).first()
            if not record:
                raise ValueError(f"Extraction record not found: {extraction_id}")

            record.canonical_cv = canonical_cv
            record.field_confidence = field_confidence or {}
            record.llm_enhancement_applied = llm_enhancement
            record.llm_confidence_score = llm_confidence
            record.extraction_status = "complete"
            record.extracted_at = datetime.now(timezone.utc)
            record.updated_at = datetime.now(timezone.utc)

            self.db.commit()

            # Store field-level confidence details
            if field_confidence:
                self._store_field_confidence_details(extraction_id, field_confidence)

            logger.info(
                f"Completed extraction staging for {extraction_id}: "
                f"{len(field_confidence or {})} field confidence scores"
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to stage canonical CV: {str(e)}")
            raise

    def _store_field_confidence_details(
        self, extraction_id: str, field_confidence: Dict[str, Dict[str, Any]]
    ) -> None:
        """Store detailed field-level confidence records."""
        try:
            for field_path, conf_data in field_confidence.items():
                if isinstance(conf_data, (int, float)):
                    # Simple confidence score
                    record = ExtractionFieldConfidence(
                        extraction_id=extraction_id,
                        field_path=field_path,
                        extraction_method="unknown",
                        confidence_score=float(conf_data),
                        validation_status="unknown",
                    )
                    self.db.add(record)
                elif isinstance(conf_data, dict):
                    # Detailed confidence record
                    record = ExtractionFieldConfidence(
                        extraction_id=extraction_id,
                        field_path=field_path,
                        extraction_method=conf_data.get("method", "unknown"),
                        confidence_score=float(conf_data.get("confidence", 0.0)),
                        extracted_value=conf_data.get("extracted"),
                        normalized_value=conf_data.get("normalized"),
                        validation_status=conf_data.get("status", "unknown"),
                        extraction_notes=conf_data.get("notes"),
                        fallback_used=conf_data.get("fallback"),
                    )
                    self.db.add(record)

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.warning(f"Failed to store detailed field confidence: {str(e)}")

    def get_extraction_record(self, extraction_id: str) -> Optional[Dict[str, Any]]:
        """Get extraction staging record as dict."""
        try:
            record = self.db.query(ExtractionStaging).filter_by(
                extraction_id=extraction_id
            ).first()
            return record.to_dict() if record else None
        except Exception as e:
            logger.error(f"Failed to retrieve extraction record: {str(e)}")
            return None

    def get_canonical_cv_from_staging(
        self, session_id: str, extraction_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get canonical CV from staging. If extraction_id not provided, gets latest for session.
        
        Args:
            session_id: User session ID
            extraction_id: Optional specific extraction ID
            
        Returns:
            Canonical CV dict or None if not found
        """
        try:
            query = self.db.query(ExtractionStaging).filter_by(session_id=session_id)

            if extraction_id:
                query = query.filter_by(extraction_id=extraction_id)
            else:
                query = query.filter(ExtractionStaging.extraction_status == "complete")

            record = query.order_by(ExtractionStaging.extracted_at.desc()).first()
            return record.canonical_cv if record else None
        except Exception as e:
            logger.error(f"Failed to retrieve canonical CV from staging: {str(e)}")
            return None

    def mark_previewed(self, extraction_id: str) -> None:
        """Mark extraction as previewed."""
        try:
            record = self.db.query(ExtractionStaging).filter_by(
                extraction_id=extraction_id
            ).first()
            if record:
                record.extraction_status = "previewed"
                record.previewed_at = datetime.now(timezone.utc)
                record.updated_at = datetime.now(timezone.utc)
                self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.warning(f"Failed to mark extraction as previewed: {str(e)}")

    def mark_exported(self, extraction_id: str) -> None:
        """Mark extraction as exported."""
        try:
            record = self.db.query(ExtractionStaging).filter_by(
                extraction_id=extraction_id
            ).first()
            if record:
                record.extraction_status = "exported"
                record.exported_at = datetime.now(timezone.utc)
                record.updated_at = datetime.now(timezone.utc)
                self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.warning(f"Failed to mark extraction as exported: {str(e)}")

    def clear_session_staging(self, session_id: str) -> Tuple[int, int]:
        """
        Clear all staging records for a session (after export or explicit reset).
        Returns count of records cleared and records marked for deletion.
        """
        try:
            records = self.db.query(ExtractionStaging).filter_by(
                session_id=session_id
            ).all()
            count = len(records)

            for record in records:
                record.extraction_status = "cleared"
                record.cleared_at = datetime.now(timezone.utc)
                record.updated_at = datetime.now(timezone.utc)

            self.db.commit()
            logger.info(f"Cleared {count} staging records for session {session_id}")
            return count, count

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to clear session staging: {str(e)}")
            return 0, 0

    def get_extraction_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get extraction history for a session."""
        try:
            records = (
                self.db.query(ExtractionStaging)
                .filter_by(session_id=session_id)
                .order_by(ExtractionStaging.created_at.desc())
                .limit(limit)
                .all()
            )
            return [r.to_dict() for r in records]
        except Exception as e:
            logger.error(f"Failed to retrieve extraction history: {str(e)}")
            return []

    def get_field_confidence_report(
        self, extraction_id: str
    ) -> Optional[Dict[str, Dict[str, Any]]]:
        """Get detailed field confidence report for extraction."""
        try:
            records = (
                self.db.query(ExtractionFieldConfidence)
                .filter_by(extraction_id=extraction_id)
                .all()
            )
            return {r.field_path: r.to_dict() for r in records} if records else None
        except Exception as e:
            logger.error(f"Failed to retrieve field confidence report: {str(e)}")
            return None
