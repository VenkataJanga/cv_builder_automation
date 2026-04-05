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
