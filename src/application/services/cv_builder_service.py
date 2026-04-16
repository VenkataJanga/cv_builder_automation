
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import ValidationError

from src.domain.cv.enums import SourceType
from src.domain.cv.models.canonical_cv_schema import (
    CanonicalCVSchema,
    CertificationModel,
    EducationModel,
    ProjectModel,
    get_empty_schema,
)
from src.questionnaire.mappers.answer_to_cv_field_mapper import AnswerToCVFieldMapper


class CVBuilderService:
    """
    Builds and updates questionnaire cv_data from answers.

    Responsibilities:
    - maintain partial structured questionnaire cv_data
    - map question answers to questionnaire field names
    - create a minimal validated CanonicalCVSchema only when minimum required fields exist
    """

    def __init__(self) -> None:
        self.mapper = AnswerToCVFieldMapper()

    def initialize_cv_data(self, role: Optional[str] = None) -> Dict[str, Any]:
        return {
            "personal_details": {},
            "summary": {},
            "skills": {},
            "work_experience": [],
            "project_experience": [],
            "certifications": [],
            "education": [],
            "publications": [],
            "awards": [],
            "languages": [],
            "leadership": {},
            "target_role": role,
            "schema_version": "1.0",
        }

    def update_from_answer(self, cv_data: Dict[str, Any], question: str, answer: str) -> Dict[str, Any]:
        return self.mapper.apply_answer(cv_data, question, answer)

    def build_partial_schema(self, cv_data: Dict[str, Any]) -> CanonicalCVSchema:
        """Build a best-effort canonical schema from partial questionnaire data."""
        schema = self._build_schema(cv_data, require_minimum=False)
        if schema is None:
            return get_empty_schema(source_type=SourceType.BOT_CONVERSATION.value)
        return schema

    def try_build_schema(self, cv_data: Dict[str, Any]) -> Optional[CanonicalCVSchema]:
        """Attempts to create a minimal CanonicalCVSchema instance."""
        return self._build_schema(cv_data, require_minimum=True)

    def _build_schema(
        self,
        cv_data: Dict[str, Any],
        require_minimum: bool,
    ) -> Optional[CanonicalCVSchema]:
        if require_minimum and not self._has_minimum_required_fields(cv_data):
            return None

        try:
            personal = cv_data.get("personal_details", {})
            summary = cv_data.get("summary", {})
            skills = cv_data.get("skills", {})

            schema = get_empty_schema(source_type=SourceType.BOT_CONVERSATION.value)
            schema.candidate.fullName = personal.get("full_name", "")
            schema.candidate.currentDesignation = personal.get("current_title", "")
            schema.candidate.currentOrganization = personal.get("current_organization", "") or ""
            schema.candidate.email = personal.get("email", "") or ""
            schema.candidate.phoneNumber = personal.get("phone", "") or ""
            schema.candidate.portalId = personal.get("employee_id", "") or ""
            schema.candidate.summary = summary.get("professional_summary", "")
            schema.candidate.careerObjective = cv_data.get("target_role") or summary.get("target_role") or ""
            schema.personalDetails.linkedinUrl = personal.get("linkedin", "") or ""
            schema.personalDetails.languagesKnown = list(cv_data.get("languages", []) or [])

            total_experience = personal.get("total_experience")
            if total_experience not in (None, ""):
                try:
                    schema.candidate.totalExperienceYears = int(float(total_experience))
                except (TypeError, ValueError):
                    schema.candidate.totalExperienceYears = 0

            location_value = personal.get("location", "")
            schema.candidate.currentLocation.fullAddress = location_value
            if isinstance(location_value, str):
                location_parts = [part.strip() for part in location_value.split(",") if part.strip()]
                if location_parts:
                    schema.candidate.currentLocation.city = location_parts[0]
                if len(location_parts) > 1:
                    schema.candidate.currentLocation.country = location_parts[-1]

            schema.skills.primarySkills = list(skills.get("primary_skills", []) or [])
            schema.skills.secondarySkills = list(skills.get("secondary_skills", []) or [])
            schema.skills.toolsAndPlatforms = list(skills.get("tools_and_platforms", []) or [])
            schema.experience.domainExperience = list(skills.get("domain_expertise", []) or [])
            schema.experience.industriesWorked = list(skills.get("domain_expertise", []) or [])

            for education_entry in cv_data.get("education", []) or []:
                if not isinstance(education_entry, dict):
                    continue
                schema.education.append(EducationModel(
                    degree=education_entry.get("degree") or education_entry.get("qualification") or "",
                    institution=education_entry.get("institution") or education_entry.get("college") or education_entry.get("university") or "",
                    specialization=education_entry.get("specialization") or "",
                    university=education_entry.get("university") or "",
                    yearOfPassing=str(education_entry.get("year_of_completion") or education_entry.get("year") or ""),
                    percentage=str(education_entry.get("percentage") or ""),
                ))

            for project_entry in cv_data.get("project_experience", []) or []:
                if not isinstance(project_entry, dict):
                    continue
                schema.experience.projects.append(ProjectModel(
                    projectName=project_entry.get("project_name") or "",
                    clientName=project_entry.get("client_name") or "",
                    role=project_entry.get("role") or "",
                    projectDescription=project_entry.get("description") or project_entry.get("project_description") or "",
                    toolsUsed=list(project_entry.get("technologies", []) or []),
                    responsibilities=list(project_entry.get("responsibilities", []) or []),
                    outcomes=list(project_entry.get("outcomes", []) or []),
                ))

            for certification in cv_data.get("certifications", []) or []:
                if not certification:
                    continue
                schema.certifications.append(CertificationModel(name=str(certification)))

            return CanonicalCVSchema(**schema.model_dump())
        except ValidationError:
            return None

    def apply_role_seed(self, cv_data: Dict[str, Any], role_answer: str) -> Dict[str, Any]:
        cv_data.setdefault("personal_details", {})
        cv_data["personal_details"]["current_title"] = role_answer.strip()
        cv_data["target_role"] = role_answer.strip()
        return cv_data

    @staticmethod
    def _has_minimum_required_fields(cv_data: Dict[str, Any]) -> bool:
        personal = cv_data.get("personal_details", {})
        summary = cv_data.get("summary", {})
        skills = cv_data.get("skills", {})

        required = [
            personal.get("full_name"),
            personal.get("current_title"),
            personal.get("location"),
            summary.get("professional_summary"),
        ]
        if not all(required):
            return False

        if not skills.get("primary_skills"):
            return False

        return True
