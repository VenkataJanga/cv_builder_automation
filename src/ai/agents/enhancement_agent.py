from typing import List


class EnhancementAgent:
    def enhance_summary(self, text: str) -> str:
        text = text.strip()
        if not text:
            return text
        if text.lower().startswith("enhanced:"):
            return text
        return f"Enhanced: {text}"

    def enhance_skills(self, skills: List[str]) -> List[str]:
        return [skill.strip() for skill in skills if skill and skill.strip()]

    def enhance_achievement(self, text: str) -> str:
        text = text.strip()
        if not text:
            return text
        if "impact" in text.lower() or "%" in text:
            return text
        return f"{text} with measurable business impact"
