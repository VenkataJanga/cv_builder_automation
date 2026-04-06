from typing import List

from src.retrieval.indexing.document_chunker import DocumentChunker
from src.retrieval.indexing.embedding_service import EmbeddingService
from src.retrieval.vectorstores.faiss_store import FAISSStore


class IndexService:
    def __init__(self) -> None:
        self.chunker = DocumentChunker()
        self.embedding_service = EmbeddingService()
        self.store = FAISSStore()

    def index_documents(self, texts: List[str]) -> int:
        total = 0
        for text in texts:
            chunks = self.chunker.chunk(text)
            embedded = self.embedding_service.embed_documents(chunks)
            self.store.add_documents(embedded)
            total += len(embedded)
        return total
