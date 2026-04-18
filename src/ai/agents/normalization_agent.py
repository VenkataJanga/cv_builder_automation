"""
Normalization and Extraction Agent

Uses LLM to normalize user input and extract structured CV fields.
Provides fallback deterministic parsing if LLM unavailable.
"""

import json
import logging
import re
from typing import Dict, Any, Optional, List

from src.ai.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class NormalizationAgent:
    """
    Normalizes free-form CV input and extracts structured fields.
    
    Uses LLM-assisted extraction with deterministic fallback.
    """

    def __init__(self):
        """Initialize with LLM service."""
        self.llm_service = get_llm_service()

    def normalize_and_extract(
        self,
        raw_text: str,
        context: Optional[Dict[str, Any]] = None,
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """
        Normalize text and extract structured CV fields.
        
        Args:
            raw_text: Free-form user input (typed, transcript, or pasted)
            context: Optional context dict (role, source type, etc.)
            use_llm: Whether to attempt LLM extraction (fall back to deterministic if disabled)
            
        Returns:
            Dictionary with:
            {
              "normalized_text": str,
              "extracted_fields": {...},
              "confidence": {...},
              "warnings": [],
              "source": "llm" or "fallback"
            }
        """
        if not raw_text or not raw_text.strip():
            logger.debug("Empty input text provided")
            return self._empty_result()

        raw_text = raw_text.strip()
        logger.debug(f"Normalizing input ({len(raw_text)} chars)")

        # Try LLM extraction if enabled and configured
        if use_llm and self.llm_service.is_enabled():
            result = self._llm_extract_and_normalize(raw_text, context)
            if result:
                result["source"] = "llm"
                logger.info("Extraction via LLM successful")
                return result

        # Fall back to deterministic extraction
        logger.info("Using deterministic fallback extraction")
        result = self._deterministic_extract(raw_text)
        result["source"] = "fallback"
        return result

    def _llm_extract_and_normalize(
        self,
        raw_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to normalize and extract.
        
        Returns None if LLM call fails.
        """
        try:
            context_str = ""
            if context:
                if isinstance(context, dict):
                    context_str = " | ".join(f"{k}: {v}" for k, v in context.items() if v)

            system_message = (
                "You are a CV normalization and extraction expert. "
                "Normalize conversational text to professional CV language. "
                "Extract structured fields. Return valid JSON only."
            )

            prompt = f"""Normalize and extract CV information.

Input text:
{raw_text}

Context: {context_str}

Return JSON object:
{{
  "normalized_text": "professional version",
  "extracted_fields": {{
    "personal_details": {{
      "full_name": null,
      "email": null,
      "phone": null,
      "location": null,
      "current_title": null,
      "current_organization": null,
      "total_experience": null
    }},
    "summary": {{
      "professional_summary": null,
      "target_role": null
    }},
    "skills": {{
      "primary_skills": [],
      "technical_skills": []
    }},
    "work_experience": [],
    "project_experience": [],
    "education": []
  }},
  "confidence": {{
    "overall": 0.7
  }},
  "warnings": []
}}

Rules:
- Extract ONLY explicitly stated information
- Do not hallucinate missing data
- Preserve all factual content
- Fix grammar and professionalize language
- Leave fields null/empty if not found"""

            response = self.llm_service.call(
                prompt=prompt,
                system_message=system_message,
                temperature=0.2,
                max_tokens=4000,
                json_mode=True,
            )

            if not response:
                logger.warning("LLM returned empty response")
                return None

            return self._parse_llm_response(response, raw_text)

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return None

    def _parse_llm_response(self, response: str, original_text: str) -> Dict[str, Any]:
        """
        Parse and validate LLM response.
        
        Ensures response is valid JSON and has required structure.
        """
        try:
            data = json.loads(response)

            # Validate structure
            if not isinstance(data, dict):
                logger.warning("LLM response is not a dict")
                return self._deterministic_extract(original_text)

            # Ensure required fields
            if "extracted_fields" not in data:
                data["extracted_fields"] = {}
            if "confidence" not in data:
                data["confidence"] = {"overall": 0.7}
            if "warnings" not in data:
                data["warnings"] = []
            if "normalized_text" not in data:
                data["normalized_text"] = original_text

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return self._deterministic_extract(original_text)

    def _deterministic_extract(self, raw_text: str) -> Dict[str, Any]:
        """
        Deterministic extraction fallback.
        
        Uses regex and heuristics to extract basic information
        without LLM dependency.
        """
        extracted = {
            "personal_details": {},
            "summary": {},
            "skills": {},
            "work_experience": [],
            "project_experience": [],
            "education": [],
            "certifications": [],
        }

        # Extract email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw_text)
        if email_match:
            extracted["personal_details"]["email"] = email_match.group()

        # Extract phone (simple pattern)
        phone_match = re.search(
            r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            raw_text
        )
        if phone_match:
            extracted["personal_details"]["phone"] = phone_match.group()

        # Extract years of experience
        years_match = re.search(r'(\d+)\s*years?\s+of\s+experience', raw_text, re.I)
        if years_match:
            try:
                extracted["personal_details"]["total_experience"] = int(years_match.group(1))
            except ValueError:
                pass

        # Basic summary: use first paragraph or first 200 chars
        lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
        if lines:
            first_para = ' '.join(lines[:3])
            extracted["summary"]["professional_summary"] = first_para[:300]

        # Extract skills: look for common markers
        skills_match = re.search(
            r'(?:skills?|expertise?|technologies?|tech stack)[\s:]+([^.]+)',
            raw_text,
            re.I
        )
        if skills_match:
            skills_text = skills_match.group(1)
            # Split by comma, slash, or "and"
            skills = re.split(r'[,/]|and', skills_text)
            skills = [s.strip() for s in skills if s.strip()]
            extracted["skills"]["primary_skills"] = skills[:5]

        # Extract organizations mentioned
        org_pattern = r'(?:at|with|worked\s+at|employed\s+at|work(?:ed)?\s+at)\s+([A-Z][A-Za-z\s&]+)'
        org_matches = re.findall(org_pattern, raw_text)
        if org_matches:
            extracted["personal_details"]["current_organization"] = org_matches[0].strip()

        # Extract job titles
        title_pattern = r'(?:as|role|position|title|worked\s+as)\s+(?:a|an)?\s+([A-Za-z\s]+?)(?:\s+at|,|\.|$)'
        title_matches = re.findall(title_pattern, raw_text, re.I)
        if title_matches:
            extracted["personal_details"]["current_title"] = title_matches[0].strip()

        # Extract education
        edu_keywords = ['bachelor', 'master', 'diploma', 'degree', 'b.tech', 'b.s.', 'm.tech', 'mba']
        for keyword in edu_keywords:
            if keyword.lower() in raw_text.lower():
                extracted["education"].append({
                    "degree": keyword.capitalize(),
                    "institution": "",
                    "field_of_study": "",
                    "year_of_passing": None
                })
                break

        return {
            "normalized_text": raw_text,  # Would need actual normalization logic
            "extracted_fields": extracted,
            "confidence": {
                "overall": 0.5,  # Lower confidence for deterministic
                "personal_details": 0.6,
                "summary": 0.7,
                "skills": 0.5,
                "experience": 0.4,
                "education": 0.5,
            },
            "warnings": [
                "Deterministic extraction used (LLM unavailable)",
                "Confidence scores may be lower than LLM extraction",
                "Manual review recommended for accuracy",
            ],
        }

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty extraction result."""
        return {
            "normalized_text": "",
            "extracted_fields": {
                "personal_details": {},
                "summary": {},
                "skills": {},
                "work_experience": [],
                "project_experience": [],
                "education": [],
                "certifications": [],
            },
            "confidence": {"overall": 0.0},
            "warnings": ["Empty input provided"],
            "source": "empty",
        }
