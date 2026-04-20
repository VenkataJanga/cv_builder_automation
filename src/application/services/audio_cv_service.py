"""
Audio CV Service - Phase 3 Audio Integration

Orchestrates audio transcript processing through canonical schema pipeline:
1. Parse enhanced transcript → Canonical CV Schema v1.1
2. Merge with existing canonical CV (preserving rich data)
3. Validate merged result
4. Return canonical CV + validation + eligibility flags

This service connects audio input to Phase 2 infrastructure (SchemaMergeService, SchemaValidationService).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import re

from src.infrastructure.parsers.canonical_audio_parser import CanonicalAudioParser
from src.domain.cv.services.schema_merge_service import SchemaMergeService
from src.domain.cv.services.unmapped_data_service import UnmappedDataService
from src.domain.cv.services.schema_validation_service import SchemaValidationService
from src.domain.cv.enums import SourceType
from src.core.config.settings import settings
from src.core.logging.logger import get_logger

logger = get_logger(__name__)


class AudioCVService:
    """
    Phase 3: Audio integration orchestration service.
    
    Coordinates audio transcript processing through canonical schema pipeline
    using Phase 2 services (merge + validation).
    """

    def __init__(self) -> None:
        self.audio_parser = CanonicalAudioParser()
        self.merge_service = SchemaMergeService()
        self.unmapped_service = UnmappedDataService()
        self.validation_service = SchemaValidationService()
        self._normalization_agent: Optional[Any] = None  # lazy-loaded

    # ------------------------------------------------------------------
    # LLM enrichment helpers (flags-gated, non-destructive)
    # ------------------------------------------------------------------

    def _get_normalization_agent(self) -> Any:
        """Lazy-load NormalizationAgent to avoid circular imports at startup."""
        if self._normalization_agent is None:
            from src.ai.agents.normalization_agent import NormalizationAgent  # noqa: PLC0415
            self._normalization_agent = NormalizationAgent()
        return self._normalization_agent

    def _projects_are_sparse(self, canonical: Dict[str, Any]) -> bool:
        """Return True when the parsed project list is empty or every entry is a stub."""
        projects: List[Dict[str, Any]] = (canonical.get("experience") or {}).get("projects") or []
        if not projects:
            return True
        for proj in projects:
            has_description = bool(
                str(proj.get("projectDescription") or proj.get("description") or "").strip()
            )
            has_responsibilities = bool(proj.get("responsibilities"))
            has_technologies = bool(
                proj.get("toolsUsed") or proj.get("technologies") or proj.get("environment")
            )
            if has_description or has_responsibilities or has_technologies:
                return False
        return True

    def _is_truthy(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict)):
            return bool(value)
        return bool(value)

    def _set_if_missing(self, target: Dict[str, Any], key: str, value: Any) -> None:
        """Write *value* into *target[key]* only when the current value is absent or empty."""
        if self._is_truthy(value) and not self._is_truthy(target.get(key)):
            target[key] = value

    def _map_llm_project_to_canonical(self, proj: Any) -> Optional[Dict[str, Any]]:
        """Map an LLM-returned project dict (any key variant) to canonical format."""
        if not isinstance(proj, dict):
            return None

        project_name = (
            proj.get("projectName") or proj.get("project_name")
            or proj.get("name") or proj.get("title") or ""
        ).strip()
        if not project_name:
            return None

        client = (
            proj.get("clientName") or proj.get("client_name")
            or proj.get("client") or ""
        ).strip() or None

        description = (
            proj.get("projectDescription") or proj.get("project_description")
            or proj.get("description") or ""
        ).strip()

        responsibilities = proj.get("responsibilities") or []
        if isinstance(responsibilities, str):
            responsibilities = [r.strip() for r in responsibilities.split(".") if r.strip()]

        technologies = (
            proj.get("technologies_used") or proj.get("technologies")
            or proj.get("toolsUsed") or []
        )
        if isinstance(technologies, str):
            technologies = [t.strip() for t in technologies.split(",") if t.strip()]

        role = (proj.get("role") or proj.get("designation") or "").strip() or None

        return {
            "projectName": project_name,
            "clientName": client,
            "client": client,
            "role": role,
            "projectDescription": description,
            "description": description,
            "startDate": None,
            "endDate": None,
            "durationMonths": None,
            "toolsUsed": technologies if isinstance(technologies, list) else [],
            "technologies": technologies if isinstance(technologies, list) else [],
            "environment": technologies if isinstance(technologies, list) else [],
            "teamSize": None,
            "responsibilities": responsibilities if isinstance(responsibilities, list) else [],
            "outcomes": [],
            "achievements": [],
        }

    def _enrich_with_llm(
        self, audio_canonical: Dict[str, Any], enhanced_transcript: str
    ) -> Dict[str, Any]:
        """
        Post-parse LLM enrichment (flags-gated, non-destructive).

        Runs NormalizationAgent on the enhanced transcript and conservatively
        fills any fields that the regex parser left empty — deterministic values
        always win; LLM output only fills genuine gaps.
        """
        if not (settings.ENABLE_LLM_EXTRACTION or settings.ENABLE_LLM_NORMALIZATION):
            # Measure 6: Warn when LLM enrichment is disabled so operators know
            # that sparse project/domain data will not be rescued by LLM.
            project_count = len(
                (audio_canonical.get("experience") or {}).get("projects") or []
            )
            logger.warning(
                "CONFIGURATION: ENABLE_LLM_EXTRACTION and ENABLE_LLM_NORMALIZATION are both "
                "False. LLM-based project rescue and role/domain disambiguation are disabled. "
                f"Parsed project count: {project_count}. "
                "Set at least one flag to True to enable full LLM enrichment."
            )
            return audio_canonical

        try:
            agent = self._get_normalization_agent()
            result = agent.normalize_and_extract(
                raw_text=enhanced_transcript,
                context={"source_type": "audio_transcript"},
                use_llm=True,
            )
        except Exception as exc:
            logger.warning(f"LLM enrichment skipped — agent call failed: {exc}")
            return audio_canonical

        extracted = result.get("extracted_fields") or {}
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
            extracted,
            known_extraction_keys,
        )
        if unmapped_top_level:
            self.unmapped_service.preserve_unmapped(
                audio_canonical,
                "audio_llm_extraction",
                "top_level_fields",
                unmapped_top_level,
            )

        normalized_text = result.get("normalized_text")
        if self._is_truthy(normalized_text):
            self.unmapped_service.preserve_snapshot(
                audio_canonical,
                "audio_llm_extraction",
                {
                    "kind": "normalized_text",
                    "text": str(normalized_text),
                },
            )

        for warning in result.get("warnings", []) or []:
            self.unmapped_service.add_mapping_warning(
                audio_canonical,
                "audio_llm_extraction",
                str(warning),
            )

        # --- Candidate fields ---
        candidate = audio_canonical.setdefault("candidate", {})
        pd = extracted.get("personal_details") or {}
        self._set_if_missing(candidate, "fullName", pd.get("full_name"))
        self._set_if_missing(candidate, "email", pd.get("email"))
        self._set_if_missing(candidate, "phoneNumber", pd.get("phone"))
        # Measure 3: Only fill currentDesignation from personal_details.current_title.
        # Never map summary.target_role into currentDesignation — they are distinct fields.
        self._set_if_missing(candidate, "currentDesignation", pd.get("current_title"))
        self._set_if_missing(candidate, "currentOrganization", pd.get("current_organization"))
        self._set_if_missing(candidate, "totalExperienceYears", pd.get("total_experience"))

        summary_obj = extracted.get("summary") or {}
        self._set_if_missing(
            candidate, "summary",
            summary_obj.get("professional_summary") or summary_obj.get("summary")
        )
        # Measure 3: Preserve target_role (desired/future role) in careerObjective —
        # a separate canonical field — so it never collides with currentDesignation.
        llm_target_role = summary_obj.get("target_role")
        if self._is_truthy(llm_target_role):
            self._set_if_missing(candidate, "careerObjective", llm_target_role)

        # --- Skills ---
        skills_obj = audio_canonical.setdefault("skills", {})
        ext_skills = extracted.get("skills") or {}
        self._set_if_missing(
            skills_obj, "primarySkills",
            ext_skills.get("primary_skills") or ext_skills.get("technical_skills")
        )
        self._set_if_missing(skills_obj, "secondarySkills", ext_skills.get("secondary_skills"))

        # --- Projects ---
        experience = audio_canonical.setdefault("experience", {})
        existing_projects: List[Dict[str, Any]] = experience.get("projects") or []
        llm_projects_raw = extracted.get("project_experience") or []

        llm_projects = [
            p for p in (self._map_llm_project_to_canonical(p) for p in llm_projects_raw)
            if p
        ]

        if llm_projects:
            if not existing_projects:
                # Parser produced nothing — take LLM results wholesale.
                experience["projects"] = llm_projects
                logger.info(f"LLM enrichment provided {len(llm_projects)} project(s) (parser had none)")
            else:
                # Fill empty fields in existing projects; add genuinely new ones.
                used_llm_indices: set = set()
                for ex_proj in existing_projects:
                    ex_name = str(ex_proj.get("projectName") or "").lower().strip()
                    for idx, llm_proj in enumerate(llm_projects):
                        if idx in used_llm_indices:
                            continue
                        llm_name = str(llm_proj.get("projectName") or "").lower().strip()
                        if ex_name and llm_name and (
                            ex_name in llm_name or llm_name in ex_name
                        ):
                            self._set_if_missing(ex_proj, "clientName", llm_proj.get("clientName"))
                            self._set_if_missing(ex_proj, "client", llm_proj.get("client"))
                            self._set_if_missing(ex_proj, "projectDescription", llm_proj.get("projectDescription"))
                            self._set_if_missing(ex_proj, "description", llm_proj.get("description"))
                            self._set_if_missing(ex_proj, "role", llm_proj.get("role"))
                            if not self._is_truthy(ex_proj.get("responsibilities")):
                                self._set_if_missing(ex_proj, "responsibilities", llm_proj.get("responsibilities"))
                            if not self._is_truthy(ex_proj.get("toolsUsed")):
                                self._set_if_missing(ex_proj, "toolsUsed", llm_proj.get("toolsUsed"))
                                self._set_if_missing(ex_proj, "technologies", llm_proj.get("technologies"))
                                self._set_if_missing(ex_proj, "environment", llm_proj.get("environment"))
                            used_llm_indices.add(idx)
                            break

                for idx, llm_proj in enumerate(llm_projects):
                    if idx not in used_llm_indices:
                        existing_projects.append(llm_proj)

                experience["projects"] = existing_projects
                logger.info(
                    f"LLM enrichment applied to {len(used_llm_indices)} project(s); "
                    f"added {len(llm_projects) - len(used_llm_indices)} new project(s)"
                )

        # --- Education ---
        if not self._is_truthy(audio_canonical.get("education")):
            llm_edu = extracted.get("education") or []
            if self._is_truthy(llm_edu):
                audio_canonical["education"] = llm_edu
                logger.info(f"LLM enrichment provided {len(llm_edu)} education entry/entries")

        # --- Certifications ---
        if not self._is_truthy(audio_canonical.get("certifications")):
            llm_certs = extracted.get("certifications") or []
            if self._is_truthy(llm_certs):
                audio_canonical["certifications"] = llm_certs

        audio_canonical.setdefault("metadata", {})["llmAudioEnrichment"] = {
            "applied": True,
            "source": result.get("source", "unknown"),
        }
        return audio_canonical

    def _is_generic_name(self, name: str) -> bool:
        candidate = str(name or "").strip().lower()
        if not candidate:
            return False
        blocked = {
            "thank you",
            "thanks",
            "thankyou",
            "hello",
            "hi",
            "good morning",
            "good evening",
        }
        return candidate in blocked

    def _is_low_signal_transcript(self, transcript: str) -> bool:
        text = str(transcript or "").strip().lower()
        if not text:
            return True

        words = re.findall(r"[a-z]+", text)
        if not words:
            return True

        filler = {
            "um", "uh", "ah", "hmm", "like", "you", "know", "so", "okay", "ok",
            "and", "the", "a", "an", "to", "is", "are", "was", "were", "i", "we",
            "me", "my", "our", "it", "this", "that", "have", "has", "had", "do", "did",
            "can", "could", "would", "should", "please", "thank", "thanks"
        }
        informative_words = [w for w in words if w not in filler]
        return len(informative_words) < 8

    def _has_meaningful_cv_content(self, cv: Dict[str, Any]) -> bool:
        doc = cv or {}
        candidate = doc.get("candidate") or {}
        experience = doc.get("experience") or {}

        has_identity = any([
            str(candidate.get("fullName") or "").strip(),
            str(candidate.get("email") or "").strip(),
            str(candidate.get("phoneNumber") or "").strip(),
            str(candidate.get("portalId") or "").strip(),
        ])
        has_profile = any([
            str(candidate.get("summary") or "").strip(),
            str(candidate.get("currentDesignation") or "").strip(),
            str(candidate.get("currentOrganization") or "").strip(),
        ])
        has_history = any([
            len(doc.get("education") or []) > 0,
            len(experience.get("projects") or []) > 0,
            len(experience.get("workHistory") or []) > 0,
            len(doc.get("certifications") or []) > 0,
        ])
        return bool(has_identity or has_profile or has_history)

    def process_audio_transcript(
        self,
        enhanced_transcript: str,
        existing_canonical_cv: Dict[str, Any],
        source_type: SourceType = SourceType.AUDIO_RECORDING,
    ) -> Dict[str, Any]:
        """
        Process enhanced audio transcript into canonical CV with merge and validation.

        Args:
            enhanced_transcript: LLM-enhanced transcript with structured sections
            existing_canonical_cv: Current canonical CV from session (may be empty)
            source_type: Audio source (AUDIO_RECORDING or AUDIO_UPLOAD)

        Returns:
            {
                "canonical_cv": dict,  # Merged canonical CV
                "validation": dict,    # Validation result
                "can_save": bool,      # Whether CV can be saved
                "can_export": bool,    # Whether CV can be exported
                "audio_extraction": dict  # Raw audio extraction (for debugging)
            }

        Raises:
            ValueError: If transcript is empty or invalid
        """
        if not enhanced_transcript or not enhanced_transcript.strip():
            raise ValueError("Enhanced transcript cannot be empty")

        # Step 1: Parse audio transcript → Canonical CV Schema v1.1
        logger.info("=" * 80)
        logger.info("AUDIO CV SERVICE - Starting transcript processing")
        logger.info(f"Transcript length: {len(enhanced_transcript)} chars")
        logger.info(f"Transcript preview: {enhanced_transcript[:200]}...")
        
        audio_canonical = self.audio_parser.parse(enhanced_transcript)
        self.unmapped_service.preserve_snapshot(
            audio_canonical,
            "audio_transcript",
            {
                "kind": "enhanced_transcript",
                "text": enhanced_transcript,
                "sourceType": source_type.value,
            },
        )
        
        logger.info("Audio parsing complete")
        logger.info(f"  - Top-level keys: {list(audio_canonical.keys())}")
        logger.info(f"  - Candidate name: {audio_canonical.get('candidate', {}).get('fullName', 'NOT SET')}")
        logger.info(f"  - Education count: {len(audio_canonical.get('education', []))}")
        logger.info(f"  - Projects count: {len((audio_canonical.get('experience') or {}).get('projects', []))}")
        logger.info(f"  - Skills count: {len(audio_canonical.get('skills', []))}")

        # Step 1b: LLM enrichment — fills fields the regex parser left empty.
        # Runs only when ENABLE_LLM_EXTRACTION or ENABLE_LLM_NORMALIZATION is True.
        # Always runs a spareness check so enrichment is skipped when parsing succeeded.
        if self._projects_are_sparse(audio_canonical):
            logger.info("Projects are sparse after regex parsing — attempting LLM enrichment")
            audio_canonical = self._enrich_with_llm(audio_canonical, enhanced_transcript)
            logger.info(
                f"  - Projects after enrichment: "
                f"{len((audio_canonical.get('experience') or {}).get('projects', []))}"
            )
        else:
            # Even when projects exist, fill other missing top-level fields via LLM.
            audio_canonical = self._enrich_with_llm(audio_canonical, enhanced_transcript)

        candidate = audio_canonical.get("candidate") or {}
        if self._is_generic_name(candidate.get("fullName", "")):
            candidate["fullName"] = ""
            audio_canonical["candidate"] = candidate
            logger.info("Sanitized generic candidate name extracted from low-quality transcript")
        
        # Ensure sourceType is set for merge precedence rules
        audio_canonical["sourceType"] = source_type.value
        if "metadata" not in audio_canonical:
            audio_canonical["metadata"] = {}
        audio_canonical["metadata"]["lastModifiedAt"] = datetime.now(timezone.utc).isoformat()

        # Step 2: Merge with existing canonical CV (Phase 2 service)
        # This preserves rich project descriptions and prevents empty overwrites
        logger.info(f"Starting merge with existing CV (has {len(existing_canonical_cv)} top-level keys)")
        
        existing_has_data = self._has_meaningful_cv_content(existing_canonical_cv)
        new_has_data = self._has_meaningful_cv_content(audio_canonical)
        low_signal = self._is_low_signal_transcript(enhanced_transcript)

        skipped_due_to_quality = False
        if low_signal and not new_has_data and existing_has_data:
            logger.warning(
                "Low-signal audio transcript detected with no meaningful CV extraction; preserving existing canonical CV"
            )
            merged_canonical = existing_canonical_cv
            skipped_due_to_quality = True
        else:
            merged_canonical = self.merge_service.merge_canonical_cvs(
                existing_cv=existing_canonical_cv,
                new_data=audio_canonical,
                source_type=source_type,
                operation="audio_merge"
            )
        
        logger.info("Merge complete")
        logger.info(f"  - Merged CV has {len(merged_canonical)} top-level keys")
        logger.info(f"  - Candidate name after merge: {merged_canonical.get('candidate', {}).get('fullName', 'NOT SET')}")

        # Step 3: Validate merged canonical CV (Phase 2 service)
        # Use save_and_validate for audio operations to get comprehensive feedback
        validation_result_obj = self.validation_service.validate_for_save_and_validate(merged_canonical)
        validation_result = validation_result_obj.to_dict()
        
        logger.info("Validation complete")
        logger.info(f"  - Can save: {validation_result['can_save']}")
        logger.info(f"  - Can export: {validation_result['can_export']}")
        logger.info("=" * 80)

        return {
            "canonical_cv": merged_canonical,
            "validation": validation_result,
            "can_save": validation_result["can_save"],
            "can_export": validation_result["can_export"],
            "audio_extraction": audio_canonical,  # Raw extraction for debugging
            "audio_quality_warning": (
                "Low-quality transcript detected. Existing CV data was kept unchanged. "
                "Please re-record with clear, specific CV details."
                if skipped_due_to_quality
                else (
                    "Low-quality transcript detected. Extracted CV details may be incomplete. "
                    "Please re-record with clear, specific CV details."
                    if low_signal and not new_has_data
                    else None
                )
            ),
        }
