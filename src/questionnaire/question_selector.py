from __future__ import annotations

from typing import Any, Dict, List

from src.questionnaire.loader import QuestionnaireLoader


class QuestionSelector:
    def __init__(self, loader: QuestionnaireLoader | None = None) -> None:
        self.loader = loader or QuestionnaireLoader()

    def get_initial_questions(self) -> List[Dict[str, Any]]:
        question_bank = self.loader.load_question_bank()
        questions = question_bank.get("initial", [])
        questions.sort(key=lambda q: q.get("order", 9999))
        return questions

    def get_questions_for_role(self, role: str) -> List[Dict[str, Any]]:
        question_bank = self.loader.load_question_bank()
        settings = self.loader.load_settings()

        include_common = settings.get("include_common_questions_first", True)
        include_leadership = settings.get("include_leadership_questions_for_senior_roles", True)

        questions: List[Dict[str, Any]] = []

        if include_common:
            questions.extend(question_bank.get("common", []))

        if include_leadership and role in {
            "technical_manager",
            "solution_architect",
            "project_manager",
            "senior_team_lead",
            "delivery_head",
            "senior_hr",
        }:
            questions.extend(question_bank.get("leadership", []))

        questions.extend(question_bank.get(role, []))

        # Deduplicate questions by normalized text so the flow never repeats the same prompt.
        unique_questions = []
        seen_questions = set()
        for q in questions:
            normalized = q.get("question", "").strip().lower()
            if not normalized or normalized in seen_questions:
                continue
            seen_questions.add(normalized)
            unique_questions.append(q)

        unique_questions.sort(key=lambda q: q.get("order", 9999))
        return unique_questions

    def get_question_texts_for_role(self, role: str) -> List[str]:
        return [q["question"] for q in self.get_questions_for_role(role) if "question" in q]

    def get_initial_question_texts(self) -> List[str]:
        return [q["question"] for q in self.get_initial_questions() if "question" in q]


def select_questions(role: str) -> List[str]:
    """
    Convenience function to get question texts for a given role.
    This function provides backward compatibility with existing imports.
    """
    selector = QuestionSelector()
    return selector.get_question_texts_for_role(role)


def select_initial_questions() -> List[str]:
    """
    Convenience function to get initial onboarding question texts.
    """
    selector = QuestionSelector()
    return selector.get_initial_question_texts()
