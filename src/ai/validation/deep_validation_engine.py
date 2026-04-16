"""
Deep Validation Engine
Multi-layer validation system with semantic, structural, and business rule validation
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime
import re


class ValidationLevel(str, Enum):
    """Validation severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"


class ValidationCategory(str, Enum):
    """Categories of validation"""
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    BUSINESS_RULE = "business_rule"
    DATA_QUALITY = "data_quality"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"


class ValidationIssue(BaseModel):
    """Represents a validation issue"""
    category: ValidationCategory
    level: ValidationLevel
    field: str
    message: str
    suggestion: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """Result of validation process"""
    is_valid: bool
    overall_score: float = Field(ge=0.0, le=1.0)
    issues: List[ValidationIssue] = Field(default_factory=list)
    validated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def error_count(self) -> int:
        return len([i for i in self.issues if i.level == ValidationLevel.ERROR])
    
    @property
    def warning_count(self) -> int:
        return len([i for i in self.issues if i.level == ValidationLevel.WARNING])
    
    @property
    def by_category(self) -> Dict[ValidationCategory, List[ValidationIssue]]:
        """Group issues by category"""
        grouped = {}
        for issue in self.issues:
            if issue.category not in grouped:
                grouped[issue.category] = []
            grouped[issue.category].append(issue)
        return grouped


class ValidationRule(BaseModel):
    """Definition of a validation rule"""
    name: str
    category: ValidationCategory
    level: ValidationLevel
    description: str
    fields: List[str]
    enabled: bool = True


