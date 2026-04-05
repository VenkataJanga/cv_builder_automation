"""
AI-powered CV extraction service using OpenAI for structured data extraction.
"""
import json
from typing import Dict, Any, Optional
from openai import OpenAI
import os


class CVExtractionService:
    """
    AI-based CV extraction service that uses OpenAI to extract structured data
    from CV text with comprehensive section detection and normalization.
    """
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY", "").strip('"')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"  # Fast and cost-effective for extraction
    
    def extract_structured_cv_data(self, cv_text: str) -> Dict[str, Any]:
        """
        Extract comprehensive structured CV data using AI.
        
        Args:
            cv_text: Raw text extracted from CV document
            
        Returns:
            Structured CV data matching canonical schema
        """
        
        extraction_prompt = self._build_extraction_prompt(cv_text)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert CV/resume parser. Extract structured information from CVs 
                        and return it in JSON format. Be thorough and extract all available information. 
                        Normalize data (e.g., standardize date formats, role titles). If information is missing, 
                        use empty arrays/strings/null as appropriate."""
                    },
                    {
                        "role": "user",
                        "content": extraction_prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                response_format={"type": "json_object"}
            )
            
            extracted_data = json.loads(response.choices[0].message.content)
            
            # Clean control characters from extracted data
            cleaned_data = self._clean_control_characters(extracted_data)
            
            # Validate and normalize the extracted data
            normalized_data = self._normalize_extracted_data(cleaned_data)
            
            return normalized_data
            
        except Exception as e:
            print(f"AI extraction failed: {str(e)}")
            # Fallback to basic extraction
            return self._basic_fallback_extraction(cv_text)
    
    def _build_extraction_prompt(self, cv_text: str) -> str:
        """Build comprehensive extraction prompt."""
        
        return f"""
Extract ALL information from this CV/resume into structured JSON format.

CV TEXT:
{cv_text}

---

Extract the following information into JSON format with this EXACT structure:

{{
  "personal_details": {{
    "full_name": "string",
    "email": "string",
    "phone": "string",
    "location": "string (city, country)",
    "linkedin": "string (URL if available)",
    "github": "string (URL if available)",
    "total_experience": "number (years, e.g., 10.5)",
    "current_organization": "string",
    "current_role": "string"
  }},
  "summary": {{
    "professional_summary": "string (2-3 sentences career summary)",
    "career_objective": "string (if mentioned separately)"
  }},
  "skills": {{
    "technical_skills": [
      {{"Primary Skills": "comma-separated primary technical skills ONLY"}},
      {{"Operating Systems": "comma-separated OS names if mentioned"}},
      {{"Languages": "comma-separated programming languages"}},
      {{"Development Tools": "comma-separated development tools/IDEs"}},
      {{"Frameworks": "comma-separated frameworks if mentioned"}},
      {{"CRM tools": "comma-separated CRM tools if mentioned"}},
      {{"Database Connectivity": "comma-separated database connectivity tools if mentioned"}},
      {{"Databases": "comma-separated database names"}},
      {{"SQL Skills": "comma-separated SQL related skills if mentioned"}},
      {{"Cloud Platforms": "comma-separated cloud platforms if mentioned"}}
    ],
    "soft_skills": ["array of soft skills like leadership, communication"],
    "domains": ["array of industry domains/expertise areas"]
  }},
  "experience": [
    {{
      "organization": "string",
      "role": "string",
      "location": "string",
      "duration": "string (e.g., 'Jan 2020 - Present')",
      "start_date": "string (YYYY-MM format if possible)",
      "end_date": "string (YYYY-MM or 'Present')",
      "responsibilities": ["array of key responsibilities/achievements"],
      "technologies_used": ["array of technologies/tools used in this role"]
    }}
  ],
  "project_experience": [
    {{
      "project_name": "string",
      "role": "string (role in the project)",
      "client": "string (if mentioned)",
      "duration": "string",
      "description": "string (project description)",
      "responsibilities": ["array of responsibilities"],
      "technologies": ["array of technologies used"],
      "achievements": ["array of key achievements/outcomes"]
    }}
  ],
  "education": [
    {{
      "degree": "string",
      "field_of_study": "string",
      "institution": "string",
      "location": "string",
      "graduation_year": "string or number",
      "grade": "string (GPA/percentage if mentioned)"
    }}
  ],
  "certifications": [
    {{
      "name": "string",
      "issuing_organization": "string",
      "issue_date": "string",
      "expiry_date": "string (if applicable)",
      "credential_id": "string (if available)"
    }}
  ],
  "publications": [
    {{
      "title": "string",
      "authors": ["array"],
      "publication": "string (journal/conference)",
      "year": "string or number",
      "link": "string (if available)"
    }}
  ],
  "awards": [
    {{
      "title": "string",
      "organization": "string",
      "year": "string or number",
      "description": "string"
    }}
  ],
  "languages": [
    {{
      "language": "string",
      "proficiency": "string (Native, Fluent, Professional, Basic)"
    }}
  ]
}}

