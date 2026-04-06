from typing import List, Dict


class EmbeddingService:
    def embed_documents(self, docs: List[Dict]) -> List[Dict]:
        embedded = []
        for i, doc in enumerate(docs):
            embedded.append({
                "id": i,
                "content": doc.get("content", ""),
                "embedding": [len(doc.get("content", "")) % 97],
            })
        return embedded
