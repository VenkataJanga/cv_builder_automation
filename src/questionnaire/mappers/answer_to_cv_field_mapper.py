from __future__ import annotations

from typing import Any, Dict, List


class AnswerToCVFieldMapper:
    """
    Maps questionnaire answers into the canonical CV data structure.

    MVP1:
    - Question text based mapping
    - Stores unknown questions in unmapped_answers so data is never lost
    """

    def __init__(self) -> None:
        self._mapping = {
            "what is your full name?": ("personal_details", "full_name"),
            "what is your current location?": ("personal_details", "location"),
            "how would you describe your professional profile in 2–3 lines?": ("summary", "professional_summary"),
            "what is your total years of experience?": ("personal_details", "total_experience"),
            "what is your current organization?": ("personal_details", "current_organization"),
            "what are your key skills?": ("skills", "primary_skills"),
            "have you led teams? if yes, what was the team size?": ("leadership", "team_leadership"),
            "what are your key leadership achievements?": ("leadership", "leadership_achievements"),
            "what business outcomes have you delivered?": ("leadership", "business_outcomes"),
        }

    def apply_answer(self, cv_data: Dict[str, Any], question: str, answer: str) -> Dict[str, Any]:
        normalized = question.strip().lower()
        target = self._mapping.get(normalized)

        if not target:
            cv_data.setdefault("unmapped_answers", {})[question] = answer
            return cv_data

        section, field = target
        cv_data.setdefault(section, {})

        if section == "skills" and field == "primary_skills":
            cv_data[section][field] = self._parse_list(answer)
            return cv_data

        if section == "personal_details" and field == "total_experience":
            cv_data[section][field] = self._parse_float(answer)
            return cv_data

        if section == "leadership":
            cv_data[section].setdefault(field, [])
            if answer and answer.strip():
                cv_data[section][field].append(answer.strip())
            return cv_data

        cv_data[section][field] = answer.strip()
        return cv_data

    @staticmethod
    def _parse_list(value: str) -> List[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @staticmethod
    def _parse_float(value: str):
        try:
            return float(value.strip())
        except Exception:
            return value.strip()
