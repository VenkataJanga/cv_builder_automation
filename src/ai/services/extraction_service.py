"""
Extraction Service

High-level service for extraction and normalization.
Coordinates between agent and CV schema mapping.
Handles fallback logic and error recovery.
"""

import logging
from typing import Dict, Any, Optional

from src.ai.agents.normalization_agent import NormalizationAgent
from src.core.config.settings import settings

logger = logging.getLogger(__name__)


class ExtractionService:
    """
    High-level extraction service with schema-aware merging.
    
    Responsibilities:
    - Coordinate extraction via NormalizationAgent
    - Merge extracted fields into CV data
    - Apply confidence scoring
    - Handle fallback logic
    """

    def __init__(self):
        """Initialize extraction service."""
        self.agent = NormalizationAgent()

    def extract_and_merge(
        self,
        raw_text: str,
        existing_cv_data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        merge_strategy: str = "questionnaire_wins",
    ) -> Dict[str, Any]:
        """
        Extract from raw text and merge with existing CV data.
        
        Args:
            raw_text: Free-form user input
            existing_cv_data: Current CV data (optional)
            context: Additional context for extraction
            merge_strategy: How to merge extracted fields
                - "questionnaire_wins": Questionnaire values override extracted
                - "extracted_wins": Extracted values override
                - "merge": Combine both, preferring questionnaire
                
        Returns:
            {
              "success": bool,
              "merged_cv_data": dict,
              "extracted_fields": dict,
              "confidence": dict,
              "warnings": list,
              "merged_fields": list of field names that changed
            }
        """
        logger.info(f"Starting extraction for {len(raw_text or '')} chars of text")

        # Use extraction based on feature flag
        use_extraction = settings.ENABLE_LLM_EXTRACTION or settings.ENABLE_LLM_NORMALIZATION
        logger.debug(f"LLM extraction enabled: {use_extraction}")

        # Extract fields
        extraction_result = self.agent.normalize_and_extract(
            raw_text=raw_text,
            context=context,
            use_llm=use_extraction,
        )

        if not extraction_result:
            logger.warning("Extraction returned empty result")
            return {
                "success": False,
                "merged_cv_data": existing_cv_data or {},
                "extracted_fields": {},
                "confidence": {},
                "warnings": ["Extraction failed"],
                "merged_fields": [],
            }

        # Merge extracted fields into CV data
        merged_cv_data = self._merge_fields(
            existing_cv_data or {},
            extraction_result.get("extracted_fields", {}),
            strategy=merge_strategy,
        )

        merged_fields = self._compute_merged_fields(
            existing_cv_data or {},
            merged_cv_data,
        )

        logger.info(f"Extraction complete. Merged {len(merged_fields)} fields.")

        return {
            "success": True,
            "merged_cv_data": merged_cv_data,
            "extracted_fields": extraction_result.get("extracted_fields", {}),
            "normalized_text": extraction_result.get("normalized_text", raw_text),
            "confidence": extraction_result.get("confidence", {}),
            "warnings": extraction_result.get("warnings", []),
            "merged_fields": merged_fields,
            "source": extraction_result.get("source", "unknown"),
        }

    def _merge_fields(
        self,
        existing_cv_data: Dict[str, Any],
        extracted_fields: Dict[str, Any],
        strategy: str = "questionnaire_wins",
    ) -> Dict[str, Any]:
        """
        Merge extracted fields into existing CV data.
        
        Args:
            existing_cv_data: Current CV data
            extracted_fields: Fields extracted by LLM
            strategy: Merge strategy
            
        Returns:
            Merged CV data dict
        """
        merged = existing_cv_data.copy()

        if not extracted_fields:
            return merged

        logger.debug(f"Merging fields with strategy: {strategy}")

        # Merge personal details
        if "personal_details" in extracted_fields:
            existing_personal = merged.get("personal_details", {})
            extracted_personal = extracted_fields["personal_details"]
            merged["personal_details"] = self._merge_dict_field(
                existing_personal,
                extracted_personal,
                strategy=strategy,
            )

        # Merge summary
        if "summary" in extracted_fields:
            existing_summary = merged.get("summary", {})
            extracted_summary = extracted_fields["summary"]
            merged["summary"] = self._merge_dict_field(
                existing_summary,
                extracted_summary,
                strategy=strategy,
            )

        # Merge skills
        if "skills" in extracted_fields:
            existing_skills = merged.get("skills", {})
            extracted_skills = extracted_fields["skills"]
            merged["skills"] = self._merge_dict_field(
                existing_skills,
                extracted_skills,
                strategy=strategy,
            )

        # Merge list fields (append extracted if they don't exist)
        for list_field in ["work_experience", "project_experience", "education", "certifications"]:
            if list_field in extracted_fields:
                extracted_list = extracted_fields[list_field]
                if isinstance(extracted_list, list) and extracted_list:
                    existing_list = merged.get(list_field, [])
                    if strategy == "questionnaire_wins":
                        # Only add if not already populated
                        if not existing_list and extracted_list:
                            merged[list_field] = extracted_list
                    else:
                        # Merge or append
                        merged[list_field] = self._merge_lists(existing_list, extracted_list)

        return merged

    def _merge_dict_field(
        self,
        existing: Dict[str, Any],
        extracted: Dict[str, Any],
        strategy: str,
    ) -> Dict[str, Any]:
        """Merge dict fields based on strategy."""
        merged = existing.copy()

        for key, extracted_value in extracted.items():
            if extracted_value is None or extracted_value == "":
                continue

            existing_value = merged.get(key)

            if strategy == "questionnaire_wins":
                # Keep existing if present and non-empty
                if not existing_value or existing_value == "":
                    merged[key] = extracted_value
            elif strategy == "extracted_wins":
                # Always use extracted
                merged[key] = extracted_value
            else:  # "merge"
                # Combine but prefer questionnaire
                if not existing_value or existing_value == "":
                    merged[key] = extracted_value

        return merged

    def _merge_lists(
        self,
        existing: list,
        extracted: list,
    ) -> list:
        """Merge lists of items (experience, projects, etc.)."""
        if not existing:
            return extracted or []

        if not extracted:
            return existing

        # Simple append strategy: add extracted items not already present
        merged = existing.copy()
        for item in extracted:
            if item not in merged:
                merged.append(item)

        return merged

    def _compute_merged_fields(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
    ) -> list:
        """
        Compute which fields changed during merge.
        
        Returns list of field paths that changed.
        """
        changed = []

        def compare_recursive(path: str, b: Any, a: Any):
            if b == a:
                return
            if isinstance(b, dict) and isinstance(a, dict):
                for key in set(list(b.keys()) + list(a.keys())):
                    compare_recursive(f"{path}.{key}" if path else key, b.get(key), a.get(key))
            elif isinstance(b, list) and isinstance(a, list):
                if len(b) != len(a):
                    changed.append(f"{path} (length)")
            else:
                changed.append(path)

        compare_recursive("", before, after)
        return changed

    def should_extract(self, question_type: str, question_text: str) -> bool:
        """
        Determine if extraction should be used for this question.
        
        Args:
            question_type: Type of question
            question_text: Question text
            
        Returns:
            True if extraction recommended
        """
        if not (settings.ENABLE_LLM_EXTRACTION or settings.ENABLE_LLM_NORMALIZATION):
            return False

        # Use extraction for long-form, summary-like, or transcript inputs
        extraction_triggers = [
            "transcript",
            "summary",
            "experience",
            "describe",
            "tell_us",
            "profile",
            "background",
        ]

        question_lower = (question_text or "").lower()
        return any(trigger in question_lower for trigger in extraction_triggers)
