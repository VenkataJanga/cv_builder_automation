"""
Enhanced Follow-up Question Engine

Features:
- Context-aware question generation
- Dynamic question prioritization
- Validation-driven follow-ups
- Adaptive questioning based on responses
- Multi-turn conversation support
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class QuestionType(str, Enum):
    """Types of follow-up questions"""
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    MULTISELECT = "multiselect"
    DATE = "date"
    NUMBER = "number"
    BOOLEAN = "boolean"


class QuestionPriority(str, Enum):
    """Priority levels for questions"""
    CRITICAL = "critical"  # Blocks progress
    HIGH = "high"  # Important for quality
    MEDIUM = "medium"  # Enhances completeness
    LOW = "low"  # Nice to have


@dataclass
class FollowUpQuestion:
    """Individual follow-up question"""
    id: str
    field_path: str
    question: str
    question_type: QuestionType
    priority: QuestionPriority
    
    # Optional fields
    hint: Optional[str] = None
    placeholder: Optional[str] = None
    options: List[str] = field(default_factory=list)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    default_value: Optional[Any] = None
    
    # Context
    context: str = ""
    depends_on: List[str] = field(default_factory=list)  # Other question IDs this depends on
    skip_if: Optional[str] = None  # Condition to skip this question
    
    # Metadata
    category: str = ""
    confidence_impact: float = 0.0  # How much this affects confidence
    completeness_impact: float = 0.0  # How much this affects completeness


@dataclass
class QuestionnaireSession:
    """Multi-turn questionnaire session"""
    session_id: str
    cv_data: Dict[str, Any]
    questions: List[FollowUpQuestion]
    answered_questions: Dict[str, Any] = field(default_factory=dict)
    skipped_questions: List[str] = field(default_factory=list)
    current_index: int = 0
    
    # State
    is_complete: bool = False
    completeness_score: float = 0.0
    confidence_score: float = 0.0


class EnhancedFollowUpEngine:
    """
    Intelligent follow-up question engine
    
    Generates context-aware questions based on:
    - Missing required fields
    - Validation issues
    - Low confidence scores
    - Incomplete sections
    - Role-specific requirements
    """
    
    # Question templates by field type
    QUESTION_TEMPLATES = {
        "header.email": {
            "question": "What is your email address?",
            "type": QuestionType.TEXT,
            "priority": QuestionPriority.CRITICAL,
            "validation": {"pattern": "email"},
            "hint": "We need this for contact purposes"
        },
        "header.contact_number": {
            "question": "What is your contact number?",
            "type": QuestionType.TEXT,
            "priority": QuestionPriority.CRITICAL,
            "validation": {"pattern": "phone"},
            "hint": "Include country code if applicable"
        },
        "header.location": {
            "question": "Where are you currently located?",
            "type": QuestionType.TEXT,
            "priority": QuestionPriority.HIGH,
            "hint": "City, State/Country"
        },
        "header.current_title": {
            "question": "What is your current job title?",
            "type": QuestionType.TEXT,
            "priority": QuestionPriority.HIGH,
            "hint": "e.g., Senior Software Engineer"
        },
        "summary": {
            "question": "Please provide a brief professional summary",
            "type": QuestionType.TEXTAREA,
            "priority": QuestionPriority.HIGH,
            "hint": "Describe your experience, key skills, and career focus (50-100 words)",
            "placeholder": "Example: Experienced software engineer with 5+ years..."
        },
        "years_of_experience": {
            "question": "How many years of professional experience do you have?",
            "type": QuestionType.NUMBER,
            "priority": QuestionPriority.MEDIUM,
            "validation": {"min": 0, "max": 50}
        },
        "databases": {
            "question": "Which database technologies have you worked with?",
            "type": QuestionType.MULTISELECT,
            "priority": QuestionPriority.MEDIUM,
            "options": [
                "MySQL", "PostgreSQL", "MongoDB", "Oracle", 
                "SQL Server", "DB2", "Redis", "Cassandra",
                "DynamoDB", "Elasticsearch"
            ]
        },
        "operating_systems": {
            "question": "Which operating systems are you familiar with?",
            "type": QuestionType.MULTISELECT,
            "priority": QuestionPriority.LOW,
            "options": ["Linux", "Windows", "macOS", "Unix", "Solaris"]
        },
        "cloud_platforms": {
            "question": "Which cloud platforms have you used?",
            "type": QuestionType.MULTISELECT,
            "priority": QuestionPriority.MEDIUM,
            "options": [
                "AWS", "Azure", "Google Cloud", "IBM Cloud",
                "Oracle Cloud", "Alibaba Cloud", "DigitalOcean"
            ]
        },
        "certifications": {
            "question": "Do you have any professional certifications?",
            "type": QuestionType.TEXTAREA,
            "priority": QuestionPriority.LOW,
            "hint": "List any relevant certifications",
            "placeholder": "e.g., AWS Certified Solutions Architect, PMP"
        }
    }
    
    def generate_followup_questions(
        self,
        cv_data: Dict[str, Any],
        validation_report: Optional[Dict[str, Any]] = None,
        role_context: Optional[str] = None
    ) -> List[FollowUpQuestion]:
        """
        Generate intelligent follow-up questions
        
        Args:
            cv_data: Current CV data
            validation_report: Validation results
            role_context: Target role context
            
        Returns:
            Prioritized list of follow-up questions
        """
        questions = []
        
        # Generate questions from missing fields
        questions.extend(self._questions_from_missing_fields(cv_data))
        
        # Generate questions from validation issues
        if validation_report:
            questions.extend(self._questions_from_validation(validation_report, cv_data))
        
        # Generate role-specific questions
        if role_context:
            questions.extend(self._questions_from_role(role_context, cv_data))
        
        # Generate questions for incomplete sections
        questions.extend(self._questions_from_incomplete_sections(cv_data))
        
        # Remove duplicates and sort by priority
        questions = self._deduplicate_and_prioritize(questions)
        
        logger.info(f"Generated {len(questions)} follow-up questions")
        
        return questions
    
    def _questions_from_missing_fields(
        self,
        cv_data: Dict[str, Any]
    ) -> List[FollowUpQuestion]:
        """Generate questions for missing required fields"""
        questions = []
        
        for field_path, template in self.QUESTION_TEMPLATES.items():
            value = self._get_nested_value(cv_data, field_path)
            
            if not value or value == "" or value == []:
                question = FollowUpQuestion(
                    id=f"missing_{field_path}",
                    field_path=field_path,
                    question=template["question"],
                    question_type=template["type"],
                    priority=template["priority"],
                    hint=template.get("hint"),
                    placeholder=template.get("placeholder"),
                    options=template.get("options", []),
                    validation_rules=template.get("validation", {}),
                    category="missing_field",
                    confidence_impact=0.1 if template["priority"] == QuestionPriority.CRITICAL else 0.05,
                    completeness_impact=0.15
                )
                questions.append(question)
        
        return questions
    
    def _questions_from_validation(
        self,
        validation_report: Dict[str, Any],
        cv_data: Dict[str, Any]
    ) -> List[FollowUpQuestion]:
        """Generate questions based on validation issues"""
        questions = []
        
        issues = validation_report.get("issues", [])
        
        for issue in issues:
            if issue.get("severity") in ["critical", "error"]:
                field = issue.get("field_path", "")
                category = issue.get("category", "")
                
                # Skip if already have a question for this field
                if any(q.field_path == field for q in questions):
                    continue
                
                # Generate appropriate question
                if category == "format":
                    question = self._generate_format_question(field, issue, cv_data)
                elif category == "completeness":
                    question = self._generate_completeness_question(field, issue, cv_data)
                elif category == "required_field":
                    question = self._generate_required_field_question(field, issue)
                else:
                    continue
                
                if question:
                    questions.append(question)
        
        return questions
    
    def _questions_from_role(
        self,
        role_context: str,
        cv_data: Dict[str, Any]
    ) -> List[FollowUpQuestion]:
        """Generate role-specific questions"""
        questions = []
        role_lower = role_context.lower()
        
        # Technical roles
        if any(term in role_lower for term in ["engineer", "developer", "architect"]):
            # Ask about technical skills if missing
            if not cv_data.get("skills"):
                questions.append(FollowUpQuestion(
                    id="role_tech_skills",
                    field_path="skills",
                    question=f"What are your key technical skills for a {role_context} role?",
                    question_type=QuestionType.TEXTAREA,
                    priority=QuestionPriority.HIGH,
                    hint="List programming languages, frameworks, and tools",
                    category="role_specific",
                    confidence_impact=0.15,
                    completeness_impact=0.2
                ))
            
            # Ask about projects
            if not cv_data.get("project_experience"):
                questions.append(FollowUpQuestion(
                    id="role_projects",
                    field_path="project_experience",
                    question=f"Can you describe a significant project you worked on as a {role_context}?",
                    question_type=QuestionType.TEXTAREA,
                    priority=QuestionPriority.MEDIUM,
                    hint="Include project name, your role, technologies used, and outcomes",
                    category="role_specific",
                    completeness_impact=0.15
                ))
        
        # Management roles
        if any(term in role_lower for term in ["manager", "lead", "director"]):
            questions.append(FollowUpQuestion(
                id="role_team_size",
                field_path="team_management",
                question="How many people have you managed?",
                question_type=QuestionType.NUMBER,
                priority=QuestionPriority.MEDIUM,
                hint="Enter team size",
                category="role_specific",
                completeness_impact=0.1
            ))
        
        return questions
    
    def _questions_from_incomplete_sections(
        self,
        cv_data: Dict[str, Any]
    ) -> List[FollowUpQuestion]:
        """Generate questions for incomplete sections"""
        questions = []
        
        # Check work experience completeness
        work_exp = cv_data.get("work_experience", [])
        if work_exp and len(work_exp) > 0:
            for idx, exp in enumerate(work_exp):
                if not exp.get("responsibilities"):
                    questions.append(FollowUpQuestion(
                        id=f"work_exp_{idx}_responsibilities",
                        field_path=f"work_experience[{idx}].responsibilities",
                        question=f"What were your key responsibilities at {exp.get('company', 'this company')}?",
                        question_type=QuestionType.TEXTAREA,
                        priority=QuestionPriority.MEDIUM,
                        hint="List your main duties and achievements",
                        category="section_completion",
                        completeness_impact=0.1
                    ))
        
        # Check education completeness
        education = cv_data.get("education", [])
        if education and len(education) > 0:
            for idx, edu in enumerate(education):
                if not edu.get("year"):
                    questions.append(FollowUpQuestion(
                        id=f"education_{idx}_year",
                        field_path=f"education[{idx}].year",
                        question=f"When did you complete your {edu.get('degree', 'degree')}?",
                        question_type=QuestionType.TEXT,
                        priority=QuestionPriority.LOW,
                        hint="e.g., 2020 or 2018-2020",
                        category="section_completion",
                        completeness_impact=0.05
                    ))
        
        return questions
    
    def _generate_format_question(
        self,
        field: str,
        issue: Dict[str, Any],
        cv_data: Dict[str, Any]
    ) -> Optional[FollowUpQuestion]:
        """Generate question for format issues"""
        current_value = self._get_nested_value(cv_data, field)
        
        if "email" in field:
            return FollowUpQuestion(
                id=f"format_{field}",
                field_path=field,
                question=f"The email address '{current_value}' appears to be invalid. Please provide a valid email:",
                question_type=QuestionType.TEXT,
                priority=QuestionPriority.HIGH,
                validation_rules={"pattern": "email"},
                category="format_correction",
                confidence_impact=0.15
            )
        
        elif "phone" in field or "contact" in field:
            return FollowUpQuestion(
                id=f"format_{field}",
                field_path=field,
                question="Please provide a valid phone number:",
                question_type=QuestionType.TEXT,
                priority=QuestionPriority.HIGH,
                hint="Include country code if applicable",
                validation_rules={"pattern": "phone"},
                category="format_correction",
                confidence_impact=0.1
            )
        
        return None
    
    def _generate_completeness_question(
        self,
        field: str,
        issue: Dict[str, Any],
        cv_data: Dict[str, Any]
    ) -> Optional[FollowUpQuestion]:
        """Generate question for completeness issues"""
        recommendation = issue.get("recommendation", "")
        
        return FollowUpQuestion(
            id=f"complete_{field}",
            field_path=field,
            question=f"Can you provide more details for {field.split('.')[-1].replace('_', ' ')}?",
            question_type=QuestionType.TEXTAREA,
            priority=QuestionPriority.MEDIUM,
            hint=recommendation,
            category="completeness_enhancement",
            completeness_impact=0.1
        )
    
    def _generate_required_field_question(
        self,
        field: str,
        issue: Dict[str, Any]
    ) -> Optional[FollowUpQuestion]:
        """Generate question for required fields"""
        # Check if we have a template for this field
        if field in self.QUESTION_TEMPLATES:
            template = self.QUESTION_TEMPLATES[field]
            return FollowUpQuestion(
                id=f"required_{field}",
                field_path=field,
                question=template["question"],
                question_type=template["type"],
                priority=QuestionPriority.CRITICAL,
                hint=template.get("hint"),
                validation_rules=template.get("validation", {}),
                category="required_field",
                confidence_impact=0.2
            )
        
        # Generate generic question
        field_name = field.split('.')[-1].replace('_', ' ').title()
        return FollowUpQuestion(
            id=f"required_{field}",
            field_path=field,
            question=f"Please provide your {field_name}:",
            question_type=QuestionType.TEXT,
            priority=QuestionPriority.CRITICAL,
            category="required_field",
            confidence_impact=0.15
        )
    
    def _deduplicate_and_prioritize(
        self,
        questions: List[FollowUpQuestion]
    ) -> List[FollowUpQuestion]:
        """Remove duplicates and sort by priority"""
        # Remove duplicates based on field_path
        seen_fields = set()
        unique_questions = []
        
        for q in questions:
            if q.field_path not in seen_fields:
                seen_fields.add(q.field_path)
                unique_questions.append(q)
        
        # Sort by priority
        priority_order = {
            QuestionPriority.CRITICAL: 0,
            QuestionPriority.HIGH: 1,
            QuestionPriority.MEDIUM: 2,
            QuestionPriority.LOW: 3
        }
        
        unique_questions.sort(key=lambda q: priority_order.get(q.priority, 4))
        
        return unique_questions
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dict using dot notation"""
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        
        return value
    
    def create_session(
        self,
        session_id: str,
        cv_data: Dict[str, Any],
        questions: List[FollowUpQuestion]
    ) -> QuestionnaireSession:
        """Create a new questionnaire session"""
        return QuestionnaireSession(
            session_id=session_id,
            cv_data=cv_data,
            questions=questions,
            completeness_score=self._calculate_initial_completeness(cv_data),
            confidence_score=0.5
        )
    
    def _calculate_initial_completeness(self, cv_data: Dict[str, Any]) -> float:
        """Calculate initial completeness score"""
        required_fields = [
            "header.full_name",
            "header.email",
            "header.contact_number",
            "summary",
            "skills"
        ]
        
        present = sum(1 for field in required_fields if self._get_nested_value(cv_data, field))
        return present / len(required_fields)
    
    def answer_question(
        self,
        session: QuestionnaireSession,
        question_id: str,
        answer: Any
    ) -> QuestionnaireSession:
        """Record answer to a question and update session"""
        session.answered_questions[question_id] = answer
        
        # Find the question and update CV data
        question = next((q for q in session.questions if q.id == question_id), None)
        if question:
            self._set_nested_value(session.cv_data, question.field_path, answer)
            
            # Update scores
            session.completeness_score += question.completeness_impact
            session.confidence_score += question.confidence_impact
        
        # Move to next question
        session.current_index += 1
        
        # Check if complete
        if session.current_index >= len(session.questions):
            session.is_complete = True
        
        return session
    
    def skip_question(
        self,
        session: QuestionnaireSession,
        question_id: str
    ) -> QuestionnaireSession:
        """Skip a question"""
        session.skipped_questions.append(question_id)
        session.current_index += 1
        
        if session.current_index >= len(session.questions):
            session.is_complete = True
        
        return session
    
    def get_current_question(
        self,
        session: QuestionnaireSession
    ) -> Optional[FollowUpQuestion]:
        """Get the current question for the session"""
        if session.current_index < len(session.questions):
            return session.questions[session.current_index]
        return None
    
    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set value in nested dict using dot notation"""
        keys = path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
