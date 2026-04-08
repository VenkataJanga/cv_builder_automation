"""
NTT DATA CV Template Rules and Validation

This module defines template-specific rules, constraints, and validation logic
for the standard NTT DATA CV template.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SectionType(Enum):
    """Types of CV sections"""
    MANDATORY = "mandatory"
    OPTIONAL = "optional"
    CONDITIONAL = "conditional"


class ValidationLevel(Enum):
    """Validation severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a validation check"""
    level: ValidationLevel
    section: str
    field: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class SectionRule:
    """Rules for a CV section"""
    name: str
    type: SectionType
    required_fields: List[str]
    optional_fields: List[str]
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    format_rules: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[str]] = None


class NTTDataTemplateRules:
    """NTT DATA template validation and formatting rules"""
    
    def __init__(self):
        self.rules = self._define_rules()
        self.formatting_constraints = self._define_formatting_constraints()
        self.client_constraints = self._define_client_constraints()
    
    def _define_rules(self) -> Dict[str, SectionRule]:
        """Define section-specific rules for NTT DATA template"""
        return {
            # Personal Information - Always required
            "personal_info": SectionRule(
                name="Personal Information",
                type=SectionType.MANDATORY,
                required_fields=["full_name", "employee_id", "email"],
                optional_fields=[
                    "contact_number", "current_title", "grade", 
                    "location", "organization", "experience", "target_role"
                ],
                min_length=3,  # At least 3 required fields must be filled
            ),
            
            # Professional Summary - Highly recommended
            "summary": SectionRule(
                name="Professional Summary",
                type=SectionType.MANDATORY,
                required_fields=["summary"],
                optional_fields=[],
                min_length=100,  # Minimum character count
                max_length=500,  # Maximum character count
            ),
            
            # Skills - Required for technical roles
            "skills": SectionRule(
                name="Skills",
                type=SectionType.MANDATORY,
                required_fields=["skills"],
                optional_fields=[
                    "secondary_skills", "tools_and_platforms", 
                    "ai_frameworks", "cloud_platforms", "operating_systems",
                    "databases", "domain_expertise"
                ],
                min_length=3,  # At least 3 skills
            ),
            
            # Work Experience - Critical for experienced professionals
            "work_experience": SectionRule(
                name="Work Experience",
                type=SectionType.CONDITIONAL,
                required_fields=["work_experience"],
                optional_fields=[],
                dependencies=["experience"],  # Required if experience > 0
                format_rules={
                    "required_subfields": ["title", "company", "duration"],
                    "optional_subfields": ["responsibilities", "achievements"]
                }
            ),
            
            # Project Experience - Important for technical roles
            "project_experience": SectionRule(
                name="Project Experience",
                type=SectionType.CONDITIONAL,
                required_fields=["project_experience"],
                optional_fields=[],
                format_rules={
                    "required_subfields": ["project_name", "role"],
                    "optional_subfields": [
                        "client", "duration", "project_description", 
                        "technologies_used", "responsibilities"
                    ]
                }
            ),
            
            # Education - Always required
            "education": SectionRule(
                name="Education",
                type=SectionType.MANDATORY,
                required_fields=["education"],
                optional_fields=[],
                format_rules={
                    "required_subfields": ["qualification"],
                    "optional_subfields": [
                        "specialization", "college", "university", 
                        "year_of_passing", "percentage"
                    ]
                }
            ),
            
            # Certifications - Recommended for technical roles
            "certifications": SectionRule(
                name="Certifications",
                type=SectionType.OPTIONAL,
                required_fields=[],
                optional_fields=["certifications"],
                format_rules={
                    "required_subfields": ["name"],
                    "optional_subfields": ["issuer", "year", "expiry"]
                }
            ),
            
            # Languages - Optional but valuable
            "languages": SectionRule(
                name="Languages",
                type=SectionType.OPTIONAL,
                required_fields=[],
                optional_fields=["languages"],
                format_rules={
                    "required_subfields": ["name"],
                    "optional_subfields": ["proficiency"]
                }
            ),
            
            # Awards - Optional
            "awards": SectionRule(
                name="Awards & Recognition",
                type=SectionType.OPTIONAL,
                required_fields=[],
                optional_fields=["awards"],
            ),
            
            # Publications - Optional for research roles
            "publications": SectionRule(
                name="Publications",
                type=SectionType.OPTIONAL,
                required_fields=[],
                optional_fields=["publications"],
            ),
            
            # Leadership - Important for senior roles
            "leadership": SectionRule(
                name="Leadership & Impact",
                type=SectionType.CONDITIONAL,
                required_fields=[],
                optional_fields=["leadership_lines"],
                dependencies=["grade", "experience"],  # Required for senior grades
            ),
        }
    
    def _define_formatting_constraints(self) -> Dict[str, Any]:
        """Define formatting constraints for the template"""
        return {
            # Text length constraints
            "max_summary_length": 500,
            "max_responsibility_length": 200,
            "max_project_description_length": 300,
            
            # List size constraints
            "max_skills_count": 15,
            "max_certifications_count": 10,
            "max_languages_count": 5,
            "max_work_experiences": 5,
            "max_projects": 8,
            
            # Field format constraints
            "email_pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "employee_id_pattern": r"^[A-Z0-9]{6,10}$",
            "phone_pattern": r"^\+?[\d\s\-\(\)]{10,15}$",
            
            # Date format constraints
            "date_formats": ["%Y", "%m/%Y", "%B %Y", "%Y-%m-%d"],
            
            # Experience format constraints
            "experience_pattern": r"^\d+(\.\d+)?\s*(year|yr|years|yrs|month|months|mo)s?$",
        }
    
    def _define_client_constraints(self) -> Dict[str, Any]:
        """Define client-specific constraints (for future expansion)"""
        return {
            # NTT DATA specific requirements
            "mandatory_branding": True,
            "required_sections": [
                "personal_info", "summary", "skills", "education"
            ],
            
            # Grade-based requirements
            "grade_requirements": {
                "A1": ["leadership", "certifications"],
                "A2": ["leadership", "certifications"],
                "B1": ["certifications"],
                "B2": ["certifications"],
                "C1": [],
                "C2": [],
            },
            
            # Role-based requirements
            "role_requirements": {
                "technical": ["skills", "certifications", "project_experience"],
                "managerial": ["leadership", "work_experience"],
                "consultant": ["project_experience", "certifications"],
            },
            
            # Content guidelines
            "content_guidelines": {
                "use_action_verbs": True,
                "quantify_achievements": True,
                "avoid_personal_pronouns": True,
                "use_professional_tone": True,
            }
        }
    
    def validate_cv_data(self, cv_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate CV data against NTT DATA template rules"""
        results = []
        
        # Validate each section
        for section_key, rule in self.rules.items():
            section_results = self._validate_section(section_key, rule, cv_data)
            results.extend(section_results)
        
        # Cross-section validations
        cross_validation_results = self._validate_cross_sections(cv_data)
        results.extend(cross_validation_results)
        
        # Format validations
        format_results = self._validate_formatting(cv_data)
        results.extend(format_results)
        
        return results
    
    def _validate_section(self, section_key: str, rule: SectionRule, 
                         cv_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate a specific section"""
        results = []
        
        # Check section type requirements
        if rule.type == SectionType.MANDATORY:
            if not any(cv_data.get(field) for field in rule.required_fields):
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    section=rule.name,
                    field=section_key,
                    message=f"Mandatory section '{rule.name}' is missing or empty",
                    suggestion="Please provide the required information for this section"
                ))
        
        elif rule.type == SectionType.CONDITIONAL:
            if rule.dependencies:
                should_be_present = self._check_dependencies(rule.dependencies, cv_data)
                if should_be_present and not any(cv_data.get(field) for field in rule.required_fields):
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        section=rule.name,
                        field=section_key,
                        message=f"Section '{rule.name}' is recommended based on your profile",
                        suggestion="Consider adding this section to strengthen your CV"
                    ))
        
        # Check required fields within section
        for field in rule.required_fields:
            field_data = cv_data.get(field)
            if not field_data:
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    section=rule.name,
                    field=field,
                    message=f"Required field '{field}' is missing",
                    suggestion=f"Please provide a value for {field}"
                ))
        
        # Check length constraints
        if rule.min_length or rule.max_length:
            results.extend(self._validate_length_constraints(rule, cv_data))
        
        # Check format rules
        if rule.format_rules:
            results.extend(self._validate_format_rules(rule, cv_data))
        
        return results
    
    def _check_dependencies(self, dependencies: List[str], cv_data: Dict[str, Any]) -> bool:
        """Check if dependencies are met for conditional sections"""
        for dep in dependencies:
            if dep == "experience":
                # Check if experience indicates need for work experience
                exp_str = cv_data.get("experience", "")
                if exp_str and any(char.isdigit() for char in str(exp_str)):
                    return True
            elif dep == "grade":
                # Check if grade indicates senior position
                grade = cv_data.get("grade", "")
                if grade and grade.upper() in ["A1", "A2", "B1"]:
                    return True
            elif cv_data.get(dep):
                return True
        return False
    
    def _validate_length_constraints(self, rule: SectionRule, 
                                   cv_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate length constraints for sections"""
        results = []
        
        for field in rule.required_fields:
            field_data = cv_data.get(field)
            if field_data:
                if isinstance(field_data, str):
                    length = len(field_data)
                elif isinstance(field_data, list):
                    length = len(field_data)
                else:
                    continue
                
                if rule.min_length and length < rule.min_length:
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        section=rule.name,
                        field=field,
                        message=f"Field '{field}' is too short (minimum: {rule.min_length})",
                        suggestion="Please provide more detailed information"
                    ))
                
                if rule.max_length and length > rule.max_length:
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        section=rule.name,
                        field=field,
                        message=f"Field '{field}' is too long (maximum: {rule.max_length})",
                        suggestion="Please condense the information"
                    ))
        
        return results
    
    def _validate_format_rules(self, rule: SectionRule, 
                             cv_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate format-specific rules"""
        results = []
        
        if not rule.format_rules:
            return results
        
        for field in rule.required_fields:
            field_data = cv_data.get(field)
            if field_data and isinstance(field_data, list):
                for item in field_data:
                    if isinstance(item, dict):
                        # Validate required subfields
                        required_subfields = rule.format_rules.get("required_subfields", [])
                        for subfield in required_subfields:
                            if not item.get(subfield):
                                results.append(ValidationResult(
                                    level=ValidationLevel.ERROR,
                                    section=rule.name,
                                    field=f"{field}.{subfield}",
                                    message=f"Required subfield '{subfield}' is missing",
                                    suggestion=f"Please provide {subfield} information"
                                ))
        
        return results
    
    def _validate_cross_sections(self, cv_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate relationships between sections"""
        results = []
        
        # Check grade-based requirements
        grade = cv_data.get("grade", "")
        if grade and grade.upper() in self.client_constraints["grade_requirements"]:
            required_sections = self.client_constraints["grade_requirements"][grade.upper()]
            for section in required_sections:
                if not cv_data.get(section):
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        section="Cross-validation",
                        field=section,
                        message=f"Section '{section}' is recommended for grade {grade}",
                        suggestion=f"Consider adding {section} information"
                    ))
        
        # Check experience consistency
        total_exp = cv_data.get("experience", "")
        work_exp = cv_data.get("work_experience", [])
        if total_exp and work_exp:
            # Could add logic to verify experience consistency
            pass
        
        return results
    
    def _validate_formatting(self, cv_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate formatting constraints"""
        results = []
        
        # Validate email format
        email = cv_data.get("email", "")
        if email:
            import re
            if not re.match(self.formatting_constraints["email_pattern"], email):
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    section="Personal Information",
                    field="email",
                    message="Email format is invalid",
                    suggestion="Please provide a valid email address"
                ))
        
        # Validate employee ID format
        emp_id = cv_data.get("employee_id", "")
        if emp_id:
            if not re.match(self.formatting_constraints["employee_id_pattern"], emp_id):
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    section="Personal Information",
                    field="employee_id",
                    message="Employee ID format may be incorrect",
                    suggestion="Employee ID should be 6-10 alphanumeric characters"
                ))
        
        # Validate phone format
        phone = cv_data.get("contact_number", "")
        if phone:
            if not re.match(self.formatting_constraints["phone_pattern"], phone):
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    section="Personal Information",
                    field="contact_number",
                    message="Phone number format may be incorrect",
                    suggestion="Please use a standard phone number format"
                ))
        
        return results
    
    def get_completion_score(self, cv_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Calculate CV completion score and provide recommendations"""
        total_sections = len(self.rules)
        completed_sections = 0
        section_scores = {}
        
        for section_key, rule in self.rules.items():
            if rule.type == SectionType.MANDATORY:
                weight = 2.0
            elif rule.type == SectionType.CONDITIONAL:
                weight = 1.5
            else:  # OPTIONAL
                weight = 1.0
            
            # Check if section has data
            has_data = any(cv_data.get(field) for field in rule.required_fields + rule.optional_fields)
            
            if has_data:
                completed_sections += weight
                section_scores[section_key] = {
                    "completed": True,
                    "weight": weight,
                    "score": weight
                }
            else:
                section_scores[section_key] = {
                    "completed": False,
                    "weight": weight,
                    "score": 0
                }
        
        # Calculate weighted completion score
        max_possible_score = sum(
            2.0 if rule.type == SectionType.MANDATORY else
            1.5 if rule.type == SectionType.CONDITIONAL else 1.0
            for rule in self.rules.values()
        )
        
        completion_score = (completed_sections / max_possible_score) * 100
        
        # Generate recommendations
        recommendations = self._generate_recommendations(cv_data, section_scores)
        
        return completion_score, {
            "score": completion_score,
            "section_scores": section_scores,
            "recommendations": recommendations,
            "validation_results": self.validate_cv_data(cv_data)
        }
    
    def _generate_recommendations(self, cv_data: Dict[str, Any], 
                                 section_scores: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # Check for missing mandatory sections
        for section_key, rule in self.rules.items():
            if rule.type == SectionType.MANDATORY and not section_scores[section_key]["completed"]:
                recommendations.append(
                    f"Complete the '{rule.name}' section - this is mandatory for NTT DATA CVs"
                )
        
        # Check for missing conditional sections
        for section_key, rule in self.rules.items():
            if (rule.type == SectionType.CONDITIONAL and 
                not section_scores[section_key]["completed"] and
                rule.dependencies):
                
                should_be_present = self._check_dependencies(rule.dependencies, cv_data)
                if should_be_present:
                    recommendations.append(
                        f"Add '{rule.name}' section - recommended based on your profile"
                    )
        
        # Grade-specific recommendations
        grade = cv_data.get("grade", "")
        if grade and grade.upper() in self.client_constraints["grade_requirements"]:
            required_sections = self.client_constraints["grade_requirements"][grade.upper()]
            for section in required_sections:
                if section not in cv_data or not cv_data[section]:
                    recommendations.append(
                        f"Add {section} information - recommended for your grade level"
                    )
        
        # Quality recommendations
        if len(recommendations) == 0:
            recommendations.extend([
                "Consider quantifying achievements with specific metrics",
                "Use action verbs to describe responsibilities and accomplishments",
                "Keep descriptions concise and professional",
                "Ensure all dates and durations are consistent and accurate"
            ])
        
        return recommendations[:5]  # Limit to top 5 recommendations


# Utility functions for template integration
def validate_ntt_template(cv_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to validate CV data against NTT DATA template rules"""
    rules_engine = NTTDataTemplateRules()
    return rules_engine.get_completion_score(cv_data)


def get_template_requirements() -> Dict[str, Any]:
    """Get template requirements and constraints"""
    rules_engine = NTTDataTemplateRules()
    return {
        "mandatory_sections": [
            name for key, rule in rules_engine.rules.items() 
            if rule.type == SectionType.MANDATORY
        ],
        "conditional_sections": [
            name for key, rule in rules_engine.rules.items() 
            if rule.type == SectionType.CONDITIONAL
        ],
        "optional_sections": [
            name for key, rule in rules_engine.rules.items() 
            if rule.type == SectionType.OPTIONAL
        ],
        "formatting_constraints": rules_engine.formatting_constraints,
        "client_constraints": rules_engine.client_constraints
    }
