from typing import Dict, Any


class AnswerAnalyzer:
    def analyze(self, question: str, answer: str, cv_data: dict | None = None) -> Dict[str, Any]:
        words = len(answer.strip().split())
        vague_markers = ["good", "worked", "handled", "did", "things", "many"]
        has_vague = any(token in answer.lower() for token in vague_markers)
        has_metric = any(token in answer for token in ["%", "$"]) or any(
            token in answer.lower() for token in ["improved", "reduced", "increased", "saved", "optimized"]
        )

        return {
            "needs_followup": words < 4 or has_vague,
            "is_short": words < 8,
            "has_metric": has_metric,
            "is_vague": has_vague,
            "word_count": words,
        }
