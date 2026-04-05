from typing import List, Dict

from src.retrieval.retrievers.contextual_retriever import ContextualRetriever


class RetrievalService:
    def __init__(self) -> None:
        self.retriever = ContextualRetriever()
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        defaults = [
            {"content": "Best practice: summaries should be concise, role-aligned, and impact-focused."},
            {"content": "Best practice: skills should include languages, frameworks, cloud, and tools."},
            {"content": "Best practice: achievements should mention measurable business outcomes where possible."},
            {"content": "Best practice: voice transcripts should be confirmed by the user before final submission."},
        ]
        self.retriever.store.add_documents(defaults)

    def get_context(self, query: str):
        return self.retriever.retrieve(query)
