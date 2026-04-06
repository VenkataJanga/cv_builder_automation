"""
CV Retrieval and Indexing System
Semantic search and retrieval for CV examples, templates, and best practices
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


class IndexType(Enum):
    """Types of indexed content"""
    CV_EXAMPLES = "cv_examples"
    TEMPLATES = "templates"
    BEST_PRACTICES = "best_practices"
    ROLE_DESCRIPTIONS = "role_descriptions"
    SKILLS_LIBRARY = "skills_library"


class RetrievalStrategy(Enum):
    """Retrieval strategies"""
    SEMANTIC = "semantic"  # Vector similarity
    KEYWORD = "keyword"  # Keyword matching
    HYBRID = "hybrid"  # Combined approach
    CONTEXTUAL = "contextual"  # Context-aware retrieval


@dataclass
class IndexedDocument:
    """Single indexed document"""
    id: str
    content: str
    metadata: Dict[str, Any]
    index_type: IndexType
    embedding: Optional[List[float]] = None
    keywords: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "index_type": self.index_type.value,
            "keywords": self.keywords
        }


@dataclass
class RetrievalResult:
    """Search result with scoring"""
    document: IndexedDocument
    score: float
    retrieval_method: RetrievalStrategy
    explanation: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "document": self.document.to_dict(),
            "score": self.score,
            "retrieval_method": self.retrieval_method.value,
            "explanation": self.explanation
        }


class CVIndexer:
    """Manage CV-related content indexing and retrieval"""
    
    def __init__(self, embedding_provider=None):
        self.embedding_provider = embedding_provider
        self.documents: Dict[str, IndexedDocument] = {}
        self.index_by_type: Dict[IndexType, List[str]] = {t: [] for t in IndexType}
        
    def index_document(
        self, 
        content: str,
        metadata: Dict[str, Any],
        index_type: IndexType,
        doc_id: Optional[str] = None
    ) -> str:
        """Index a document"""
        if not doc_id:
            doc_id = self._generate_id(content)
        
        # Extract keywords
        keywords = self._extract_keywords(content)
        
        # Generate embedding if provider available
        embedding = None
        if self.embedding_provider:
            try:
                embedding = self.embedding_provider.embed(content)
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}")
        
        # Create document
        doc = IndexedDocument(
            id=doc_id,
            content=content,
            metadata=metadata,
            index_type=index_type,
            embedding=embedding,
            keywords=keywords
        )
        
        # Store document
        self.documents[doc_id] = doc
        self.index_by_type[index_type].append(doc_id)
        
        logger.info(f"Indexed document {doc_id} as {index_type.value}")
        return doc_id
    
    def retrieve(
        self,
        query: str,
        index_type: Optional[IndexType] = None,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Retrieve relevant documents"""
        
        # Filter by index type if specified
        candidate_ids = []
        if index_type:
            candidate_ids = self.index_by_type.get(index_type, [])
        else:
            candidate_ids = list(self.documents.keys())
        
        # Apply metadata filters
        if filters:
            candidate_ids = self._apply_filters(candidate_ids, filters)
        
        # Apply retrieval strategy
        if strategy == RetrievalStrategy.SEMANTIC:
            results = self._semantic_retrieval(query, candidate_ids, top_k)
        elif strategy == RetrievalStrategy.KEYWORD:
            results = self._keyword_retrieval(query, candidate_ids, top_k)
        elif strategy == RetrievalStrategy.HYBRID:
            results = self._hybrid_retrieval(query, candidate_ids, top_k)
        else:
            results = self._contextual_retrieval(query, candidate_ids, top_k)
        
        return results
    
    def _semantic_retrieval(
        self, 
        query: str, 
        candidate_ids: List[str],
        top_k: int
    ) -> List[RetrievalResult]:
        """Semantic similarity-based retrieval"""
        if not self.embedding_provider:
            logger.warning("Embedding provider not available, falling back to keyword")
            return self._keyword_retrieval(query, candidate_ids, top_k)
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_provider.embed(query)
            
            # Calculate similarities
            results = []
            for doc_id in candidate_ids:
                doc = self.documents[doc_id]
                if doc.embedding:
                    similarity = self._cosine_similarity(query_embedding, doc.embedding)
                    results.append(RetrievalResult(
                        document=doc,
                        score=similarity,
                        retrieval_method=RetrievalStrategy.SEMANTIC,
                        explanation=f"Semantic similarity score: {similarity:.3f}"
                    ))
            
            # Sort by score and return top_k
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Semantic retrieval failed: {e}")
            return []
    
    def _keyword_retrieval(
        self, 
        query: str, 
        candidate_ids: List[str],
        top_k: int
    ) -> List[RetrievalResult]:
        """Keyword-based retrieval"""
        query_keywords = set(self._extract_keywords(query))
        
        results = []
        for doc_id in candidate_ids:
            doc = self.documents[doc_id]
            if doc.keywords:
                doc_keywords = set(doc.keywords)
                # Calculate Jaccard similarity
                intersection = len(query_keywords & doc_keywords)
                union = len(query_keywords | doc_keywords)
                score = intersection / union if union > 0 else 0.0
                
                if score > 0:
                    results.append(RetrievalResult(
                        document=doc,
                        score=score,
                        retrieval_method=RetrievalStrategy.KEYWORD,
                        explanation=f"Keyword overlap: {intersection}/{union} (score: {score:.3f})"
                    ))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _hybrid_retrieval(
        self, 
        query: str, 
        candidate_ids: List[str],
        top_k: int
    ) -> List[RetrievalResult]:
        """Hybrid retrieval combining semantic and keyword"""
        semantic_results = self._semantic_retrieval(query, candidate_ids, top_k * 2)
        keyword_results = self._keyword_retrieval(query, candidate_ids, top_k * 2)
        
        # Combine results with weighted scoring
        combined_scores: Dict[str, Tuple[float, str]] = {}
        
        # Weight: 70% semantic, 30% keyword
        for result in semantic_results:
            combined_scores[result.document.id] = (result.score * 0.7, result.explanation)
        
        for result in keyword_results:
            doc_id = result.document.id
            if doc_id in combined_scores:
                prev_score, prev_exp = combined_scores[doc_id]
                combined_scores[doc_id] = (
                    prev_score + result.score * 0.3,
                    f"{prev_exp} + {result.explanation}"
                )
            else:
                combined_scores[doc_id] = (result.score * 0.3, result.explanation)
        
        # Create final results
        results = []
        for doc_id, (score, explanation) in combined_scores.items():
            results.append(RetrievalResult(
                document=self.documents[doc_id],
                score=score,
                retrieval_method=RetrievalStrategy.HYBRID,
                explanation=f"Hybrid score: {score:.3f} ({explanation})"
            ))
        
        # Sort and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _contextual_retrieval(
        self, 
        query: str, 
        candidate_ids: List[str],
        top_k: int
    ) -> List[RetrievalResult]:
        """Context-aware retrieval with role/domain awareness"""
        # Start with hybrid retrieval
        base_results = self._hybrid_retrieval(query, candidate_ids, top_k * 2)
        
        # Extract context from query (e.g., role, domain)
        context = self._extract_context(query)
        
        # Re-rank based on context match
        for result in base_results:
            context_boost = self._calculate_context_boost(result.document, context)
            result.score = result.score * context_boost
            result.retrieval_method = RetrievalStrategy.CONTEXTUAL
            result.explanation = f"{result.explanation} (context boost: {context_boost:.2f})"
        
        # Sort and return top_k
        base_results.sort(key=lambda x: x.score, reverse=True)
        return base_results[:top_k]
    
    def _apply_filters(
        self, 
        candidate_ids: List[str],
        filters: Dict[str, Any]
    ) -> List[str]:
        """Apply metadata filters"""
        filtered = []
        for doc_id in candidate_ids:
            doc = self.documents[doc_id]
            matches = True
            for key, value in filters.items():
                if key not in doc.metadata or doc.metadata[key] != value:
                    matches = False
                    break
            if matches:
                filtered.append(doc_id)
        return filtered
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction (can be enhanced with NLP)
        words = text.lower().split()
        # Filter stop words and short words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        return list(set(keywords))[:20]  # Top 20 unique keywords
    
    def _extract_context(self, query: str) -> Dict[str, Any]:
        """Extract context from query"""
        context = {
            "role": None,
            "domain": None,
            "seniority": None
        }
        
        # Simple pattern matching (can be enhanced)
        query_lower = query.lower()
        
        # Detect role
        roles = ['developer', 'engineer', 'manager', 'architect', 'analyst', 'designer']
        for role in roles:
            if role in query_lower:
                context["role"] = role
                break
        
        # Detect seniority
        if any(word in query_lower for word in ['senior', 'lead', 'principal']):
            context["seniority"] = "senior"
        elif any(word in query_lower for word in ['junior', 'entry']):
            context["seniority"] = "junior"
        else:
            context["seniority"] = "mid"
        
        return context
    
    def _calculate_context_boost(
        self, 
        document: IndexedDocument,
        context: Dict[str, Any]
    ) -> float:
        """Calculate context-based boost factor"""
        boost = 1.0
        
        # Check metadata matches
        if context.get("role") and document.metadata.get("role") == context["role"]:
            boost *= 1.3
        
        if context.get("seniority") and document.metadata.get("seniority") == context["seniority"]:
            boost *= 1.2
        
        if context.get("domain") and document.metadata.get("domain") == context["domain"]:
            boost *= 1.2
        
        return boost
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between vectors"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID for content"""
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        return {
            "total_documents": len(self.documents),
            "by_type": {
                t.value: len(ids) for t, ids in self.index_by_type.items()
            },
            "with_embeddings": len([d for d in self.documents.values() if d.embedding]),
            "with_keywords": len([d for d in self.documents.values() if d.keywords])
        }
    
    def export_index(self, filepath: str):
        """Export index to file"""
        data = {
            "documents": {
                doc_id: {
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "index_type": doc.index_type.value,
                    "keywords": doc.keywords
                }
                for doc_id, doc in self.documents.items()
            }
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Exported index to {filepath}")
    
    def load_index(self, filepath: str):
        """Load index from file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        for doc_id, doc_data in data['documents'].items():
            self.index_document(
                content=doc_data['content'],
                metadata=doc_data['metadata'],
                index_type=IndexType(doc_data['index_type']),
                doc_id=doc_id
            )
        
        logger.info(f"Loaded index from {filepath}")
