"""
UI Signals and Feedback System
Rich UI feedback for follow-up prompts, validation, retrieval, and confidence indicators
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Types of UI signals"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    RECOMMENDATION = "recommendation"


class ConfidenceLevel(Enum):
    """Confidence levels for extracted data"""
    HIGH = "high"  # >= 0.8
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"  # < 0.5
    
    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        """Convert score to confidence level"""
        if score >= 0.8:
            return cls.HIGH
        elif score >= 0.5:
            return cls.MEDIUM
        else:
            return cls.LOW


@dataclass
class UISignal:
    """Base UI signal"""
    signal_type: SignalType
    message: str
    title: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    action_required: bool = False
    dismissible: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "type": self.signal_type.value,
            "message": self.message,
            "title": self.title,
            "details": self.details,
            "action_required": self.action_required,
            "dismissible": self.dismissible
        }


@dataclass
class FollowUpPrompt:
    """Follow-up question prompt for UI"""
    question_id: str
    question_text: str
    priority: str  # "critical", "high", "medium", "low"
    section: str  # CV section this relates to
    field: Optional[str] = None
    current_value: Optional[Any] = None
    suggested_values: List[str] = field(default_factory=list)
    input_type: str = "text"  # "text", "textarea", "select", "multiselect"
    placeholder: Optional[str] = None
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    help_text: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "id": self.question_id,
            "question": self.question_text,
            "priority": self.priority,
            "section": self.section,
            "field": self.field,
            "current_value": self.current_value,
            "suggested_values": self.suggested_values,
            "input_type": self.input_type,
            "placeholder": self.placeholder,
            "validation_rules": self.validation_rules,
            "help_text": self.help_text
        }


@dataclass
class ValidationFeedback:
    """Validation feedback for UI"""
    field_path: str  # e.g., "header.name", "experience.0.company"
    level: str  # "critical", "warning", "info"
    message: str
    suggestion: Optional[str] = None
    can_auto_fix: bool = False
    auto_fix_preview: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "field_path": self.field_path,
            "level": self.level,
            "message": self.message,
            "suggestion": self.suggestion,
            "can_auto_fix": self.can_auto_fix,
            "auto_fix_preview": self.auto_fix_preview
        }


@dataclass
class RetrievalRecommendation:
    """Retrieval-based recommendation for UI"""
    recommendation_id: str
    title: str
    description: str
    source: str  # "example_cv", "best_practice", "template"
    relevance_score: float
    section: Optional[str] = None
    content_preview: Optional[str] = None
    apply_action: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "id": self.recommendation_id,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "relevance_score": round(self.relevance_score, 3),
            "section": self.section,
            "content_preview": self.content_preview,
            "apply_action": self.apply_action
        }


@dataclass
class ConfidenceIndicator:
    """Confidence indicator for extracted data"""
    field_path: str
    confidence_level: ConfidenceLevel
    confidence_score: float
    extraction_method: str
    needs_review: bool = False
    supporting_evidence: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "field_path": self.field_path,
            "confidence_level": self.confidence_level.value,
            "confidence_score": round(self.confidence_score, 3),
            "extraction_method": self.extraction_method,
            "needs_review": self.needs_review,
            "supporting_evidence": self.supporting_evidence
        }


@dataclass
class WorkflowProgress:
    """Workflow progress indicator"""
    current_step: str
    total_steps: int
    completed_steps: int
    step_details: Dict[str, Any] = field(default_factory=dict)
    estimated_time_remaining: Optional[float] = None
    
    @property
    def progress_percentage(self) -> int:
        """Calculate progress percentage"""
        if self.total_steps == 0:
            return 0
        return int((self.completed_steps / self.total_steps) * 100)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "progress_percentage": self.progress_percentage,
            "step_details": self.step_details,
            "estimated_time_remaining": self.estimated_time_remaining
        }


class UISignalManager:
    """Manage UI signals and feedback"""
    
    def __init__(self):
        self.signals: List[UISignal] = []
        self.followup_prompts: List[FollowUpPrompt] = []
        self.validation_feedback: List[ValidationFeedback] = []
        self.recommendations: List[RetrievalRecommendation] = []
        self.confidence_indicators: Dict[str, ConfidenceIndicator] = {}
        self.workflow_progress: Optional[WorkflowProgress] = None
    
    def add_signal(
        self,
        signal_type: SignalType,
        message: str,
        title: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        action_required: bool = False
    ):
        """Add a UI signal"""
        signal = UISignal(
            signal_type=signal_type,
            message=message,
            title=title,
            details=details,
            action_required=action_required
        )
        self.signals.append(signal)
        logger.debug(f"Added UI signal: {signal_type.value} - {message}")
    
    def add_followup_prompt(
        self,
        question_id: str,
        question_text: str,
        priority: str,
        section: str,
        **kwargs
    ):
        """Add a follow-up prompt"""
        prompt = FollowUpPrompt(
            question_id=question_id,
            question_text=question_text,
            priority=priority,
            section=section,
            **kwargs
        )
        self.followup_prompts.append(prompt)
        logger.debug(f"Added follow-up prompt: {question_id}")
    
    def add_validation_feedback(
        self,
        field_path: str,
        level: str,
        message: str,
        **kwargs
    ):
        """Add validation feedback"""
        feedback = ValidationFeedback(
            field_path=field_path,
            level=level,
            message=message,
            **kwargs
        )
        self.validation_feedback.append(feedback)
        logger.debug(f"Added validation feedback: {field_path} - {level}")
    
    def add_recommendation(
        self,
        recommendation_id: str,
        title: str,
        description: str,
        source: str,
        relevance_score: float,
        **kwargs
    ):
        """Add retrieval recommendation"""
        recommendation = RetrievalRecommendation(
            recommendation_id=recommendation_id,
            title=title,
            description=description,
            source=source,
            relevance_score=relevance_score,
            **kwargs
        )
        self.recommendations.append(recommendation)
        logger.debug(f"Added recommendation: {recommendation_id}")
    
    def set_confidence_indicator(
        self,
        field_path: str,
        confidence_score: float,
        extraction_method: str,
        **kwargs
    ):
        """Set confidence indicator for a field"""
        confidence_level = ConfidenceLevel.from_score(confidence_score)
        indicator = ConfidenceIndicator(
            field_path=field_path,
            confidence_level=confidence_level,
            confidence_score=confidence_score,
            extraction_method=extraction_method,
            needs_review=confidence_level != ConfidenceLevel.HIGH,
            **kwargs
        )
        self.confidence_indicators[field_path] = indicator
        logger.debug(f"Set confidence indicator: {field_path} - {confidence_level.value}")
    
    def update_workflow_progress(
        self,
        current_step: str,
        completed_steps: int,
        total_steps: int,
        **kwargs
    ):
        """Update workflow progress"""
        self.workflow_progress = WorkflowProgress(
            current_step=current_step,
            completed_steps=completed_steps,
            total_steps=total_steps,
            **kwargs
        )
        logger.debug(f"Updated workflow progress: {completed_steps}/{total_steps}")
    
    def get_critical_prompts(self) -> List[FollowUpPrompt]:
        """Get critical follow-up prompts"""
        return [p for p in self.followup_prompts if p.priority == "critical"]
    
    def get_critical_validation_issues(self) -> List[ValidationFeedback]:
        """Get critical validation issues"""
        return [v for v in self.validation_feedback if v.level == "critical"]
    
    def get_low_confidence_fields(self) -> List[ConfidenceIndicator]:
        """Get fields with low confidence"""
        return [
            ind for ind in self.confidence_indicators.values()
            if ind.confidence_level == ConfidenceLevel.LOW
        ]
    
    def get_top_recommendations(self, limit: int = 5) -> List[RetrievalRecommendation]:
        """Get top recommendations by relevance"""
        sorted_recs = sorted(
            self.recommendations,
            key=lambda r: r.relevance_score,
            reverse=True
        )
        return sorted_recs[:limit]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all signals to dictionary for API response"""
        return {
            "signals": [s.to_dict() for s in self.signals],
            "followup_prompts": [p.to_dict() for p in self.followup_prompts],
            "validation_feedback": [v.to_dict() for v in self.validation_feedback],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "confidence_indicators": {
                path: ind.to_dict() 
                for path, ind in self.confidence_indicators.items()
            },
            "workflow_progress": self.workflow_progress.to_dict() if self.workflow_progress else None,
            "summary": {
                "total_signals": len(self.signals),
                "critical_prompts": len(self.get_critical_prompts()),
                "critical_issues": len(self.get_critical_validation_issues()),
                "low_confidence_fields": len(self.get_low_confidence_fields()),
                "recommendations_available": len(self.recommendations)
            }
        }
    
    def clear(self):
        """Clear all signals"""
        self.signals.clear()
        self.followup_prompts.clear()
        self.validation_feedback.clear()
        self.recommendations.clear()
        self.confidence_indicators.clear()
        self.workflow_progress = None
        logger.debug("Cleared all UI signals")


