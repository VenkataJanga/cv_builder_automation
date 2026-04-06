"""
Hybrid Extraction Service - Combines multiple extraction strategies

Features:
- Multi-source extraction (PDF, DOCX, voice transcript)
- Intelligent result merging
- Confidence-weighted synthesis
- Fallback strategies
- Data reconciliation
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ExtractionSource(str, Enum):
    """Source types for extraction"""
    PDF = "pdf"
    DOCX = "docx"
    VOICE = "voice"
    MANUAL = "manual"
    HYBRID = "hybrid"


class MergeStrategy(str, Enum):
    """Strategies for merging conflicting data"""
    HIGHEST_CONFIDENCE = "highest_confidence"
    MOST_COMPLETE = "most_complete"
    NEWEST = "newest"
    MANUAL_PRIORITY = "manual_priority"


@dataclass
class ExtractionResult:
    """Result from a single extraction source"""
    source: ExtractionSource
    data: Dict[str, Any]
    confidence_scores: Dict[str, float]  # Per-field confidence
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class HybridResult:
    """Combined result from multiple sources"""
    merged_data: Dict[str, Any]
    sources_used: List[ExtractionSource]
    field_sources: Dict[str, ExtractionSource]  # Which source was used for each field
    confidence_scores: Dict[str, float]
    merge_conflicts: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class HybridExtractionService:
    """
    Combines multiple extraction sources intelligently
    
    Strategy:
    1. Extract from all available sources
    2. Calculate confidence per field per source
    3. Merge using configurable strategy
    4. Report conflicts for manual resolution
    """
    
    def __init__(
        self,
        merge_strategy: MergeStrategy = MergeStrategy.HIGHEST_CONFIDENCE
    ):
        self.merge_strategy = merge_strategy
        self.extraction_results: List[ExtractionResult] = []
    
    def add_extraction(
        self,
        source: ExtractionSource,
        data: Dict[str, Any],
        confidence_scores: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an extraction result to be merged"""
        result = ExtractionResult(
            source=source,
            data=data,
            confidence_scores=confidence_scores or {},
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        self.extraction_results.append(result)
        logger.info(f"Added extraction from {source}")
    
    def merge_all(self) -> HybridResult:
        """
        Merge all extraction results into a single coherent result
        
        Returns:
            HybridResult with merged data and metadata
        """
        if not self.extraction_results:
            logger.warning("No extraction results to merge")
            return HybridResult(
                merged_data={},
                sources_used=[],
                field_sources={},
                confidence_scores={},
                metadata={"warning": "No data to merge"}
            )
        
        logger.info(f"Merging {len(self.extraction_results)} extraction results")
        
        # Initialize merged result
        merged_data = {}
        field_sources = {}
        confidence_scores = {}
        conflicts = []
        
        # Get all unique field paths from all results
        all_field_paths = self._get_all_field_paths()
        
        # Merge each field
        for field_path in all_field_paths:
            merged_value, source, confidence, conflict = self._merge_field(field_path)
            
            if merged_value is not None:
                self._set_nested_value(merged_data, field_path, merged_value)
                field_sources[field_path] = source
                confidence_scores[field_path] = confidence
            
            if conflict:
                conflicts.append(conflict)
        
        sources_used = list(set(r.source for r in self.extraction_results))
        
        result = HybridResult(
            merged_data=merged_data,
            sources_used=sources_used,
            field_sources=field_sources,
            confidence_scores=confidence_scores,
            merge_conflicts=conflicts,
            metadata={
                "merge_strategy": self.merge_strategy.value,
                "num_sources": len(self.extraction_results),
                "num_conflicts": len(conflicts),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        logger.info(f"Merge complete. {len(conflicts)} conflicts detected")
        
        return result
    
    def _get_all_field_paths(self) -> List[str]:
        """Get all unique field paths across all extraction results"""
        all_paths = set()
        
        for result in self.extraction_results:
            paths = self._extract_field_paths(result.data)
            all_paths.update(paths)
        
        return sorted(all_paths)
    
    def _extract_field_paths(
        self,
        data: Dict[str, Any],
        prefix: str = ""
    ) -> List[str]:
        """Recursively extract all field paths from nested dict"""
        paths = []
        
        for key, value in data.items():
            full_path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                paths.extend(self._extract_field_paths(value, full_path))
            else:
                paths.append(full_path)
        
        return paths
    
    def _merge_field(
        self,
        field_path: str
    ) -> Tuple[Any, ExtractionSource, float, Optional[Dict[str, Any]]]:
        """
        Merge a single field from all sources
        
        Returns:
            (merged_value, source_used, confidence, conflict_info)
        """
        # Collect all values for this field
        candidates = []
        
        for result in self.extraction_results:
            value = self._get_nested_value(result.data, field_path)
            
            if value is not None and value != "" and value != []:
                confidence = result.confidence_scores.get(field_path, 0.5)
                
                candidates.append({
                    "value": value,
                    "source": result.source,
                    "confidence": confidence,
                    "timestamp": result.timestamp
                })
        
        if not candidates:
            return None, ExtractionSource.HYBRID, 0.0, None
        
        if len(candidates) == 1:
            # No conflict, use the only value
            c = candidates[0]
            return c["value"], c["source"], c["confidence"], None
        
        # Multiple values - use merge strategy
        conflict_info = None
        
        if self.merge_strategy == MergeStrategy.HIGHEST_CONFIDENCE:
            winner = max(candidates, key=lambda x: x["confidence"])
        
        elif self.merge_strategy == MergeStrategy.MOST_COMPLETE:
            winner = max(candidates, key=lambda x: self._calculate_completeness(x["value"]))
        
        elif self.merge_strategy == MergeStrategy.NEWEST:
            winner = max(candidates, key=lambda x: x["timestamp"])
        
        elif self.merge_strategy == MergeStrategy.MANUAL_PRIORITY:
            # Prioritize manual > voice > docx > pdf
            priority = {
                ExtractionSource.MANUAL: 4,
                ExtractionSource.VOICE: 3,
                ExtractionSource.DOCX: 2,
                ExtractionSource.PDF: 1
            }
            winner = max(candidates, key=lambda x: priority.get(x["source"], 0))
        
        else:
            winner = candidates[0]
        
        # Check if there's significant disagreement
        if self._has_significant_conflict(candidates, winner):
            conflict_info = {
                "field": field_path,
                "candidates": candidates,
                "selected": winner,
                "reason": self.merge_strategy.value
            }
        
        return winner["value"], winner["source"], winner["confidence"], conflict_info
    
    def _calculate_completeness(self, value: Any) -> float:
        """Calculate how complete a value is"""
        if value is None or value == "":
            return 0.0
        
        if isinstance(value, (list, tuple)):
            return len(value)
        
        if isinstance(value, dict):
            return sum(1 for v in value.values() if v)
        
        if isinstance(value, str):
            return len(value.split())
        
        return 1.0
    
    def _has_significant_conflict(
        self,
        candidates: List[Dict[str, Any]],
        winner: Dict[str, Any]
    ) -> bool:
        """Check if there's a significant conflict between candidates"""
        if len(candidates) < 2:
            return False
        
        # Check if winner's confidence is only marginally better
        winner_conf = winner["confidence"]
        other_confs = [c["confidence"] for c in candidates if c != winner]
        
        if other_confs and max(other_confs) > winner_conf - 0.1:
            return True
        
        # Check if values are significantly different
        winner_value = str(winner["value"]).lower()
        for candidate in candidates:
            if candidate != winner:
                other_value = str(candidate["value"]).lower()
                if winner_value != other_value:
                    return True
        
        return False
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dict using dot notation"""
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        
        return value
    
    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set value in nested dict using dot notation"""
        keys = path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def enhance_with_rag(
        self,
        result: HybridResult,
        rag_context: Optional[Dict[str, Any]] = None
    ) -> HybridResult:
        """
        Enhance merged result with RAG-retrieved information
        
        Args:
            result: Hybrid extraction result
            rag_context: Retrieved context from RAG system
            
        Returns:
            Enhanced result
        """
        if not rag_context:
            return result
        
        logger.info("Enhancing result with RAG context")
        
        # Add retrieved information to metadata
        result.metadata["rag_enhanced"] = True
        result.metadata["rag_sources"] = rag_context.get("sources", [])
        
        # Use RAG to fill missing fields
        for field, value in rag_context.get("suggested_values", {}).items():
            if self._get_nested_value(result.merged_data, field) is None:
                self._set_nested_value(result.merged_data, field, value)
                result.field_sources[field] = ExtractionSource.HYBRID
                result.confidence_scores[field] = rag_context.get("confidence", 0.7)
                logger.info(f"Filled missing field {field} from RAG")
        
        return result
    
    def create_scaffold_for_missing_fields(
        self,
        result: HybridResult,
        required_schema: Dict[str, Any]
    ) -> HybridResult:
        """
        Create scaffold structure for missing required fields
        
        This ensures the output has all required fields, even if empty
        """
        logger.info("Creating scaffold for missing fields")
        
        def ensure_structure(schema: Dict[str, Any], data: Dict[str, Any]) -> None:
            """Recursively ensure data matches schema structure"""
            for key, value_type in schema.items():
                if key not in data:
                    # Create empty structure based on type
                    if value_type == "object" or isinstance(value_type, dict):
                        data[key] = {}
                        if isinstance(value_type, dict):
                            ensure_structure(value_type, data[key])
                    elif value_type == "array":
                        data[key] = []
                    elif value_type == "string":
                        data[key] = ""
                    elif value_type == "number":
                        data[key] = 0
                    elif value_type == "boolean":
                        data[key] = False
                    else:
                        data[key] = None
        
        ensure_structure(required_schema, result.merged_data)
        result.metadata["scaffolded"] = True
        
        return result


def merge_extraction_results(
    results: List[Dict[str, Any]],
    sources: List[ExtractionSource],
    strategy: MergeStrategy = MergeStrategy.HIGHEST_CONFIDENCE
) -> Dict[str, Any]:
    """
    Convenience function to merge multiple extraction results
    
    Args:
        results: List of extraction result dicts
        sources: List of source types (same length as results)
        strategy: Merge strategy to use
        
    Returns:
        Merged result dictionary
    """
    service = HybridExtractionService(merge_strategy=strategy)
    
    for result, source in zip(results, sources):
        service.add_extraction(source, result)
    
    hybrid_result = service.merge_all()
    return hybrid_result.merged_data
