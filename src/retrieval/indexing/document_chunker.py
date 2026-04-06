from typing import List, Dict


class DocumentChunker:
    def chunk(self, text: str, chunk_size: int = 400) -> List[Dict]:
        words = text.split()
        if not words:
            return []
        chunks = []
        current = []
        for word in words:
            current.append(word)
            if len(" ".join(current)) >= chunk_size:
                chunks.append({"content": " ".join(current)})
                current = []
        if current:
            chunks.append({"content": " ".join(current)})
        return chunks
