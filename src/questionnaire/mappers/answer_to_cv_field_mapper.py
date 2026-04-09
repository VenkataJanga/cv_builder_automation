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
            "what kinds of roles are you targeting?": ("summary", "target_role"),
            "which industries or domains have you worked in?": ("skills", "domain_expertise"),
            "what are your core areas of expertise?": ("skills", "domain_expertise"),
            "what are your key primary skills?": ("skills", "primary_skills"),
            "what are your secondary skills or supporting technologies?": ("skills", "secondary_skills"),
            "which tools, platforms, databases, cloud services, or operating systems have you worked with?": ("skills", "tools_and_platforms"),
            "what certifications do you hold?": ("certifications", "certifications"),
            "please share your educational qualifications.": ("education", "education"),
            "which languages do you speak or write?": ("languages", "languages"),
            "have you led teams? if yes, what was the team size?": ("leadership", "team_leadership"),
            "what are your key leadership achievements?": ("leadership", "leadership_achievements"),
            "what business outcomes have you delivered?": ("leadership", "business_outcomes"),
            "what was your role in project execution?": ("leadership", "execution_role"),
            "how did you manage your team’s performance?": ("leadership", "team_performance"),
            "what technologies or tools did your team use?": ("leadership", "technologies_tools"),
            "how did you handle delivery challenges?": ("leadership", "delivery_challenges"),
            "did you mentor or coach team members?": ("leadership", "mentoring"),
            "how did you ensure code quality or delivery quality?": ("leadership", "quality_assurance"),
            "have you handled sprint planning or agile ceremonies?": ("leadership", "agile_ceremonies"),
            "what improvements did you bring to your team?": ("leadership", "improvements"),
            "what measurable impact did your team deliver?": ("leadership", "measurable_impact"),
            "how many projects have you managed simultaneously?": ("leadership", "projects_managed"),
            "what was the average project size in terms of budget or team?": ("leadership", "avg_project_size"),
            "how do you handle project risks and issues?": ("leadership", "risk_management"),
            "have you handled client communication directly?": ("leadership", "client_communication"),
            "how do you track project progress and kpis?": ("leadership", "progress_tracking"),
            "what tools have you used (jira, ms project, etc.)?": ("leadership", "tools_used"),
            "what is your biggest project success story?": ("leadership", "success_story"),
            "have you delivered projects under tight deadlines or constraints?": ("leadership", "tight_deadline_delivery"),
            "what are your primary technical domains?": ("skills", "primary_technical_domains"),
            "what kind of systems have you built (scalable, distributed, cloud)?": ("leadership", "system_types"),
            "which technologies and platforms do you specialize in?": ("leadership", "technology_specializations"),
            "how do you make technical decisions?": ("leadership", "decision_making"),
            "have you reviewed code or set technical standards?": ("leadership", "code_review_standards"),
            "how do you ensure system performance and scalability?": ("leadership", "performance_scalability"),
            "how do you handle technical risks?": ("leadership", "technical_risks"),
            "have you mentored engineers or technical leads?": ("leadership", "mentoring_engineers"),
            "have you handled end-to-end recruitment cycles?": ("leadership", "recruitment_experience"),
            "what is your experience with employee engagement initiatives?": ("leadership", "employee_engagement"),
            "have you worked on performance management systems?": ("leadership", "performance_management"),
            "have you handled conflict resolution or employee relations?": ("leadership", "conflict_resolution"),
            "what hr tools or systems have you used?": ("leadership", "hr_tools"),
            "have you worked on hr policies or compliance?": ("leadership", "policies_compliance"),
            "what hiring volume have you handled?": ("leadership", "hiring_volume"),
            "have you supported leadership or business units directly?": ("leadership", "leadership_support"),
            "what hr transformations or initiatives have you led?": ("leadership", "hr_transformations"),
            "have you handled multiple accounts or programs?": ("leadership", "accounts_programs"),
            "what is your experience in p&l management?": ("leadership", "pnl_management"),
            "how do you ensure delivery excellence across projects?": ("leadership", "delivery_excellence"),
            "have you driven digital transformation or large programs?": ("leadership", "digital_transformation"),
            "how do you manage client relationships at leadership level?": ("leadership", "client_relationships"),
            "how do you handle escalations and crisis situations?": ("leadership", "escalations_crisis"),
            "what governance models have you implemented?": ("leadership", "governance_models"),
            "what business growth or revenue impact have you driven?": ("leadership", "business_impact"),
            "how do you align delivery with business strategy?": ("leadership", "alignment_strategy"),
        }

    def apply_answer(self, cv_data: Dict[str, Any], question: str, answer: str) -> Dict[str, Any]:
        normalized = question.strip().lower()
        target = self._mapping.get(normalized)

        if not target:
            cv_data.setdefault("unmapped_answers", {})[question] = answer
            return cv_data

        section, field = target
        cv_data.setdefault(section, {})

        if section == "skills" and field in {"primary_skills", "secondary_skills", "tools_and_platforms", "domain_expertise"}:
            parsed = self._parse_list(answer)
            existing = cv_data[section].get(field, [])
            if isinstance(existing, list):
                merged = list(existing)
                for item in parsed:
                    if item and item not in merged:
                        merged.append(item)
                cv_data[section][field] = merged
            else:
                cv_data[section][field] = parsed
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
            r'(?=(?:Next,|Then|I have completed intermediate|My secondary school))',
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
