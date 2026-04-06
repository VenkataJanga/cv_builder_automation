from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


class PdfRenderer:
    def render(self, context: dict) -> bytes:
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)

        width, height = A4
        y = height - 50

        def write_line(text, font="Helvetica", size=11, gap=16):
            nonlocal y
            pdf.setFont(font, size)
            pdf.drawString(40, y, str(text))
            y -= gap
            if y < 50:
                pdf.showPage()
                y = height - 50

        # Extract header information (handles both flat and nested structure)
        header = context.get("header", context)
        
        write_line("Professional CV", "Helvetica-Bold", 16, 24)
        full_name = header.get("full_name", "Unnamed Candidate")
        write_line(full_name, "Helvetica-Bold", 13, 18)

        if header.get("employee_id"):
            write_line(f"Employee ID: {header.get('employee_id')}")
        if header.get("email"):
            write_line(f"Email: {header.get('email')}")
        if header.get("contact_number"):
            write_line(f"Contact: {header.get('contact_number')}")
        if header.get("grade"):
            write_line(f"Grade: {header.get('grade')}")
        if header.get("current_title"):
            write_line(f"Title: {header.get('current_title')}")
        if header.get("location"):
            write_line(f"Location: {header.get('location')}")
        if header.get("current_organization"):
            write_line(f"Organization: {header.get('current_organization')}")
        if header.get("total_experience"):
            write_line(f"Total Experience: {header.get('total_experience')}")
        if header.get("target_role"):
            write_line(f"Target Role: {header.get('target_role')}")

        if context.get("summary"):
            write_line("")
            write_line("Professional Summary", "Helvetica-Bold", 12, 18)
            for part in self._split_text(context.get("summary"), 95):
                write_line(part)

        # Use "skills" as primary skills (the preview uses "skills" not "primary_skills")
        skills = context.get("skills", [])
        if skills:
            write_line("")
            write_line("Primary Skills", "Helvetica-Bold", 12, 18)
            for skill in skills:
                write_line(f"- {skill}")
        
        secondary_skills = context.get("secondary_skills", [])
        if secondary_skills:
            write_line("")
            write_line("Secondary Skills", "Helvetica-Bold", 12, 18)
            for skill in secondary_skills:
                write_line(f"- {skill}")
        
        if context.get("tools_and_platforms"):
            write_line("")
            write_line("Tools & Platforms", "Helvetica-Bold", 12, 18)
            for tool in context.get("tools_and_platforms", []):
                write_line(f"- {tool}")
        
        if context.get("ai_frameworks"):
            write_line("")
            write_line("AI Frameworks", "Helvetica-Bold", 12, 18)
            for framework in context.get("ai_frameworks", []):
                write_line(f"- {framework}")
        
        if context.get("cloud_platforms"):
            write_line("")
            write_line("Cloud Platforms", "Helvetica-Bold", 12, 18)
            for platform in context.get("cloud_platforms", []):
                write_line(f"- {platform}")
        
        if context.get("operating_systems"):
            write_line("")
            write_line("Operating Systems", "Helvetica-Bold", 12, 18)
            for os in context.get("operating_systems", []):
                write_line(f"- {os}")
        
        if context.get("databases"):
            write_line("")
            write_line("Databases", "Helvetica-Bold", 12, 18)
            for db in context.get("databases", []):
                write_line(f"- {db}")
        
        if context.get("domain_expertise"):
            write_line("")
            write_line("Domain Expertise", "Helvetica-Bold", 12, 18)
            for domain in context.get("domain_expertise", []):
                write_line(f"- {domain}")

        if context.get("leadership_lines"):
            write_line("")
            write_line("Leadership & Impact", "Helvetica-Bold", 12, 18)
            for line in context.get("leadership_lines", []):
                for part in self._split_text(f"- {line}", 95):
                    write_line(part)
        
        # Leadership dictionary format
        leadership = context.get("leadership", {})
        if leadership:
            write_line("")
            write_line("Leadership & Impact", "Helvetica-Bold", 12, 18)
            for category, items in leadership.items():
                if items:
                    category_title = category.replace("_", " ").title()
                    write_line(f"{category_title}:", "Helvetica-Bold", 11, 16)
                    for item in items:
                        for part in self._split_text(f"  • {item}", 93):
                            write_line(part)
        
        if context.get("work_experience"):
            write_line("")
            write_line("Work Experience", "Helvetica-Bold", 12, 18)
            for exp in context.get("work_experience", []):
                if isinstance(exp, dict):
                    title = exp.get("title", "")
                    company = exp.get("company", "")
                    duration = exp.get("duration", "")
                    if title or company:
                        write_line(f"{title} at {company}", "Helvetica-Bold", 11, 16)
                    if duration:
                        write_line(f"Duration: {duration}")
                    if exp.get("responsibilities"):
                        for resp in exp.get("responsibilities", []):
                            for part in self._split_text(f"  • {resp}", 93):
                                write_line(part)
                    write_line("")
                else:
                    for part in self._split_text(f"• {exp}", 95):
                        write_line(part)
        
        if context.get("project_experience"):
            write_line("")
            write_line("Project Experience", "Helvetica-Bold", 12, 18)
            for proj in context.get("project_experience", []):
                if isinstance(proj, dict):
                    name = proj.get("project_name", "")
                    role = proj.get("role", "")
                    client = proj.get("client", "")
                    duration = proj.get("duration", "")
                    if name:
                        write_line(name, "Helvetica-Bold", 11, 16)
                    if role:
                        write_line(f"Role: {role}")
                    if client:
                        write_line(f"Client: {client}")
                    if duration:
                        write_line(f"Duration: {duration}")
                    if proj.get("description"):
                        for part in self._split_text(proj.get("description"), 95):
                            write_line(part)
                    if proj.get("technologies"):
                        techs = ", ".join(proj.get("technologies", []))
                        for part in self._split_text(f"Technologies: {techs}", 95):
                            write_line(part)
                    write_line("")
                else:
                    for part in self._split_text(f"• {proj}", 95):
                        write_line(part)
        
        certifications = context.get("certifications") or context.get("certifications_and_trainings", [])
        if certifications:
            write_line("")
            write_line("Certifications & Training", "Helvetica-Bold", 12, 18)
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
                        for part in self._split_text(f"• {cert_text}", 95):
                            write_line(part)
                else:
                    for part in self._split_text(f"• {cert}", 95):
                        write_line(part)
        
        if context.get("education"):
            write_line("")
            write_line("Education", "Helvetica-Bold", 12, 18)
            for edu in context.get("education", []):
                if isinstance(edu, dict):
                    degree = edu.get("degree", "")
                    institution = edu.get("institution", "")
                    year = edu.get("year", "")
                    if degree or institution:
                        edu_text = degree
                        if institution:
                            edu_text += f" from {institution}" if degree else institution
                        if year:
                            edu_text += f" ({year})"
                        for part in self._split_text(f"• {edu_text}", 95):
                            write_line(part)
                else:
                    for part in self._split_text(f"• {edu}", 95):
                        write_line(part)
        
        if context.get("publications"):
            write_line("")
            write_line("Publications", "Helvetica-Bold", 12, 18)
            for pub in context.get("publications", []):
                for part in self._split_text(f"• {pub}", 95):
                    write_line(part)
        
        if context.get("awards"):
            write_line("")
            write_line("Awards & Recognition", "Helvetica-Bold", 12, 18)
            for award in context.get("awards", []):
                for part in self._split_text(f"• {award}", 95):
                    write_line(part)
        
        if context.get("languages"):
            write_line("")
            write_line("Languages", "Helvetica-Bold", 12, 18)
            langs = context.get("languages", [])
            if isinstance(langs, list):
                for lang in langs:
                    if isinstance(lang, dict):
                        name = lang.get("name", "")
                        level = lang.get("proficiency", "")
                        lang_text = name
                        if level:
                            lang_text += f" - {level}"
                        write_line(f"• {lang_text}")
                    else:
                        write_line(f"• {lang}")

        pdf.save()
        buffer.seek(0)
        return buffer.read()

    def _split_text(self, text: str, max_chars: int) -> list[str]:
        words = str(text).split()
        if not words:
            return []
        lines = []
        current = []
        for word in words:
            trial = " ".join(current + [word])
            if len(trial) <= max_chars:
                current.append(word)
            else:
                lines.append(" ".join(current))
                current = [word]
        if current:
            lines.append(" ".join(current))
        return lines
