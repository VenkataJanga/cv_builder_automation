from __future__ import annotations

from typing import Any, Dict, List

from src.core.i18n import get_default_locale, normalize_locale
from src.questionnaire.loader import QuestionnaireLoader


class QuestionSelector:
    def __init__(self, loader: QuestionnaireLoader | None = None) -> None:
        self.loader = loader or QuestionnaireLoader()

    def _resolve_question_text(self, question: Dict[str, Any], locale: str | None = None) -> str:
        question_id = question.get("id")
        resolved_locale = normalize_locale(locale) or get_default_locale()
        catalog = self.loader.load_locale_catalog(resolved_locale)
        questions_map = catalog.get("questions", {}) if isinstance(catalog, dict) else {}

        if question_id and question_id in questions_map:
            translated = questions_map.get(question_id)
            if isinstance(translated, str) and translated.strip():
                return translated.strip()

        raw = question.get("question", "")
        return raw.strip() if isinstance(raw, str) else ""

    def _apply_locale(self, questions: List[Dict[str, Any]], locale: str | None = None) -> List[Dict[str, Any]]:
        resolved: List[Dict[str, Any]] = []
        for item in questions:
            clone = dict(item)
            clone["question"] = self._resolve_question_text(clone, locale)
            resolved.append(clone)
        return resolved

    def get_initial_questions(self, locale: str | None = None) -> List[Dict[str, Any]]:
        question_bank = self.loader.load_question_bank()
        questions = question_bank.get("initial", [])
        questions.sort(key=lambda q: q.get("order", 9999))
        return self._apply_locale(questions, locale)

    def get_questions_for_role(self, role: str, locale: str | None = None) -> List[Dict[str, Any]]:
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
        return self._apply_locale(unique_questions, locale)

    def get_question_texts_for_role(self, role: str, locale: str | None = None) -> List[str]:
        return [q["question"] for q in self.get_questions_for_role(role, locale=locale) if "question" in q]

    def get_initial_question_texts(self, locale: str | None = None) -> List[str]:
        return [q["question"] for q in self.get_initial_questions(locale=locale) if "question" in q]


def select_questions(role: str, locale: str | None = None) -> List[str]:
    """
    Convenience function to get question texts for a given role.
    This function provides backward compatibility with existing imports.
    """
    selector = QuestionSelector()
    return selector.get_question_texts_for_role(role, locale=locale)


def select_initial_questions(locale: str | None = None) -> List[str]:
    """
    Convenience function to get initial onboarding question texts.
    """
    selector = QuestionSelector()
    return selector.get_initial_question_texts(locale=locale)
