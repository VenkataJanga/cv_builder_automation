"""
Schema Validation Service for Canonical CV Schema

This service provides comprehensive validation capabilities for the Canonical CV Schema
across different operation contexts (save, save_and_validate, export).

Author: CV Builder Automation System
Date: 2026-04-12
"""

from datetime import datetime
from typing import Dict, List, Any, Optional

from src.core.i18n import t
from src.domain.cv.models.canonical_cv_schema import CanonicalCVSchema


class ValidationResult:
    """
    Standardized validation result container for all CV validation operations.
    
    Provides consistent response structure across save, save_and_validate, and export operations.
    """
    
    def __init__(
        self,
        success: bool,
        operation: str,
        can_save: bool = True,
        can_export: bool = False,
        is_export_ready: bool = False,
        completeness_percentage: float = 0.0,
        missing_mandatory_fields: Optional[List[str]] = None,
        missing_recommended_fields: Optional[List[str]] = None,
        validation_errors: Optional[List[str]] = None,
        validation_warnings: Optional[List[str]] = None,
        blocked_reason: Optional[str] = None
    ):
        self.success = success
        self.operation = operation
        self.can_save = can_save
        self.can_export = can_export
        self.is_export_ready = is_export_ready
        self.completeness_percentage = completeness_percentage
        self.missing_mandatory_fields = missing_mandatory_fields or []
        self.missing_recommended_fields = missing_recommended_fields or []
        self.validation_errors = validation_errors or []
        self.validation_warnings = validation_warnings or []
        self.blocked_reason = blocked_reason
        self.validation_timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary for API responses and session storage."""
        return {
            "success": self.success,
            "operation": self.operation,
            "can_save": self.can_save,
            "can_export": self.can_export,
            "is_export_ready": self.is_export_ready,
            "completeness_percentage": self.completeness_percentage,
            "missing_mandatory_fields": self.missing_mandatory_fields,
            "missing_recommended_fields": self.missing_recommended_fields,
            "validation_errors": self.validation_errors,
            "validation_warnings": self.validation_warnings,
            "blocked_reason": self.blocked_reason,
            "validation_timestamp": self.validation_timestamp
        }


class SchemaValidationService:
    """
    Canonical CV Schema validation service with context-aware validation rules.
    
    Provides different validation levels:
    - Save: Always allowed (supports partial saves)
    - Save & Validate: Shows missing fields but doesn't block
    - Export: Blocks if mandatory fields missing
    """
    
    # Mandatory fields required for CV export
    MANDATORY_FIELDS = [
        "candidate.fullName",
        "candidate.phoneNumber", 
        "candidate.email",
        "candidate.currentLocation.city",
        "candidate.currentLocation.country"
    ]
    
    # Recommended fields for better CV quality
    RECOMMENDED_FIELDS = [
        "candidate.summary",
        "candidate.totalExperienceYears",
        "candidate.currentOrganization",
        "candidate.currentDesignation",
        "skills.primarySkills",
        "skills.technicalSkills"
    ]
    
    # Field weights for completeness calculation
    COMPLETENESS_WEIGHTS = {
        "candidate": 0.30,    # 30% - Personal information
        "experience": 0.40,   # 40% - Work history and projects
        "skills": 0.20,       # 20% - Skills and technologies  
        "education": 0.10     # 10% - Educational background
    }
    
    def validate_for_save(self, canonical_cv: CanonicalCVSchema, locale: str | None = None) -> ValidationResult:
        """
        Validate CV for save operation.
        
        Save operations are always allowed to support partial saves and progressive data entry.
        This method provides completeness feedback without blocking the operation.
        
        Args:
            canonical_cv: The canonical CV schema to validate
            
        Returns:
            ValidationResult with save permission and completeness info
        """
        # Convert Pydantic model to dict if needed
        if isinstance(canonical_cv, dict):
            cv_dict = canonical_cv
        elif hasattr(canonical_cv, 'model_dump'):
            cv_dict = canonical_cv.model_dump()
        elif hasattr(canonical_cv, 'dict'):
            cv_dict = canonical_cv.dict()
        else:
            cv_dict = canonical_cv
        
        completeness = self.get_completeness_percentage(cv_dict)
        missing_mandatory = self.get_missing_mandatory_fields(cv_dict)
        missing_recommended = self.get_missing_recommended_fields(cv_dict)
        
        warnings = []
        if missing_mandatory:
            warnings.append(t("validation.save.missing_mandatory", locale=locale, fields=", ".join(missing_mandatory)))
        if completeness < 50:
            warnings.append(t("validation.save.less_than_50", locale=locale))
            
        return ValidationResult(
            success=True,
            operation="save",
            can_save=True,
            can_export=len(missing_mandatory) == 0,
            is_export_ready=len(missing_mandatory) == 0 and completeness >= 70,
            completeness_percentage=completeness,
            missing_mandatory_fields=missing_mandatory,
            missing_recommended_fields=missing_recommended,
            validation_warnings=warnings
        )
    
    def validate_for_save_and_validate(self, canonical_cv: CanonicalCVSchema, locale: str | None = None) -> ValidationResult:
        """
        Validate CV for save and validate operation.
        
        This validation level provides detailed feedback about missing fields and completion
        status while still allowing the save operation. Used when users want comprehensive
        validation feedback.
        
        Args:
            canonical_cv: The canonical CV schema to validate
            
        Returns:
            ValidationResult with detailed validation feedback
        """
        # Convert Pydantic model to dict if needed
        if isinstance(canonical_cv, dict):
            cv_dict = canonical_cv
        elif hasattr(canonical_cv, 'model_dump'):
            cv_dict = canonical_cv.model_dump()
        elif hasattr(canonical_cv, 'dict'):
            cv_dict = canonical_cv.dict()
        else:
            cv_dict = canonical_cv
        
        completeness = self.get_completeness_percentage(cv_dict)
        missing_mandatory = self.get_missing_mandatory_fields(cv_dict)
        missing_recommended = self.get_missing_recommended_fields(cv_dict)
        
        errors = []
        warnings = []
        
        # Check for critical missing sections
        if not self._has_experience_data(cv_dict):
            warnings.append(t("validation.save_validate.no_experience", locale=locale))
        
        if not self._has_skills_data(cv_dict):
            warnings.append(t("validation.save_validate.no_skills", locale=locale))
            
        if not self._has_education_data(cv_dict):
            warnings.append(t("validation.save_validate.no_education", locale=locale))
        
        # Mandatory field warnings
        if missing_mandatory:
            warnings.append(t("validation.save_validate.required_for_export", locale=locale, fields=", ".join(missing_mandatory)))
        
        # Recommended field suggestions
        if missing_recommended:
            warnings.append(t("validation.save_validate.recommended_add", locale=locale, fields=", ".join(missing_recommended[:3])))
        
        return ValidationResult(
            success=True,
            operation="save_and_validate",
            can_save=True,
            can_export=len(missing_mandatory) == 0,
            is_export_ready=len(missing_mandatory) == 0 and completeness >= 70,
            completeness_percentage=completeness,
            missing_mandatory_fields=missing_mandatory,
            missing_recommended_fields=missing_recommended,
            validation_errors=errors,
            validation_warnings=warnings
        )
    
    def validate_for_export(self, canonical_cv: CanonicalCVSchema, locale: str | None = None) -> ValidationResult:
        """
        Validate CV for export operation.
        
        Export validation is strict and will block the operation if mandatory fields
        are missing or if the CV doesn't meet minimum export readiness criteria.
        
        Args:
            canonical_cv: The canonical CV schema to validate
            
        Returns:
            ValidationResult with export readiness determination
        """
        # Convert Pydantic model to dict if needed
        if isinstance(canonical_cv, dict):
            cv_dict = canonical_cv
        elif hasattr(canonical_cv, 'model_dump'):
            cv_dict = canonical_cv.model_dump()
        elif hasattr(canonical_cv, 'dict'):
            cv_dict = canonical_cv.dict()
        else:
            cv_dict = canonical_cv
        
        completeness = self.get_completeness_percentage(cv_dict)
        missing_mandatory = self.get_missing_mandatory_fields(cv_dict)
        
        errors = []
        blocked_reason = None
        
        # Check mandatory fields
        if missing_mandatory:
            errors.append(t("validation.export.missing_required", locale=locale, fields=", ".join(missing_mandatory)))
            blocked_reason = t("validation.export.blocked_no_mandatory", locale=locale)
        
        # Check minimum experience requirement
        if not self._has_experience_data(cv_dict):
            errors.append(t("validation.export.no_experience_required", locale=locale))
            if not blocked_reason:
                blocked_reason = t("validation.export.blocked_no_experience", locale=locale)
        
        # Check minimum completeness
        if completeness < 40:
            errors.append(t("validation.export.too_incomplete", locale=locale, completeness=completeness))
            if not blocked_reason:
                blocked_reason = t("validation.export.blocked_not_complete", locale=locale)
        
        can_export = len(errors) == 0
        
        return ValidationResult(
            success=can_export,
            operation="export",
            can_save=True,  # Can always save even if can't export
            can_export=can_export,
            is_export_ready=can_export and completeness >= 70,
            completeness_percentage=completeness,
            missing_mandatory_fields=missing_mandatory,
            validation_errors=errors,
            blocked_reason=blocked_reason
        )
    
    def get_completeness_percentage(self, cv_dict: Dict[str, Any]) -> float:
        """
        Calculate CV completeness percentage based on weighted section scoring.
        
        Scoring breakdown:
        - Candidate (30%): Personal info, contact details, summary
        - Experience (40%): Work history and projects
        - Skills (20%): Technical and functional skills
        - Education (10%): Educational background
        
        Args:
            cv_dict: CV data as dictionary
            
        Returns:
            Completeness percentage (0.0 to 100.0)
        """
        if not cv_dict:
            return 0.0
        
        section_scores = {
            "candidate": self._score_candidate_section(cv_dict.get("candidate", {})),
            "experience": self._score_experience_section(cv_dict.get("experience", {})),
            "skills": self._score_skills_section(cv_dict.get("skills", {})),
            "education": self._score_education_section(cv_dict.get("education", []))
        }
        
        weighted_score = sum(
            score * self.COMPLETENESS_WEIGHTS[section]
            for section, score in section_scores.items()
        )
        
        return min(100.0, max(0.0, weighted_score))
    
    def get_missing_mandatory_fields(self, cv_dict: Dict[str, Any]) -> List[str]:
        """
        Get list of missing mandatory fields required for CV export.
        
        Args:
            cv_dict: CV data as dictionary
            
        Returns:
            List of missing mandatory field paths
        """
        missing_fields = []
        
        for field_path in self.MANDATORY_FIELDS:
            if not self._get_nested_field(cv_dict, field_path):
                # Convert field path to human-readable format
                readable_field = self._get_readable_field_name(field_path)
                missing_fields.append(readable_field)
        
        return missing_fields
    
    def get_missing_recommended_fields(self, cv_dict: Dict[str, Any]) -> List[str]:
        """
        Get list of missing recommended fields for better CV quality.
        
        Args:
            cv_dict: CV data as dictionary
            
        Returns:
            List of missing recommended field paths
        """
        missing_fields = []
        
        for field_path in self.RECOMMENDED_FIELDS:
            if not self._get_nested_field(cv_dict, field_path):
                readable_field = self._get_readable_field_name(field_path)
                missing_fields.append(readable_field)
        
        return missing_fields
    
    def _score_candidate_section(self, candidate: Dict[str, Any]) -> float:
        """Score candidate section (0-100)."""
        if not candidate:
            return 0.0
        
        required_fields = ["fullName", "phoneNumber", "email"]
        location_fields = ["currentLocation.city", "currentLocation.country"]
        optional_fields = ["summary", "totalExperienceYears", "currentOrganization"]
        
        score = 0.0
        
        # Required fields (60% of section score)
        required_score = sum(
            20 for field in required_fields 
            if self._get_nested_field({"candidate": candidate}, f"candidate.{field}")
        )
        
        # Location fields (20% of section score)  
        location_score = 20 if all(
            self._get_nested_field({"candidate": candidate}, f"candidate.{field}")
            for field in location_fields
        ) else 0
        
        # Optional fields (20% of section score)
        optional_score = sum(
            7 for field in optional_fields[:3]  # Limit to 3 fields for 21 points max
            if self._get_nested_field({"candidate": candidate}, f"candidate.{field}")
        )
        
        return min(100.0, required_score + location_score + optional_score)
    
    def _score_experience_section(self, experience: Dict[str, Any]) -> float:
        """Score experience section (0-100)."""
        if not experience:
            return 0.0
        
        score = 0.0
        
        # Work history (50% of experience score)
        work_history = experience.get("workHistory", [])
        if work_history:
            score += 50.0
            # Bonus for detailed work history
            if len(work_history) >= 2:
                score += 10.0
        
        # Projects (50% of experience score)
        projects = experience.get("projects", [])
        if projects:
            score += 50.0
            # Bonus for multiple projects
            if len(projects) >= 2:
                score += 10.0
        
        return min(100.0, score)
    
    def _score_skills_section(self, skills: Dict[str, Any]) -> float:
        """Score skills section (0-100)."""
        if not skills:
            return 0.0
        
        skill_fields = [
            "primarySkills", "secondarySkills", "technicalSkills", 
            "functionalSkills", "toolsAndPlatforms"
        ]
        
        score = 0.0
        populated_fields = 0
        
        for field in skill_fields:
            field_data = skills.get(field, [])
            if field_data and len(field_data) > 0:
                populated_fields += 1
                score += 20.0  # 20 points per populated skill category
        
        return min(100.0, score)
    
    def _score_education_section(self, education: List[Dict[str, Any]]) -> float:
        """Score education section (0-100)."""
        if not education:
            return 0.0
        
        score = 60.0  # Base score for having education
        
        # Bonus for multiple education entries
        if len(education) >= 2:
            score += 20.0
        
        # Bonus for detailed education info
        for edu in education[:2]:  # Check first 2 entries
            if edu.get("degree") and edu.get("institution"):
                score += 10.0
        
        return min(100.0, score)
    
    def _has_experience_data(self, cv_dict: Dict[str, Any]) -> bool:
        """Check if CV has work experience or project data."""
        experience = cv_dict.get("experience", {})
        work_history = experience.get("workHistory", [])
        projects = experience.get("projects", [])
        return len(work_history) > 0 or len(projects) > 0
    
    def _has_skills_data(self, cv_dict: Dict[str, Any]) -> bool:
        """Check if CV has skills data."""
        skills = cv_dict.get("skills", {})
        skill_fields = ["primarySkills", "secondarySkills", "technicalSkills", "functionalSkills"]
        return any(skills.get(field, []) for field in skill_fields)
    
    def _has_education_data(self, cv_dict: Dict[str, Any]) -> bool:
        """Check if CV has education data."""
        education = cv_dict.get("education", [])
        return len(education) > 0
    
    def _get_nested_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """
        Get value from nested dictionary using dot notation path.
        
        Args:
            data: Dictionary to search in
            field_path: Dot-separated path (e.g., "candidate.currentLocation.city")
            
        Returns:
            Field value or None if not found
        """
        if not data or not field_path:
            return None
        
        keys = field_path.split(".")
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        # Consider empty strings, empty lists, and None as missing
        if current == "" or current == [] or current is None:
            return None
            
        return current
    
    def _get_readable_field_name(self, field_path: str) -> str:
        """
        Convert field path to human-readable field name.
        
        Args:
            field_path: Dot-separated field path
            
        Returns:
            Human-readable field name
        """
        field_mapping = {
            "candidate.fullName": "Full Name",
            "candidate.phoneNumber": "Phone Number",
            "candidate.email": "Email Address",
            "candidate.currentLocation.city": "Current City",
            "candidate.currentLocation.country": "Current Country",
            "candidate.summary": "Professional Summary",
            "candidate.totalExperienceYears": "Total Experience",
            "candidate.currentOrganization": "Current Organization",
            "candidate.currentDesignation": "Current Role",
            "skills.primarySkills": "Primary Skills",
            "skills.technicalSkills": "Technical Skills"
        }
        
        return field_mapping.get(field_path, field_path.split(".")[-1].replace("_", " ").title())
