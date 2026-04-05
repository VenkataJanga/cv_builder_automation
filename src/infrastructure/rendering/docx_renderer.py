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

        if context.get("work_experience"):
            doc.add_heading("Work Experience", level=2)
            for item in context.get("work_experience", []):
                doc.add_paragraph(str(item), style="List Bullet")

        if context.get("project_experience"):
            doc.add_heading("Project Experience", level=2)
            for item in context.get("project_experience", []):
                doc.add_paragraph(str(item), style="List Bullet")

        if context.get("certifications"):
            doc.add_heading("Certifications", level=2)
            for item in context.get("certifications", []):
                doc.add_paragraph(str(item), style="List Bullet")

        if context.get("education"):
            doc.add_heading("Education", level=2)
            for item in context.get("education", []):
                doc.add_paragraph(str(item), style="List Bullet")

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.read()
