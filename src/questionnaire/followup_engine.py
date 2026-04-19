from typing import Optional, Dict, Any

from src.core.i18n import t


class FollowupEngine:
    @staticmethod
    def _contains_any(text: str, phrases: list[str]) -> bool:
        lowered = text.lower().strip()
        return any(phrase in lowered for phrase in phrases)

    def generate_followup(
        self,
        question: str,
        answer: str,
        role: str | None = None,
        analysis: Dict[str, Any] | None = None,
        cv_data: dict | None = None,
        locale: str | None = None,
    ) -> Optional[str]:
        q = question.lower().strip()
        analysis = analysis or {}
        answer = answer.strip()

        if not answer:
            return t("followup.more_details", locale=locale)

        if self._contains_any(q, ["professional profile", "berufliches profil"]) and analysis.get("is_short"):
            return t("followup.expand_summary", locale=locale)

        if self._contains_any(q, ["skills", "kenntnisse", "kompetenzen"]) and analysis.get("is_short"):
            return t("followup.add_skills", locale=locale)

        if self._contains_any(q, ["leadership achievements", "fuhrungserfolge"]) and not analysis.get("has_metric"):
            return t("followup.quantify_achievement", locale=locale)

        if self._contains_any(q, ["business outcomes", "geschaftsergebnisse"]) and not analysis.get("has_metric"):
            return t("followup.business_result", locale=locale)

        if role == "technical_manager" and self._contains_any(q, ["projects", "projekte"]) and analysis.get("is_vague"):
            return t("followup.describe_technical_leadership", locale=locale)

        return None
