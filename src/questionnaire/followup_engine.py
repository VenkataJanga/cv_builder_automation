from typing import Optional, Dict, Any


class FollowupEngine:
    def generate_followup(
        self,
        question: str,
        answer: str,
        role: str | None = None,
        analysis: Dict[str, Any] | None = None,
        cv_data: dict | None = None,
    ) -> Optional[str]:
        q = question.lower().strip()
        analysis = analysis or {}
        answer = answer.strip()

        if not answer:
            return "Could you please provide more details?"

        if "professional profile" in q and analysis.get("is_short"):
            return "Can you expand that summary into 2–3 formal lines including your role focus and strengths?"

        if "skills" in q and analysis.get("is_short"):
            return "Please add more skills, tools, platforms, and frameworks relevant to your role."

        if "leadership achievements" in q and not analysis.get("has_metric"):
            return "Can you quantify that achievement with impact, percentage improvement, savings, or delivery result?"

        if "business outcomes" in q and not analysis.get("has_metric"):
            return "What measurable business result did this create, such as efficiency, savings, quality, or delivery improvement?"

        if role == "technical_manager" and "projects" in q and analysis.get("is_vague"):
            return "Can you describe the system type, technologies used, and your exact technical leadership role?"

        return None
