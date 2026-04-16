from io import BytesIO
from typing import Dict, Any
import tempfile
import os

from src.core.logging.logger import get_logger

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import inch
except ImportError:
    # Fallback for environments where reportlab is not available
    A4 = None
    canvas = None

# Try to import docx2pdf for DOCX to PDF conversion
try:
    import docx2pdf
    DOCX2PDF_AVAILABLE = True
except ImportError:
    DOCX2PDF_AVAILABLE = False

# Try to import alternative PDF libraries
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False


logger = get_logger(__name__)


def print(*args, **kwargs):
    message = " ".join(str(arg) for arg in args)
    if message.startswith("Error"):
        logger.error(message)
    elif message.startswith("Warning"):
        logger.warning(message)
    else:
        logger.info(message)


class PdfRenderer:
    def __init__(self, template_name: str = "standard_nttdata"):
        self.template_name = template_name

    def render(self, context: Dict[str, Any]) -> bytes:
        """Render CV to PDF using template-based approach"""
        try:
            # Method 1: Convert from DOCX template
            if DOCX2PDF_AVAILABLE:
                return self._render_from_docx(context)
            
            # Method 2: Direct PDF generation with template styling
            elif A4 and canvas:
                return self._render_direct_pdf(context)
            
            # Method 3: HTML to PDF conversion
            elif WEASYPRINT_AVAILABLE:
                return self._render_from_html(context)
            
            else:
                # Fallback: Simple text-based PDF
                return self._render_fallback(context)
                
        except Exception as e:
            print(f"Warning: Template PDF rendering failed ({e}), using fallback")
            return self._render_fallback(context)

    def _render_from_docx(self, context: Dict[str, Any]) -> bytes:
        """Convert DOCX template to PDF"""
        from src.infrastructure.rendering.docx_renderer import DocxRenderer
        
        # Generate DOCX first
        docx_renderer = DocxRenderer(self.template_name)
        docx_bytes = docx_renderer.render(context)
        
        # Create temporary files for conversion
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as docx_temp:
            docx_temp.write(docx_bytes)
            docx_temp_path = docx_temp.name
        
        try:
            # Convert DOCX to PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_temp:
                pdf_temp_path = pdf_temp.name
            
            # Use docx2pdf for conversion
            docx2pdf.convert(docx_temp_path, pdf_temp_path)
            
            # Read the generated PDF
            with open(pdf_temp_path, 'rb') as pdf_file:
                pdf_bytes = pdf_file.read()
            
            return pdf_bytes
            
        finally:
            # Clean up temporary files
            try:
                os.unlink(docx_temp_path)
                if 'pdf_temp_path' in locals():
                    os.unlink(pdf_temp_path)
            except:
                pass

    def _render_from_html(self, context: Dict[str, Any]) -> bytes:
        """Render PDF from HTML template"""
        html_content = self._generate_html_template(context)
        css_content = self._generate_ntt_css()
        
        # Convert HTML to PDF
        html_doc = HTML(string=html_content)
        css_doc = CSS(string=css_content)
        
        pdf_bytes = html_doc.write_pdf(stylesheets=[css_doc])
        return pdf_bytes

    def _generate_html_template(self, context: Dict[str, Any]) -> str:
        """Generate HTML template with NTT DATA styling"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Professional CV - {context.get('full_name', '')}</title>
        </head>
        <body>
            <header class="ntt-header">
                <h1>NTT DATA</h1>
                <div class="cv-title">Professional CV</div>
            </header>
            
            <main class="cv-content">
                <!-- Personal Information -->
                <section class="personal-info">
                    <h2>Personal Information</h2>
                    <div class="info-grid">
                        {self._generate_personal_info_html(context)}
                    </div>
                </section>
                
                <!-- Professional Summary -->
                {self._generate_section_html("Professional Summary", "summary", context)}
                
                <!-- Skills Sections -->
                {self._generate_skills_html(context)}
                
                <!-- Experience Sections -->
                {self._generate_experience_html(context)}
                
                <!-- Education and Additional -->
                {self._generate_education_html(context)}
            </main>
        </body>
        </html>
        """
        return html

    def _generate_ntt_css(self) -> str:
        """Generate NTT DATA-style CSS"""
        return """
        @page {
            size: A4;
            margin: 1in;
        }
        
        body {
            font-family: Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #333;
        }
        
        .ntt-header {
            text-align: center;
            border-bottom: 2px solid #0066cc;
            margin-bottom: 20px;
            padding-bottom: 10px;
        }
        
        .ntt-header h1 {
            color: #0066cc;
            font-size: 24pt;
            margin: 0;
        }
        
        .cv-title {
            font-size: 16pt;
            font-weight: bold;
            margin-top: 5px;
        }
        
        h2 {
            color: #0066cc;
            font-size: 14pt;
            border-bottom: 1px solid #0066cc;
            padding-bottom: 2px;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: 150px 1fr;
            gap: 5px 20px;
            margin-bottom: 15px;
        }
        
        .info-label {
            font-weight: bold;
        }
        
        .section-content {
            margin-bottom: 15px;
            white-space: pre-line;
        }
        
        .skills-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .skill-section h3 {
            font-size: 12pt;
            color: #333;
            margin-bottom: 5px;
        }
        
        ul {
            margin: 5px 0;
            padding-left: 20px;
        }
        
        li {
            margin-bottom: 2px;
        }
        """

    def _generate_personal_info_html(self, context: Dict[str, Any]) -> str:
        """Generate personal information HTML"""
        info_fields = [
            ("Name", "full_name"),
            ("Employee ID", "employee_id"),
            ("Email", "email"),
            ("Contact", "contact_number"),
            ("Title", "current_title"),
            ("Grade", "grade"),
            ("Location", "location"),
            ("Organization", "organization"),
            ("Experience", "experience"),
            ("Target Role", "target_role"),
        ]
        
        html_parts = []
        for label, key in info_fields:
            value = context.get(key, "")
            if value:
                html_parts.append(f'<div class="info-label">{label}:</div>')
                html_parts.append(f'<div class="info-value">{value}</div>')
        
        return "\n".join(html_parts)

    def _generate_section_html(self, title: str, key: str, context: Dict[str, Any]) -> str:
        """Generate a standard section HTML"""
        content = context.get(key, "")
        if not content:
            return ""
        
        return f"""
        <section>
            <h2>{title}</h2>
            <div class="section-content">{content}</div>
        </section>
        """

    def _generate_skills_html(self, context: Dict[str, Any]) -> str:
        """Generate skills sections HTML"""
        skills_sections = [
            ("Primary Skills", "skills"),
            ("Secondary Skills", "secondary_skills"),
            ("Tools & Platforms", "tools_and_platforms"),
            ("AI Frameworks", "ai_frameworks"),
            ("Cloud Platforms", "cloud_platforms"),
            ("Operating Systems", "operating_systems"),
            ("Databases", "databases"),
            ("Domain Expertise", "domain_expertise"),
        ]
        
        html_parts = []
        for title, key in skills_sections:
            content = context.get(key, "")
            if content:
                html_parts.append(self._generate_section_html(title, key, context))
        
        return "\n".join(html_parts)

    def _generate_experience_html(self, context: Dict[str, Any]) -> str:
        """Generate experience sections HTML"""
        experience_sections = [
            ("Work Experience", "work_experience"),
            ("Project Experience", "project_experience"),
            ("Leadership & Impact", "leadership_lines"),
        ]
        
        html_parts = []
        for title, key in experience_sections:
            content = context.get(key, "")
            if content:
                html_parts.append(self._generate_section_html(title, key, context))
        
        return "\n".join(html_parts)

    def _generate_education_html(self, context: Dict[str, Any]) -> str:
        """Generate education and additional sections HTML"""
        sections = [
            ("Education", "education"),
            ("Certifications", "certifications"),
            ("Languages", "languages"),
            ("Awards & Recognition", "awards"),
            ("Publications", "publications"),
        ]
        
        html_parts = []
        for title, key in sections:
            content = context.get(key, "")
            if content:
                html_parts.append(self._generate_section_html(title, key, context))
        
        return "\n".join(html_parts)

    def _render_direct_pdf(self, context: Dict[str, Any]) -> bytes:
        """Direct PDF generation using ReportLab with template styling"""
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        # Custom styles for NTT DATA
        ntt_title_style = ParagraphStyle(
            'NTTTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor='#0066cc',
            alignment=1,  # Center
        )
        
        ntt_heading_style = ParagraphStyle(
            'NTTHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor='#0066cc',
        )
        
        # Build document content
        story = []
        
        # Header
        story.append(Paragraph("NTT DATA", ntt_title_style))
        story.append(Paragraph("Professional CV", styles['Title']))
        story.append(Spacer(1, 0.2*inch))
        
        # Personal Information
        story.append(Paragraph("Personal Information", ntt_heading_style))
        personal_info = self._format_personal_info_pdf(context)
        story.append(Paragraph(personal_info, styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        
        # Content sections
        sections = [
            ("Professional Summary", "summary"),
            ("Skills", "skills"),
            ("Secondary Skills", "secondary_skills"),
            ("Work Experience", "work_experience"),
            ("Project Experience", "project_experience"),
            ("Education", "education"),
            ("Certifications", "certifications"),
            ("Languages", "languages"),
        ]
        
        for title, key in sections:
            content = context.get(key, "")
            if content:
                story.append(Paragraph(title, ntt_heading_style))
                story.append(Paragraph(str(content), styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.read()

    def _format_personal_info_pdf(self, context: Dict[str, Any]) -> str:
        """Format personal information for PDF"""
        info_fields = [
            ("Name", "full_name"),
            ("Employee ID", "employee_id"),
            ("Email", "email"),
            ("Contact", "contact_number"),
            ("Title", "current_title"),
            ("Grade", "grade"),
            ("Location", "location"),
            ("Organization", "organization"),
            ("Experience", "experience"),
            ("Target Role", "target_role"),
        ]
        
        info_lines = []
        for label, key in info_fields:
            value = context.get(key, "")
            if value:
                info_lines.append(f"<b>{label}:</b> {value}")
        
        return "<br/>".join(info_lines)

    def _render_fallback(self, context: Dict[str, Any]) -> bytes:
        """Fallback text-based PDF rendering"""
        # Create simple text content
        lines = []
        lines.append("=== NTT DATA PROFESSIONAL CV ===\n")
        
        # Personal Information
        lines.append("PERSONAL INFORMATION:")
        info_fields = [
            ("Name", "full_name"),
            ("Employee ID", "employee_id"),
            ("Email", "email"),
            ("Contact", "contact_number"),
            ("Title", "current_title"),
            ("Grade", "grade"),
            ("Location", "location"),
            ("Organization", "organization"),
            ("Experience", "experience"),
            ("Target Role", "target_role"),
        ]
        
        for label, key in info_fields:
            value = context.get(key, "")
            if value:
                lines.append(f"{label}: {value}")
        
        lines.append("")
        
        # Content sections
        content_sections = [
            ("PROFESSIONAL SUMMARY", "summary"),
            ("SKILLS", "skills"),
            ("SECONDARY SKILLS", "secondary_skills"),
            ("TOOLS & PLATFORMS", "tools_and_platforms"),
            ("WORK EXPERIENCE", "work_experience"),
            ("PROJECT EXPERIENCE", "project_experience"),
            ("EDUCATION", "education"),
            ("CERTIFICATIONS", "certifications"),
            ("LANGUAGES", "languages"),
            ("AWARDS", "awards"),
            ("PUBLICATIONS", "publications"),
        ]
        
        for section_title, key in content_sections:
            content = context.get(key, "")
            if content:
                lines.append(f"{section_title}:")
                lines.append(str(content))
                lines.append("")
        
        # Convert to bytes (simplified fallback)
        content_str = "\n".join(lines)
        return content_str.encode('utf-8')
