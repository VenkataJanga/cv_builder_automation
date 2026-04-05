
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import ValidationError

from src.domain.cv.models.cv_schema import CVSchema, PersonalDetails, Summary, Skills
from src.questionnaire.mappers.answer_to_cv_field_mapper import AnswerToCVFieldMapper


class CVBuilderService:
    """
    Builds and updates canonical CV data from questionnaire answers.

    MVP1 responsibilities:
    - maintain partial structured CV data
    - map question answers to schema fields
    - create a validated CVSchema only when minimum required fields exist
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

    def try_build_schema(self, cv_data: Dict[str, Any]) -> Optional[CVSchema]:
        """Attempts to create a CVSchema instance."""
        if not self._has_minimum_required_fields(cv_data):
            return None

        try:
            return CVSchema(
                personal_details=PersonalDetails(
                    full_name=cv_data["personal_details"]["full_name"],
                    current_title=cv_data["personal_details"]["current_title"],
                    total_experience=cv_data["personal_details"].get("total_experience"),
                    current_organization=cv_data["personal_details"].get("current_organization"),
                    location=cv_data["personal_details"]["location"],
                    email=cv_data["personal_details"].get("email"),
                    phone=cv_data["personal_details"].get("phone"),
                    linkedin=cv_data["personal_details"].get("linkedin"),
                ),
                summary=Summary(
                    professional_summary=cv_data["summary"]["professional_summary"],
                    target_role=cv_data.get("target_role"),
                ),
                skills=Skills(
                    primary_skills=cv_data["skills"].get("primary_skills", []),
                    secondary_skills=cv_data["skills"].get("secondary_skills", []),
                    tools_and_platforms=cv_data["skills"].get("tools_and_platforms", []),
                    domain_expertise=cv_data["skills"].get("domain_expertise", []),
                ),
                work_experience=cv_data.get("work_experience", []),
                project_experience=cv_data.get("project_experience", []),
                certifications=cv_data.get("certifications", []),
                education=cv_data.get("education", []),
                publications=cv_data.get("publications") or None,
                awards=cv_data.get("awards") or None,
                languages=cv_data.get("languages") or None,
                target_role=cv_data.get("target_role"),
                schema_version=cv_data.get("schema_version", "1.0"),
            )
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
