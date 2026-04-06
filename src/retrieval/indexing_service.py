"""
Enhanced Retrieval and Indexing Service for CV content retrieval.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class IndexType(Enum):
    """Types of indexes"""
    SKILLS = "skills"
    EXPERIENCE = "experience"
    ACHIEVEMENTS = "achievements"
    METADATA = "metadata"


@dataclass
class IndexedDocument:
    """Indexed document"""
    id: str
    content: str
    index_type: IndexType
    metadata: Dict[str, Any]
    embeddings: Optional[List[float]] = None


class IndexingService:
    """Service for indexing and retrieving CV content"""
    
    def __init__(self):
        self.indexes: Dict[IndexType, List[IndexedDocument]] = {
            IndexType.SKILLS: [],
            IndexType.EXPERIENCE: [],
            IndexType.ACHIEVEMENTS: [],
            IndexType.METADATA: []
        }
    
    def index_cv(self, cv_data: Dict[str, Any]) -> Dict[str, int]:
        """Index CV data for retrieval"""
        counts = {}
        
        # Index skills
        if "skills" in cv_data:
            count = self._index_skills(cv_data["skills"])
            counts["skills"] = count
        
        # Index experience
        if "experience" in cv_data:
            count = self._index_experience(cv_data["experience"])
            counts["experience"] = count
        
        # Index leadership
        if "leadership" in cv_data:
            count = self._index_achievements(cv_data["leadership"])
            counts["achievements"] = count
        
        return counts
    
    def _index_skills(self, skills_data: Dict[str, Any]) -> int:
        """Index skills data"""
        count = 0
        
        if "primary_skills" in skills_data:
            for skill in skills_data["primary_skills"]:
                doc = IndexedDocument(
                    id=f"skill_{count}",
                    content=skill,
                    index_type=IndexType.SKILLS,
                    metadata={"category": "primary"}
                )
                self.indexes[IndexType.SKILLS].append(doc)
                count += 1
        
        return count
    
    def _index_experience(self, exp_data: Dict[str, Any]) -> int:
        """Index experience data"""
        count = 0
        
        if "projects" in exp_data:
            for project in exp_data["projects"]:
                content = f"{project.get('name', '')} {project.get('description', '')}"
                doc = IndexedDocument(
                    id=f"project_{count}",
                    content=content,
                    index_type=IndexType.EXPERIENCE,
                    metadata=project
                )
                self.indexes[IndexType.EXPERIENCE].append(doc)
                count += 1
        
        return count
    
    def _index_achievements(self, leadership_data: Dict[str, Any]) -> int:
        """Index achievements"""
        count = 0
        
        for key in ["key_achievements", "business_outcomes"]:
            if key in leadership_data:
                for item in leadership_data[key]:
                    doc = IndexedDocument(
                        id=f"achievement_{count}",
                        content=item,
                        index_type=IndexType.ACHIEVEMENTS,
                        metadata={"type": key}
                    )
                    self.indexes[IndexType.ACHIEVEMENTS].append(doc)
                    count += 1
        
        return count
    
    def search(self, query: str, index_type: Optional[IndexType] = None, top_k: int = 5) -> List[IndexedDocument]:
        """Search indexed content"""
        query_lower = query.lower()
        results = []
        
        indexes_to_search = [index_type] if index_type else list(IndexType)
        
        for idx_type in indexes_to_search:
            for doc in self.indexes.get(idx_type, []):
                if query_lower in doc.content.lower():
                    results.append(doc)
        
        return results[:top_k]
    
    def get_recommendations(self, cv_data: Dict[str, Any]) -> List[str]:
        """Get retrieval-based recommendations"""
        recommendations = []
        
        # Check for missing skills
        if len(self.indexes[IndexType.SKILLS]) < 5:
            recommendations.append("Add more technical skills to strengthen your profile")
        
        # Check for missing projects
        if len(self.indexes[IndexType.EXPERIENCE]) < 2:
            recommendations.append("Add more project experience to showcase your work")
        
        # Check for achievements
        if len(self.indexes[IndexType.ACHIEVEMENTS]) == 0:
            recommendations.append("Add quantifiable achievements to demonstrate impact")
        
        return recommendations
