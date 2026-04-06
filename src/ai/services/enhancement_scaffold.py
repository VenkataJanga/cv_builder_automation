"""
Enhancement Scaffold System
Provides structured enhancement capabilities with confidence tracking
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class EnhancementType(str, Enum):
    """Types of enhancements available"""
    GRAMMAR = "grammar"
    CLARITY = "clarity"
    PROFESSIONAL_TONE = "professional_tone"
    TECHNICAL_ACCURACY = "technical_accuracy"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"


class ConfidenceLevel(str, Enum):
    """Confidence levels for extracted data"""
    HIGH = "high"  # 90-100%
    MEDIUM = "medium"  # 70-89%
    LOW = "low"  # 50-69%
    VERY_LOW = "very_low"  # <50%


class EnhancementSuggestion(BaseModel):
    """Individual enhancement suggestion"""
    field_path: str = Field(description="JSON path to the field (e.g., 'header.email')")
    enhancement_type: EnhancementType
    original_value: Any
    suggested_value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    auto_apply: bool = Field(default=False, description="Whether to auto-apply this enhancement")


class FieldConfidence(BaseModel):
    """Confidence score for a specific field"""
    field_path: str
    confidence_level: ConfidenceLevel
    confidence_score: float = Field(ge=0.0, le=1.0)
    extraction_method: str = Field(description="How this field was extracted")
    validation_status: str = Field(default="pending")
    requires_review: bool = Field(default=False)


class EnhancementScaffold(BaseModel):
    """Structured enhancement recommendations"""
    suggestions: List[EnhancementSuggestion] = Field(default_factory=list)
    field_confidences: List[FieldConfidence] = Field(default_factory=list)
    overall_quality_score: float = Field(ge=0.0, le=1.0)
    completeness_score: float = Field(ge=0.0, le=1.0)
    requires_followup: bool = Field(default=False)
    followup_questions: List[str] = Field(default_factory=list)


class EnhancementScaffoldService:
    """Service for managing enhancement scaffolds"""
    
    def __init__(self):
        self.enhancement_rules = self._load_enhancement_rules()
    
    def _load_enhancement_rules(self) -> Dict:
        """Load enhancement rules configuration"""
        return {
            "required_fields": [
                "header.full_name",
                "header.email",
                "header.contact_number",
                "skills",
                "education"
            ],
            "high_value_fields": [
                "summary",
                "project_experience",
                "work_experience",
                "certifications"
            ],
            "confidence_thresholds": {
                "auto_apply": 0.95,
                "suggest": 0.70,
                "flag_review": 0.50
            }
        }
    
    def analyze_extraction(self, extracted_data: Dict) -> EnhancementScaffold:
        """Analyze extracted data and generate enhancement scaffold"""
        scaffold = EnhancementScaffold(
            overall_quality_score=0.0,
            completeness_score=0.0
        )
        
        # Calculate field confidences
        field_confidences = self._calculate_field_confidences(extracted_data)
        scaffold.field_confidences = field_confidences
        
        # Generate enhancement suggestions
        suggestions = self._generate_enhancement_suggestions(extracted_data, field_confidences)
        scaffold.suggestions = suggestions
        
        # Calculate scores
        scaffold.completeness_score = self._calculate_completeness(extracted_data)
        scaffold.overall_quality_score = self._calculate_quality_score(field_confidences)
        
        # Determine if follow-up needed
        low_confidence_fields = [fc for fc in field_confidences if fc.confidence_score < 0.7]
        if low_confidence_fields:
            scaffold.requires_followup = True
            scaffold.followup_questions = self._generate_followup_questions(low_confidence_fields)
        
        return scaffold
    
    def _calculate_field_confidences(self, data: Dict) -> List[FieldConfidence]:
        """Calculate confidence for each extracted field"""
        confidences = []
        
        # Header fields
        header = data.get("header", {})
        for field, value in header.items():
            conf = self._assess_field_confidence(f"header.{field}", value, "header")
            confidences.append(conf)
        
        # Skills
        if data.get("skills"):
            confidences.append(FieldConfidence(
                field_path="skills",
                confidence_level=ConfidenceLevel.HIGH,
                confidence_score=0.9,
                extraction_method="structured_extraction"
            ))
        
        # Education
        if data.get("education"):
            for idx, edu in enumerate(data["education"]):
                conf = self._assess_field_confidence(
                    f"education[{idx}]",
                    edu,
                    "education"
                )
                confidences.append(conf)
        
        return confidences
    
    def _assess_field_confidence(
        self,
        field_path: str,
        value: Any,
        context: str
    ) -> FieldConfidence:
        """Assess confidence for a specific field"""
        
        # Empty values = low confidence
        if not value or (isinstance(value, str) and not value.strip()):
            return FieldConfidence(
                field_path=field_path,
                confidence_level=ConfidenceLevel.LOW,
                confidence_score=0.3,
                extraction_method="empty",
                requires_review=True
            )
        
        # Email validation
        if "email" in field_path:
            if "@" in str(value) and "." in str(value):
                return FieldConfidence(
                    field_path=field_path,
                    confidence_level=ConfidenceLevel.HIGH,
                    confidence_score=0.95,
                    extraction_method="regex_validated"
                )
            else:
                return FieldConfidence(
                    field_path=field_path,
                    confidence_level=ConfidenceLevel.LOW,
                    confidence_score=0.4,
                    extraction_method="regex_unvalidated",
                    requires_review=True
                )
        
        # Phone number validation
        if "contact" in field_path or "phone" in field_path:
            if str(value).replace(" ", "").replace("-", "").isdigit():
                return FieldConfidence(
                    field_path=field_path,
                    confidence_level=ConfidenceLevel.HIGH,
                    confidence_score=0.92,
                    extraction_method="regex_validated"
                )
        
        # Default medium confidence
        return FieldConfidence(
            field_path=field_path,
            confidence_level=ConfidenceLevel.MEDIUM,
            confidence_score=0.75,
            extraction_method="standard_extraction"
        )
    
    def _generate_enhancement_suggestions(
        self,
        data: Dict,
        confidences: List[FieldConfidence]
    ) -> List[EnhancementSuggestion]:
        """Generate enhancement suggestions based on analysis"""
        suggestions = []
        
        # Check for grammar in summary
        summary = data.get("summary", "")
        if summary and ("using" in summary or "with" in summary):
            suggestions.append(EnhancementSuggestion(
                field_path="summary",
                enhancement_type=EnhancementType.PROFESSIONAL_TONE,
                original_value=summary,
                suggested_value=self._enhance_professional_tone(summary),
                confidence=0.85,
                reasoning="Improved professional tone and clarity",
                auto_apply=False
            ))
        
        # Check email format
        email = data.get("header", {}).get("email", "")
        if email and "@" not in email:
            suggestions.append(EnhancementSuggestion(
                field_path="header.email",
                enhancement_type=EnhancementType.TECHNICAL_ACCURACY,
                original_value=email,
                suggested_value=f"{email}@nttdata.com",
                confidence=0.90,
                reasoning="Email missing domain",
                auto_apply=True
            ))
        
        return suggestions
    
    def _enhance_professional_tone(self, text: str) -> str:
        """Enhance professional tone of text"""
        # Remove casual language
        enhanced = text.replace("using", "utilizing")
        enhanced = enhanced.replace("with", "featuring")
        # Capitalize first letter
        if enhanced:
            enhanced = enhanced[0].upper() + enhanced[1:]
        return enhanced
    
    def _calculate_completeness(self, data: Dict) -> float:
        """Calculate completeness score"""
        required = self.enhancement_rules["required_fields"]
        filled = 0
        
        for field_path in required:
            parts = field_path.split(".")
            value = data
            for part in parts:
                value = value.get(part, None)
                if value is None:
                    break
            if value:
                filled += 1
        
        return filled / len(required) if required else 0.0
    
    def _calculate_quality_score(self, confidences: List[FieldConfidence]) -> float:
        """Calculate overall quality score"""
        if not confidences:
            return 0.0
        
        total = sum(fc.confidence_score for fc in confidences)
        return total / len(confidences)
    
    def _generate_followup_questions(
        self,
        low_confidence_fields: List[FieldConfidence]
    ) -> List[str]:
        """Generate follow-up questions for low confidence fields"""
        questions = []
        
        for field in low_confidence_fields:
            if "email" in field.field_path:
                questions.append("Could you please confirm your email address?")
            elif "contact" in field.field_path:
                questions.append("Could you please verify your contact number?")
            elif "education" in field.field_path:
                questions.append("Could you provide more details about your education?")
        
        return questions
    
    def apply_enhancements(
        self,
        data: Dict,
        scaffold: EnhancementScaffold,
        auto_only: bool = True
    ) -> Dict:
        """Apply enhancement suggestions to data"""
        enhanced_data = data.copy()
        
        for suggestion in scaffold.suggestions:
            if auto_only and not suggestion.auto_apply:
                continue
            
            # Apply the enhancement
            parts = suggestion.field_path.split(".")
            target = enhanced_data
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = suggestion.suggested_value
        
        return enhanced_data
