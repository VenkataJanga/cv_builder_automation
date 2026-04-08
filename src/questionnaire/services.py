from __future__ import annotations

from typing import Any, Dict, List

from src.questionnaire.loader import QuestionnaireLoader
from src.questionnaire.question_selector import QuestionSelector
from src.questionnaire.role_resolver import RoleResolver


class QuestionnaireService:
    def __init__(self, base_path: str = "config/questionnaire") -> None:
        loader = QuestionnaireLoader(base_path=base_path)
        self.loader = loader
        self.role_resolver = RoleResolver(loader=loader)
        self.question_selector = QuestionSelector(loader=loader)

    def resolve_role_from_title(self, title: str) -> str:
        return self.role_resolver.resolve(title)

    def get_questions_by_title(self, title: str) -> Dict[str, Any]:
        role = self.resolve_role_from_title(title)
        questions = self.question_selector.get_questions_for_role(role)

        return {
            "input_title": title,
            "resolved_role": role,
            "questions": questions,
            "question_texts": [q["question"] for q in questions],
        }

    def get_question_texts_by_title(self, title: str) -> List[str]:
        role = self.resolve_role_from_title(title)
        return self.question_selector.get_question_texts_for_role(role)