def create_extraction_signals(
    extraction_result: Dict[str, Any],
    signal_manager: UISignalManager
):
    """Create UI signals from extraction result"""
    confidence = extraction_result.get("confidence", 0.0)
    method = extraction_result.get("method", "unknown")
    
    # Overall confidence signal
    confidence_level = ConfidenceLevel.from_score(confidence)
    if confidence_level == ConfidenceLevel.HIGH:
        signal_manager.add_signal(
            SignalType.SUCCESS,
            f"Data extracted successfully with high confidence ({confidence:.1%})",
            title="Extraction Complete"
        )
    elif confidence_level == ConfidenceLevel.MEDIUM:
        signal_manager.add_signal(
            SignalType.WARNING,
            f"Data extracted with moderate confidence ({confidence:.1%}). Please review.",
            title="Review Recommended"
        )
    else:
        signal_manager.add_signal(
            SignalType.WARNING,
            f"Data extracted with low confidence ({confidence:.1%}). Manual review required.",
            title="Manual Review Required",
            action_required=True
        )
    
    # Field-level confidence
    data = extraction_result.get("data", {})
    for section, content in data.items():
        if isinstance(content, dict):
            for field, value in content.items():
                field_path = f"{section}.{field}"
                # Simplified: use overall confidence, could be field-specific
                signal_manager.set_confidence_indicator(
                    field_path=field_path,
                    confidence_score=confidence,
                    extraction_method=method
                )


