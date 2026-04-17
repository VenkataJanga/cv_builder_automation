from pathlib import Path


class TemplateService:
	def __init__(self, templates_root: str = "src/templates") -> None:
		self.templates_root = Path(templates_root)

	def list_templates(self) -> list[dict]:
		templates: list[dict] = []
		if self.templates_root.exists():
			for path in sorted(self.templates_root.iterdir()):
				if path.is_dir() and not path.name.startswith("__"):
					templates.append(
						{
							"id": path.name,
							"name": path.name.replace("_", " ").title(),
							"path": str(path),
						}
					)

		if templates:
			return templates

		return [
			{"id": "standard", "name": "Standard", "path": "n/a"},
			{"id": "modern", "name": "Modern", "path": "n/a"},
			{"id": "hybrid", "name": "Hybrid", "path": "n/a"},
		]

	def get_template(self, template_id: str) -> dict:
		for template in self.list_templates():
			if template["id"] == template_id:
				return template
		raise KeyError(f"Template not found: {template_id}")
