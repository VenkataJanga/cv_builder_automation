
from __future__ import annotations

from copy import deepcopy
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

            # Preserve non-canonical personal detail fields to avoid data loss.
            extra_personal_fields = {
                key: value
                for key, value in personal.items()
                if key
                not in {
                    "full_name",
                    "current_title",
                    "current_organization",
                    "email",
                    "phone",
                    "employee_id",
                    "linkedin",
                    "total_experience",
                    "location",
                }
                and value not in (None, "", [], {})
            }
            if extra_personal_fields:
                schema.unmappedData["personal_details"] = extra_personal_fields

            # Preserve non-canonical summary fields to avoid data loss.
            extra_summary_fields = {
                key: value
                for key, value in summary.items()
                if key not in {"professional_summary", "target_role"}
                and value not in (None, "", [], {})
            }
            if extra_summary_fields:
                schema.unmappedData["summary"] = extra_summary_fields

            # Preserve role-specific skill fields that do not map to canonical SkillsModel keys.
            extra_skill_fields = {
                key: value
                for key, value in skills.items()
                if key not in {"primary_skills", "secondary_skills", "tools_and_platforms", "domain_expertise"}
                and value not in (None, "", [], {})
            }
            if extra_skill_fields:
                schema.unmappedData["skills"] = extra_skill_fields

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

            # Transfer leadership data to unmappedData for preservation (Phase 4 fallback)
            leadership_data = cv_data.get("leadership", {})
            if leadership_data and isinstance(leadership_data, dict):
                schema.unmappedData["leadership"] = leadership_data

            # Preserve any additional questionnaire sections not projected into canonical fields.
            for section_name, section_value in cv_data.items():
                if section_name in {
                    "personal_details",
                    "summary",
                    "skills",
                    "work_experience",
                    "project_experience",
                    "certifications",
                    "education",
                    "publications",
                    "awards",
                    "languages",
                    "leadership",
                    "target_role",
                    "schema_version",
                }:
                    continue

                if section_value in (None, "", [], {}):
                    continue

                schema.unmappedData[section_name] = section_value

            # Keep full questionnaire snapshot for strict no-data-loss guarantees.
            schema.sourceSnapshots["questionnaire_cv_data"] = deepcopy(cv_data)

            return CanonicalCVSchema(**schema.model_dump())
        except ValidationError:
            return None

    def apply_role_seed(self, cv_data: Dict[str, Any], role_answer: str) -> Dict[str, Any]:
        cv_data.setdefault("personal_details", {})
        cv_data["personal_details"]["current_title"] = role_answer.strip()
        cv_data["target_role"] = role_answer.strip()
        return cv_data

    def merge_extracted_fields(
        self,
        cv_data: Dict[str, Any],
        extracted_fields: Dict[str, Any],
        merge_strategy: str = "questionnaire_wins",
    ) -> Dict[str, Any]:
        """
        Merge LLM-extracted fields into CV data safely.
        
        Args:
            cv_data: Current CV data from questionnaire
            extracted_fields: Fields extracted by LLM
            merge_strategy: How to merge
                - "questionnaire_wins": Keep questionnaire values if present
                - "extracted_wins": Use extracted values
                
        Returns:
            Merged CV data dict
            
        Notes:
            - Questionnaire-confirmed values always take priority
            - Extracted fields fill gaps
            - List fields (experience, projects, education) append non-duplicates
        """
        if not extracted_fields:
            return cv_data

        merged = cv_data.copy()

        # Merge personal details dict
        if "personal_details" in extracted_fields:
            existing_personal = merged.get("personal_details", {})
            extracted_personal = extracted_fields["personal_details"]
            for key, extracted_val in extracted_personal.items():
                if extracted_val is None or extracted_val == "":
                    continue
                existing_val = existing_personal.get(key)
                if merge_strategy == "questionnaire_wins":
                    if not existing_val or existing_val == "":
                        existing_personal[key] = extracted_val
                else:
                    existing_personal[key] = extracted_val
            merged["personal_details"] = existing_personal

        # Merge summary dict
        if "summary" in extracted_fields:
            existing_summary = merged.get("summary", {})
            extracted_summary = extracted_fields["summary"]
            for key, extracted_val in extracted_summary.items():
                if extracted_val is None or extracted_val == "":
                    continue
                existing_val = existing_summary.get(key)
                if merge_strategy == "questionnaire_wins":
                    if not existing_val or existing_val == "":
                        existing_summary[key] = extracted_val
                else:
                    existing_summary[key] = extracted_val
            merged["summary"] = existing_summary

        # Merge skills dict
        if "skills" in extracted_fields:
            existing_skills = merged.get("skills", {})
            extracted_skills = extracted_fields["skills"]
            for key, extracted_list in extracted_skills.items():
                if not isinstance(extracted_list, list) or not extracted_list:
                    continue
                existing_list = existing_skills.get(key, [])
                if not existing_list and merge_strategy == "questionnaire_wins":
                    # Only use extracted if questionnaire is empty
                    existing_skills[key] = extracted_list
                elif merge_strategy == "extracted_wins":
                    existing_skills[key] = extracted_list
            merged["skills"] = existing_skills

        # Merge list fields (append if questionnaire is empty)
        for list_field in ["work_experience", "project_experience", "education", "certifications"]:
            if list_field in extracted_fields:
                extracted_list = extracted_fields[list_field]
                if isinstance(extracted_list, list) and extracted_list:
                    existing_list = merged.get(list_field, [])
                    if not existing_list and merge_strategy == "questionnaire_wins":
                        merged[list_field] = extracted_list
                    elif merge_strategy == "extracted_wins":
                        merged[list_field] = extracted_list
                    # "merge" strategy: append non-duplicates (simple append for now)
                    elif not existing_list:
                        merged[list_field] = extracted_list

        return merged

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
