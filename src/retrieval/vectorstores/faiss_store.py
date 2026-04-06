from typing import List, Dict


class FAISSStore:
    def __init__(self) -> None:
        self._documents: List[Dict] = []

    def add_documents(self, docs: List[Dict]) -> None:
        self._documents.extend(docs)

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        query_lower = query.lower()
        scored = []
        for doc in self._documents:
            content = str(doc.get("content", "")).lower()
            score = 0
            for token in query_lower.split():
                if token in content:
                    score += 1
            if score > 0:
                scored.append({
                    "content": doc.get("content", ""),
                    "score": score,
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
