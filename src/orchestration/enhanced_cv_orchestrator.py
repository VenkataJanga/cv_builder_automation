"""
Enhanced CV Processing Orchestrator

Integrates all enhanced components:
- Hybrid extraction
- Enhanced validation
- Follow-up question engine
- RAG-powered retrieval
- LangSmith tracing
- UI signals

This orchestrator provides a complete, production-ready workflow.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from src.ai.services.hybrid_extraction_service import HybridExtractionService
from src.ai.services.validation_service_v2 import ValidationServiceV2
from src.questionnaire.enhanced_followup_engine import EnhancedFollowUpEngine
from src.retrieval.enhanced_rag_service import EnhancedRAGService
from src.observability.langsmith_tracer import LangSmithTracer, SpanType
from src.web.ui_signals import UISignalManager

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Complete processing result with all enhancements"""
    # Core data
    extracted_data: Dict[str, Any]
    validation_report: Dict[str, Any]
    followup_questions: List[Dict[str, Any]]
    
    # Retrieval suggestions
    retrieval_suggestions: Dict[str, List[Dict[str, Any]]]
    
    # Metadata
    confidence_scores: Dict[str, float]
    processing_time_ms: float
    trace_id: str
    
    # UI signals
    ui_signals: Dict[str, Any]
    
    # Status
    status: str
    errors: List[str]


