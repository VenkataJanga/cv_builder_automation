"""
Enhancement Scaffolds
Provides structured scaffolding for CV enhancement with confidence scoring
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class EnhancementType(Enum):
    """Types of enhancements that can be applied"""
    GRAMMAR = "grammar"
    CLARITY = "clarity"
    PROFESSIONAL_TONE = "professional_tone"
    CONCISENESS = "conciseness"
    IMPACT = "impact"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"


class ConfidenceLevel(Enum):
    """Confidence levels for enhancements"""
    HIGH = "high"  # 80-100%
    MEDIUM = "medium"  # 50-79%
    LOW = "low"  # 0-49%


@dataclass
class EnhancementSuggestion:
    """Single enhancement suggestion"""
    type: EnhancementType
    original_text: str
    suggested_text: str
    reason: str
    confidence: float
    section: str
    requires_user_approval: bool = False
    
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level from score"""
        if self.confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW


@dataclass
class ValidationIssue:
    """Validation issue found in CV"""
    severity: str  # 'error', 'warning', 'info'
    section: str
    field: str
    message: str
    suggested_fix: Optional[str] = None
    confidence: float = 1.0


class EnhancementScaffold:
    """Main scaffold for CV enhancement"""
    
    def __init__(self):
        self.suggestions: List[EnhancementSuggestion] = []
        self.validation_issues: List[ValidationIssue] = []
        self.follow_up_questions: List[Dict[str, Any]] = []
        
    def add_suggestion(self, suggestion: EnhancementSuggestion):
        """Add enhancement suggestion"""
        self.suggestions.append(suggestion)
        
    def add_validation_issue(self, issue: ValidationIssue):
        """Add validation issue"""
        self.validation_issues.append(issue)
        
    def add_follow_up_question(self, question: Dict[str, Any]):
        """Add follow-up question"""
        self.follow_up_questions.append(question)
        
    def get_high_confidence_suggestions(self) -> List[EnhancementSuggestion]:
        """Get only high confidence suggestions"""
        return [s for s in self.suggestions if s.confidence >= 0.8]
    
    def get_critical_validation_issues(self) -> List[ValidationIssue]:
        """Get critical validation issues"""
        return [v for v in self.validation_issues if v.severity == 'error']
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "suggestions": [
                {
                    "type": s.type.value,
                    "original": s.original_text,
                    "suggested": s.suggested_text,
                    "reason": s.reason,
                    "confidence": s.confidence,
                    "confidence_level": s.confidence_level.value,
                    "section": s.section,
                    "requires_approval": s.requires_user_approval
                }
                for s in self.suggestions
            ],
            "validation_issues": [
                {
                    "severity": v.severity,
                    "section": v.section,
                    "field": v.field,
                    "message": v.message,
                    "suggested_fix": v.suggested_fix,
                    "confidence": v.confidence
                }
                for v in self.validation_issues
            ],
            "follow_up_questions": self.follow_up_questions,
            "summary": {
                "total_suggestions": len(self.suggestions),
                "high_confidence": len(self.get_high_confidence_suggestions()),
                "critical_issues": len(self.get_critical_validation_issues()),
                "follow_ups": len(self.follow_up_questions)
            }
        }


def create_scaffold_from_cv(cv_data: Dict[str, Any]) -> EnhancementScaffold:
    """Create enhancement scaffold from CV data"""
    scaffold = EnhancementScaffold()
    
    # Validate required sections
    required_sections = ['header', 'summary', 'skills', 'work_experience']
    for section in required_sections:
        if not cv_data.get(section):
            scaffold.add_validation_issue(ValidationIssue(
                severity='error',
                section=section,
                field='_root',
                message=f'Required section "{section}" is missing or empty',
                suggested_fix=f'Please provide information for {section}'
            ))
    
    # Check summary length
    summary = cv_data.get('summary', '')
    if summary and len(summary) < 50:
        scaffold.add_validation_issue(ValidationIssue(
            severity='warning',
            section='summary',
            field='text',
            message='Professional summary is too short (< 50 characters)',
            suggested_fix='Expand summary to at least 100-150 characters',
            confidence=0.9
        ))
    
    # Check for skills
    skills = cv_data.get('skills', [])
    if len(skills) < 3:
        scaffold.add_follow_up_question({
            'question': 'We found fewer than 3 primary skills. Would you like to add more?',
            'section': 'skills',
            'current_count': len(skills),
            'recommended_count': '5-10',
            'confidence': 0.85
        })
    
    return scaffold
