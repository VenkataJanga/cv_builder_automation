from io import BytesIO
from docx import Document


class DocxRenderer:
    def render(self, context: dict) -> bytes:
        doc = Document()
        doc.add_heading("Professional CV", level=1)

        # Extract header information (handles both flat and nested structure)
        header = context.get("header", context)
        
        full_name = header.get("full_name", "Unnamed Candidate")
        doc.add_heading(full_name, level=2)
        
        if header.get("employee_id"):
            doc.add_paragraph(f"Employee ID: {header.get('employee_id')}")
        if header.get("email"):
            doc.add_paragraph(f"Email: {header.get('email')}")
        if header.get("contact_number"):
            doc.add_paragraph(f"Contact: {header.get('contact_number')}")
        if header.get("grade"):
            doc.add_paragraph(f"Grade: {header.get('grade')}")
        if header.get("current_title"):
            doc.add_paragraph(f"Title: {header.get('current_title')}")
        if header.get("location"):
            doc.add_paragraph(f"Location: {header.get('location')}")
        if header.get("current_organization"):
            doc.add_paragraph(f"Organization: {header.get('current_organization')}")
        if header.get("total_experience"):
            doc.add_paragraph(f"Total Experience: {header.get('total_experience')}")
        if header.get("target_role"):
            doc.add_paragraph(f"Target Role: {header.get('target_role')}")

        if context.get("summary"):
            doc.add_heading("Professional Summary", level=2)
            doc.add_paragraph(context.get("summary"))

        # Use "skills" as primary skills (the preview uses "skills" not "primary_skills")
        skills = context.get("skills", [])
        if skills:
            doc.add_heading("Primary Skills", level=2)
            for skill in skills:
                doc.add_paragraph(skill, style="List Bullet")
        
        secondary_skills = context.get("secondary_skills", [])
        if secondary_skills:
            doc.add_heading("Secondary Skills", level=2)
            for skill in secondary_skills:
                doc.add_paragraph(skill, style="List Bullet")
        
        if context.get("tools_and_platforms"):
            doc.add_heading("Tools & Platforms", level=2)
            for tool in context.get("tools_and_platforms", []):
                doc.add_paragraph(tool, style="List Bullet")
        
        if context.get("ai_frameworks"):
            doc.add_heading("AI Frameworks", level=2)
            for framework in context.get("ai_frameworks", []):
                doc.add_paragraph(framework, style="List Bullet")
        
        if context.get("cloud_platforms"):
            doc.add_heading("Cloud Platforms", level=2)
            for platform in context.get("cloud_platforms", []):
                doc.add_paragraph(platform, style="List Bullet")
        
        if context.get("operating_systems"):
            doc.add_heading("Operating Systems", level=2)
            for os in context.get("operating_systems", []):
                doc.add_paragraph(os, style="List Bullet")
        
        if context.get("databases"):
            doc.add_heading("Databases", level=2)
            for db in context.get("databases", []):
                doc.add_paragraph(db, style="List Bullet")
        
        if context.get("domain_expertise"):
            doc.add_heading("Domain Expertise", level=2)
            for domain in context.get("domain_expertise", []):
                doc.add_paragraph(domain, style="List Bullet")

        if context.get("leadership_lines"):
            doc.add_heading("Leadership & Impact", level=2)
            for line in context.get("leadership_lines", []):
                doc.add_paragraph(line, style="List Bullet")
        
        # Leadership dictionary format
        leadership = context.get("leadership", {})
        if leadership:
            doc.add_heading("Leadership & Impact", level=2)
            for category, items in leadership.items():
                if items:
                    category_title = category.replace("_", " ").title()
                    doc.add_paragraph(f"{category_title}:", style="Heading 3")
                    for item in items:
                        doc.add_paragraph(item, style="List Bullet")

        if context.get("work_experience"):
            doc.add_heading("Work Experience", level=2)
            for exp in context.get("work_experience", []):
                if isinstance(exp, dict):
                    title = exp.get("title", "")
                    company = exp.get("company", "")
                    duration = exp.get("duration", "")
                    if title or company:
                        doc.add_paragraph(f"{title} at {company}", style="Heading 3")
                    if duration:
                        doc.add_paragraph(f"Duration: {duration}")
                    if exp.get("responsibilities"):
                        for resp in exp.get("responsibilities", []):
                            doc.add_paragraph(resp, style="List Bullet")
                    doc.add_paragraph("")  # Add spacing
                else:
                    doc.add_paragraph(str(exp), style="List Bullet")

        if context.get("project_experience"):
            doc.add_heading("Project Experience", level=2)
            for proj in context.get("project_experience", []):
                if isinstance(proj, dict):
                    name = proj.get("project_name", "")
                    role = proj.get("role", "")
                    client = proj.get("client", "")
                    duration = proj.get("duration", "")
                    if name:
                        doc.add_paragraph(name, style="Heading 3")
                    if role:
                        doc.add_paragraph(f"Role: {role}")
                    if client:
                        doc.add_paragraph(f"Client: {client}")
                    if duration:
                        doc.add_paragraph(f"Duration: {duration}")
                    
                    # Fix: Use correct field name for project description
                    if proj.get("project_description"):
                        doc.add_paragraph(proj.get("project_description"))
                    
                    # Fix: Use correct field name for technologies
                    if proj.get("technologies_used"):
                        techs = ", ".join(proj.get("technologies_used", []))
                        doc.add_paragraph(f"Technologies: {techs}")
                    
                    # Add missing responsibilities section
                    if proj.get("responsibilities"):
                        doc.add_paragraph("Key Responsibilities:", style="Heading 4")
                        for resp in proj.get("responsibilities", []):
                            doc.add_paragraph(resp, style="List Bullet")
                    
                    doc.add_paragraph("")  # Add spacing
                else:
                    doc.add_paragraph(str(proj), style="List Bullet")

        certifications = context.get("certifications") or context.get("certifications_and_trainings", [])
        if certifications:
            doc.add_heading("Certifications & Training", level=2)
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
                        doc.add_paragraph(cert_text, style="List Bullet")
                else:
                    doc.add_paragraph(str(cert), style="List Bullet")

        if context.get("education"):
            doc.add_heading("Education", level=2)
            for edu in context.get("education", []):
                if isinstance(edu, dict):
                    # Use correct field names from enhanced transcript parser
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
                        
                        doc.add_paragraph(edu_text, style="List Bullet")
                else:
                    doc.add_paragraph(str(edu), style="List Bullet")
        
        if context.get("publications"):
            doc.add_heading("Publications", level=2)
            for pub in context.get("publications", []):
                doc.add_paragraph(str(pub), style="List Bullet")
        
        if context.get("awards"):
            doc.add_heading("Awards & Recognition", level=2)
            for award in context.get("awards", []):
                doc.add_paragraph(str(award), style="List Bullet")
        
        if context.get("languages"):
            doc.add_heading("Languages", level=2)
            langs = context.get("languages", [])
            if isinstance(langs, list):
                for lang in langs:
                    if isinstance(lang, dict):
                        name = lang.get("name", "")
                        level = lang.get("proficiency", "")
                        lang_text = name
                        if level:
                            lang_text += f" - {level}"
                        doc.add_paragraph(lang_text, style="List Bullet")
                    else:
                        doc.add_paragraph(str(lang), style="List Bullet")

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.read()
