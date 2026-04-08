from __future__ import annotations

from typing import Any, Dict
from uuid import uuid4

from src.application.services.cv_builder_service import CVBuilderService
from src.application.services.retrieval_service import RetrievalService
from src.application.services.validation_service import ValidationService
from src.ai.services.llm_enhancement_service import LLMEnhancementService
from src.ai.services.langsmith_service import LangSmithService
from src.questionnaire.answer_analyzer import AnswerAnalyzer
from src.questionnaire.followup_engine import FollowupEngine
from src.questionnaire.question_selector import select_initial_questions, select_questions
from src.questionnaire.role_resolver import resolve_role


SESSION_STORE: Dict[str, Dict[str, Any]] = {}


class ConversationService:
    def __init__(self) -> None:
        self.cv_builder_service = CVBuilderService()
        self.answer_analyzer = AnswerAnalyzer()
        self.followup_engine = FollowupEngine()
        self.retrieval_service = RetrievalService()
        self.validation_service = ValidationService()
        self.enhancement_service = LLMEnhancementService()
        self.langsmith_service = LangSmithService()

    def start_session(self) -> Dict[str, Any]:
        session_id = str(uuid4())
        initial_questions = select_initial_questions()

        SESSION_STORE[session_id] = {
            "session_id": session_id,
            "step": "initial",
            "role": None,
            "answers": {},
            "questions": initial_questions,
            "current_index": 0,
            "cv_data": self.cv_builder_service.initialize_cv_data(),
        }
        return {
            "session_id": session_id,
            "question": initial_questions[0] if initial_questions else "What is your full name?",
        }

    def submit_answer(self, session_id: str, answer: str) -> Dict[str, Any]:
        if session_id not in SESSION_STORE:
            return {"error": "Invalid session_id"}

        session = SESSION_STORE[session_id]

        if session["step"] == "initial":
            idx = session["current_index"]
            questions = session["questions"]
            current_question = questions[idx]

            session["answers"][current_question] = answer
            session["cv_data"] = self.cv_builder_service.update_from_answer(
                session["cv_data"],
                current_question,
                answer,
            )

            session["current_index"] += 1

            # If the current question was the role question, resolve the role and seed CV data
            if current_question.strip().lower() == "what is your current role/title?":
                role = resolve_role(answer)
                session["role"] = role
                session["cv_data"] = self.cv_builder_service.apply_role_seed(session["cv_data"], answer)

            if session["current_index"] < len(questions):
                return {
                    "session_id": session_id,
                    "question": questions[session["current_index"]],
                    "cv_data": session["cv_data"],
                }

            # Move to role-specific questions after initial onboarding
            role = session.get("role") or resolve_role(answer)
            session["role"] = role
            role_questions = select_questions(role)
            asked_questions = {q.strip().lower() for q in session["answers"].keys()}
            session["questions"] = [q for q in role_questions if q.strip().lower() not in asked_questions]
            session["step"] = "questions"
            session["current_index"] = 0

            if not session["questions"]:
                return {
                    "session_id": session_id,
                    "message": "I have no role-specific questions right now. You can continue by sharing more details or uploading your CV.",
                    "cv_data": session["cv_data"],
                }

            return {
                "session_id": session_id,
                "question": session["questions"][0],
                "cv_data": session["cv_data"],
            }

        if session["step"] == "role":
            role = resolve_role(answer)
            questions = select_questions(role)

            session["role"] = role
            session["questions"] = questions
            session["step"] = "questions"
            session["current_index"] = 0
            session["cv_data"] = self.cv_builder_service.apply_role_seed(session["cv_data"], answer)

            return {
                "session_id": session_id,
                "resolved_role": role,
                "question": questions[0] if questions else "No questions found for this role",
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

            role = session.get("role")
            # LLM should only be used for transcript enhancement, not CV data enhancement
            # CV data updates remain deterministic through cv_builder_service

            analysis = self.answer_analyzer.analyze(current_question, answer, cv_data=session["cv_data"])
            context = self.retrieval_service.get_context(current_question, top_k=3)
            validation = self.validation_service.validate(session["cv_data"])
            followup = self.followup_engine.generate_followup(
                current_question,
                answer,
                role=role,
                analysis=analysis,
                cv_data=session["cv_data"],
            )

            trace = self.langsmith_service.trace(
                "conversation_submit_answer",
                {
                    "session_id": session_id,
                    "question": current_question,
                    "role": role,
                    "analysis": analysis,
                },
            )

            built_schema = self.cv_builder_service.try_build_schema(session["cv_data"])

            if followup:
                return {
                    "session_id": session_id,
                    "followup_question": followup,
                    "cv_data": session["cv_data"],
                    "cv_schema_ready": built_schema is not None,
                    "validation": validation,
                    "retrieved_context": context,
                    "confidence": validation.get("confidence", {}),
                    "trace": trace,
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
                    "confidence": validation.get("confidence", {}),
                    "trace": trace,
                }

            next_question = questions[session["current_index"]]
            return {
                "session_id": session_id,
                "question": next_question,
                "cv_data": session["cv_data"],
                "cv_schema_ready": built_schema is not None,
                "validation": validation,
                "retrieved_context": context,
                "confidence": validation.get("confidence", {}),
                "trace": trace,
            }

        return {"message": "Invalid state"}

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return SESSION_STORE.get(session_id, {"error": "Invalid session_id"})

    def reset_session(self, session_id: str) -> Dict[str, Any]:
        if session_id in SESSION_STORE:
            del SESSION_STORE[session_id]
            return {"message": "Session reset successfully"}
        return {"error": "Invalid session_id"}