IMPORTANT INSTRUCTIONS:
1. Extract ALL information you find - be comprehensive
2. If a section has no data, use empty arrays [] or empty strings ""
3. For skills.technical_skills, it MUST be an array of single-key objects where each object has ONE category
4. Each technical skill category should be a separate object in the array: [{{"Primary Skills": "..."}}, {{"Languages": "..."}}]
5. For "Primary Skills", ONLY include the skills explicitly listed under "Primary Skills" section in the CV
6. For each category, list items as comma-separated strings within the value
7. If a category doesn't have any skills, omit that object from the array entirely
8. Clean up skill names - remove version numbers unless they're significant (e.g., ".Net" not "9.6.1")
9. Normalize role titles (e.g., "Sr. Engineer" → "Senior Engineer")
10. Standardize company names (remove "Pvt Ltd", "Inc.", etc.)
11. Extract dates in consistent format when possible
12. Split responsibilities into clear bullet points
13. Identify and list all technologies/tools mentioned
14. Calculate total experience from work history if not explicitly stated
15. Distinguish between work experience and project experience
16. Return ONLY valid JSON, no additional text or control characters

CRITICAL: technical_skills MUST be an array of single-key objects, NOT a nested dictionary!

Extract thoroughly and return the JSON structure now.
"""
    
    def _clean_control_characters(self, data: Any) -> Any:
        """
        Recursively clean control characters from extracted data.
        Removes \r, \x07, and other control characters that may appear in parsed text.
        """
        import re
        
        if isinstance(data, dict):
            return {k: self._clean_control_characters(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_control_characters(item) for item in data]
        elif isinstance(data, str):
            # Remove control characters (except \n and \t which might be useful)
            cleaned = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', data)
            # Clean up multiple spaces and newlines
            cleaned = re.sub(r'\s+', ' ', cleaned)
            return cleaned.strip()
        else:
            return data
    
    def _normalize_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate extracted data."""
        
        # Ensure all required sections exist
        normalized = {
            "personal_details": data.get("personal_details", {}),
            "summary": data.get("summary", {}),
            "skills": data.get("skills", {}),
            "experience": data.get("experience", []),
            "project_experience": data.get("project_experience", []),
            "education": data.get("education", []),
            "certifications": data.get("certifications", []),
            "publications": data.get("publications", []),
            "awards": data.get("awards", []),
            "languages": data.get("languages", [])
        }
        
        # Clean up personal details
        if not isinstance(normalized["personal_details"], dict):
            normalized["personal_details"] = {}
        
        # Clean up arrays
        for key in ["experience", "project_experience", "education", "certifications", "publications", "awards", "languages"]:
            if not isinstance(normalized[key], list):
                normalized[key] = []
        
        # Normalize skills structure
        normalized["skills"] = self._normalize_skills(normalized.get("skills", {}))
        
        # Deduplicate projects
        normalized["project_experience"] = self._deduplicate_projects(normalized["project_experience"])
        
        # Deduplicate work experience
        normalized["experience"] = self._deduplicate_work_experience(normalized["experience"])
        
        return normalized
    
    def _normalize_skills(self, skills: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize skills structure to ensure consistent format.
        Ensures technical_skills is a dict with categorized skills.
        """
        normalized_skills = {
            "technical_skills": {},
            "soft_skills": [],
            "domains": []
        }
        
        # Handle technical_skills
        tech_skills = skills.get("technical_skills", {})
        if isinstance(tech_skills, dict):
            # Already in correct format, just clean it up
            for category, value in tech_skills.items():
                if value and value.strip():
                    normalized_skills["technical_skills"][category] = value.strip()
        elif isinstance(tech_skills, list):
            # Convert from list to categorized dict (fallback case)
            # Group all into "Other Tools" if it's just a flat list
            if tech_skills:
                normalized_skills["technical_skills"]["Other Tools"] = ", ".join(tech_skills)
        
        # Handle soft_skills
        soft_skills = skills.get("soft_skills", [])
        if isinstance(soft_skills, list):
            normalized_skills["soft_skills"] = [s.strip() for s in soft_skills if s and s.strip()]
        
        # Handle domains
        domains = skills.get("domains", [])
        if isinstance(domains, list):
            normalized_skills["domains"] = [d.strip() for d in domains if d and d.strip()]
        
        return normalized_skills
    
    def _basic_fallback_extraction(self, cv_text: str) -> Dict[str, Any]:
        """Fallback to basic extraction if AI fails."""
        import re
        
        result = {
            "personal_details": {},
            "summary": {},
            "skills": {},
            "experience": [],
            "project_experience": [],
            "education": [],
            "certifications": [],
            "publications": [],
            "awards": [],
            "languages": []
        }
        
        lines = [l.strip() for l in cv_text.split("\n") if l.strip()]
        if lines and self._looks_like_name(lines[0]):
            result["personal_details"]["full_name"] = lines[0]
        
        # Extract email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', cv_text)
        if email_match:
            result["personal_details"]["email"] = email_match.group(0)
        
        # Extract phone
        phone_match = re.search(r'[\+\(]?[0-9][0-9\s\-\(\)]{7,}[0-9]', cv_text)
        if phone_match:
            result["personal_details"]["phone"] = phone_match.group(0)
        
        # Extract experience years
        exp_match = re.search(r'(\d+\.?\d*)\s*\+?\s*(years|yrs|year|yr)', cv_text, re.IGNORECASE)
        if exp_match:
            result["personal_details"]["total_experience"] = float(exp_match.group(1))
        
        return result
    
    def _looks_like_name(self, value: str) -> bool:
        """Check if string looks like a person's name."""
        if len(value.split()) < 2 or len(value.split()) > 5:
            return False
        if ":" in value or "@" in value:
            return False
        return True
    
    def detect_gaps(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect missing or incomplete information in CV data.
        
        Returns:
            Dictionary with gaps and suggestions
        """
        gaps = {
            "missing_required_fields": [],
            "missing_recommended_fields": [],
            "incomplete_sections": [],
            "suggestions": []
        }
        
        # Check required fields
        required_fields = [
            ("personal_details.full_name", "Full Name"),
            ("personal_details.email", "Email"),
            ("personal_details.phone", "Phone"),
            ("summary.professional_summary", "Professional Summary"),
        ]
        
        for field_path, field_name in required_fields:
            if not self._get_nested_value(cv_data, field_path):
                gaps["missing_required_fields"].append(field_name)
        
        # Check recommended fields
        if not cv_data.get("experience") or len(cv_data.get("experience", [])) == 0:
            gaps["missing_recommended_fields"].append("Work Experience")
        
        if not cv_data.get("education") or len(cv_data.get("education", [])) == 0:
            gaps["missing_recommended_fields"].append("Education")
        
        skills = cv_data.get("skills", {})
        if not skills.get("technical_skills") or len(skills.get("technical_skills", [])) == 0:
            gaps["missing_recommended_fields"].append("Technical Skills")
        
        # Generate suggestions
        if gaps["missing_required_fields"]:
            gaps["suggestions"].append(f"Please provide: {', '.join(gaps['missing_required_fields'])}")
        
        if gaps["missing_recommended_fields"]:
            gaps["suggestions"].append(f"Consider adding: {', '.join(gaps['missing_recommended_fields'])}")
        
        # Check for incomplete experience entries
        for i, exp in enumerate(cv_data.get("experience", [])):
            if not exp.get("responsibilities") or len(exp.get("responsibilities", [])) == 0:
                gaps["incomplete_sections"].append(f"Experience #{i+1}: {exp.get('role', 'Unknown')} - missing responsibilities")
        
        return gaps
    
    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get nested dictionary value using dot notation."""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def _deduplicate_projects(self, projects: list) -> list:
        """
        Remove duplicate projects based on project name and key attributes.
        Uses fuzzy matching to handle slight variations.
        """
        if not projects or len(projects) <= 1:
            return projects
        
        unique_projects = []
        seen_signatures = set()
        
        for project in projects:
            # Create a signature for this project
            project_name = (project.get("project_name") or "").strip().lower()
            client = (project.get("client") or "").strip().lower()
            role = (project.get("role") or "").strip().lower()
            description = (project.get("description") or "").strip().lower()
            
            # Skip if project name is empty
            if not project_name:
                continue
            
            # Create a signature combining key fields
            # If two projects have the same name and client, they're likely duplicates
            signature = f"{project_name}|{client}"
            
            # Check if we've seen this signature before
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_projects.append(project)
            else:
                # This is a duplicate - merge any additional information
                # Find the existing project with this signature
                for existing_project in unique_projects:
                    existing_name = (existing_project.get("project_name") or "").strip().lower()
                    existing_client = (existing_project.get("client") or "").strip().lower()
                    existing_signature = f"{existing_name}|{existing_client}"
                    
                    if existing_signature == signature:
                        # Merge responsibilities if the duplicate has more
                        existing_resp = existing_project.get("responsibilities", [])
                        new_resp = project.get("responsibilities", [])
                        if len(new_resp) > len(existing_resp):
                            existing_project["responsibilities"] = new_resp
                        
                        # Merge technologies
                        existing_tech = set(existing_project.get("technologies", []))
                        new_tech = set(project.get("technologies", []))
                        existing_project["technologies"] = list(existing_tech | new_tech)
                        
                        # Use longer description
                        if len(project.get("description", "")) > len(existing_project.get("description", "")):
                            existing_project["description"] = project.get("description")
                        
                        break
        
        return unique_projects
    
    def _deduplicate_work_experience(self, experiences: list) -> list:
        """
        Remove duplicate work experience entries based on organization and role.
        """
        if not experiences or len(experiences) <= 1:
            return experiences
        
        unique_experiences = []
        seen_signatures = set()
        
        for experience in experiences:
            # Create a signature for this experience
            organization = (experience.get("organization") or "").strip().lower()
            role = (experience.get("role") or "").strip().lower()
            start_date = (experience.get("start_date") or "").strip().lower()
            
            # Skip if organization is empty
            if not organization:
                continue
            
            # Create a signature combining key fields
            signature = f"{organization}|{role}|{start_date}"
            
            # Check if we've seen this signature before
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_experiences.append(experience)
            else:
                # This is a duplicate - merge any additional information
                for existing_exp in unique_experiences:
                    existing_org = (existing_exp.get("organization") or "").strip().lower()
                    existing_role = (existing_exp.get("role") or "").strip().lower()
                    existing_start = (existing_exp.get("start_date") or "").strip().lower()
                    existing_signature = f"{existing_org}|{existing_role}|{existing_start}"
                    
                    if existing_signature == signature:
                        # Merge responsibilities if the duplicate has more
                        existing_resp = existing_exp.get("responsibilities", [])
                        new_resp = experience.get("responsibilities", [])
                        if len(new_resp) > len(existing_resp):
                            existing_exp["responsibilities"] = new_resp
                        
                        # Merge technologies
                        existing_tech = set(existing_exp.get("technologies_used", []))
                        new_tech = set(experience.get("technologies_used", []))
                        existing_exp["technologies_used"] = list(existing_tech | new_tech)
                        
                        break
        
        return unique_experiences
