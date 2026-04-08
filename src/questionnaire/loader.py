from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


class QuestionnaireLoader:
    def __init__(self, base_path: str = "config/questionnaire") -> None:
        self.base_path = Path(base_path)

    def load_yaml(self, file_name: str) -> Dict[str, Any]:
        file_path = self.base_path / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"Questionnaire file not found: {file_path}")

        with file_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML structure in {file_path}")
        return data

    def load_question_bank(self) -> Dict[str, Any]:
        return self.load_yaml("question_bank.yaml")

    def load_role_mapping(self) -> Dict[str, Any]:
        return self.load_yaml("role_mapping.yaml")

    def load_section_rules(self) -> Dict[str, Any]:
        return self.load_yaml("section_rules.yaml")

    def load_followup_rules(self) -> Dict[str, Any]:
        return self.load_yaml("followup_rules.yaml")

    def load_settings(self) -> Dict[str, Any]:
        return self.load_yaml("questionnaire_settings.yaml")
