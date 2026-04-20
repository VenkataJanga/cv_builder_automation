"""
Document CV Service
Handles CV document upload workflow with canonical schema integration
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from copy import deepcopy

from src.application.services.conversation_service import ConversationService
from src.infrastructure.parsers.canonical_document_parser import CanonicalDocumentParser
from src.domain.cv.services.schema_merge_service import SchemaMergeService
from src.domain.cv.services.unmapped_data_service import UnmappedDataService
from src.domain.cv.services.schema_validation_service import SchemaValidationService
from src.domain.cv.services.canonical_data_staging_service import (
    CanonicalDataStagingService,
)
from src.core.exceptions.base import ValidationException
from src.core.config.settings import settings

logger = logging.getLogger(__name__)


class DocumentCVService:
    """
    Service for handling CV document uploads and integration with canonical schema
    """
    
    def __init__(
        self,
        session_store: Optional[Dict[str, Dict[str, Any]]] = None,
        conversation_service: Optional[ConversationService] = None,
        merge_service: Optional[SchemaMergeService] = None,
        validation_service: Optional[SchemaValidationService] = None
    ):
        """
        Initialize DocumentCVService
        
        Args:
            session_store: Legacy in-memory session store for backward compatibility tests
            conversation_service: Conversation/session persistence service
            merge_service: Schema merge service (optional, will create if not provided)
            validation_service: Schema validation service (optional, will create if not provided)
        """
        self.session_store = session_store
        self.conversation_service = conversation_service or ConversationService()
        self.document_parser = CanonicalDocumentParser()
        self.merge_service = merge_service or SchemaMergeService()
        self.unmapped_service = UnmappedDataService()
        self.validation_service = validation_service or SchemaValidationService()
        self.staging_service = CanonicalDataStagingService()
        self.extraction_service = None

        if settings.ENABLE_LLM_EXTRACTION or settings.ENABLE_LLM_NORMALIZATION:
            try:
                from src.ai.services.extraction_service import ExtractionService
                self.extraction_service = ExtractionService()
            except Exception as exc:
                logger.warning(f"Could not initialize extraction service for document uploads: {exc}")

    def _get_session(self, session_id: str) -> Dict[str, Any]:
        if self.session_store is not None:
            session = self.session_store.get(session_id)
            if not session:
                raise ValidationException(f"Session {session_id} not found")
            return session

        session = self.conversation_service.get_session(session_id)
        if not session or "error" in session:
            raise ValidationException(f"Session {session_id} not found")
        return session

    def _save_session(self, session_id: str, session: Dict[str, Any]) -> None:
        if self.session_store is not None:
            self.session_store[session_id] = session
            return
        self.conversation_service.save_session(session_id, session)

    def _is_truthy(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict, tuple, set)):
            return len(value) > 0
        return True

    def _set_if_missing(self, target: Dict[str, Any], key: str, value: Any) -> None:
        if not self._is_truthy(value):
            return
        if not self._is_truthy(target.get(key)):
            target[key] = value

    def _calculate_field_confidence(self, canonical_cv: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate extraction confidence scores for each field based on presence and completeness.
        
        Args:
            canonical_cv: Canonical CV dictionary
            
        Returns:
            Dict mapping field paths to confidence scores (0.0-1.0)
        """
        confidence = {}
        
        # Candidate fields
        candidate = canonical_cv.get("candidate", {})
        if candidate.get("fullName"):
            confidence["candidate.fullName"] = 0.95
        if candidate.get("currentDesignation"):
            confidence["candidate.currentDesignation"] = 0.9
        if candidate.get("email"):
            confidence["candidate.email"] = 0.95
        if candidate.get("phone"):
            confidence["candidate.phone"] = 0.9
        if candidate.get("summary"):
            confidence["candidate.summary"] = 0.85
        
        # Skills
        skills = canonical_cv.get("skills", {})
        primary_skills = skills.get("primarySkills", [])
        if primary_skills:
            confidence["skills.primarySkills"] = min(0.9, 0.7 + (len(primary_skills) * 0.05))
        else:
            confidence["skills.primarySkills"] = 0.3
            
        technical_skills = skills.get("technicalSkills", [])
        if technical_skills:
            confidence["skills.technicalSkills"] = min(0.95, 0.7 + (len(technical_skills) * 0.03))
        else:
            confidence["skills.technicalSkills"] = 0.3
        
        # Experience
        experience = canonical_cv.get("experience", [])
        if experience:
            confidence["experience"] = min(0.95, 0.6 + (len(experience) * 0.08))
        else:
            confidence["experience"] = 0.2
        
        # Projects
        projects = canonical_cv.get("projects", [])
        if projects:
            confidence["projects"] = min(0.95, 0.5 + (len(projects) * 0.1))
        else:
            confidence["projects"] = 0.2
        
        # Education
        education = canonical_cv.get("education", [])
        if education:
            confidence["education"] = min(0.9, 0.6 + (len(education) * 0.1))
        else:
            confidence["education"] = 0.2
        
        return confidence

    def _merge_llm_extracted_into_canonical(
        self,
        canonical_cv: Dict[str, Any],
        extracted_fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merge LLM-extracted fields into canonical CV conservatively.

        Deterministic parser output always wins; LLM only fills missing values.
        """
        merged = deepcopy(canonical_cv or {})
        if not extracted_fields:
            return merged

        candidate = merged.setdefault("candidate", {})
        skills = merged.setdefault("skills", {})
        experience = merged.setdefault("experience", {})

        personal = extracted_fields.get("personal_details") or {}
        summary = extracted_fields.get("summary") or {}
        extracted_skills = extracted_fields.get("skills") or {}

        self._set_if_missing(candidate, "fullName", personal.get("full_name"))
        self._set_if_missing(candidate, "email", personal.get("email"))
        self._set_if_missing(candidate, "phoneNumber", personal.get("phone"))
        self._set_if_missing(candidate, "currentDesignation", personal.get("current_title"))
        self._set_if_missing(candidate, "currentOrganization", personal.get("current_organization"))
        self._set_if_missing(candidate, "summary", summary.get("professional_summary"))

        total_exp = personal.get("total_experience")
        if total_exp is not None and not self._is_truthy(candidate.get("totalExperienceYears")):
            try:
                candidate["totalExperienceYears"] = int(float(total_exp))
            except (TypeError, ValueError):
                pass

        location = personal.get("location")
        if self._is_truthy(location):
            current_location = candidate.get("currentLocation")
            if not isinstance(current_location, dict):
                current_location = {}
            if isinstance(location, str):
                self._set_if_missing(current_location, "fullAddress", location)
            elif isinstance(location, dict):
                for key in ("fullAddress", "city", "state", "country"):
                    self._set_if_missing(current_location, key, location.get(key))
            candidate["currentLocation"] = current_location

        self._set_if_missing(skills, "primarySkills", extracted_skills.get("primary_skills"))
        self._set_if_missing(skills, "technicalSkills", extracted_skills.get("technical_skills"))

        extracted_work = extracted_fields.get("work_experience")
        if isinstance(extracted_work, list) and extracted_work and not self._is_truthy(experience.get("workHistory")):
            experience["workHistory"] = extracted_work

        extracted_projects = extracted_fields.get("project_experience")
        if isinstance(extracted_projects, list) and extracted_projects and not self._is_truthy(experience.get("projects")):
            experience["projects"] = extracted_projects

        extracted_education = extracted_fields.get("education")
        if isinstance(extracted_education, list) and extracted_education and not self._is_truthy(merged.get("education")):
            merged["education"] = extracted_education

        extracted_certs = extracted_fields.get("certifications")
        if isinstance(extracted_certs, list) and extracted_certs and not self._is_truthy(merged.get("certifications")):
            merged["certifications"] = extracted_certs

        return merged

    def _try_apply_llm_document_enhancement(
        self,
        file_path: str,
        file_metadata: Optional[Dict[str, Any]],
        canonical_cv: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not (settings.ENABLE_LLM_EXTRACTION or settings.ENABLE_LLM_NORMALIZATION):
            return canonical_cv
        if self.extraction_service is None:
            return canonical_cv

        try:
            raw_text = self.document_parser.extract_text(file_path)
            if not raw_text or not raw_text.strip():
                return canonical_cv

            extraction_result = self.extraction_service.extract_and_merge(
                raw_text=raw_text,
                existing_cv_data={},
                context={
                    "source": "document_upload",
                    "filename": (file_metadata or {}).get("filename") or "",
                },
                merge_strategy="questionnaire_wins",
            )

            self.unmapped_service.preserve_snapshot(
                canonical_cv,
                "document_upload",
                {
                    "kind": "raw_document_text",
                    "filename": (file_metadata or {}).get("filename") or "",
                    "text": raw_text,
                },
            )

            if extraction_result.get("normalized_text"):
                self.unmapped_service.preserve_snapshot(
                    canonical_cv,
                    "document_upload",
                    {
                        "kind": "normalized_text",
                        "text": str(extraction_result.get("normalized_text")),
                    },
                )

            known_extraction_keys = {
                "personal_details",
                "summary",
                "skills",
                "work_experience",
                "project_experience",
                "education",
                "certifications",
            }
            extracted_fields = extraction_result.get("extracted_fields") or {}
            unmapped_top_level = self.unmapped_service.collect_unmapped_top_level(
                extracted_fields,
                known_extraction_keys,
            )
            if unmapped_top_level:
                self.unmapped_service.preserve_unmapped(
                    canonical_cv,
                    "document_upload",
                    "top_level_fields",
                    unmapped_top_level,
                )

            for warning in extraction_result.get("warnings", []) or []:
                self.unmapped_service.add_mapping_warning(
                    canonical_cv,
                    "document_upload",
                    str(warning),
                    context={"filename": (file_metadata or {}).get("filename") or ""},
                )

            if not extraction_result.get("success"):
                return canonical_cv

            enhanced = self._merge_llm_extracted_into_canonical(
                canonical_cv=canonical_cv,
                extracted_fields=extraction_result.get("extracted_fields") or {},
            )

            metadata = enhanced.setdefault("metadata", {})
            metadata["llmEnhancement"] = {
                "applied": True,
                "source": extraction_result.get("source", "unknown"),
                "warnings": extraction_result.get("warnings", []),
            }
            normalized_text = extraction_result.get("normalized_text")
            if self._is_truthy(normalized_text):
                metadata["normalizedTextPreview"] = str(normalized_text)[:500]

            return enhanced
        except Exception as exc:
            self.unmapped_service.add_mapping_warning(
                canonical_cv,
                "document_upload",
                "LLM document enhancement skipped due to error",
                context={"error": str(exc)},
            )
            logger.warning(f"LLM document enhancement skipped due to error: {exc}")
            return canonical_cv
    
    def process_document_upload(
        self,
        session_id: str,
        file_path: str,
        file_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process CV document upload: parse, merge, validate, and store in session.
        Uses canonical data staging service to persist extraction at each step.
        
        Args:
            session_id: User session ID
            file_path: Path to uploaded CV file
            file_metadata: Optional metadata about the file
            
        Returns:
            Dict containing:
                - canonical_cv: Merged canonical CV data
                - validation: Validation results
                - merge_stats: Merge statistics
                - extraction_id: Staging extraction ID for traceability
                
        Raises:
            ValidationException: If session not found or processing fails
        """
        extraction_id = None
        try:
            logger.info(f"Processing document upload for session {session_id}")
            
            # Step 0: Create extraction staging record for persistence
            file_metadata = file_metadata or {}
            extraction_id = self.staging_service.create_extraction_record(
                session_id=session_id,
                source_type="document_upload",
                source_filename=file_metadata.get("filename"),
                source_size_bytes=file_metadata.get("size_bytes"),
            )
            logger.info(f"Created extraction staging record: {extraction_id}")
            
            # Step 1: Get session
            session = self._get_session(session_id)
            
            # Step 2: Parse document to canonical schema
            logger.info(f"Parsing document: {file_path}")
            
            # Extract raw text first for staging
            raw_text = self.document_parser.extract_text(file_path)
            self.staging_service.stage_raw_extraction(
                extraction_id=extraction_id, raw_text=raw_text
            )
            
            # Parse to canonical
            new_canonical = self.document_parser.parse_document_to_canonical(
                file_path=file_path,
                session_id=session_id,
                file_metadata=file_metadata
            )

            # Stage canonical output after initial parsing
            self.staging_service.stage_canonical_and_confidence(
                extraction_id=extraction_id,
                canonical_cv=new_canonical,
                field_confidence=self._calculate_field_confidence(new_canonical),
            )
            
            # Optional Phase 5 extension: LLM-assisted normalization + extraction.
            # This is non-breaking and only fills missing canonical values.
            llm_applied = "none"
            llm_confidence = None
            new_canonical_before_llm = deepcopy(new_canonical)
            new_canonical = self._try_apply_llm_document_enhancement(
                file_path=file_path,
                file_metadata=file_metadata,
                canonical_cv=new_canonical,
            )
            if new_canonical != new_canonical_before_llm:
                llm_applied = "hybrid"
                llm_confidence = 0.7  # Default hybrid confidence
                self.staging_service.stage_canonical_and_confidence(
                    extraction_id=extraction_id,
                    canonical_cv=new_canonical,
                    field_confidence=self._calculate_field_confidence(new_canonical),
                    llm_enhancement=llm_applied,
                    llm_confidence=llm_confidence,
                )
            
            # Step 3: Get existing canonical CV from session (if any)
            existing_canonical = session.get("canonical_cv")
            
            # Step 4: Merge with existing data
            logger.info("Merging document data with existing canonical CV")
            if existing_canonical:
                from src.domain.cv.enums import SourceType
                merged_canonical = self.merge_service.merge_canonical_cvs(
                    existing_cv=existing_canonical,
                    new_data=new_canonical,
                    source_type=SourceType.DOCUMENT_UPLOAD,
                    operation="document_upload_merge"
                )
                # Calculate merge stats from comparison
                merge_stats = {
                    "new_fields": 0,
                    "updated_fields": 0,
                    "preserved_fields": 0,
                    "conflicts_resolved": 0
                }
            else:
                merged_canonical = new_canonical
                merge_stats = {
                    "new_fields": 0,
                    "updated_fields": 0,
                    "preserved_fields": 0,
                    "conflicts_resolved": 0
                }
            
            # Step 5: Validate merged canonical CV
            logger.info("Validating merged canonical CV")
            validation_result = self.validation_service.validate_for_save_and_validate(merged_canonical)
            
            # Convert ValidationResult to dict
            if hasattr(validation_result, 'to_dict'):
                validation_result = validation_result.to_dict()
            
            # Step 6: Update session with merged canonical CV and validation results
            session["canonical_cv"] = merged_canonical
            session["validation_results"] = validation_result
            session["last_source"] = "document_upload"
            session["document_metadata"] = file_metadata or {}
            # Register immutable flow stage — the document pipeline's processed output
            # becomes the stable canonical base for preview, edit, and export.
            # Switch flow first so any previous audio/conversation stage is archived.
            from src.application.services.conversation_service import ConversationService as _ConvSvc  # noqa: PLC0415
            _conv = _ConvSvc()
            _conv.switch_flow(session, _ConvSvc.FLOW_DOCUMENT_UPLOAD)
            _conv.set_flow_stage(
                session,
                _ConvSvc.FLOW_DOCUMENT_UPLOAD,
                merged_canonical,
                source_metadata={"filename": (file_metadata or {}).get("filename", "")},
            )
            
            self._save_session(session_id, session)
            
            # DEBUG: Verify session state after update
            logger.info(f"DEBUG: Session {session_id} after document upload:")
            logger.info(f"  - canonical_cv exists: {bool(session.get('canonical_cv'))}")
            logger.info(f"  - validation_results exists: {bool(session.get('validation_results'))}")
            
            # Check candidate data
            cv = session.get('canonical_cv', {})
            candidate = cv.get('candidate', {})
            logger.info(f"  - candidate exists: {bool(candidate)}")
            logger.info(f"  - candidate keys: {list(candidate.keys()) if candidate else 'None'}")
            logger.info(f"  - candidate fullName: {candidate.get('fullName')}")
            logger.info(f"  - candidate personalInfo: {candidate.get('personalInfo')}")
            logger.info(f"  - canonical_cv top-level keys: {list(cv.keys())}")
            
            logger.info(f"Document processing complete for session {session_id}")
            
            # Mark as previewed in staging
            self.staging_service.mark_previewed(extraction_id)
            
            return {
                "canonical_cv": merged_canonical,
                "validation": validation_result,
                "merge_stats": merge_stats,
                "session_id": session_id,
                "extraction_id": extraction_id,
            }
            
        except Exception as e:
            logger.error(f"Error processing document upload: {str(e)}", exc_info=True)
            if extraction_id:
                try:
                    self.staging_service.db.query(
                        __import__(
                            "src.infrastructure.persistence.mysql.staging_models",
                            fromlist=["ExtractionStaging"],
                        ).ExtractionStaging
                    ).filter_by(extraction_id=extraction_id).update(
                        {"extraction_status": "failed"}
                    )
                    self.staging_service.db.commit()
                except:
                    pass
            raise ValidationException(f"Document processing failed: {str(e)}")
    
    def upload_cv_document(
        self,
        session_id: str,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Handle CV document upload with file saving
        
        Args:
            session_id: User session ID
            file_content: Raw file bytes
            filename: Original filename
            
        Returns:
            Processing result from process_document_upload
            
        Raises:
            ValidationException: If upload or processing fails
        """
        temp_file_path: Optional[Path] = None
        try:
            # Validate session before writing any file to disk to avoid orphaned uploads.
            self._get_session(session_id)

            # Validate file extension
            allowed_extensions = ['.doc', '.docx', '.pdf']
            file_ext = Path(filename).suffix.lower()
            
            if file_ext not in allowed_extensions:
                raise ValidationException(
                    f"Unsupported file type: {file_ext}. "
                    f"Allowed types: {', '.join(allowed_extensions)}"
                )
            
            # Create uploads directory if it doesn't exist
            upload_dir = Path("data/storage/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file temporarily
            temp_file_path = upload_dir / f"{session_id}_{filename}"
            
            with open(temp_file_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"Saved document to {temp_file_path}")
            
            # Prepare file metadata
            file_metadata = {
                "filename": filename,
                "size_bytes": len(file_content),
                "extension": file_ext,
                "saved_path": str(temp_file_path)
            }
            
            # Process the document
            result = self.process_document_upload(
                session_id=session_id,
                file_path=str(temp_file_path),
                file_metadata=file_metadata
            )
            
            # Optionally clean up temporary file after processing
            # (You may want to keep it for debugging or reprocessing)
            # temp_file_path.unlink()
            
            return result
            
        except Exception as e:
            if temp_file_path and temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                    logger.info(f"Removed orphaned upload file after failure: {temp_file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup orphaned upload file {temp_file_path}: {cleanup_error}")
            logger.error(f"Error uploading CV document: {str(e)}", exc_info=True)
            raise ValidationException(f"CV document upload failed: {str(e)}")
    
    def get_cv_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get current CV status including validation and completeness
        
        Args:
            session_id: User session ID
            
        Returns:
            Dict containing CV status information
            
        Raises:
            ValidationException: If session not found
        """
        try:
            session = self._get_session(session_id)
            
            canonical_cv = session.get("canonical_cv")
            
            if not canonical_cv:
                return {
                    "has_cv": False,
                    "can_save": False,
                    "can_export": False,
                    "completeness_score": 0.0,
                    "validation": None
                }
            
            # Validate current CV
            validation_result = self.validation_service.validate_for_save_and_validate(canonical_cv)
            
            # Convert ValidationResult to dict
            if hasattr(validation_result, 'to_dict'):
                validation_dict = validation_result.to_dict()
            else:
                validation_dict = validation_result
            
            return {
                "has_cv": True,
                "can_save": validation_dict.get("can_save", False),
                "can_export": validation_dict.get("can_export", False),
                "completeness_score": validation_dict.get("completeness_score", 0.0),
                "validation": validation_dict,
                "last_source": session.get("last_source"),
                "document_metadata": session.get("document_metadata")
            }
            
        except Exception as e:
            logger.error(f"Error getting CV status: {str(e)}", exc_info=True)
            raise ValidationException(f"Failed to get CV status: {str(e)}")
