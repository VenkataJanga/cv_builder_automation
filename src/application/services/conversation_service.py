from __future__ import annotations

from typing import Any, Dict
from uuid import uuid4

from src.application.services.cv_builder_service import CVBuilderService
from src.application.services.retrieval_service import RetrievalService
from src.application.services.validation_service import ValidationService
from src.ai.agents.enhancement_agent import EnhancementAgent
from src.questionnaire.answer_analyzer import AnswerAnalyzer
from src.questionnaire.followup_engine import FollowupEngine
from src.questionnaire.question_selector import select_questions
from src.questionnaire.role_resolver import resolve_role


SESSION_STORE: Dict[str, Dict[str, Any]] = {}


class ConversationService:
    def __init__(self) -> None:
        self.cv_builder_service = CVBuilderService()
        self.answer_analyzer = AnswerAnalyzer()
        self.followup_engine = FollowupEngine()
        self.enhancement_agent = EnhancementAgent()
        self.retrieval_service = RetrievalService()
        self.validation_service = ValidationService()

    def start_session(self) -> Dict[str, Any]:
        session_id = str(uuid4())
        SESSION_STORE[session_id] = {
            "session_id": session_id,
            "step": "role",
            "role": None,
            "answers": {},
            "questions": [],
            "current_index": 0,
            "cv_data": self.cv_builder_service.initialize_cv_data(),
        }
        return {
            "session_id": session_id,
            "question": "What is your current role/title?",
        }

    def submit_answer(self, session_id: str, answer: str) -> Dict[str, Any]:
        if session_id not in SESSION_STORE:
            return {"error": "Invalid session_id"}

        session = SESSION_STORE[session_id]

        if session["step"] == "role":
            role = resolve_role(answer)
            questions = select_questions(role)

            session["role"] = role
            session["questions"] = questions
            session["step"] = "questions"
            session["current_index"] = 0
            session["cv_data"] = self.cv_builder_service.apply_role_seed(session["cv_data"], answer)

            if not questions:
                return {
                    "session_id": session_id,
                    "message": "No questions found for this role",
                    "cv_data": session["cv_data"],
                }

            return {
                "session_id": session_id,
                "resolved_role": role,
                "question": questions[0],
                "cv_data": session["cv_data"],
            }

        if session["step"] == "questions":
            idx = session["current_index"]
            questions = session["questions"]

            current_question = questions[idx]
            session["answers"][current_question] = answer
            session["cv_data"] = self.cv_builder_service.update_from_answer(
                session["cv_data"],
                current_question,
                answer,
            )

            if "professional profile" in current_question.lower():
                summary = session["cv_data"].get("summary", {}).get("professional_summary", "")
                session["cv_data"].setdefault("summary", {})
                session["cv_data"]["summary"]["professional_summary"] = self.enhancement_agent.enhance_summary(summary)

            analysis = self.answer_analyzer.analyze(current_question, answer)
            followup = self.followup_engine.generate_followup(current_question, answer) if analysis["needs_followup"] else None

            built_schema = self.cv_builder_service.try_build_schema(session["cv_data"])
            validation = self.validation_service.validate(session["cv_data"])
            context = self.retrieval_service.get_context(current_question)

            if followup:
                return {
                    "session_id": session_id,
                    "followup_question": followup,
                    "cv_data": session["cv_data"],
                    "cv_schema_ready": built_schema is not None,
                    "validation": validation,
                    "retrieved_context": context,
                }

            session["current_index"] += 1

            if session["current_index"] >= len(questions):
                return {
                    "session_id": session_id,
                    "message": "All questions completed",
                    "answers": session["answers"],
                    "cv_data": session["cv_data"],
                    "cv_schema_ready": built_schema is not None,
                    "validation": validation,
                    "retrieved_context": context,
                }

            next_question = questions[session["current_index"]]
            return {
                "session_id": session_id,
                "question": next_question,
                "cv_data": session["cv_data"],
                "cv_schema_ready": built_schema is not None,
                "validation": validation,
                "retrieved_context": context,
            }

        return {"message": "Invalid state"}

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return SESSION_STORE.get(session_id, {"error": "Invalid session_id"})

    def reset_session(self, session_id: str) -> Dict[str, Any]:
        if session_id in SESSION_STORE:
            del SESSION_STORE[session_id]
            return {"message": "Session reset successfully"}
        return {"error": "Invalid session_id"}
