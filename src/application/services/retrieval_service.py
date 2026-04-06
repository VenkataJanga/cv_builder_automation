from typing import List, Dict

from src.retrieval.retrievers.contextual_retriever import ContextualRetriever


class RetrievalService:
    def __init__(self) -> None:
        self.retriever = ContextualRetriever()
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        defaults = [
            {"content": "Summaries should be concise, role-aligned, and impact-focused."},
            {"content": "Leadership bullets should mention measurable outcomes, team size, and scope."},
            {"content": "Skills should include platforms, frameworks, tools, and domain strengths."},
            {"content": "Business outcomes should mention savings, efficiency, quality, revenue, or delivery improvements."},
            {"content": "Voice transcripts should be corrected by the user before final submission if confidence is low."},
        ]
        self.retriever.store.add_documents(defaults)

    def get_context(self, query: str, top_k: int = 3) -> List[Dict]:
        return self.retriever.retrieve(query, top_k=top_k)
