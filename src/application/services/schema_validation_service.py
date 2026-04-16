"""
Schema Validation Service - Phase 5

Validates CanonicalCVSchema instances against business rules.
Stores validation results in session for export gates.
"""

from datetime import datetime
from typing import Dict, List, Any
import logging
from copy import deepcopy

from pydantic import ValidationError
from src.domain.cv.models.canonical_cv_schema import CanonicalCVSchema


class ValidationResult:
    """Container for validation results"""
    
    def __init__(
        self,
        errors: List[str] = None,
        warnings: List[str] = None,
        can_export: bool = False,
        validation_timestamp: str = None
    ):
        self.errors = errors or []
        self.warnings = warnings or []
        self.can_export = can_export
        self.validation_timestamp = validation_timestamp or datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for session storage"""
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "can_export": self.can_export,
            "validation_timestamp": self.validation_timestamp
        }


class SchemaValidationService:
    """
    Service for validating CanonicalCVSchema instances
    
    Phase 5: Validates canonical_cv against business rules and schema constraints.
    Replaces legacy ValidationService that operated on cv_data.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _sanitize_for_schema(self, canonical_cv: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize known legacy payload shapes so CanonicalCVSchema validation remains stable.

        Currently fixes malformed audit.manualEdits entries that were stored as merge
        operation records without the required 'field' key.
        """
        cleaned = deepcopy(canonical_cv)
        audit = cleaned.setdefault("audit", {})
        manual_edits = audit.get("manualEdits")

        if not isinstance(manual_edits, list):
            audit["manualEdits"] = []
            return cleaned

        normalized_edits = []
        for idx, entry in enumerate(manual_edits):
            if not isinstance(entry, dict):
                continue

            # Map legacy merge-entry shape into ManualEditModel-compatible shape.
            field_name = entry.get("field") or f"audit.merge.operation.{idx + 1}"
            normalized_edits.append({
                "field": str(field_name),
                "previousValue": entry.get("previousValue"),
                "newValue": entry.get("newValue") or entry.get("description") or entry.get("operation"),
                "editedBy": entry.get("editedBy") or entry.get("sourceType") or "system",
                "editedAt": entry.get("editedAt") or entry.get("timestamp") or datetime.utcnow().isoformat(),
                "editReason": entry.get("editReason") or entry.get("description") or "merge",
            })

        audit["manualEdits"] = normalized_edits
        return cleaned
    
    def validate(self, canonical_cv: Dict[str, Any] | CanonicalCVSchema) -> ValidationResult:
        """
        Validate canonical CV against schema and business rules
        
        Args:
            canonical_cv: Dictionary or CanonicalCVSchema instance
            
        Returns:
            ValidationResult with errors, warnings, and export eligibility
        """
        if not canonical_cv:
            self.logger.error("Cannot validate: canonical_cv is None or empty")
            return ValidationResult(
                errors=["No canonical CV data provided"],
                can_export=False
            )
        
        try:
            # Convert dict to CanonicalCVSchema if needed
            if isinstance(canonical_cv, dict):
                sanitized_cv = self._sanitize_for_schema(canonical_cv)
                schema = CanonicalCVSchema(**sanitized_cv)
            else:
                schema = canonical_cv
            
            self.logger.info(f"Validating canonical CV (cv_id: {schema.cvId})")
            
            errors = []
            warnings = []
            
            # Validate required fields
            errors.extend(self._validate_candidate_info(schema.candidate))
            errors.extend(self._validate_experience(schema.experience))
            errors.extend(self._validate_education(schema.education))
            
            # Validate optional but important fields
            warnings.extend(self._validate_skills(schema.skills))
            warnings.extend(self._validate_personal_details(schema.personalDetails))
            
            # Determine export eligibility
            can_export = len(errors) == 0
            
            result = ValidationResult(
                errors=errors,
                warnings=warnings,
                can_export=can_export
            )
            
            self.logger.info(
                f"Validation complete: {len(errors)} errors, {len(warnings)} warnings, "
                f"can_export={can_export}"
            )
            
            return result
            
        except ValidationError as e:
            self.logger.error(f"Schema validation error: {str(e)}", exc_info=True)
            readable_errors = []
            for err in e.errors():
                location = ".".join(str(part) for part in err.get("loc", []))
                msg = err.get("msg", "Invalid value")
                if location:
                    readable_errors.append(f"{location}: {msg}")
                else:
                    readable_errors.append(msg)
            return ValidationResult(
                errors=readable_errors or ["Invalid CV structure. Please review the highlighted fields."],
                can_export=False,
            )
        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}", exc_info=True)
            return ValidationResult(
                errors=["Unable to validate CV right now. Please try again."],
                can_export=False
            )
    
    def _validate_candidate_info(self, candidate) -> List[str]:
        """Validate candidate information"""
        errors = []
        
        if not candidate.fullName or len(candidate.fullName.strip()) == 0:
            errors.append("Candidate full name is required")
        
        if not candidate.currentDesignation:
            errors.append("Current designation/title is required")
        
        if not candidate.email or "@" not in candidate.email:
            errors.append("Valid email address is required")
        
        if candidate.totalExperienceYears is not None and candidate.totalExperienceYears < 0:
            errors.append("Total experience years cannot be negative")
        
        return errors
    
    def _validate_experience(self, experience) -> List[str]:
        """Validate experience section"""
        errors = []
        
        # At least one project or work history entry required
        if not experience.projects and not experience.workHistory:
            errors.append("At least one project or work experience entry is required")
        
        # Validate each project
        for idx, project in enumerate(experience.projects):
            if not project.projectName:
                errors.append(f"Project #{idx + 1}: Project name is required")
            
            if not project.role:
                errors.append(f"Project #{idx + 1}: Role/designation is required")
        
        return errors
    
    def _validate_education(self, education) -> List[str]:
        """Validate education section"""
        errors = []
        
        if not education or len(education) == 0:
            errors.append("At least one education entry is required")
            return errors
        
        for idx, edu in enumerate(education):
            if not edu.degree:
                errors.append(f"Education #{idx + 1}: Degree is required")
            
            if not edu.institution:
                errors.append(f"Education #{idx + 1}: Institution name is required")
        
        return errors
    
    def _validate_skills(self, skills) -> List[str]:
        """Validate skills section (warnings only)"""
        warnings = []
        
        if not skills.primarySkills or len(skills.primarySkills) == 0:
            warnings.append("No primary skills listed - consider adding key technical skills")
        
        if len(skills.primarySkills) < 3:
            warnings.append("Less than 3 primary skills - consider adding more for better representation")
        
        return warnings
    
    def _validate_personal_details(self, personal_details) -> List[str]:
        """Validate personal details (warnings only)"""
        warnings = []
        
        if not personal_details.linkedinUrl:
            warnings.append("LinkedIn URL not provided - recommended for professional CVs")
        
        if not personal_details.languagesKnown or len(personal_details.languagesKnown) == 0:
            warnings.append("No languages listed - consider adding languages known")
        
        return warnings
