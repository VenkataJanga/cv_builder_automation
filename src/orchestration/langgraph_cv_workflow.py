"""
LangGraph CV Workflow - State Machine for CV Processing
Orchestrates the complete CV extraction, validation, and enhancement pipeline
"""

from typing import Dict, List, Any, Optional, TypedDict, Annotated
from enum import Enum
import operator


class WorkflowState(TypedDict):
    """State object for LangGraph workflow"""
    # Input
    raw_input: str
    input_type: str  # "text", "voice_transcript", "uploaded_cv"
    user_id: str
    session_id: str
    
    # Extraction
    extracted_data: Dict[str, Any]
    extraction_confidence: Dict[str, float]
    extraction_metadata: Dict[str, Any]
    
    # Validation
    validation_results: Dict[str, Any]
    validation_passed: bool
    validation_issues: List[Dict[str, Any]]
    
    # Enhancement
    enhanced_data: Dict[str, Any]
    enhancement_suggestions: List[Dict[str, Any]]
    
    # Follow-up
    followup_questions: List[Dict[str, Any]]
    user_answers: Dict[str, Any]
    questions_remaining: int
    
    # Retrieval
    retrieved_context: List[Dict[str, Any]]
    retrieval_metadata: Dict[str, Any]
    
    # Output
    final_cv_data: Dict[str, Any]
    export_formats: List[str]
    
    # Control flow
    current_node: str
    iterations: int
    max_iterations: int
    errors: Annotated[List[str], operator.add]
    warnings: Annotated[List[str], operator.add]


class NodeNames:
    """Node names in the workflow"""
    START = "start"
    PREPROCESS = "preprocess"
    HYBRID_EXTRACT = "hybrid_extract"
    DEEP_VALIDATE = "deep_validate"
    ENHANCE = "enhance"
    GENERATE_FOLLOWUPS = "generate_followups"
    WAIT_FOR_USER = "wait_for_user"
    RETRIEVE_CONTEXT = "retrieve_context"
    FINALIZE = "finalize"
    ERROR = "error"
    END = "end"


