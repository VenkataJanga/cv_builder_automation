from typing import List, Dict

from src.retrieval.vectorstores.faiss_store import FAISSStore


class ContextualRetriever:
    def __init__(self, store: FAISSStore | None = None) -> None:
        self.store = store or FAISSStore()

    def retrieve(self, query: str) -> List[Dict]:
        return self.store.search(query=query, top_k=3)
