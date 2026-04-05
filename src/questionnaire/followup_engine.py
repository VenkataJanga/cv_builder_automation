from typing import Optional


class FollowupEngine:
    def generate_followup(self, question: str, answer: str) -> Optional[str]:
        q = question.lower().strip()
        a = answer.strip()

        if not a:
            return "Could you please provide more details?"

        if "experience" in q and len(a.split()) < 2:
            return "Can you provide a bit more detail about your experience?"
        if "skills" in q and len(a.split(",")) < 2:
            return "Can you list a few more skills or tools you have worked with?"
        if "leadership achievements" in q and len(a.split()) < 5:
            return "Can you share one specific leadership achievement with measurable impact?"
        if "business outcomes" in q and len(a.split()) < 5:
            return "What was the measurable business impact or outcome?"
        if "professional profile" in q and len(a.split()) < 8:
            return "Can you make that summary a little more detailed in 2–3 lines?"

        return None
