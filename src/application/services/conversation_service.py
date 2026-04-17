from __future__ import annotations

from typing import Any, Dict
from uuid import uuid4

from src.application.services.cv_builder_service import CVBuilderService
from src.application.services.retrieval_service import RetrievalService
from src.application.services.validation_service import ValidationService
from src.ai.services.llm_enhancement_service import LLMEnhancementService
from src.ai.services.langsmith_service import LangSmithService
from src.core.config.settings import settings
from src.questionnaire.answer_analyzer import AnswerAnalyzer
from src.questionnaire.followup_engine import FollowupEngine
from src.questionnaire.question_selector import select_initial_questions, select_questions
from src.questionnaire.role_resolver import resolve_role
from src.domain.session import (
    DatabaseSessionRepository,
    FileSessionRepository,
    InMemorySessionRepository,
    SessionService,
    SessionSourceType,
)
from src.infrastructure.persistence.mysql.database import SessionLocal
from src.domain.session.models import CVSession


def _build_session_repository():
    backend = (settings.SESSION_REPOSITORY_BACKEND or "memory").strip().lower()
    if backend == "mysql":
        return DatabaseSessionRepository(connection_factory=SessionLocal)
    if backend == "file":
        return FileSessionRepository(root_dir=settings.SESSION_FILE_STORE_PATH)
    return InMemorySessionRepository()


_SESSION_REPOSITORY = _build_session_repository()
_SESSION_SERVICE = SessionService(repository=_SESSION_REPOSITORY)


def get_session_persistence_service() -> SessionService:
    """Expose singleton session persistence service for routers/services."""
    return _SESSION_SERVICE


