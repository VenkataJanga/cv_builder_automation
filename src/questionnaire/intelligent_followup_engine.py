"""
Intelligent Follow-up Engine - Context-Aware Question Generation
Dynamically generates follow-up questions based on validation results and extraction confidence
"""

from typing import Dict, List, Any, Optional, Set
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class QuestionType(str, Enum):
    """Types of follow-up questions"""
    CLARIFICATION = "clarification"  # Clarify ambiguous information
    VERIFICATION = "verification"  # Verify low-confidence extractions
    EXPANSION = "expansion"  # Request more details
    CORRECTION = "correction"  # Fix validation errors
    ENRICHMENT = "enrichment"  # Add missing information
    CONTEXTUALIZATION = "contextualization"  # Provide context


class QuestionPriority(str, Enum):
    """Question priority levels"""
    CRITICAL = "critical"  # Must answer
    HIGH = "high"  # Should answer
    MEDIUM = "medium"  # Recommended to answer
    LOW = "low"  # Optional


class FollowUpQuestion(BaseModel):
    """Follow-up question model"""
    question_id: str
    question_type: QuestionType
    priority: QuestionPriority
    field_name: str
    question_text: str
    context: str  # Why we're asking
    suggested_answers: Optional[List[str]] = None
    input_validation: Optional[Dict[str, Any]] = None
    depends_on: Optional[List[str]] = None  # Question IDs this depends on
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class FollowUpStrategy(BaseModel):
    """Strategy for follow-up questions"""
    max_questions: int = 10
    prioritize_critical: bool = True
    group_by_section: bool = True
    adaptive: bool = True  # Adjust based on previous answers


