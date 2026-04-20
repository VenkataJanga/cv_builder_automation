import re
from typing import Dict, Any, List


class CVFormattingAgent:
    def format_cv(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        # Handle both old structure (personal_details) and new structure (personal_information/header)
        # IMPORTANT: We need to merge data from multiple sources, not just pick the first one
        personal = cv_data.get("personal_details", {})
        personal_info = cv_data.get("personal_information", {})
        header_data = cv_data.get("header", {})
        
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
                "full_name": (
                    personal.get("full_name") or 
                    personal_info.get("full_name") or 
                    header_data.get("full_name") or
                    personal.get("name") or 
                    personal.get("candidate_name", "")
                ),
                "current_title": (
                    personal.get("current_title") or 
                    personal_info.get("current_title") or 
                    header_data.get("current_title") or
                    personal.get("designation") or 
                    personal.get("title") or 
                    personal.get("job_title", "")
                ),
                "location": (
                    personal.get("location") or 
                    personal_info.get("location") or 
                    header_data.get("location") or
                    personal.get("current_location") or 
                    personal.get("city") or 
                    personal.get("address", "")
                ),
                "current_organization": (
                    personal.get("current_organization") or 
                    personal_info.get("current_organization") or 
                    header_data.get("current_organization") or
                    personal.get("organization") or 
                    personal.get("company") or 
                    employment.get("current_company") or 
                    personal.get("employer", "")
                ),
                "total_experience": (
                    personal.get("total_experience") or 
                    personal_info.get("total_experience") or 
                    header_data.get("total_experience") or
                    personal.get("experience") or 
                    personal.get("years_of_experience") or 
                    (f"{exp_years} years" if exp_years else "")
                ),
                "target_role": (
                    cv_data.get("target_role") or 
                    (summary.get("target_role") if isinstance(summary, dict) else "")
                ),
                "email": (
                    personal.get("email") or 
                    personal_info.get("email") or 
                    header_data.get("email") or
                    personal.get("email_address") or 
                    personal.get("email_id", "")
                ),
                "employee_id": (
                    personal.get("employee_id") or 
                    personal_info.get("employee_id") or 
                    header_data.get("employee_id") or
                    personal.get("portal_id") or 
                    header_data.get("portal_id") or
                    personal.get("emp_id") or 
                    personal.get("staff_id") or 
                    personal.get("employee_number", "")
                ),
                "contact_number": (
                    personal.get("contact_number") or 
                    personal_info.get("contact_number") or 
                    header_data.get("contact_number") or
                    personal.get("phone") or 
                    header_data.get("phone") or
                    personal.get("mobile") or 
                    personal.get("phone_number") or 
                    personal.get("mobile_number") or 
                    personal.get("contact", "")
                ),
                "grade": (
                    personal.get("grade") or 
                    personal_info.get("grade") or 
                    header_data.get("grade") or
                    personal.get("level") or 
                    personal.get("job_level", "")
                ),
            },
            "summary": self._format_summary(self._extract_summary_text(summary, cv_data)),
            "skills": self._format_skills(skills.get("primary_skills", []) if isinstance(skills, dict) else cv_data.get("skills", [])),
            "secondary_skills": self._format_skills(
                (skills.get("secondary_skills", []) if isinstance(skills, dict) else []) or 
                cv_data.get("secondary_skills", [])
            ),
            "tools_and_platforms": self._format_skills(skills.get("tools_and_platforms", []) if isinstance(skills, dict) else cv_data.get("tools_and_platforms", [])),
            "ai_frameworks": self._format_skills(skills.get("ai_frameworks", []) if isinstance(skills, dict) else cv_data.get("ai_frameworks", [])),
            "cloud_platforms": self._format_skills(skills.get("cloud_platforms", []) if isinstance(skills, dict) else cv_data.get("cloud_platforms", [])),
            "operating_systems": self._format_skills(skills.get("operating_systems", []) if isinstance(skills, dict) else cv_data.get("operating_systems", [])),
            "databases": self._format_skills(skills.get("databases", []) if isinstance(skills, dict) else cv_data.get("databases", [])),
            "domain_expertise": self._format_domains(
                cv_data.get("domain_expertise", [])
                or (skills.get("domain_expertise", []) if isinstance(skills, dict) else [])
            ),
            "development_tools": self._format_skills(skills.get("development_tools", []) if isinstance(skills, dict) else cv_data.get("development_tools", [])),
            "crm_tools": self._format_skills(skills.get("crm_tools", []) if isinstance(skills, dict) else cv_data.get("crm_tools", [])),
            "database_connectivity": self._format_skills(skills.get("database_connectivity", []) if isinstance(skills, dict) else cv_data.get("database_connectivity", [])),
            "sql_skills": self._format_skills(skills.get("sql_skills", []) if isinstance(skills, dict) else cv_data.get("sql_skills", [])),
            "erp": self._format_skills(skills.get("erp", []) if isinstance(skills, dict) else cv_data.get("erp", [])),
            "legacy_systems": self._format_skills(skills.get("legacy_systems", []) if isinstance(skills, dict) else cv_data.get("legacy_systems", [])),
            "networking": self._format_skills(skills.get("networking", []) if isinstance(skills, dict) else cv_data.get("networking", [])),
            "testing_tools": self._format_skills(skills.get("testing_tools", []) if isinstance(skills, dict) else cv_data.get("testing_tools", [])),
            "documentation": self._format_skills(skills.get("documentation", []) if isinstance(skills, dict) else cv_data.get("documentation", [])),
            "configuration_management": self._format_skills(skills.get("configuration_management", []) if isinstance(skills, dict) else cv_data.get("configuration_management", [])),
            "client_server_technologies": self._format_skills(skills.get("client_server_technologies", []) if isinstance(skills, dict) else cv_data.get("client_server_technologies", [])),
            "foreign_language_known": self._format_skills(skills.get("foreign_language_known", []) if isinstance(skills, dict) else cv_data.get("foreign_language_known", [])),
            "employment": employment,
            "leadership": self._format_leadership(leadership),
            "work_experience": cv_data.get("work_experience", []),
            "project_experience": cv_data.get("project_experience", []),
            "certifications": self._format_certifications(
                cv_data.get("certifications") or cv_data.get("certifications_and_trainings", [])
            ),
            "education": cv_data.get("education", []),
            "publications": cv_data.get("publications", []),
            "awards": cv_data.get("awards", []),
            "languages": cv_data.get("languages", []),
            "schema_version": cv_data.get("schema_version", "1.0"),
        }

    def _extract_summary_text(self, summary, cv_data: Dict[str, Any]) -> str:
        def normalize_value(value):
            if isinstance(value, str):
                return value.strip()
            if isinstance(value, list):
                return "\n".join(
                    normalize_value(item) for item in value if item is not None
                )
            if isinstance(value, dict):
                preferred_keys = [
                    "professional_summary",
                    "summary",
                    "experience_summary",
                    "profile_summary",
                    "description",
                    "text",
                    "content",
                ]
                for key in preferred_keys:
                    if key in value and value.get(key) not in (None, ""):
                        extracted = normalize_value(value.get(key))
                        if extracted:
                            return extracted

                ignored_keys = {
                    "target_role",
                    "total_experience_years",
                    "total_experience_months",
                    "relevant_experience_years",
                    "relevant_experience_months",
                    "years_of_experience",
                }
                parts = []
                for key, item in value.items():
                    if str(key).lower() in ignored_keys:
                        continue
                    extracted = normalize_value(item)
                    if extracted:
                        parts.append(extracted)
                return "\n".join(parts)
            return ""

        if isinstance(summary, dict):
            return normalize_value(summary)

        if isinstance(summary, (str, list)):
            return normalize_value(summary)

        fallback = cv_data.get("summary")
        if isinstance(fallback, (str, list, dict)):
            return normalize_value(fallback)
        return ""

    def _format_summary(self, text: str) -> str:
        text = (text or "").replace("\r\n", "\n")
        text = re.sub(r"(?m)^\s*[\u2022\u25E6\u25AA\u25CF\u25C6\u25BA\uF076]\s*", "• ", text)
        text = re.sub(r"(?m)^\s*[-*]\s+", "• ", text)
        text = "\n".join(line.strip() for line in text.split("\n"))
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

    def _format_skills(self, skills) -> List[str]:
        clean = []
        
        # Handle different input types
        if isinstance(skills, str):
            # If it's a string, split by comma
            skill_list = [s.strip() for s in skills.split(',')]
        elif isinstance(skills, list):
            skill_list = skills
        else:
            # Handle None or other types
            skill_list = []
        
        for skill in skill_list:
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

    def _format_domains(self, domains) -> List[str]:
        return self._normalize_text_list(domains, ["domain", "industry", "name", "value", "label", "title"])

    def _format_certifications(self, certifications) -> List[str]:
        return self._normalize_text_list(
            certifications,
            ["name", "certification_name", "certification", "title", "course", "value", "label"]
        )

    def _normalize_text_list(self, value, preferred_keys: List[str]) -> List[str]:
        def split_text(text: Any) -> List[str]:
            raw = str(text or "")
            if not raw:
                return []
            items = []
            for token in re.split(r"\n|,", raw):
                cleaned = re.sub(r"^[-*\u2022]\s*", "", token).strip()
                if cleaned:
                    items.append(cleaned)
            return items

        def to_items(item: Any) -> List[str]:
            if item is None:
                return []
            if isinstance(item, str) or isinstance(item, int) or isinstance(item, float):
                return split_text(item)
            if isinstance(item, list):
                flat = []
                for child in item:
                    flat.extend(to_items(child))
                return flat
            if isinstance(item, dict):
                for key in preferred_keys:
                    if key in item:
                        extracted = to_items(item.get(key))
                        if extracted:
                            return extracted
                flat = []
                for child in item.values():
                    flat.extend(to_items(child))
                return flat
            return split_text(item)

        seen = set()
        normalized = []
        for entry in to_items(value):
            key = entry.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(entry)
        return normalized
