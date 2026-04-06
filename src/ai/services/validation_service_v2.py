"""
Enhanced Validation Service V2 - Deep validation with confidence scoring

Features:
- Multi-level validation (syntax, semantic, completeness)
- Confidence scoring per field
- Actionable recommendations
- Schema compliance verification
- Data quality metrics
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Validation issue severity levels"""
    CRITICAL = "critical"  # Blocks export
    ERROR = "error"  # Major issues
    WARNING = "warning"  # Minor issues
    INFO = "info"  # Suggestions


class ValidationCategory(str, Enum):
    """Categories of validation"""
    REQUIRED_FIELD = "required_field"
    FORMAT = "format"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    QUALITY = "quality"


@dataclass
class ValidationIssue:
    """Individual validation issue"""
    field_path: str
    category: ValidationCategory
    severity: ValidationSeverity
    message: str
    recommendation: str
    confidence_impact: float = 0.0  # How much this affects confidence (0-1)
    auto_fixable: bool = False


@dataclass
class FieldValidation:
    """Validation result for a single field"""
    field_path: str
    is_valid: bool
    confidence_score: float  # 0-1
    issues: List[ValidationIssue] = field(default_factory=list)
    quality_score: float = 1.0  # 0-1
    completeness: float = 1.0  # 0-1


@dataclass
class ValidationReport:
    """Comprehensive validation report"""
    overall_valid: bool
    can_export: bool
    confidence_score: float
    completeness_score: float
    quality_score: float
    
    field_validations: Dict[str, FieldValidation]
    issues: List[ValidationIssue]
    
    # Categorized issues
    critical_issues: List[ValidationIssue] = field(default_factory=list)
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    follow_up_questions: List[Dict[str, Any]] = field(default_factory=list)
    
    metadata: Dict[str, Any] = field(default_factory=dict)


