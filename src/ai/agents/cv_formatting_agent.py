from typing import Dict, Any, List


class CVFormattingAgent:
    def format_cv(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        # Handle both old structure (personal_details) and new structure (personal_information/header)
        personal = cv_data.get("personal_details") or cv_data.get("personal_information") or cv_data.get("header", {})
        summary = cv_data.get("summary") or cv_data.get("professional_summary", {})
        skills = cv_data.get("skills", {})
        leadership = cv_data.get("leadership", {})
        employment = cv_data.get("employment_details", {})
        
        # Extract experience years
        exp_years = 0
        if isinstance(summary, dict):
            exp_years = summary.get("total_experience_years", 0)
        
        return {
            "header": {
                "full_name": personal.get("full_name", ""),
                "current_title": personal.get("current_title") or personal.get("designation", ""),
                "location": personal.get("location") or personal.get("current_location", ""),
                "current_organization": personal.get("current_organization") or employment.get("current_company", ""),
                "total_experience": personal.get("total_experience") or f"{exp_years} years" if exp_years else "",
                "target_role": cv_data.get("target_role", ""),
                "email": personal.get("email", ""),
                "employee_id": personal.get("employee_id") or personal.get("portal_id", ""),
                "contact_number": personal.get("contact_number", ""),
                "grade": personal.get("grade", ""),
            },
            "summary": self._format_summary(
                summary.get("summary") if isinstance(summary, dict) 
                else (summary if isinstance(summary, str) else cv_data.get("summary", ""))
            ),
            "skills": self._format_skills(skills.get("primary_skills", []) if isinstance(skills, dict) else cv_data.get("skills", [])),
            "secondary_skills": self._format_skills(skills.get("secondary_skills", []) if isinstance(skills, dict) else cv_data.get("secondary_skills", [])),
            "tools_and_platforms": self._format_skills(skills.get("tools_and_platforms", []) if isinstance(skills, dict) else cv_data.get("tools_and_platforms", [])),
            "ai_frameworks": self._format_skills(skills.get("ai_frameworks", []) if isinstance(skills, dict) else cv_data.get("ai_frameworks", [])),
            "cloud_platforms": self._format_skills(skills.get("cloud_platforms", []) if isinstance(skills, dict) else cv_data.get("cloud_platforms", [])),
            "operating_systems": self._format_skills(skills.get("operating_systems", []) if isinstance(skills, dict) else cv_data.get("operating_systems", [])),
            "databases": self._format_skills(skills.get("databases", []) if isinstance(skills, dict) else cv_data.get("databases", [])),
            "domain_expertise": cv_data.get("domain_expertise", []),
            "employment": employment,
            "leadership": self._format_leadership(leadership),
            "work_experience": cv_data.get("work_experience", []),
            "project_experience": cv_data.get("project_experience", []),
            "certifications": cv_data.get("certifications") or cv_data.get("certifications_and_trainings", []),
            "education": cv_data.get("education", []),
            "publications": cv_data.get("publications", []),
            "awards": cv_data.get("awards", []),
            "languages": cv_data.get("languages", []),
            "schema_version": cv_data.get("schema_version", "1.0"),
        }

    def _format_summary(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        text = " ".join(text.split())
        if not text.endswith("."):
            text += "."
        return text

    def _format_skills(self, skills: List[str]) -> List[str]:
        clean = []
        for skill in skills or []:
            value = str(skill).strip()
            if value and value not in clean:
                clean.append(value)
        return clean

    def _format_leadership(self, leadership: Dict[str, Any]) -> Dict[str, List[str]]:
        formatted = {}
        for key, values in leadership.items():
            if isinstance(values, list):
                cleaned = []
                for item in values:
                    text = str(item).strip()
                    if text:
                        if not text.endswith("."):
                            text += "."
                        cleaned.append(text)
                formatted[key] = cleaned
        return formatted
