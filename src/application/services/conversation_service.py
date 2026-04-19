from __future__ import annotations

import logging
from typing import Any, Dict
from uuid import uuid4

from src.application.services.cv_builder_service import CVBuilderService
from src.application.services.retrieval_service import RetrievalService
from src.application.services.validation_service import ValidationService
from src.ai.services.llm_enhancement_service import LLMEnhancementService
from src.ai.services.langsmith_service import LangSmithService
from src.ai.services.extraction_service import ExtractionService
from src.core.config.settings import settings
from src.core.i18n import resolve_locale
from src.questionnaire.answer_analyzer import AnswerAnalyzer
from src.questionnaire.followup_engine import FollowupEngine
from src.questionnaire.question_selector import select_initial_questions, select_questions
from src.questionnaire.role_resolver import resolve_role
from src.domain.cv.services.unmapped_data_service import UnmappedDataService
from src.domain.cv.services.canonical_data_staging_service import (
    CanonicalDataStagingService,
)
from src.domain.session import (
    DatabaseSessionRepository,
    FileSessionRepository,
    InMemorySessionRepository,
    SessionService,
    SessionSourceType,
)
from src.infrastructure.persistence.mysql.database import SessionLocal
from src.domain.session.models import CVSession, SessionMetadata


def _build_session_repository():
    backend = (settings.SESSION_REPOSITORY_BACKEND or "memory").strip().lower()
    if backend == "mysql":
        return DatabaseSessionRepository(connection_factory=SessionLocal)
    if backend == "file":
        return FileSessionRepository(root_dir=settings.SESSION_FILE_STORE_PATH)
    return InMemorySessionRepository()