class DeepValidationEngine:
    """
    Comprehensive validation engine with multiple validation layers
    """
    
    def __init__(self):
        self.rules: List[ValidationRule] = []
        self._initialize_rules()
    
    def _initialize_rules(self):
        """Initialize validation rules"""
        
        # Structural validation rules
        self.rules.extend([
            ValidationRule(
                name="required_fields_present",
                category=ValidationCategory.STRUCTURAL,
                level=ValidationLevel.ERROR,
                description="Check all required fields are present",
                fields=["full_name", "email", "contact_number", "total_experience"]
            ),
            ValidationRule(
                name="field_type_validation",
                category=ValidationCategory.STRUCTURAL,
                level=ValidationLevel.ERROR,
                description="Validate field data types",
                fields=["*"]
            )
        ])
        
        # Semantic validation rules
        self.rules.extend([
            ValidationRule(
                name="email_format",
                category=ValidationCategory.SEMANTIC,
                level=ValidationLevel.ERROR,
                description="Validate email format",
                fields=["email"]
            ),
            ValidationRule(
                name="phone_format",
                category=ValidationCategory.SEMANTIC,
                level=ValidationLevel.WARNING,
                description="Validate phone number format",
                fields=["contact_number"]
            ),
            ValidationRule(
                name="experience_range",
                category=ValidationCategory.SEMANTIC,
                level=ValidationLevel.WARNING,
                description="Validate experience is within reasonable range",
                fields=["total_experience"]
            )
        ])
        
        # Business rule validation
        self.rules.extend([
            ValidationRule(
                name="minimum_skills_count",
                category=ValidationCategory.BUSINESS_RULE,
                level=ValidationLevel.WARNING,
                description="Ensure minimum number of skills are listed",
                fields=["skills"]
            ),
            ValidationRule(
                name="education_consistency",
                category=ValidationCategory.BUSINESS_RULE,
                level=ValidationLevel.INFO,
                description="Check education timeline consistency",
                fields=["education"]
            )
        ])
        
        # Data quality validation
        self.rules.extend([
            ValidationRule(
                name="text_quality",
                category=ValidationCategory.DATA_QUALITY,
                level=ValidationLevel.WARNING,
                description="Check text quality (spelling, grammar indicators)",
                fields=["professional_summary", "projects"]
            ),
            ValidationRule(
                name="data_richness",
                category=ValidationCategory.DATA_QUALITY,
                level=ValidationLevel.SUGGESTION,
                description="Assess richness and detail of data",
                fields=["*"]
            )
        ])
        
        # Completeness validation
        self.rules.extend([
            ValidationRule(
                name="optional_fields_completeness",
                category=ValidationCategory.COMPLETENESS,
                level=ValidationLevel.SUGGESTION,
                description="Check completeness of optional but recommended fields",
                fields=["professional_summary", "certifications", "achievements"]
            )
        ])
        
        # Consistency validation
        self.rules.extend([
            ValidationRule(
                name="cross_field_consistency",
                category=ValidationCategory.CONSISTENCY,
                level=ValidationLevel.WARNING,
                description="Check consistency across related fields",
                fields=["*"]
            )
        ])
    
    def validate(self, cv_data: Dict[str, Any]) -> ValidationResult:
        """
        Perform comprehensive validation on CV data
        """
        issues: List[ValidationIssue] = []
        
        # Run all enabled validation rules
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            rule_issues = self._apply_rule(rule, cv_data)
            issues.extend(rule_issues)
        
        # Calculate overall validation score
        overall_score = self._calculate_score(issues)
        
        # Determine if valid (no errors)
        is_valid = all(issue.level != ValidationLevel.ERROR for issue in issues)
        
        return ValidationResult(
            is_valid=is_valid,
            overall_score=overall_score,
            issues=issues,
            metadata={
                "rules_applied": len([r for r in self.rules if r.enabled]),
                "cv_fields": list(cv_data.keys())
            }
        )
    
    def _apply_rule(
        self,
        rule: ValidationRule,
        cv_data: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """Apply a single validation rule"""
        
        method_name = f"_validate_{rule.name}"
        validator_method = getattr(self, method_name, None)
        
        if validator_method:
            return validator_method(cv_data, rule)
        
        return []
    
    def _validate_required_fields_present(
        self,
        cv_data: Dict,
        rule: ValidationRule
    ) -> List[ValidationIssue]:
        """Validate required fields are present"""
        issues = []
        
        required_fields = rule.fields
        
        for field in required_fields:
            if field not in cv_data or not cv_data.get(field):
                issues.append(ValidationIssue(
                    category=rule.category,
                    level=rule.level,
                    field=field,
                    message=f"Required field '{field}' is missing or empty",
                    suggestion=f"Please provide a value for {field}",
                    confidence=1.0
                ))
        
        return issues
    
    def _validate_field_type_validation(
        self,
        cv_data: Dict,
        rule: ValidationRule
    ) -> List[ValidationIssue]:
        """Validate field data types"""
        issues = []
        
        expected_types = {
            "full_name": str,
            "email": str,
            "contact_number": str,
            "total_experience": (str, int, float),
            "skills": list,
            "education": list,
            "projects": list
        }
        
        for field, expected_type in expected_types.items():
            if field in cv_data:
                value = cv_data[field]
                if not isinstance(value, expected_type):
                    issues.append(ValidationIssue(
                        category=rule.category,
                        level=rule.level,
                        field=field,
                        message=f"Field '{field}' has incorrect type. Expected {expected_type}, got {type(value)}",
                        confidence=1.0
                    ))
        
        return issues
    
    def _validate_email_format(
        self,
        cv_data: Dict,
        rule: ValidationRule
    ) -> List[ValidationIssue]:
        """Validate email format"""
        issues = []
        
        email = cv_data.get("email", "")
        if email:
            # Simple email regex
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                issues.append(ValidationIssue(
                    category=rule.category,
                    level=rule.level,
                    field="email",
                    message="Email format appears invalid",
                    suggestion="Please provide a valid email address (e.g., user@example.com)",
                    confidence=0.9
                ))
        
        return issues
    
    def _validate_phone_format(
        self,
        cv_data: Dict,
        rule: ValidationRule
    ) -> List[ValidationIssue]:
        """Validate phone number format"""
        issues = []
        
        phone = cv_data.get("contact_number", "")
        if phone:
            # Remove common separators
            clean_phone = re.sub(r'[\s\-\(\)]', '', str(phone))
            
            # Check if it's a valid number (basic check)
            if not clean_phone.isdigit() or len(clean_phone) < 10:
                issues.append(ValidationIssue(
                    category=rule.category,
                    level=rule.level,
                    field="contact_number",
                    message="Phone number format may be invalid",
                    suggestion="Please provide a valid phone number with at least 10 digits",
                    confidence=0.8
                ))
        
        return issues
    
    def _validate_experience_range(
        self,
        cv_data: Dict,
        rule: ValidationRule
    ) -> List[ValidationIssue]:
        """Validate experience is within reasonable range"""
        issues = []
        
        experience = cv_data.get("total_experience")
        if experience:
            try:
                # Extract numeric value
                exp_years = float(re.findall(r'\d+\.?\d*', str(experience))[0])
                
                if exp_years < 0 or exp_years > 50:
                    issues.append(ValidationIssue(
                        category=rule.category,
                        level=rule.level,
                        field="total_experience",
                        message=f"Experience value ({exp_years} years) seems outside normal range",
                        suggestion="Please verify the years of experience",
                        confidence=0.85
                    ))
            except (IndexError, ValueError):
                issues.append(ValidationIssue(
                    category=rule.category,
                    level=ValidationLevel.WARNING,
                    field="total_experience",
                    message="Could not parse experience value",
                    confidence=0.7
                ))
        
        return issues
    
    def _validate_minimum_skills_count(
        self,
        cv_data: Dict,
        rule: ValidationRule
    ) -> List[ValidationIssue]:
        """Ensure minimum number of skills are listed"""
        issues = []
        
        skills = cv_data.get("skills", [])
        min_skills = 3
        
        if len(skills) < min_skills:
            issues.append(ValidationIssue(
                category=rule.category,
                level=rule.level,
                field="skills",
                message=f"Only {len(skills)} skills listed. Consider adding more for a comprehensive CV",
                suggestion=f"Add at least {min_skills} skills to strengthen your CV",
                confidence=0.9
            ))
        
        return issues
    
    def _validate_education_consistency(
        self,
        cv_data: Dict,
        rule: ValidationRule
    ) -> List[ValidationIssue]:
        """Check education timeline consistency"""
        issues = []
        
        education = cv_data.get("education", [])
        
        # Check if education entries have years
        for idx, edu in enumerate(education):
            if isinstance(edu, dict):
                if "year" not in edu and "end_year" not in edu:
                    issues.append(ValidationIssue(
                        category=rule.category,
                        level=rule.level,
                        field=f"education[{idx}]",
                        message="Education entry missing graduation year",
                        suggestion="Add graduation year for better timeline clarity",
                        confidence=0.75
                    ))
        
        return issues
    
    def _validate_text_quality(
        self,
        cv_data: Dict,
        rule: ValidationRule
    ) -> List[ValidationIssue]:
        """Check text quality"""
        issues = []
        
        text_fields = ["professional_summary"]
        
        for field in text_fields:
            if field in cv_data:
                text = cv_data[field]
                if isinstance(text, str):
                    # Check for very short text
                    if len(text) < 50:
                        issues.append(ValidationIssue(
                            category=rule.category,
                            level=ValidationLevel.SUGGESTION,
                            field=field,
                            message=f"{field} seems too brief",
                            suggestion=f"Consider expanding {field} to provide more detail",
                            confidence=0.8
                        ))
                    
                    # Check for excessive repetition
                    words = text.lower().split()
                    if len(words) > 10:
                        word_freq = {}
                        for word in words:
                            word_freq[word] = word_freq.get(word, 0) + 1
                        
                        max_freq = max(word_freq.values())
                        if max_freq > len(words) * 0.2:  # 20% repetition
                            issues.append(ValidationIssue(
                                category=rule.category,
                                level=ValidationLevel.INFO,
                                field=field,
                                message=f"{field} contains repetitive words",
                                suggestion="Consider varying word choice for better readability",
                                confidence=0.7
                            ))
        
        return issues
    
    def _validate_data_richness(
        self,
        cv_data: Dict,
        rule: ValidationRule
    ) -> List[ValidationIssue]:
        """Assess richness and detail of data"""
        issues = []
        
        # Check if projects have detailed descriptions
        projects = cv_data.get("projects", [])
        if projects:
            for idx, project in enumerate(projects):
                if isinstance(project, dict):
                    desc = project.get("description", "")
                    if len(desc) < 100:
                        issues.append(ValidationIssue(
                            category=rule.category,
                            level=ValidationLevel.SUGGESTION,
                            field=f"projects[{idx}].description",
                            message="Project description could be more detailed",
                            suggestion="Add more details about your role, technologies used, and impact",
                            confidence=0.75
                        ))
        
        return issues
    
    def _validate_optional_fields_completeness(
        self,
        cv_data: Dict,
        rule: ValidationRule
    ) -> List[ValidationIssue]:
        """Check completeness of optional but recommended fields"""
        issues = []
        
        recommended_fields = {
            "professional_summary": "Professional summary helps recruiters understand your profile quickly",
            "certifications": "Certifications demonstrate expertise and commitment to professional development",
            "achievements": "Highlighting achievements makes your CV stand out"
        }
        
        for field, benefit in recommended_fields.items():
            if field not in cv_data or not cv_data.get(field):
                issues.append(ValidationIssue(
                    category=rule.category,
                    level=rule.level,
                    field=field,
                    message=f"Optional field '{field}' is missing",
                    suggestion=f"Consider adding {field}. {benefit}",
                    confidence=0.7
                ))
        
        return issues
    
    def _validate_cross_field_consistency(
        self,
        cv_data: Dict,
        rule: ValidationRule
    ) -> List[ValidationIssue]:
        """Check consistency across related fields"""
        issues = []
        
        # Check if experience matches project timeline
        experience = cv_data.get("total_experience")
        projects = cv_data.get("projects", [])
        
        if experience and projects:
            try:
                exp_years = float(re.findall(r'\d+\.?\d*', str(experience))[0])
                
                # Count project years (rough estimate)
                project_years = 0
                for project in projects:
                    if isinstance(project, dict):
                        duration = project.get("duration", "")
                        if duration:
                            year_matches = re.findall(r'\d+', str(duration))
                            if year_matches:
                                project_years += float(year_matches[0])
                
                # If project years significantly exceed experience, flag it
                if project_years > exp_years * 1.5:
                    issues.append(ValidationIssue(
                        category=rule.category,
                        level=rule.level,
                        field="projects",
                        message="Project timeline seems inconsistent with total experience",
                        suggestion="Review project durations and total experience for consistency",
                        confidence=0.65
                    ))
            except (IndexError, ValueError):
                pass
        
        return issues
    
    def _calculate_score(self, issues: List[ValidationIssue]) -> float:
        """Calculate overall validation score"""
        
        if not issues:
            return 1.0
        
        # Weight by severity
        weights = {
            ValidationLevel.ERROR: -0.25,
            ValidationLevel.WARNING: -0.10,
            ValidationLevel.INFO: -0.05,
            ValidationLevel.SUGGESTION: -0.02
        }
        
        total_penalty = sum(weights.get(issue.level, 0) for issue in issues)
        score = max(0.0, 1.0 + total_penalty)
        
        return score
    
    def get_validation_summary(self, result: ValidationResult) -> str:
        """Generate human-readable validation summary"""
        
        lines = [
            f"Validation Status: {'PASS' if result.is_valid else 'FAIL'}",
            f"Overall Score: {result.overall_score:.2%}",
            f"Issues: {len(result.issues)} total",
            f"  - Errors: {result.error_count}",
            f"  - Warnings: {result.warning_count}",
            ""
        ]
        
        if result.issues:
            lines.append("Issues by Category:")
            for category, cat_issues in result.by_category.items():
                lines.append(f"\n{category.value.upper()}:")
                for issue in cat_issues:
                    lines.append(f"  [{issue.level.value}] {issue.field}: {issue.message}")
                    if issue.suggestion:
                        lines.append(f"    → {issue.suggestion}")
        
        return "\n".join(lines)


class ValidationOrchestrator:
    """Orchestrate validation workflow with follow-up actions"""
    
    def __init__(self):
        self.engine = DeepValidationEngine()
    
    def validate_with_recommendations(
        self,
        cv_data: Dict[str, Any]
    ) -> Tuple[ValidationResult, List[Dict[str, Any]]]:
        """
        Validate CV and generate actionable recommendations
        """
        
        result = self.engine.validate(cv_data)
        recommendations = self._generate_recommendations(result)
        
        return result, recommendations
    
    def _generate_recommendations(
        self,
        result: ValidationResult
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations from validation issues"""
        
        recommendations = []
        
        # Group issues by field
        field_issues = {}
        for issue in result.issues:
            if issue.field not in field_issues:
                field_issues[issue.field] = []
            field_issues[issue.field].append(issue)
        
        # Generate recommendations per field
        for field, issues in field_issues.items():
            # Find highest priority issue
            priority_issue = min(issues, key=lambda i: list(ValidationLevel).index(i.level))
            
            recommendation = {
                "field": field,
                "priority": priority_issue.level.value,
                "action": priority_issue.suggestion or priority_issue.message,
                "confidence": priority_issue.confidence,
                "related_issues": len(issues)
            }
            
            recommendations.append(recommendation)
        
        # Sort by priority
        priority_order = {
            ValidationLevel.ERROR: 0,
            ValidationLevel.WARNING: 1,
            ValidationLevel.INFO: 2,
            ValidationLevel.SUGGESTION: 3
        }
        
        recommendations.sort(key=lambda r: priority_order.get(
            ValidationLevel(r["priority"]), 999
        ))
        
        return recommendations
    
    def validate_incrementally(
        self,
        cv_data: Dict[str, Any],
        previous_result: Optional[ValidationResult] = None
    ) -> Tuple[ValidationResult, List[str]]:
        """
        Validate with awareness of previous validation state
        Returns current result and list of improvements made
        """
        
        current_result = self.engine.validate(cv_data)
        
        improvements = []
        if previous_result:
            # Compare issue counts
            prev_errors = previous_result.error_count
            curr_errors = current_result.error_count
            
            if curr_errors < prev_errors:
                improvements.append(f"Fixed {prev_errors - curr_errors} error(s)")
            
            prev_warnings = previous_result.warning_count
            curr_warnings = current_result.warning_count
            
            if curr_warnings < prev_warnings:
                improvements.append(f"Resolved {prev_warnings - curr_warnings} warning(s)")
            
            # Check score improvement
            score_diff = current_result.overall_score - previous_result.overall_score
            if score_diff > 0.05:
                improvements.append(f"Score improved by {score_diff:.1%}")
        
        return current_result, improvements
