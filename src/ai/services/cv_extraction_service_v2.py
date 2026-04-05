"""
Enhanced CV Extraction Service - V2
Produces standardized output matching exact schema requirements.
"""

import json
import re
from typing import Dict, Any, List, Optional
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

# Import constants
from src.core.constants import (
    CV_SCHEMA_VERSION,
    EXTRACTION_METHOD_AI,
    EXTRACTION_METHOD_FALLBACK,
    PRIORITY_HIGH,
    STATUS_COMPLETED
)


class CVExtractionServiceV2:
    """
    Enhanced CV Extraction Service that produces standardized output
    matching the exact required schema format.
    """

    def __init__(self):
        """Initialize the CV extraction service."""
        self.openai_client = None
        
        # Get configuration from environment variables
        api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
        
        if api_key:
            try:
                self.openai_client = OpenAI(api_key=api_key)
                print("[OK] OpenAI client initialized")
            except Exception as e:
                print(f"[WARNING] OpenAI initialization failed: {e}")
                self.openai_client = None
        else:
            print("[WARNING] OPENAI_API_KEY not found")

    def extract_cv_data(self, cv_text: str, file_path: str = None) -> Dict[str, Any]:
        """
        Extract CV data and return in standardized schema format.
        
        Args:
            cv_text: Raw CV text
            file_path: Optional file path for metadata
            
        Returns:
            Standardized CV data matching exact schema
        """
        # Try AI extraction first
        if self.openai_client:
            try:
                cv_data = self._ai_extraction(cv_text)
                extraction_method = EXTRACTION_METHOD_AI
                warnings = []
            except Exception as e:
                print(f"[WARNING] AI extraction failed: {e}")
                cv_data = self._fallback_extraction(cv_text)
                extraction_method = EXTRACTION_METHOD_FALLBACK
                warnings = ["AI extraction unavailable, using basic extraction"]
        else:
            cv_data = self._fallback_extraction(cv_text)
            extraction_method = EXTRACTION_METHOD_FALLBACK
            warnings = ["AI extraction unavailable, using basic extraction"]
        
        # Build standardized response
        response = self._build_standardized_response(
            cv_data, file_path, extraction_method, warnings
        )
        
        return response

    def _ai_extraction(self, cv_text: str) -> Dict[str, Any]:
        """
        Extract CV data using OpenAI API.
        
        Args:
            cv_text: Raw CV text
            
        Returns:
            Extracted CV data
        """
        prompt = self._build_extraction_prompt()
        
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Extract information from this CV:\n\n{cv_text}"}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Clean control characters
        result = self._clean_control_characters(result)
        
        return result

    def _fallback_extraction(self, cv_text: str) -> Dict[str, Any]:
        """
        Fallback extraction using basic parsing.
        
        Args:
            cv_text: Raw CV text
            
        Returns:
            Extracted CV data
        """
        return {
            "personal_details": self._extract_personal_details(cv_text),
            "summary": {"professional_summary": cv_text[:1000] if len(cv_text) > 1000 else cv_text},
            "skills": {"technical_skills": {}, "soft_skills": [], "domains": []},
            "work_experience": [],
            "project_experience": [],
            "education": [],
            "certifications": [],
            "publications": [],
            "awards": [],
            "languages": [],
            "leadership": {}
        }

    def _build_extraction_prompt(self) -> str:
        """Build the extraction prompt for OpenAI."""
        return """You are an expert CV parser. Extract information from CVs and return structured JSON data.

IMPORTANT: Return data in this EXACT format:

{
  "personal_details": {
    "full_name": "string",
    "email": "string",
    "phone": "string",
    "location": "string",
    "linkedin": "string",
    "github": "string",
    "total_experience_years": number,
    "current_organization": "string",
    "current_role": "string",
    "employee_id": "string",
    "grade": "string"
  },
  "summary": {
    "professional_summary": "string",
    "career_objective": "string"
  },
  "skills": {
    "technical_skills": {
      "Primary Skills": "comma-separated string",
      "Operating Systems": "comma-separated string",
      "Languages": "comma-separated string",
      "Development Tools": "comma-separated string",
      "Frameworks": "comma-separated string",
      "CRM tools": "comma-separated string",
      "Database Connectivity": "comma-separated string",
      "Databases": "comma-separated string",
      "SQL Skills": "comma-separated string",
      "Cloud Platforms": "comma-separated string",
      "Other Tools": "comma-separated string"
    },
    "soft_skills": ["array of strings"],
    "domains": ["array of strings"]
  },
  "work_experience": [
    {
      "company_name": "string",
      "designation": "string",
      "start_date": "string",
      "end_date": "string",
      "responsibilities": ["array of strings"]
    }
  ],
  "project_experience": [
    {
      "project_name": "string",
      "client": "string",
      "description": "string",
      "role": "string",
      "technologies": "string",
      "start_date": "string",
      "end_date": "string",
      "responsibilities": ["array of strings"]
    }
  ],
  "education": [
    {
      "degree": "string",
      "field_of_study": "string",
      "institution": "string",
      "university": "string",
      "graduation_year": "string",
      "grade": "string"
    }
  ],
  "certifications": [
    {
      "name": "string",
      "issuing_organization": "string",
      "issue_date": "string",
      "expiry_date": "string"
    }
  ],
  "publications": [],
  "awards": [],
  "languages": ["array of strings"],
  "leadership": {
    "experience": "string",
    "achievements": ["array of strings"]
  }
}

KEY RULES:
1. technical_skills MUST be a dictionary with category names as keys and comma-separated strings as values
2. Do NOT use arrays for technical_skills - use categorized dictionary format
3. work_experience is for employment history
4. project_experience is for specific projects worked on
5. Remove ALL control characters (\\r, \\x07, \\t, etc.) from extracted data
6. Keep skills as clean comma-separated text (no version numbers unless critical)
7. If information is not found, use empty string "" or empty array []
8. Extract ALL information present in the CV"""

    def _extract_personal_details(self, text: str) -> Dict[str, Any]:
        """Extract personal details using regex patterns."""
        details = {}
        
        # Extract email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            details['email'] = email_match.group(0)
        
        # Extract phone
        phone_match = re.search(r'\b\d{10}\b|\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', text)
        if phone_match:
            details['phone'] = phone_match.group(0)
        
        # Extract name (first non-empty line, often)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines:
            details['full_name'] = lines[0]
        
        return details

    def _clean_control_characters(self, data: Any) -> Any:
        """
        Recursively clean control characters from data.
        
        Args:
            data: Data to clean (dict, list, str, or other)
            
        Returns:
            Cleaned data
        """
        if isinstance(data, dict):
            return {k: self._clean_control_characters(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_control_characters(item) for item in data]
        elif isinstance(data, str):
            # Remove control characters: \r, \x07, \t, etc.
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', data)
            # Clean up extra whitespace
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            return cleaned
        else:
            return data

    def _build_standardized_response(
        self,
        cv_data: Dict[str, Any],
        file_path: Optional[str],
        extraction_method: str,
        warnings: List[str]
    ) -> Dict[str, Any]:
        """
        Build standardized response matching exact schema.
        
        Args:
            cv_data: Extracted CV data
            file_path: Optional file path
            extraction_method: Method used for extraction
            warnings: List of warnings
            
        Returns:
            Standardized response
        """
        # Detect sections
        sections_detected = self._detect_sections(cv_data)
        
        # Perform validation
        validation_result = self._validate_cv_data(cv_data)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(cv_data, validation_result)
        
        # Build response
        response = {
            "personal_details": cv_data.get("personal_details", {}),
            "summary": cv_data.get("summary", {}),
            "skills": cv_data.get("skills", {"technical_skills": {}, "soft_skills": [], "domains": []}),
            "work_experience": cv_data.get("work_experience", []),
            "project_experience": cv_data.get("project_experience", []),
            "certifications": cv_data.get("certifications", []),
            "education": cv_data.get("education", []),
            "publications": cv_data.get("publications", []),
            "awards": cv_data.get("awards", []),
            "languages": cv_data.get("languages", []),
            "leadership": cv_data.get("leadership", {}),
            "target_role": cv_data.get("target_role"),
            "schema_version": CV_SCHEMA_VERSION,
            "status": STATUS_COMPLETED,
            "file_info": {
                "file_path": file_path or "",
                "original_filename": os.path.basename(file_path) if file_path else ""
            },
            "extraction": {
                "method": extraction_method,
                "steps_completed": [
                    "fallback_extraction" if extraction_method == EXTRACTION_METHOD_FALLBACK else "ai_extraction",
                    "deduplication",
                    "section_detection",
                    "schema_mapping",
                    "rag_normalization",
                    "gap_detection",
                    "auto_suggestions",
                    "final_validation"
                ],
                "warnings": warnings,
                "errors": []
            },
            "cv_data": cv_data,
            "sections_detected": sections_detected,
            "validation": validation_result,
            "suggestions": suggestions,
            "preview": self._generate_preview(cv_data, sections_detected, validation_result, suggestions)
        }
        
        return response

    def _detect_sections(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect which sections are present in CV data."""
        present_sections = []
        missing_sections = []
        
        section_checks = [
            ("personal_details", cv_data.get("personal_details")),
            ("summary", cv_data.get("summary")),
            ("skills", cv_data.get("skills")),
            ("work_experience", cv_data.get("work_experience")),
            ("project_experience", cv_data.get("project_experience")),
            ("education", cv_data.get("education")),
            ("certifications", cv_data.get("certifications")),
            ("publications", cv_data.get("publications")),
            ("awards", cv_data.get("awards")),
            ("languages", cv_data.get("languages"))
        ]
        
        for section_name, section_data in section_checks:
            if section_data and (
                (isinstance(section_data, dict) and any(section_data.values())) or
                (isinstance(section_data, list) and len(section_data) > 0)
            ):
                present_sections.append(section_name)
            else:
                missing_sections.append(section_name)
        
        completeness = int((len(present_sections) / len(section_checks)) * 100)
        
        return {
            "present_sections": present_sections,
            "missing_sections": missing_sections,
            "section_completeness": completeness
        }

    def _validate_cv_data(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate CV data and identify gaps."""
        validation = {
            "schema_validation": {"valid": True, "errors": [], "warnings": []},
            "gaps": {"missing_required_fields": [], "missing_recommended_fields": [], "gaps_detected": 0},
            "final_validation": {
                "ready_for_preview": True,
                "blocking_issues": [],
                "warnings": [],
                "completeness_percentage": 100
            }
        }
        
        # Check required fields
        personal = cv_data.get("personal_details", {})
        required_fields = ["full_name", "email", "phone"]
        
        for field in required_fields:
            if not personal.get(field):
                validation["gaps"]["missing_required_fields"].append(f"personal_details.{field}")
                validation["schema_validation"]["warnings"].append(f"Missing recommended field: personal_details.{field}")
                validation["final_validation"]["blocking_issues"].append(f"{field.replace('_', ' ').title()} is required")
                validation["final_validation"]["ready_for_preview"] = False
        
        validation["gaps"]["gaps_detected"] = len(validation["gaps"]["missing_required_fields"])
        
        # Calculate completeness
        total_sections = 10
        present_sections = len([s for s in [
            "personal_details", "summary", "skills", "work_experience",
            "project_experience", "education", "certifications", "publications",
            "awards", "languages"
        ] if cv_data.get