class ValidationServiceV2:
    """Enhanced validation with deep checks and confidence scoring"""
    
    # Required fields that must be present
    REQUIRED_FIELDS = {
        "header.full_name": "Full name is required",
        "header.email": "Email address is required",
        "header.contact_number": "Contact number is required",
        "summary": "Professional summary is required",
        "skills": "At least one skill is required",
    }
    
    # Email regex pattern
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # Phone patterns
    PHONE_PATTERN = r'^[\d\s\-\+\(\)]{10,}$'
    
    def validate_comprehensive(
        self,
        cv_data: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None
    ) -> ValidationReport:
        """
        Perform comprehensive validation with confidence scoring
        
        Args:
            cv_data: Extracted CV data
            schema: Optional schema definition
            
        Returns:
            ValidationReport with detailed findings
        """
        logger.info("Starting comprehensive validation")
        
        field_validations = {}
        all_issues = []
        
        # Validate required fields
        required_issues = self._validate_required_fields(cv_data)
        all_issues.extend(required_issues)
        
        # Validate header
        header_validation = self._validate_header(cv_data.get("header", {}))
        field_validations["header"] = header_validation
        all_issues.extend(header_validation.issues)
        
        # Validate summary
        summary_validation = self._validate_summary(cv_data.get("summary", ""))
        field_validations["summary"] = summary_validation
        all_issues.extend(summary_validation.issues)
        
        # Validate skills
        skills_validation = self._validate_skills(
            cv_data.get("skills", []),
            cv_data.get("secondary_skills", [])
        )
        field_validations["skills"] = skills_validation
        all_issues.extend(skills_validation.issues)
        
        # Validate work experience
        work_validation = self._validate_work_experience(
            cv_data.get("work_experience", [])
        )
        field_validations["work_experience"] = work_validation
        all_issues.extend(work_validation.issues)
        
        # Validate projects
        project_validation = self._validate_projects(
            cv_data.get("project_experience", [])
        )
        field_validations["project_experience"] = project_validation
        all_issues.extend(project_validation.issues)
        
        # Validate education
        edu_validation = self._validate_education(
            cv_data.get("education", [])
        )
        field_validations["education"] = edu_validation
        all_issues.extend(edu_validation.issues)
        
        # Validate technical fields
        tech_validation = self._validate_technical_fields(cv_data)
        all_issues.extend(tech_validation)
        
        # Categorize issues by severity
        critical_issues = [i for i in all_issues if i.severity == ValidationSeverity.CRITICAL]
        errors = [i for i in all_issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in all_issues if i.severity == ValidationSeverity.WARNING]
        
        # Calculate scores
        confidence_score = self._calculate_confidence(field_validations, all_issues)
        completeness_score = self._calculate_completeness(cv_data, field_validations)
        quality_score = self._calculate_quality(field_validations)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(all_issues, cv_data)
        
        # Generate follow-up questions
        follow_up_questions = self._generate_followup_questions(all_issues, cv_data)
        
        # Determine if can export
        can_export = len(critical_issues) == 0
        overall_valid = len(critical_issues) == 0 and len(errors) == 0
        
        report = ValidationReport(
            overall_valid=overall_valid,
            can_export=can_export,
            confidence_score=confidence_score,
            completeness_score=completeness_score,
            quality_score=quality_score,
            field_validations=field_validations,
            issues=all_issues,
            critical_issues=critical_issues,
            errors=errors,
            warnings=warnings,
            recommendations=recommendations,
            follow_up_questions=follow_up_questions,
            metadata={
                "total_issues": len(all_issues),
                "critical_count": len(critical_issues),
                "error_count": len(errors),
                "warning_count": len(warnings)
            }
        )
        
        logger.info(f"Validation complete. Confidence: {confidence_score:.2f}, Can export: {can_export}")
        
        return report
    
    def _validate_required_fields(self, cv_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate presence of required fields"""
        issues = []
        
        for field_path, message in self.REQUIRED_FIELDS.items():
            value = self._get_nested_value(cv_data, field_path)
            
            if not value:
                issues.append(ValidationIssue(
                    field_path=field_path,
                    category=ValidationCategory.REQUIRED_FIELD,
                    severity=ValidationSeverity.CRITICAL,
                    message=message,
                    recommendation=f"Please provide {field_path.split('.')[-1]}",
                    confidence_impact=0.3,
                    auto_fixable=False
                ))
        
        return issues
    
    def _validate_header(self, header: Dict[str, Any]) -> FieldValidation:
        """Validate header fields"""
        issues = []
        confidence = 1.0
        
        # Validate email format
        email = header.get("email", "")
        if email and not re.match(self.EMAIL_PATTERN, email):
            issues.append(ValidationIssue(
                field_path="header.email",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.ERROR,
                message="Invalid email format",
                recommendation="Provide a valid email address (e.g., name@company.com)",
                confidence_impact=0.2,
                auto_fixable=False
            ))
            confidence -= 0.2
        
        # Validate phone format
        phone = header.get("contact_number", "")
        if phone and not re.match(self.PHONE_PATTERN, phone):
            issues.append(ValidationIssue(
                field_path="header.contact_number",
                category=ValidationCategory.FORMAT,
                severity=ValidationSeverity.WARNING,
                message="Phone number format may be invalid",
                recommendation="Provide phone number with at least 10 digits",
                confidence_impact=0.1,
                auto_fixable=False
            ))
            confidence -= 0.1
        
        # Validate name
        name = header.get("full_name", "")
        if name and len(name.split()) < 2:
            issues.append(ValidationIssue(
                field_path="header.full_name",
                category=ValidationCategory.QUALITY,
                severity=ValidationSeverity.WARNING,
                message="Name should include first and last name",
                recommendation="Provide full name (first and last)",
                confidence_impact=0.1,
                auto_fixable=False
            ))
            confidence -= 0.1
        
        # Check completeness
        expected_fields = ["full_name", "email", "contact_number", "current_title", "location"]
        present = sum(1 for f in expected_fields if header.get(f))
        completeness = present / len(expected_fields)
        
        return FieldValidation(
            field_path="header",
            is_valid=len([i for i in issues if i.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]]) == 0,
            confidence_score=max(0.0, confidence),
            issues=issues,
            completeness=completeness
        )
    
    def _validate_summary(self, summary: str) -> FieldValidation:
        """Validate professional summary"""
        issues = []
        confidence = 1.0
        
        if not summary:
            return FieldValidation(
                field_path="summary",
                is_valid=False,
                confidence_score=0.0,
                completeness=0.0
            )
        
        # Check length
        word_count = len(summary.split())
        if word_count < 20:
            issues.append(ValidationIssue(
                field_path="summary",
                category=ValidationCategory.QUALITY,
                severity=ValidationSeverity.WARNING,
                message="Professional summary is too short",
                recommendation="Summary should be at least 20 words to provide meaningful context",
                confidence_impact=0.15,
                auto_fixable=False
            ))
            confidence -= 0.15
        elif word_count > 150:
            issues.append(ValidationIssue(
                field_path="summary",
                category=ValidationCategory.QUALITY,
                severity=ValidationSeverity.INFO,
                message="Professional summary is quite long",
                recommendation="Consider condensing to 50-100 words for better readability",
                confidence_impact=0.05,
                auto_fixable=False
            ))
            confidence -= 0.05
        
        return FieldValidation(
            field_path="summary",
            is_valid=True,
            confidence_score=max(0.0, confidence),
            issues=issues,
            completeness=1.0 if word_count >= 20 else 0.5
        )
    
    def _validate_skills(
        self,
        primary_skills: List[str],
        secondary_skills: List[str]
    ) -> FieldValidation:
        """Validate skills lists"""
        issues = []
        confidence = 1.0
        
        total_skills = len(primary_skills) + len(secondary_skills)
        
        if total_skills < 3:
            issues.append(ValidationIssue(
                field_path="skills",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.WARNING,
                message="Very few skills listed",
                recommendation="Add more relevant skills to strengthen your profile",
                confidence_impact=0.2,
                auto_fixable=False
            ))
            confidence -= 0.2
        
        # Check for duplicates
        all_skills_lower = [s.lower() for s in primary_skills + secondary_skills]
        if len(all_skills_lower) != len(set(all_skills_lower)):
            issues.append(ValidationIssue(
                field_path="skills",
                category=ValidationCategory.QUALITY,
                severity=ValidationSeverity.INFO,
                message="Duplicate skills detected",
                recommendation="Remove duplicate skills across primary and secondary",
                confidence_impact=0.05,
                auto_fixable=True
            ))
            confidence -= 0.05
        
        return FieldValidation(
            field_path="skills",
            is_valid=total_skills >= 1,
            confidence_score=max(0.0, confidence),
            issues=issues,
            completeness=min(1.0, total_skills / 5.0)
        )
    
    def _validate_work_experience(
        self,
        work_experience: List[Dict[str, Any]]
    ) -> FieldValidation:
        """Validate work experience entries"""
        issues = []
        confidence = 1.0
        
        if not work_experience:
            issues.append(ValidationIssue(
                field_path="work_experience",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.WARNING,
                message="No work experience entries",
                recommendation="Add work experience details to strengthen your CV",
                confidence_impact=0.2,
                auto_fixable=False
            ))
            return FieldValidation(
                field_path="work_experience",
                is_valid=True,
                confidence_score=0.5,
                issues=issues,
                completeness=0.0
            )
        
        # Validate each entry
        for idx, entry in enumerate(work_experience):
            required = ["company", "role", "duration"]
            missing = [f for f in required if not entry.get(f)]
            
            if missing:
                issues.append(ValidationIssue(
                    field_path=f"work_experience[{idx}]",
                    category=ValidationCategory.COMPLETENESS,
                    severity=ValidationSeverity.WARNING,
                    message=f"Missing fields: {', '.join(missing)}",
                    recommendation=f"Add {', '.join(missing)} for complete work history",
                    confidence_impact=0.1,
                    auto_fixable=False
                ))
                confidence -= 0.1
        
        return FieldValidation(
            field_path="work_experience",
            is_valid=True,
            confidence_score=max(0.0, confidence),
            issues=issues,
            completeness=min(1.0, len(work_experience) / 2.0)
        )
    
    def _validate_projects(
        self,
        projects: List[Dict[str, Any]]
    ) -> FieldValidation:
        """Validate project experience entries"""
        issues = []
        confidence = 1.0
        
        if not projects:
            issues.append(ValidationIssue(
                field_path="project_experience",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.WARNING,
                message="No project experience entries",
                recommendation="Add project details to showcase your work",
                confidence_impact=0.15,
                auto_fixable=False
            ))
            return FieldValidation(
                field_path="project_experience",
                is_valid=True,
                confidence_score=0.6,
                issues=issues,
                completeness=0.0
            )
        
        # Validate each project
        for idx, project in enumerate(projects):
            if not project.get("project_name"):
                issues.append(ValidationIssue(
                    field_path=f"project_experience[{idx}].project_name",
                    category=ValidationCategory.REQUIRED_FIELD,
                    severity=ValidationSeverity.ERROR,
                    message="Project name is missing",
                    recommendation="Provide a name for the project",
                    confidence_impact=0.15,
                    auto_fixable=False
                ))
                confidence -= 0.15
            
            if not project.get("description"):
                issues.append(ValidationIssue(
                    field_path=f"project_experience[{idx}].description",
                    category=ValidationCategory.COMPLETENESS,
                    severity=ValidationSeverity.WARNING,
                    message="Project description is missing",
                    recommendation="Add a description of what the project involved",
                    confidence_impact=0.1,
                    auto_fixable=False
                ))
                confidence -= 0.1
        
        return FieldValidation(
            field_path="project_experience",
            is_valid=True,
            confidence_score=max(0.0, confidence),
            issues=issues,
            completeness=min(1.0, len(projects) / 2.0)
        )
    
    def _validate_education(
        self,
        education: List[Dict[str, Any]]
    ) -> FieldValidation:
        """Validate education entries"""
        issues = []
        confidence = 1.0
        
        if not education:
            issues.append(ValidationIssue(
                field_path="education",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.WARNING,
                message="No education entries",
                recommendation="Add your education background",
                confidence_impact=0.2,
                auto_fixable=False
            ))
            return FieldValidation(
                field_path="education",
                is_valid=True,
                confidence_score=0.5,
                issues=issues,
                completeness=0.0
            )
        
        # Validate each entry
        for idx, edu in enumerate(education):
            if not edu.get("degree"):
                issues.append(ValidationIssue(
                    field_path=f"education[{idx}].degree",
                    category=ValidationCategory.REQUIRED_FIELD,
                    severity=ValidationSeverity.ERROR,
                    message="Degree name is missing",
                    recommendation="Specify the degree obtained",
                    confidence_impact=0.15,
                    auto_fixable=False
                ))
                confidence -= 0.15
            
            if not edu.get("institution"):
                issues.append(ValidationIssue(
                    field_path=f"education[{idx}].institution",
                    category=ValidationCategory.COMPLETENESS,
                    severity=ValidationSeverity.WARNING,
                    message="Institution name is missing",
                    recommendation="Add the name of the educational institution",
                    confidence_impact=0.1,
                    auto_fixable=False
                ))
                confidence -= 0.1
        
        return FieldValidation(
            field_path="education",
            is_valid=True,
            confidence_score=max(0.0, confidence),
            issues=issues,
            completeness=1.0
        )
    
    def _validate_technical_fields(self, cv_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate technical skill fields"""
        issues = []
        
        # Check databases
        databases = cv_data.get("databases", [])
        if not databases:
            issues.append(ValidationIssue(
                field_path="databases",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.INFO,
                message="No database experience listed",
                recommendation="Consider adding database technologies you've worked with",
                confidence_impact=0.05,
                auto_fixable=False
            ))
        
        # Check operating systems
        os_list = cv_data.get("operating_systems", [])
        if not os_list:
            issues.append(ValidationIssue(
                field_path="operating_systems",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.INFO,
                message="No operating systems listed",
                recommendation="Add operating systems you're familiar with",
                confidence_impact=0.05,
                auto_fixable=False
            ))
        
        # Check cloud platforms
        cloud = cv_data.get("cloud_platforms", [])
        if not cloud:
            issues.append(ValidationIssue(
                field_path="cloud_platforms",
                category=ValidationCategory.COMPLETENESS,
                severity=ValidationSeverity.INFO,
                message="No cloud platforms listed",
                recommendation="Add cloud platforms if you have experience with them",
                confidence_impact=0.05,
                auto_fixable=False
            ))
        
        return issues
    
    def _calculate_confidence(
        self,
        field_validations: Dict[str, FieldValidation],
        issues: List[ValidationIssue]
    ) -> float:
        """Calculate overall confidence score"""
        if not field_validations:
            return 0.0
        
        # Start with perfect score
        confidence = 1.0
        
        # Deduct for issues
        for issue in issues:
            confidence -= issue.confidence_impact
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_completeness(
        self,
        cv_data: Dict[str, Any],
        field_validations: Dict[str, FieldValidation]
    ) -> float:
        """Calculate overall completeness score"""
        if not field_validations:
            return 0.0
        
        scores = [v.completeness for v in field_validations.values()]
        return sum(scores) / len(scores) if scores else 0.0
    
    def _calculate_quality(
        self,
        field_validations: Dict[str, FieldValidation]
    ) -> float:
        """Calculate overall quality score"""
        if not field_validations:
            return 0.0
        
        scores = [v.quality_score for v in field_validations.values()]
        return sum(scores) / len(scores) if scores else 0.0
    
    def _generate_recommendations(
        self,
        issues: List[ValidationIssue],
        cv_data: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Group issues by severity
        critical = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in issues if i.severity == ValidationSeverity.WARNING]
        
        if critical:
            recommendations.append(f"⚠️ Fix {len(critical)} critical issue(s) before exporting")
            for issue in critical[:3]:  # Top 3
                recommendations.append(f"  • {issue.recommendation}")
        
        if errors:
            recommendations.append(f"🔴 Address {len(errors)} error(s) to improve quality")
            for issue in errors[:2]:  # Top 2
                recommendations.append(f"  • {issue.recommendation}")
        
        if warnings:
            recommendations.append(f"⚡ Consider fixing {len(warnings)} warning(s) for completeness")
        
        # Add specific recommendations based on content
        if len(cv_data.get("project_experience", [])) < 2:
            recommendations.append("💡 Add more project details to showcase your experience")
        
        if len(cv_data.get("skills", [])) + len(cv_data.get("secondary_skills", [])) < 5:
            recommendations.append("💡 Add more skills to strengthen your profile")
        
        return recommendations
    
    def _generate_followup_questions(
        self,
        issues: List[ValidationIssue],
        cv_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate intelligent follow-up questions"""
        questions = []
        
        # Questions based on missing critical fields
        if not cv_data.get("header", {}).get("email"):
            questions.append({
                "field": "header.email",
                "question": "What is your email address?",
                "type": "text",
                "validation": "email",
                "priority": "high"
            })
        
        if not cv_data.get("header", {}).get("contact_number"):
            questions.append({
                "field": "header.contact_number",
                "question": "What is your contact number?",
                "type": "text",
                "validation": "phone",
                "priority": "high"
            })
        
        # Questions based on incomplete sections
        if not cv_data.get("project_experience"):
            questions.append({
                "field": "project_experience",
                "question": "Can you describe a recent project you worked on?",
                "type": "textarea",
                "priority": "medium",
                "hint": "Include project name, role, technologies, and key achievements"
            })
        
        if not cv_data.get("databases"):
            questions.append({
                "field": "databases",
                "question": "Which database technologies have you worked with?",
                "type": "multiselect",
                "options": ["MySQL", "PostgreSQL", "MongoDB", "Oracle", "SQL Server", "DB2"],
                "priority": "low"
            })
        
        if not cv_data.get("operating_systems"):
            questions.append({
                "field": "operating_systems",
                "question": "Which operating systems are you familiar with?",
                "type": "multiselect",
                "options": ["Linux", "Windows", "macOS", "Unix"],
                "priority": "low"
            })
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        questions.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2))
        
        return questions[:5]  # Return top 5 questions
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dict using dot notation"""
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        
        return value