def create_validation_signals(
    validation_results: List[Dict[str, Any]],
    signal_manager: UISignalManager
):
    """Create UI signals from validation results"""
    for issue in validation_results:
        level = issue.get("level", "warning")
        field = issue.get("field", "unknown")
        message = issue.get("message", "")
        
        signal_manager.add_validation_feedback(
            field_path=field,
            level=level,
            message=message,
            suggestion=issue.get("suggestion"),
            can_auto_fix=issue.get("can_auto_fix", False),
            auto_fix_preview=issue.get("auto_fix_preview")
        )
        
        # Add signal for critical issues
        if level == "critical":
            signal_manager.add_signal(
                SignalType.ERROR,
                f"Critical issue in {field}: {message}",
                title="Validation Error",
                action_required=True
            )


def create_retrieval_signals(
    retrieval_results: List[Dict[str, Any]],
    signal_manager: UISignalManager
):
    """Create UI signals from retrieval results"""
    if not retrieval_results:
        return
    
    signal_manager.add_signal(
        SignalType.RECOMMENDATION,
        f"Found {len(retrieval_results)} relevant recommendations",
        title="Recommendations Available"
    )
    
    for result in retrieval_results:
        signal_manager.add_recommendation(
            recommendation_id=result.get("id", ""),
            title=result.get("title", ""),
            description=result.get("description", ""),
            source=result.get("source", "unknown"),
            relevance_score=result.get("score", 0.0),
            section=result.get("section"),
            content_preview=result.get("preview"),
            apply_action=result.get("action")
        )
