import yaml
from pathlib import Path
from typing import Any, Dict
from functools import lru_cache

from src.core.config.settings import settings


class ConfigLoader:
    """
    Loads YAML-based configuration files.

    Supports:
    - questionnaire configs
    - prompt templates
    - template registry
    - environment configs

    Uses caching to avoid repeated disk reads.
    """

    def __init__(self):
        self.base_path = Path(__file__).resolve().parents[3]

    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """
        Load YAML file safely.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    # ---------------------------------------------------------
    # Environment Config
    # ---------------------------------------------------------
    @lru_cache()
    def load_environment_config(self) -> Dict[str, Any]:
        """
        Load environment-specific config file.
        """
        env_file = self.base_path / "config" / "environments" / f"{settings.ENV}.yaml"
        return self._load_yaml(env_file)

    # ---------------------------------------------------------
    # Questionnaire Configs
    # ---------------------------------------------------------
    @lru_cache()
    def load_question_bank(self) -> Dict[str, Any]:
        path = self.base_path / settings.QUESTIONNAIRE_PATH / "question_bank.yaml"
        return self._load_yaml(path)

    @lru_cache()
    def load_role_mapping(self) -> Dict[str, Any]:
        path = self.base_path / settings.QUESTIONNAIRE_PATH / "role_mapping.yaml"
        return self._load_yaml(path)

    @lru_cache()
    def load_section_rules(self) -> Dict[str, Any]:
        path = self.base_path / settings.QUESTIONNAIRE_PATH / "section_rules.yaml"
        return self._load_yaml(path)

    @lru_cache()
    def load_followup_rules(self) -> Dict[str, Any]:
        path = self.base_path / settings.QUESTIONNAIRE_PATH / "followup_rules.yaml"
        return self._load_yaml(path)

    @lru_cache()
    def load_questionnaire_settings(self) -> Dict[str, Any]:
        path = self.base_path / settings.QUESTIONNAIRE_PATH / "questionnaire_settings.yaml"
        return self._load_yaml(path)

    # ---------------------------------------------------------
    # Prompt Configs
    # ---------------------------------------------------------
    @lru_cache()
    def load_prompt(self, prompt_name: str) -> Dict[str, Any]:
        """
        Load a specific prompt YAML.
        Example: extraction.yaml, enhancement.yaml
        """
        path = self.base_path / "config" / "prompts" / f"{prompt_name}.yaml"
        return self._load_yaml(path)

    # ---------------------------------------------------------
    # Template Config
    # ---------------------------------------------------------
    @lru_cache()
    def load_template_registry(self) -> Dict[str, Any]:
        path = self.base_path / "config" / "templates" / "registry.yaml"
        return self._load_yaml(path)

    @lru_cache()
    def load_template_defaults(self) -> Dict[str, Any]:
        path = self.base_path / "config" / "templates" / "template_defaults.yaml"
        return self._load_yaml(path)

    # ---------------------------------------------------------
    # Security Config
    # ---------------------------------------------------------
    @lru_cache()
    def load_roles(self) -> Dict[str, Any]:
        path = self.base_path / "config" / "security" / "roles.yaml"
        return self._load_yaml(path)

    @lru_cache()
    def load_permissions(self) -> Dict[str, Any]:
        path = self.base_path / "config" / "security" / "permissions.yaml"
        return self._load_yaml(path)

    @lru_cache()
    def load_oauth_config(self) -> Dict[str, Any]:
        path = self.base_path / "config" / "security" / "oauth2.yaml"
        return self._load_yaml(path)


# ---------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------
config_loader = ConfigLoader()