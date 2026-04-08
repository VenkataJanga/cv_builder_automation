from typing import Dict, Any
import yaml
import os
from pathlib import Path

from src.ai.agents.cv_formatting_agent import CVFormattingAgent


class TemplateEngine:
    def __init__(self, template_name: str = "standard_nttdata") -> None:
        self.formatter = CVFormattingAgent()
        self.template_name = template_name
        self.placeholders = self._load_placeholders()

    def _load_placeholders(self) -> Dict[str, str]:
        """Load template placeholders from YAML file"""
        template_path = Path("src/templates") / self.template_name / "placeholders.yml"
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Remove comments for cleaner parsing
                lines = [line for line in content.split('\n') if not line.strip().startswith('#') and line.strip()]
                clean_content = '\n'.join(lines)
                return yaml.safe_load(clean_content) or {}
        except FileNotFoundError:
            return {}
        except yaml.YAMLError:
            return {}

    def render_context(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate render context aligned with template placeholders"""
        formatted = self.formatter.format_cv(cv_data)
        
        # Build context aligned with placeholders.yml structure
        context = self._build_template_context(formatted)
        
        # Ensure all placeholder keys have values (even if empty)
        for placeholder_key in self.placeholders.keys():
            if placeholder_key not in context:
                context[placeholder_key] = ""
        
        return context

    def _build_template_context(self, formatted: Dict[str, Any]) -> Dict[str, Any]:
        """Build template context from formatted CV data"""
        # Handle both formatted structure and direct personal_details structure
        header = formatted.get("header", {})
        personal_details = formatted.get("personal_details", {})
        
        # Merge header and personal_details, with header taking precedence
        personal_info = {**personal_details, **header}
        
        skills = formatted.get("skills", [])
        leadership = formatted.get("leadership", {})

        # Generate leadership lines
        leadership_lines = []
        for section_name, items in leadership.items():
            for item in items:
                leadership_lines.append(f"{section_name.replace('_', ' ').title()}: {item}")

        # Format skills for different representations
        if isinstance(skills, list):
            skills_str = ", ".join(str(skill) for skill in skills)
        elif isinstance(skills, str):
            skills_str = skills
        else:
            skills_str = ""
            
        secondary_skills = formatted.get("secondary_skills", [])
        if isinstance(secondary_skills, list):
            secondary_skills_str = ", ".join(str(skill) for skill in secondary_skills)
        elif isinstance(secondary_skills, str):
            secondary_skills_str = secondary_skills
        else:
            secondary_skills_str = ""
        
        # Format work experience for template
        work_experience = self._format_work_experience(formatted.get("work_experience", []))
        
        # Format project experience for template
        project_experience = self._format_project_experience(formatted.get("project_experience", []))
        
        # Format education for template
        education = self._format_education(formatted.get("education", []))
        
        # Format certifications for template
        certifications = self._format_certifications(formatted.get("certifications", []))
        
        # Format languages for template
        languages = self._format_languages(formatted.get("languages", []))

        # Enhanced field mapping with better data extraction
        context = {
            # Personal Information - Enhanced mapping
            "full_name": self._get_field_value(personal_info, ["full_name", "name"]),
            "employee_id": self._get_field_value(personal_info, ["employee_id", "portal_id", "emp_id"]),
            "email": self._get_field_value(personal_info, ["email", "email_address"]),
            "contact_number": self._get_field_value(personal_info, ["contact_number", "phone", "mobile", "contact"]),
            "current_title": self._get_field_value(personal_info, ["current_title", "title", "designation", "position"]),
            "location": self._get_field_value(personal_info, ["location", "city", "address"]),
            "organization": self._get_field_value(personal_info, ["current_organization", "organization", "company"]),
            "grade": self._get_field_value(personal_info, ["grade", "level"]),
            "experience": self._get_field_value(personal_info, ["total_experience", "experience", "years_of_experience"]),
            "target_role": self._get_field_value(personal_info, ["target_role", "desired_position"]),
            
            # Professional Summary
            "summary": formatted.get("summary", ""),
            
            # Skills & Expertise
            "skills": skills_str,
            "secondary_skills": secondary_skills_str,
            "tools_and_platforms": self._format_list_items(formatted.get("tools_and_platforms", [])),
            "ai_frameworks": self._format_list_items(formatted.get("ai_frameworks", [])),
            "cloud_platforms": self._format_list_items(formatted.get("cloud_platforms", [])),
            "operating_systems": self._format_list_items(formatted.get("operating_systems", [])),
            "databases": self._format_list_items(formatted.get("databases", [])),
            "domain_expertise": self._format_list_items(formatted.get("domain_expertise", [])),
            
            # Experience & Leadership
            "work_experience": work_experience,
            "project_experience": project_experience,
            "leadership_lines": self._format_list_items(leadership_lines),
            
            # Education & Certifications
            "education": education,
            "certifications": certifications,
            
            # Additional Information
            "languages": languages,
            "awards": self._format_list_items(formatted.get("awards", [])),
            "publications": self._format_list_items(formatted.get("publications", [])),
        }
        
        # Apply field-specific formatting
        context = self._apply_field_formatting(context)
        
        return context

    def _format_work_experience(self, work_exp: list) -> str:
        """Format work experience for template insertion"""
        if not work_exp:
            return ""
        
        formatted_items = []
        for exp in work_exp:
            if isinstance(exp, dict):
                parts = []
                if exp.get("title") and exp.get("company"):
                    parts.append(f"{exp['title']} at {exp['company']}")
                if exp.get("duration"):
                    parts.append(f"Duration: {exp['duration']}")
                if exp.get("responsibilities"):
                    parts.extend([f"• {resp}" for resp in exp["responsibilities"]])
                formatted_items.append("\n".join(parts))
            else:
                formatted_items.append(str(exp))
        
        return "\n\n".join(formatted_items)

    def _format_project_experience(self, projects: list) -> str:
        """Format project experience for template insertion"""
        if not projects:
            return ""
        
        formatted_items = []
        for proj in projects:
            if isinstance(proj, dict):
                parts = []
                
                # Project title - make it prominent
                project_name = proj.get("project_name", "")
                if project_name:
                    parts.append(f"PROJECT: {project_name.upper()}")
                
                # Key project details in a structured format
                details = []
                if proj.get("client"):
                    details.append(f"Client: {proj['client']}")
                if proj.get("role"):
                    details.append(f"Role: {proj['role']}")
                if proj.get("duration"):
                    details.append(f"Duration: {proj['duration']}")
                if proj.get("domain"):
                    details.append(f"Domain: {proj['domain']}")
                
                if details:
                    parts.append(" | ".join(details))
                
                # Project description
                if proj.get("project_description"):
                    parts.append(f"\nDescription: {proj['project_description']}")
                
                # Technologies used
                if proj.get("technologies_used"):
                    if isinstance(proj["technologies_used"], list):
                        techs = ", ".join(proj["technologies_used"])
                    else:
                        techs = str(proj["technologies_used"])
                    parts.append(f"Technologies: {techs}")
                
                # Responsibilities
                if proj.get("responsibilities"):
                    responsibilities = proj["responsibilities"]
                    if isinstance(responsibilities, list):
                        parts.append("Key Responsibilities:")
                        for resp in responsibilities:
                            # Clean up responsibility text
                            resp_text = str(resp).strip()
                            if resp_text:
                                # Capitalize first letter if not already
                                if resp_text[0].islower():
                                    resp_text = resp_text[0].upper() + resp_text[1:]
                                # Ensure it ends with a period
                                if not resp_text.endswith('.'):
                                    resp_text += '.'
                                parts.append(f"• {resp_text}")
                    else:
                        parts.append(f"Responsibilities: {responsibilities}")
                
                formatted_items.append("\n".join(parts))
            else:
                # Handle non-dict project data
                formatted_items.append(str(proj))
        
        return "\n\n".join(formatted_items)

    def _format_education(self, education: list) -> str:
        """Format education for template insertion"""
        if not education:
            return ""
        
        formatted_items = []
        for edu in education:
            if isinstance(edu, dict):
                parts = []
                qualification = edu.get("qualification", "")
                specialization = edu.get("specialization", "")
                college = edu.get("college", "")
                university = edu.get("university", "")
                year = edu.get("year_of_passing", "")
                percentage = edu.get("percentage", "")
                
                if qualification or specialization:
                    edu_text = qualification
                    if specialization and specialization != qualification:
                        edu_text += f" in {specialization}" if qualification else specialization
                    
                    if college:
                        edu_text += f" from {college}"
                    elif university:
                        edu_text += f" from {university}"
                    
                    if year:
                        edu_text += f" ({year})"
                    
                    if percentage:
                        edu_text += f" - {percentage}"
                    
                    formatted_items.append(edu_text)
            else:
                formatted_items.append(str(edu))
        
        return "\n".join([f"• {item}" for item in formatted_items])

    def _format_certifications(self, certifications: list) -> str:
        """Format certifications for template insertion"""
        if not certifications:
            return ""
        
        formatted_items = []
        for cert in certifications:
            if isinstance(cert, dict):
                name = cert.get("name", "")
                issuer = cert.get("issuer", "")
                year = cert.get("year", "")
                
                if name:
                    cert_text = name
                    if issuer:
                        cert_text += f" - {issuer}"
                    if year:
                        cert_text += f" ({year})"
                    formatted_items.append(cert_text)
            else:
                formatted_items.append(str(cert))
        
        return "\n".join([f"• {item}" for item in formatted_items])

    def _format_languages(self, languages: list) -> str:
        """Format languages for template insertion"""
        if not languages:
            return ""
        
        formatted_items = []
        for lang in languages:
            if isinstance(lang, dict):
                name = lang.get("name", "")
                level = lang.get("proficiency", "")
                lang_text = name
                if level:
                    lang_text += f" - {level}"
                formatted_items.append(lang_text)
            else:
                formatted_items.append(str(lang))
        
        return "\n".join([f"• {item}" for item in formatted_items])

    def _format_list_items(self, items) -> str:
        """Format list items for template insertion"""
        if not items:
            return ""
        
        # Handle string input that might be mistakenly passed
        if isinstance(items, str):
            # If it's already a formatted string with bullets, return as-is
            if items.startswith("•") or "\n•" in items:
                return items
            # If it's a comma-separated string, split it
            if "," in items:
                item_list = [item.strip() for item in items.split(",")]
                return "\n".join([f"• {item}" for item in item_list if item])
            # Single item
            return f"• {items}"
        
        # Handle list input
        if isinstance(items, list):
            return "\n".join([f"• {str(item)}" for item in items if str(item).strip()])
        
        # Handle other types
        return f"• {str(items)}" if str(items).strip() else ""

    def _get_field_value(self, data_dict: Dict[str, Any], field_names: list) -> str:
        """Get field value from data dictionary, trying multiple field names"""
        for field_name in field_names:
            value = data_dict.get(field_name)
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""

    def _apply_field_formatting(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply specific formatting to fields based on their type"""
        # Format employee ID/portal ID
        if context.get("employee_id"):
            # Ensure employee ID is properly formatted (numbers only, remove spaces)
            emp_id = str(context["employee_id"]).strip().replace(" ", "")
            if emp_id.isdigit():
                context["employee_id"] = emp_id
        
        # Format contact number
        if context.get("contact_number"):
            # Clean contact number (remove spaces, dashes, parentheses)
            contact = str(context["contact_number"]).strip()
            # Remove common formatting characters
            contact = contact.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
            if contact.isdigit() and len(contact) >= 10:
                context["contact_number"] = contact
        
        # Format experience field
        if context.get("experience"):
            exp = str(context["experience"]).strip()
            # Ensure experience has proper format
            if not ("year" in exp.lower() or "yr" in exp.lower() or "+" in exp):
                if exp.replace(".", "").isdigit():
                    context["experience"] = f"{exp}+ years"
        
        # Clean up empty fields
        for key, value in context.items():
            if isinstance(value, str):
                context[key] = value.strip()
                
        return context
