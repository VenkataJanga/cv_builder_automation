"""
Enhanced UI Signals - Frontend Communication Layer
Provides rich signals for follow-up prompts, validation, retrieval, and confidence indicators
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class SignalType(str, Enum):
    """Types of UI signals"""
    FOLLOWUP = "followup"
    VALIDATION = "validation"
    RETRIEVAL = "retrieval"
    CONFIDENCE = "confidence"
    PROGRESS = "progress"
    ERROR = "error"
    SUCCESS = "success"


class SignalSeverity(str, Enum):
    """Severity levels for signals"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ConfidenceLevel(str, Enum):
    """Confidence level categories"""
    HIGH = "high"  # >= 0.8
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"  # < 0.5


class FollowUpPromptSignal(BaseModel):
    """Signal for follow-up questions"""
    signal_type: SignalType = SignalType.FOLLOWUP
    question_id: str
    question_text: str
    question_category: str  # "basic_info", "experience", "skills", etc.
    priority: int = Field(ge=1, le=10, description="1=lowest, 10=highest")
    
    # Context
    reason: str  # Why this question is being asked
    related_field: Optional[str] = None
    current_value: Optional[str] = None
    
    # UI hints
    input_type: str = "text"  # text, multiline, select, multiselect, date
    placeholder: Optional[str] = None
    options: Optional[List[str]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    
    # Engagement
    helpful_hint: Optional[str] = None
    example_answer: Optional[str] = None
    skip_allowed: bool = True
    
    # Metadata
    estimated_time_seconds: int = 30
    confidence_impact: float = Field(ge=0, le=1, description="How much this will improve confidence")


class ValidationSignal(BaseModel):
    """Signal for validation issues"""
    signal_type: SignalType = SignalType.VALIDATION
    issue_id: str
    field_name: str
    severity: SignalSeverity
    
    # Issue details
    message: str
    detailed_explanation: Optional[str] = None
    current_value: Any = None
    expected_format: Optional[str] = None
    
    # Suggestions
    suggestions: List[str] = Field(default_factory=list)
    auto_fix_available: bool = False
    auto_fix_preview: Optional[str] = None
    
    # UI hints
    highlight_location: Optional[str] = None  # CSS selector or field path
    show_inline: bool = True
    dismissible: bool = False
    
    # Actions
    action_buttons: List[Dict[str, str]] = Field(default_factory=list)
    # e.g., [{"label": "Fix automatically", "action": "auto_fix"}, {"label": "Edit manually", "action": "edit"}]


class RetrievalRecommendationSignal(BaseModel):
    """Signal for retrieval/template recommendations"""
    signal_type: SignalType = SignalType.RETRIEVAL
    recommendation_id: str
    
    # Recommendation details
    title: str
    description: str
    relevance_score: float = Field(ge=0, le=1)
    source: str  # "template", "example", "best_practice"
    
    # Content
    content_preview: str
    full_content: Optional[str] = None
    content_type: str = "text"  # text, bullet_points, template
    
    # Application
    target_field: Optional[str] = None
    apply_action: Optional[str] = None  # "replace", "append", "merge"
    
    # UI hints
    show_as: str = "card"  # card, inline, sidebar
    icon: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    # Interaction
    accept_button_text: str = "Use this"
    reject_button_text: str = "Dismiss"
    edit_before_apply: bool = True


class ConfidenceIndicatorSignal(BaseModel):
    """Signal for confidence indicators"""
    signal_type: SignalType = SignalType.CONFIDENCE
    field_name: str
    confidence_score: float = Field(ge=0, le=1)
    confidence_level: ConfidenceLevel
    
    # Context
    extraction_method: str  # "llm", "rule_based", "hybrid"
    data_source: str  # "user_input", "document", "inferred"
    
    # Explanation
    confidence_factors: List[Dict[str, Any]] = Field(default_factory=list)
    # e.g., [{"factor": "Direct mention", "impact": 0.3}, {"factor": "Consistent format", "impact": 0.2}]
    
    # Improvement suggestions
    how_to_improve: Optional[str] = None
    related_followup_questions: List[str] = Field(default_factory=list)
    
    # UI hints
    show_indicator: bool = True
    indicator_position: str = "inline"  # inline, tooltip, badge
    color_code: str = "auto"  # auto, green, yellow, red
    
    # Details
    show_details_link: bool = True
    confidence_breakdown: Optional[Dict[str, float]] = None


class ProgressSignal(BaseModel):
    """Signal for progress indication"""
    signal_type: SignalType = SignalType.PROGRESS
    stage: str
    stage_name: str
    
    # Progress
    current_step: int
    total_steps: int
    percentage_complete: float = Field(ge=0, le=100)
    
    # Status
    status: str = "in_progress"  # in_progress, completed, error
    status_message: str
    
    # Timing
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    estimated_completion: Optional[str] = None
    estimated_remaining_seconds: Optional[int] = None
    
    # Details
    substeps: List[Dict[str, Any]] = Field(default_factory=list)
    current_substep: Optional[str] = None
    
    # UI hints
    show_percentage: bool = True
    show_spinner: bool = True
    allow_cancel: bool = False


class UISignalManager:
    """Manager for creating and organizing UI signals"""
    
    def __init__(self):
        self.signals: List[BaseModel] = []
    
    def create_followup_prompt(
        self,
        question_id: str,
        question_text: str,
        category: str,
        priority: int,
        reason: str,
        **kwargs
    ) -> FollowUpPromptSignal:
        """Create a follow-up prompt signal"""
        
        signal = FollowUpPromptSignal(
            question_id=question_id,
            question_text=question_text,
            question_category=category,
            priority=priority,
            reason=reason,
            **kwargs
        )
        
        self.signals.append(signal)
        return signal
    
    def create_validation_issue(
        self,
        issue_id: str,
        field_name: str,
        severity: SignalSeverity,
        message: str,
        **kwargs
    ) -> ValidationSignal:
        """Create a validation issue signal"""
        
        signal = ValidationSignal(
            issue_id=issue_id,
            field_name=field_name,
            severity=severity,
            message=message,
            **kwargs
        )
        
        self.signals.append(signal)
        return signal
    
    def create_retrieval_recommendation(
        self,
        recommendation_id: str,
        title: str,
        description: str,
        content_preview: str,
        relevance_score: float,
        source: str,
        **kwargs
    ) -> RetrievalRecommendationSignal:
        """Create a retrieval recommendation signal"""
        
        signal = RetrievalRecommendationSignal(
            recommendation_id=recommendation_id,
            title=title,
            description=description,
            content_preview=content_preview,
            relevance_score=relevance_score,
            source=source,
            **kwargs
        )
        
        self.signals.append(signal)
        return signal
    
    def create_confidence_indicator(
        self,
        field_name: str,
        confidence_score: float,
        **kwargs
    ) -> ConfidenceIndicatorSignal:
        """Create a confidence indicator signal"""
        
        # Determine confidence level
        if confidence_score >= 0.8:
            confidence_level = ConfidenceLevel.HIGH
        elif confidence_score >= 0.5:
            confidence_level = ConfidenceLevel.MEDIUM
        else:
            confidence_level = ConfidenceLevel.LOW
        
        signal = ConfidenceIndicatorSignal(
            field_name=field_name,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            **kwargs
        )
        
        self.signals.append(signal)
        return signal
    
    def create_progress_signal(
        self,
        stage: str,
        stage_name: str,
        current_step: int,
        total_steps: int,
        status_message: str,
        **kwargs
    ) -> ProgressSignal:
        """Create a progress signal"""
        
        percentage = (current_step / total_steps * 100) if total_steps > 0 else 0
        
        signal = ProgressSignal(
            stage=stage,
            stage_name=stage_name,
            current_step=current_step,
            total_steps=total_steps,
            percentage_complete=percentage,
            status_message=status_message,
            **kwargs
        )
        
        self.signals.append(signal)
        return signal
    
    def get_signals_by_type(self, signal_type: SignalType) -> List[BaseModel]:
        """Get all signals of a specific type"""
        return [s for s in self.signals if s.signal_type == signal_type]
    
    def get_high_priority_followups(self, limit: int = 5) -> List[FollowUpPromptSignal]:
        """Get high priority follow-up questions"""
        followups = self.get_signals_by_type(SignalType.FOLLOWUP)
        return sorted(followups, key=lambda x: x.priority, reverse=True)[:limit]
    
    def get_critical_validations(self) -> List[ValidationSignal]:
        """Get critical validation issues"""
        validations = self.get_signals_by_type(SignalType.VALIDATION)
        return [v for v in validations if v.severity == SignalSeverity.CRITICAL]
    
    def get_low_confidence_fields(self, threshold: float = 0.5) -> List[ConfidenceIndicatorSignal]:
        """Get fields with low confidence"""
        confidence_signals = self.get_signals_by_type(SignalType.CONFIDENCE)
        return [c for c in confidence_signals if c.confidence_score < threshold]
    
    def export_for_ui(self) -> Dict[str, Any]:
        """Export all signals in UI-friendly format"""
        
        return {
            "followup_prompts": [s.dict() for s in self.get_signals_by_type(SignalType.FOLLOWUP)],
            "validation_issues": [s.dict() for s in self.get_signals_by_type(SignalType.VALIDATION)],
            "retrieval_recommendations": [s.dict() for s in self.get_signals_by_type(SignalType.RETRIEVAL)],
            "confidence_indicators": [s.dict() for s in self.get_signals_by_type(SignalType.CONFIDENCE)],
            "progress": [s.dict() for s in self.get_signals_by_type(SignalType.PROGRESS)],
            "summary": {
                "total_followups": len(self.get_signals_by_type(SignalType.FOLLOWUP)),
                "critical_validations": len(self.get_critical_validations()),
                "low_confidence_fields": len(self.get_low_confidence_fields()),
                "recommendations_available": len(self.get_signals_by_type(SignalType.RETRIEVAL))
            }
        }
    
    def clear_signals(self, signal_type: Optional[SignalType] = None):
        """Clear signals of a specific type or all signals"""
        if signal_type:
            self.signals = [s for s in self.signals if s.signal_type != signal_type]
        else:
            self.signals = []


class SignalGenerator:
    """Utility class for generating common signal patterns"""
    
    @staticmethod
    def generate_from_extraction_result(
        extraction_result: Dict[str, Any],
        manager: UISignalManager
    ):
        """Generate signals from extraction results"""
        
        extracted_data = extraction_result.get("extracted_data", {})
        field_confidence = extraction_result.get("field_confidence", {})
        
        # Generate confidence indicators for all fields
        for field, value in extracted_data.items():
            confidence = field_confidence.get(field, 0.5)
            
            manager.create_confidence_indicator(
                field_name=field,
                confidence_score=confidence,
                extraction_method=extraction_result.get("method", "hybrid"),
                data_source="extraction",
                confidence_factors=[
                    {"factor": "Extraction confidence", "impact": confidence}
                ]
            )
            
            # Generate follow-up for low confidence fields
            if confidence < 0.6:
                manager.create_followup_prompt(
                    question_id=f"verify_{field}",
                    question_text=f"Can you verify or provide more details about: {field}?",
                    category="verification",
                    priority=8 if confidence < 0.4 else 5,
                    reason=f"Low confidence ({confidence:.0%}) in extracted value",
                    related_field=field,
                    current_value=str(value),
                    confidence_impact=0.4
                )
    
    @staticmethod
    def generate_from_validation_result(
        validation_result: Dict[str, Any],
        manager: UISignalManager
    ):
        """Generate signals from validation results"""
        
        issues = validation_result.get("issues", [])
        
        for issue in issues:
            severity_map = {
                "critical": SignalSeverity.CRITICAL,
                "error": SignalSeverity.ERROR,
                "warning": SignalSeverity.WARNING,
                "info": SignalSeverity.INFO
            }
            
            manager.create_validation_issue(
                issue_id=issue.get("issue_id", str(uuid.uuid4())),
                field_name=issue.get("field"),
                severity=severity_map.get(issue.get("severity"), SignalSeverity.WARNING),
                message=issue.get("message"),
                detailed_explanation=issue.get("explanation"),
                suggestions=issue.get("suggestions", []),
                auto_fix_available=issue.get("fixable", False)
            )
    
    @staticmethod
    def generate_from_retrieval_result(
        retrieval_result: Dict[str, Any],
        manager: UISignalManager
    ):
        """Generate signals from retrieval results"""
        
        results = retrieval_result.get("results", [])
        
        for idx, result in enumerate(results[:5]):  # Top 5 results
            manager.create_retrieval_recommendation(
                recommendation_id=f"retrieval_{idx}",
                title=result.get("title", f"Recommendation {idx + 1}"),
                description=result.get("description", ""),
                content_preview=result.get("content", "")[:200],
                full_content=result.get("content"),
                relevance_score=result.get("score", 0.5),
                source=result.get("source", "template"),
                target_field=result.get("target_field"),
                tags=result.get("tags", [])
            )
