"""
Audio CV Service - Phase 3 Audio Integration

Orchestrates audio transcript processing through canonical schema pipeline:
1. Parse enhanced transcript → Canonical CV Schema v1.1
2. Merge with existing canonical CV (preserving rich data)
3. Validate merged result
4. Return canonical CV + validation + eligibility flags

This service connects audio input to Phase 2 infrastructure (SchemaMergeService, SchemaValidationService).
"""

from __future__ import annotations

from typing import Any, Dict
from datetime import datetime, timezone

from src.infrastructure.parsers.canonical_audio_parser import CanonicalAudioParser
from src.domain.cv.services.schema_merge_service import SchemaMergeService
from src.domain.cv.services.schema_validation_service import SchemaValidationService
from src.domain.cv.enums import SourceType
from src.core.logging.logger import get_logger

logger = get_logger(__name__)


class AudioCVService:
    """
    Phase 3: Audio integration orchestration service.
    
    Coordinates audio transcript processing through canonical schema pipeline
    using Phase 2 services (merge + validation).
    """

    def __init__(self) -> None:
        self.audio_parser = CanonicalAudioParser()
        self.merge_service = SchemaMergeService()
        self.validation_service = SchemaValidationService()

    def process_audio_transcript(
        self,
        enhanced_transcript: str,
        existing_canonical_cv: Dict[str, Any],
        source_type: SourceType = SourceType.AUDIO_RECORDING,
    ) -> Dict[str, Any]:
        """
        Process enhanced audio transcript into canonical CV with merge and validation.

        Args:
            enhanced_transcript: LLM-enhanced transcript with structured sections
            existing_canonical_cv: Current canonical CV from session (may be empty)
            source_type: Audio source (AUDIO_RECORDING or AUDIO_UPLOAD)

        Returns:
            {
                "canonical_cv": dict,  # Merged canonical CV
                "validation": dict,    # Validation result
                "can_save": bool,      # Whether CV can be saved
                "can_export": bool,    # Whether CV can be exported
                "audio_extraction": dict  # Raw audio extraction (for debugging)
            }

        Raises:
            ValueError: If transcript is empty or invalid
        """
        if not enhanced_transcript or not enhanced_transcript.strip():
            raise ValueError("Enhanced transcript cannot be empty")

        # Step 1: Parse audio transcript → Canonical CV Schema v1.1
        logger.info("=" * 80)
        logger.info("AUDIO CV SERVICE - Starting transcript processing")
        logger.info(f"Transcript length: {len(enhanced_transcript)} chars")
        logger.info(f"Transcript preview: {enhanced_transcript[:200]}...")
        
        audio_canonical = self.audio_parser.parse(enhanced_transcript)
        
        logger.info("Audio parsing complete")
        logger.info(f"  - Top-level keys: {list(audio_canonical.keys())}")
        logger.info(f"  - Candidate name: {audio_canonical.get('candidate', {}).get('fullName', 'NOT SET')}")
        logger.info(f"  - Education count: {len(audio_canonical.get('education', []))}")
        logger.info(f"  - Projects count: {len(audio_canonical.get('projects', []))}")
        logger.info(f"  - Skills count: {len(audio_canonical.get('skills', []))}")
        
        # Ensure sourceType is set for merge precedence rules
        audio_canonical["sourceType"] = source_type.value
        if "metadata" not in audio_canonical:
            audio_canonical["metadata"] = {}
        audio_canonical["metadata"]["lastModifiedAt"] = datetime.now(timezone.utc).isoformat()

        # Step 2: Merge with existing canonical CV (Phase 2 service)
        # This preserves rich project descriptions and prevents empty overwrites
        logger.info(f"Starting merge with existing CV (has {len(existing_canonical_cv)} top-level keys)")
        
        merged_canonical = self.merge_service.merge_canonical_cvs(
            existing_cv=existing_canonical_cv,
            new_data=audio_canonical,
            source_type=source_type,
            operation="audio_merge"
        )
        
        logger.info("Merge complete")
        logger.info(f"  - Merged CV has {len(merged_canonical)} top-level keys")
        logger.info(f"  - Candidate name after merge: {merged_canonical.get('candidate', {}).get('fullName', 'NOT SET')}")

        # Step 3: Validate merged canonical CV (Phase 2 service)
        # Use save_and_validate for audio operations to get comprehensive feedback
        validation_result_obj = self.validation_service.validate_for_save_and_validate(merged_canonical)
        validation_result = validation_result_obj.to_dict()
        
        logger.info("Validation complete")
        logger.info(f"  - Can save: {validation_result['can_save']}")
        logger.info(f"  - Can export: {validation_result['can_export']}")
        logger.info("=" * 80)

        return {
            "canonical_cv": merged_canonical,
            "validation": validation_result,
            "can_save": validation_result["can_save"],
            "can_export": validation_result["can_export"],
            "audio_extraction": audio_canonical  # Raw extraction for debugging
        }
