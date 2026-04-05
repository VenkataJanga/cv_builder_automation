from typing import Dict


class AnswerAnalyzer:
    def analyze(self, question: str, answer: str) -> Dict[str, bool]:
        words = len(answer.strip().split())
        return {
            "needs_followup": words < 3,
            "is_short": words < 8,
        }
