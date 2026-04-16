"""
Resume Parser for DOCX/PDF Upload

Extracts structured CV data from uploaded documents and maps to Canonical CV Schema.

Key Features:
1. Handles DOCX and PDF document uploads
2. Extracts all CV fields (personal details, skills, experience, education)
3. Integrates with SchemaMapperService for canonical format
4. Ensures consistency across all input modes

Author: CV Builder Automation Team
Last Updated: 2026
"""

import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.domain.cv.services.schema_mapper_service import get_schema_mapper_service

logger = logging.getLogger(__name__)


class ResumeParser:
    """
    Parser for extracting structured CV data from DOCX/PDF documents.
    
    This class handles document parsing and delegates mapping to the
    SchemaMapperService to ensure consistent canonical schema usage.
    """
    
    def __init__(self):
        """Initialize the resume parser with schema mapper."""
        self.schema_mapper = get_schema_mapper_service()
    
    def parse(self, text: str, cv_id: Optional[str] = None, file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse document text and return data in Canonical CV Schema format.
        
        Args:
            text: Extracted text from DOCX or PDF
            cv_id: Optional CV identifier
            file_name: Original file name for metadata
            
        Returns:
            Dictionary conforming to Canonical CV Schema (v1.1)
            
        Process Flow:
            1. Extract raw data from document text
            2. Structure data in intermediate format
            3. Map to Canonical CV Schema via SchemaMapperService
            4. Return canonical format for downstream processing
        """
        logger.info(f"Starting document parsing for file: {file_name or 'unknown'}")
        
        try:
            # Split text into lines for processing
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            
            # Step 1: Extract raw data from document
            logger.debug("Extracting raw data from document...")
            personal_details = self._extract_personal_details(text, lines)
            skills = self._extract_skills(text)
            work_experience = self._extract_work_experience(text)
            education = self._extract_education(text)
            certifications = self._extract_certifications(text)
            projects = self._extract_projects(text)
            summary = self._extract_summary(text)
            
            # Step 2: Structure data in intermediate format
            logger.debug("Structuring extracted data...")
            intermediate_data = {
                # Candidate information
                "candidate": {
                    "fullName": personal_details.get("full_name", ""),
                    "firstName": personal_details.get("full_name", "").split()[0] if personal_details.get("full_name") else "",
                    "lastName": personal_details.get("full_name", "").split()[-1] if personal_details.get("full_name") and len(personal_details.get("full_name", "").split()) > 1 else "",
                    "email": personal_details.get("email", ""),
                    "phoneNumber": personal_details.get("phone", ""),
                    "portalId": personal_details.get("employee_id", ""),
                    "currentLocation": {
                        "city": personal_details.get("location", ""),
                        "fullAddress": personal_details.get("location", "")
                    },
                    "totalExperienceYears": personal_details.get("experience_years", 0),
                    "totalExperienceMonths": personal_details.get("experience_months", 0),
                    "summary": summary
                },
                
                # Skills
                "skills": {
                    "primarySkills": skills.get("primary_skills", []),
                    "secondarySkills": skills.get("secondary_skills", []),
                    "technicalSkills": skills.get("technical_skills", []),
                    "toolsAndPlatforms": skills.get("tools_and_platforms", []),
                    "operatingSystems": skills.get("operating_systems", []),
                    "databases": skills.get("databases", []),
                    "cloudTechnologies": skills.get("cloud_technologies", [])
                },
                
                # Experience
                "experience": {
                    "workHistory": work_experience,
                    "projects": projects
                },
                
                # Education
                "education": education,
                
                # Certifications
                "certifications": certifications,
                
                # Metadata
                "sourceType": "document_upload",
                "inputFileName": file_name or "",
                "extractionTimestamp": datetime.now().isoformat()
            }
            
            # Step 3: Map to Canonical CV Schema using SchemaMapperService
            logger.debug("Mapping to Canonical CV Schema...")
            canonical_cv = self.schema_mapper.map_to_canonical(
                source_data=intermediate_data,
                source_type="document_upload",
                cv_id=cv_id
            )
            
            logger.info("Successfully parsed document and mapped to Canonical CV Schema")
            return canonical_cv
            
        except Exception as e:
            logger.error(f"Error during document parsing: {e}", exc_info=True)
            # Return empty canonical schema on error
            from src.domain.cv.models.canonical_cv_schema import create_empty_canonical_cv
            return create_empty_canonical_cv(cv_id=cv_id or "", source_type="document_upload")
    
    def low_confidence(self, parsed: Dict[str, Any]) -> bool:
        """
        Determine if parsed data has low confidence.
        
        Args:
            parsed: Parsed CV data in canonical format
            
        Returns:
            True if confidence is low, False otherwise
        """
        try:
            candidate = parsed.get("candidate", {})
            skills = parsed.get("skills", {})
            
            # Check if essential fields are present
            has_name = bool(candidate.get("fullName"))
            has_skills = bool(skills.get("primarySkills") or skills.get("technicalSkills"))
            
            return not (has_name and has_skills)
        except Exception:
            return True
    
    def _extract_personal_details(self, text: str, lines: List[str]) -> Dict[str, Any]:
        """Extract personal details from document."""
        details = {}
        
        # Name - typically first line if it looks like a name
        if lines and self._looks_like_name(lines[0]):
            details["full_name"] = lines[0]
        
        # Email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            details["email"] = email_match.group(0)
        
        # Phone
        phone_patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                details["phone"] = phone_match.group(0)
                break
        
        # Employee/Portal ID
        id_patterns = [
            r'(?:Employee ID|Portal ID|ID):\s*([A-Z0-9]+)',
            r'(?:Employee|Portal)\s*:\s*([A-Z0-9]+)'
        ]
        for pattern in id_patterns:
            id_match = re.search(pattern, text, re.IGNORECASE)
            if id_match:
                details["employee_id"] = id_match.group(1).upper()
                break
        
        # Location
        location_patterns = [
            r'(?:Location|Address|City):\s*([A-Za-z\s,]+?)(?:\n|$)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2})\b'
        ]
        for pattern in location_patterns:
            location_match = re.search(pattern, text, re.IGNORECASE)
            if location_match:
                details["location"] = location_match.group(1).strip()
                break
        
        # Experience
        exp_match = re.search(r'(\d+)\+?\s*years?\s+(?:of\s+)?experience', text, re.IGNORECASE)
        if exp_match:
            details["experience_years"] = int(exp_match.group(1))
            details["experience_months"] = 0
        
        return details
    
    def _extract_summary(self, text: str) -> str:
        """Extract professional summary or objective."""
        headings = ["summary", "profile", "about", "objective", "professional summary"]
        summary = self._extract_section_block(text, headings)
        return summary
    
    def _extract_skills(self, text: str) -> Dict[str, List[str]]:
        """Extract all types of skills from document."""
        skills = {
            "primary_skills": [],
            "secondary_skills": [],
            "technical_skills": [],
            "tools_and_platforms": [],
            "operating_systems": [],
            "databases": [],
            "cloud_technologies": []
        }
        
        # Primary/Technical Skills
        primary_keywords = ["skills", "technical skills", "primary skills", "technologies", "expertise"]
        primary_skills_text = self._extract_inline_value(text, primary_keywords)
        if primary_skills_text:
            skills["primary_skills"] = self._parse_skills_list(primary_skills_text)
            skills["technical_skills"] = skills["primary_skills"].copy()
        
        # Secondary Skills
        secondary_keywords = ["secondary skills", "additional skills"]
        secondary_skills_text = self._extract_inline_value(text, secondary_keywords)
        if secondary_skills_text:
            skills["secondary_skills"] = self._parse_skills_list(secondary_skills_text)
        
        # Tools & Platforms
        tools_keywords = ["tools", "platforms", "tools and platforms"]
        tools_text = self._extract_inline_value(text, tools_keywords)
        if tools_text:
            skills["tools_and_platforms"] = self._parse_skills_list(tools_text)
        
        # Operating Systems
        os_list = []
        if re.search(r'\blinux\b', text, re.IGNORECASE):
            os_list.append("Linux")
        if re.search(r'\bwindows\b', text, re.IGNORECASE):
            os_list.append("Windows")
        if re.search(r'\bmac\s*os\b', text, re.IGNORECASE):
            os_list.append("macOS")
        skills["operating_systems"] = os_list
        
        # Databases
        db_mapping = {
            r'\bmysql\b': 'MySQL',
            r'\bpostgresql\b|\bpostgres\b': 'PostgreSQL',
            r'\boracle\b': 'Oracle',
            r'\bsql\s+server\b': 'SQL Server',
            r'\bmongodb\b': 'MongoDB',
            r'\bdb2\b': 'DB2'
        }
        for pattern, db_name in db_mapping.items():
            if re.search(pattern, text, re.IGNORECASE):
                skills["databases"].append(db_name)
        
        # Cloud Technologies
        if re.search(r'\baws\b|\bamazon web services\b', text, re.IGNORECASE):
            skills["cloud_technologies"].append("AWS")
        if re.search(r'\bazure\b', text, re.IGNORECASE):
            skills["cloud_technologies"].append("Azure")
        if re.search(r'\bgcp\b|\bgoogle cloud\b', text, re.IGNORECASE):
            skills["cloud_technologies"].append("GCP")
        
        return skills
    
    def _extract_work_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extract work history from document."""
        work_history = []
        
        # Look for experience section
        exp_section = self._extract_section_block(text, ["work experience", "experience", "employment", "work history"])
        if not exp_section:
            return work_history
        
        # Try to parse individual job entries
        # This is a simplified parser - production would need more robust parsing
        lines = exp_section.split('\n')
        current_job = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line looks like a company/title
            if re.match(r'^[A-Z]', line) and len(line) < 100:
                if current_job:
                    work_history.append(current_job)
                current_job = {"organization": line, "responsibilities": []}
            elif current_job:
                current_job["responsibilities"].append(line)
        
        if current_job:
            work_history.append(current_job)
        
        return work_history
    
    def _extract_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract education details from document."""
        education = []
        
        # Look for education section
        edu_section = self._extract_section_block(text, ["education", "academic", "qualifications"])
        if not edu_section:
            return education
        
        # Look for degree patterns
        degree_patterns = [
            r"(Bachelor'?s?\s+(?:of\s+)?(?:degree\s+in\s+)?[^,\n]+)",
            r"(Master'?s?\s+(?:of\s+)?(?:degree\s+in\s+)?[^,\n]+)",
            r"(B\.?Tech\.?\s+in\s+[^,\n]+)",
            r"(M\.?Tech\.?\s+in\s+[^,\n]+)"
        ]
        
        for pattern in degree_patterns:
            matches = re.finditer(pattern, edu_section, re.IGNORECASE)
            for match in matches:
                degree = match.group(1).strip()
                education.append({"degree": degree})
        
        return education
    
    def _extract_certifications(self, text: str) -> List[Dict[str, Any]]:
        """Extract certifications from document."""
        certifications = []
        
        # Look for certifications section
        cert_section = self._extract_section_block(text, ["certifications", "certificates", "credentials"])
        if not cert_section:
            return certifications
        
        # Split by lines and extract cert names
        lines = cert_section.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 5:
                certifications.append({"name": line})
        
        return certifications
    
    def _extract_projects(self, text: str) -> List[Dict[str, Any]]:
        """Extract project details from document."""
        projects = []
        
        # Look for projects section
        proj_section = self._extract_section_block(text, ["projects", "project experience"])
        if not proj_section:
            return projects
        
        # Try to parse project entries
        lines = proj_section.split('\n')
        current_project = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line looks like a project name
            if re.match(r'^[A-Z]', line) and len(line) < 100:
                if current_project:
                    projects.append(current_project)
                current_project = {"projectName": line, "responsibilities": []}
            elif current_project:
                current_project["responsibilities"].append(line)
        
        if current_project:
            projects.append(current_project)
        
        return projects
    
    # ============================================================================
    # HELPER METHODS FOR TEXT EXTRACTION
    # ============================================================================
    
    def _looks_like_name(self, text: str) -> bool:
        """
        Check if text looks like a person's name.
        
        Args:
            text: Text to check
            
        Returns:
            True if text appears to be a name, False otherwise
        """
        # Basic heuristics: starts with capital, 2-4 words, no special chars
        words = text.split()
        if len(words) < 1 or len(words) > 4:
            return False
        
        # Check if words start with capital letters
        for word in words:
            if not word[0].isupper():
                return False
        
        # Should not contain numbers or special chars (except periods for initials)
        if re.search(r'[0-9@#$%^&*()+=\[\]{}|\\/<>]', text):
            return False
        
        return True
    
    def _extract_section_block(self, text: str, headings: List[str]) -> str:
        """
        Extract text block following a section heading.
        
        Args:
            text: Full document text
            headings: List of possible section headings to look for
            
        Returns:
            Extracted section text, or empty string if not found
        """
        for heading in headings:
            # Look for heading (case-insensitive)
            pattern = rf'(?i)^{re.escape(heading)}[\s:]*\n(.*?)(?=\n[A-Z][A-Za-z\s]+:|$)'
            match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_inline_value(self, text: str, keywords: List[str]) -> str:
        """
        Extract value that follows a keyword on the same line.
        
        Args:
            text: Full document text
            keywords: List of keywords to search for
            
        Returns:
            Extracted value, or empty string if not found
        """
        for keyword in keywords:
            # Look for "Keyword: Value" pattern
            pattern = rf'(?i){re.escape(keyword)}[\s:]+([^\n]+)'
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _parse_skills_list(self, skills_text: str) -> List[str]:
        """
        Parse a skills string into a list of individual skills.
        
        Args:
            skills_text: Raw skills text (comma-separated, bullet-pointed, etc.)
            
        Returns:
            List of individual skill strings
        """
        # Split by common delimiters
        skills = []
        
        # Try comma-separated first
        if ',' in skills_text:
            skills = [s.strip() for s in skills_text.split(',')]
        # Try bullet points
        elif '•' in skills_text or '·' in skills_text:
            skills = [s.strip() for s in re.split(r'[•·]', skills_text)]
        # Try pipe separator
        elif '|' in skills_text:
            skills = [s.strip() for s in skills_text.split('|')]
        # Try semicolon
        elif ';' in skills_text:
            skills = [s.strip() for s in skills_text.split(';')]
        # Single skill
        else:
            skills = [skills_text.strip()]
        
        # Filter out empty strings
        skills = [s for s in skills if s]
        
        return skills
