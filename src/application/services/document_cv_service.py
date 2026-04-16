"""
Document CV Service
Handles CV document upload workflow with canonical schema integration
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from src.application.services.conversation_service import ConversationService
from src.infrastructure.parsers.canonical_document_parser import CanonicalDocumentParser
from src.domain.cv.services.schema_merge_service import SchemaMergeService
from src.domain.cv.services.schema_validation_service import SchemaValidationService
from src.core.exceptions.base import ValidationException

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
        self.validation_service = validation_service or SchemaValidationService()

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
    
    def process_document_upload(
        self,
        session_id: str,
        file_path: str,
        file_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process CV document upload: parse, merge, validate, and store in session
        
        Args:
            session_id: User session ID
            file_path: Path to uploaded CV file
            file_metadata: Optional metadata about the file
            
        Returns:
            Dict containing:
                - canonical_cv: Merged canonical CV data
                - validation: Validation results
                - merge_stats: Merge statistics
                
        Raises:
            ValidationException: If session not found or processing fails
        """
        try:
            logger.info(f"Processing document upload for session {session_id}")
            
            # Step 1: Get session
            session = self._get_session(session_id)
            
            # Step 2: Parse document to canonical schema
            logger.info(f"Parsing document: {file_path}")
            new_canonical = self.document_parser.parse_document_to_canonical(
                file_path=file_path,
                session_id=session_id,
                file_metadata=file_metadata
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
            
            return {
                "canonical_cv": merged_canonical,
                "validation": validation_result,
                "merge_stats": merge_stats,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error processing document upload: {str(e)}", exc_info=True)
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
        try:
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
