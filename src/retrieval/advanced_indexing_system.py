"""
Advanced Indexing System - Multi-Level Document Retrieval
Provides hybrid retrieval with dense embeddings, sparse search, and metadata filtering
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
import numpy as np


class IndexType(str, Enum):
    """Types of indexes"""
    DENSE_EMBEDDING = "dense_embedding"  # Vector embeddings
    SPARSE_KEYWORD = "sparse_keyword"  # BM25-style
    METADATA = "metadata"  # Structured filters
    HYBRID = "hybrid"  # Combination


class RetrievalStrategy(str, Enum):
    """Retrieval strategies"""
    SEMANTIC = "semantic"  # Meaning-based
    KEYWORD = "keyword"  # Exact/fuzzy matching
    HYBRID = "hybrid"  # Combined
    RERANK = "rerank"  # Two-stage retrieval


class DocumentChunk(BaseModel):
    """Document chunk for indexing"""
    chunk_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_document: str
    chunk_index: int
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class RetrievalResult(BaseModel):
    """Single retrieval result"""
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    retrieval_method: str
    rank: int


class RetrievalResponse(BaseModel):
    """Complete retrieval response"""
    query: str
    results: List[RetrievalResult]
    strategy_used: RetrievalStrategy
    total_results: int
    retrieval_time_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AdvancedIndexingSystem:
    """Multi-level document indexing and retrieval"""
    
    def __init__(self):
        self.dense_index: Dict[str, DocumentChunk] = {}
        self.sparse_index: Dict[str, List[str]] = {}  # keyword -> chunk_ids
        self.metadata_index: Dict[str, Dict[str, Any]] = {}
        self.embeddings_cache: Dict[str, np.ndarray] = {}
    
    def index_document(
        self,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> List[str]:
        """Index a document with chunking"""
        
        chunks = self._chunk_document(content, chunk_size, chunk_overlap)
        chunk_ids = []
        
        for i, chunk_text in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            
            # Create chunk
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                content=chunk_text,
                source_document=document_id,
                chunk_index=i,
                metadata=metadata or {}
            )
            
            # Index in dense store
            self.dense_index[chunk_id] = chunk
            
            # Index keywords
            keywords = self._extract_keywords(chunk_text)
            for keyword in keywords:
                if keyword not in self.sparse_index:
                    self.sparse_index[keyword] = []
                self.sparse_index[keyword].append(chunk_id)
            
            # Index metadata
            if metadata:
                self.metadata_index[chunk_id] = metadata
            
            chunk_ids.append(chunk_id)
        
        return chunk_ids
    
    def retrieve(
        self,
        query: str,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        rerank: bool = True
    ) -> RetrievalResponse:
        """Retrieve relevant chunks"""
        
        start_time = datetime.utcnow()
        
        if strategy == RetrievalStrategy.SEMANTIC:
            results = self._semantic_retrieval(query, top_k, filters)
        elif strategy == RetrievalStrategy.KEYWORD:
            results = self._keyword_retrieval(query, top_k, filters)
        elif strategy == RetrievalStrategy.HYBRID:
            results = self._hybrid_retrieval(query, top_k, filters)
        else:
            results = self._semantic_retrieval(query, top_k, filters)
        
        # Rerank if requested
        if rerank and len(results) > 0:
            results = self._rerank_results(query, results)
        
        # Calculate retrieval time
        end_time = datetime.utcnow()
        retrieval_time_ms = (end_time - start_time).total_seconds() * 1000
        
        return RetrievalResponse(
            query=query,
            results=results,
            strategy_used=strategy,
            total_results=len(results),
            retrieval_time_ms=retrieval_time_ms,
            metadata={"filters_applied": filters is not None}
        )
    
    def _chunk_document(
        self,
        content: str,
        chunk_size: int,
        overlap: int
    ) -> List[str]:
        """Chunk document with overlap"""
        
        words = content.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))
        
        return chunks
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        
        # Simple implementation - would use proper NLP in production
        words = text.lower().split()
        
        # Filter stopwords
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        
        return list(set(keywords))
    
    def _semantic_retrieval(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[RetrievalResult]:
        """Semantic similarity-based retrieval"""
        
        # This is a simplified implementation
        # In production, would use actual embeddings and vector similarity
        
        results = []
        for chunk_id, chunk in self.dense_index.items():
            # Apply filters
            if filters and not self._match_filters(chunk, filters):
                continue
            
            # Calculate similarity (simplified)
            score = self._calculate_similarity(query, chunk.content)
            
            results.append(RetrievalResult(
                chunk_id=chunk_id,
                content=chunk.content,
                score=score,
                metadata=chunk.metadata,
                retrieval_method="semantic",
                rank=0
            ))
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Assign ranks and limit
        for i, result in enumerate(results[:top_k]):
            result.rank = i + 1
        
        return results[:top_k]
    
    def _keyword_retrieval(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[RetrievalResult]:
        """Keyword-based retrieval"""
        
        query_keywords = self._extract_keywords(query)
        chunk_scores: Dict[str, float] = {}
        
        # Score chunks by keyword matches
        for keyword in query_keywords:
            if keyword in self.sparse_index:
                for chunk_id in self.sparse_index[keyword]:
                    if chunk_id not in chunk_scores:
                        chunk_scores[chunk_id] = 0.0
                    chunk_scores[chunk_id] += 1.0
        
        # Create results
        results = []
        for chunk_id, score in chunk_scores.items():
            chunk = self.dense_index[chunk_id]
            
            # Apply filters
            if filters and not self._match_filters(chunk, filters):
                continue
            
            # Normalize score
            normalized_score = score / len(query_keywords) if query_keywords else 0.0
            
            results.append(RetrievalResult(
                chunk_id=chunk_id,
                content=chunk.content,
                score=normalized_score,
                metadata=chunk.metadata,
                retrieval_method="keyword",
                rank=0
            ))
        
        # Sort and rank
        results.sort(key=lambda x: x.score, reverse=True)
        for i, result in enumerate(results[:top_k]):
            result.rank = i + 1
        
        return results[:top_k]
    
    def _hybrid_retrieval(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[RetrievalResult]:
        """Hybrid retrieval combining semantic and keyword"""
        
        # Get results from both methods
        semantic_results = self._semantic_retrieval(query, top_k * 2, filters)
        keyword_results = self._keyword_retrieval(query, top_k * 2, filters)
        
        # Combine scores using reciprocal rank fusion
        combined_scores: Dict[str, float] = {}
        
        for result in semantic_results:
            rrf_score = 1.0 / (60 + result.rank)
            combined_scores[result.chunk_id] = combined_scores.get(result.chunk_id, 0.0) + rrf_score
        
        for result in keyword_results:
            rrf_score = 1.0 / (60 + result.rank)
            combined_scores[result.chunk_id] = combined_scores.get(result.chunk_id, 0.0) + rrf_score
        
        # Create combined results
        results = []
        for chunk_id, score in combined_scores.items():
            chunk = self.dense_index[chunk_id]
            results.append(RetrievalResult(
                chunk_id=chunk_id,
                content=chunk.content,
                score=score,
                metadata=chunk.metadata,
                retrieval_method="hybrid",
                rank=0
            ))
        
        # Sort and rank
        results.sort(key=lambda x: x.score, reverse=True)
        for i, result in enumerate(results[:top_k]):
            result.rank = i + 1
        
        return results[:top_k]
    
    def _rerank_results(
        self,
        query: str,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """Rerank results using cross-encoder or similar"""
        
        # Simplified reranking - in production would use a cross-encoder model
        for result in results:
            # Boost score based on query term proximity, freshness, etc.
            boost = 1.0
            
            # Boost recent content
            if "created_at" in result.metadata:
                boost *= 1.1
            
            # Boost exact matches
            if query.lower() in result.content.lower():
                boost *= 1.2
            
            result.score *= boost
        
        # Re-sort
        results.sort(key=lambda x: x.score, reverse=True)
        for i, result in enumerate(results):
            result.rank = i + 1
        
        return results
    
    def _calculate_similarity(self, query: str, content: str) -> float:
        """Calculate similarity between query and content"""
        
        # Simplified similarity - in production would use embeddings
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        intersection = query_words.intersection(content_words)
        return len(intersection) / len(query_words)
    
    def _match_filters(
        self,
        chunk: DocumentChunk,
        filters: Dict[str, Any]
    ) -> bool:
        """Check if chunk matches metadata filters"""
        
        for key, value in filters.items():
            if key not in chunk.metadata:
                return False
            if chunk.metadata[key] != value:
                return False
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get index statistics"""
        
        return {
            "total_chunks": len(self.dense_index),
            "total_keywords": len(self.sparse_index),
            "total_documents": len(set(c.source_document for c in self.dense_index.values())),
            "average_chunk_length": sum(len(c.content) for c in self.dense_index.values()) / len(self.dense_index) if self.dense_index else 0
        }