class IntelligentFollowUpEngine:
    """Generate context-aware follow-up questions"""
    
    def __init__(self):
        self.question_templates = self._initialize_templates()
        self.field_dependencies = self._initialize_dependencies()
        self.asked_questions: Set[str] = set()
    
    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize question templates"""
        return {
            "missing_contact": {
                "type": QuestionType.ENRICHMENT,
                "priority": QuestionPriority.CRITICAL,
                "template": "What is your {field_name}?",
                "context": "Contact information is required for your CV"
            },
            "low_confidence_extraction": {
                "type": QuestionType.VERIFICATION,
                "priority": QuestionPriority.HIGH,
                "template": "I extracted '{extracted_value}' for {field_name}. Is this correct?",
                "context": "The extraction confidence was low, please verify"
            },
            "validation_error": {
                "type": QuestionType.CORRECTION,
                "priority": QuestionPriority.HIGH,
                "template": "There's an issue with {field_name}: {error_message}. Can you provide the correct information?",
                "context": "Validation detected an error that needs correction"
            },
            "missing_details": {
                "type": QuestionType.EXPANSION,
                "priority": QuestionPriority.MEDIUM,
                "template": "Can you provide more details about {field_name}?",
                "context": "Additional details would strengthen your CV"
            },
            "achievement_quantification": {
                "type": QuestionType.ENRICHMENT,
                "priority": QuestionPriority.MEDIUM,
                "template": "For '{experience_title}', can you quantify the impact? (e.g., percentage increase, cost savings, time saved)",
                "context": "Quantifiable achievements make your CV more impactful"
            },
            "skill_demonstration": {
                "type": QuestionType.CONTEXTUALIZATION,
                "priority": QuestionPriority.MEDIUM,
                "template": "You listed '{skill}' as a skill. Can you describe a project where you used it?",
                "context": "Demonstrating skills through experience strengthens credibility"
            },
            "experience_gap": {
                "type": QuestionType.CLARIFICATION,
                "priority": QuestionPriority.HIGH,
                "template": "I noticed a gap between {end_date} and {start_date}. What were you doing during this time?",
                "context": "Explaining employment gaps provides clarity"
            },
            "title_mismatch": {
                "type": QuestionType.CLARIFICATION,
                "priority": QuestionPriority.HIGH,
                "template": "Your current title is '{current_title}' but your most recent role was '{recent_title}'. Which is correct?",
                "context": "Ensuring title consistency across your CV"
            }
        }
    
    def _initialize_dependencies(self) -> Dict[str, List[str]]:
        """Initialize field dependencies"""
        return {
            "years_experience": ["work_experience"],
            "key_achievements": ["work_experience"],
            "primary_skills": ["skills", "work_experience"],
            "career_summary": ["years_experience", "current_title"],
        }
    
    def generate_followup_questions(
        self,
        cv_data: Dict[str, Any],
        extraction_results: Optional[Dict[str, Any]] = None,
        validation_results: Optional[Dict[str, Any]] = None,
        strategy: Optional[FollowUpStrategy] = None
    ) -> List[FollowUpQuestion]:
        """Generate follow-up questions based on multiple inputs"""
        
        if strategy is None:
            strategy = FollowUpStrategy()
        
        questions = []
        
        # Generate questions from extraction results
        if extraction_results:
            questions.extend(self._questions_from_extraction(extraction_results))
        
        # Generate questions from validation results
        if validation_results:
            questions.extend(self._questions_from_validation(validation_results))
        
        # Generate questions from missing information
        questions.extend(self._questions_from_missing_info(cv_data))
        
        # Generate enhancement questions
        questions.extend(self._questions_for_enhancement(cv_data))
        
        # Filter and prioritize
        questions = self._filter_questions(questions, strategy)
        questions = self._prioritize_questions(questions, strategy)
        
        # Limit to max questions
        if len(questions) > strategy.max_questions:
            questions = questions[:strategy.max_questions]
        
        return questions
    
    def _questions_from_extraction(
        self,
        extraction_results: Dict[str, Any]
    ) -> List[FollowUpQuestion]:
        """Generate questions from extraction results"""
        questions = []
        
        for field_name, result in extraction_results.items():
            # Check confidence level
            confidence = result.get("final_confidence", 1.0)
            needs_verification = result.get("needs_verification", False)
            
            if confidence < 0.7 or needs_verification:
                question = FollowUpQuestion(
                    question_id=f"verify_{field_name}",
                    question_type=QuestionType.VERIFICATION,
                    priority=QuestionPriority.HIGH if confidence < 0.5 else QuestionPriority.MEDIUM,
                    field_name=field_name,
                    question_text=f"I extracted '{result.get('final_value')}' for {field_name.replace('_', ' ')}. Is this correct?",
                    context=f"Extraction confidence: {confidence:.2%}. Please verify.",
                    suggested_answers=["Yes, that's correct", "No, let me correct it"],
                    metadata={
                        "confidence": confidence,
                        "extraction_strategy": result.get("strategy_used"),
                        "verification_reason": result.get("verification_reason")
                    }
                )
                questions.append(question)
        
        return questions
    
    def _questions_from_validation(
        self,
        validation_results: Dict[str, Any]
    ) -> List[FollowUpQuestion]:
        """Generate questions from validation results"""
        questions = []
        
        issues = validation_results.get("issues", [])
        
        for issue in issues:
            # Only create questions for actionable issues
            if issue.get("severity") in ["critical", "error"]:
                question = FollowUpQuestion(
                    question_id=f"fix_{issue.get('issue_id')}",
                    question_type=QuestionType.CORRECTION,
                    priority=QuestionPriority.CRITICAL if issue.get("severity") == "critical" else QuestionPriority.HIGH,
                    field_name=issue.get("field_name"),
                    question_text=f"{issue.get('message')}. {issue.get('suggestion', '')}",
                    context="Validation detected an issue that needs correction",
                    metadata={
                        "issue_id": issue.get("issue_id"),
                        "validation_level": issue.get("validation_level"),
                        "auto_fixable": issue.get("auto_fixable", False)
                    }
                )
                questions.append(question)
        
        return questions
    
    def _questions_from_missing_info(
        self,
        cv_data: Dict[str, Any]
    ) -> List[FollowUpQuestion]:
        """Generate questions for missing information"""
        questions = []
        
        # Check for missing critical fields
        critical_fields = {
            "email": "email address",
            "phone": "phone number",
            "full_name": "full name"
        }
        
        header = cv_data.get("header", {})
        for field, display_name in critical_fields.items():
            if not header.get(field):
                question = FollowUpQuestion(
                    question_id=f"missing_{field}",
                    question_type=QuestionType.ENRICHMENT,
                    priority=QuestionPriority.CRITICAL,
                    field_name=field,
                    question_text=f"What is your {display_name}?",
                    context="This information is required for your CV",
                    input_validation={
                        "type": "email" if field == "email" else "text",
                        "required": True
                    }
                )
                questions.append(question)
        
        # Check for missing sections
        if not cv_data.get("work_experience"):
            questions.append(FollowUpQuestion(
                question_id="missing_experience",
                question_type=QuestionType.ENRICHMENT,
                priority=QuestionPriority.CRITICAL,
                field_name="work_experience",
                question_text="Please provide details about your work experience. Start with your most recent role.",
                context="Work experience is essential for your CV",
                metadata={"section": "experience"}
            ))
        
        if not cv_data.get("skills"):
            questions.append(FollowUpQuestion(
                question_id="missing_skills",
                question_type=QuestionType.ENRICHMENT,
                priority=QuestionPriority.HIGH,
                field_name="skills",
                question_text="What are your key technical and professional skills?",
                context="Skills help match you with relevant opportunities",
                suggested_answers=["Technical skills (e.g., Python, Java)", "Soft skills (e.g., Leadership, Communication)"],
                metadata={"section": "skills"}
            ))
        
        return questions
    
    def _questions_for_enhancement(
        self,
        cv_data: Dict[str, Any]
    ) -> List[FollowUpQuestion]:
        """Generate questions to enhance CV quality"""
        questions = []
        
        # Check for quantifiable achievements
        experiences = cv_data.get("work_experience", [])
        for i, exp in enumerate(experiences[:3]):  # Focus on top 3
            description = str(exp.get("description", ""))
            
            # Check if it lacks quantification
            has_numbers = any(char.isdigit() for char in description)
            if not has_numbers:
                question = FollowUpQuestion(
                    question_id=f"quantify_exp_{i}",
                    question_type=QuestionType.ENRICHMENT,
                    priority=QuestionPriority.MEDIUM,
                    field_name=f"work_experience.{i}",
                    question_text=f"For your role as '{exp.get('job_title', 'your position')}' at {exp.get('company', 'this company')}, can you quantify your achievements? (e.g., '30% improvement', '$100K saved', '5-person team')",
                    context="Quantifiable achievements make your CV more impactful",
                    metadata={"experience_index": i}
                )
                questions.append(question)
        
        # Check for undemonstrated skills
        skills = cv_data.get("skills", [])
        if isinstance(skills, list):
            # Sample a few skills to ask about
            for skill in skills[:2]:
                questions.append(FollowUpQuestion(
                    question_id=f"demonstrate_skill_{skill}",
                    question_type=QuestionType.CONTEXTUALIZATION,
                    priority=QuestionPriority.LOW,
                    field_name="skills",
                    question_text=f"Can you describe a specific project or achievement where you used {skill}?",
                    context="Demonstrating skills through concrete examples strengthens your CV",
                    metadata={"skill": skill}
                ))
        
        return questions
    
    def _filter_questions(
        self,
        questions: List[FollowUpQuestion],
        strategy: FollowUpStrategy
    ) -> List[FollowUpQuestion]:
        """Filter duplicate or irrelevant questions"""
        
        # Remove duplicates based on question_id
        seen_ids = set()
        filtered = []
        
        for q in questions:
            if q.question_id not in seen_ids and q.question_id not in self.asked_questions:
                seen_ids.add(q.question_id)
                filtered.append(q)
        
        return filtered
    
    def _prioritize_questions(
        self,
        questions: List[FollowUpQuestion],
        strategy: FollowUpStrategy
    ) -> List[FollowUpQuestion]:
        """Prioritize questions based on strategy"""
        
        priority_order = {
            QuestionPriority.CRITICAL: 0,
            QuestionPriority.HIGH: 1,
            QuestionPriority.MEDIUM: 2,
            QuestionPriority.LOW: 3
        }
        
        # Sort by priority
        questions.sort(key=lambda q: (priority_order[q.priority], q.created_at))
        
        # Group by section if requested
        if strategy.group_by_section:
            questions = self._group_by_section(questions)
        
        return questions
    
    def _group_by_section(
        self,
        questions: List[FollowUpQuestion]
    ) -> List[FollowUpQuestion]:
        """Group questions by CV section"""
        
        sections = {
            "header": [],
            "experience": [],
            "skills": [],
            "education": [],
            "other": []
        }
        
        for q in questions:
            if "header" in q.field_name or q.field_name in ["email", "phone", "full_name"]:
                sections["header"].append(q)
            elif "experience" in q.field_name:
                sections["experience"].append(q)
            elif "skill" in q.field_name:
                sections["skills"].append(q)
            elif "education" in q.field_name:
                sections["education"].append(q)
            else:
                sections["other"].append(q)
        
        # Flatten back to list, maintaining section order
        grouped = []
        for section in ["header", "experience", "skills", "education", "other"]:
            grouped.extend(sections[section])
        
        return grouped
    
    def mark_question_asked(self, question_id: str):
        """Mark a question as asked"""
        self.asked_questions.add(question_id)
    
    def process_answer(
        self,
        question_id: str,
        answer: Any,
        cv_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process answer and update CV data"""
        
        self.mark_question_asked(question_id)
        
        # Extract field name from question_id
        # This is a simplified implementation
        return {
            "question_id": question_id,
            "answer": answer,
            "processed": True,
            "updated_cv_data": cv_data
        }
