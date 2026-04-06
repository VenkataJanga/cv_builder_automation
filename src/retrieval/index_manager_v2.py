"""
Index Manager V2 - Advanced retrieval and indexing for CV context.

Enhanced retrieval that provides:
- Multi-modal indexing (skills, experience, projects)
- Semantic search capabilities
- Context-aware retrieval
- Reranking and relevance scoring
- Cache management
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class IndexType(str, Enum):
    """Types of indices"""
    SKILLS = "skills"
    EXPERIENCE = "experience"
    PROJECTS = "projects"
    EDUCATION = "education"
    CERTIFICATIONS = "certifications"
    GENERAL = "general"


@dataclass
class IndexedDocument:
    """A document in the index"""
    id: str
    content: str
    index_type: IndexType
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SearchResult:
    """A search result with relevance scoring"""
    document: IndexedDocument
    score: float
    relevance_context: str
    matched_terms: List[str] = field(default_factory=list)


class IndexManagerV2:
    """
    Advanced index manager for CV context retrieval.
    
    Supports multiple index types and semantic search.
    """
    
    def __init__(self, embedding_service: Optional[Any] = None):
        """
        Initialize index manager.
        
        Args:
            embedding_service: Service for generating embeddings (optional)
        """
        self.embedding_service = embedding_service
        self.indices: Dict[IndexType, List[IndexedDocument]] = {
            index_type: [] for index_type in IndexType
        }
        self.cache: Dict[str, List[SearchResult]] = {}
        logger.info("IndexManagerV2 initialized")
    
    async def index_cv_data(
        self,
        cv_data: Dict[str, Any],
        user_id: str
    ) -> Dict[str, int]:
        """
        Index all CV data for retrieval.
        
        Args:
            cv_data: Complete CV data
            user_id: User identifier
        
        Returns:
            Dictionary with count of indexed documents per type
        """
        logger.info(f"Indexing CV data for user {user_id}")
        
        indexed_counts = {}
        
        # Index skills
        skills_count = await self._index_skills(
            cv_data.get('skills', []),
            cv_data.get('secondary_skills', []),
            user_id
        )
        indexed_counts['skills'] = skills_count
        
        # Index experience
        exp_count = await self._index_experience(
            cv_data.get('work_experience', []),
            user_id
        )
        indexed_counts['experience'] = exp_count
        
        # Index projects
        proj_count = await self._index_projects(
            cv_data.get('project_experience', []),
            user_id
        )
        indexed_counts['projects'] = proj_count
        
        # Index education
        edu_count = await self._index_education(
            cv_data.get('education', []),
            user_id
        )
        indexed_counts['education'] = edu_count
        
        # Index certifications
        cert_count = await self._index_certifications(
            cv_data.get('certifications', []),
            user_id
        )
        indexed_counts['certifications'] = cert_count
        
        # Index general info
        general_count = await self._index_general(cv_data, user_id)
        indexed_counts['general'] = general_count
        
        logger.info(f"Indexed {sum(indexed_counts.values())} total documents")
        
        return indexed_counts
    
    async def _index_skills(
        self,
        primary_skills: List[str],
        secondary_skills: List[str],
        user_id: str
    ) -> int:
        """Index skills data"""
        count = 0
        
        # Index primary skills
        if primary_skills:
            content = f"Primary Skills: {', '.join(primary_skills)}"
            doc = IndexedDocument(
                id=f"{user_id}_skills_primary",
                content=content,
                index_type=IndexType.SKILLS,
                metadata={
                    'user_id': user_id,
                    'skill_type': 'primary',
                    'skills': primary_skills
                }
            )
            
            if self.embedding_service:
                doc.embedding = await self._get_embedding(content)
            
            self.indices[IndexType.SKILLS].append(doc)
            count += 1
        
        # Index secondary skills
        if secondary_skills:
            content = f"Secondary Skills: {', '.join(secondary_skills)}"
            doc = IndexedDocument(
                id=f"{user_id}_skills_secondary",
                content=content,
                index_type=IndexType.SKILLS,
                metadata={
                    'user_id': user_id,
                    'skill_type': 'secondary',
                    'skills': secondary_skills
                }
            )
            
            if self.embedding_service:
                doc.embedding = await self._get_embedding(content)
            
            self.indices[IndexType.SKILLS].append(doc)
            count += 1
        
        return count
    
    async def _index_experience(
        self,
        experiences: List[Dict[str, Any]],
        user_id: str
    ) -> int:
        """Index work experience"""
        count = 0
        
        for i, exp in enumerate(experiences):
            if not isinstance(exp, dict):
                continue
            
            # Build content
            parts = []
            if exp.get('company_name'):
                parts.append(f"Company: {exp['company_name']}")
            if exp.get('role'):
                parts.append(f"Role: {exp['role']}")
            if exp.get('duration'):
                parts.append(f"Duration: {exp['duration']}")
            if exp.get('responsibilities'):
                if isinstance(exp['responsibilities'], list):
                    parts.append(f"Responsibilities: {', '.join(exp['responsibilities'])}")
                else:
                    parts.append(f"Responsibilities: {exp['responsibilities']}")
            
            content = " | ".join(parts)
            
            doc = IndexedDocument(
                id=f"{user_id}_experience_{i}",
                content=content,
                index_type=IndexType.EXPERIENCE,
                metadata={
                    'user_id': user_id,
                    'company': exp.get('company_name'),
                    'role': exp.get('role'),
                    'index': i
                }
            )
            
            if self.embedding_service:
                doc.embedding = await self._get_embedding(content)
            
            self.indices[IndexType.EXPERIENCE].append(doc)
            count += 1
        
        return count
    
    async def _index_projects(
        self,
        projects: List[Dict[str, Any]],
        user_id: str
    ) -> int:
        """Index project experience"""
        count = 0
        
        for i, proj in enumerate(projects):
            if not isinstance(proj, dict):
                continue
            
            # Build content
            parts = []
            if proj.get('project_name'):
                parts.append(f"Project: {proj['project_name']}")
            if proj.get('project_description'):
                parts.append(f"Description: {proj['project_description']}")
            if proj.get('technologies_used'):
                if isinstance(proj['technologies_used'], list):
                    parts.append(f"Technologies: {', '.join(proj['technologies_used'])}")
                else:
                    parts.append(f"Technologies: {proj['technologies_used']}")
            if proj.get('role'):
                parts.append(f"Role: {proj['role']}")
            
            content = " | ".join(parts)
            
            doc = IndexedDocument(
                id=f"{user_id}_project_{i}",
                content=content,
                index_type=IndexType.PROJECTS,
                metadata={
                    'user_id': user_id,
                    'project_name': proj.get('project_name'),
                    'technologies': proj.get('technologies_used', []),
                    'index': i
                }
            )
            
            if self.embedding_service:
                doc.embedding = await self._get_embedding(content)
            
            self.indices[IndexType.PROJECTS].append(doc)
            count += 1
        
        return count
    
    async def _index_education(
        self,
        education: List[Dict[str, Any]],
        user_id: str
    ) -> int:
        """Index education"""
        count = 0
        
        for i, edu in enumerate(education):
            if not isinstance(edu, dict):
                continue
            
            parts = []
            if edu.get('degree'):
                parts.append(f"Degree: {edu['degree']}")
            if edu.get('institution'):
                parts.append(f"Institution: {edu['institution']}")
            if edu.get('year'):
                parts.append(f"Year: {edu['year']}")
            if edu.get('grade'):
                parts.append(f"Grade: {edu['grade']}")
            
            content = " | ".join(parts)
            
            doc = IndexedDocument(
                id=f"{user_id}_education_{i}",
                content=content,
                index_type=IndexType.EDUCATION,
                metadata={
                    'user_id': user_id,
                    'degree': edu.get('degree'),
                    'institution': edu.get('institution'),
                    'index': i
                }
            )
            
            if self.embedding_service:
                doc.embedding = await self._get_embedding(content)
            
            self.indices[IndexType.EDUCATION].append(doc)
            count += 1
        
        return count
    
    async def _index_certifications(
        self,
        certifications: List[Dict[str, Any]],
        user_id: str
    ) -> int:
        """Index certifications"""
        count = 0
        
        for i, cert in enumerate(certifications):
            if isinstance(cert, dict):
                content = f"{cert.get('name', '')} - {cert.get('issuer', '')}"
            else:
                content = str(cert)
            
            doc = IndexedDocument(
                id=f"{user_id}_cert_{i}",
                content=content,
                index_type=IndexType.CERTIFICATIONS,
                metadata={
                    'user_id': user_id,
                    'index': i
                }
            )
            
            if self.embedding_service:
                doc.embedding = await self._get_embedding(content)
            
            self.indices[IndexType.CERTIFICATIONS].append(doc)
            count += 1
        
        return count
    
    async def _index_general(
        self,
        cv_data: Dict[str, Any],
        user_id: str
    ) -> int:
        """Index general CV information"""
        count = 0
        
        # Index professional summary
        summary = cv_data.get('professional_summary') or cv_data.get('summary')
        if summary:
            doc = IndexedDocument(
                id=f"{user_id}_summary",
                content=f"Professional Summary: {summary}",
                index_type=IndexType.GENERAL,
                metadata={'user_id': user_id, 'field': 'summary'}
            )
            
            if self.embedding_service:
                doc.embedding = await self._get_embedding(doc.content)
            
            self.indices[IndexType.GENERAL].append(doc)
            count += 1
        
        # Index header info
        header = cv_data.get('header', {})
        if header:
            header_parts = []
            for key, value in header.items():
                if value:
                    header_parts.append(f"{key}: {value}")
            
            if header_parts:
                doc = IndexedDocument(
                    id=f"{user_id}_header",
                    content=" | ".join(header_parts),
                    index_type=IndexType.GENERAL,
                    metadata={'user_id': user_id, 'field': 'header'}
                )
                
                if self.embedding_service:
                    doc.embedding = await self._get_embedding(doc.content)
                
                self.indices[IndexType.GENERAL].append(doc)
                count += 1
        
        return count
    
    async def search(
        self,
        query: str,
        index_types: Optional[List[IndexType]] = None,
        top_k: int = 5,
        user_id: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search across indices.
        
        Args:
            query: Search query
            index_types: Types of indices to search (None = all)
            top_k: Number of results to return
            user_id: Filter by user ID
        
        Returns:
            List of search results with scores
        """
        # Check cache
        cache_key = f"{query}_{index_types}_{top_k}_{user_id}"
        if cache_key in self.cache:
            logger.info("Returning cached search results")
            return self.cache[cache_key]
        
        logger.info(f"Searching for: {query}")
        
        # Determine which indices to search
        if index_types is None:
            indices_to_search = list(self.indices.values())
        else:
            indices_to_search = [self.indices[it] for it in index_types]
        
        # Flatten documents
        all_docs = []
        for index in indices_to_search:
            all_docs.extend(index)
        
        # Filter by user_id if provided
        if user_id:
            all_docs = [d for d in all_docs if d.metadata.get('user_id') == user_id]
        
        # Search
        if self.embedding_service and all(d.embedding for d in all_docs):
            # Semantic search
            results = await self._semantic_search(query, all_docs, top_k)
        else:
            # Keyword search
            results = self._keyword_search(query, all_docs, top_k)
        
        # Cache results
        self.cache[cache_key] = results
        
        logger.info(f"Found {len(results)} results")
        
        return results
    
    async def _semantic_search(
        self,
        query: str,
        documents: List[IndexedDocument],
        top_k: int
    ) -> List[SearchResult]:
        """Perform semantic search using embeddings"""
        # Get query embedding
        query_embedding = await self._get_embedding(query)
        
        # Calculate cosine similarity
        results = []
        for doc in documents:
            if doc.embedding:
                score = self._cosine_similarity(query_embedding, doc.embedding)
                results.append(SearchResult(
                    document=doc,
                    score=score,
                    relevance_context="Semantic match"
                ))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _keyword_search(
        self,
        query: str,
        documents: List[IndexedDocument],
        top_k: int
    ) -> List[SearchResult]:
        """Perform keyword-based search"""
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        results = []
        for doc in documents:
            content_lower = doc.content.lower()
            
            # Count matching terms
            matched_terms = [term for term in query_terms if term in content_lower]
            score = len(matched_terms) / len(query_terms) if query_terms else 0
            
            if score > 0:
                results.append(SearchResult(
                    document=doc,
                    score=score,
                    relevance_context=f"Matched {len(matched_terms)} terms",
                    matched_terms=matched_terms
                ))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text"""
        if self.embedding_service:
            return await self.embedding_service.get_embedding(text)
        return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import math
        
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def clear_cache(self):
        """Clear search cache"""
        self.cache.clear()
        logger.info("Search cache cleared")
    
    def clear_index(self, index_type: Optional[IndexType] = None):
        """Clear index(es)"""
        if index_type:
            self.indices[index_type] = []
            logger.info(f"Cleared {index_type.value} index")
        else:
            for idx_type in IndexType:
                self.indices[idx_type] = []
            logger.info("Cleared all indices")
        
        self.clear_cache()
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about indices"""
        stats = {
            'total_documents': sum(len(docs) for docs in self.indices.values()),
            'by_type': {
                idx_type.value: len(docs)
                for idx_type, docs in self.indices.items()
            },
            'cache_size': len(self.cache)
        }
        return stats