class ConversationService:
    def __init__(self) -> None:
        self.cv_builder_service = CVBuilderService()
        self.answer_analyzer = AnswerAnalyzer()
        self.followup_engine = FollowupEngine()
        self.retrieval_service = RetrievalService()
        self.validation_service = ValidationService()
        self.enhancement_service = LLMEnhancementService()
        self.langsmith_service = LangSmithService()

    def _update_session_projection(
        self,
        session: Dict[str, Any],
        validation: Dict[str, Any] | None = None,
    ) -> Any:
        """Project questionnaire cv_data into canonical_cv for preview/export consumers."""
        partial_schema = self.cv_builder_service.build_partial_schema(session.get("cv_data", {}))
        session["canonical_cv"] = partial_schema.model_dump()
        built_schema = self.cv_builder_service.try_build_schema(session.get("cv_data", {}))
        if validation is not None:
            session["validation_results"] = validation
            session["validation"] = validation
        return built_schema

    def _get_empty_canonical_schema(self) -> Dict[str, Any]:
        """
        Phase 4: Return empty Canonical CV Schema v1.1 for new sessions.
        
        This is the single source of truth for CV data.
        Legacy cv_data maintained for backward compatibility during migration.
        """
        return {
            "schemaVersion": "1.1.0",
            "sourceType": "new_session",
            "metadata": {
                "createdAt": None,
                "lastModifiedAt": None,
                "completenessScore": 0.0,
                "dataQuality": {
                    "overall": "incomplete",
                    "missingMandatoryFields": [],
                    "weakFields": []
                }
            },
            "candidate": {
                "personalInfo": {
                    "fullName": None,
                    "email": None,
                    "phone": None,
                    "location": {
                        "city": None,
                        "state": None,
                        "country": None
                    },
                    "linkedIn": None,
                    "github": None,
                    "portfolio": None
                },
                "professionalSummary": None,
                "currentRole": None,
                "yearsOfExperience": None
            },
            "skills": {
                "technical": [],
                "soft": [],
                "languages": [],
                "tools": []
            },
            "experience": {
                "projects": [],
                "roles": []
            },
            "education": [],
            "certifications": [],
            "publications": [],
            "awards": []
        }

    def start_session(self) -> Dict[str, Any]:
        session_id = str(uuid4())
        initial_questions = select_initial_questions()

        session_payload = {
            "session_id": session_id,
            "step": "initial",
            "role": None,
            "answers": {},
            "questions": initial_questions,
            "current_index": 0,
            "cv_data": self.cv_builder_service.initialize_cv_data(),  # Legacy format (backward compatibility)
            "canonical_cv": self._get_empty_canonical_schema(),  # Phase 4: Canonical CV Schema v1.1 (source of truth)
            "review_status": "pending",  # pending | in_progress | completed
            "has_user_edits": False,  # Track if user has made manual edits via review endpoint
            "validation_results": {},  # Phase 4: Store SchemaValidationService results (can_export, errors, warnings)
        }
        self.save_session(session_id, session_payload)
        return {
            "session_id": session_id,
            "question": initial_questions[0] if initial_questions else "What is your full name?",
        }

    def submit_answer(self, session_id: str, answer: str) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if "error" in session:
            return {"error": "Invalid session_id"}

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
            self._update_session_projection(session)

            session["current_index"] += 1

            # If the current question was the role question, resolve the role and seed CV data
            if current_question.strip().lower() == "what is your current role/title?":
                role = resolve_role(answer)
                session["role"] = role
                session["cv_data"] = self.cv_builder_service.apply_role_seed(session["cv_data"], answer)
                self._update_session_projection(session)

            if session["current_index"] < len(questions):
                self.save_session(session_id, session)
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
                self.save_session(session_id, session)
                return {
                    "session_id": session_id,
                    "message": "I have no role-specific questions right now. You can continue by sharing more details or uploading your CV.",
                    "cv_data": session["cv_data"],
                }

            self.save_session(session_id, session)
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
            self._update_session_projection(session)

            self.save_session(session_id, session)
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

            built_schema = self._update_session_projection(session, validation)

            if followup:
                self.save_session(session_id, session)
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
                self.save_session(session_id, session)
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
            self.save_session(session_id, session)
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
        persisted = _SESSION_REPOSITORY.get_session(session_id)
        if not persisted:
            return {"error": "Invalid session_id"}
        return self._to_legacy_dict(persisted)

    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """
        Phase 4: Save or update session data in the store.
        
        Used by external services to persist changes:
        - /cv/save endpoint updates canonical_cv and validation_results
        - /cv/validate endpoint updates validation_results
        - Review endpoint updates review metadata
        
        canonical_cv is the single source of truth for all reads (preview, edit, export).
        """
        existing = _SESSION_REPOSITORY.get_session(session_id)

        workflow_state = {
            k: v
            for k, v in (session_data or {}).items()
            if k not in {
                "session_id",
                "canonical_cv",
                "validation_results",
                "status",
                "created_at",
                "last_updated_at",
                "exported_at",
                "expires_at",
                "source_history",
                "uploaded_artifacts",
                "metadata",
                "version",
            }
        }

        if existing:
            existing.canonical_cv = session_data.get("canonical_cv", existing.canonical_cv)
            existing.validation_results = session_data.get("validation_results", existing.validation_results)
            existing.workflow_state = workflow_state
            existing.add_source_event(SessionSourceType.MANUAL_EDIT, description="session_save")
            existing.touch()
            _SESSION_REPOSITORY.save_session(existing)
        else:
            created = _SESSION_SERVICE.initialize_session(
                session_id=session_id,
                canonical_cv=session_data.get("canonical_cv", {}),
            )
            created.validation_results = session_data.get("validation_results", {})
            created.workflow_state = workflow_state
            created.add_source_event(SessionSourceType.MANUAL_EDIT, description="session_create")
            created.touch()
            _SESSION_REPOSITORY.save_session(created)

    def reset_session(self, session_id: str) -> Dict[str, Any]:
        exists = _SESSION_REPOSITORY.get_session(session_id)
        if exists:
            _SESSION_REPOSITORY.delete_session(session_id)
            return {"message": "Session reset successfully"}
        return {"error": "Invalid session_id"}

    def _to_legacy_dict(self, persisted: CVSession) -> Dict[str, Any]:
        payload = dict(persisted.workflow_state or {})
        payload["session_id"] = persisted.session_id
        payload["canonical_cv"] = persisted.canonical_cv
        payload["validation_results"] = persisted.validation_results
        payload.setdefault("validation", persisted.validation_results)
        payload.setdefault("review_status", payload.get("review_status", "pending"))
        return payload
