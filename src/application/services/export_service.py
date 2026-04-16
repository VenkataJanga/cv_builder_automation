"""
Export Service - Integrated with Canonical CV Schema
Handles CV export operations with consistent data structure across all input modes.
"""

import logging
from typing import Dict, Any, Optional

from src.application.services.preview_service import PreviewService
from src.infrastructure.rendering.template_engine import TemplateEngine
from src.infrastructure.rendering.docx_renderer import DocxRenderer
from src.infrastructure.rendering.pdf_renderer import PdfRenderer
from src.domain.cv.models.canonical_cv_schema import CanonicalCVSchema, SourceType
from src.application.services.schema_mapper_service import SchemaMapperService


class ExportService:
    """
    Service for exporting CV data to various formats with Canonical CV Schema integration
    
    This service ensures that all export data comes from the standardized
    Canonical CV Schema regardless of the input source.
    """
    
    def __init__(self) -> None:
        self.preview_service = PreviewService()
        self.template_engine = TemplateEngine()
        self.docx_renderer = DocxRenderer()
        self.pdf_renderer = PdfRenderer()
        self.schema_mapper = SchemaMapperService()
        self.logger = logging.getLogger(__name__)

    def export_docx(self, cv_data: dict, template_style: str = "standard") -> bytes:
        """
        Export CV as DOCX with template style selection.
        
        Args:
            cv_data: CV data dictionary
            template_style: Template style to use
                - "standard": Traditional table-based NTT DATA format (for internal use)
                - "modern": Clean 2026 format with minimal tables (for external clients)
                - "hybrid": Best of both - structured tables for skills, clean format for experience
        
        Returns:
            DOCX file as bytes
        """
        # Normalize CV data through preview formatting so export matches UI preview
        cv_data = self._normalize_cv_data(cv_data)

        # For DOCX export, bypass template engine to preserve structured data
        # The DOCX renderer has its own field mapping and table population logic
        context = self._prepare_docx_context(cv_data)
        
        # Create renderer with template style
        renderer = DocxRenderer(template_style=template_style)
        return renderer.render(context)

    def export_pdf(self, cv_data: dict, template_style: str = "standard") -> bytes:
        """
        Export CV as PDF with template style selection.
        
        Args:
            cv_data: CV data dictionary
            template_style: Template style to use (standard/modern/hybrid)
        
        Returns:
            PDF file as bytes
        """
        cv_data = self._normalize_cv_data(cv_data)
        context = self.template_engine.render_context(cv_data)
        # PDF rendering can also support template styles
        return self.pdf_renderer.render(context, template_style=template_style)

    def export_docx_from_canonical(self, canonical_data: CanonicalCVSchema, template_style: str = "standard") -> bytes:
        """
        Export CV as DOCX directly from Canonical CV Schema
        
        Args:
            canonical_data: CanonicalCVSchema instance
            template_style: Template style to use
        
        Returns:
            DOCX file as bytes
        """
        try:
            self.logger.info("Exporting DOCX from canonical schema")
            
            # Use preview service to convert canonical data to formatter format
            formatted_data = self.preview_service.build_preview_from_canonical(canonical_data)
            
            # Prepare context for DOCX rendering
            context = self._prepare_docx_context(formatted_data)
            
            # Create renderer with template style
            renderer = DocxRenderer(template_style=template_style)
            return renderer.render(context)
            
        except Exception as e:
            self.logger.error(f"Error exporting DOCX from canonical schema: {str(e)}")
            raise

    def _normalize_cv_data(self, cv_data: dict) -> dict:
        """
        Phase 4: Normalize CV data from canonical schema to preview format for export
        
        This method now expects data to already be in canonical format or preview format.
        All fallback logic has been removed - canonical_cv is the single source of truth.
        """
        if not isinstance(cv_data, dict):
            return cv_data
        
        # Check if data is already in preview format (has 'header' or 'summary' keys)
        if 'header' in cv_data or 'summary' in cv_data:
            self.logger.info("Data already in preview format, using as-is for export")
            return cv_data
        
        # Otherwise, assume canonical format and convert to preview format
        try:
            self.logger.info("Converting canonical CV to preview format for export")
            canonical_data = CanonicalCVSchema(**cv_data)
            normalized = self.preview_service.build_preview_from_canonical(canonical_data)
            return normalized
        except Exception as e:
            self.logger.error(f"Error converting canonical CV to preview format: {str(e)}")
            raise ValueError(f"Invalid canonical CV data for export: {str(e)}")

    def _prepare_docx_context(self, cv_data: dict) -> dict:
        """Prepare context specifically for DOCX rendering without losing structured data"""
        # Handle both formatted structure and direct personal_details structure
        header = cv_data.get("header", {})
        personal_details = cv_data.get("personal_details", {})
        personal_info = cv_data.get("personal_information", {})
        contact_info = cv_data.get("contact_info", {})
        
        # Enhanced merge strategy: Try all possible field variations across all data structures
        # This fixes the phone number, portal ID, and other missing field issues
        # Priority: formatted header first, then various personal structures, then root cv_data
        all_data_sources = [header, personal_details, personal_info, contact_info, cv_data]
        
        # Enhanced field mapping with better data extraction
        context = {
            # Personal Information - Enhanced mapping with comprehensive field search
            "full_name": self._get_field_value_from_sources(all_data_sources, ["full_name", "name", "candidate_name"]),
            "employee_id": self._get_field_value_from_sources(all_data_sources, ["employee_id", "portal_id", "emp_id", "staff_id", "employee_number"]),
            "email": self._get_field_value_from_sources(all_data_sources, ["email", "email_address", "email_id"]),
            "contact_number": self._get_field_value_from_sources(all_data_sources, ["contact_number", "phone", "mobile", "contact", "phone_number", "mobile_number"]),
            "current_title": self._get_field_value_from_sources(all_data_sources, ["current_title", "title", "designation", "position", "job_title"]),
            "location": self._get_field_value_from_sources(all_data_sources, ["location", "city", "address", "current_location"]),
            "organization": self._get_field_value_from_sources(all_data_sources, ["current_organization", "organization", "company", "employer", "current_company"]),
            "grade": self._get_field_value_from_sources(all_data_sources, ["grade", "level", "job_level"]),
            "experience": self._get_field_value_from_sources(all_data_sources, ["total_experience", "experience", "years_of_experience", "work_experience"]),
            "target_role": self._get_field_value_from_sources(all_data_sources, ["target_role", "desired_position", "target_position"]),
            
            # Professional Summary
            "summary": cv_data.get("summary", ""),
            
            # Skills & Expertise - Enhanced extraction with fallbacks
            "skills": self._format_skills_for_docx(self._extract_skills(cv_data, "primary")),
            "secondary_skills": self._format_skills_for_docx(self._extract_skills(cv_data, "secondary")),
            "tools_and_platforms": self._extract_skill_category(cv_data, ["tools_and_platforms", "tools", "platforms"]),
            "ai_frameworks": self._extract_skill_category(cv_data, ["ai_frameworks", "ai_tools", "ml_frameworks"]),
            "cloud_platforms": self._extract_skill_category(cv_data, ["cloud_platforms", "cloud", "cloud_services"]),
            "operating_systems": self._extract_skill_category(cv_data, ["operating_systems", "os", "systems"]),
            "databases": self._extract_skill_category(cv_data, ["databases", "db", "database_systems"]),
            "domain_expertise": self._extract_skill_category(cv_data, ["domain_expertise", "domains", "business_domains"]),
            
            # Formatted sections for template placeholders
            "core_competencies": self._format_core_competencies(cv_data),
            "technical_skills_section": self._format_technical_skills_section(cv_data),
            "key_achievements_section": self._format_key_achievements(cv_data.get("key_achievements", [])),
            "experience_section": self._format_experience_section(cv_data.get("work_experience", [])),
            "projects_section": self._format_projects_section(cv_data.get("project_experience", [])),
            "education_section": self._format_education_section(cv_data.get("education", [])),
            "certifications_section": self._format_certifications_section(cv_data.get("certifications", [])),
            
            # Experience & Leadership - PRESERVE STRUCTURED DATA
            "work_experience": cv_data.get("work_experience", []),
            "project_experience": cv_data.get("project_experience", []),  # Keep as list for table population
            "leadership_lines": cv_data.get("leadership", {}),
            
            # Education & Certifications - PRESERVE STRUCTURED DATA + Individual Fields
            "education": cv_data.get("education", []),
            "certifications": cv_data.get("certifications", []),
            
            # Individual education fields for template placeholders
            **self._extract_primary_education_fields(cv_data.get("education", [])),
            
            # Individual certification fields for template placeholders  
            **self._extract_primary_certification_fields(cv_data.get("certifications", [])),
            
            # Additional Information
            "languages": cv_data.get("languages", []),
            "awards": cv_data.get("awards", []),
            "publications": cv_data.get("publications", []),
        }
        
        # Apply basic field formatting without losing structure
        context = self._apply_basic_formatting(context)
        
        # ADD TEMPLATE PLACEHOLDER ALIASES
        # The template uses specific placeholder names that differ from our internal field names
        # Map our field names to template placeholder names
        context['phone'] = context.get('contact_number', '')
        context['portal_id'] = context.get('employee_id', '')
        context['job_title'] = context.get('current_title', '')
        context['professional_summary'] = context.get('summary', '')
        
        return context

    def _get_field_value_from_sources(self, data_sources: list, field_names: list) -> str:
        """Get field value from multiple data sources, trying multiple field names"""
        for data_dict in data_sources:
            if not isinstance(data_dict, dict):
                continue
            for field_name in field_names:
                value = data_dict.get(field_name)
                if value is not None and str(value).strip():
                    return str(value).strip()
        return ""

    def _get_field_value(self, data_dict: dict, field_names: list) -> str:
        """Get field value from data dictionary, trying multiple field names"""
        for field_name in field_names:
            value = data_dict.get(field_name)
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""

    def _extract_skills(self, cv_data: dict, skill_type: str):
        """
        Extract skills with enhanced fallback logic for primary/secondary skills.
        
        Args:
            cv_data: CV data dictionary
            skill_type: "primary" or "secondary"
        
        Returns:
            List of skills or empty list
        """
        skills_data = cv_data.get("skills", [])
        
        # Handle structured skills object
        if isinstance(skills_data, dict):
            if skill_type == "primary":
                return skills_data.get("primary_skills", []) or skills_data.get("skills", [])
            elif skill_type == "secondary":
                return skills_data.get("secondary_skills", [])
        
        # Handle direct skills list (assume primary)
        elif isinstance(skills_data, list) and skill_type == "primary":
            return skills_data
        
        # Handle direct field access
        if skill_type == "secondary":
            return cv_data.get("secondary_skills", [])
        
        return []

    def _extract_skill_category(self, cv_data: dict, field_names: list):
        """
        Extract skill category with fallback field names.
        
        Args:
            cv_data: CV data dictionary
            field_names: List of possible field names to try
            
        Returns:
            List of skills or formatted string
        """
        # Try direct field access first
        for field_name in field_names:
            value = cv_data.get(field_name)
            if value:
                return value
        
        # Try nested skills object
        skills_data = cv_data.get("skills", {})
        if isinstance(skills_data, dict):
            for field_name in field_names:
                value = skills_data.get(field_name)
                if value:
                    return value
        
        return []

    def _extract_primary_education_fields(self, education_list: list) -> dict:
        """
        Extract individual education fields for template placeholders.
        Uses the first/primary education entry or most recent by year.
        
        NOTE: The template uses {{institution}} for "University/Institution" column,
        so we intelligently combine university + institution for that field.
        Similarly, {{grade}} is used for "Grade/GPA" column, so we format all grade variants there.
        
        Args:
            education_list: List of education dictionaries
            
        Returns:
            Dictionary with individual education fields for template
        """
        if not education_list or not isinstance(education_list, list):
            return {
                "degree": "",
                "institution": "",
                "year": "",
                "grade": ""
            }
        
        # Find primary education entry (first or most recent)
        primary_education = education_list[0]
        
        # If multiple entries, try to find the most recent
        if len(education_list) > 1:
            dated_entries = []
            for edu in education_list:
                if isinstance(edu, dict):
                    year = edu.get("year") or edu.get("year_of_completion") or edu.get("graduation_year") or edu.get("completion_year")
                    if year:
                        try:
                            # Extract numeric year
                            year_num = int(str(year).strip())
                            dated_entries.append((year_num, edu))
                        except (ValueError, TypeError):
                            pass
            
            # Use most recent if we found dated entries
            if dated_entries:
                primary_education = max(dated_entries, key=lambda x: x[0])[1]
        
        # Extract institution and university separately first
        institution = self._get_field_value(primary_education, ["institution", "college", "school"])
        university = self._get_field_value(primary_education, ["university", "affiliated_university"])
        
        # Intelligently combine institution and university for the template
        # Template expects: "Institution, University" or just one if only one is available
        combined_institution = ""
        if institution and university and institution != university:
            combined_institution = f"{institution}, {university}"
        elif university:
            combined_institution = university
        elif institution:
            combined_institution = institution
        
        # Extract grade with all variations (percentile, percentage, CGPA, GPA)
        grade = self._get_field_value(primary_education, ["grade", "percentile", "percentage", "cgpa", "gpa", "marks", "score"])
        
        return {
            "degree": self._get_field_value(primary_education, ["degree", "qualification", "program"]),
            "institution": combined_institution,
            "year": self._get_field_value(primary_education, ["year", "year_of_completion", "graduation_year", "completion_year"]),
            "grade": grade
        }

    def _extract_primary_certification_fields(self, certifications_list: list) -> dict:
        """
        Extract individual certification fields for template placeholders.
        Uses the first/primary certification entry.
        
        Args:
            certifications_list: List of certification dictionaries
            
        Returns:
            Dictionary with individual certification fields for template
        """
        if not certifications_list or not isinstance(certifications_list, list):
            return {
                "certification": "",
                "issuer": "",
                "cert_year": ""
            }
        
        # Find first valid certification entry
        primary_cert = None
        for cert in certifications_list:
            if isinstance(cert, dict) and cert.get("name"):
                primary_cert = cert
                break
        
        if not primary_cert:
            return {
                "certification": "",
                "issuer": "",
                "cert_year": ""
            }
        
        # Extract fields with fallback names
        return {
            "certification": self._get_field_value(primary_cert, ["name", "certification", "title"]),
            "issuer": self._get_field_value(primary_cert, ["issuer", "organization", "provider", "authority"]),
            "cert_year": self._get_field_value(primary_cert, ["year", "date", "completion_date", "issue_date"])
        }

    def _format_skills_for_docx(self, skills) -> str:
        """
        Format skills for DOCX rendering with optional proficiency levels.
        Supports both formats:
        - Simple: ["Python", "ML"]
        - With proficiency: [{"name": "Python", "proficiency": "Expert"}, {"name": "ML", "proficiency": "Advanced"}]
        """
        if isinstance(skills, list):
            formatted_skills = []
            for skill in skills:
                if isinstance(skill, dict):
                    # Handle dict format with proficiency
                    name = skill.get("name", "")
                    proficiency = skill.get("proficiency", "")
                    if name.strip():
                        if proficiency and proficiency.strip():
                            formatted_skills.append(f"{name.strip()} ({proficiency.strip()})")
                        else:
                            formatted_skills.append(name.strip())
                elif isinstance(skill, str) and skill.strip():
                    # Handle simple string format
                    formatted_skills.append(skill.strip())
            return ", ".join(formatted_skills)
        elif isinstance(skills, str):
            return skills
        else:
            return ""

    def _apply_basic_formatting(self, context: dict) -> dict:
        """Apply basic formatting without losing structured data"""
        # Format employee ID/portal ID
        if context.get("employee_id"):
            emp_id = str(context["employee_id"]).strip().replace(" ", "")
            if emp_id.isdigit():
                context["employee_id"] = emp_id
        
        # Format contact number
        if context.get("contact_number"):
            contact = str(context["contact_number"]).strip()
            contact = contact.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
            if contact.isdigit() and len(contact) >= 10:
                context["contact_number"] = contact
        
        # Format experience field
        if context.get("experience"):
            exp = str(context["experience"]).strip()
            if not ("year" in exp.lower() or "yr" in exp.lower() or "+" in exp):
                if exp.replace(".", "").isdigit():
                    context["experience"] = f"{exp}+ years"
        
        # Clean up empty string fields
        for key, value in context.items():
            if isinstance(value, str):
                context[key] = value.strip()
                
        return context

    def _format_key_achievements(self, achievements: list) -> str:
        """
        Format key achievements/impact metrics section (2026 feature).
        Only displays if data exists.
        
        Args:
            achievements: List of achievement strings
            
        Returns:
            Formatted achievements section or empty string
        """
        if not achievements:
            return ""
        
        formatted = []
        for achievement in achievements:
            if isinstance(achievement, str) and achievement.strip():
                achievement_text = achievement.strip()
                if not achievement_text.startswith("•"):
                    achievement_text = f"• {achievement_text}"
                formatted.append(achievement_text)
        
        return "\n".join(formatted) if formatted else ""

    def _format_core_competencies(self, cv_data: dict) -> str:
        """Format core competencies/skills as bullet-point text"""
        skills = cv_data.get("skills", [])
        if isinstance(skills, dict):
            skills = skills.get("primary_skills", []) or skills.get("secondary_skills", []) or []

        if not skills:
            return ""
        
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        
        formatted = []
        for skill in skills:
            if isinstance(skill, str) and skill.strip():
                formatted.append(f"• {skill.strip()}")
        
        return "\n".join(formatted) if formatted else ""

    def _format_technical_skills_section(self, cv_data: dict) -> str:
        """Format all technical skills into organized categories with optional proficiency levels"""
        sections = []
        
        skills = cv_data.get("skills", [])
        if isinstance(skills, dict):
            skills = skills.get("primary_skills", [])
        if skills:
            skills_text = self._format_skills_for_docx(skills)
            if skills_text:
                sections.append(f"Primary Skills: {skills_text}")
        
        secondary = cv_data.get("secondary_skills", [])
        if not secondary and isinstance(cv_data.get("skills"), dict):
            secondary = cv_data.get("skills", {}).get("secondary_skills", [])
        if secondary:
            sec_text = self._format_skills_for_docx(secondary)
            if sec_text:
                sections.append(f"Secondary Skills: {sec_text}")
        
        tools = cv_data.get("tools_and_platforms", [])
        if not tools and isinstance(cv_data.get("skills"), dict):
            tools = cv_data.get("skills", {}).get("tools_and_platforms", [])
        if tools:
            if isinstance(tools, list):
                tools_text = ", ".join(str(t) for t in tools if str(t).strip())
            else:
                tools_text = str(tools)
            if tools_text:
                sections.append(f"Tools & Platforms: {tools_text}")
        
        ai = cv_data.get("ai_frameworks", [])
        if not ai and isinstance(cv_data.get("skills"), dict):
            ai = cv_data.get("skills", {}).get("ai_frameworks", [])
        if ai:
            ai_text = self._format_skills_for_docx(ai)
            if ai_text:
                sections.append(f"AI Frameworks: {ai_text}")
        
        cloud = cv_data.get("cloud_platforms", [])
        if not cloud and isinstance(cv_data.get("skills"), dict):
            cloud = cv_data.get("skills", {}).get("cloud_platforms", [])
        if cloud:
            if isinstance(cloud, list):
                cloud_text = ", ".join(str(c) for c in cloud if str(c).strip())
            else:
                cloud_text = str(cloud)
            if cloud_text:
                sections.append(f"Cloud Platforms: {cloud_text}")
        
        databases = cv_data.get("databases", [])
        if not databases and isinstance(cv_data.get("skills"), dict):
            databases = cv_data.get("skills", {}).get("databases", [])
        if databases:
            if isinstance(databases, list):
                db_text = ", ".join(str(d) for d in databases if str(d).strip())
            else:
                db_text = str(databases)
            if db_text:
                sections.append(f"Databases: {db_text}")
        
        os_list = cv_data.get("operating_systems", [])
        if not os_list and isinstance(cv_data.get("skills"), dict):
            os_list = cv_data.get("skills", {}).get("operating_systems", [])
        if os_list:
            if isinstance(os_list, list):
                os_text = ", ".join(str(o) for o in os_list if str(o).strip())
            else:
                os_text = str(os_list)
            if os_text:
                sections.append(f"Operating Systems: {os_text}")
        
        domain = cv_data.get("domain_expertise", [])
        if not domain and isinstance(cv_data.get("skills"), dict):
            domain = cv_data.get("skills", {}).get("domain_expertise", [])
        if domain:
            if isinstance(domain, list):
                domain_text = ", ".join(str(d) for d in domain if str(d).strip())
            else:
                domain_text = str(domain)
            if domain_text:
                sections.append(f"Domain Expertise: {domain_text}")
        
        return "\n\n".join(sections) if sections else ""

    def _format_experience_section(self, work_experience: list) -> str:
        """Format work experience as text"""
        if not work_experience:
            return ""
        
        formatted = []
        for exp in work_experience:
            if not isinstance(exp, dict):
                continue
            
            # Extract fields with multiple possible keys
            title = exp.get("title") or exp.get("position") or exp.get("role") or ""
            company = exp.get("company") or exp.get("organization") or ""
            duration = exp.get("duration") or exp.get("period") or ""
            location = exp.get("location") or ""
            description = exp.get("description") or exp.get("responsibilities") or ""
            
            exp_text = []
            
            # Title and Company
            if title and company:
                exp_text.append(f"{title} | {company}")
            elif title:
                exp_text.append(title)
            elif company:
                exp_text.append(company)
            
            # Duration and Location
            details = []
            if duration:
                details.append(duration)
            if location:
                details.append(location)
            if details:
                exp_text.append(" | ".join(details))
            
            # Description/Responsibilities
            if description:
                if isinstance(description, list):
                    for item in description:
                        exp_text.append(f"• {item}")
                else:
                    exp_text.append(str(description))
            
            if exp_text:
                formatted.append("\n".join(exp_text))
        
        return "\n\n".join(formatted) if formatted else ""

    def _format_projects_section(self, project_experience: list) -> str:
        """Format project experience as text"""
        if not project_experience:
            return ""
        
        formatted = []
        for proj in project_experience:
            if not isinstance(proj, dict):
                continue
            
            # Extract fields with multiple possible keys
            name = proj.get("project_name") or proj.get("name") or proj.get("title") or ""
            client = proj.get("client") or proj.get("company") or ""
            role = proj.get("role") or proj.get("position") or ""
            duration = proj.get("duration") or proj.get("period") or ""
            description = proj.get("description") or proj.get("summary") or ""
            technologies = proj.get("technologies") or proj.get("tech_stack") or []
            responsibilities = proj.get("responsibilities") or proj.get("key_achievements") or []
            
            proj_text = []
            
            # Project Name and Client
            if name and client:
                proj_text.append(f"Project: {name} | Client: {client}")
            elif name:
                proj_text.append(f"Project: {name}")
            
            # Role and Duration
            details = []
            if role:
                details.append(f"Role: {role}")
            if duration:
                details.append(f"Duration: {duration}")
            if details:
                proj_text.append(" | ".join(details))
            
            # Description
            if description:
                proj_text.append(f"\n{description}")
            
            # Technologies
            if technologies:
                if isinstance(technologies, list):
                    tech_text = ", ".join(str(t) for t in technologies if str(t).strip())
                else:
                    tech_text = str(technologies)
                if tech_text:
                    proj_text.append(f"Technologies: {tech_text}")
            
            # Responsibilities
            if responsibilities:
                proj_text.append("\nKey Responsibilities:")
                if isinstance(responsibilities, list):
                    for resp in responsibilities:
                        proj_text.append(f"• {resp}")
                else:
                    proj_text.append(str(responsibilities))
            
            if proj_text:
                formatted.append("\n".join(proj_text))
        
        return "\n\n".join(formatted) if formatted else ""

    def _format_education_section(self, education: list) -> str:
        """Format education as text"""
        if not education:
            return ""
        
        formatted = []
        for edu in education:
            if not isinstance(edu, dict):
                continue
            
            # Extract fields with multiple possible keys
            degree = edu.get("degree") or edu.get("qualification") or ""
            field = edu.get("field_of_study") or edu.get("specialization") or edu.get("major") or ""
            institution = edu.get("institution") or edu.get("university") or edu.get("college") or ""
            year = edu.get("year") or edu.get("graduation_year") or edu.get("completion_year") or ""
            grade = edu.get("grade") or edu.get("gpa") or edu.get("percentage") or ""
            
            edu_text = []
            
            # Degree and Field
            if degree and field:
                edu_text.append(f"{degree} in {field}")
            elif degree:
                edu_text.append(degree)
            
            # Institution
            if institution:
                edu_text.append(institution)
            
            # Year and Grade
            details = []
            if year:
                details.append(str(year))
            if grade:
                details.append(f"Grade: {grade}")
            if details:
                edu_text.append(" | ".join(details))
            
            if edu_text:
                formatted.append("\n".join(edu_text))
        
        return "\n\n".join(formatted) if formatted else ""

    def _format_certifications_section(self, certifications: list) -> str:
        """Format certifications as text"""
        if not certifications:
            return ""
        
        formatted = []
        for cert in certifications:
            if not isinstance(cert, dict):
                # Handle string certifications
                if isinstance(cert, str) and cert.strip():
                    formatted.append(f"• {cert.strip()}")
                continue
            
            # Extract fields with multiple possible keys
            name = cert.get("name") or cert.get("certification") or cert.get("title") or ""
            issuer = cert.get("issuer") or cert.get("organization") or cert.get("provider") or ""
            year = cert.get("year") or cert.get("date") or cert.get("completion_date") or ""
            credential = cert.get("credential_id") or cert.get("id") or ""
            
            cert_text = []
            
            # Certification Name
            if name:
                cert_text.append(f"• {name}")
            
            # Issuer and Year
            details = []
            if issuer:
                details.append(issuer)
            if year:
                details.append(str(year))
            if details:
                cert_text.append("  " + " | ".join(details))
            
            # Credential ID
            if credential:
                cert_text.append(f"  Credential ID: {credential}")
            
            if cert_text:
                formatted.append("\n".join(cert_text))
        
        return "\n".join(formatted) if formatted else ""
