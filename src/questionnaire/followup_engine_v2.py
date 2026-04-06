"""
Follow-up Engine V2 - Intelligent follow-up question generation.

Enhanced follow-up logic that provides:
- Context-aware question generation
- Priority-based follow-up ordering
- Smart question templates
- Validation-driven follow-ups
- Conversation state management
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FollowUpPriority(str, Enum):
    """Priority levels for follow-up questions"""
    CRITICAL = "critical"  # Must have - blocks CV generation
    HIGH = "high"  # Important - significantly improves quality
    MEDIUM = "medium"  # Recommended - improves completeness
    LOW = "low"  # Optional - enhances details


class FollowUpType(str, Enum):
    """Types of follow-up questions"""
    MISSING_FIELD = "missing_field"
    LOW_CONFIDENCE = "low_confidence"
    INCONSISTENCY = "inconsistency"
    CLARIFICATION = "clarification"
    ENRICHMENT = "enrichment"


@dataclass
class FollowUpQuestion:
    """A single follow-up question"""
    field: str
    question: str
    priority: FollowUpPriority
    followup_type: FollowUpType
    context: str  # Why we're asking
    expected_format: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    validation_rule: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FollowUpSession:
    """Follow-up conversation session state"""
    questions: List[FollowUpQuestion]
    current_index: int = 0
    responses: Dict[str, Any] = field(default_factory=dict)
    skipped: List[str] = field(default_factory=list)
    completed: bool = False


class FollowUpEngineV2:
    """
    Intelligent follow-up question generation engine.
    """
    
    # Question templates by field
    QUESTION_TEMPLATES = {
        'header.full_name': {
            'question': "What is your full name?",
            'expected_format': "First name and last name",
            'priority': FollowUpPriority.CRITICAL
        },
        'header.email': {
            'question': "What is your email address?",
            'expected_format': "name@domain.com",
            'priority': FollowUpPriority.CRITICAL
        },
        'header.contact_number': {
            'question': "What is your contact number?",
            'expected_format': "10-digit phone number",
            'priority': FollowUpPriority.CRITICAL
        },
        'header.location': {
            'question': "What is your current location?",
            'expected_format': "City, Country",
            'priority': FollowUpPriority.HIGH
        },
        'header.total_experience': {
            'question': "How many years of total experience do you have?",
            'expected_format': "Number of years",
            'priority': FollowUpPriority.HIGH
        },
        'professional_summary': {
            'question': "Can you provide a brief professional summary about yourself?",
            'expected_format': "2-3 sentences describing your expertise and experience",
            'priority': FollowUpPriority.HIGH
        },
        'skills': {
            'question': "What are your primary technical skills?",
            'expected_format': "List of skills (e.g., Python, Java, AWS)",
            'priority': FollowUpPriority.HIGH,
            'suggestions': ['Python', 'Java', 'JavaScript', 'AWS', 'Azure', 'Docker', 'Kubernetes']
        },
        'work_experience': {
            'question': "Can you describe your work experience?",
            'expected_format': "Company name, role, duration, and responsibilities",
            'priority': FollowUpPriority.CRITICAL
        },
        'education': {
            'question': "What is your educational background?",
            'expected_format': "Degree, institution, and year",
            'priority': FollowUpPriority.HIGH
        },
        'project_experience': {
            'question': "Can you describe one or more projects you've worked on?",
            'expected_format': "Project name, description, technologies used, and your role",
            'priority': FollowUpPriority.MEDIUM
        },
        'certifications': {
            'question': "Do you have any professional certifications?",
            'expected_format': "Certification name and issuing organization",
            'priority': FollowUpPriority.LOW
        }
    }
    
    # Context templates for different follow-up types
    CONTEXT_TEMPLATES = {
        FollowUpType.MISSING_FIELD: "This field is required for your CV.",
        FollowUpType.LOW_CONFIDENCE: "I'm not completely confident about this information. Could you confirm or provide it again?",
        FollowUpType.INCONSISTENCY: "There seems to be some inconsistency in the information provided.",
        FollowUpType.CLARIFICATION: "I need some clarification to ensure accuracy.",
        FollowUpType.ENRICHMENT: "Additional details here would strengthen your CV."
    }
    
    def __init__(self):
        """Initialize follow-up engine"""
        logger.info("FollowUpEngineV2 initialized")
    
    async def generate_followups(
        self,
        extracted_data: Dict[str, Any],
        validation_result: Any,  # ValidationResult from validation_service_v2
        original_text: Optional[str] = None
    ) -> FollowUpSession:
        """
        Generate follow-up questions based on validation results.
        
        Args:
            extracted_data: Extracted CV data
            validation_result: Validation result with issues
            original_text: Original input text for context
        
        Returns:
            FollowUpSession with prioritized questions
        """
        logger.info("Generating follow-up questions")
        
        questions = []
        
        # 1. Generate questions from validation issues
        for issue in validation_result.issues:
            if issue.requires_followup:
                question = self._create_question_from_issue(
                    issue,
                    extracted_data,
                    original_text
                )
                if question:
                    questions.append(question)
        
        # 2. Generate questions for fields needing follow-up
        for field in validation_result.followup_needed:
            if not any(q.field == field for q in questions):
                question = self._create_question_for_field(
                    field,
                    FollowUpType.MISSING_FIELD,
                    extracted_data
                )
                if question:
                    questions.append(question)
        
        # 3. Generate enrichment questions for incomplete sections
        enrichment_questions = self._generate_enrichment_questions(
            extracted_data,
            validation_result.completeness
        )
        questions.extend(enrichment_questions)
        
        # 4. Sort by priority
        questions = self._prioritize_questions(questions)
        
        # 5. Remove duplicates
        questions = self._deduplicate_questions(questions)
        
        logger.info(f"Generated {len(questions)} follow-up questions")
        
        return FollowUpSession(questions=questions)
    
    def _create_question_from_issue(
        self,
        issue: Any,
        data: Dict[str, Any],
        original_text: Optional[str]
    ) -> Optional[FollowUpQuestion]:
        """Create follow-up question from validation issue"""
        
        # Map severity to priority
        priority_map = {
            'error': FollowUpPriority.CRITICAL,
            'warning': FollowUpPriority.HIGH,
            'info': FollowUpPriority.MEDIUM
        }
        priority = priority_map.get(issue.severity.value, FollowUpPriority.MEDIUM)
        
        # Determine follow-up type
        followup_type_map = {
            'completeness': FollowUpType.MISSING_FIELD,
            'accuracy': FollowUpType.LOW_CONFIDENCE,
            'consistency': FollowUpType.INCONSISTENCY,
            'format': FollowUpType.CLARIFICATION,
            'quality': FollowUpType.ENRICHMENT
        }
        followup_type = followup_type_map.get(
            issue.category.value,
            FollowUpType.CLARIFICATION
        )
        
        # Get template or create custom question
        template = self.QUESTION_TEMPLATES.get(issue.field, {})
        
        question_text = template.get('question', f"Could you provide information for {issue.field.replace('_', ' ')}?")
        context = self.CONTEXT_TEMPLATES.get(followup_type, issue.message)
        
        return FollowUpQuestion(
            field=issue.field,
            question=question_text,
            priority=priority,
            followup_type=followup_type,
            context=context,
            expected_format=template.get('expected_format'),
            suggestions=template.get('suggestions', []),
            metadata={'validation_issue': issue.message}
        )
    
    def _create_question_for_field(
        self,
        field: str,
        followup_type: FollowUpType,
        data: Dict[str, Any]
    ) -> Optional[FollowUpQuestion]:
        """Create follow-up question for a specific field"""
        
        template = self.QUESTION_TEMPLATES.get(field)
        if not template:
            # Generate generic question
            field_name = field.replace('_', ' ').replace('.', ' - ')
            return FollowUpQuestion(
                field=field,
                question=f"Could you provide information about your {field_name}?",
                priority=FollowUpPriority.MEDIUM,
                followup_type=followup_type,
                context=self.CONTEXT_TEMPLATES.get(followup_type, "")
            )
        
        return FollowUpQuestion(
            field=field,
            question=template['question'],
            priority=template.get('priority', FollowUpPriority.MEDIUM),
            followup_type=followup_type,
            context=self.CONTEXT_TEMPLATES.get(followup_type, ""),
            expected_format=template.get('expected_format'),
            suggestions=template.get('suggestions', [])
        )
    
    def _generate_enrichment_questions(
        self,
        data: Dict[str, Any],
        completeness: Dict[str, float]
    ) -> List[FollowUpQuestion]:
        """Generate questions to enrich incomplete sections"""
        questions = []
        
        # Check for missing certifications
        certs = data.get('certifications', [])
        if not certs or len(certs) == 0:
            questions.append(FollowUpQuestion(
                field='certifications',
                question="Do you have any professional certifications you'd like to include?",
                priority=FollowUpPriority.LOW,
                followup_type=FollowUpType.ENRICHMENT,
                context="Certifications can strengthen your CV",
                suggestions=['AWS Certified', 'Azure Certified', 'PMP', 'Scrum Master']
            ))
        
        # Check for missing secondary skills
        secondary_skills = data.get('secondary_skills', [])
        if not secondary_skills or len(secondary_skills) < 3:
            questions.append(FollowUpQuestion(
                field='secondary_skills',
                question="Do you have any additional technical skills or frameworks?",
                priority=FollowUpPriority.MEDIUM,
                followup_type=FollowUpType.ENRICHMENT,
                context="Secondary skills help showcase your full expertise",
                expected_format="Databases, cloud platforms, tools, etc."
            ))
        
        # Check for missing project details
        projects = data.get('project_experience', [])
        if projects and len(projects) > 0:
            for i, project in enumerate(projects):
                if isinstance(project, dict):
                    # Check if project has minimal info
                    if not project.get('technologies_used'):
                        questions.append(FollowUpQuestion(
                            field=f'project_experience[{i}].technologies_used',
                            question=f"What technologies did you use in the {project.get('project_name', 'project')}?",
                            priority=FollowUpPriority.MEDIUM,
                            followup_type=FollowUpType.ENRICHMENT,
                            context="Technology details show your practical experience"
                        ))
        
        return questions
    
    def _prioritize_questions(
        self,
        questions: List[FollowUpQuestion]
    ) -> List[FollowUpQuestion]:
        """Sort questions by priority"""
        priority_order = {
            FollowUpPriority.CRITICAL: 0,
            FollowUpPriority.HIGH: 1,
            FollowUpPriority.MEDIUM: 2,
            FollowUpPriority.LOW: 3
        }
        
        return sorted(questions, key=lambda q: priority_order[q.priority])
    
    def _deduplicate_questions(
        self,
        questions: List[FollowUpQuestion]
    ) -> List[FollowUpQuestion]:
        """Remove duplicate questions for the same field"""
        seen_fields = set()
        unique_questions = []
        
        for question in questions:
            if question.field not in seen_fields:
                unique_questions.append(question)
                seen_fields.add(question.field)
        
        return unique_questions
    
    async def process_response(
        self,
        session: FollowUpSession,
        response: str
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Process user response to current follow-up question.
        
        Args:
            session: Current follow-up session
            response: User's response text
        
        Returns:
            Tuple of (extracted_data, has_more_questions)
        """
        if session.current_index >= len(session.questions):
            session.completed = True
            return {}, False
        
        current_question = session.questions[session.current_index]
        
        # Extract data from response
        extracted = await self._extract_from_response(
            response,
            current_question
        )
        
        # Store response
        session.responses[current_question.field] = extracted
        
        # Move to next question
        session.current_index += 1
        
        # Check if more questions remain
        has_more = session.current_index < len(session.questions)
        if not has_more:
            session.completed = True
        
        return extracted, has_more
    
    async def _extract_from_response(
        self,
        response: str,
        question: FollowUpQuestion
    ) -> Any:
        """Extract structured data from user response"""
        # Simple extraction logic - can be enhanced with LLM
        response = response.strip()
        
        # Handle common patterns
        if question.field.endswith('email'):
            # Extract email
            import re
            email_match = re.search(r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b', response)
            return email_match.group(0) if email_match else response
        
        elif question.field.endswith('contact_number'):
            # Extract phone
            import re
            phone = re.sub(r'[^\d+]', '', response)
            return phone
        
        elif 'skills' in question.field:
            # Extract skills list
            import re
            skills = [s.strip() for s in re.split(r'[,\n]', response) if s.strip()]
            return skills
        
        elif 'experience' in question.field.lower():
            # Return as-is for further processing
            return response
        
        else:
            # Default: return raw response
            return response
    
    def get_current_question(self, session: FollowUpSession) -> Optional[FollowUpQuestion]:
        """Get current question from session"""
        if session.current_index < len(session.questions):
            return session.questions[session.current_index]
        return None
    
    def skip_current_question(self, session: FollowUpSession) -> bool:
        """
        Skip current question and move to next.
        
        Returns:
            True if more questions remain
        """
        if session.current_index < len(session.questions):
            current = session.questions[session.current_index]
            session.skipped.append(current.field)
            session.current_index += 1
        
        has_more = session.current_index < len(session.questions)
        if not has_more:
            session.completed = True
        
        return has_more
    
    def get_session_summary(self, session: FollowUpSession) -> Dict[str, Any]:
        """Get summary of follow-up session"""
        return {
            'total_questions': len(session.questions),
            'answered': len(session.responses),
            'skipped': len(session.skipped),
            'remaining': len(session.questions) - session.current_index,
            'completed': session.completed,
            'completion_rate': len(session.responses) / len(session.questions) if session.questions else 0
        }