class EnhancedCVOrchestrator:
    """
    Complete orchestrator for CV processing with all enhancements
    
    Features:
    - Multi-strategy extraction (voice, text, PDF)
    - Deep validation with auto-correction
    - Smart follow-up question generation
    - RAG-powered suggestions
    - Full observability with LangSmith
    - Rich UI signals
    
    Usage:
        orchestrator = EnhancedCVOrchestrator(
            extraction_service=extraction_service,
            validation_service=validation_service,
            followup_engine=followup_engine,
            rag_service=rag_service,
            tracer=tracer
        )
        
        # Process voice transcript
        result = await orchestrator.process_voice_cv(
            transcript="I'm John Doe, a senior software engineer...",
            user_id="user_123",
            session_id="session_456"
        )
        
        # Handle follow-up answers
        result = await orchestrator.process_followup_answers(
            result.trace_id,
            answers={"q1": "Python, Java, JavaScript"}
        )
    """
    
    def __init__(
        self,
        extraction_service: HybridExtractionService,
        validation_service: ValidationServiceV2,
        followup_engine: EnhancedFollowUpEngine,
        rag_service: EnhancedRAGService,
        tracer: LangSmithTracer,
        signal_manager: Optional[UISignalManager] = None
    ):
        self.extraction_service = extraction_service
        self.validation_service = validation_service
        self.followup_engine = followup_engine
        self.rag_service = rag_service
        self.tracer = tracer
        self.signal_manager = signal_manager or UISignalManager()
        
        # Track active processing sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def process_voice_cv(
        self,
        transcript: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """
        Process a voice transcript into a CV
        
        Args:
            transcript: Voice transcript text
            user_id: User identifier
            session_id: Session identifier
            initial_data: Any pre-existing data to merge
            
        Returns:
            Complete processing result
        """
        # Start trace
        trace = self.tracer.start_trace(
            name="voice_cv_processing",
            user_id=user_id,
            session_id=session_id,
            tags=["voice", "cv_extraction"],
            metadata={"transcript_length": len(transcript)}
        )
        
        start_time = datetime.now()
        
        try:
            # Progress signal
            self.signal_manager.generate_progress_signal(
                stage="extraction",
                progress_percent=10,
                completed_steps=[],
                current_step="Extracting CV data from transcript",
                total_steps=6
            )
            
            # Step 1: Extract CV data
            with self.tracer.span("extraction", SpanType.EXTRACTION, trace.trace_id) as span:
                span.inputs = {"transcript": transcript[:500]}
                
                extraction_result = await self.extraction_service.extract_from_voice(
                    transcript=transcript,
                    initial_data=initial_data
                )
                
                span.outputs = {"extracted_fields": list(extraction_result.keys())}
                span.metadata = {"confidence": extraction_result.get("_confidence", {}).get("overall", 0.0)}
            
            self.signal_manager.generate_progress_signal(
                stage="extraction",
                progress_percent=30,
                completed_steps=["Extraction"],
                current_step="Validating extracted data",
                total_steps=6
            )
            
            # Step 2: Validate extracted data
            with self.tracer.span("validation", SpanType.VALIDATION, trace.trace_id) as span:
                span.inputs = {"data": extraction_result}
                
                validation_report = await self.validation_service.validate(
                    data=extraction_result,
                    auto_correct=True
                )
                
                span.outputs = {
                    "is_valid": validation_report["is_valid"],
                    "issue_count": len(validation_report.get("issues", []))
                }
            
            # Apply auto-corrections
            if validation_report.get("auto_corrections"):
                extraction_result = self._apply_corrections(
                    extraction_result,
                    validation_report["auto_corrections"]
                )
            
            self.signal_manager.generate_progress_signal(
                stage="extraction",
                progress_percent=50,
                completed_steps=["Extraction", "Validation"],
                current_step="Generating follow-up questions",
                total_steps=6
            )
            
            # Step 3: Generate follow-up questions
            with self.tracer.span("followup_generation", SpanType.FOLLOWUP, trace.trace_id) as span:
                span.inputs = {"data": extraction_result, "validation": validation_report}
                
                followup_questions = await self.followup_engine.generate_questions(
                    extracted_data=extraction_result,
                    validation_report=validation_report
                )
                
                span.outputs = {"question_count": len(followup_questions)}
            
            self.signal_manager.generate_progress_signal(
                stage="extraction",
                progress_percent=70,
                completed_steps=["Extraction", "Validation", "Follow-up Generation"],
                current_step="Retrieving suggestions",
                total_steps=6
            )
            
            # Step 4: Get retrieval suggestions
            with self.tracer.span("retrieval", SpanType.RETRIEVAL, trace.trace_id) as span:
                span.inputs = {"extracted_data": extraction_result}
                
                retrieval_suggestions = await self._get_retrieval_suggestions(
                    extraction_result,
                    trace.trace_id
                )
                
                span.outputs = {"suggestion_fields": list(retrieval_suggestions.keys())}
            
            self.signal_manager.generate_progress_signal(
                stage="extraction",
                progress_percent=90,
                completed_steps=["Extraction", "Validation", "Follow-up", "Retrieval"],
                current_step="Generating UI signals",
                total_steps=6
            )
            
            # Step 5: Generate UI signals
            self._generate_ui_signals(
                extraction_result,
                validation_report,
                followup_questions,
                retrieval_suggestions
            )
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(
                extraction_result,
                validation_report
            )
            
            # End trace
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.tracer.end_trace(trace.trace_id)
            
            self.signal_manager.generate_progress_signal(
                stage="extraction",
                progress_percent=100,
                completed_steps=["Extraction", "Validation", "Follow-up", "Retrieval", "Signals", "Complete"],
                current_step="Processing complete",
                total_steps=6
            )
            
            # Store session data
            self.active_sessions[trace.trace_id] = {
                "extracted_data": extraction_result,
                "validation_report": validation_report,
                "followup_questions": followup_questions,
                "trace_id": trace.trace_id
            }
            
            return ProcessingResult(
                extracted_data=extraction_result,
                validation_report=validation_report,
                followup_questions=followup_questions,
                retrieval_suggestions=retrieval_suggestions,
                confidence_scores=confidence_scores,
                processing_time_ms=processing_time,
                trace_id=trace.trace_id,
                ui_signals=self.signal_manager.to_dict(),
                status="success",
                errors=[]
            )
            
        except Exception as e:
            logger.error(f"Error processing voice CV: {str(e)}", exc_info=True)
            self.tracer.end_trace(trace.trace_id, status="error")
            
            return ProcessingResult(
                extracted_data={},
                validation_report={"is_valid": False, "issues": []},
                followup_questions=[],
                retrieval_suggestions={},
                confidence_scores={},
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                trace_id=trace.trace_id,
                ui_signals=self.signal_manager.to_dict(),
                status="error",
                errors=[str(e)]
            )
    
    async def process_followup_answers(
        self,
        trace_id: str,
        answers: Dict[str, Any]
    ) -> ProcessingResult:
        """
        Process follow-up answers and update CV data
        
        Args:
            trace_id: Original trace ID
            answers: Question ID to answer mapping
            
        Returns:
            Updated processing result
        """
        if trace_id not in self.active_sessions:
            raise ValueError(f"Session {trace_id} not found")
        
        session = self.active_sessions[trace_id]
        
        # Create child trace
        trace = self.tracer.start_trace(
            name="followup_processing",
            tags=["followup", "cv_update"],
            metadata={"parent_trace": trace_id}
        )
        
        start_time = datetime.now()
        
        try:
            # Incorporate answers
            with self.tracer.span("incorporate_answers", SpanType.FOLLOWUP, trace.trace_id) as span:
                span.inputs = {"answers": answers}
                
                updated_data = await self.followup_engine.incorporate_answers(
                    base_data=session["extracted_data"],
                    questions=session["followup_questions"],
                    answers=answers
                )
                
                span.outputs = {"updated_fields": list(answers.keys())}
            
            # Re-validate
            validation_report = await self.validation_service.validate(
                data=updated_data,
                auto_correct=True
            )
            
            # Generate new follow-up questions if needed
            followup_questions = await self.followup_engine.generate_questions(
                extracted_data=updated_data,
                validation_report=validation_report
            )
            
            # Update retrieval suggestions
            retrieval_suggestions = await self._get_retrieval_suggestions(
                updated_data,
                trace.trace_id
            )
            
            # Update UI signals
            self.signal_manager.clear_signals_by_type("followup")
            self._generate_ui_signals(
                updated_data,
                validation_report,
                followup_questions,
                retrieval_suggestions
            )
            
            # Calculate confidence
            confidence_scores = self._calculate_confidence_scores(
                updated_data,
                validation_report
            )
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.tracer.end_trace(trace.trace_id)
            
            # Update session
            session["extracted_data"] = updated_data
            session["validation_report"] = validation_report
            session["followup_questions"] = followup_questions
            
            return ProcessingResult(
                extracted_data=updated_data,
                validation_report=validation_report,
                followup_questions=followup_questions,
                retrieval_suggestions=retrieval_suggestions,
                confidence_scores=confidence_scores,
                processing_time_ms=processing_time,
                trace_id=trace.trace_id,
                ui_signals=self.signal_manager.to_dict(),
                status="success",
                errors=[]
            )
            
        except Exception as e:
            logger.error(f"Error processing follow-up answers: {str(e)}", exc_info=True)
            self.tracer.end_trace(trace.trace_id, status="error")
            raise
    
    async def _get_retrieval_suggestions(
        self,
        extracted_data: Dict[str, Any],
        trace_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get retrieval suggestions for fields"""
        suggestions = {}
        
        # Check for incomplete or low-confidence fields
        fields_needing_suggestions = self._identify_fields_for_retrieval(extracted_data)
        
        for field_path in fields_needing_suggestions:
            try:
                results = await self.rag_service.get_field_suggestions(
                    field_path=field_path,
                    context=extracted_data,
                    top_k=3
                )
                
                if results:
                    suggestions[field_path] = results
                    
            except Exception as e:
                logger.warning(f"Error getting suggestions for {field_path}: {e}")
        
        return suggestions
    
    def _identify_fields_for_retrieval(self, data: Dict[str, Any]) -> List[str]:
        """Identify fields that could benefit from retrieval"""
        fields = []
        
        # Check skills
        if not data.get("skills", {}).get("primary"):
            fields.append("skills.primary")
        
        # Check professional summary
        if not data.get("professional_summary") or len(data.get("professional_summary", "")) < 50:
            fields.append("professional_summary")
        
        # Check certifications
        if not data.get("certifications"):
            fields.append("certifications")
        
        return fields
    
    def _generate_ui_signals(
        self,
        extracted_data: Dict[str, Any],
        validation_report: Dict[str, Any],
        followup_questions: List[Dict[str, Any]],
        retrieval_suggestions: Dict[str, List[Dict[str, Any]]]
    ):
        """Generate all UI signals"""
        # Follow-up signals
        if followup_questions:
            self.signal_manager.generate_followup_signals(followup_questions)
        
        # Validation signals
        if not validation_report["is_valid"]:
            self.signal_manager.generate_validation_signals(validation_report)
        
        # Retrieval signals
        if retrieval_suggestions:
            confidence_scores = self._calculate_confidence_scores(
                extracted_data,
                validation_report
            )
            self.signal_manager.generate_retrieval_signals(
                retrieval_suggestions,
                confidence_scores
            )
        
        # Confidence signal
        confidence_scores = self._calculate_confidence_scores(
            extracted_data,
            validation_report
        )
        self.signal_manager.generate_confidence_signal(confidence_scores)
    
    def _calculate_confidence_scores(
        self,
        extracted_data: Dict[str, Any],
        validation_report: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate confidence scores for extracted data"""
        scores = {}
        
        # Get extraction confidence if available
        extraction_confidence = extracted_data.get("_confidence", {})
        
        # Calculate field-level confidence
        for field, value in extracted_data.items():
            if field.startswith("_"):
                continue
            
            # Base confidence from extraction
            field_confidence = extraction_confidence.get(field, 0.5)
            
            # Adjust based on validation
            if validation_report.get("issues"):
                for issue in validation_report["issues"]:
                    if issue.get("field_path", "").startswith(field):
                        # Reduce confidence for validation issues
                        severity = issue.get("severity", "medium")
                        if severity == "critical":
                            field_confidence *= 0.5
                        elif severity == "high":
                            field_confidence *= 0.7
                        elif severity == "medium":
                            field_confidence *= 0.85
            
            # Check completeness
            if not value or (isinstance(value, (list, dict)) and not value):
                field_confidence *= 0.6
            
            scores[field] = min(1.0, max(0.0, field_confidence))
        
        # Calculate overall confidence
        if scores:
            scores["overall"] = sum(scores.values()) / len(scores)
        else:
            scores["overall"] = 0.0
        
        return scores
    
    def _apply_corrections(
        self,
        data: Dict[str, Any],
        corrections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply auto-corrections to data"""
        corrected_data = data.copy()
        
        for correction in corrections:
            field_path = correction.get("field_path", "")
            new_value = correction.get("corrected_value")
            
            if not field_path:
                continue
            
            # Apply correction using dot notation
            parts = field_path.split(".")
            current = corrected_data
            
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            current[parts[-1]] = new_value
            
            logger.info(f"Applied correction to {field_path}: {new_value}")
        
        return corrected_data
    
    def get_session_data(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by trace ID"""
        return self.active_sessions.get(trace_id)
    
    def clear_session(self, trace_id: str):
        """Clear session data"""
        if trace_id in self.active_sessions:
            del self.active_sessions[trace_id]
            logger.info(f"Cleared session: {trace_id}")
