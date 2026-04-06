"""
Intelligent Follow-up Question System
Context-aware follow-up generation based on extraction and validation results
"""

from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class FollowUpPriority(str, Enum):
    """Priority levels for follow-up questions"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FollowUpCategory(str, Enum):
    """Categories of follow-up questions"""
    MISSING_REQUIRED = "missing_required"
    CLARIFICATION = "clarification"
    ENHANCEMENT = "enhancement"
    VALIDATION = "validation"
    COMPLETION = "completion"


class FollowUpQuestion(BaseModel):
    """Represents a follow-up question"""
    id: str
    category: FollowUpCategory
    priority: FollowUpPriority
    question: str
    field: str
    context: Dict[str, Any] = Field(default_factory=dict)
    suggested_answers: List[str] = Field(default_factory=list)
    validation_rules: List[str] = Field(default_factory=list)
    skip_conditions: List[str] = Field(default_factory=list)


class FollowUpSession(BaseModel):
    """Track a follow-up session"""
    session_id: str
    questions: List[FollowUpQuestion]
    answered: Dict[str, Any] = Field(default_factory=dict)
    skipped: Set[str] = Field(default_factory=set)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed: bool = False


class IntelligentFollowUpEngine:
    """
    Generate context-aware follow-up questions based on CV data analysis
    """
    
    def __init__(self):
        self.question_templates = self._initialize_templates()
        self.active_sessions: Dict[str, FollowUpSession] = {}
    
    def _initialize_templates(self) -> Dict[str, Dict]:
        """Initialize question templates"""
        return {
            "missing_name": {
                "category": FollowUpCategory.MISSING_REQUIRED,
                "priority": FollowUpPriority.CRITICAL,
                "question": "What is your full name?",
                "field": "full_name",
                "validation_rules": ["not_empty", "valid_name_format"]
            },
            "missing_email": {
                "category": FollowUpCategory.MISSING_REQUIRED,
                "priority": FollowUpPriority.CRITICAL,
                "question": "What is your email address?",
                "field": "email",
                "validation_rules": ["valid_email"]
            },
            "missing_phone": {
                "category": FollowUpCategory.MISSING_REQUIRED,
                "priority": FollowUpPriority.CRITICAL,
                "question": "What is your contact number?",
                "field": "contact_number",
                "validation_rules": ["valid_phone"]
            },
            "missing_experience": {
                "category": FollowUpCategory.MISSING_REQUIRED,
                "priority": FollowUpPriority.HIGH,
                "question": "How many years of professional experience do you have?",
                "field": "total_experience",
                "validation_rules": ["numeric", "reasonable_range"]
            },
            "clarify_skills": {
                "category": FollowUpCategory.CLARIFICATION,
                "priority": FollowUpPriority.HIGH,
                "question": "Can you list your key technical skills? (e.g., programming languages, frameworks, tools)",
                "field": "skills",
                "validation_rules": ["list_format", "minimum_count"]
            },
            "enhance_summary": {
                "category": FollowUpCategory.ENHANCEMENT,
                "priority": FollowUpPriority.MEDIUM,
                "question": "Could you provide a brief professional summary highlighting your key strengths and career goals?",
                "field": "professional_summary",
                "validation_rules": ["minimum_length"]
            },
            "clarify_education": {
                "category": FollowUpCategory.CLARIFICATION,
                "priority": FollowUpPriority.HIGH,
                "question": "What is your highest educational qualification?",
                "field": "education",
                "suggested_answers": ["Bachelor's", "Master's", "PhD", "Diploma", "Other"]
            },
            "add_certifications": {
                "category": FollowUpCategory.COMPLETION,
                "priority": FollowUpPriority.LOW,
                "question": "Do you have any professional certifications? If yes, please list them.",
                "field": "certifications",
                "skip_conditions": ["no_certifications"]
            },
            "clarify_project_details": {
                "category": FollowUpCategory.ENHANCEMENT,
                "priority": FollowUpPriority.MEDIUM,
                "question": "Can you provide more details about your project: {project_name}? Include your role, technologies used, and key achievements.",
                "field": "projects",
                "validation_rules": ["minimum_length"]
            },
            "add_achievements": {
                "category": FollowUpCategory.COMPLETION,
                "priority": FollowUpPriority.LOW,
                "question": "What are your key professional achievements or accomplishments?",
                "field": "achievements",
                "skip_conditions": ["no_achievements"]
            },
            "clarify_role_preference": {
                "category": FollowUpCategory.CLARIFICATION,
                "priority": FollowUpPriority.MEDIUM,
                "question": "What type of role are you looking for?",
                "field": "desired_role",
                "suggested_answers": ["Software Engineer", "Data Scientist", "Product Manager", "DevOps Engineer", "Other"]
            },
            "validate_experience_timeline": {
                "category": FollowUpCategory.VALIDATION,
                "priority": FollowUpPriority.MEDIUM,
                "question": "Your total experience ({total_exp} years) seems inconsistent with your project timeline ({project_exp} years). Could you clarify?",
                "field": "total_experience",
                "validation_rules": ["timeline_consistency"]
            }
        }
    
    def generate_followups(
        self,
        cv_data: Dict[str, Any],
        validation_result: Optional[Any] = None,
        extraction_confidence: Optional[Any] = None
    ) -> FollowUpSession:
        """
        Generate intelligent follow-up questions based on CV data, validation, and extraction confidence
        """
        
        questions = []
        session_id = f"session_{datetime.utcnow().timestamp()}"
        
        # Check for missing required fields
        questions.extend(self._generate_missing_field_questions(cv_data))
        
        # Check for low confidence extractions
        if extraction_confidence:
            questions.extend(self._generate_low_confidence_questions(cv_data, extraction_confidence))
        
        # Check validation issues
        if validation_result:
            questions.extend(self._generate_validation_questions(cv_data, validation_result))
        
        # Check for enhancement opportunities
        questions.extend(self._generate_enhancement_questions(cv_data))
        
        # Sort by priority
        questions = self._prioritize_questions(questions)
        
        # Create session
        session = FollowUpSession(
            session_id=session_id,
            questions=questions
        )
        
        self.active_sessions[session_id] = session
        
        return session
    
    def _generate_missing_field_questions(
        self,
        cv_data: Dict[str, Any]
    ) -> List[FollowUpQuestion]:
        """Generate questions for missing required fields"""
        
        questions = []
        required_fields = {
            "full_name": "missing_name",
            "email": "missing_email",
            "contact_number": "missing_phone",
            "total_experience": "missing_experience"
        }
        
        for field, template_key in required_fields.items():
            if field not in cv_data or not cv_data.get(field):
                template = self.question_templates[template_key]
                questions.append(FollowUpQuestion(
                    id=f"q_{field}_{datetime.utcnow().timestamp()}",
                    category=template["category"],
                    priority=template["priority"],
                    question=template["question"],
                    field=template["field"],
                    validation_rules=template.get("validation_rules", []),
                    suggested_answers=template.get("suggested_answers", [])
                ))
        
        return questions
    
    def _generate_low_confidence_questions(
        self,
        cv_data: Dict[str, Any],
        extraction_confidence: Any
    ) -> List[FollowUpQuestion]:
        """Generate questions for fields with low extraction confidence"""
        
        questions = []
        
        if hasattr(extraction_confidence, 'by_field'):
            for field, confidence in extraction_confidence.by_field.items():
                if confidence < 0.6 and cv_data.get(field):
                    # Generate clarification question
                    questions.append(FollowUpQuestion(
                        id=f"q_clarify_{field}_{datetime.utcnow().timestamp()}",
                        category=FollowUpCategory.CLARIFICATION,
                        priority=FollowUpPriority.HIGH,
                        question=f"We extracted '{cv_data[field]}' for {field}. Is this correct?",
                        field=field,
                        context={"extracted_value": cv_data[field], "confidence": confidence},
                        suggested_answers=["Yes, correct", "No, let me provide the correct value"]
                    ))
        
        return questions
    
    def _generate_validation_questions(
        self,
        cv_data: Dict[str, Any],
        validation_result: Any
    ) -> List[FollowUpQuestion]:
        """Generate questions based on validation issues"""
        
        questions = []
        
        if hasattr(validation_result, 'issues'):
            for issue in validation_result.issues:
                # Only generate questions for high-priority issues
                if issue.level.value in ['error', 'warning']:
                    priority_map = {
                        'error': FollowUpPriority.CRITICAL,
                        'warning': FollowUpPriority.HIGH
                    }
                    
                    questions.append(FollowUpQuestion(
                        id=f"q_validation_{issue.field}_{datetime.utcnow().timestamp()}",
                        category=FollowUpCategory.VALIDATION,
                        priority=priority_map.get(issue.level.value, FollowUpPriority.MEDIUM),
                        question=f"{issue.message}. {issue.suggestion or 'Could you provide the correct information?'}",
                        field=issue.field,
                        context={"validation_issue": issue.message}
                    ))
        
        return questions
    
    def _generate_enhancement_questions(
        self,
        cv_data: Dict[str, Any]
    ) -> List[FollowUpQuestion]:
        """Generate questions for enhancing CV completeness"""
        
        questions = []
        
        # Check if professional summary is missing or brief
        summary = cv_data.get("professional_summary", "")
        if not summary or len(str(summary)) < 100:
            template = self.question_templates["enhance_summary"]
            questions.append(FollowUpQuestion(
                id=f"q_enhance_summary_{datetime.utcnow().timestamp()}",
                category=template["category"],
                priority=template["priority"],
                question=template["question"],
                field=template["field"],
                validation_rules=template.get("validation_rules", [])
            ))
        
        # Check if skills are minimal
        skills = cv_data.get("skills", [])
        if len(skills) < 3:
            template = self.question_templates["clarify_skills"]
            questions.append(FollowUpQuestion(
                id=f"q_skills_{datetime.utcnow().timestamp()}",
                category=template["category"],
                priority=template["priority"],
                question=template["question"],
                field=template["field"],
                validation_rules=template.get("validation_rules", [])
            ))
        
        # Check for certifications
        if "certifications" not in cv_data or not cv_data.get("certifications"):
            template = self.question_templates["add_certifications"]
            questions.append(FollowUpQuestion(
                id=f"q_cert_{datetime.utcnow().timestamp()}",
                category=template["category"],
                priority=template["priority"],
                question=template["question"],
                field=template["field"],
                skip_conditions=template.get("skip_conditions", [])
            ))
        
        # Check project details
        projects = cv_data.get("projects", [])
        for idx, project in enumerate(projects):
            if isinstance(project, dict):
                desc = project.get("description", "")
                if len(desc) < 100:
                    questions.append(FollowUpQuestion(
                        id=f"q_project_{idx}_{datetime.utcnow().timestamp()}",
                        category=FollowUpCategory.ENHANCEMENT,
                        priority=FollowUpPriority.MEDIUM,
                        question=f"Can you provide more details about project {idx + 1}? Include your role, technologies used, and key achievements.",
                        field=f"projects[{idx}]",
                        context={"project_index": idx}
                    ))
        
        return questions
    
    def _prioritize_questions(
        self,
        questions: List[FollowUpQuestion]
    ) -> List[FollowUpQuestion]:
        """Sort questions by priority and category"""
        
        priority_order = {
            FollowUpPriority.CRITICAL: 0,
            FollowUpPriority.HIGH: 1,
            FollowUpPriority.MEDIUM: 2,
            FollowUpPriority.LOW: 3
        }
        
        return sorted(questions, key=lambda q: priority_order.get(q.priority, 999))
    
    def answer_question(
        self,
        session_id: str,
        question_id: str,
        answer: Any
    ) -> Dict[str, Any]:
        """Record answer to a follow-up question"""
        
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        # Find the question
        question = next((q for q in session.questions if q.id == question_id), None)
        
        if not question:
            return {"error": "Question not found"}
        
        # Store answer
        session.answered[question_id] = {
            "field": question.field,
            "answer": answer,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check if session is complete
        answered_count = len(session.answered) + len(session.skipped)
        if answered_count >= len(session.questions):
            session.completed = True
        
        return {
            "success": True,
            "session_completed": session.completed,
            "progress": f"{answered_count}/{len(session.questions)}"
        }
    
    def skip_question(
        self,
        session_id: str,
        question_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Skip a follow-up question"""
        
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        session.skipped.add(question_id)
        
        # Check if session is complete
        answered_count = len(session.answered) + len(session.skipped)
        if answered_count >= len(session.questions):
            session.completed = True
        
        return {
            "success": True,
            "session_completed": session.completed,
            "progress": f"{answered_count}/{len(session.questions)}"
        }
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get the current status of a follow-up session"""
        
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session.session_id,
            "total_questions": len(session.questions),
            "answered": len(session.answered),
            "skipped": len(session.skipped),
            "remaining": len(session.questions) - len(session.answered) - len(session.skipped),
            "completed": session.completed,
            "created_at": session.created_at
        }
    
    def get_next_question(self, session_id: str) -> Optional[FollowUpQuestion]:
        """Get the next unanswered question in the session"""
        
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        answered_ids = set(session.answered.keys())
        
        for question in session.questions:
            if question.id not in answered_ids and question.id not in session.skipped:
                return question
        
        return None
    
    def get_collected_data(self, session_id: str) -> Dict[str, Any]:
        """Get all collected answers from the session"""
        
        if session_id not in self.active_sessions:
            return {}
        
        session = self.active_sessions[session_id]
        
        collected = {}
        for question_id, answer_data in session.answered.items():
            field = answer_data["field"]
            answer = answer_data["answer"]
            collected[field] = answer
        
        return collected
