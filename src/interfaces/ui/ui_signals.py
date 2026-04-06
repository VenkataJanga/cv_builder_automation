"""
Enhanced UI Signals for CV Builder.

Provides rich UI feedback signals for:
- Follow-up prompt recommendations
- Validation status and issues
- Retrieval/RAG recommendations
- Confidence indicators
- Progress tracking
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    """Types of UI signals"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    QUESTION = "question"
    RECOMMENDATION = "recommendation"


class ConfidenceLevel(str, Enum):
    """Confidence level indicators"""
    VERY_HIGH = "very_high"  # 90-100%
    HIGH = "high"  # 75-90%
    MEDIUM = "medium"  # 50-75%
    LOW = "low"  # 25-50%
    VERY_LOW = "very_low"  # 0-25%
    
    @classmethod
    def from_score(cls, score: float) -> 'ConfidenceLevel':
        """Convert numeric score to confidence level"""
        if score >= 0.9:
            return cls.VERY_HIGH
        elif score >= 0.75:
            return cls.HIGH
        elif score >= 0.5:
            return cls.MEDIUM
        elif score >= 0.25:
            return cls.LOW
        else:
            return cls.VERY_LOW


@dataclass
class UISignal:
    """Base UI signal"""
    signal_type: SignalType
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            'type': self.signal_type.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class FollowUpSignal(UISignal):
    """Signal for follow-up questions"""
    question: str = ""
    field: str = ""
    priority: str = "medium"
    suggestions: List[str] = field(default_factory=list)
    expected_format: Optional[str] = None
    context: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'question': self.question,
            'field': self.field,
            'priority': self.priority,
            'suggestions': self.suggestions,
            'expected_format': self.expected_format,
            'context': self.context
        })
        return base


@dataclass
class ValidationSignal(UISignal):
    """Signal for validation results"""
    is_valid: bool = False
    field: Optional[str] = None
    severity: str = "info"
    issue_category: Optional[str] = None
    suggested_fix: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'is_valid': self.is_valid,
            'field': self.field,
            'severity': self.severity,
            'category': self.issue_category,
            'suggested_fix': self.suggested_fix
        })
        return base


@dataclass
class RetrievalSignal(UISignal):
    """Signal for retrieval/RAG recommendations"""
    recommendation_text: str = ""
    source: Optional[str] = None
    relevance_score: float = 0.0
    template_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'recommendation': self.recommendation_text,
            'source': self.source,
            'relevance_score': self.relevance_score,
            'template': self.template_name
        })
        return base


@dataclass
class ConfidenceSignal(UISignal):
    """Signal for confidence indicators"""
    field: str = ""
    score: float = 0.0
    level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    explanation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'field': self.field,
            'score': self.score,
            'level': self.level.value,
            'explanation': self.explanation
        })
        return base


@dataclass
class ProgressSignal(UISignal):
    """Signal for progress tracking"""
    stage: str = ""
    progress_percent: float = 0.0
    estimated_time_remaining: Optional[float] = None
    substeps: List[str] = field(default_factory=list)
    current_substep: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'stage': self.stage,
            'progress': self.progress_percent,
            'eta': self.estimated_time_remaining,
            'substeps': self.substeps,
            'current_substep': self.current_substep
        })
        return base


