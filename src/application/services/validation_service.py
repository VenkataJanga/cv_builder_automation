"""
Application-level Validation Service

Provides validation capabilities for CV data using the domain SchemaValidationService.
This service acts as a bridge between the REST API and domain validation logic.

Phase 4: Updated to work with canonical CV schema only.
"""

from typing import Dict, Any

from src.core.i18n import t
from src.domain.cv.services.schema_validation_service import SchemaValidationService, ValidationResult
from src.domain.cv.models.canonical_cv_schema import CanonicalCVSchema


class ValidationService:
    """
    Application validation service that delegates to domain SchemaValidationService.
    
    Supports three validation contexts:
    - save: Always allowed, provides completeness feedback
    - save_and_validate: Detailed validation with warnings
    - export: Strict validation, blocks if criteria not met
    """
    
    def __init__(self):
        self.schema_validator = SchemaValidationService()
    
    def validate(self, canonical_cv: Dict[str, Any], operation: str = "save", locale: str | None = None) -> Dict[str, Any]:
        """
        Validate canonical CV data for specified operation.
        
        Args:
            canonical_cv: Canonical CV schema data (dict or CanonicalCVSchema)
            operation: Validation context - "save", "save_and_validate", or "export"
            
        Returns:
            Validation result dictionary compatible with session storage
        """
        # Convert dict to CanonicalCVSchema if needed
        if isinstance(canonical_cv, dict):
            try:
                cv_schema = CanonicalCVSchema(**canonical_cv)
            except Exception:
                # If validation fails, work with dict directly
                cv_schema = canonical_cv
        else:
            cv_schema = canonical_cv
        
        # Select appropriate validation method based on operation
        if operation == "save":
            result = self.schema_validator.validate_for_save(cv_schema, locale=locale)
        elif operation == "save_and_validate":
            result = self.schema_validator.validate_for_save_and_validate(cv_schema, locale=locale)
        elif operation == "export":
            result = self.schema_validator.validate_for_export(cv_schema, locale=locale)
        else:
            # Default to save validation
            result = self.schema_validator.validate_for_save(cv_schema, locale=locale)
        
        return self._convert_to_session_format(result)
    
    def validate_for_save(self, canonical_cv: Dict[str, Any], locale: str | None = None) -> Dict[str, Any]:
        """
        Validate CV for save operation (always allowed).
        
        Args:
            canonical_cv: Canonical CV schema data
            
        Returns:
            Validation result dictionary
        """
        return self.validate(canonical_cv, operation="save", locale=locale)
    
    def validate_for_save_and_validate(self, canonical_cv: Dict[str, Any], locale: str | None = None) -> Dict[str, Any]:
        """
        Validate CV with detailed feedback (save allowed, export conditional).
        
        Args:
            canonical_cv: Canonical CV schema data
            
        Returns:
            Validation result dictionary with detailed warnings
        """
        return self.validate(canonical_cv, operation="save_and_validate", locale=locale)
    
    def validate_for_export(self, canonical_cv: Dict[str, Any], locale: str | None = None) -> Dict[str, Any]:
        """
        Validate CV for export operation (strict, may block).
        
        Args:
            canonical_cv: Canonical CV schema data
            
        Returns:
            Validation result dictionary with export readiness
        """
        return self.validate(canonical_cv, operation="export", locale=locale)
    
    def get_completeness_percentage(self, canonical_cv: Dict[str, Any]) -> float:
        """
        Calculate CV completeness percentage.
        
        Args:
            canonical_cv: Canonical CV schema data
            
        Returns:
            Completeness percentage (0.0 to 100.0)
        """
        return self.schema_validator.get_completeness_percentage(canonical_cv)
    
    def _convert_to_session_format(self, validation_result: ValidationResult) -> Dict[str, Any]:
        """
        Convert ValidationResult to dictionary format for session storage.
        
        Maintains backward compatibility with existing session validation format
        while adding new fields for Phase 4 canonical integration.
        
        Args:
            validation_result: ValidationResult from SchemaValidationService or dict
            
        Returns:
            Dictionary with validation results for session storage
        """
        # Handle both ValidationResult objects and dicts (for testing/mocking)
        if isinstance(validation_result, dict):
            result_dict = validation_result
        else:
            result_dict = validation_result.to_dict()
        
        # Build combined issues list for backward compatibility
        all_issues = []
        all_issues.extend(result_dict.get("validation_errors", []))
        all_issues.extend(result_dict.get("validation_warnings", []))
        
        # Calculate score based on completeness and issues
        completeness = result_dict.get("completeness_percentage", 0)
        error_count = len(result_dict.get("validation_errors", []))
        warning_count = len(result_dict.get("validation_warnings", []))
        
        # Score: Base completeness minus penalties for errors and warnings
        score = max(0, completeness - (error_count * 15) - (warning_count * 5))
        
        # Build response with both old and new formats for compatibility
        return {
            # Legacy format (backward compatibility)
            "is_valid": result_dict.get("success", False),
            "score": score,
            "issues": all_issues,
            "errors": result_dict.get("validation_errors", []),
            "warnings": result_dict.get("validation_warnings", []),
            "suggestions": [],  # Deprecated, kept for compatibility
            
            # Phase 4 canonical format
            "success": result_dict.get("success", False),
            "operation": result_dict.get("operation", "save"),
            "can_save": result_dict.get("can_save", True),
            "can_export": result_dict.get("can_export", False),
            "is_export_ready": result_dict.get("is_export_ready", False),
            "completeness_percentage": completeness,
            "missing_mandatory_fields": result_dict.get("missing_mandatory_fields", []),
            "missing_recommended_fields": result_dict.get("missing_recommended_fields", []),
            "blocked_reason": result_dict.get("blocked_reason"),
            "validation_timestamp": result_dict.get("validation_timestamp"),
            
            # Section scores for confidence (computed from completeness)
            "section_scores": self._compute_section_scores(completeness),
            "confidence": self._compute_confidence(completeness, error_count, warning_count),
        }
    
    def _compute_section_scores(self, completeness: float) -> Dict[str, float]:
        """
        Compute section scores for backward compatibility.
        
        Args:
            completeness: Overall completeness percentage
            
        Returns:
            Dictionary with section scores
        """
        # Simplified scoring based on overall completeness
        base_score = completeness
        
        return {
            "summary_score": base_score,
            "skills_score": base_score,
            "leadership_score": max(40, base_score),  # Minimum 40 for leadership
        }

    def add_extraction_confidence_warnings(
        self,
        validation_result: Dict[str, Any],
        confidence_scores: Dict[str, float],
        locale: str | None = None,
    ) -> Dict[str, Any]:
        """
        Add warnings if LLM extraction confidence is low (Phase 5).
        
        Args:
            validation_result: Existing validation result dict
            confidence_scores: Extraction confidence scores
            
        Returns:
            Updated validation result with warnings added
        """
        if not confidence_scores:
            return validation_result

        result = validation_result.copy()
        overall_confidence = confidence_scores.get("overall", 0.0)

        # Add warning if overall confidence is low
        if overall_confidence < 0.6:
            warning = t(
                "validation.extraction.low_overall",
                locale=locale,
                confidence=overall_confidence * 100,
            )
            if "warnings" not in result:
                result["warnings"] = []
            result["warnings"].append(warning)

        # Add warnings for specific low-confidence fields
        for field, confidence in confidence_scores.items():
            if field != "overall" and confidence < 0.5:
                warning = t(
                    "validation.extraction.low_field",
                    locale=locale,
                    field=field,
                    confidence=confidence * 100,
                )
                if "warnings" not in result:
                    result["warnings"] = []
                if warning not in result["warnings"]:
                    result["warnings"].append(warning)

        return result
    
    def _compute_confidence(
        self, completeness: float, error_count: int, warning_count: int
    ) -> Dict[str, float]:
        """
        Compute confidence scores for backward compatibility.
        
        Args:
            completeness: Overall completeness percentage
            error_count: Number of validation errors
            warning_count: Number of validation warnings
            
        Returns:
            Dictionary with confidence scores
        """
        # Base confidence from completeness
        base_confidence = completeness / 100.0
        
        # Reduce confidence for errors and warnings
        error_penalty = error_count * 0.1
        warning_penalty = warning_count * 0.05
        
        adjusted_confidence = max(0.0, base_confidence - error_penalty - warning_penalty)
        
        return {
            "personal_details_confidence": adjusted_confidence,
            "skills_confidence": adjusted_confidence,
            "summary_confidence": adjusted_confidence,
            "leadership_confidence": max(0.4, adjusted_confidence),  # Minimum 40%
            "overall_score": adjusted_confidence * 100,
        }
