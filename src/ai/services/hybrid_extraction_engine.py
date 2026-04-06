"""
Hybrid Extraction Engine - Advanced Multi-Strategy Extraction
Combines rule-based, ML-based, and LLM-based extraction with confidence scoring
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
import re


class ExtractionStrategy(str, Enum):
    """Extraction strategies"""
    RULE_BASED = "rule_based"
    PATTERN_BASED = "pattern_based"
    LLM_BASED = "llm_based"
    HYBRID = "hybrid"


class ConfidenceLevel(str, Enum):
    """Confidence levels"""
    VERY_HIGH = "very_high"  # > 0.9
    HIGH = "high"  # 0.7 - 0.9
    MEDIUM = "medium"  # 0.5 - 0.7
    LOW = "low"  # 0.3 - 0.5
    VERY_LOW = "very_low"  # < 0.3


class ExtractionResult(BaseModel):
    """Result from a single extraction strategy"""
    strategy: ExtractionStrategy
    field_name: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extracted_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class HybridExtractionResult(BaseModel):
    """Combined result from multiple extraction strategies"""
    field_name: str
    final_value: Any
    final_confidence: float
    confidence_level: ConfidenceLevel
    strategy_used: ExtractionStrategy
    all_results: List[ExtractionResult]
    consensus_score: float  # Agreement between strategies
    needs_verification: bool
    verification_reason: Optional[str] = None


class HybridExtractionEngine:
    """Advanced extraction engine with multiple strategies"""
    
    def __init__(self):
        self.extractors = {
            ExtractionStrategy.RULE_BASED: self._rule_based_extraction,
            ExtractionStrategy.PATTERN_BASED: self._pattern_based_extraction,
            ExtractionStrategy.LLM_BASED: self._llm_based_extraction
        }
        self.field_patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize extraction patterns for different fields"""
        return {
            "email": {
                "patterns": [
                    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                ],
                "confidence_base": 0.95,
                "validators": [self._validate_email]
            },
            "phone": {
                "patterns": [
                    r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
                    r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'
                ],
                "confidence_base": 0.85,
                "validators": [self._validate_phone]
            },
            "linkedin": {
                "patterns": [
                    r'linkedin\.com/in/[\w-]+',
                    r'linkedin\.com/pub/[\w-]+',
                ],
                "confidence_base": 0.90,
                "validators": []
            },
            "github": {
                "patterns": [
                    r'github\.com/[\w-]+',
                ],
                "confidence_base": 0.90,
                "validators": []
            },
            "years_experience": {
                "patterns": [
                    r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
                    r'experience[:\s]+(\d+)\+?\s*years?'
                ],
                "confidence_base": 0.75,
                "validators": [self._validate_years]
            }
        }
    
    def extract_field(
        self,
        text: str,
        field_name: str,
        context: Optional[Dict[str, Any]] = None,
        strategies: Optional[List[ExtractionStrategy]] = None
    ) -> HybridExtractionResult:
        """Extract a specific field using hybrid approach"""
        
        if strategies is None:
            strategies = [
                ExtractionStrategy.PATTERN_BASED,
                ExtractionStrategy.RULE_BASED,
                ExtractionStrategy.LLM_BASED
            ]
        
        all_results = []
        
        # Run all extraction strategies
        for strategy in strategies:
            if strategy in self.extractors:
                try:
                    result = self.extractors[strategy](text, field_name, context)
                    if result:
                        all_results.append(result)
                except Exception as e:
                    # Log error but continue with other strategies
                    pass
        
        # Combine results
        return self._combine_results(field_name, all_results)
    
    def extract_all_fields(
        self,
        text: str,
        field_list: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, HybridExtractionResult]:
        """Extract multiple fields using hybrid approach"""
        
        results = {}
        
        for field_name in field_list:
            result = self.extract_field(text, field_name, context)
            results[field_name] = result
        
        return results
    
    def _rule_based_extraction(
        self,
        text: str,
        field_name: str,
        context: Optional[Dict[str, Any]]
    ) -> Optional[ExtractionResult]:
        """Rule-based extraction using predefined rules"""
        
        # Implement field-specific rules
        if field_name == "full_name":
            return self._extract_name_rule_based(text)
        elif field_name == "email":
            return self._extract_email_rule_based(text)
        elif field_name == "current_title":
            return self._extract_title_rule_based(text)
        
        return None
    
    def _pattern_based_extraction(
        self,
        text: str,
        field_name: str,
        context: Optional[Dict[str, Any]]
    ) -> Optional[ExtractionResult]:
        """Pattern-based extraction using regex"""
        
        if field_name not in self.field_patterns:
            return None
        
        pattern_config = self.field_patterns[field_name]
        
        for pattern in pattern_config["patterns"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1) if match.groups() else match.group(0)
                
                # Apply validators
                is_valid = True
                for validator in pattern_config.get("validators", []):
                    if not validator(value):
                        is_valid = False
                        break
                
                if is_valid:
                    return ExtractionResult(
                        strategy=ExtractionStrategy.PATTERN_BASED,
                        field_name=field_name,
                        value=value.strip(),
                        confidence=pattern_config["confidence_base"],
                        metadata={
                            "pattern_used": pattern,
                            "match_position": match.start()
                        }
                    )
        
        return None
    
    def _llm_based_extraction(
        self,
        text: str,
        field_name: str,
        context: Optional[Dict[str, Any]]
    ) -> Optional[ExtractionResult]:
        """LLM-based extraction (placeholder for actual LLM call)"""
        
        # This would call an actual LLM service
        # For now, return a placeholder
        
        # Simulate LLM extraction confidence
        confidence = 0.85
        
        # Check if we have enough context
        if len(text) < 50:
            confidence *= 0.7
        
        return ExtractionResult(
            strategy=ExtractionStrategy.LLM_BASED,
            field_name=field_name,
            value=None,  # Would be extracted by LLM
            confidence=confidence,
            metadata={
                "model": "gpt-4",
                "tokens_used": len(text.split())
            }
        )
    
    def _extract_name_rule_based(self, text: str) -> Optional[ExtractionResult]:
        """Extract name using rules"""
        
        # Look for name at the start of document
        lines = text.split('\n')
        for i, line in enumerate(lines[:5]):  # Check first 5 lines
            line = line.strip()
            
            # Name is typically 2-4 words, capitalized
            words = line.split()
            if 2 <= len(words) <= 4:
                if all(word[0].isupper() for word in words if word):
                    # Check if it looks like a name (not a title or company)
                    if not any(keyword in line.lower() for keyword in 
                              ['engineer', 'developer', 'manager', 'resume', 'cv', 'curriculum']):
                        return ExtractionResult(
                            strategy=ExtractionStrategy.RULE_BASED,
                            field_name="full_name",
                            value=line,
                            confidence=0.80,
                            metadata={"line_number": i}
                        )
        
        return None
    
    def _extract_email_rule_based(self, text: str) -> Optional[ExtractionResult]:
        """Extract email using rules"""
        
        # Use pattern-based extraction
        return self._pattern_based_extraction(text, "email", None)
    
    def _extract_title_rule_based(self, text: str) -> Optional[ExtractionResult]:
        """Extract job title using rules"""
        
        # Common title keywords
        title_keywords = [
            'engineer', 'developer', 'architect', 'manager', 'lead',
            'senior', 'junior', 'principal', 'staff', 'consultant',
            'analyst', 'scientist', 'specialist', 'director'
        ]
        
        lines = text.split('\n')
        for i, line in enumerate(lines[:10]):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in title_keywords):
                # Avoid lines with too many words (likely descriptions)
                if 2 <= len(line.split()) <= 6:
                    return ExtractionResult(
                        strategy=ExtractionStrategy.RULE_BASED,
                        field_name="current_title",
                        value=line.strip(),
                        confidence=0.75,
                        metadata={"line_number": i}
                    )
        
        return None
    
    def _combine_results(
        self,
        field_name: str,
        results: List[ExtractionResult]
    ) -> HybridExtractionResult:
        """Combine results from multiple strategies"""
        
        if not results:
            return HybridExtractionResult(
                field_name=field_name,
                final_value=None,
                final_confidence=0.0,
                confidence_level=ConfidenceLevel.VERY_LOW,
                strategy_used=ExtractionStrategy.HYBRID,
                all_results=[],
                consensus_score=0.0,
                needs_verification=True,
                verification_reason="No extraction results found"
            )
        
        # Calculate consensus
        values = [r.value for r in results if r.value]
        value_counts = {}
        for v in values:
            v_str = str(v)
            value_counts[v_str] = value_counts.get(v_str, 0) + 1
        
        # Get most common value
        if value_counts:
            most_common_value = max(value_counts, key=value_counts.get)
            consensus_score = value_counts[most_common_value] / len(values)
        else:
            most_common_value = None
            consensus_score = 0.0
        
        # Calculate weighted confidence
        total_confidence = sum(r.confidence for r in results)
        weighted_confidence = total_confidence / len(results)
        
        # Boost confidence if there's consensus
        if consensus_score > 0.5:
            weighted_confidence = min(1.0, weighted_confidence * (1 + consensus_score * 0.2))
        
        # Determine confidence level
        confidence_level = self._get_confidence_level(weighted_confidence)
        
        # Determine if verification needed
        needs_verification = (
            weighted_confidence < 0.7 or
            consensus_score < 0.5 or
            len(results) < 2
        )
        
        verification_reason = None
        if needs_verification:
            if weighted_confidence < 0.7:
                verification_reason = "Low confidence score"
            elif consensus_score < 0.5:
                verification_reason = "Low consensus between strategies"
            else:
                verification_reason = "Insufficient extraction strategies"
        
        # Select best strategy
        best_result = max(results, key=lambda r: r.confidence)
        
        return HybridExtractionResult(
            field_name=field_name,
            final_value=most_common_value or best_result.value,
            final_confidence=weighted_confidence,
            confidence_level=confidence_level,
            strategy_used=best_result.strategy,
            all_results=results,
            consensus_score=consensus_score,
            needs_verification=needs_verification,
            verification_reason=verification_reason
        )
    
    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Convert confidence score to level"""
        if confidence > 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif confidence > 0.7:
            return ConfidenceLevel.HIGH
        elif confidence > 0.5:
            return ConfidenceLevel.MEDIUM
        elif confidence > 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    # Validators
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _validate_phone(self, phone: str) -> bool:
        """Validate phone number"""
        # Remove common separators
        digits = re.sub(r'[-.\s()]', '', phone)
        # Should have 10-15 digits
        return 10 <= len(digits) <= 15 and digits.isdigit()
    
    def _validate_years(self, years_str: str) -> bool:
        """Validate years of experience"""
        try:
            years = int(years_str)
            return 0 <= years <= 50
        except:
            return False
    
    def get_extraction_summary(
        self,
        results: Dict[str, HybridExtractionResult]
    ) -> Dict[str, Any]:
        """Get summary of extraction results"""
        
        total_fields = len(results)
        high_confidence = sum(1 for r in results.values() if r.final_confidence > 0.7)
        needs_verification = sum(1 for r in results.values() if r.needs_verification)
        
        # Calculate average confidence
        avg_confidence = sum(r.final_confidence for r in results.values()) / total_fields if total_fields > 0 else 0.0
        
        # Group by confidence level
        by_confidence_level = {}
        for result in results.values():
            level = result.confidence_level.value
            by_confidence_level[level] = by_confidence_level.get(level, 0) + 1
        
        return {
            "total_fields": total_fields,
            "high_confidence_fields": high_confidence,
            "needs_verification": needs_verification,
            "average_confidence": round(avg_confidence, 3),
            "by_confidence_level": by_confidence_level,
            "extraction_completeness": round(high_confidence / total_fields, 3) if total_fields > 0 else 0.0
        }
