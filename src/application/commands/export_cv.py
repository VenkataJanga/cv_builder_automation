from src.application.services.export_service import ExportService


class ExportCVCommand:
	def __init__(self) -> None:
		self.service = ExportService()

	def export_docx(self, cv_data: dict, template_style: str = "standard") -> bytes:
		return self.service.export_docx(cv_data, template_style)

	def export_pdf(self, cv_data: dict, template_style: str = "standard") -> bytes:
		return self.service.export_pdf(cv_data, template_style)
