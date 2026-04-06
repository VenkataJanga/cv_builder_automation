"""
Smart Indexing and Retrieval System
Handles CV data indexing, semantic search, and context retrieval
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import hashlib
import json


class IndexType(str, Enum):
    """Types of indices"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class RetrievalMode(str, Enum):
    """Retrieval modes"""
    SIMILAR = "similar"
    EXACT = "exact"
    FUZZY = "fuzzy"
    CONTEXTUAL = "contextual"


class IndexedDocument(BaseModel):
    """Represents an indexed document"""
    doc_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embeddings: Optional[List[float]] = None
    keywords: List[str] = Field(default_factory=list)
    indexed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SearchResult(BaseModel):
    """Search result with relevance score"""
    doc_id: str
    content: str
    score: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    highlights: List[str] = Field(default_factory=list)


class SmartIndexer:
    """
    Intelligent indexing system for CV data with semantic and keyword search
    """
    
    def __init__(self):
        self.documents: Dict[str, IndexedDocument] = {}
        self.keyword_index: Dict[str, List[str]] = {}  # keyword -> [doc_ids]
        self.metadata_index: Dict[str, Dict[str, List[str]]] = {}  # field -> {value -> [doc_ids]}
    
    def index_cv_data(
        self,
        cv_data: Dict[str, Any],
        cv_id: Optional[str] = None
    ) -> str:
        """
        Index CV data for retrieval
        """
        
        if not cv_id:
            cv_id = self._generate_id(cv_data)
        
        # Create searchable content
        content_parts = []
        
        # Add basic info
        if cv_data.get("full_name"):
            content_parts.append(f"Name: {cv_data['full_name']}")
        
        if cv_data.get("professional_summary"):
            content_parts.append(f"Summary: {cv_data['professional_summary']}")
        
        # Add skills
        if cv_data.get("skills"):
            skills = cv_data["skills"]
            if isinstance(skills, list):
                content_parts.append(f"Skills: {', '.join(skills)}")
            else:
                content_parts.append(f"Skills: {skills}")
        
        # Add experience
        if cv_data.get("work_experience"):
            for exp in cv_data["work_experience"]:
                if isinstance(exp, dict):
                    role = exp.get("role", "")
                    company = exp.get("company", "")
                    desc = exp.get("description", "")
                    content_parts.append(f"Experience: {role} at {company}. {desc}")
        
        # Add projects
        if cv_data.get("projects"):
            for proj in cv_data["projects"]:
                if isinstance(proj, dict):
                    name = proj.get("name", "")
                    desc = proj.get("description", "")
                    content_parts.append(f"Project: {name}. {desc}")
        
        # Add education
        if cv_data.get("education"):
            for edu in cv_data["education"]:
                if isinstance(edu, dict):
                    degree = edu.get("degree", "")
                    inst = edu.get("institution", "")
                    content_parts.append(f"Education: {degree} from {inst}")
        
        content = "\n".join(content_parts)
        
        # Extract keywords
        keywords = self._extract_keywords(content)
        
        # Create indexed document
        doc = IndexedDocument(
            doc_id=cv_id,
            content=content,
            metadata={
                "cv_id": cv_id,
                "indexed_at": datetime.utcnow().isoformat(),
                "field_count": len(cv_data),
                "has_skills": bool(cv_data.get("skills")),
                "has_experience": bool(cv_data.get("work_experience")),
                "has_projects": bool(cv_data.get("projects"))
            },
            keywords=keywords
        )
        
        # Store document
        self.documents[cv_id] = doc
        
        # Update keyword index
        for keyword in keywords:
            if keyword not in self.keyword_index:
                self.keyword_index[keyword] = []
            if cv_id not in self.keyword_index[keyword]:
                self.keyword_index[keyword].append(cv_id)
        
        # Update metadata index
        for field, value in cv_data.items():
            if field not in self.metadata_index:
                self.metadata_index[field] = {}
            
            value_str = str(value)[:100]  # Truncate long values
            if value_str not in self.metadata_index[field]:
                self.metadata_index[field][value_str] = []
            
            if cv_id not in self.metadata_index[field][value_str]:
                self.metadata_index[field][value_str].append(cv_id)
        
        return cv_id
    
    def search(
        self,
        query: str,
        mode: RetrievalMode = RetrievalMode.HYBRID,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search indexed documents
        """
        
        results = []
        
        if mode == RetrievalMode.KEYWORD or mode == RetrievalMode.HYBRID:
            results.extend(self._keyword_search(query, top_k))
        
        if mode == RetrievalMode.FUZZY:
            results.extend(self._fuzzy_search(query, top_k))
        
        if mode == RetrievalMode.CONTEXTUAL:
            results.extend(self._contextual_search(query, top_k))
        
        # Apply filters
        if filters:
            results = self._apply_filters(results, filters)
        
        # Remove duplicates and sort by score
        seen = set()
        unique_results = []
        for result in results:
            if result.doc_id not in seen:
                seen.add(result.doc_id)
                unique_results.append(result)
        
        unique_results.sort(key=lambda x: x.score, reverse=True)
        
        return unique_results[:top_k]
    
    def _keyword_search(
        self,
        query: str,
        top_k: int
    ) -> List[SearchResult]:
        """Keyword-based search"""
        
        query_keywords = self._extract_keywords(query.lower())
        doc_scores: Dict[str, float] = {}
        
        for keyword in query_keywords:
            if keyword in self.keyword_index:
                for doc_id in self.keyword_index[keyword]:
                    doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + 1.0
        
        results = []
        for doc_id, score in doc_scores.items():
            if doc_id in self.documents:
                doc = self.documents[doc_id]
                normalized_score = min(score / len(query_keywords), 1.0) if query_keywords else 0.0
                
                # Find highlights
                highlights = self._find_highlights(doc.content, query_keywords)
                
                results.append(SearchResult(
                    doc_id=doc_id,
                    content=doc.content,
                    score=normalized_score,
                    metadata=doc.metadata,
                    highlights=highlights
                ))
        
        return results
    
    def _fuzzy_search(
        self,
        query: str,
        top_k: int
    ) -> List[SearchResult]:
        """Fuzzy matching search"""
        
        results = []
        query_lower = query.lower()
        
        for doc_id, doc in self.documents.items():
            content_lower = doc.content.lower()
            
            # Simple fuzzy matching: check if query words appear in content
            query_words = query_lower.split()
            matches = sum(1 for word in query_words if word in content_lower)
            score = matches / len(query_words) if query_words else 0.0
            
            if score > 0:
                highlights = self._find_highlights(doc.content, query_words)
                
                results.append(SearchResult(
                    doc_id=doc_id,
                    content=doc.content,
                    score=score * 0.8,  # Slightly lower score for fuzzy
                    metadata=doc.metadata,
                    highlights=highlights
                ))
        
        return results
    
    def _contextual_search(
        self,
        query: str,
        top_k: int
    ) -> List[SearchResult]:
        """Context-aware search considering document structure"""
        
        results = []
        query_lower = query.lower()
        
        for doc_id, doc in self.documents.items():
            lines = doc.content.split('\n')
            relevant_lines = []
            total_score = 0.0
            
            for line in lines:
                line_lower = line.lower()
                if query_lower in line_lower:
                    relevant_lines.append(line)
                    total_score += 1.0
                else:
                    # Check for partial matches
                    query_words = query_lower.split()
                    matches = sum(1 for word in query_words if word in line_lower)
                    if matches > 0:
                        relevant_lines.append(line)
                        total_score += matches / len(query_words)
            
            if relevant_lines:
                score = min(total_score / max(len(lines), 1), 1.0)
                
                results.append(SearchResult(
                    doc_id=doc_id,
                    content=doc.content,
                    score=score,
                    metadata=doc.metadata,
                    highlights=relevant_lines[:3]  # Top 3 relevant lines
                ))
        
        return results
    
    def _apply_filters(
        self,
        results: List[SearchResult],
        filters: Dict[str, Any]
    ) -> List[SearchResult]:
        """Apply metadata filters to search results"""
        
        filtered = []
        for result in results:
            matches_all = True
            for key, value in filters.items():
                if key not in result.metadata or result.metadata[key] != value:
                    matches_all = False
                    break
            
            if matches_all:
                filtered.append(result)
        
        return filtered
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        
        # Simple keyword extraction
        stop_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
        }
        
        words = text.lower().split()
        keywords = []
        
        for word in words:
            # Clean word
            word = ''.join(c for c in word if c.isalnum())
            
            # Filter out stop words and short words
            if word and len(word) > 2 and word not in stop_words:
                keywords.append(word)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords
    
    def _find_highlights(
        self,
        content: str,
        keywords: List[str],
        max_highlights: int = 3
    ) -> List[str]:
        """Find text highlights containing keywords"""
        
        highlights = []
        lines = content.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            for keyword in keywords:
                if keyword in line_lower and line not in highlights:
                    highlights.append(line.strip())
                    break
            
            if len(highlights) >= max_highlights:
                break
        
        return highlights
    
    def _generate_id(self, data: Dict[str, Any]) -> str:
        """Generate unique ID for document"""
        
        content = json.dumps(data, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_document(self, doc_id: str) -> Optional[IndexedDocument]:
        """Retrieve a document by ID"""
        return self.documents.get(doc_id)
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the index"""
        
        if doc_id not in self.documents:
            return False
        
        # Remove from main storage
        del self.documents[doc_id]
        
        # Remove from keyword index
        for keyword, doc_ids in self.keyword_index.items():
            if doc_id in doc_ids:
                doc_ids.remove(doc_id)
        
        # Remove from metadata index
        for field_dict in self.metadata_index.values():
            for doc_ids in field_dict.values():
                if doc_id in doc_ids:
                    doc_ids.remove(doc_id)
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        
        return {
            "total_documents": len(self.documents),
            "total_keywords": len(self.keyword_index),
            "total_metadata_fields": len(self.metadata_index),
            "average_keywords_per_doc": (
                sum(len(doc.keywords) for doc in self.documents.values()) / len(self.documents)
                if self.documents else 0
            )
        }
    
    def recommend_similar(
        self,
        doc_id: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """Recommend similar documents"""
        
        if doc_id not in self.documents:
            return []
        
        source_doc = self.documents[doc_id]
        
        # Use keywords from source document to find similar ones
        similar_scores: Dict[str, float] = {}
        
        for keyword in source_doc.keywords:
            if keyword in self.keyword_index:
                for other_doc_id in self.keyword_index[keyword]:
                    if other_doc_id != doc_id:
                        similar_scores[other_doc_id] = similar_scores.get(other_doc_id, 0.0) + 1.0
        
        # Normalize scores
        max_score = max(similar_scores.values()) if similar_scores else 1.0
        
        results = []
        for other_doc_id, score in similar_scores.items():
            if other_doc_id in self.documents:
                other_doc = self.documents[other_doc_id]
                normalized_score = score / max_score
                
                results.append(SearchResult(
                    doc_id=other_doc_id,
                    content=other_doc.content,
                    score=normalized_score,
                    metadata=other_doc.metadata,
                    highlights=[]
                ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
