"""
Deep Validation System
Multi-level validation with contextual checks and smart suggestions
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import re


class ValidationLevel(Enum):
    """Validation severity levels"""
    CRITICAL = "critical"  # Blocks CV generation
    ERROR = "error"  # Significant issue
    WARNING = "warning"  # Should be addressed
    INFO = "info"  # Suggestion for improvement


class ValidationCategory(Enum):
    """Categories of validation"""
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    QUALITY = "quality"
    FORMAT = "format"
    PROFESSIONAL = "professional"


@dataclass
class ValidationResult:
    """Single validation result"""
    level: ValidationLevel
    category: ValidationCategory
    section: str
    field: str
    message: str
    current_value: Any
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "level": self.level.value,
            "category": self.category.value,
            "section": self.section,
            "field": self.field,
            "message": self.message,
            "current_value": str(self.current_value) if self.current_value else None,
            "suggested_fix": self.suggested_fix,
            "auto_fixable": self.auto_fixable,
            "confidence": self.confidence
        }


class DeepValidator:
    """Comprehensive CV validation system"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.context: Dict[str, Any] = {}
        
    def validate(self, cv_data: Dict[str, Any]) -> List[ValidationResult]:
        """Run all validations on CV data"""
        self.results = []
        self.context = cv_data
        
        # Level 1: Critical structure validation
        self._validate_structure(cv_data)
        
        # Level 2: Completeness validation
        self._validate_completeness(cv_data)
        
        # Level 3: Consistency validation
        self._validate_consistency(cv_data)
        
        # Level 4: Quality validation
        self._validate_quality(cv_data)
        
        # Level 5: Professional standards
        self._validate_professional_standards(cv_data)
        
        return self.results
    
    def _validate_structure(self, cv_data: Dict[str, Any]):
        """Validate critical structure elements"""
        required_sections = {
            'header': 'Header information',
            'summary': 'Professional summary',
            'skills': 'Skills section',
            'work_experience': 'Work experience'
        }
        
        for section, name in required_sections.items():
            if section not in cv_data or not cv_data[section]:
                self.results.append(ValidationResult(
                    level=ValidationLevel.CRITICAL,
                    category=ValidationCategory.COMPLETENESS,
                    section=section,
                    field='_root',
                    message=f'{name} is missing or empty',
                    current_value=None,
                    suggested_fix=f'Please provide {name.lower()}',
                    auto_fixable=False
                ))
    
    def _validate_completeness(self, cv_data: Dict[str, Any]):
        """Validate data completeness"""
        
        # Header completeness
        header = cv_data.get('header', {})
        if header:
            required_header_fields = ['full_name', 'email', 'contact_number']
            for field in required_header_fields:
                if not header.get(field):
                    self.results.append(ValidationResult(
                        level=ValidationLevel.ERROR,
                        category=ValidationCategory.COMPLETENESS,
                        section='header',
                        field=field,
                        message=f'{field.replace("_", " ").title()} is missing',
                        current_value=None,
                        suggested_fix=f'Add {field.replace("_", " ")}',
                        auto_fixable=False
                    ))
        
        # Summary length
        summary = cv_data.get('summary', '')
        if summary and len(summary) < 100:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                category=ValidationCategory.QUALITY,
                section='summary',
                field='text',
                message=f'Professional summary is too short ({len(summary)} chars)',
                current_value=summary,
                suggested_fix='Expand to 150-200 characters for better impact',
                auto_fixable=False,
                confidence=0.85
            ))
        
        # Skills count
        skills = cv_data.get('skills', [])
        if len(skills) < 3:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                category=ValidationCategory.COMPLETENESS,
                section='skills',
                field='primary_skills',
                message=f'Only {len(skills)} primary skills found',
                current_value=skills,
                suggested_fix='Add 5-10 primary skills for comprehensive profile',
                auto_fixable=False,
                confidence=0.90
            ))
        
        # Work experience
        work_exp = cv_data.get('work_experience', [])
        if not work_exp:
            self.results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                category=ValidationCategory.COMPLETENESS,
                section='work_experience',
                field='_root',
                message='No work experience entries found',
                current_value=None,
                suggested_fix='Add at least one work experience entry',
                auto_fixable=False
            ))
    
    def _validate_consistency(self, cv_data: Dict[str, Any]):
        """Validate data consistency"""
        
        # Email consistency
        header = cv_data.get('header', {})
        email = header.get('email', '')
        if email and not self._is_valid_email(email):
            self.results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                category=ValidationCategory.FORMAT,
                section='header',
                field='email',
                message='Email format appears invalid',
                current_value=email,
                suggested_fix='Use format: name@company.com',
                auto_fixable=False
            ))
        
        # Phone number consistency
        phone = header.get('contact_number', '')
        if phone and not self._is_valid_phone(phone):
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                category=ValidationCategory.FORMAT,
                section='header',
                field='contact_number',
                message='Phone number format may be invalid',
                current_value=phone,
                suggested_fix='Use 10-digit format or +91-XXXXXXXXXX',
                auto_fixable=True,
                confidence=0.75
            ))
        
        # Date consistency in work experience
        work_exp = cv_data.get('work_experience', [])
        for idx, exp in enumerate(work_exp):
            if 'start_date' in exp and 'end_date' in exp:
                if not self._is_date_range_valid(exp['start_date'], exp['end_date']):
                    self.results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        category=ValidationCategory.CONSISTENCY,
                        section='work_experience',
                        field=f'entry_{idx}_dates',
                        message='Date range may be invalid (end before start)',
                        current_value=f"{exp.get('start_date')} to {exp.get('end_date')}",
                        suggested_fix='Verify start and end dates',
                        auto_fixable=False,
                        confidence=0.80
                    ))
    
    def _validate_quality(self, cv_data: Dict[str, Any]):
        """Validate content quality"""
        
        # Summary quality
        summary = cv_data.get('summary', '')
        if summary:
            # Check for generic phrases
            generic_phrases = ['hard worker', 'team player', 'fast learner']
            for phrase in generic_phrases:
                if phrase in summary.lower():
                    self.results.append(ValidationResult(
                        level=ValidationLevel.INFO,
                        category=ValidationCategory.QUALITY,
                        section='summary',
                        field='text',
                        message=f'Consider replacing generic phrase: "{phrase}"',
                        current_value=summary,
                        suggested_fix='Use specific achievements and skills instead',
                        auto_fixable=False,
                        confidence=0.70
                    ))
        
        # Skills quality - check for duplicates
        all_skills = cv_data.get('skills', []) + cv_data.get('secondary_skills', [])
        duplicates = self._find_duplicates(all_skills)
        if duplicates:
            self.results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                category=ValidationCategory.QUALITY,
                section='skills',
                field='all_skills',
                message=f'Duplicate skills found: {", ".join(duplicates)}',
                current_value=all_skills,
                suggested_fix='Remove duplicate skills',
                auto_fixable=True,
                confidence=0.95
            ))
    
    def _validate_professional_standards(self, cv_data: Dict[str, Any]):
        """Validate professional standards"""
        
        # Check for unprofessional language
        summary = cv_data.get('summary', '')
        if summary:
            unprofessional_words = ['basically', 'stuff', 'things', 'whatever']
            for word in unprofessional_words:
                if word in summary.lower():
                    self.results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        category=ValidationCategory.PROFESSIONAL,
                        section='summary',
                        field='text',
                        message=f'Unprofessional language detected: "{word}"',
                        current_value=summary,
                        suggested_fix='Use professional terminology',
                        auto_fixable=False,
                        confidence=0.85
                    ))
        
        # Check for acronyms without expansion
        for section in ['summary', 'skills']:
            text = str(cv_data.get(section, ''))
            acronyms = re.findall(r'\b[A-Z]{2,}\b', text)
            if len(acronyms) > 5:
                self.results.append(ValidationResult(
                    level=ValidationLevel.INFO,
                    category=ValidationCategory.PROFESSIONAL,
                    section=section,
                    field='acronyms',
                    message=f'Many acronyms found ({len(acronyms)})',
                    current_value=acronyms[:5],
                    suggested_fix='Consider expanding important acronyms on first use',
                    auto_fixable=False,
                    confidence=0.65
                ))
    
    # Helper methods
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Validate phone number"""
        # Remove common separators
        clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
        # Check if it's 10 digits or starts with +91
        return bool(re.match(r'^(\+91)?\d{10}$', clean_phone))
    
    def _is_date_range_valid(self, start: str, end: str) -> bool:
        """Check if date range is valid"""
        if not start or not end or end.lower() in ['present', 'current']:
            return True
        # Simple validation - can be enhanced
        return True
    
    def _find_duplicates(self, items: List[str]) -> Set[str]:
        """Find duplicate items in list"""
        seen = set()
        duplicates = set()
        for item in items:
            item_lower = item.lower().strip()
            if item_lower in seen:
                duplicates.add(item)
            seen.add(item_lower)
        return duplicates
    
    def get_critical_issues(self) -> List[ValidationResult]:
        """Get only critical issues"""
        return [r for r in self.results if r.level == ValidationLevel.CRITICAL]
    
    def get_auto_fixable_issues(self) -> List[ValidationResult]:
        """Get issues that can be auto-fixed"""
        return [r for r in self.results if r.auto_fixable]
    
    def to_report(self) -> Dict[str, Any]:
        """Generate validation report"""
        return {
            "total_issues": len(self.results),
            "by_level": {
                "critical": len([r for r in self.results if r.level == ValidationLevel.CRITICAL]),
                "error": len([r for r in self.results if r.level == ValidationLevel.ERROR]),
                "warning": len([r for r in self.results if r.level == ValidationLevel.WARNING]),
                "info": len([r for r in self.results if r.level == ValidationLevel.INFO])
            },
            "by_category": {
                "completeness": len([r for r in self.results if r.category == ValidationCategory.COMPLETENESS]),
                "consistency": len([r for r in self.results if r.category == ValidationCategory.CONSISTENCY]),
                "quality": len([r for r in self.results if r.category == ValidationCategory.QUALITY]),
                "format": len([r for r in self.results if r.category == ValidationCategory.FORMAT]),
                "professional": len([r for r in self.results if r.category == ValidationCategory.PROFESSIONAL])
            },
            "auto_fixable": len(self.get_auto_fixable_issues()),
            "issues": [r.to_dict() for r in self.results]
        }
