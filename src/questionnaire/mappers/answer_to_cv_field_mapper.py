from __future__ import annotations

import re
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
            "what is your current role/title?": ("personal_details", "current_title"),
            "what is your employee or portal id?": ("personal_details", "employee_id"),
            "what is your official email address?": ("personal_details", "email"),
            "what is your current location?": ("personal_details", "location"),
            "how would you describe your professional profile in 2-3 lines?": ("summary", "professional_summary"),
            "how would you describe your professional profile in 2–3 lines?": ("summary", "professional_summary"),
            "what is your total years of experience?": ("personal_details", "total_experience"),
            "what is your current organization?": ("personal_details", "current_organization"),
            "what are your key primary skills?": ("skills", "primary_skills"),
            "what are your secondary skills or supporting technologies?": ("skills", "secondary_skills"),
            "which tools, platforms, databases, cloud services, or operating systems have you worked with?": ("skills", "tools_and_platforms"),
            "what certifications do you hold?": ("certifications", "certifications"),
            "please share your educational qualifications.": ("education", "education"),
            "which languages do you speak or write?": ("languages", "languages"),
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

        if section == "skills" and field in {"primary_skills", "secondary_skills", "tools_and_platforms"}:
            cv_data[section][field] = self._parse_list(answer)
            return cv_data

        if section == "personal_details" and field == "total_experience":
            cv_data[section][field] = self._parse_float(answer)
            return cv_data

        if section == "certifications" and field == "certifications":
            cv_data[section] = self._parse_list(answer)
            return cv_data

        if section == "languages" and field == "languages":
            cv_data[section] = self._parse_list(answer)
            return cv_data

        if section == "education" and field == "education":
            cv_data[section] = self._parse_education(answer)
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
        normalized = value.replace("\r", " ").replace("\n", ", ")
        normalized = re.sub(r"\s+and\s+", ", ", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"[;/]+", ", ", normalized)
        normalized = re.sub(r"\s+\|\s+", ", ", normalized)
        normalized = re.sub(r"\s+-\s+", ", ", normalized)
        normalized = re.sub(r"\s+&\s+", ", ", normalized)
        normalized = re.sub(
            r'^(my\s+)?(primary|secondary|supporting|key|core)?\s*(skill|skills|technology|technologies|tool|tools|platform|platforms|frameworks|framework)\s*(is|are|include|includes|:)?\s*',
            '',
            normalized,
            flags=re.IGNORECASE,
        )
        return [item.strip().rstrip('.') for item in normalized.split(",") if item.strip()]

    @staticmethod
    def _parse_float(value: str):
        try:
            return float(value.strip())
        except Exception:
            return value.strip()

    @staticmethod
    def _parse_education(value: str) -> List[Dict[str, Any]]:
        if not value or not value.strip():
            return []

        text = value.strip()
        # Normalize delimiters and split on clear education boundaries
        text = re.sub(r"\r?\n+", " ", text)
        parts = [part.strip() for part in re.split(
            r'(?=(?:My second educational qualification|Then I have completed my 12th standard|I have completed my 10th standard))',
            text,
            flags=re.IGNORECASE,
        ) if part.strip()]

        education = []
        for part in parts:
            qualification = ""
            specialization = ""
            college = ""
            university = ""
            year = ""
            percentage = ""

            # Degree or qualification
            degree_match = re.search(r"(Master(?: of [A-Za-z ]+)?|Bachelor(?: of [A-Za-z ]+)?|B\.?Sc\.?|B\.?Tech\.?|M\.?C\.?A\.?|MBA|Bachelors?|Masters?)", part, re.IGNORECASE)
            if degree_match:
                qualification = degree_match.group(0).strip()

            branch_match = re.search(r"branch is ([^.,]+)", part, re.IGNORECASE)
            if branch_match:
                specialization = branch_match.group(1).strip()

            college_match = re.search(r"college (?:name )?(?:is )?([^.,]+)", part, re.IGNORECASE)
            if college_match:
                college = college_match.group(1).strip()

            university_match = re.search(r"university (?:name )?(?:is )?([^.,]+)", part, re.IGNORECASE)
            if university_match:
                university = university_match.group(1).strip()

            year_match = re.search(r"(20\d{2}|19\d{2})", part)
            if year_match:
                year = year_match.group(0)

            percentage_match = re.search(r"(\d{1,3}(?:\.\d+)?\s*(?:%|percent|percentage))", part, re.IGNORECASE)
            if percentage_match:
                percentage = percentage_match.group(1).strip()

            if not qualification:
                # Identify common education phrases for string fallback
                qual_fallback_match = re.search(r"(\d+(?:th|st|nd|rd) standard|Bachelor of Science|Master of Computer Applications|Master in [^.,]+)", part, re.IGNORECASE)
                if qual_fallback_match:
                    qualification = qual_fallback_match.group(0).strip()

            if not qualification and part:
                qualification = part.strip()

            education.append({
                "qualification": qualification,
                "specialization": specialization,
                "college": college,
                "university": university,
                "year": year,
                "percentage": percentage,
            })

        return education
