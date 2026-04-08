from __future__ import annotations

from src.questionnaire.loader import QuestionnaireLoader


class RoleResolver:
    def __init__(self, loader: QuestionnaireLoader | None = None) -> None:
        self.loader = loader or QuestionnaireLoader()

    def resolve(self, user_title: str) -> str:
        if not user_title or not user_title.strip():
            return "common"

        mapping_data = self.loader.load_role_mapping()
        role_mapping = mapping_data.get("role_mapping", {})

        normalized_title = user_title.strip().lower()
        return role_mapping.get(normalized_title, "common")


def resolve_role(user_title: str) -> str:
    """
    Convenience function to resolve a user role from a title.
    This function provides backward compatibility with existing imports.
    """
    resolver = RoleResolver()
    return resolver.resolve(user_title)
