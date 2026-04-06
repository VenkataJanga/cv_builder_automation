"""
Enhanced RAG Service with Advanced Indexing

Features:
- Multi-index support (FAISS, Azure AI Search)
- Semantic chunking strategies
- Hybrid search (vector + keyword)
- Contextual retrieval with reranking
- Cache-aware retrieval
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class IndexType(str, Enum):
    """Types of indexes"""
    FAISS = "faiss"
    AZURE_SEARCH = "azure_search"
    HYBRID = "hybrid"


class ChunkingStrategy(str, Enum):
    """Chunking strategies"""
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    SECTION_BASED = "section_based"
    SLIDING_WINDOW = "sliding_window"


@dataclass
class RetrievalContext:
    """Context for a retrieval operation"""
    query: str
    top_k: int = 5
    filters: Dict[str, Any] = field(default_factory=dict)
    rerank: bool = True
    use_cache: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedDocument:
    """Retrieved document with metadata"""
    content: str
    score: float
    source: str
    chunk_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Reranking
    rerank_score: Optional[float] = None
    relevance_explanation: str = ""


@dataclass
class RetrievalResult:
    """Complete retrieval result"""
    query: str
    documents: List[RetrievedDocument]
    total_retrieved: int
    retrieval_time_ms: float
    cache_hit: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnhancedRAGService:
    """
    Advanced RAG service with multiple indexing strategies
    
    Capabilities:
    - Vector similarity search
    - Keyword search
    - Hybrid search combining both
    - Semantic reranking
    - Contextual chunk retrieval
    - Result caching
    """
    
    def __init__(
        self,
        index_type: IndexType = IndexType.HYBRID,
        chunking_strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC
    ):
        self.index_type = index_type
        self.chunking_strategy = chunking_strategy
        self.cache: Dict[str, Tuple[RetrievalResult, datetime]] = {}
        self.cache_ttl = timedelta(hours=1)
    
    def index_documents(
        self,
        documents: List[Dict[str, Any]],
        doc_type: str = "cv_template"
    ) -> Dict[str, Any]:
        """
        Index documents for retrieval
        
        Args:
            documents: List of documents to index
            doc_type: Type of document (cv_template, skill_description, etc.)
            
        Returns:
            Indexing result with statistics
        """
        logger.info(f"Indexing {len(documents)} documents of type {doc_type}")
        
        start_time = datetime.now()
        
        # Chunk documents
        chunks = self._chunk_documents(documents)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Create embeddings (mock for now)
        indexed_count = len(chunks)
        
        # Index based on type
        if self.index_type in [IndexType.FAISS, IndexType.HYBRID]:
            self._index_faiss(chunks)
        
        if self.index_type in [IndexType.AZURE_SEARCH, IndexType.HYBRID]:
            self._index_azure_search(chunks)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        result = {
            "indexed_count": indexed_count,
            "chunk_count": len(chunks),
            "doc_type": doc_type,
            "elapsed_seconds": elapsed,
            "index_type": self.index_type.value,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Indexing complete: {result}")
        return result
    
    def retrieve(
        self,
        context: RetrievalContext
    ) -> RetrievalResult:
        """
        Retrieve relevant documents
        
        Args:
            context: Retrieval context with query and parameters
            
        Returns:
            Retrieval result with ranked documents
        """
        logger.info(f"Retrieving documents for query: {context.query[:100]}...")
        
        # Check cache
        if context.use_cache:
            cached_result = self._get_from_cache(context.query)
            if cached_result:
                logger.info("Cache hit")
                return cached_result
        
        start_time = datetime.now()
        
        # Retrieve from indexes
        documents = self._retrieve_documents(context)
        
        # Rerank if requested
        if context.rerank and len(documents) > 0:
            documents = self._rerank_documents(documents, context.query)
        
        # Trim to top_k
        documents = documents[:context.top_k]
        
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        result = RetrievalResult(
            query=context.query,
            documents=documents,
            total_retrieved=len(documents),
            retrieval_time_ms=elapsed_ms,
            cache_hit=False,
            metadata={
                "index_type": self.index_type.value,
                "reranked": context.rerank,
                "filters": context.filters
            }
        )
        
        # Cache result
        if context.use_cache:
            self._add_to_cache(context.query, result)
        
        logger.info(f"Retrieved {len(documents)} documents in {elapsed_ms:.2f}ms")
        
        return result
    
    def retrieve_for_field_completion(
        self,
        field_name: str,
        current_value: Optional[str],
        cv_context: Dict[str, Any]
    ) -> List[str]:
        """
        Retrieve suggestions for completing a specific field
        
        Args:
            field_name: Name of field to complete
            current_value: Current partial value
            cv_context: Full CV context
            
        Returns:
            List of suggestions
        """
        logger.info(f"Retrieving suggestions for field: {field_name}")
        
        # Build contextual query
        role = cv_context.get("header", {}).get("current_title", "")
        skills = cv_context.get("skills", "")
        
        query = f"{field_name} for {role} with skills: {skills}"
        if current_value:
            query += f" starting with {current_value}"
        
        context = RetrievalContext(
            query=query,
            top_k=5,
            filters={"field_type": field_name},
            rerank=True
        )
        
        result = self.retrieve(context)
        
        # Extract suggestions from retrieved documents
        suggestions = []
        for doc in result.documents:
            # Parse relevant content
            suggestion = self._extract_field_value(doc.content, field_name)
            if suggestion and suggestion not in suggestions:
                suggestions.append(suggestion)
        
        return suggestions[:5]
    
    def retrieve_similar_cvs(
        self,
        cv_data: Dict[str, Any],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar CVs for reference
        
        Args:
            cv_data: Current CV data
            top_k: Number of similar CVs to retrieve
            
        Returns:
            List of similar CV documents
        """
        logger.info("Retrieving similar CVs")
        
        # Build query from CV
        role = cv_data.get("header", {}).get("current_title", "")
        skills = str(cv_data.get("skills", ""))
        experience = cv_data.get("years_of_experience", 0)
        
        query = f"{role} with {experience} years experience and skills: {skills}"
        
        context = RetrievalContext(
            query=query,
            top_k=top_k,
            filters={"doc_type": "cv_template"},
            rerank=True
        )
        
        result = self.retrieve(context)
        
        similar_cvs = []
        for doc in result.documents:
            cv = {
                "content": doc.content,
                "similarity_score": doc.rerank_score or doc.score,
                "source": doc.source,
                "metadata": doc.metadata
            }
            similar_cvs.append(cv)
        
        return similar_cvs
    
    def _chunk_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Chunk documents based on strategy"""
        chunks = []
        
        for doc in documents:
            content = doc.get("content", "")
            
            if self.chunking_strategy == ChunkingStrategy.FIXED_SIZE:
                doc_chunks = self._fixed_size_chunking(content)
            elif self.chunking_strategy == ChunkingStrategy.SEMANTIC:
                doc_chunks = self._semantic_chunking(content)
            elif self.chunking_strategy == ChunkingStrategy.SECTION_BASED:
                doc_chunks = self._section_based_chunking(content)
            else:
                doc_chunks = [content]
            
            for idx, chunk in enumerate(doc_chunks):
                chunks.append({
                    "chunk_id": f"{doc.get('id', 'unknown')}_{idx}",
                    "content": chunk,
                    "source": doc.get("source", "unknown"),
                    "metadata": doc.get("metadata", {})
                })
        
        return chunks
    
    def _fixed_size_chunking(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        """Split text into fixed-size chunks with overlap"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
        
        return chunks
    
    def _semantic_chunking(self, text: str) -> List[str]:
        """Split text based on semantic boundaries"""
        # Split on double newlines (paragraphs)
        paragraphs = text.split("\n\n")
        
        chunks = []
        current_chunk = []
        current_length = 0
        max_chunk_length = 500
        
        for para in paragraphs:
            para_length = len(para.split())
            
            if current_length + para_length > max_chunk_length and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [para]
                current_length = para_length
            else:
                current_chunk.append(para)
                current_length += para_length
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _section_based_chunking(self, text: str) -> List[str]:
        """Split text based on CV sections"""
        # Common section headers
        section_markers = [
            "SUMMARY", "EXPERIENCE", "EDUCATION", "SKILLS",
            "PROJECTS", "CERTIFICATIONS", "AWARDS"
        ]
        
        chunks = []
        current_chunk = []
        
        for line in text.split("\n"):
            # Check if line is a section header
            is_header = any(marker in line.upper() for marker in section_markers)
            
            if is_header and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
            else:
                current_chunk.append(line)
        
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        
        return chunks
    
    def _index_faiss(self, chunks: List[Dict[str, Any]]) -> None:
        """Index chunks in FAISS (mock implementation)"""
        logger.info(f"Indexing {len(chunks)} chunks in FAISS")
        # Actual implementation would create embeddings and add to FAISS index
        pass
    
    def _index_azure_search(self, chunks: List[Dict[str, Any]]) -> None:
        """Index chunks in Azure AI Search (mock implementation)"""
        logger.info(f"Indexing {len(chunks)} chunks in Azure AI Search")
        # Actual implementation would use Azure SDK
        pass
    
    def _retrieve_documents(
        self,
        context: RetrievalContext
    ) -> List[RetrievedDocument]:
        """Retrieve documents from indexes (mock implementation)"""
        # Mock retrieved documents
        mock_docs = [
            RetrievedDocument(
                content=f"Relevant content for: {context.query}",
                score=0.9,
                source="template_1",
                chunk_id="chunk_1",
                metadata={"section": "skills"}
            ),
            RetrievedDocument(
                content=f"Another relevant document about: {context.query}",
                score=0.85,
                source="template_2",
                chunk_id="chunk_2",
                metadata={"section": "experience"}
            )
        ]
        
        return mock_docs
    
    def _rerank_documents(
        self,
        documents: List[RetrievedDocument],
        query: str
    ) -> List[RetrievedDocument]:
        """Rerank documents using cross-encoder or similar"""
        logger.info(f"Reranking {len(documents)} documents")
        
        # Mock reranking - in reality would use a reranking model
        for doc in documents:
            # Simple heuristic: boost if query terms appear in content
            query_terms = set(query.lower().split())
            content_terms = set(doc.content.lower().split())
            overlap = len(query_terms & content_terms)
            
            doc.rerank_score = doc.score * (1 + overlap * 0.1)
            doc.relevance_explanation = f"Contains {overlap} query terms"
        
        # Sort by rerank score
        documents.sort(key=lambda d: d.rerank_score or d.score, reverse=True)
        
        return documents
    
    def _extract_field_value(self, content: str, field_name: str) -> Optional[str]:
        """Extract field value from content"""
        # Simple extraction - would be more sophisticated in reality
        lines = content.split("\n")
        for line in lines:
            if field_name.lower() in line.lower():
                return line.split(":")[-1].strip()
        return None
    
    def _get_from_cache(self, query: str) -> Optional[RetrievalResult]:
        """Get result from cache if available and not expired"""
        if query in self.cache:
            result, timestamp = self.cache[query]
            if datetime.now() - timestamp < self.cache_ttl:
                result.cache_hit = True
                return result
            else:
                del self.cache[query]
        return None
    
    def _add_to_cache(self, query: str, result: RetrievalResult) -> None:
        """Add result to cache"""
        self.cache[query] = (result, datetime.now())
        
        # Limit cache size
        if len(self.cache) > 1000:
            # Remove oldest entries
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
    
    def clear_cache(self) -> None:
        """Clear the retrieval cache"""
        self.cache.clear()
        logger.info("Cache cleared")
