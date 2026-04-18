"""
Staging models for canonical CV extraction data persistence.

These models provide a staging layer for all extracted CV data before preview/validation,
ensuring traceability and preventing data loss across all input channels (document, audio, conversation).
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, DateTime, Float, JSON, Integer, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ExtractionStaging(Base):
    """
    Staging table for canonical CV extraction from all sources.
    Stores raw input, normalized intermediate, and mapped schema outputs for traceability.
    """

    __tablename__ = "cv_extraction_staging"

    # Identifiers
    extraction_id = Column(String(64), primary_key=True, nullable=False)
    session_id = Column(String(64), nullable=False, index=True)

    # Source metadata
    source_type = Column(
        String(32), nullable=False
    )  # document_upload, audio_upload, conversation
    source_filename = Column(String(255), nullable=True)  # For document/audio uploads
    source_size_bytes = Column(Integer, nullable=True)

    # Extraction pipeline outputs (stored as JSON for flexibility)
    raw_extracted_text = Column(
        Text, nullable=True
    )  # Raw text before normalization
    normalized_text = Column(
        Text, nullable=True
    )  # After normalization/cleanup
    parsed_intermediate = Column(
        JSON, nullable=True
    )  # Intermediate parsed structure before mapping
    canonical_cv = Column(
        JSON, nullable=True
    )  # Final canonical schema output

    # Field-level extraction confidence (0.0 to 1.0 per field)
    field_confidence = Column(
        JSON, nullable=True
    )  # {"candidate.fullName": 0.95, "skills.primarySkills": 0.65, ...}
    extraction_warnings = Column(
        JSON, nullable=True
    )  # List of warnings from extraction pipeline
    extraction_errors = Column(
        JSON, nullable=True
    )  # List of recoverable errors (not blocking extraction)

    # Lifecycle tracking
    extraction_status = Column(
        String(32), default="pending", nullable=False
    )  # pending, in_progress, complete, failed, staged, previewed, exported, cleared
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    extracted_at = Column(DateTime, nullable=True)  # When extraction completed
    previewed_at = Column(DateTime, nullable=True)  # When preview generated
    exported_at = Column(DateTime, nullable=True)  # When export completed
    cleared_at = Column(DateTime, nullable=True)  # When staging was cleared

    # Audit fields
    llm_enhancement_applied = Column(
        String(32), default="none", nullable=False
    )  # none, hybrid, full_llm
    llm_confidence_score = Column(Float, nullable=True)  # Overall LLM extraction quality

    __table_args__ = (
        Index("ix_extraction_staging_extraction_id", "extraction_id", unique=True),
        Index("ix_extraction_staging_session", "session_id"),
        Index("ix_extraction_staging_status", "extraction_status"),
        Index("ix_extraction_staging_created", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "extraction_id": self.extraction_id,
            "source_type": self.source_type,
            "source_filename": self.source_filename,
            "source_size_bytes": self.source_size_bytes,
            "raw_extracted_text_len": len(self.raw_extracted_text or ""),
            "normalized_text_len": len(self.normalized_text or ""),
            "parsed_intermediate_keys": (
                list((self.parsed_intermediate or {}).keys())
                if self.parsed_intermediate
                else []
            ),
            "canonical_cv_keys": (
                list((self.canonical_cv or {}).keys()) if self.canonical_cv else []
            ),
            "field_confidence": self.field_confidence,
            "extraction_status": self.extraction_status,
            "extraction_warnings": self.extraction_warnings,
            "extraction_errors": self.extraction_errors,
            "llm_enhancement_applied": self.llm_enhancement_applied,
            "llm_confidence_score": self.llm_confidence_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "extracted_at": self.extracted_at.isoformat() if self.extracted_at else None,
            "previewed_at": self.previewed_at.isoformat() if self.previewed_at else None,
            "exported_at": self.exported_at.isoformat() if self.exported_at else None,
            "cleared_at": self.cleared_at.isoformat() if self.cleared_at else None,
        }


class ExtractionFieldConfidence(Base):
    """
    Detailed field-level extraction confidence and status tracking.
    Allows granular audit of which fields have high confidence vs need review/refinement.
    """

    __tablename__ = "cv_extraction_field_confidence"

    extraction_id = Column(
        String(64), ForeignKey("cv_extraction_staging.extraction_id"), primary_key=True
    )
    field_path = Column(String(128), primary_key=True)  # e.g., "candidate.fullName"

    # Field extraction details
    extraction_method = Column(
        String(64), nullable=False
    )  # deterministic, regex, llm, fallback, default
    confidence_score = Column(Float, nullable=False)  # 0.0 to 1.0
    extracted_value = Column(Text, nullable=True)  # Raw extracted value
    normalized_value = Column(Text, nullable=True)  # After normalization
    validation_status = Column(
        String(32), default="unknown"
    )  # unknown, valid, questionable, invalid, required_missing

    # Traceability
    extraction_notes = Column(Text, nullable=True)  # Why this extraction method was used
    fallback_used = Column(String(64), nullable=True)  # If fallback was applied, which one
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("ix_field_confidence_extraction", "extraction_id"),)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_path": self.field_path,
            "extraction_method": self.extraction_method,
            "confidence_score": self.confidence_score,
            "extracted_value": self.extracted_value,
            "normalized_value": self.normalized_value,
            "validation_status": self.validation_status,
            "extraction_notes": self.extraction_notes,
            "fallback_used": self.fallback_used,
        }
