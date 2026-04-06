"""
Hybrid Extraction System
Combines rule-based, ML-based, and LLM-based extraction strategies
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import re


class ExtractionStrategy(str, Enum):
    """Extraction strategy types"""
    RULE_BASED = "rule_based"
    ML_BASED = "ml_based"
    LLM_BASED = "llm_based"
    HYBRID = "hybrid"


class ExtractionConfidence(BaseModel):
    """Confidence metrics for extracted data"""
    overall: float = Field(ge=0.0, le=1.0)
    by_field: Dict[str, float] = Field(default_factory=dict)
    strategy_used: ExtractionStrategy
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractedField(BaseModel):
    """Represents an extracted field with metadata"""
    field_name: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    strategy: ExtractionStrategy
    source_text: Optional[str] = None
    alternatives: List[Any] = Field(default_factory=list)


class HybridExtractor:
    """
    Hybrid extraction combining multiple strategies for robust extraction
    """
    
    def __init__(self):
        self.extraction_history: List[Dict] = []
        self.field_extractors = self._initialize_extractors()
    
    def _initialize_extractors(self) -> Dict[str, callable]:
        """Initialize field-specific extractors"""
        return {
            "email": self._extract_email,
            "phone": self._extract_phone,
            "name": self._extract_name,
            "experience": self._extract_experience,
            "skills": self._extract_skills,
            "education": self._extract_education,
            "projects": self._extract_projects,
            "summary": self._extract_summary
        }
    
    def extract(
        self,
        text: str,
        strategy: ExtractionStrategy = ExtractionStrategy.HYBRID,
        context: Optional[Dict] = None
    ) -> Tuple[Dict[str, Any], ExtractionConfidence]:
        """
        Extract CV data using specified strategy
        """
        context = context or {}
        extracted_data = {}
        field_confidences = {}
        
        # Extract each field
        for field_name, extractor in self.field_extractors.items():
            try:
                field_result = extractor(text, strategy, context)
                
                if isinstance(field_result, ExtractedField):
                    extracted_data[field_name] = field_result.value
                    field_confidences[field_name] = field_result.confidence
                else:
                    extracted_data[field_name] = field_result
                    field_confidences[field_name] = 0.5  # Default confidence
                    
            except Exception as e:
                field_confidences[field_name] = 0.0
        
        # Calculate overall confidence
        overall_confidence = (
            sum(field_confidences.values()) / len(field_confidences)
            if field_confidences else 0.0
        )
        
        confidence = ExtractionConfidence(
            overall=overall_confidence,
            by_field=field_confidences,
            strategy_used=strategy,
            metadata={
                "text_length": len(text),
                "fields_extracted": len([v for v in extracted_data.values() if v])
            }
        )
        
        # Record extraction
        self.extraction_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "strategy": strategy.value,
            "confidence": overall_confidence,
            "fields_count": len(extracted_data)
        })
        
        return extracted_data, confidence
    
    def _extract_email(
        self,
        text: str,
        strategy: ExtractionStrategy,
        context: Dict
    ) -> ExtractedField:
        """Extract email address"""
        
        # Rule-based extraction
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, text)
        
        if matches:
            return ExtractedField(
                field_name="email",
                value=matches[0],
                confidence=0.95,
                strategy=ExtractionStrategy.RULE_BASED,
                source_text=matches[0],
                alternatives=matches[1:] if len(matches) > 1 else []
            )
        
        return ExtractedField(
            field_name="email",
            value=None,
            confidence=0.0,
            strategy=strategy
        )
    
    def _extract_phone(
        self,
        text: str,
        strategy: ExtractionStrategy,
        context: Dict
    ) -> ExtractedField:
        """Extract phone number"""
        
        # Rule-based patterns for various phone formats
        patterns = [
            r'\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\d{10,}',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Clean up the match
                phone = re.sub(r'[^\d+]', '', matches[0])
                if len(phone) >= 10:
                    return ExtractedField(
                        field_name="phone",
                        value=matches[0],
                        confidence=0.9,
                        strategy=ExtractionStrategy.RULE_BASED,
                        source_text=matches[0]
                    )
        
        return ExtractedField(
            field_name="phone",
            value=None,
            confidence=0.0,
            strategy=strategy
        )
    
    def _extract_name(
        self,
        text: str,
        strategy: ExtractionStrategy,
        context: Dict
    ) -> ExtractedField:
        """Extract full name"""
        
        # Try to find name near the beginning
        lines = text.split('\n')[:10]  # Check first 10 lines
        
        # Simple heuristic: look for capitalized words
        for line in lines:
            line = line.strip()
            if line and len(line.split()) <= 4:  # Names usually 2-4 words
                words = line.split()
                if all(word[0].isupper() for word in words if word):
                    # Check if it looks like a name (not email, phone, etc.)
                    if not any(char in line for char in ['@', '+', ':', '|']):
                        return ExtractedField(
                            field_name="name",
                            value=line,
                            confidence=0.7,
                            strategy=ExtractionStrategy.RULE_BASED,
                            source_text=line
                        )
        
        return ExtractedField(
            field_name="name",
            value=None,
            confidence=0.0,
            strategy=strategy
        )
    
    def _extract_experience(
        self,
        text: str,
        strategy: ExtractionStrategy,
        context: Dict
    ) -> ExtractedField:
        """Extract years of experience"""
        
        # Pattern for experience mentions
        patterns = [
            r'(\d+\.?\d*)\s*(?:\+)?\s*years?\s+(?:of\s+)?experience',
            r'experience\s+of\s+(\d+\.?\d*)\s*(?:\+)?\s*years?',
            r'(\d+\.?\d*)\s*(?:\+)?\s*yrs?\s+(?:of\s+)?(?:exp|experience)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                years = float(matches[0])
                return ExtractedField(
                    field_name="experience",
                    value=f"{years} years",
                    confidence=0.85,
                    strategy=ExtractionStrategy.RULE_BASED,
                    source_text=matches[0]
                )
        
        return ExtractedField(
            field_name="experience",
            value=None,
            confidence=0.0,
            strategy=strategy
        )
    
    def _extract_skills(
        self,
        text: str,
        strategy: ExtractionStrategy,
        context: Dict
    ) -> ExtractedField:
        """Extract skills"""
        
        # Common skill keywords
        skill_keywords = [
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'go', 'rust',
            'react', 'angular', 'vue', 'django', 'flask', 'spring', 'express', 'fastapi',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'ansible',
            'sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'git', 'jenkins', 'gitlab', 'github', 'ci/cd', 'devops',
            'machine learning', 'ai', 'deep learning', 'nlp', 'computer vision',
            'agile', 'scrum', 'tdd', 'microservices', 'rest', 'graphql'
        ]
        
        # Find skills in text
        found_skills = []
        text_lower = text.lower()
        
        for skill in skill_keywords:
            if skill in text_lower:
                # Find the actual case-preserved version
                pattern = re.compile(re.escape(skill), re.IGNORECASE)
                matches = pattern.findall(text)
                if matches:
                    found_skills.append(matches[0])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_skills = []
        for skill in found_skills:
            skill_lower = skill.lower()
            if skill_lower not in seen:
                seen.add(skill_lower)
                unique_skills.append(skill)
        
        if unique_skills:
            return ExtractedField(
                field_name="skills",
                value=unique_skills,
                confidence=0.8,
                strategy=ExtractionStrategy.RULE_BASED,
                source_text=", ".join(unique_skills[:5])
            )
        
        return ExtractedField(
            field_name="skills",
            value=[],
            confidence=0.0,
            strategy=strategy
        )
    
    def _extract_education(
        self,
        text: str,
        strategy: ExtractionStrategy,
        context: Dict
    ) -> ExtractedField:
        """Extract education information"""
        
        education_keywords = ['bachelor', 'master', 'phd', 'mba', 'b.tech', 'm.tech', 'b.e.', 'm.e.']
        education_entries = []
        
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in education_keywords):
                # Extract degree and year
                year_match = re.search(r'(19|20)\d{2}', line)
                year = year_match.group(0) if year_match else None
                
                education_entries.append({
                    "degree": line.strip(),
                    "year": year
                })
        
        if education_entries:
            return ExtractedField(
                field_name="education",
                value=education_entries,
                confidence=0.75,
                strategy=ExtractionStrategy.RULE_BASED
            )
        
        return ExtractedField(
            field_name="education",
            value=[],
            confidence=0.0,
            strategy=strategy
        )
    
    def _extract_projects(
        self,
        text: str,
        strategy: ExtractionStrategy,
        context: Dict
    ) -> ExtractedField:
        """Extract project information"""
        
        # Look for project sections
        project_indicators = ['project', 'projects:', 'key projects', 'work experience']
        
        # This is a simplified extraction - in production, would use more sophisticated parsing
        projects = []
        
        # Simple heuristic: look for bullet points or numbered lists
        lines = text.split('\n')
        in_project_section = False
        
        for line in lines:
            line_lower = line.lower()
            
            if any(indicator in line_lower for indicator in project_indicators):
                in_project_section = True
                continue
            
            if in_project_section:
                if line.strip().startswith(('-', '•', '*', '◦')) or re.match(r'^\d+\.', line.strip()):
                    project_desc = line.strip().lstrip('-•*◦').strip()
                    if len(project_desc) > 20:  # Meaningful description
                        projects.append({
                            "description": project_desc
                        })
        
        if projects:
            return ExtractedField(
                field_name="projects",
                value=projects,
                confidence=0.6,
                strategy=ExtractionStrategy.RULE_BASED
            )
        
        return ExtractedField(
            field_name="projects",
            value=[],
            confidence=0.0,
            strategy=strategy
        )
    
    def _extract_summary(
        self,
        text: str,
        strategy: ExtractionStrategy,
        context: Dict
    ) -> ExtractedField:
        """Extract professional summary"""
        
        # Look for summary section
        summary_keywords = ['summary', 'profile', 'objective', 'about']
        
        lines = text.split('\n')
        summary_lines = []
        in_summary = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            if any(keyword in line_lower for keyword in summary_keywords):
                in_summary = True
                continue
            
            if in_summary:
                if line.strip():
                    # Check if we've hit another section
                    if line.strip().endswith(':') or line.strip().isupper():
                        break
                    summary_lines.append(line.strip())
                elif summary_lines:  # Empty line after content
                    break
        
        if summary_lines:
            summary = ' '.join(summary_lines)
            return ExtractedField(
                field_name="summary",
                value=summary,
                confidence=0.7,
                strategy=ExtractionStrategy.RULE_BASED,
                source_text=summary[:100]
            )
        
        # Fallback: use first few substantial lines as summary
        substantial_lines = [l.strip() for l in lines[:20] if len(l.strip()) > 50]
        if substantial_lines:
            summary = ' '.join(substantial_lines[:3])
            return ExtractedField(
                field_name="summary",
                value=summary,
                confidence=0.4,
                strategy=ExtractionStrategy.RULE_BASED,
                source_text=summary[:100]
            )
        
        return ExtractedField(
            field_name="summary",
            value=None,
            confidence=0.0,
            strategy=strategy
        )
    
    def extract_with_fallback(
        self,
        text: str,
        primary_strategy: ExtractionStrategy = ExtractionStrategy.LLM_BASED,
        fallback_strategy: ExtractionStrategy = ExtractionStrategy.RULE_BASED
    ) -> Tuple[Dict[str, Any], ExtractionConfidence]:
        """
        Extract with fallback strategy if primary fails
        """
        
        # Try primary strategy
        data, confidence = self.extract(text, primary_strategy)
        
        # If confidence is low, try fallback
        if confidence.overall < 0.5:
            fallback_data, fallback_confidence = self.extract(text, fallback_strategy)
            
            # Merge results, preferring higher confidence values
            merged_data = {}
            merged_confidences = {}
            
            all_fields = set(list(data.keys()) + list(fallback_data.keys()))
            
            for field in all_fields:
                primary_conf = confidence.by_field.get(field, 0.0)
                fallback_conf = fallback_confidence.by_field.get(field, 0.0)
                
                if fallback_conf > primary_conf:
                    merged_data[field] = fallback_data.get(field)
                    merged_confidences[field] = fallback_conf
                else:
                    merged_data[field] = data.get(field)
                    merged_confidences[field] = primary_conf
            
            overall = sum(merged_confidences.values()) / len(merged_confidences) if merged_confidences else 0.0
            
            return merged_data, ExtractionConfidence(
                overall=overall,
                by_field=merged_confidences,
                strategy_used=ExtractionStrategy.HYBRID,
                metadata={
                    "primary_strategy": primary_strategy.value,
                    "fallback_strategy": fallback_strategy.value,
                    "fallback_used": True
                }
            )
        
        return data, confidence
    
    def get_extraction_report(self) -> Dict[str, Any]:
        """Generate extraction performance report"""
        
        if not self.extraction_history:
            return {"message": "No extractions performed yet"}
        
        total_extractions = len(self.extraction_history)
        avg_confidence = sum(e["confidence"] for e in self.extraction_history) / total_extractions
        
        strategy_counts = {}
        for extraction in self.extraction_history:
            strategy = extraction["strategy"]
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        return {
            "total_extractions": total_extractions,
            "average_confidence": avg_confidence,
            "strategy_distribution": strategy_counts,
            "last_extraction": self.extraction_history[-1] if self.extraction_history else None
        }
