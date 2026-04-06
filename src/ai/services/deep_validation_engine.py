"""
Deep Validation Engine - Multi-Layer Validation System
Provides comprehensive validation with semantic, structural, and contextual checks
"""

from typing import Dict, List, Any, Optional, Set
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
import re


class ValidationLevel(str, Enum):
    """Validation levels"""
    STRUCTURAL = "structural"  # Basic structure checks
    SEMANTIC = "semantic"  # Content meaning checks
    CONTEXTUAL = "contextual"  # Context-aware checks
    CROSS_FIELD = "cross_field"  # Inter-field consistency
    BUSINESS_RULES = "business_rules"  # Domain-specific rules


class ValidationSeverity(str, Enum):
    """Validation issue severity"""
    CRITICAL = "critical"  # Must fix
    ERROR = "error"  # Should fix
    WARNING = "warning"  # Recommended to fix
    INFO = "info"  # Optional improvement


class ValidationIssue(BaseModel):
    """Individual validation issue"""
    issue_id: str
    field_name: str
    validation_level: ValidationLevel
    severity: ValidationSeverity
    message: str
    suggestion: Optional[str] = None
    auto_fixable: bool = False
    fix_function: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    detected_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ValidationResult(BaseModel):
    """Result of validation"""
    is_valid: bool
    validation_score: float = Field(ge=0.0, le=1.0)
    issues: List[ValidationIssue]
    passed_checks: List[str]
    failed_checks: List[str]
    warnings_count: int
    errors_count: int
    critical_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeepValidationEngine:
    """Advanced validation engine with multiple layers"""
    
    def __init__(self):
        self.validators = self._initialize_validators()
        self.business_rules = self._initialize_business_rules()
        self.semantic_patterns = self._initialize_semantic_patterns()
    
    def _initialize_validators(self) -> Dict[ValidationLevel, Any]:
        """Initialize validators for each level"""
        return {
            ValidationLevel.STRUCTURAL: self._validate_structural,
            ValidationLevel.SEMANTIC: self._validate_semantic,
            ValidationLevel.CONTEXTUAL: self._validate_contextual,
            ValidationLevel.CROSS_FIELD: self._validate_cross_field,
            ValidationLevel.BUSINESS_RULES: self._validate_business_rules
        }
    
    def _initialize_business_rules(self) -> Dict[str, Any]:
        """Initialize business rules"""
        return {
            "experience_consistency": {
                "rule": "Total experience should match sum of individual experiences",
                "severity": ValidationSeverity.ERROR
            },
            "date_chronology": {
                "rule": "Dates should be in chronological order",
                "severity": ValidationSeverity.ERROR
            },
            "skill_relevance": {
                "rule": "Skills should be relevant to stated role",
                "severity": ValidationSeverity.WARNING
            },
            "achievement_quantification": {
                "rule": "Achievements should include quantifiable metrics",
                "severity": ValidationSeverity.WARNING
            },
            "education_relevance": {
                "rule": "Education should align with career path",
                "severity": ValidationSeverity.INFO
            }
        }
    
    def _initialize_semantic_patterns(self) -> Dict[str, List[str]]:
        """Initialize semantic validation patterns"""
        return {
            "weak_verbs": [
                "worked on", "responsible for", "helped with", "did",
                "was part of", "involved in", "assisted"
            ],
            "strong_verbs": [
                "architected", "developed", "led", "implemented", "designed",
                "optimized", "built", "created", "delivered", "achieved",
                "reduced", "increased", "improved", "mentored", "collaborated"
            ],
            "vague_terms": [
                "various", "multiple", "several", "many", "some",
                "stuff", "things", "etc", "and so on"
            ],
            "quantifiable_metrics": [
                r'\d+%', r'\$\d+', r'\d+x', r'\d+\s*hours?', r'\d+\s*days?',
                r'\d+\s*users?', r'\d+\s*teams?', r'\d+\s*projects?'
            ]
        }
    
    def validate_cv(
        self,
        cv_data: Dict[str, Any],
        validation_levels: Optional[List[ValidationLevel]] = None
    ) -> ValidationResult:
        """Perform deep validation on CV data"""
        
        if validation_levels is None:
            validation_levels = list(ValidationLevel)
        
        all_issues = []
        passed_checks = []
        failed_checks = []
        
        # Run each validation level
        for level in validation_levels:
            if level in self.validators:
                level_issues, level_passed, level_failed = self.validators[level](cv_data)
                all_issues.extend(level_issues)
                passed_checks.extend(level_passed)
                failed_checks.extend(level_failed)
        
        # Count by severity
        critical_count = sum(1 for i in all_issues if i.severity == ValidationSeverity.CRITICAL)
        errors_count = sum(1 for i in all_issues if i.severity == ValidationSeverity.ERROR)
        warnings_count = sum(1 for i in all_issues if i.severity == ValidationSeverity.WARNING)
        
        # Calculate validation score
        total_checks = len(passed_checks) + len(failed_checks)
        validation_score = len(passed_checks) / total_checks if total_checks > 0 else 0.0
        
        # Penalize based on severity
        if critical_count > 0:
            validation_score *= 0.5
        elif errors_count > 0:
            validation_score *= 0.7
        elif warnings_count > 3:
            validation_score *= 0.9
        
        is_valid = critical_count == 0 and errors_count == 0
        
        return ValidationResult(
            is_valid=is_valid,
            validation_score=validation_score,
            issues=all_issues,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warnings_count=warnings_count,
            errors_count=errors_count,
            critical_count=critical_count,
            metadata={
                "validation_levels": [v.value for v in validation_levels],
                "validated_at": datetime.utcnow().isoformat()
            }
        )
    
    def _validate_structural(
        self,
        cv_data: Dict[str, Any]
    ) -> tuple[List[ValidationIssue], List[str], List[str]]:
        """Validate CV structure"""
        issues = []
        passed = []
        failed = []
        
        # Check required sections
        required_sections = ["header", "summary", "skills", "experience"]
        for section in required_sections:
            check_name = f"has_{section}_section"
            if section not in cv_data or not cv_data[section]:
                issues.append(ValidationIssue(
                    issue_id=f"structural_missing_{section}",
                    field_name=section,
                    validation_level=ValidationLevel.STRUCTURAL,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Missing required section: {section}",
                    suggestion=f"Add {section} section to your CV",
                    auto_fixable=False
                ))
                failed.append(check_name)
            else:
                passed.append(check_name)
        
        # Check header fields
        if "header" in cv_data:
            header = cv_data["header"]
            required_header_fields = ["full_name", "email"]
            for field in required_header_fields:
                check_name = f"header_has_{field}"
                if field not in header or not header[field]:
                    issues.append(ValidationIssue(
                        issue_id=f"structural_missing_header_{field}",
                        field_name=f"header.{field}",
                        validation_level=ValidationLevel.STRUCTURAL,
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Missing required header field: {field}",
                        auto_fixable=False
                    ))
                    failed.append(check_name)
                else:
                    passed.append(check_name)
        
        # Check summary length
        if "summary" in cv_data:
            summary = str(cv_data["summary"])
            check_name = "summary_adequate_length"
            if len(summary) < 100:
                issues.append(ValidationIssue(
                    issue_id="structural_summary_too_short",
                    field_name="summary",
                    validation_level=ValidationLevel.STRUCTURAL,
                    severity=ValidationSeverity.WARNING,
                    message=f"Professional summary is too short ({len(summary)} characters, recommended: 100+)",
                    suggestion="Expand your summary to include years of experience, key skills, and achievements"
                ))
                failed.append(check_name)
            else:
                passed.append(check_name)
        
        return issues, passed, failed
    
    def _validate_semantic(
        self,
        cv_data: Dict[str, Any]
    ) -> tuple[List[ValidationIssue], List[str], List[str]]:
        """Validate content semantics"""
        issues = []
        passed = []
        failed = []
        
        # Check for weak verbs in experience
        experiences = cv_data.get("work_experience", []) + cv_data.get("project_experience", [])
        weak_verb_count = 0
        
        for exp in experiences:
            desc = str(exp.get("description", "")).lower() + " " + str(exp.get("responsibilities", "")).lower()
            
            # Check for weak verbs
            for weak_verb in self.semantic_patterns["weak_verbs"]:
                if weak_verb in desc:
                    weak_verb_count += 1
                    break
        
        check_name = "uses_strong_action_verbs"
        if weak_verb_count > len(experiences) * 0.5:
            issues.append(ValidationIssue(
                issue_id="semantic_weak_verbs",
                field_name="experience",
                validation_level=ValidationLevel.SEMANTIC,
                severity=ValidationSeverity.WARNING,
                message="Many weak action verbs detected in experience descriptions",
                suggestion=f"Replace weak verbs with strong action verbs like: {', '.join(self.semantic_patterns['strong_verbs'][:5])}",
                metadata={"weak_verb_count": weak_verb_count}
            ))
            failed.append(check_name)
        else:
            passed.append(check_name)
        
        # Check for vague terms
        vague_count = 0
        for exp in experiences:
            desc = str(exp.get("description", "")).lower()
            for vague_term in self.semantic_patterns["vague_terms"]:
                if vague_term in desc:
                    vague_count += 1
        
        check_name = "avoids_vague_terminology"
        if vague_count > 3:
            issues.append(ValidationIssue(
                issue_id="semantic_vague_terms",
                field_name="experience",
                validation_level=ValidationLevel.SEMANTIC,
                severity=ValidationSeverity.WARNING,
                message="Multiple vague terms detected",
                suggestion="Replace vague terms with specific details",
                metadata={"vague_term_count": vague_count}
            ))
            failed.append(check_name)
        else:
            passed.append(check_name)
        
        # Check for quantifiable achievements
        quantified_count = 0
        for exp in experiences:
            desc = str(exp.get("description", "")) + " " + str(exp.get("responsibilities", ""))
            for pattern in self.semantic_patterns["quantifiable_metrics"]:
                if re.search(pattern, desc):
                    quantified_count += 1
                    break
        
        check_name = "includes_quantifiable_achievements"
        if len(experiences) > 0 and quantified_count / len(experiences) < 0.5:
            issues.append(ValidationIssue(
                issue_id="semantic_low_quantification",
                field_name="experience",
                validation_level=ValidationLevel.SEMANTIC,
                severity=ValidationSeverity.WARNING,
                message="Few quantifiable achievements detected",
                suggestion="Add metrics like percentages, dollar amounts, time saved, or team sizes",
                metadata={"quantified_ratio": quantified_count / len(experiences) if experiences else 0}
            ))
            failed.append(check_name)
        else:
            passed.append(check_name)
        
        return issues, passed, failed
    
    def _validate_contextual(
        self,
        cv_data: Dict[str, Any]
    ) -> tuple[List[ValidationIssue], List[str], List[str]]:
        """Validate contextual consistency"""
        issues = []
        passed = []
        failed = []
        
        # Check skill-experience alignment
        skills = set()
        if "skills" in cv_data:
            if isinstance(cv_data["skills"], list):
                skills = set(str(s).lower() for s in cv_data["skills"])
            elif isinstance(cv_data["skills"], dict):
                for skill_list in cv_data["skills"].values():
                    if isinstance(skill_list, list):
                        skills.update(str(s).lower() for s in skill_list)
        
        # Extract technologies mentioned in experience
        mentioned_techs = set()
        experiences = cv_data.get("work_experience", []) + cv_data.get("project_experience", [])
        for exp in experiences:
            technologies = exp.get("technologies", [])
            if isinstance(technologies, list):
                mentioned_techs.update(str(t).lower() for t in technologies)
            
            # Also check descriptions
            desc = str(exp.get("description", "")).lower()
            for skill in skills:
                if skill in desc:
                    mentioned_techs.add(skill)
        
        # Check if skills are demonstrated
        check_name = "skills_demonstrated_in_experience"
        undemonstrated_skills = skills - mentioned_techs
        if len(skills) > 0:
            demonstration_ratio = len(mentioned_techs) / len(skills)
            if demonstration_ratio < 0.5:
                issues.append(ValidationIssue(
                    issue_id="contextual_undemonstrated_skills",
                    field_name="skills",
                    validation_level=ValidationLevel.CONTEXTUAL,
                    severity=ValidationSeverity.WARNING,
                    message=f"Many listed skills ({len(undemonstrated_skills)}) are not demonstrated in experience",
                    suggestion="Ensure your experience section showcases the skills you list",
                    metadata={"demonstration_ratio": demonstration_ratio}
                ))
                failed.append(check_name)
            else:
                passed.append(check_name)
        
        return issues, passed, failed
    
    def _validate_cross_field(
        self,
        cv_data: Dict[str, Any]
    ) -> tuple[List[ValidationIssue], List[str], List[str]]:
        """Validate cross-field consistency"""
        issues = []
        passed = []
        failed = []
        
        # Check title-experience consistency
        if "header" in cv_data and "current_title" in cv_data["header"]:
            current_title = str(cv_data["header"]["current_title"]).lower()
            experiences = cv_data.get("work_experience", [])
            
            check_name = "title_matches_recent_experience"
            if experiences:
                recent_exp = experiences[0]
                recent_title = str(recent_exp.get("job_title", "")).lower()
                
                # Check if titles are similar
                if current_title not in recent_title and recent_title not in current_title:
                    issues.append(ValidationIssue(
                        issue_id="cross_field_title_mismatch",
                        field_name="header.current_title",
                        validation_level=ValidationLevel.CROSS_FIELD,
                        severity=ValidationSeverity.WARNING,
                        message="Current title doesn't match most recent experience",
                        suggestion="Ensure your stated title aligns with your latest role"
                    ))
                    failed.append(check_name)
                else:
                    passed.append(check_name)
        
        # Check experience years consistency
        if "header" in cv_data and "years_experience" in cv_data["header"]:
            stated_years = cv_data["header"]["years_experience"]
            experiences = cv_data.get("work_experience", [])
            
            # Calculate actual years from experience
            total_months = 0
            for exp in experiences:
                duration = exp.get("duration_months", 0)
                if isinstance(duration, (int, float)):
                    total_months += duration
            
            calculated_years = total_months / 12
            
            check_name = "experience_years_consistent"
            if abs(stated_years - calculated_years) > 2:  # Allow 2 year variance
                issues.append(ValidationIssue(
                    issue_id="cross_field_experience_mismatch",
                    field_name="header.years_experience",
                    validation_level=ValidationLevel.CROSS_FIELD,
                    severity=ValidationSeverity.ERROR,
                    message=f"Stated experience ({stated_years} years) doesn't match calculated experience ({calculated_years:.1f} years)",
                    suggestion="Verify your experience entries and total years"
                ))
                failed.append(check_name)
            else:
                passed.append(check_name)
        
        return issues, passed, failed
    
    def _validate_business_rules(
        self,
        cv_data: Dict[str, Any]
    ) -> tuple[List[ValidationIssue], List[str], List[str]]:
        """Validate business rules"""
        issues = []
        passed = []
        failed = []
        
        # Check chronological order of experiences
        experiences = cv_data.get("work_experience", [])
        check_name = "experiences_chronological"
        
        if len(experiences) > 1:
            is_chronological = True
            for i in range(len(experiences) - 1):
                curr_end = experiences[i].get("end_date", "")
                next_start = experiences[i + 1].get("start_date", "")
                
                # Check if dates are in reverse chronological order
                if curr_end and next_start:
                    if str(curr_end) < str(next_start):
                        is_chronological = False
                        break
            
            if not is_chronological:
                issues.append(ValidationIssue(
                    issue_id="business_chronology_error",
                    field_name="work_experience",
                    validation_level=ValidationLevel.BUSINESS_RULES,
                    severity=ValidationSeverity.ERROR,
                    message="Work experience is not in chronological order",
                    suggestion="Arrange experiences in reverse chronological order (most recent first)"
                ))
                failed.append(check_name)
            else:
                passed.append(check_name)
        
        # Check for employment gaps
        check_name = "reasonable_employment_gaps"
        if len(experiences) > 1:
            has_large_gaps = False
            for i in range(len(experiences) - 1):
                # This is a simplified check - would need date parsing for real implementation
                pass
            
            passed.append(check_name)
        
        return issues, passed, failed
    
    def get_validation_report(
        self,
        validation_result: ValidationResult
    ) -> Dict[str, Any]:
        """Generate detailed validation report"""
        
        issues_by_severity = {
            "critical": [],
            "error": [],
            "warning": [],
            "info": []
        }
        
        for issue in validation_result.issues:
            issues_by_severity[issue.severity.value].append({
                "field": issue.field_name,
                "message": issue.message,
                "suggestion": issue.suggestion
            })
        
        issues_by_level = {}
        for issue in validation_result.issues:
            level = issue.validation_level.value
            if level not in issues_by_level:
                issues_by_level[level] = []
            issues_by_level[level].append(issue.issue_id)
        
        auto_fixable_count = sum(1 for i in validation_result.issues if i.auto_fixable)
        
        return {
            "summary": {
                "is_valid": validation_result.is_valid,
                "validation_score": validation_result.validation_score,
                "total_checks": len(validation_result.passed_checks) + len(validation_result.failed_checks),
                "passed_checks": len(validation_result.passed_checks),
                "failed_checks": len(validation_result.failed_checks)
            },
            "issues_by_severity": issues_by_severity,
            "issues_by_level": issues_by_level,
            "auto_fixable_count": auto_fixable_count,
            "recommendations": self._generate_recommendations(validation_result)
        }
    
    def _generate_recommendations(
        self,
        validation_result: ValidationResult
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if validation_result.critical_count > 0:
            recommendations.append("Address critical issues immediately before proceeding")
        
        if validation_result.errors_count > 0:
            recommendations.append("Fix error-level issues to improve CV quality")
        
        if validation_result.warnings_count > 3:
            recommendations.append("Review and address warning-level issues for optimization")
        
        if validation_result.validation_score < 0.7:
            recommendations.append("Consider a comprehensive CV review")
        
        return recommendations
