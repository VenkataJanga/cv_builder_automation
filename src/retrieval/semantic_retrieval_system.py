"""
Semantic Retrieval System
Vector-based retrieval and indexing for CV content and templates
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from enum import Enum
import hashlib
import json


class DocumentType(str, Enum):
    """Types of documents that can be indexed"""
    CV_TEMPLATE = "cv_template"
    PROJECT_DESCRIPTION = "project_description"
    SKILL_DESCRIPTION = "skill_description"
    JOB_DESCRIPTION = "job_description"
    INDUSTRY_KNOWLEDGE = "industry_knowledge"
    EXAMPLE_CV = "example_cv"


class RetrievalStrategy(str, Enum):
    """Retrieval strategies"""
    SEMANTIC = "semantic"  # Vector similarity
    KEYWORD = "keyword"  # Keyword matching
    HYBRID = "hybrid"  # Combination
    CONTEXTUAL = "contextual"  # Context-aware


class IndexedDocument(BaseModel):
    """Document in the index"""
    id: str
    doc_type: DocumentType
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    tags: List[str] = Field(default_factory=list)
    relevance_score: float = 0.0


class RetrievalQuery(BaseModel):
    """Query for retrieval"""
    query_text: str
    doc_types: List[DocumentType] = Field(default_factory=list)
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    top_k: int = 5
    min_score: float = 0.5
    context: Dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """Result from retrieval"""
    documents: List[IndexedDocument] = Field(default_factory=list)
    query: RetrievalQuery
    total_results: int = 0
    retrieval_time_ms: float = 0.0


class SemanticRetrievalSystem:
    """
    Semantic retrieval system for CV content and templates
    with vector similarity and hybrid search
    """
    
    def __init__(self):
        self.index: Dict[str, IndexedDocument] = {}
        self.keyword_index: Dict[str, List[str]] = {}  # keyword -> doc_ids
        self.type_index: Dict[DocumentType, List[str]] = {}  # type -> doc_ids
        
    def index_document(
        self,
        doc_type: DocumentType,
        content: str,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> IndexedDocument:
        """
        Index a document for retrieval
        """
        # Generate document ID
        doc_id = self._generate_doc_id(content, doc_type)
        
        # Create indexed document
        doc = IndexedDocument(
            id=doc_id,
            doc_type=doc_type,
            content=content,
            metadata=metadata or {},
            tags=tags or []
        )
        
        # Generate embedding (placeholder - would use actual embedding model)
        doc.embedding = self._generate_embedding(content)
        
        # Add to main index
        self.index[doc_id] = doc
        
        # Update keyword index
        keywords = self._extract_keywords(content)
        for keyword in keywords:
            if keyword not in self.keyword_index:
                self.keyword_index[keyword] = []
            if doc_id not in self.keyword_index[keyword]:
                self.keyword_index[keyword].append(doc_id)
        
        # Update type index
        if doc_type not in self.type_index:
            self.type_index[doc_type] = []
        if doc_id not in self.type_index[doc_type]:
            self.type_index[doc_type].append(doc_id)
        
        return doc
    
    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        """
        Retrieve documents based on query
        """
        import time
        start_time = time.time()
        
        if query.strategy == RetrievalStrategy.SEMANTIC:
            results = self._semantic_retrieval(query)
        elif query.strategy == RetrievalStrategy.KEYWORD:
            results = self._keyword_retrieval(query)
        elif query.strategy == RetrievalStrategy.CONTEXTUAL:
            results = self._contextual_retrieval(query)
        else:  # HYBRID
            results = self._hybrid_retrieval(query)
        
        # Filter by score
        results = [r for r in results if r.relevance_score >= query.min_score]
        
        # Limit to top_k
        results = results[:query.top_k]
        
        retrieval_time = (time.time() - start_time) * 1000  # ms
        
        return RetrievalResult(
            documents=results,
            query=query,
            total_results=len(results),
            retrieval_time_ms=round(retrieval_time, 2)
        )
    
    def _semantic_retrieval(self, query: RetrievalQuery) -> List[IndexedDocument]:
        """Retrieve using semantic similarity"""
        query_embedding = self._generate_embedding(query.query_text)
        
        candidates = self._get_candidates(query.doc_types)
        
        # Calculate similarity scores
        results = []
        for doc_id in candidates:
            doc = self.index[doc_id]
            if doc.embedding:
                score = self._cosine_similarity(query_embedding, doc.embedding)
                doc_copy = doc.model_copy()
                doc_copy.relevance_score = score
                results.append(doc_copy)
        
        # Sort by score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results
    
    def _keyword_retrieval(self, query: RetrievalQuery) -> List[IndexedDocument]:
        """Retrieve using keyword matching"""
        keywords = self._extract_keywords(query.query_text)
        
        # Find documents matching keywords
        doc_scores: Dict[str, float] = {}
        
        for keyword in keywords:
            if keyword in self.keyword_index:
                for doc_id in self.keyword_index[keyword]:
                    if doc_id not in doc_scores:
                        doc_scores[doc_id] = 0.0
                    doc_scores[doc_id] += 1.0 / len(keywords)
        
        # Filter by document type if specified
        if query.doc_types:
            candidates = self._get_candidates(query.doc_types)
            doc_scores = {k: v for k, v in doc_scores.items() if k in candidates}
        
        # Create results
        results = []
        for doc_id, score in doc_scores.items():
            doc = self.index[doc_id]
            doc_copy = doc.model_copy()
            doc_copy.relevance_score = score
            results.append(doc_copy)
        
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results
    
    def _hybrid_retrieval(self, query: RetrievalQuery) -> List[IndexedDocument]:
        """Retrieve using hybrid approach (semantic + keyword)"""
        # Get semantic results
        semantic_query = query.model_copy()
        semantic_query.strategy = RetrievalStrategy.SEMANTIC
        semantic_results = self._semantic_retrieval(semantic_query)
        
        # Get keyword results
        keyword_query = query.model_copy()
        keyword_query.strategy = RetrievalStrategy.KEYWORD
        keyword_results = self._keyword_retrieval(keyword_query)
        
        # Combine scores
        combined_scores: Dict[str, Tuple[IndexedDocument, float]] = {}
        
        for doc in semantic_results:
            combined_scores[doc.id] = (doc, doc.relevance_score * 0.7)  # 70% weight
        
        for doc in keyword_results:
            if doc.id in combined_scores:
                existing_doc, existing_score = combined_scores[doc.id]
                combined_scores[doc.id] = (existing_doc, existing_score + doc.relevance_score * 0.3)
            else:
                combined_scores[doc.id] = (doc, doc.relevance_score * 0.3)  # 30% weight
        
        # Create final results
        results = []
        for doc, score in combined_scores.values():
            doc_copy = doc.model_copy()
            doc_copy.relevance_score = score
            results.append(doc_copy)
        
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results
    
    def _contextual_retrieval(self, query: RetrievalQuery) -> List[IndexedDocument]:
        """Retrieve with contextual awareness"""
        # Start with hybrid retrieval
        results = self._hybrid_retrieval(query)
        
        # Boost scores based on context
        context = query.context
        
        for doc in results:
            boost = 1.0
            
            # Boost based on role match
            if "role" in context and "role" in doc.metadata:
                if context["role"].lower() in doc.metadata["role"].lower():
                    boost *= 1.3
            
            # Boost based on experience level
            if "experience_level" in context and "experience_level" in doc.metadata:
                if context["experience_level"] == doc.metadata["experience_level"]:
                    boost *= 1.2
            
            # Boost based on industry
            if "industry" in context and "industry" in doc.metadata:
                if context["industry"] in doc.metadata.get("industries", []):
                    boost *= 1.15
            
            # Apply boost
            doc.relevance_score *= boost
        
        # Re-sort after boosting
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results
    
    def _get_candidates(self, doc_types: List[DocumentType]) -> set:
        """Get candidate document IDs filtered by type"""
        if not doc_types:
            return set(self.index.keys())
        
        candidates = set()
        for doc_type in doc_types:
            if doc_type in self.type_index:
                candidates.update(self.type_index[doc_type])
        
        return candidates
    
    def _generate_doc_id(self, content: str, doc_type: DocumentType) -> str:
        """Generate unique document ID"""
        hash_input = f"{doc_type}:{content[:100]}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text
        Placeholder - would use actual embedding model (OpenAI, Sentence Transformers, etc.)
        """
        # Simple hash-based pseudo-embedding for demo
        # In production, use OpenAI embeddings or similar
        import hashlib
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to normalized floats
        embedding = []
        for i in range(0, min(len(hash_bytes), 128), 4):
            chunk = hash_bytes[i:i+4]
            value = int.from_bytes(chunk, 'big') / (2**32)
            embedding.append(value)
        
        # Normalize
        magnitude = sum(x**2 for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        return embedding
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction
        # In production, use more sophisticated NLP
        import re
        
        # Remove special characters and convert to lowercase
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Split into words
        words = text.split()
        
        # Filter stop words and short words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'been', 'be'}
        
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return list(set(keywords))  # Remove duplicates
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = sum(a**2 for a in vec1) ** 0.5
        mag2 = sum(b**2 for b in vec2) ** 0.5
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        stats = {
            "total_documents": len(self.index),
            "documents_by_type": {},
            "total_keywords": len(self.keyword_index),
            "index_size_mb": self._estimate_size() / (1024 * 1024)
        }
        
        for doc_type in DocumentType:
            count = len(self.type_index.get(doc_type, []))
            if count > 0:
                stats["documents_by_type"][doc_type.value] = count
        
        return stats
    
    def _estimate_size(self) -> int:
        """Estimate index size in bytes"""
        # Rough estimation
        size = 0
        for doc in self.index.values():
            size += len(doc.content.encode('utf-8'))
            if doc.embedding:
                size += len(doc.embedding) * 8  # float size
        return size
    
    def clear_index(self):
        """Clear all indexed documents"""
        self.index.clear()
        self.keyword_index.clear()
        self.type_index.clear()
    
    def export_index(self, filepath: str):
        """Export index to file"""
        export_data = {
            "documents": [doc.model_dump() for doc in self.index.values()],
            "stats": self.get_stats()
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def import_index(self, filepath: str):
        """Import index from file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.clear_index()
        
        for doc_data in data.get("documents", []):
            doc = IndexedDocument(**doc_data)
            self.index[doc.id] = doc
            
            # Rebuild indexes
            if doc.doc_type not in self.type_index:
                self.type_index[doc.doc_type] = []
            self.type_index[doc.doc_type].append(doc.id)
            
            keywords = self._extract_keywords(doc.content)
            for keyword in keywords:
                if keyword not in self.keyword_index:
                    self.keyword_index[keyword] = []
                if doc.id not in self.keyword_index[keyword]:
                    self.keyword_index[keyword].append(doc.id)
