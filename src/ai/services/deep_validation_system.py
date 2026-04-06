"""
Deep Validation System
Multi-layered validation with business rules and data quality checks
"""

from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import re


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues"""
    CRITICAL = "critical"  # Prevents CV generation
    ERROR = "error"  # Should be fixed
    WARNING = "warning"  # Recommended to fix
    INFO = "info"  # Informational only


class ValidationCategory(str, Enum):
    """Categories of validation checks"""
    COMPLETENESS = "completeness"
    FORMAT = "format"
    CONSISTENCY = "consistency"
    BUSINESS_RULE = "business_rule"
    DATA_QUALITY = "data_quality"
    CROSS_FIELD = "cross_field"


class ValidationIssue(BaseModel):
    """Individual validation issue"""
    field_path: str
    category: ValidationCategory
    severity: ValidationSeverity
    message: str
    suggestion: Optional[str] = None
    current_value: Any = None
    expected_format: Optional[str] = None
    can_auto_fix: bool = False
    auto_fix_value: Any = None


class ValidationReport(BaseModel):
    """Complete validation report"""
    is_valid: bool
    validation_score: float = Field(ge=0.0, le=1.0)
    issues: List[ValidationIssue] = Field(default_factory=list)
    critical_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    validated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    summary: str = ""


class ValidationRule(BaseModel):
    """Defines a validation rule"""
    name: str
    category: ValidationCategory
    severity: ValidationSeverity
    field_path: str
    validator_func: str  # Name of validator function
    error_message: str
    suggestion_template: Optional[str] = None


class DeepValidationSystem:
    """
    Comprehensive validation system with multiple layers of checks
    """
    
    def __init__(self):
        self.rules = self._load_validation_rules()
        self.validators = self._register_validators()
    
    def _load_validation_rules(self) -> List[ValidationRule]:
        """Load all validation rules"""
        return [
            # Completeness Rules
            ValidationRule(
                name="required_full_name",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.CRITICAL,
                field_path="header.full_name",
                validator_func="validate_required",
                error_message="Full name is required"
            ),
            ValidationRule(
                name="required_email",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.CRITICAL,
                field_path="header.email",
                validator_func="validate_required",
                error_message="Email address is required"
            ),
            ValidationRule(
                name="required_contact",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.CRITICAL,
                field_path="header.contact_number",
                validator_func="validate_required",
                error_message="Contact number is required"
            ),
            ValidationRule(
                name="required_skills",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.ERROR,
                field_path="skills",
                validator_func="validate_required_array",
                error_message="At least one skill is required"
            ),
            
            # Format Rules
            ValidationRule(
                name="email_format",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.ERROR,
                field_path="header.email",
                validator_func="validate_email_format",
                error_message="Invalid email format",
                suggestion_template="Email should be in format: name@domain.com"
            ),
            ValidationRule(
                name="phone_format",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.WARNING,
                field_path="header.contact_number",
                validator_func="validate_phone_format",
                error_message="Invalid phone number format",
                suggestion_template="Phone should be 10 digits"
            ),
            
            # Business Rules
            ValidationRule(
                name="experience_years",
                category=ValidationCategory.BUSINESS_RULE,
                severity=ValidationSeverity.WARNING,
                field_path="header.total_experience",
                validator_func="validate_experience_range",
                error_message="Experience years seem unusual",
                suggestion_template="Experience should be between 0-50 years"
            ),
            ValidationRule(
                name="minimum_education",
                category=ValidationCategory.BUSINESS_RULE,
                severity=ValidationSeverity.WARNING,
                field_path="education",
                validator_func="validate_minimum_education",
                error_message="At least one education entry recommended"
            ),
            
            # Data Quality Rules
            ValidationRule(
                name="name_quality",
                category=ValidationCategory.DATA_QUALITY,
                severity=ValidationSeverity.WARNING,
                field_path="header.full_name",
                validator_func="validate_name_quality",
                error_message="Name may contain invalid characters"
            ),
            ValidationRule(
                name="summary_quality",
                category=ValidationCategory.DATA_QUALITY,
                severity=ValidationSeverity.INFO,
                field_path="summary",
                validator_func="validate_summary_quality",
                error_message="Summary could be improved"
            ),
            
            # Cross-field Rules
            ValidationRule(
                name="skills_project_alignment",
                category=ValidationCategory.CROSS_FIELD,
                severity=ValidationSeverity.WARNING,
                field_path="skills",
                validator_func="validate_skills_projects_alignment",
                error_message="Skills don't align with project technologies"
            )
        ]
    
    def _register_validators(self) -> Dict[str, callable]:
        """Register all validator functions"""
        return {
            "validate_required": self._validate_required,
            "validate_required_array": self._validate_required_array,
            "validate_email_format": self._validate_email_format,
            "validate_phone_format": self._validate_phone_format,
            "validate_experience_range": self._validate_experience_range,
            "validate_minimum_education": self._validate_minimum_education,
            "validate_name_quality": self._validate_name_quality,
            "validate_summary_quality": self._validate_summary_quality,
            "validate_skills_projects_alignment": self._validate_skills_projects_alignment
        }
    
    def validate(self, cv_data: Dict) -> ValidationReport:
        """
        Perform comprehensive validation of CV data
        """
        report = ValidationReport(is_valid=True, validation_score=1.0)
        issues = []
        
        # Run all validation rules
        for rule in self.rules:
            validator = self.validators.get(rule.validator_func)
            if not validator:
                continue
            
            issue = validator(cv_data, rule)
            if issue:
                issues.append(issue)
                
                # Count by severity
                if issue.severity == ValidationSeverity.CRITICAL:
                    report.critical_count += 1
                    report.is_valid = False
                elif issue.severity == ValidationSeverity.ERROR:
                    report.error_count += 1
                elif issue.severity == ValidationSeverity.WARNING:
                    report.warning_count += 1
                else:
                    report.info_count += 1
        
        report.issues = issues
        
        # Calculate validation score
        report.validation_score = self._calculate_validation_score(report)
        
        # Generate summary
        report.summary = self._generate_summary(report)
        
        return report
    
    def _validate_required(self, data: Dict, rule: ValidationRule) -> Optional[ValidationIssue]:
        """Validate required field is present and not empty"""
        value = self._get_field_value(data, rule.field_path)
        
        if not value or (isinstance(value, str) and not value.strip()):
            return ValidationIssue(
                field_path=rule.field_path,
                category=rule.category,
                severity=rule.severity,
                message=rule.error_message,
                suggestion="Please provide this required information",
                current_value=value
            )
        return None
    
    def _validate_required_array(self, data: Dict, rule: ValidationRule) -> Optional[ValidationIssue]:
        """Validate required array field has at least one item"""
        value = self._get_field_value(data, rule.field_path)
        
        if not value or not isinstance(value, list) or len(value) == 0:
            return ValidationIssue(
                field_path=rule.field_path,
                category=rule.category,
                severity=rule.severity,
                message=rule.error_message,
                suggestion="Please add at least one item",
                current_value=value
            )
        return None
    
    def _validate_email_format(self, data: Dict, rule: ValidationRule) -> Optional[ValidationIssue]:
        """Validate email format"""
        value = self._get_field_value(data, rule.field_path)
        
        if not value:
            return None  # Handle by required validation
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, str(value)):
            return ValidationIssue(
                field_path=rule.field_path,
                category=rule.category,
                severity=rule.severity,
                message=rule.error_message,
                suggestion=rule.suggestion_template,
                current_value=value,
                expected_format="name@domain.com"
            )
        return None
    
    def _validate_phone_format(self, data: Dict, rule: ValidationRule) -> Optional[ValidationIssue]:
        """Validate phone number format"""
        value = self._get_field_value(data, rule.field_path)
        
        if not value:
            return None
        
        # Remove common separators
        cleaned = str(value).replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        
        if not cleaned.isdigit() or len(cleaned) not in [10, 11, 12]:
            return ValidationIssue(
                field_path=rule.field_path,
                category=rule.category,
                severity=rule.severity,
                message=rule.error_message,
                suggestion=rule.suggestion_template,
                current_value=value,
                expected_format="10-12 digits"
            )
        return None
    
    def _validate_experience_range(self, data: Dict, rule: ValidationRule) -> Optional[ValidationIssue]:
        """Validate experience years is in reasonable range"""
        value = self._get_field_value(data, rule.field_path)
        
        if not value:
            return None
        
        # Extract number from string like "16 years"
        match = re.search(r'(\d+)', str(value))
        if match:
            years = int(match.group(1))
            if years < 0 or years > 50:
                return ValidationIssue(
                    field_path=rule.field_path,
                    category=rule.category,
                    severity=rule.severity,
                    message=rule.error_message,
                    suggestion=rule.suggestion_template,
                    current_value=value
                )
        return None
    
    def _validate_minimum_education(self, data: Dict, rule: ValidationRule) -> Optional[ValidationIssue]:
        """Validate at least one education entry"""
        value = self._get_field_value(data, rule.field_path)
        
        if not value or not isinstance(value, list) or len(value) == 0:
            return ValidationIssue(
                field_path=rule.field_path,
                category=rule.category,
                severity=rule.severity,
                message=rule.error_message,
                suggestion="Add education background information",
                current_value=value
            )
        return None
    
    def _validate_name_quality(self, data: Dict, rule: ValidationRule) -> Optional[ValidationIssue]:
        """Validate name doesn't contain numbers or special chars"""
        value = self._get_field_value(data, rule.field_path)
        
        if not value:
            return None
        
        # Check for numbers or excessive special chars
        if re.search(r'\d', str(value)) or re.search(r'[^a-zA-Z\s\.\-]', str(value)):
            return ValidationIssue(
                field_path=rule.field_path,
                category=rule.category,
                severity=rule.severity,
                message=rule.error_message,
                suggestion="Name should contain only letters and spaces",
                current_value=value
            )
        return None
    
    def _validate_summary_quality(self, data: Dict, rule: ValidationRule) -> Optional[ValidationIssue]:
        """Validate summary meets quality standards"""
        value = self._get_field_value(data, rule.field_path)
        
        if not value:
            return None
        
        summary_text = str(value)
        
        # Check minimum length
        if len(summary_text) < 50:
            return ValidationIssue(
                field_path=rule.field_path,
                category=rule.category,
                severity=rule.severity,
                message="Summary is too short",
                suggestion="Summary should be at least 50 characters and describe your expertise",
                current_value=value
            )
        
        return None
    
    def _validate_skills_projects_alignment(
        self,
        data: Dict,
        rule: ValidationRule
    ) -> Optional[ValidationIssue]:
        """Validate skills align with project technologies"""
        skills = self._get_field_value(data, "skills")
        projects = self._get_field_value(data, "project_experience")
        
        if not skills or not projects:
            return None
        
        # Extract all technologies from projects
        project_techs = set()
        for project in projects:
            if isinstance(project, dict):
                techs = project.get("technologies_used", [])
                if isinstance(techs, list):
                    project_techs.update([t.lower() for t in techs])
        
        # Check if primary skills appear in projects
        skill_list = skills if isinstance(skills, list) else [skills]
        unmatched_skills = []
        
        for skill in skill_list[:3]:  # Check top 3 skills
            if skill.lower() not in project_techs:
                unmatched_skills.append(skill)
        
        if unmatched_skills:
            return ValidationIssue(
                field_path=rule.field_path,
                category=rule.category,
                severity=rule.severity,
                message=f"Some skills not reflected in projects: {', '.join(unmatched_skills)}",
                suggestion="Ensure primary skills are demonstrated in project experience",
                current_value=skills
            )
        
        return None
    
    def _get_field_value(self, data: Dict, field_path: str) -> Any:
        """Get value from nested dict using dot notation"""
        parts = field_path.split(".")
        value = data
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            
            if value is None:
                return None
        
        return value
    
    def _calculate_validation_score(self, report: ValidationReport) -> float:
        """Calculate overall validation score"""
        if not report.issues:
            return 1.0
        
        # Weight by severity
        weights = {
            ValidationSeverity.CRITICAL: 0.3,
            ValidationSeverity.ERROR: 0.2,
            ValidationSeverity.WARNING: 0.1,
            ValidationSeverity.INFO: 0.05
        }
        
        total_deduction = 0.0
        for issue in report.issues:
            total_deduction += weights.get(issue.severity, 0.0)
        
        score = max(0.0, 1.0 - total_deduction)
        return round(score, 2)
    
    def _generate_summary(self, report: ValidationReport) -> str:
        """Generate human-readable summary"""
        if report.is_valid and not report.issues:
            return "All validation checks passed successfully"
        
        parts = []
        
        if report.critical_count > 0:
            parts.append(f"{report.critical_count} critical issue(s)")
        if report.error_count > 0:
            parts.append(f"{report.error_count} error(s)")
        if report.warning_count > 0:
            parts.append(f"{report.warning_count} warning(s)")
        if report.info_count > 0:
            parts.append(f"{report.info_count} info message(s)")
        
        return "Found: " + ", ".join(parts)
    
    def get_auto_fixable_issues(self, report: ValidationReport) -> List[ValidationIssue]:
        """Get list of issues that can be auto-fixed"""
        return [issue for issue in report.issues if issue.can_auto_fix]
    
    def apply_auto_fixes(self, data: Dict, report: ValidationReport) -> Dict:
        """Apply auto-fixes to data"""
        fixed_data = data.copy()
        
        for issue in self.get_auto_fixable_issues(report):
            if issue.auto_fix_value is not None:
                # Apply the fix
                parts = issue.field_path.split(".")
                target = fixed_data
                for part in parts[:-1]:
                    target = target.setdefault(part, {})
                target[parts[-1]] = issue.auto_fix_value
        
        return fixed_data
