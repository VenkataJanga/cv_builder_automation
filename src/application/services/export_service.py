from src.infrastructure.rendering.template_engine import TemplateEngine
from src.infrastructure.rendering.docx_renderer import DocxRenderer
from src.infrastructure.rendering.pdf_renderer import PdfRenderer


class ExportService:
    def __init__(self) -> None:
        self.template_engine = TemplateEngine()
        self.docx_renderer = DocxRenderer()
        self.pdf_renderer = PdfRenderer()

    def export_docx(self, cv_data: dict) -> bytes:
        context = self.template_engine.render_context(cv_data)
        return self.docx_renderer.render(context)

    def export_pdf(self, cv_data: dict) -> bytes:
        context = self.template_engine.render_context(cv_data)
        return self.pdf_renderer.render(context)