class UISignalAggregator:
    """
    Aggregates and manages UI signals for frontend display.
    
    Provides methods to generate rich UI feedback from workflow state.
    """
    
    def __init__(self):
        """Initialize signal aggregator"""
        self.signals: List[UISignal] = []
        logger.info("UISignalAggregator initialized")
    
    def add_signal(self, signal: UISignal):
        """Add a signal to the collection"""
        self.signals.append(signal)
        logger.debug(f"Added {signal.signal_type.value} signal: {signal.message}")
    
    def generate_followup_signals(
        self,
        followup_session: Dict[str, Any]
    ) -> List[FollowUpSignal]:
        """
        Generate follow-up question signals.
        
        Args:
            followup_session: Follow-up session data
        
        Returns:
            List of follow-up signals
        """
        signals = []
        
        if not followup_session or not followup_session.get('questions'):
            return signals
        
        for q in followup_session['questions']:
            signal = FollowUpSignal(
                signal_type=SignalType.QUESTION,
                message=f"Additional information needed for {q.get('field', 'field')}",
                question=q.get('question', ''),
                field=q.get('field', ''),
                priority=q.get('priority', 'medium'),
                suggestions=q.get('suggestions', []),
                expected_format=q.get('expected_format'),
                context=q.get('context'),
                metadata={
                    'followup_type': q.get('type'),
                    'can_skip': q.get('priority') == 'low'
                }
            )
            signals.append(signal)
            self.add_signal(signal)
        
        return signals
    
    def generate_validation_signals(
        self,
        validation_result: Dict[str, Any]
    ) -> List[ValidationSignal]:
        """
        Generate validation status signals.
        
        Args:
            validation_result: Validation result data
        
        Returns:
            List of validation signals
        """
        signals = []
        
        # Overall status signal
        if validation_result.get('is_valid'):
            overall_signal = ValidationSignal(
                signal_type=SignalType.SUCCESS,
                message="CV data validation passed",
                is_valid=True,
                metadata={
                    'completeness': validation_result.get('completeness', {}),
                    'quality_score': validation_result.get('quality_score', 0)
                }
            )
            signals.append(overall_signal)
            self.add_signal(overall_signal)
        
        # Issue signals
        for issue in validation_result.get('issues', []):
            severity = issue.get('severity', 'info')
            
            signal_type = SignalType.INFO
            if severity == 'error':
                signal_type = SignalType.ERROR
            elif severity == 'warning':
                signal_type = SignalType.WARNING
            
            signal = ValidationSignal(
                signal_type=signal_type,
                message=issue.get('message', ''),
                is_valid=False,
                field=issue.get('field'),
                severity=severity,
                issue_category=issue.get('category'),
                suggested_fix=issue.get('suggested_fix'),
                metadata={
                    'requires_followup': issue.get('requires_followup', False)
                }
            )
            signals.append(signal)
            self.add_signal(signal)
        
        return signals
    
    def generate_retrieval_signals(
        self,
        retrieval_results: List[Dict[str, Any]]
    ) -> List[RetrievalSignal]:
        """
        Generate retrieval/RAG recommendation signals.
        
        Args:
            retrieval_results: List of retrieval results
        
        Returns:
            List of retrieval signals
        """
        signals = []
        
        for result in retrieval_results:
            signal = RetrievalSignal(
                signal_type=SignalType.RECOMMENDATION,
                message=f"Recommendation from {result.get('source', 'knowledge base')}",
                recommendation_text=result.get('text', ''),
                source=result.get('source'),
                relevance_score=result.get('score', 0.0),
                template_name=result.get('template'),
                metadata={
                    'context': result.get('context', {}),
                    'applied': result.get('applied', False)
                }
            )
            signals.append(signal)
            self.add_signal(signal)
        
        return signals
    
    def generate_confidence_signals(
        self,
        confidence_scores: Dict[str, float],
        threshold: float = 0.7
    ) -> List[ConfidenceSignal]:
        """
        Generate confidence indicator signals.
        
        Args:
            confidence_scores: Field -> confidence score mapping
            threshold: Threshold for warnings
        
        Returns:
            List of confidence signals
        """
        signals = []
        
        for field, score in confidence_scores.items():
            level = ConfidenceLevel.from_score(score)
            
            # Determine signal type
            if score >= threshold:
                signal_type = SignalType.SUCCESS
                message = f"High confidence in {field}"
            elif score >= 0.5:
                signal_type = SignalType.WARNING
                message = f"Medium confidence in {field}"
            else:
                signal_type = SignalType.WARNING
                message = f"Low confidence in {field} - review recommended"
            
            # Generate explanation
            explanation = self._generate_confidence_explanation(field, score, level)
            
            signal = ConfidenceSignal(
                signal_type=signal_type,
                message=message,
                field=field,
                score=score,
                level=level,
                explanation=explanation,
                metadata={
                    'needs_review': score < threshold
                }
            )
            signals.append(signal)
            self.add_signal(signal)
        
        return signals
    
    def _generate_confidence_explanation(
        self,
        field: str,
        score: float,
        level: ConfidenceLevel
    ) -> str:
        """Generate human-readable confidence explanation"""
        explanations = {
            ConfidenceLevel.VERY_HIGH: f"The {field} was clearly identified with strong indicators.",
            ConfidenceLevel.HIGH: f"The {field} appears reliable based on the input.",
            ConfidenceLevel.MEDIUM: f"The {field} is moderately certain but may benefit from review.",
            ConfidenceLevel.LOW: f"The {field} has limited supporting information.",
            ConfidenceLevel.VERY_LOW: f"The {field} could not be reliably determined."
        }
        return explanations.get(level, f"Confidence score for {field}: {score:.2%}")
    
    def generate_progress_signal(
        self,
        current_stage: str,
        stages: List[str],
        substeps: Optional[List[str]] = None,
        current_substep: Optional[str] = None
    ) -> ProgressSignal:
        """
        Generate progress tracking signal.
        
        Args:
            current_stage: Current workflow stage
            stages: List of all stages
            substeps: Optional list of substeps for current stage
            current_substep: Current substep
        
        Returns:
            Progress signal
        """
        # Calculate progress
        if current_stage in stages:
            current_index = stages.index(current_stage)
            progress_percent = (current_index / len(stages)) * 100
        else:
            progress_percent = 0
        
        # Stage-specific messages
        stage_messages = {
            'extraction': 'Extracting CV information...',
            'validation': 'Validating extracted data...',
            'followup': 'Generating follow-up questions...',
            'enhancement': 'Enhancing CV content...',
            'generation': 'Generating final CV...',
            'completed': 'CV processing complete!'
        }
        
        message = stage_messages.get(current_stage, f'Processing: {current_stage}')
        
        signal = ProgressSignal(
            signal_type=SignalType.INFO,
            message=message,
            stage=current_stage,
            progress_percent=progress_percent,
            substeps=substeps or [],
            current_substep=current_substep,
            metadata={
                'total_stages': len(stages),
                'completed_stages': current_index if current_stage in stages else 0
            }
        )
        
        self.add_signal(signal)
        return signal
    
    def generate_from_workflow_state(
        self,
        workflow_state: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate all relevant signals from workflow state.
        
        Args:
            workflow_state: Complete workflow state
        
        Returns:
            Dictionary of categorized signals
        """
        result = {
            'followup': [],
            'validation': [],
            'retrieval': [],
            'confidence': [],
            'progress': [],
            'all': []
        }
        
        # Follow-up signals
        if workflow_state.get('followup_session'):
            followup_signals = self.generate_followup_signals(
                workflow_state['followup_session']
            )
            result['followup'] = [s.to_dict() for s in followup_signals]
        
        # Validation signals
        if workflow_state.get('validation_result'):
            validation_signals = self.generate_validation_signals(
                workflow_state['validation_result']
            )
            result['validation'] = [s.to_dict() for s in validation_signals]
        
        # Retrieval signals
        if workflow_state.get('retrieval_results'):
            retrieval_signals = self.generate_retrieval_signals(
                workflow_state['retrieval_results']
            )
            result['retrieval'] = [s.to_dict() for s in retrieval_signals]
        
        # Confidence signals
        if workflow_state.get('extraction_confidence'):
            confidence_signals = self.generate_confidence_signals(
                workflow_state['extraction_confidence']
            )
            result['confidence'] = [s.to_dict() for s in confidence_signals]
        
        # Progress signal
        if workflow_state.get('current_state'):
            stages = ['extraction', 'validation', 'followup', 'enhancement', 'generation', 'completed']
            progress_signal = self.generate_progress_signal(
                workflow_state['current_state'],
                stages
            )
            result['progress'] = [progress_signal.to_dict()]
        
        # Combine all signals
        result['all'] = [s.to_dict() for s in self.signals]
        
        return result
    
    def get_signals_by_type(self, signal_type: SignalType) -> List[Dict[str, Any]]:
        """Get all signals of a specific type"""
        return [
            s.to_dict()
            for s in self.signals
            if s.signal_type == signal_type
        ]
    
    def get_critical_signals(self) -> List[Dict[str, Any]]:
        """Get critical signals that require user attention"""
        critical_types = {SignalType.ERROR, SignalType.WARNING, SignalType.QUESTION}
        return [
            s.to_dict()
            for s in self.signals
            if s.signal_type in critical_types
        ]
    
    def clear(self):
        """Clear all signals"""
        self.signals.clear()
        logger.info("All signals cleared")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of signals"""
        summary = {
            'total': len(self.signals),
            'by_type': {}
        }
        
        for signal_type in SignalType:
            count = sum(1 for s in self.signals if s.signal_type == signal_type)
            if count > 0:
                summary['by_type'][signal_type.value] = count
        
        return summary
