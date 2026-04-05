from typing import List, Dict


class FAISSStore:
    def __init__(self) -> None:
        self._documents: List[Dict] = []

    def add_documents(self, docs: List[Dict]) -> None:
        self._documents.extend(docs)

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        query_lower = query.lower()
        results = []
        for doc in self._documents:
            content = str(doc.get("content", "")).lower()
            if query_lower in content:
                results.append(doc)
        return results[:top_k]
