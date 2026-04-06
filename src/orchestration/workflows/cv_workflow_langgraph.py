"""
LangGraph-Ready CV Processing Workflow.

Complete CV processing workflow ready for LangGraph orchestration with:
- State management
- Conditional routing
- Error handling
- Tracing integration
"""

import logging
from typing import Dict, List, Any, Optional, Annotated, TypedDict
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowState(str, Enum):
    """Workflow execution states"""
    INITIALIZED = "initialized"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    FOLLOWING_UP = "following_up"
    ENHANCING = "enhancing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowDecision(str, Enum):
    """Conditional routing decisions"""
    CONTINUE = "continue"
    FOLLOWUP_REQUIRED = "followup_required"
    VALIDATION_FAILED = "validation_failed"
    ENHANCEMENT_NEEDED = "enhancement_needed"
    SKIP_TO_GENERATION = "skip_to_generation"
    RETRY = "retry"
    ABORT = "abort"


# LangGraph State Schema
class CVWorkflowState(TypedDict):
    """
    State schema for LangGraph workflow.
    
    This follows LangGraph's state management pattern.
    """
    # Input
    input_text: str
    input_type: str  # 'document', 'transcript', 'manual'
    user_id: str
    
    # Extraction
    extracted_data: Optional[Dict[str, Any]]
    extraction_confidence: Optional[Dict[str, float]]
    extraction_metadata: Optional[Dict[str, Any]]
    
    # Validation
    validation_result: Optional[Dict[str, Any]]
    validation_passed: bool
    issues: List[Dict[str, Any]]
    
    # Follow-up
    followup_session: Optional[Dict[str, Any]]
    followup_responses: Dict[str, Any]
    followup_completed: bool
    
    # Enhancement
    enhanced_data: Optional[Dict[str, Any]]
    enhancement_applied: List[str]
    
    # Generation
    generated_cv: Optional[Dict[str, Any]]
    output_format: str
    
    # Workflow control
    current_state: str
    decision: Optional[str]
    error: Optional[str]
    retry_count: int
    metadata: Dict[str, Any]


@dataclass
class WorkflowNode:
    """A node in the workflow graph"""
    name: str
    handler: str  # Function name to call
    next_nodes: Dict[str, str]  # decision -> next node mapping
    retry_on_error: bool = False
    max_retries: int = 3


