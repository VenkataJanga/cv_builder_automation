"""
Preview Service - Phase 4: Canonical CV Only

This service handles CV data preview generation exclusively from the Canonical CV Schema.
All preview operations read from canonical_cv only.
"""

import logging
from typing import Dict, Any, Optional

from src.ai.agents.cv_formatting_agent import CVFormattingAgent
from src.domain.cv.models.canonical_cv_schema import CanonicalCVSchema
from src.domain.cv.services.canonical_data_staging_service import (
    CanonicalDataStagingService,
)

logger = logging.getLogger(__name__)

_INVALID_LOCATION_VALUES = {
    "and",
    "na",
    "n/a",
    "none",
    "none, none",
    "none, none, none",
    "null",
    "undefined",
    "nil",
    "unknown",
    "not available",
    "not applicable",
}

_INVALID_PROJECT_NAMES = {
    "operating",
    "operating system",
    "operating systems",
    "current role",
    "project experience",
    "responsibilities",
    "education",
    "skills",
    "summary",
}


class PreviewService:
    """
    Service for generating CV previews from Canonical CV Schema
    
    Phase 4: This service reads exclusively from canonical_cv.
    No fallbacks to cv_data or legacy formats.
    """
    
    def __init__(self) -> None:
        self.formatter = CVFormattingAgent()
        self.staging_service = CanonicalDataStagingService()
        self.logger = logging.getLogger(__name__)
    
    def build_preview_from_canonical(self, canonical_data: Dict[str, Any]) -> dict:
        """
        Build CV preview from Canonical CV Schema (Phase 4: Canonical-only).

        Measure 5: Before converting, runs a field-level completeness gate that
        checks critical sections (currentDesignation, experience.projects,
        experience.domainExperience, education).  When a critical section is empty
        but a richer version exists in sourceSnapshots, the richer version is
        restored so the preview is never blank for fields that were once populated.
        """
        if not canonical_data:
            self.logger.error("Cannot build preview: canonical_data is None")
            raise ValueError("Canonical CV data is required for preview generation")

        # Measure 5: restore critical fields from sourceSnapshots when they are empty.
        canonical_data = self._restore_critical_fields_from_snapshots(canonical_data)

        try:
            # Convert dict to CanonicalCVSchema if needed
            canonical_schema = None
            if isinstance(canonical_data, dict):
                try:
                    canonical_schema = CanonicalCVSchema(**canonical_data)
                except Exception as ex:
                    self.logger.warning(
                        "Canonical CV validation failed; falling back to dict-based preview conversion. "
                        f"Validation error: {ex}"
                    )
            else:
                canonical_schema = canonical_data

            preview_source = canonical_schema if canonical_schema is not None else canonical_data
            if isinstance(canonical_data, dict) and canonical_schema is not None:
                # Preserve non-schema compatibility keys from the raw dict for defensive preview fallbacks.
                preview_source = {**canonical_schema.model_dump(), **canonical_data}
            cv_id = (
                getattr(preview_source, "cvId", None)
                if not isinstance(preview_source, dict)
                else preview_source.get("cvId")
            ) or "unknown"
            self.logger.info(f"Building CV preview from canonical schema (cv_id: {cv_id})")
            self.logger.info(
                "Canonical preview input details: "
                f"portalId={self._get_value(preview_source, 'candidate', 'portalId') or 'NOT SET'} "
                f"email={self._get_value(preview_source, 'candidate', 'email') or 'NOT SET'} "
                f"currentDesignation={self._get_value(preview_source, 'candidate', 'currentDesignation') or 'NOT SET'} "
                f"education_count={len(self._get_value(preview_source, 'education') or [])} "
                f"project_count={len(self._get_value(preview_source, 'experience', 'projects') or [])}"
            )

            # Convert canonical schema to formatter-compatible format
            formatted_data = self._convert_canonical_to_formatter_format(preview_source)

            # Generate preview using formatter
            preview = self.formatter.format_cv(formatted_data)

            self.logger.info(
                "Successfully generated CV preview from canonical schema: "
                f"preview_keys={[k for k in preview.keys()] if isinstance(preview, dict) else 'unknown'} "
                f"formatted_keys={[k for k in formatted_data.keys()]}"
            )
            return preview

        except Exception as e:
            self.logger.error(f"Error building CV preview from canonical schema: {str(e)}", exc_info=True)
            raise

    def _restore_critical_fields_from_snapshots(
        self, canonical_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Measure 5: Field-level completeness gate.

        For each critical section, if the live canonical value is empty but a
        richer version is available in sourceSnapshots, restore it and log a warning.
        This prevents a chat turn (which rebuilds canonical_cv from the thin
        questionnaire) from producing a blank preview for fields that the audio or
        document pipeline already populated.
        """
        if not isinstance(canonical_data, dict):
            return canonical_data

        from copy import deepcopy as _deepcopy
        cv = _deepcopy(canonical_data)
        snapshots = cv.get("sourceSnapshots") or {}

        # Helper: get the richest snapshot value for a given key across all snapshot entries.
        def _best_from_snapshots(snapshot_key: str, sub_key: Optional[str] = None):
            """Return the first non-empty value found in any snapshot under snapshot_key."""
            for _snap_name, snap_val in snapshots.items():
                if not isinstance(snap_val, dict):
                    continue
                val = snap_val.get(snapshot_key)
                if val is None:
                    continue
                if sub_key:
                    val = val.get(sub_key) if isinstance(val, dict) else None
                if val not in (None, "", [], {}):
                    return val
            return None

        candidate = cv.setdefault("candidate", {})
        experience = cv.setdefault("experience", {})

        # 1. currentDesignation
        if not (candidate.get("currentDesignation") or "").strip():
            restored = _best_from_snapshots("candidate", "currentDesignation")
            if restored:
                candidate["currentDesignation"] = restored
                self.logger.warning(
                    "Measure5: restored candidate.currentDesignation from sourceSnapshots"
                )

        # 2. experience.projects
        if not (experience.get("projects") or []):
            # Check the audio_transcript snapshot for projects stored directly
            for snap_name, snap_val in snapshots.items():
                if not isinstance(snap_val, dict):
                    continue
                snap_exp = snap_val.get("experience") or {}
                snap_projects = snap_exp.get("projects") or []
                if snap_projects:
                    experience["projects"] = snap_projects
                    self.logger.warning(
                        f"Measure5: restored experience.projects from sourceSnapshots[{snap_name!r}]"
                    )
                    break

        # 3. experience.domainExperience
        if not (experience.get("domainExperience") or []):
            for snap_name, snap_val in snapshots.items():
                if not isinstance(snap_val, dict):
                    continue
                snap_exp = snap_val.get("experience") or {}
                snap_domains = snap_exp.get("domainExperience") or []
                if snap_domains:
                    experience["domainExperience"] = snap_domains
                    self.logger.warning(
                        f"Measure5: restored experience.domainExperience from sourceSnapshots[{snap_name!r}]"
                    )
                    break

        # 4. education
        if not (cv.get("education") or []):
            for snap_name, snap_val in snapshots.items():
                if not isinstance(snap_val, dict):
                    continue
                snap_edu = snap_val.get("education") or []
                if snap_edu:
                    cv["education"] = snap_edu
                    self.logger.warning(
                        f"Measure5: restored education from sourceSnapshots[{snap_name!r}]"
                    )
                    break

        cv["experience"] = experience
        return cv
    
    def build_preview_from_staging(
        self, 
        session_id: str,
        extraction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build CV preview from staged extraction data.
        
        Retrieves canonical CV from persistent staging layer and generates preview.
        Marks extraction as previewed in staging for audit trail.
        
        Args:
            session_id: User session ID
            extraction_id: Optional specific extraction to use (latest if not provided)
            
        Returns:
            Formatted CV preview data
            
        Raises:
            ValueError: If no staged extraction found
        """
        canonical_cv = self.staging_service.get_canonical_cv_from_staging(
            session_id=session_id, extraction_id=extraction_id
        )
        
        if not canonical_cv:
            self.logger.error(f"No staged extraction found for session {session_id}")
            raise ValueError(f"No staged extraction found for session {session_id}")
        
        # Mark as previewed if extraction_id is known
        if extraction_id:
            self.staging_service.mark_previewed(extraction_id)
        
        # Build preview from canonical
        return self.build_preview_from_canonical(canonical_cv)
    
    def _convert_canonical_to_formatter_format(self, canonical_data: CanonicalCVSchema) -> dict:
        """
        Convert canonical schema to format expected by CV formatter
        
        Args:
            canonical_data: CanonicalCVSchema instance
            
        Returns:
            Dictionary in formatter-compatible format
        """
        try:
            canonical_dict = canonical_data if isinstance(canonical_data, dict) else canonical_data.model_dump()
            candidate = self._to_dict(canonical_dict.get("candidate", {}))
            candidate_personal_info = self._to_dict(
                candidate.get("personalInfo")
                or candidate.get("personal_info")
                or candidate.get("personalDetails")
                or {}
            )
            skills = self._to_dict(canonical_dict.get("skills", {}))
            experience = self._to_dict(canonical_dict.get("experience", {}))
            personal_details = self._to_dict(canonical_dict.get("personalDetails", {}))
            skills_catalog = self._to_dict((canonical_dict.get("unmappedData") or {}).get("skillsCatalog", {}))

            def candidate_field(*keys):
                for key in keys:
                    value = candidate.get(key)
                    if value not in [None, ""]:
                        return value
                    value = candidate_personal_info.get(key)
                    if value not in [None, ""]:
                        return value
                return None

            candidate_location = self._to_dict(
                candidate_field("currentLocation", "location", "current_location") or {}
            )
            candidate_email = candidate_field("email", "emailAddress", "email_address") or ""
            candidate_portal_id = (
                candidate_field("portalId", "portal_id", "employee_id", "portal_id", "employeeId")
                or ""
            )
            current_title = self._sanitize_current_title(
                candidate_field("currentDesignation", "designation", "currentRole", "current_role", "title") or ""
            )
            total_experience = candidate_field(
                "totalExperienceYears",
                "yearsOfExperience",
                "total_experience",
                "experienceYears",
            )
            total_experience_str = (
                f"{total_experience} years"
                if isinstance(total_experience, (int, float))
                else str(total_experience or "")
            )
            domain_expertise = self._extract_domain_expertise(experience, skills, canonical_dict)
            summary_text = (
                candidate_field("summary", "professionalSummary", "careerObjective", "career_objective")
                or canonical_dict.get("summary")
                or self._build_summary_fallback(candidate)
                or self._build_summary_fallback(candidate_personal_info)
            )

            if not summary_text:
                summary_text = self._build_summary_fallback(
                    {
                        "designation": candidate_field(
                            "currentDesignation", "designation", "currentRole", "current_role", "title"
                        ),
                        "totalExperienceYears": total_experience,
                        "currentOrganization": candidate_field(
                            "currentOrganization", "current_organization", "organization"
                        ),
                    }
                )

            formatted_data = {
                "header": {
                    "full_name": candidate_field("fullName", "firstName", "name", "full_name") or "",
                    "current_title": current_title,
                    "location": self._format_location(candidate_location),
                    "current_organization": candidate_field("currentOrganization", "current_organization", "organization") or "",
                    "total_experience": total_experience_str,
                    "email": candidate_email,
                    "contact_number": candidate_field("phoneNumber", "phone", "contact_number") or "",
                    "employee_id": candidate_portal_id,
                    "portal_id": candidate_portal_id,
                    "phone": candidate_field("phoneNumber", "phone", "contact_number") or "",
                    "grade": candidate_field("currentGrade", "grade") or "",
                },
                "personal_details": {
                    "full_name": candidate_field("fullName", "firstName", "name", "full_name") or "",
                    "current_title": current_title,
                    "total_experience": float(total_experience)
                    if isinstance(total_experience, (int, float))
                    else (float(total_experience) if str(total_experience).isdigit() else 0.0),
                    "current_organization": candidate_field("currentOrganization", "current_organization", "organization") or "",
                    "location": self._format_location(candidate_location) or personal_details.get("location", ""),
                    "email": candidate_email,
                    "phone": candidate_field("phoneNumber", "phone", "contact_number") or "",
                    "linkedin": personal_details.get("linkedinUrl", "")
                    or candidate_field("linkedIn", "linkedinUrl", "linkedin")
                    or "",
                    "grade": candidate_field("currentGrade", "grade") or "",
                },
                "summary": {
                    "professional_summary": summary_text,
                    "target_role": candidate_field("careerObjective", "career_objective", "targetRole") or "",
                },
                "skills": {
                    "primary_skills": skills.get("primarySkills", []),
                    "secondary_skills": skills.get("secondarySkills", []),
                    "tools_and_platforms": skills.get("toolsAndPlatforms", []),
                    "domain_expertise": domain_expertise,
                    "development_tools": self._to_list(skills_catalog.get("developmentTools")),
                    "crm_tools": self._to_list(skills_catalog.get("crmTools")),
                    "database_connectivity": self._to_list(skills_catalog.get("databaseConnectivity")),
                    "sql_skills": self._to_list(skills_catalog.get("sqlSkills")),
                    "erp": self._to_list(skills_catalog.get("erp")),
                    "legacy_systems": self._to_list(skills_catalog.get("legacySystems")),
                    "networking": self._to_list(skills_catalog.get("networking")),
                    "testing_tools": self._to_list(skills_catalog.get("testingTools")),
                    "documentation": self._to_list(skills_catalog.get("documentation")),
                    "configuration_management": self._to_list(skills_catalog.get("configurationManagement")),
                    "client_server_technologies": self._to_list(skills_catalog.get("clientServerTechnologies")),
                    "foreign_language_known": self._to_list(skills_catalog.get("foreignLanguageKnown")),
                },
                "tools_and_platforms": skills.get("toolsAndPlatforms", []),
                "ai_frameworks": skills.get("aiToolsAndFrameworks", []),
                "cloud_platforms": skills.get("cloudTechnologies", []),
                "operating_systems": skills.get("operatingSystems", []),
                "databases": skills.get("databases", []),
                "domain_expertise": domain_expertise,
                "development_tools": self._to_list(skills_catalog.get("developmentTools")),
                "crm_tools": self._to_list(skills_catalog.get("crmTools")),
                "database_connectivity": self._to_list(skills_catalog.get("databaseConnectivity")),
                "sql_skills": self._to_list(skills_catalog.get("sqlSkills")),
                "erp": self._to_list(skills_catalog.get("erp")),
                "legacy_systems": self._to_list(skills_catalog.get("legacySystems")),
                "networking": self._to_list(skills_catalog.get("networking")),
                "testing_tools": self._to_list(skills_catalog.get("testingTools")),
                "documentation": self._to_list(skills_catalog.get("documentation")),
                "configuration_management": self._to_list(skills_catalog.get("configurationManagement")),
                "client_server_technologies": self._to_list(skills_catalog.get("clientServerTechnologies")),
                "foreign_language_known": self._to_list(skills_catalog.get("foreignLanguageKnown")),
                "secondary_skills": skills.get("secondarySkills", []),
                "employment": {
                    "current_employer": candidate_field("currentOrganization", "current_organization", "organization") or "",
                    "total_experience": total_experience_str,
                },
                "project_experience": self._convert_projects_to_formatter_format(experience.get("projects", [])),
                "education": self._convert_education_to_formatter_format(canonical_dict.get("education", [])),
                "work_experience": self._convert_work_history_to_formatter_format(experience.get("workHistory", [])),
                "certifications": self._convert_certifications_to_formatter_format(canonical_dict.get("certifications", [])),
                "achievements": self._convert_achievements_to_formatter_format(canonical_dict.get("achievements", [])),
                "languages": self._to_list(personal_details.get("languagesKnown") or canonical_dict.get("languages")),
                "schema_version": canonical_dict.get("schema_version", "") or canonical_dict.get("schemaVersion", ""),
                "target_role": candidate_field("careerObjective", "career_objective", "targetRole") or "",
            }

            unmapped_data = canonical_dict.get("unmappedData", {})
            role_details: dict[str, Any] = {}
            if isinstance(unmapped_data, dict):
                for section_name, section_value in unmapped_data.items():
                    if section_name in {"unmapped_answers", "attributes", "skillsCatalog"}:
                        continue

                    if isinstance(section_value, dict):
                        for field_name, field_value in section_value.items():
                            if field_value in (None, "", [], {}):
                                continue
                            label = field_name if section_name == "leadership" else f"{section_name}_{field_name}"
                            role_details[label] = field_value
                    elif section_value not in (None, "", [], {}):
                        role_details[section_name] = section_value

            if role_details:
                formatted_data["leadership"] = role_details

            # Surface structured Others contract for UI review panels.
            attributes = unmapped_data.get("attributes") if isinstance(unmapped_data, dict) else []
            if isinstance(attributes, list) and attributes:
                formatted_data["unmapped_attributes"] = attributes

            return formatted_data

        except Exception as e:
            self.logger.error(f"Error converting canonical data to formatter format: {str(e)}")
            return {}
    
    def _convert_projects_to_formatter_format(self, projects) -> list:
        """Convert canonical projects to formatter format"""
        formatter_projects = []
        for project in projects:
            project_dict = self._to_dict(project)
            if self._is_placeholder_project(project_dict):
                continue
            formatter_project = {
                "project_name": project_dict.get("projectName", "") or project_dict.get("name", ""),
                "client_name": project_dict.get("clientName", "") or project_dict.get("client", ""),
                "role": project_dict.get("role", ""),
                "duration": self._format_project_duration(project_dict),
                "team_size": project_dict.get("teamSize") or project_dict.get("team_size"),
                "technologies": self._to_list(project_dict.get("toolsUsed") or project_dict.get("technologies") or project_dict.get("environment")),
                "responsibilities": self._to_list(project_dict.get("responsibilities")),
                "outcomes": self._to_list(project_dict.get("outcomes")),
                "description": project_dict.get("projectDescription", "") or project_dict.get("description", "")
            }
            formatter_projects.append(formatter_project)
        return formatter_projects

    def _is_placeholder_project(self, project_dict: Dict[str, Any]) -> bool:
        name = str(project_dict.get("projectName", "") or project_dict.get("name", "")).strip()
        normalized_name = name.lower().strip(' .,:;')
        if normalized_name in _INVALID_PROJECT_NAMES:
            return True

        description = str(project_dict.get("projectDescription", "") or project_dict.get("description", "")).strip()
        responsibilities = self._to_list(project_dict.get("responsibilities"))
        technologies = self._to_list(project_dict.get("toolsUsed") or project_dict.get("technologies") or project_dict.get("environment"))
        client = str(project_dict.get("clientName", "") or project_dict.get("client", "")).strip()

        if not client and not technologies and not description and len(responsibilities) == 1:
            only_resp = responsibilities[0].strip().lower().strip(' .,:;')
            if normalized_name and only_resp == f"worked on {normalized_name}":
                return True

        return False
    
    def _convert_education_to_formatter_format(self, education) -> list:
        """Convert canonical education to formatter format"""
        formatter_education = []
        for edu in education:
            edu_dict = self._to_dict(edu)
            formatter_edu = {
                "degree": edu_dict.get("degree", "") or edu_dict.get("qualification", "") or edu_dict.get("title", ""),
                "institution": edu_dict.get("institution", "") or edu_dict.get("university", "") or edu_dict.get("college", ""),
                "university": edu_dict.get("university", ""),
                "specialization": edu_dict.get("specialization", "") or edu_dict.get("field", ""),
                "year_of_completion": int(edu_dict.get("yearOfPassing")) if str(edu_dict.get("yearOfPassing", "")).isdigit() else (
                    int(edu_dict.get("graduationYear")) if str(edu_dict.get("graduationYear", "")).isdigit() else None
                ),
                "year": edu_dict.get("yearOfPassing", "") or edu_dict.get("graduationYear", "") or edu_dict.get("year", ""),
                "grade": edu_dict.get("grade", "") or edu_dict.get("percentage", "") or edu_dict.get("gpa", ""),
                "percentage": edu_dict.get("percentage", "") or edu_dict.get("gpa", "")
            }
            formatter_education.append(formatter_edu)
        return formatter_education
    
    def _convert_work_history_to_formatter_format(self, work_history) -> list:
        """Convert canonical work history to formatter format"""
        formatter_work = []
        for work in work_history:
            work_dict = self._to_dict(work)
            formatter_work_item = {
                "organization": work_dict.get("organization", ""),
                "designation": work_dict.get("designation", ""),
                "start_date": work_dict.get("employmentStartDate", "") or work_dict.get("startDate", ""),
                "end_date": work_dict.get("employmentEndDate", ""),
                "is_current": work_dict.get("isCurrentCompany", False),
                "location": work_dict.get("location", ""),
                "responsibilities": self._to_list(work_dict.get("responsibilities")),
                "achievements": self._to_list(work_dict.get("achievements")),
                "technologies": self._to_list(work_dict.get("technologiesUsed") or work_dict.get("technologies"))
            }
            formatter_work.append(formatter_work_item)
        return formatter_work
    
    def _convert_certifications_to_formatter_format(self, certifications) -> list:
        """Convert canonical certifications to formatter format"""
        formatter_certs = []
        for cert in certifications:
            cert_dict = self._to_dict(cert)
            formatter_cert = {
                "name": cert_dict.get("name", ""),
                "issuing_organization": cert_dict.get("issuingOrganization", "") or cert_dict.get("organization", ""),
                "issue_date": cert_dict.get("issueDate", ""),
                "expiry_date": cert_dict.get("expiryDate", ""),
                "credential_id": cert_dict.get("credentialId", ""),
                "credential_url": cert_dict.get("credentialUrl", "")
            }
            formatter_certs.append(formatter_cert)
        return formatter_certs
    
    def _convert_achievements_to_formatter_format(self, achievements) -> list:
        """Convert canonical achievements to formatter format"""
        formatter_achievements = []
        for achievement in achievements:
            achievement_dict = self._to_dict(achievement)
            formatter_achievement = {
                "title": achievement_dict.get("title", ""),
                "description": achievement_dict.get("description", ""),
                "date": achievement_dict.get("date", "")
            }
            formatter_achievements.append(formatter_achievement)
        return formatter_achievements

    def _to_dict(self, item):
        if isinstance(item, dict):
            return item
        if hasattr(item, "model_dump"):
            try:
                return item.model_dump()
            except Exception:
                pass
        if hasattr(item, "__dict__"):
            return {k: v for k, v in vars(item).items() if not k.startswith("_")}
        return {}

    def _get_value(self, source, *path, default=None):
        current = source
        for key in path:
            if current is None:
                return default
            if isinstance(current, dict):
                current = current.get(key, default)
            else:
                current = getattr(current, key, default)
        return current if current is not None else default

    def _format_location(self, location):
        location_dict = self._to_dict(location)
        raw_location = location_dict.get("fullAddress") or ", ".join(
            filter(None, [location_dict.get("city"), location_dict.get("state"), location_dict.get("country")])
        )
        text = str(raw_location or "").strip(" ,.;:-")
        if not text:
            return ""

        lowered = text.lower()
        if lowered in _INVALID_LOCATION_VALUES:
            return ""

        parts = [part.strip(" .;:-") for part in text.split(",")]
        normalized_parts = [part for part in parts if part]
        invalid_tokens = _INVALID_LOCATION_VALUES | {"none", "null", "undefined", "n/a", "na", "nil"}
        cleaned_parts = [part for part in normalized_parts if part.lower() not in invalid_tokens]
        if not cleaned_parts:
            return ""
        cleaned = ", ".join(cleaned_parts)

        # Strip parser noise prefixes while preserving original user casing.
        for prefix in ("and ", "is ", "in "):
            if cleaned.lower().startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break

        cleaned = cleaned.strip(" ,.;:-")
        cleaned_lower = cleaned.lower()
        if not cleaned or cleaned_lower in _INVALID_LOCATION_VALUES:
            return ""

        return cleaned

    def _format_project_duration(self, project_dict):
        from_date = (
            project_dict.get("durationFrom") or
            project_dict.get("from") or
            project_dict.get("startDate") or
            project_dict.get("start_date") or
            ""
        )
        to_date = (
            project_dict.get("durationTo") or
            project_dict.get("to") or
            project_dict.get("endDate") or
            project_dict.get("end_date") or
            ""
        )
        if from_date and to_date:
            return f"{from_date} to {to_date}"
        return from_date or to_date or ""

    def _build_summary_fallback(self, candidate: dict) -> str:
        title = self._sanitize_current_title(candidate.get("currentDesignation") or candidate.get("designation") or "")
        organization = candidate.get("currentOrganization") or ""
        years = candidate.get("totalExperienceYears")
        summary_parts = []
        if title:
            summary_parts.append(title)
        if organization:
            summary_parts.append(f"at {organization}")
        if years:
            summary_parts.append(f"with {years} years of experience")
        summary = " ".join(summary_parts).strip()
        return summary if summary else ""

    def _sanitize_current_title(self, title: Any) -> str:
        cleaned = str(title or "")
        cleaned = " ".join(cleaned.split())
        cleaned = cleaned.strip(" ,.;:-")
        cleaned = cleaned.removeprefix("Experience ").strip()
        cleaned = cleaned.removeprefix("Current Role ").strip()
        cleaned = cleaned.removeprefix("Role ").strip()

        lowered = cleaned.lower().strip(" ,.;:-")
        if lowered in {"experience", "current role", "role", "project experience", "summary", "skills"}:
            return ""
        return cleaned

    def _extract_domain_expertise(self, experience: dict, skills: dict, canonical_dict: dict) -> list:
        candidates = []
        # Check experience section
        exp_dict = self._to_dict(experience) if experience else {}
        candidates.extend(self._to_list(exp_dict.get("domainExperience")))
        candidates.extend(self._to_list(exp_dict.get("domain_expertise")))
        candidates.extend(self._to_list(exp_dict.get("domainExpertise")))
        candidates.extend(self._to_list(exp_dict.get("domains")))
        
        # Check skills section
        skills_dict = self._to_dict(skills) if skills else {}
        candidates.extend(self._to_list(skills_dict.get("domainExperience")))
        candidates.extend(self._to_list(skills_dict.get("domain_expertise")))
        candidates.extend(self._to_list(skills_dict.get("domainExpertise")))
        candidates.extend(self._to_list(skills_dict.get("domains")))
        
        # Check canonical dict
        candidates.extend(self._to_list(canonical_dict.get("domainExperience")))
        candidates.extend(self._to_list(canonical_dict.get("domain_expertise")))

        # Last-resort fallback: infer domains from summary text if structured fields are missing.
        summary_text = " ".join(
            [
                str(self._to_dict(canonical_dict.get("candidate", {})).get("summary", "") or ""),
                str(canonical_dict.get("summary", "") or ""),
            ]
        ).strip()
        if summary_text:
            candidates.extend(self._extract_domains_from_text(summary_text))

        seen = set()
        normalized = []
        for item in candidates:
            text = str(item or "").strip(" ,.;:-")
            if not text:
                continue
            if text.lower() in {"domain", "domains", "domain expertise"}:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(text)

        return normalized

    def _extract_domains_from_text(self, text: str) -> list:
        lowered = str(text or "").lower()
        if not lowered:
            return []

        # Common domain set seen across the pipeline; only add when exact term exists.
        known_domains = [
            "healthcare",
            "insurance",
            "banking",
            "financial services",
            "retail",
            "manufacturing",
            "energy",
            "telecom",
            "automotive",
            "ecommerce",
            "e-commerce",
            "education",
            "logistics",
            "pharma",
        ]

        results = []
        for domain in known_domains:
            if domain in lowered:
                # Normalize display casing.
                normalized = "E-Commerce" if domain == "e-commerce" else domain.title()
                if normalized == "Ecommerce":
                    normalized = "E-Commerce"
                if normalized not in results:
                    results.append(normalized)
        return results

    def _to_list(self, value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [value]
        try:
            return list(value)
        except Exception:
            return [value]

    def _get_empty_preview(self) -> dict:
        """
        Get empty preview structure for error cases
        
        Returns:
            Empty preview dictionary
        """
        return {
            "header": {},
            "summary": {"professional_summary": "", "target_role": ""},
            "skills": {"primary_skills": [], "secondary_skills": []},
            "education": [],
            "work_experience": [],
            "project_experience": [],
            "certifications": [],
            "achievements": [],
            "languages": []
        }