_SESSION_REPOSITORY = _build_session_repository()
_SESSION_SERVICE = SessionService(repository=_SESSION_REPOSITORY)
logger = logging.getLogger(__name__)


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
        self.extraction_service = ExtractionService()
        self.unmapped_service = UnmappedDataService()

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
            "awards": [],
            "unmappedData": {},
            "sourceSnapshots": {},
            "mappingWarnings": [],
        }

    def _preserve_conversation_data_loss_guards(
        self,
        session: Dict[str, Any],
        question: str,
        answer: str,
        extraction_result: Dict[str, Any] | None = None,
    ) -> None:
        canonical_cv = session.get("canonical_cv") or {}
        self.unmapped_service.ensure_sections(canonical_cv)

        self.unmapped_service.preserve_snapshot(
            canonical_cv,
            "conversation",
            {
                "kind": "question_answer",
                "question": question,
                "answer": answer,
            },
        )

        unmapped_answers = (session.get("cv_data") or {}).get("unmapped_answers") or {}
        if unmapped_answers:
            self.unmapped_service.preserve_unmapped(
                canonical_cv,
                "conversation",
                "questionnaire_unmapped_answers",
                unmapped_answers,
            )

        if extraction_result:
            extracted_fields = extraction_result.get("extracted_fields") or {}
            known_extraction_keys = {
                "personal_details",
                "summary",
                "skills",
                "work_experience",
                "project_experience",
                "education",
                "certifications",
            }
            unmapped_top_level = self.unmapped_service.collect_unmapped_top_level(
                extracted_fields,
                known_extraction_keys,
            )
            if unmapped_top_level:
                self.unmapped_service.preserve_unmapped(
                    canonical_cv,
                    "conversation_llm_extraction",
                    "top_level_fields",
                    unmapped_top_level,
                )

            if extraction_result.get("normalized_text"):
                self.unmapped_service.preserve_snapshot(
                    canonical_cv,
                    "conversation_llm_extraction",
                    {
                        "kind": "normalized_text",
                        "text": extraction_result.get("normalized_text"),
                    },
                )

            for warning in extraction_result.get("warnings", []) or []:
                self.unmapped_service.add_mapping_warning(
                    canonical_cv,
                    "conversation_llm_extraction",
                    str(warning),
                    context={"question": question},
                )

        session["canonical_cv"] = canonical_cv

    def start_session(self, locale: str | None = None) -> Dict[str, Any]:
        session_id = str(uuid4())
        resolved_locale = resolve_locale(explicit_locale=locale)
        initial_questions = select_initial_questions(locale=resolved_locale)

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
            "locale": resolved_locale,
        }
        self.save_session(session_id, session_payload)
        return {
            "session_id": session_id,
            "locale": resolved_locale,
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

            self._preserve_conversation_data_loss_guards(
                session,
                current_question,
                answer,
                extraction_result=None,
            )

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
            role_questions = select_questions(role, locale=session.get("locale"))
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
            questions = select_questions(role, locale=session.get("locale"))

            session["role"] = role
            session["questions"] = questions
            session["step"] = "questions"
            session["current_index"] = 0
            session["cv_data"] = self.cv_builder_service.apply_role_seed(session["cv_data"], answer)
            self._update_session_projection(session)
            self._preserve_conversation_data_loss_guards(
                session,
                "What is your current role/title?",
                answer,
                extraction_result=None,
            )

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

            # Optional LLM extraction step (Phase 5)
            # Skip LLM extraction for structured questionnaire questions that already
            # have a deterministic mapper target — the mapper handles these correctly and
            # LLM extraction on neighbouring answers can corrupt already-set skill fields
            # (e.g. tools_and_platforms answer triggering extraction before primary_skills
            # is answered, causing the LLM to pre-populate primary_skills incorrectly).
            _q_is_mapped = (
                current_question.strip().lower()
                in self.cv_builder_service.mapper._mapping
            )
            if _q_is_mapped:
                extraction_result = None
            else:
                session["cv_data"], extraction_result = self._try_apply_extraction(
                    current_question,
                    answer,
                    session["cv_data"],
                )

            role = session.get("role")
            # LLM should only be used for transcript enhancement, not CV data enhancement
            # CV data updates remain deterministic through cv_builder_service

            analysis = self.answer_analyzer.analyze(current_question, answer, cv_data=session["cv_data"])
            context = self.retrieval_service.get_context(current_question, top_k=3)
            validation = self.validation_service.validate(
                session["cv_data"],
                locale=session.get("locale"),
            )
            followup = self.followup_engine.generate_followup(
                current_question,
                answer,
                role=role,
                analysis=analysis,
                cv_data=session["cv_data"],
                locale=session.get("locale"),
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
            self._preserve_conversation_data_loss_guards(
                session,
                current_question,
                answer,
                extraction_result=extraction_result,
            )

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

    def _try_apply_extraction(
        self,
        question: str,
        answer: str,
        cv_data: Dict[str, Any],
    ) -> tuple[Dict[str, Any], Dict[str, Any] | None]:
        """
        Optionally apply LLM extraction to answer and merge results into cv_data.
        
        This is a non-breaking integration point:
        - Only runs if ENABLE_LLM_EXTRACTION is True
        - Only for suitable question types
        - Falls back gracefully if LLM disabled
        - Questionnaire values always take priority
        
        Args:
            question: The question asked
            answer: The user's answer
            cv_data: Current CV data
            
        Returns:
            Tuple of:
            - updated CV data (or unchanged if extraction not applied)
            - extraction result payload (or None)
        """
        if not (settings.ENABLE_LLM_EXTRACTION or settings.ENABLE_LLM_NORMALIZATION):
            return cv_data, None

        if not self.extraction_service.should_extract(question, answer):
            return cv_data, None

        try:
            logger.debug(f"Attempting LLM extraction for question: {question[:50]}...")

            # Extract and merge
            result = self.extraction_service.extract_and_merge(
                raw_text=answer,
                existing_cv_data=cv_data,
                context={"question": question},
                merge_strategy="questionnaire_wins",
            )

            if result.get("success"):
                logger.info(f"LLM extraction successful. Merged {len(result.get('merged_fields', []))} fields.")
                return result["merged_cv_data"], result

            logger.debug("LLM extraction returned empty or failed result")
            return cv_data, result

        except Exception as e:
            logger.error(f"Error during LLM extraction: {e}")
            return cv_data, None

    def get_session(self, session_id: str) -> Dict[str, Any]:
        try:
            persisted = _SESSION_SERVICE.get_latest(session_id)
        except Exception:
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
        expected_version = session_data.get("version") if isinstance(session_data.get("version"), int) else None
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

        try:
            _SESSION_SERVICE.save_workflow_state(
                session_id=session_id,
                workflow_state=workflow_state,
                canonical_cv=session_data.get("canonical_cv"),
                validation_results=session_data.get("validation_results"),
                expected_version=expected_version,
            )
        except Exception:
            # If the session does not exist yet, initialize and persist it.
            metadata_payload = session_data.get("metadata")
            if not isinstance(metadata_payload, dict):
                metadata_payload = {}

            resolved_ui_locale = resolve_locale(
                explicit_locale=session_data.get("locale"),
                session_ui_locale=metadata_payload.get("ui_locale"),
            )
            resolved_content_locale = resolve_locale(
                explicit_locale=metadata_payload.get("content_locale"),
                session_ui_locale=resolved_ui_locale,
            )

            created = _SESSION_SERVICE.initialize_session(
                session_id=session_id,
                canonical_cv=session_data.get("canonical_cv", {}),
                workflow_state=workflow_state,
                metadata=SessionMetadata(
                    user_id=metadata_payload.get("user_id"),
                    tenant_id=metadata_payload.get("tenant_id"),
                    ui_locale=resolved_ui_locale,
                    content_locale=resolved_content_locale,
                    client_app=str(metadata_payload.get("client_app") or ""),
                    tags=metadata_payload.get("tags") if isinstance(metadata_payload.get("tags"), dict) else {},
                ),
            )
            created.validation_results = session_data.get("validation_results", {})
            created.add_source_event(SessionSourceType.MANUAL_EDIT, description="session_create")
            created.touch()
            _SESSION_REPOSITORY.save_session(created)

    def reset_session(self, session_id: str) -> Dict[str, Any]:
        try:
            # Clear staged extraction data from persistence layer
            staging_service = CanonicalDataStagingService()
            cleared_count, marked_count = staging_service.clear_session_staging(session_id)
            logger.info(
                f"Cleared staging data for session {session_id}: "
                f"{cleared_count} records cleared, {marked_count} marked"
            )
            
            # Delete session from repository
            exists = _SESSION_REPOSITORY.get_session(session_id)
            if exists:
                _SESSION_REPOSITORY.delete_session(session_id)
                return {
                    "message": "Session reset successfully",
                    "staging_records_cleared": cleared_count
                }
            return {"error": "Invalid session_id"}
        except Exception as e:
            logger.error(f"Error resetting session {session_id}: {str(e)}")
            return {"error": f"Failed to reset session: {str(e)}"}

    def _to_legacy_dict(self, persisted: CVSession) -> Dict[str, Any]:
        payload = dict(persisted.workflow_state or {})
        payload["session_id"] = persisted.session_id
        payload["canonical_cv"] = persisted.canonical_cv
        payload["validation_results"] = persisted.validation_results
        payload["locale"] = persisted.metadata.ui_locale
        payload["metadata"] = persisted.metadata.model_dump(mode="json")
        payload.setdefault("validation", persisted.validation_results)
        payload.setdefault("review_status", payload.get("review_status", "pending"))
        return payload
