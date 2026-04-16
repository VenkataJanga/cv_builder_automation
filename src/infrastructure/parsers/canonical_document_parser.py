"""
Canonical Document Parser for CV Documents
Parses uploaded CV documents (DOC/DOCX/PDF) directly into Canonical CV Schema v1.1
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.infrastructure.parsers.docx_extractor import extract_docx
from src.infrastructure.parsers.doc_extractor import extract_doc
from src.infrastructure.parsers.pdf_extractor import extract_pdf
from src.domain.cv.services.schema_mapper_service import SchemaMapperService


class CanonicalDocumentParser:
    """
    Parser that outputs Canonical CV Schema v1.1 from uploaded CV documents
    Handles DOC, DOCX, and PDF resume/CV formats
    """
    
    def __init__(self):
        self.schema_version = "1.1.0"
        self.schema_mapper = SchemaMapperService()
    
    def parse_document_to_canonical(
        self, 
        file_path: str, 
        session_id: Optional[str] = None, 
        file_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse CV document into Canonical CV Schema v1.1
        
        Args:
            file_path: Path to CV file (DOC/DOCX/PDF)
            session_id: Optional session ID
            file_metadata: Optional file metadata (filename, size, etc.)
            
        Returns:
            Dict following Canonical CV Schema v1.1
            
        Raises:
            ValueError: If file format is unsupported or text extraction fails
        """
        # Step 1: Extract text from document
        text = self._extract_text_from_file(file_path)
        
        if not text or not text.strip():
            # Return minimal valid structure for empty document
            return self._create_empty_canonical(file_metadata)
        
        # Step 2: Parse document structure into intermediate format
        parsed_data = self._parse_document_structure(text)
        
        # Step 3: Map to canonical schema using SchemaMapperService
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: Parsed data keys: {list(parsed_data.keys())}")
        logger.info(f"DEBUG: personal_info: {parsed_data.get('personal_info')}")
        
        canonical_cv = self.schema_mapper.map_to_canonical(parsed_data, source_type="document_upload")
        
        logger.info(f"DEBUG: After mapping - candidate exists: {bool(canonical_cv.get('candidate'))}")
        logger.info(f"DEBUG: After mapping - candidate fullName: {canonical_cv.get('candidate', {}).get('fullName')}")
        
        # Step 4: Enrich metadata
        if not canonical_cv.get("metadata"):
            canonical_cv["metadata"] = {}
        
        canonical_cv["metadata"].update({
            "schemaVersion": self.schema_version,
            "sources": ["document_upload"],
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "documentMetadata": file_metadata or {}
        })
        
        return canonical_cv
    
    def _extract_text_from_file(self, file_path: str) -> str:
        """
        Extract text from uploaded CV file
        
        Args:
            file_path: Path to the file
            
        Returns:
            Extracted text content
            
        Raises:
            ValueError: If file format is unsupported
        """
        if file_path.endswith(".docx"):
            return extract_docx(file_path)
        elif file_path.endswith(".doc"):
            return extract_doc(file_path)
        elif file_path.endswith(".pdf"):
            return extract_pdf(file_path)
        else:
            raise ValueError("Unsupported file format. Please use .doc, .docx, or .pdf")
    
    def _create_empty_canonical(self, file_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create minimal valid canonical structure for empty/failed documents"""
        return {
            "candidate": {
                "fullName": None,
                "email": None,
                "phoneNumber": None,
                "currentOrganization": None,
                "currentDesignation": None,
                "totalExperienceYears": 0,
                "totalExperienceMonths": 0,
                "summary": "",
                "location": {}
            },
            "skills": {
                "primarySkills": [],
                "secondarySkills": [],
                "frameworks": [],
                "toolsAndPlatforms": []
            },
            "experience": {
                "projects": [],
                "workHistory": []
            },
            "education": [],
            "certifications": [],
            "personalDetails": {
                "languagesKnown": [],
                "dateOfBirth": None,
                "nationality": None,
                "maritalStatus": None
            },
            "metadata": {
                "schemaVersion": self.schema_version,
                "sources": ["document_upload"],
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
                "documentMetadata": file_metadata or {}
            }
        }
    
    def _parse_document_structure(self, text: str) -> Dict[str, Any]:
        """
        Parse CV document text into intermediate structured format
        This intermediate format will be mapped to canonical schema by SchemaMapperService
        
        Args:
            text: Extracted text from CV document
            
        Returns:
            Intermediate parsed structure
        """
        # Normalize text
        text = self._normalize_text(text)
        
        # Segment document into sections
        sections = self._segment_document(text)
        
        # Parse each section
        parsed_data = {
            "personal_info": self._parse_personal_info(sections.get("header", ""), text),
            "summary": self._parse_summary(sections.get("summary", "")),
            "experience": self._parse_experience(sections.get("experience", ""), text),
            "education": self._parse_education(sections.get("education", ""), text),
            "skills": self._parse_skills(sections.get("skills", ""), text),
            "certifications": self._parse_certifications(sections.get("certifications", ""), text),
            "projects": self._parse_projects(sections.get("projects", ""), text),
            "languages": self._parse_languages(sections.get("languages", ""), text)
        }
        
        return parsed_data
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for parsing"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    
    def _segment_document(self, text: str) -> Dict[str, str]:
        """
        Segment CV document into sections (header, summary, experience, education, etc.)
        
        Args:
            text: Full CV text
            
        Returns:
            Dict mapping section names to section text
        """
        sections = {}
        
        # Common section headers
        section_patterns = {
            "summary": r"(?:Professional\s+Summary|Summary|Profile|Objective|About\s+Me)",
            "experience": r"(?:Professional\s+Experience|Work\s+Experience|Experience|Employment\s+History|Work\s+History)",
            "education": r"(?:Education(?:al)?\s+(?:Qualifications|Background)?|Academic\s+Background|Qualifications)",
            "skills": r"(?:Technical\s+Skills|Skills|Core\s+Competencies|Expertise|Technologies)",
            "certifications": r"(?:Certifications?|Licenses?|Professional\s+Certifications?)",
            "projects": r"(?:Projects?|Key\s+Projects?|Professional\s+Projects?)",
            "languages": r"(?:Languages?|Language\s+Proficiency)"
        }
        
        # Extract header (first ~500 chars usually contain contact info)
        sections["header"] = text[:500]
        
        # Find section boundaries
        boundaries = []
        for section_name, pattern in section_patterns.items():
            matches = list(re.finditer(rf'\n\s*({pattern})\s*[:\n]', text, re.IGNORECASE))
            for match in matches:
                boundaries.append((match.start(), section_name, match.group(1)))
        
        # Sort boundaries by position
        boundaries.sort(key=lambda x: x[0])
        
        # Extract section text
        for i, (start_pos, section_name, header_text) in enumerate(boundaries):
            # Determine end position (start of next section or end of text)
            end_pos = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
            
            # Extract section content (skip the header itself)
            section_text = text[start_pos:end_pos]
            # Remove the section header from the text
            section_text = re.sub(rf'^.*?{re.escape(header_text)}\s*[:\n]\s*', '', section_text, flags=re.IGNORECASE)
            
            sections[section_name] = section_text.strip()
        
        return sections
    
    def _parse_personal_info(self, header_text: str, full_text: str) -> Dict[str, Any]:
        """Parse personal information from document header"""
        personal_info = {
            "name": self._extract_name(header_text, full_text),
            "email": self._extract_email(full_text),
            "phone": self._extract_phone(full_text),
            "location": self._extract_location(header_text, full_text),
            "linkedin": self._extract_linkedin(full_text),
            "github": self._extract_github(full_text)
        }
        return personal_info
    
    def _extract_name(self, header_text: str, full_text: str) -> Optional[str]:
        """Extract candidate name (usually first line or prominently displayed)"""
        # Try first line of header
        lines = header_text.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            # Check if first line looks like a name (2-4 words, capitalized OR all caps)
            if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}$', first_line):
                return first_line
            # Also accept ALL CAPS names
            if re.match(r'^[A-Z\s]+$', first_line) and 5 <= len(first_line) <= 50:
                return first_line
            # Accept first line if short and doesn't contain common headers
            if len(first_line) < 50 and not any(word in first_line.lower() for word in ['curriculum', 'resume', 'cv', 'vitae', 'professional']):
                return first_line
        
        # Try pattern matching in full text
        name_patterns = [
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # Start of text
            r'Name[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',  # "Name: John Doe"
            r'^([A-Z][A-Z\s]+)$',  # ALL CAPS NAME
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, full_text[:500], re.MULTILINE)
            if match:
                name = match.group(1).strip()
                if 5 <= len(name) <= 50:
                    return name
        
        return None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number"""
        phone_patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US/International
            r'\+?\d{10,15}',  # General international
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'  # US format
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(0)
                # Validate it has at least 10 digits
                if len(re.sub(r'\D', '', phone)) >= 10:
                    return phone
        
        return None
    
    def _extract_location(self, header_text: str, full_text: str) -> Dict[str, Any]:
        """Extract location information"""
        location = {"city": None, "state": None, "country": None}
        
        # Common location patterns in CVs
        location_patterns = [
            r'(?:Location|Address)[:\s]+([^|\n]+)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2})\b',  # City, ST
            r'\b([A-Z][a-z]+),\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'  # City, Country
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, header_text)
            if match:
                location_text = match.group(1) if match.lastindex == 1 else match.group(0)
                parts = [p.strip() for p in location_text.split(',')]
                if len(parts) >= 1:
                    location["city"] = parts[0]
                if len(parts) >= 2:
                    location["state"] = parts[1]
                if len(parts) >= 3:
                    location["country"] = parts[2]
                break
        
        return location
    
    def _extract_linkedin(self, text: str) -> Optional[str]:
        """Extract LinkedIn URL"""
        linkedin_pattern = r'(?:linkedin\.com/in/|linkedin\.com/pub/)[\w-]+'
        match = re.search(linkedin_pattern, text, re.IGNORECASE)
        return match.group(0) if match else None
    
    def _extract_github(self, text: str) -> Optional[str]:
        """Extract GitHub URL"""
        github_pattern = r'github\.com/[\w-]+'
        match = re.search(github_pattern, text, re.IGNORECASE)
        return match.group(0) if match else None
    
    def _parse_summary(self, summary_text: str) -> Optional[str]:
        """Parse professional summary"""
        if not summary_text or not summary_text.strip():
            return None
        
        # Clean up summary text
        summary = summary_text.strip()
        # Remove section headers if they snuck in
        summary = re.sub(r'^(?:Professional\s+)?Summary[:\s]*', '', summary, flags=re.IGNORECASE)
        
        return summary if len(summary) > 20 else None
    
    def _parse_experience(self, experience_text: str, full_text: str) -> List[Dict[str, Any]]:
        """Parse work experience/employment history"""
        experience = []
        
        if not experience_text:
            return experience
        
        # Split into individual job entries
        job_entries = self._split_job_entries(experience_text)
        
        for entry in job_entries:
            job = self._parse_job_entry(entry)
            if job:
                experience.append(job)
        
        return experience
    
    def _split_job_entries(self, text: str) -> List[str]:
        """Split experience section into individual job entries"""
        # Jobs typically start with company name or job title (capitalized lines)
        # or with date ranges
        entries = []
        
        # Pattern to detect job entry boundaries (dates, companies, titles)
        boundary_pattern = r'\n\s*(?:[A-Z][^\n]{20,80}\n|\d{4}\s*[-–—]\s*(?:\d{4}|Present))'
        
        parts = re.split(boundary_pattern, text)
        
        current_entry = ""
        for part in parts:
            if part and part.strip():
                if len(current_entry) > 50:  # Minimum length for a job entry
                    entries.append(current_entry.strip())
                    current_entry = part
                else:
                    current_entry += part
        
        if current_entry.strip():
            entries.append(current_entry.strip())
        
        return entries if entries else [text]
    
    def _parse_job_entry(self, entry: str) -> Optional[Dict[str, Any]]:
        """Parse a single job entry"""
        # Extract dates
        dates = self._extract_dates(entry)
        
        # Extract company name
        company = self._extract_company_name(entry)
        
        # Extract job title
        title = self._extract_job_title(entry)
        
        # Extract description/responsibilities
        description = self._extract_job_description(entry)
        
        if not (company or title):
            return None
        
        return {
            "company": company,
            "title": title,
            "startDate": dates.get("start"),
            "endDate": dates.get("end"),
            "description": description,
            "responsibilities": [description] if description else []
        }
    
    def _extract_dates(self, text: str) -> Dict[str, Optional[str]]:
        """Extract start and end dates from text"""
        dates = {"start": None, "end": None}
        
        # Common date range patterns
        date_patterns = [
            r'(\d{1,2}/\d{4})\s*[-–—]\s*(\d{1,2}/\d{4}|Present|Current)',
            r'(\w+\s+\d{4})\s*[-–—]\s*(\w+\s+\d{4}|Present|Current)',
            r'(\d{4})\s*[-–—]\s*(\d{4}|Present|Current)'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dates["start"] = match.group(1)
                dates["end"] = match.group(2)
                break
        
        return dates
    
    def _extract_company_name(self, text: str) -> Optional[str]:
        """Extract company name from job entry"""
        # Company names usually appear near the top, often capitalized
        lines = text.strip().split('\n')
        
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            # Look for capitalized lines that aren't dates
            if line and not re.search(r'\d{4}', line):
                # Clean up
                line = re.sub(r'\s*[-–—]\s*$', '', line)
                if len(line) > 2 and len(line) < 100:
                    return line
        
        return None
    
    def _extract_job_title(self, text: str) -> Optional[str]:
        """Extract job title from entry"""
        # Title often appears in first few lines
        title_patterns = [
            r'(?:Position|Title|Role)[:\s]+([^\n]{5,60})',
            r'^([A-Z][^\n]{10,60})$'  # Capitalized line
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                title = match.group(1).strip()
                if not re.search(r'\d{4}', title):  # Not a date
                    return title
        
        return None
    
    def _extract_job_description(self, text: str) -> str:
        """Extract job description/responsibilities"""
        # Remove dates and title lines, keep the rest
        lines = text.split('\n')
        description_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip lines that are just dates or too short
            if line and len(line) > 20 and not re.match(r'^\d{4}.*\d{4}', line):
                description_lines.append(line)
        
        return ' '.join(description_lines) if description_lines else ""
    
    def _parse_education(self, education_text: str, full_text: str) -> List[Dict[str, Any]]:
        """Parse education section"""
        education = []
        
        if not education_text:
            return education
        
        # Split into individual education entries
        entries = self._split_education_entries(education_text)
        
        for entry in entries:
            edu = self._parse_education_entry(entry)
            if edu:
                education.append(edu)
        
        return education
    
    def _split_education_entries(self, text: str) -> List[str]:
        """Split education section into individual entries"""
        # Education entries often separated by dates or degree names
        entries = re.split(r'\n\s*(?=\d{4}|\b(?:Bachelor|Master|PhD|B\.?S\.?|M\.?S\.?|MBA))', text)
        return [e.strip() for e in entries if e.strip()]
    
    def _parse_education_entry(self, entry: str) -> Optional[Dict[str, Any]]:
        """Parse a single education entry"""
        degree = self._extract_degree(entry)
        field = self._extract_field_of_study(entry)
        institution = self._extract_institution_name(entry)
        year = self._extract_year(entry)
        gpa = self._extract_gpa(entry)
        
        if not (degree or institution):
            return None
        
        return {
            "degree": degree,
            "field": field,
            "institution": institution,
            "year": year,
            "gpa": gpa
        }
    
    def _extract_degree(self, text: str) -> Optional[str]:
        """Extract degree name"""
        degree_patterns = [
            r'\b(Bachelor\'?s?|Master\'?s?|PhD|Doctorate)\b',
            r'\b(B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?|MBA|MCA|B\.?Tech|M\.?Tech)\b'
        ]
        
        for pattern in degree_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_field_of_study(self, text: str) -> Optional[str]:
        """Extract field of study"""
        field_patterns = [
            r'(?:in|of)\s+([A-Z][^\n,]{5,50})',
            r'\b(Computer Science|Engineering|Business Administration|Information Technology)\b'
        ]
        
        for pattern in field_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_institution_name(self, text: str) -> Optional[str]:
        """Extract institution name"""
        # Institution names often appear as capitalized lines
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) > 10 and re.search(r'(?:University|College|Institute|School)', line, re.IGNORECASE):
                return line
        
        return None
    
    def _extract_year(self, text: str) -> Optional[str]:
        """Extract graduation year"""
        year_match = re.search(r'\b(19\d{2}|20[0-2]\d)\b', text)
        return year_match.group(1) if year_match else None
    
    def _extract_gpa(self, text: str) -> Optional[str]:
        """Extract GPA/grade"""
        gpa_patterns = [
            r'GPA[:\s]+(\d+\.?\d*)',
            r'(\d+\.?\d+)\s*/\s*4\.0',
            r'(\d+)%'
        ]
        
        for pattern in gpa_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _parse_skills(self, skills_text: str, full_text: str) -> List[str]:
        """Parse skills section"""
        skills = []
        
        if not skills_text:
            return skills
        
        # Common skill separators
        separators = r'[,;•\n]+'
        skill_items = re.split(separators, skills_text)
        
        for item in skill_items:
            item = item.strip()
            # Clean up bullet points and numbering
            item = re.sub(r'^[-•\d]+[\.\)]\s*', '', item)
            if len(item) > 2 and len(item) < 50:
                skills.append(item)
        
        return skills
    
    def _parse_certifications(self, cert_text: str, full_text: str) -> List[Dict[str, Any]]:
        """Parse certifications section"""
        certifications = []
        
        if not cert_text:
            return certifications
        
        # Split by lines or common separators
        cert_lines = re.split(r'\n|;', cert_text)
        
        for line in cert_lines:
            line = line.strip()
            # Clean up bullets
            line = re.sub(r'^[-•\d]+[\.\)]\s*', '', line)
            
            if len(line) > 5:
                cert = {
                    "name": line,
                    "issuer": None,
                    "date": None
                }
                
                # Try to extract issuer (often in parentheses or after "by")
                issuer_match = re.search(r'\(([^)]+)\)|by\s+(\w+)', line, re.IGNORECASE)
                if issuer_match:
                    cert["issuer"] = issuer_match.group(1) or issuer_match.group(2)
                
                # Try to extract date
                date_match = re.search(r'\d{4}', line)
                if date_match:
                    cert["date"] = date_match.group(0)
                
                certifications.append(cert)
        
        return certifications
    
    def _parse_projects(self, projects_text: str, full_text: str) -> List[Dict[str, Any]]:
        """Parse projects section"""
        projects = []
        
        if not projects_text:
            return projects
        
        # Split into individual project entries
        project_entries = re.split(r'\n\s*(?=[A-Z][^\n]{10,60}\n)', projects_text)
        
        for entry in project_entries:
            if len(entry.strip()) < 20:
                continue
            
            lines = entry.strip().split('\n')
            project_name = lines[0].strip() if lines else "Unnamed Project"
            description = ' '.join(lines[1:]) if len(lines) > 1 else ""
            
            projects.append({
                "name": project_name,
                "description": description,
                "technologies": [],
                "role": None
            })
        
        return projects
    
    def _parse_languages(self, lang_text: str, full_text: str) -> List[str]:
        """Parse languages section"""
        languages = []
        
        if not lang_text:
            return languages
        
        # Common languages
        common_langs = ['English', 'Spanish', 'French', 'German', 'Hindi', 'Chinese', 'Japanese', 'Arabic', 'Portuguese', 'Russian']
        
        for lang in common_langs:
            if re.search(r'\b' + re.escape(lang) + r'\b', lang_text, re.IGNORECASE):
                languages.append(lang)
        
        return languages
