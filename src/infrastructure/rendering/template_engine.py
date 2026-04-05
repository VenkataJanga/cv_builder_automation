from typing import Dict, Any

from src.ai.agents.cv_formatting_agent import CVFormattingAgent


class TemplateEngine:
    def __init__(self) -> None:
        self.formatter = CVFormattingAgent()

    def render_context(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        formatted = self.formatter.format_cv(cv_data)

        header = formatted.get("header", {})
        skills = formatted.get("skills", [])
        leadership = formatted.get("leadership", {})

        leadership_lines = []
        for section_name, items in leadership.items():
            for item in items:
                leadership_lines.append(f"{section_name.replace('_', ' ').title()}: {item}")

        return {
            "full_name": header.get("full_name", ""),
            "employee_id": header.get("employee_id", ""),
            "email": header.get("email", ""),
            "contact_number": header.get("contact_number", ""),
            "grade": header.get("grade", ""),
            "title": header.get("current_title", ""),
            "location": header.get("location", ""),
            "organization": header.get("current_organization", ""),
            "experience": header.get("total_experience", ""),
            "target_role": header.get("target_role", ""),
            "summary": formatted.get("summary", ""),
            "skills": ", ".join(skills),
            "primary_skills": formatted.get("skills", []),
            "secondary_skills": formatted.get("secondary_skills", []),
            "tools_and_platforms": formatted.get("tools_and_platforms", []),
            "ai_frameworks": formatted.get("ai_frameworks", []),
            "cloud_platforms": formatted.get("cloud_platforms", []),
            "operating_systems": formatted.get("operating_systems", []),
            "databases": formatted.get("databases", []),
            "domain_expertise": formatted.get("domain_expertise", []),
            "employment": formatted.get("employment", {}),
            "leadership_lines": leadership_lines,
            "work_experience": formatted.get("work_experience", []),
            "project_experience": formatted.get("project_experience", []),
            "certifications": formatted.get("certifications", []),
            "education": formatted.get("education", []),
            "publications": formatted.get("publications", []),
            "awards": formatted.get("awards", []),
            "languages": formatted.get("languages", []),
        }
