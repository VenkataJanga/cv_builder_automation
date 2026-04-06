"""
Hybrid Extraction Layer
Combines rule-based and AI-based extraction with fallback strategies
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExtractionMethod(Enum):
    """Methods used for extraction"""
    RULE_BASED = "rule_based"
    AI_BASED = "ai_based"
    HYBRID = "hybrid"
    FALLBACK = "fallback"


class ExtractionConfidence(Enum):
    """Confidence levels for extracted data"""
    VERIFIED = "verified"  # 95-100%
    HIGH = "high"  # 80-94%
    MEDIUM = "medium"  # 60-79%
    LOW = "low"  # 40-59%
    UNCERTAIN = "uncertain"  # 0-39%


class HybridExtractor:
    """Combines multiple extraction strategies"""
    
    def __init__(self, ai_provider=None, rule_extractor=None):
        self.ai_provider = ai_provider
        self.rule_extractor = rule_extractor
        self.extraction_metadata = {}
        
    def extract(
        self, 
        source_data: Any, 
        source_type: str = "text"
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract CV data using hybrid approach
        Returns: (extracted_data, extraction_metadata)
        """
        extracted_data = {}
        metadata = {
            "methods_used": [],
            "field_confidence": {},
            "fallback_used": [],
            "extraction_warnings": []
        }
        
        # Try rule-based first (fast and reliable for structured data)
        if self.rule_extractor:
            try:
                rule_result = self.rule_extractor.extract(source_data)
                extracted_data = self._merge_results(extracted_data, rule_result)
                metadata["methods_used"].append(ExtractionMethod.RULE_BASED.value)
                self._update_confidence(metadata, rule_result, ExtractionMethod.RULE_BASED)
            except Exception as e:
                logger.warning(f"Rule-based extraction failed: {e}")
                metadata["extraction_warnings"].append(f"Rule-based: {str(e)}")
        
        # Enhance with AI-based extraction (better for unstructured/complex data)
        if self.ai_provider:
            try:
                ai_result = self.ai_provider.extract(source_data)
                extracted_data = self._merge_results(extracted_data, ai_result, prefer_ai=True)
                metadata["methods_used"].append(ExtractionMethod.AI_BASED.value)
                self._update_confidence(metadata, ai_result, ExtractionMethod.AI_BASED)
            except Exception as e:
                logger.warning(f"AI-based extraction failed: {e}")
                metadata["extraction_warnings"].append(f"AI-based: {str(e)}")
        
        # Apply fallback strategies for missing critical fields
        extracted_data, metadata = self._apply_fallbacks(extracted_data, metadata, source_data)
        
        # Validate and score overall confidence
        self._calculate_overall_confidence(extracted_data, metadata)
        
        return extracted_data, metadata
    
    def _merge_results(
        self, 
        base_data: Dict[str, Any], 
        new_data: Dict[str, Any],
        prefer_ai: bool = False
    ) -> Dict[str, Any]:
        """Merge extraction results intelligently"""
        merged = base_data.copy()
        
        for key, value in new_data.items():
            if key not in merged or not merged[key]:
                # Field is empty, use new value
                merged[key] = value
            elif prefer_ai and value:
                # AI result preferred and has value
                merged[key] = value
            elif isinstance(value, list) and isinstance(merged[key], list):
                # Merge lists, avoiding duplicates
                merged[key] = self._merge_lists(merged[key], value)
            elif isinstance(value, dict) and isinstance(merged[key], dict):
                # Recursively merge dictionaries
                merged[key] = self._merge_results(merged[key], value, prefer_ai)
        
        return merged
    
    def _merge_lists(self, list1: List, list2: List) -> List:
        """Merge two lists avoiding duplicates"""
        result = list1.copy()
        for item in list2:
            if item not in result:
                result.append(item)
        return result
    
    def _update_confidence(
        self, 
        metadata: Dict[str, Any], 
        result: Dict[str, Any], 
        method: ExtractionMethod
    ):
        """Update confidence scores for extracted fields"""
        for key, value in result.items():
            if value:  # Only track non-empty values
                current_conf = metadata["field_confidence"].get(key, 0)
                
                # Rule-based gets 0.85 confidence, AI-based gets 0.90
                if method == ExtractionMethod.RULE_BASED:
                    new_conf = 0.85
                else:
                    new_conf = 0.90
                
                # Use highest confidence
                metadata["field_confidence"][key] = max(current_conf, new_conf)
    
    def _apply_fallbacks(
        self, 
        data: Dict[str, Any], 
        metadata: Dict[str, Any],
        source_data: Any
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Apply fallback strategies for missing data"""
        critical_fields = ['header', 'skills', 'work_experience']
        
        for field in critical_fields:
            if not data.get(field):
                # Try fallback extraction
                fallback_value = self._fallback_extract(field, source_data)
                if fallback_value:
                    data[field] = fallback_value
                    metadata["fallback_used"].append(field)
                    metadata["field_confidence"][field] = 0.60  # Lower confidence
        
        return data, metadata
    
    def _fallback_extract(self, field: str, source_data: Any) -> Any:
        """Fallback extraction for specific field"""
        # Simple fallback strategies
        if field == 'header':
            return {"full_name": "", "email": "", "phone": ""}
        elif field == 'skills':
            return []
        elif field == 'work_experience':
            return []
        return None
    
    def _calculate_overall_confidence(
        self, 
        data: Dict[str, Any], 
        metadata: Dict[str, Any]
    ):
        """Calculate overall extraction confidence"""
        if not metadata["field_confidence"]:
            metadata["overall_confidence"] = 0.0
            metadata["confidence_level"] = ExtractionConfidence.UNCERTAIN.value
            return
        
        # Average confidence across all fields
        avg_confidence = sum(metadata["field_confidence"].values()) / len(metadata["field_confidence"])
        metadata["overall_confidence"] = avg_confidence
        
        # Categorize
        if avg_confidence >= 0.95:
            metadata["confidence_level"] = ExtractionConfidence.VERIFIED.value
        elif avg_confidence >= 0.80:
            metadata["confidence_level"] = ExtractionConfidence.HIGH.value
        elif avg_confidence >= 0.60:
            metadata["confidence_level"] = ExtractionConfidence.MEDIUM.value
        elif avg_confidence >= 0.40:
            metadata["confidence_level"] = ExtractionConfidence.LOW.value
        else:
            metadata["confidence_level"] = ExtractionConfidence.UNCERTAIN.value


def create_hybrid_extractor(
    ai_provider=None, 
    rule_extractor=None
) -> HybridExtractor:
    """Factory function to create hybrid extractor"""
    return HybridExtractor(ai_provider=ai_provider, rule_extractor=rule_extractor)