class CVWorkflowLangGraph:
    """
    LangGraph-ready CV processing workflow.
    
    This workflow can be compiled into a LangGraph StateGraph for
    robust orchestration with built-in checkpointing and error handling.
    """
    
    def __init__(
        self,
        extraction_service: Any,
        validation_service: Any,
        followup_engine: Any,
        enhancement_service: Any,
        generation_service: Any,
        tracer: Optional[Any] = None
    ):
        """
        Initialize workflow with required services.
        
        Args:
            extraction_service: Hybrid extraction service
            validation_service: Validation service V2
            followup_engine: Follow-up engine V2
            enhancement_service: Enhancement scaffold
            generation_service: CV generation service
            tracer: LangSmith tracer (optional)
        """
        self.extraction_service = extraction_service
        self.validation_service = validation_service
        self.followup_engine = followup_engine
        self.enhancement_service = enhancement_service
        self.generation_service = generation_service
        self.tracer = tracer
        
        # Define workflow graph
        self.graph = self._build_graph()
        
        logger.info("CVWorkflowLangGraph initialized")
    
    def _build_graph(self) -> Dict[str, WorkflowNode]:
        """
        Build the workflow graph structure.
        
        This defines the complete flow:
        START -> extract -> validate -> [followup?] -> enhance -> generate -> END
        """
        return {
            'extract': WorkflowNode(
                name='extract',
                handler='extraction_node',
                next_nodes={
                    WorkflowDecision.CONTINUE: 'validate',
                    WorkflowDecision.RETRY: 'extract',
                    WorkflowDecision.ABORT: 'end'
                },
                retry_on_error=True
            ),
            'validate': WorkflowNode(
                name='validate',
                handler='validation_node',
                next_nodes={
                    WorkflowDecision.CONTINUE: 'enhance',
                    WorkflowDecision.FOLLOWUP_REQUIRED: 'followup',
                    WorkflowDecision.VALIDATION_FAILED: 'followup',
                    WorkflowDecision.SKIP_TO_GENERATION: 'generate'
                }
            ),
            'followup': WorkflowNode(
                name='followup',
                handler='followup_node',
                next_nodes={
                    WorkflowDecision.CONTINUE: 'validate',
                    WorkflowDecision.SKIP_TO_GENERATION: 'generate'
                }
            ),
            'enhance': WorkflowNode(
                name='enhance',
                handler='enhancement_node',
                next_nodes={
                    WorkflowDecision.CONTINUE: 'generate',
                    WorkflowDecision.RETRY: 'enhance'
                },
                retry_on_error=True
            ),
            'generate': WorkflowNode(
                name='generate',
                handler='generation_node',
                next_nodes={
                    WorkflowDecision.CONTINUE: 'end',
                    WorkflowDecision.RETRY: 'generate'
                },
                retry_on_error=True
            )
        }
    
    async def extraction_node(self, state: CVWorkflowState) -> CVWorkflowState:
        """
        Extraction node - extracts CV data from input.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with extraction results
        """
        logger.info("Executing extraction node")
        
        # Trace with LangSmith if available
        if self.tracer:
            with self.tracer.trace("extraction", inputs={"input_type": state['input_type']}):
                result = await self._do_extraction(state)
        else:
            result = await self._do_extraction(state)
        
        state['current_state'] = WorkflowState.EXTRACTING.value
        return result
    
    async def _do_extraction(self, state: CVWorkflowState) -> CVWorkflowState:
        """Perform extraction"""
        try:
            extraction_result = await self.extraction_service.extract_cv_data(
                input_text=state['input_text'],
                input_type=state['input_type']
            )
            
            state['extracted_data'] = extraction_result.data
            state['extraction_confidence'] = extraction_result.confidence_scores
            state['extraction_metadata'] = extraction_result.metadata
            state['decision'] = WorkflowDecision.CONTINUE.value
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            state['error'] = str(e)
            state['retry_count'] += 1
            
            if state['retry_count'] < 3:
                state['decision'] = WorkflowDecision.RETRY.value
            else:
                state['decision'] = WorkflowDecision.ABORT.value
        
        return state
    
    async def validation_node(self, state: CVWorkflowState) -> CVWorkflowState:
        """
        Validation node - validates extracted data.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with validation results
        """
        logger.info("Executing validation node")
        
        if self.tracer:
            with self.tracer.trace("validation"):
                result = await self._do_validation(state)
        else:
            result = await self._do_validation(state)
        
        state['current_state'] = WorkflowState.VALIDATING.value
        return result
    
    async def _do_validation(self, state: CVWorkflowState) -> CVWorkflowState:
        """Perform validation"""
        try:
            validation_result = await self.validation_service.validate(
                cv_data=state['extracted_data'],
                context={
                    'input_type': state['input_type'],
                    'confidence': state.get('extraction_confidence', {})
                }
            )
            
            state['validation_result'] = {
                'is_valid': validation_result.is_valid,
                'completeness': validation_result.completeness,
                'quality_score': validation_result.quality_score,
                'issues': [
                    {
                        'field': issue.field,
                        'message': issue.message,
                        'severity': issue.severity.value,
                        'category': issue.category.value
                    }
                    for issue in validation_result.issues
                ],
                'followup_needed': validation_result.followup_needed
            }
            
            state['validation_passed'] = validation_result.is_valid
            state['issues'] = state['validation_result']['issues']
            
            # Decide next step
            if validation_result.followup_needed:
                state['decision'] = WorkflowDecision.FOLLOWUP_REQUIRED.value
            elif not validation_result.is_valid and validation_result.quality_score < 0.5:
                state['decision'] = WorkflowDecision.VALIDATION_FAILED.value
            else:
                state['decision'] = WorkflowDecision.CONTINUE.value
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            state['error'] = str(e)
            # Still continue to enhance/generate with what we have
            state['decision'] = WorkflowDecision.CONTINUE.value
        
        return state
    
    async def followup_node(self, state: CVWorkflowState) -> CVWorkflowState:
        """
        Follow-up node - handles follow-up questions.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with follow-up session
        """
        logger.info("Executing follow-up node")
        
        if self.tracer:
            with self.tracer.trace("followup"):
                result = await self._do_followup(state)
        else:
            result = await self._do_followup(state)
        
        state['current_state'] = WorkflowState.FOLLOWING_UP.value
        return result
    
    async def _do_followup(self, state: CVWorkflowState) -> CVWorkflowState:
        """Generate follow-up questions"""
        try:
            # Convert validation_result dict back to object if needed
            from src.ai.services.validation_service_v2 import ValidationResult, ValidationIssue, IssueSeverity, IssueCategory
            
            issues = []
            for issue_dict in state['issues']:
                issues.append(ValidationIssue(
                    field=issue_dict['field'],
                    message=issue_dict['message'],
                    severity=IssueSeverity(issue_dict['severity']),
                    category=IssueCategory(issue_dict['category']),
                    requires_followup=True
                ))
            
            validation_result = ValidationResult(
                is_valid=state['validation_passed'],
                issues=issues,
                completeness=state['validation_result']['completeness'],
                quality_score=state['validation_result']['quality_score'],
                followup_needed=state['validation_result']['followup_needed']
            )
            
            followup_session = await self.followup_engine.generate_followups(
                extracted_data=state['extracted_data'],
                validation_result=validation_result,
                original_text=state['input_text']
            )
            
            state['followup_session'] = {
                'questions': [
                    {
                        'field': q.field,
                        'question': q.question,
                        'priority': q.priority.value,
                        'type': q.followup_type.value,
                        'context': q.context,
                        'expected_format': q.expected_format,
                        'suggestions': q.suggestions
                    }
                    for q in followup_session.questions
                ],
                'current_index': followup_session.current_index,
                'completed': followup_session.completed
            }
            
            state['followup_completed'] = followup_session.completed
            
            # In a real implementation, this would pause for user input
            # For now, mark as needing user interaction
            state['decision'] = WorkflowDecision.CONTINUE.value
            
        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}")
            state['error'] = str(e)
            # Skip follow-up and continue
            state['decision'] = WorkflowDecision.SKIP_TO_GENERATION.value
        
        return state
    
    async def enhancement_node(self, state: CVWorkflowState) -> CVWorkflowState:
        """
        Enhancement node - enhances CV data.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with enhancements
        """
        logger.info("Executing enhancement node")
        
        if self.tracer:
            with self.tracer.trace("enhancement"):
                result = await self._do_enhancement(state)
        else:
            result = await self._do_enhancement(state)
        
        state['current_state'] = WorkflowState.ENHANCING.value
        return result
    
    async def _do_enhancement(self, state: CVWorkflowState) -> CVWorkflowState:
        """Perform enhancements"""
        try:
            # Merge follow-up responses if any
            data_to_enhance = state['extracted_data'].copy()
            if state.get('followup_responses'):
                data_to_enhance.update(state['followup_responses'])
            
            enhanced_result = await self.enhancement_service.enhance_cv_data(
                cv_data=data_to_enhance,
                context={
                    'validation_result': state.get('validation_result'),
                    'confidence': state.get('extraction_confidence', {})
                }
            )
            
            state['enhanced_data'] = enhanced_result.enhanced_data
            state['enhancement_applied'] = enhanced_result.enhancements_applied
            state['decision'] = WorkflowDecision.CONTINUE.value
            
        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            state['error'] = str(e)
            # Use extracted data as fallback
            state['enhanced_data'] = state['extracted_data']
            state['enhancement_applied'] = []
            state['decision'] = WorkflowDecision.CONTINUE.value
        
        return state
    
    async def generation_node(self, state: CVWorkflowState) -> CVWorkflowState:
        """
        Generation node - generates final CV.
        
        Args:
            state: Current workflow state
        
        Returns:
            Updated state with generated CV
        """
        logger.info("Executing generation node")
        
        if self.tracer:
            with self.tracer.trace("generation"):
                result = await self._do_generation(state)
        else:
            result = await self._do_generation(state)
        
        state['current_state'] = WorkflowState.GENERATING.value
        return result
    
    async def _do_generation(self, state: CVWorkflowState) -> CVWorkflowState:
        """Perform CV generation"""
        try:
            data_to_generate = state.get('enhanced_data') or state['extracted_data']
            
            generated_cv = await self.generation_service.generate_cv(
                cv_data=data_to_generate,
                output_format=state.get('output_format', 'json')
            )
            
            state['generated_cv'] = generated_cv
            state['decision'] = WorkflowDecision.CONTINUE.value
            state['current_state'] = WorkflowState.COMPLETED.value
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            state['error'] = str(e)
            state['retry_count'] += 1
            
            if state['retry_count'] < 3:
                state['decision'] = WorkflowDecision.RETRY.value
            else:
                state['current_state'] = WorkflowState.FAILED.value
        
        return state
    
    def get_node_handler(self, node_name: str):
        """Get the handler function for a node"""
        handlers = {
            'extraction_node': self.extraction_node,
            'validation_node': self.validation_node,
            'followup_node': self.followup_node,
            'enhancement_node': self.enhancement_node,
            'generation_node': self.generation_node
        }
        return handlers.get(node_name)
    
    async def execute(self, initial_state: Dict[str, Any]) -> CVWorkflowState:
        """
        Execute the complete workflow.
        
        Args:
            initial_state: Initial workflow state
        
        Returns:
            Final workflow state
        """
        logger.info("Starting workflow execution")
        
        # Initialize state
        state: CVWorkflowState = {
            'input_text': initial_state['input_text'],
            'input_type': initial_state['input_type'],
            'user_id': initial_state['user_id'],
            'extracted_data': None,
            'extraction_confidence': None,
            'extraction_metadata': None,
            'validation_result': None,
            'validation_passed': False,
            'issues': [],
            'followup_session': None,
            'followup_responses': initial_state.get('followup_responses', {}),
            'followup_completed': False,
            'enhanced_data': None,
            'enhancement_applied': [],
            'generated_cv': None,
            'output_format': initial_state.get('output_format', 'json'),
            'current_state': WorkflowState.INITIALIZED.value,
            'decision': None,
            'error': None,
            'retry_count': 0,
            'metadata': initial_state.get('metadata', {})
        }
        
        # Start with extraction node
        current_node_name = 'extract'
        
        while current_node_name != 'end':
            node = self.graph.get(current_node_name)
            if not node:
                logger.error(f"Unknown node: {current_node_name}")
                break
            
            # Execute node
            logger.info(f"Executing node: {node.name}")
            handler = self.get_node_handler(node.handler)
            
            if handler:
                state = await handler(state)
            else:
                logger.error(f"No handler for node: {node.name}")
                break
            
            # Determine next node based on decision
            decision = state.get('decision')
            next_node = node.next_nodes.get(decision, 'end')
            
            logger.info(f"Decision: {decision}, Next node: {next_node}")
            current_node_name = next_node
            
            # Safety check
            if state['retry_count'] > 10:
                logger.error("Too many retries, aborting")
                state['current_state'] = WorkflowState.FAILED.value
                break
        
        logger.info(f"Workflow completed with state: {state['current_state']}")
        
        return state
    
    def to_langgraph_definition(self) -> Dict[str, Any]:
        """
        Export workflow as LangGraph definition.
        
        Returns a structure that can be used to create a LangGraph StateGraph.
        """
        return {
            'state_schema': CVWorkflowState,
            'nodes': {
                name: {
                    'handler': node.handler,
                    'retry_on_error': node.retry_on_error,
                    'max_retries': node.max_retries
                }
                for name, node in self.graph.items()
            },
            'edges': {
                name: node.next_nodes
                for name, node in self.graph.items()
            },
            'entry_point': 'extract'
        }