class LangGraphCVWorkflow:
    """LangGraph workflow for CV processing"""
    
    def __init__(self):
        self.workflow_graph = self._build_workflow()
    
    def _build_workflow(self):
        """Build the LangGraph workflow"""
        
        # This would use actual LangGraph in production
        # For now, returning a structure that represents the graph
        
        return {
            "nodes": {
                NodeNames.START: self.start_node,
                NodeNames.PREPROCESS: self.preprocess_node,
                NodeNames.HYBRID_EXTRACT: self.hybrid_extract_node,
                NodeNames.DEEP_VALIDATE: self.deep_validate_node,
                NodeNames.ENHANCE: self.enhance_node,
                NodeNames.GENERATE_FOLLOWUPS: self.generate_followups_node,
                NodeNames.WAIT_FOR_USER: self.wait_for_user_node,
                NodeNames.RETRIEVE_CONTEXT: self.retrieve_context_node,
                NodeNames.FINALIZE: self.finalize_node,
                NodeNames.ERROR: self.error_node,
                NodeNames.END: self.end_node
            },
            "edges": {
                NodeNames.START: [NodeNames.PREPROCESS],
                NodeNames.PREPROCESS: [NodeNames.HYBRID_EXTRACT],
                NodeNames.HYBRID_EXTRACT: [NodeNames.DEEP_VALIDATE, NodeNames.ERROR],
                NodeNames.DEEP_VALIDATE: [NodeNames.ENHANCE, NodeNames.ERROR],
                NodeNames.ENHANCE: [NodeNames.GENERATE_FOLLOWUPS],
                NodeNames.GENERATE_FOLLOWUPS: [NodeNames.WAIT_FOR_USER, NodeNames.FINALIZE],
                NodeNames.WAIT_FOR_USER: [NodeNames.HYBRID_EXTRACT, NodeNames.FINALIZE],
                NodeNames.RETRIEVE_CONTEXT: [NodeNames.ENHANCE],
                NodeNames.FINALIZE: [NodeNames.END],
                NodeNames.ERROR: [NodeNames.END]
            },
            "conditional_edges": {
                NodeNames.HYBRID_EXTRACT: self.route_after_extraction,
                NodeNames.DEEP_VALIDATE: self.route_after_validation,
                NodeNames.GENERATE_FOLLOWUPS: self.route_after_followups,
                NodeNames.WAIT_FOR_USER: self.route_after_user_input
            }
        }
    
    # Node implementations
    
    def start_node(self, state: WorkflowState) -> WorkflowState:
        """Initialize workflow"""
        state["current_node"] = NodeNames.START
        state["iterations"] = 0
        state["max_iterations"] = state.get("max_iterations", 5)
        state["errors"] = []
        state["warnings"] = []
        return state
    
    def preprocess_node(self, state: WorkflowState) -> WorkflowState:
        """Preprocess input"""
        state["current_node"] = NodeNames.PREPROCESS
        
        # Clean and normalize input
        raw_input = state["raw_input"]
        input_type = state["input_type"]
        
        # Type-specific preprocessing
        if input_type == "voice_transcript":
            # Clean transcript artifacts
            raw_input = self._clean_transcript(raw_input)
        elif input_type == "uploaded_cv":
            # Extract text from document
            raw_input = self._extract_text_from_document(raw_input)
        
        state["raw_input"] = raw_input
        state["extraction_metadata"] = {"preprocessed": True}
        
        return state
    
    def hybrid_extract_node(self, state: WorkflowState) -> WorkflowState:
        """Extract CV data using hybrid approach"""
        state["current_node"] = NodeNames.HYBRID_EXTRACT
        
        try:
            # Import here to avoid circular dependency
            from src.ai.services.hybrid_extraction_engine import HybridExtractionEngine
            
            engine = HybridExtractionEngine()
            
            # Merge any user answers into the input
            enriched_input = state["raw_input"]
            if state.get("user_answers"):
                enriched_input += "\n\nAdditional Information:\n"
                for q_id, answer in state["user_answers"].items():
                    enriched_input += f"{q_id}: {answer}\n"
            
            result = engine.extract(enriched_input)
            
            state["extracted_data"] = result["extracted_data"]
            state["extraction_confidence"] = result["field_confidence"]
            state["extraction_metadata"] = result
            
        except Exception as e:
            state["errors"].append(f"Extraction failed: {str(e)}")
            state["current_node"] = NodeNames.ERROR
        
        return state
    
    def deep_validate_node(self, state: WorkflowState) -> WorkflowState:
        """Deep validation of extracted data"""
        state["current_node"] = NodeNames.DEEP_VALIDATE
        
        try:
            from src.ai.services.deep_validation_engine import DeepValidationEngine
            
            engine = DeepValidationEngine()
            result = engine.validate(state["extracted_data"])
            
            state["validation_results"] = result
            state["validation_passed"] = result["overall_valid"]
            state["validation_issues"] = result["issues"]
            
        except Exception as e:
            state["errors"].append(f"Validation failed: {str(e)}")
            state["current_node"] = NodeNames.ERROR
        
        return state
    
    def enhance_node(self, state: WorkflowState) -> WorkflowState:
        """Enhance extracted data"""
        state["current_node"] = NodeNames.ENHANCE
        
        try:
            from src.ai.services.enhanced_scaffold_system import EnhancedScaffoldSystem
            
            system = EnhancedScaffoldSystem()
            result = system.enhance(state["extracted_data"])
            
            state["enhanced_data"] = result["enhanced_cv"]
            state["enhancement_suggestions"] = result["suggestions"]
            
        except Exception as e:
            state["errors"].append(f"Enhancement failed: {str(e)}")
            state["warnings"].append("Proceeding with unenhanced data")
            state["enhanced_data"] = state["extracted_data"]
        
        return state
    
    def generate_followups_node(self, state: WorkflowState) -> WorkflowState:
        """Generate follow-up questions"""
        state["current_node"] = NodeNames.GENERATE_FOLLOWUPS
        
        try:
            from src.questionnaire.intelligent_followup_engine import IntelligentFollowUpEngine
            
            engine = IntelligentFollowUpEngine()
            questions = engine.generate_followup_questions(
                cv_data=state["enhanced_data"],
                extraction_results=state["extraction_metadata"],
                validation_results=state["validation_results"]
            )
            
            state["followup_questions"] = [q.dict() for q in questions]
            state["questions_remaining"] = len(questions)
            
        except Exception as e:
            state["warnings"].append(f"Follow-up generation failed: {str(e)}")
            state["followup_questions"] = []
            state["questions_remaining"] = 0
        
        return state
    
    def wait_for_user_node(self, state: WorkflowState) -> WorkflowState:
        """Wait for user to answer questions"""
        state["current_node"] = NodeNames.WAIT_FOR_USER
        
        # This is a special node that pauses execution
        # In practice, would use LangGraph's interrupt mechanism
        
        return state
    
    def retrieve_context_node(self, state: WorkflowState) -> WorkflowState:
        """Retrieve relevant context"""
        state["current_node"] = NodeNames.RETRIEVE_CONTEXT
        
        try:
            from src.retrieval.advanced_indexing_system import AdvancedIndexingSystem, RetrievalStrategy
            
            system = AdvancedIndexingSystem()
            
            # Build query from extracted data
            query = self._build_retrieval_query(state["extracted_data"])
            
            result = system.retrieve(
                query=query,
                strategy=RetrievalStrategy.HYBRID,
                top_k=5
            )
            
            state["retrieved_context"] = [r.dict() for r in result.results]
            state["retrieval_metadata"] = result.dict()
            
        except Exception as e:
            state["warnings"].append(f"Retrieval failed: {str(e)}")
            state["retrieved_context"] = []
        
        return state
    
    def finalize_node(self, state: WorkflowState) -> WorkflowState:
        """Finalize CV data"""
        state["current_node"] = NodeNames.FINALIZE
        
        # Use enhanced data if available, otherwise extracted data
        state["final_cv_data"] = state.get("enhanced_data", state["extracted_data"])
        
        # Mark exports to generate
        state["export_formats"] = ["json", "pdf", "docx"]
        
        return state
    
    def error_node(self, state: WorkflowState) -> WorkflowState:
        """Handle errors"""
        state["current_node"] = NodeNames.ERROR
        return state
    
    def end_node(self, state: WorkflowState) -> WorkflowState:
        """End workflow"""
        state["current_node"] = NodeNames.END
        return state
    
    # Conditional routing
    
    def route_after_extraction(self, state: WorkflowState) -> str:
        """Route after extraction"""
        if state.get("errors"):
            return NodeNames.ERROR
        return NodeNames.DEEP_VALIDATE
    
    def route_after_validation(self, state: WorkflowState) -> str:
        """Route after validation"""
        if state.get("errors"):
            return NodeNames.ERROR
        return NodeNames.ENHANCE
    
    def route_after_followups(self, state: WorkflowState) -> str:
        """Route after followup generation"""
        if state["questions_remaining"] > 0 and state["iterations"] < state["max_iterations"]:
            return NodeNames.WAIT_FOR_USER
        return NodeNames.FINALIZE
    
    def route_after_user_input(self, state: WorkflowState) -> str:
        """Route after user provides answers"""
        state["iterations"] += 1
        
        # If user provided substantial new information, re-extract
        if state.get("user_answers") and len(state["user_answers"]) > 2:
            return NodeNames.HYBRID_EXTRACT
        
        return NodeNames.FINALIZE
    
    # Helper methods
    
    def _clean_transcript(self, transcript: str) -> str:
        """Clean voice transcript"""
        # Remove filler words, fix common transcription errors
        transcript = transcript.replace("um ", "").replace("uh ", "")
        return transcript.strip()
    
    def _extract_text_from_document(self, document: str) -> str:
        """Extract text from document"""
        # In production, would handle various formats
        return document
    
    def _build_retrieval_query(self, cv_data: Dict[str, Any]) -> str:
        """Build query for retrieval"""
        parts = []
        
        if "current_title" in cv_data:
            parts.append(cv_data["current_title"])
        
        if "primary_skills" in cv_data:
            parts.extend(cv_data["primary_skills"][:5])
        
        return " ".join(parts)
    
    def run(self, initial_state: Dict[str, Any]) -> WorkflowState:
        """Run the workflow"""
        
        # Initialize state
        state: WorkflowState = {
            **initial_state,
            "iterations": 0,
            "errors": [],
            "warnings": []
        }
        
        # Execute nodes in sequence (simplified)
        # In production, would use LangGraph's execution engine
        
        current_node = NodeNames.START
        
        while current_node != NodeNames.END and state["iterations"] < state["max_iterations"]:
            # Execute current node
            node_func = self.workflow_graph["nodes"][current_node]
            state = node_func(state)
            
            # Get next node
            if current_node in self.workflow_graph["conditional_edges"]:
                next_node = self.workflow_graph["conditional_edges"][current_node](state)
            else:
                next_node = self.workflow_graph["edges"][current_node][0]
            
            current_node = next_node
            
            # Handle waiting for user
            if current_node == NodeNames.WAIT_FOR_USER:
                break
        
        return state
