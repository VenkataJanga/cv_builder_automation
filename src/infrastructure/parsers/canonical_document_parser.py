"""
Canonical Document Parser for CV Documents
Parses uploaded CV documents (DOC/DOCX/PDF) directly into Canonical CV Schema v1.1
"""

import re
import difflib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.infrastructure.parsers.docx_extractor import extract_docx
from src.infrastructure.parsers.doc_extractor import extract_doc
from src.infrastructure.parsers.pdf_extractor import extract_pdf
from src.domain.cv.services.schema_mapper_service import SchemaMapperService
from src.core.constants import (
    DESIGNATION_FALLBACKS,
    SUMMARY_SECTION_ALIASES,
    TECHNICAL_SECTION_ALIASES,
    PROJECT_SECTION_ALIASES,
)


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
        file_metadata: Optional[Dict[str, Any]] = None,
        extracted_text: Optional[str] = None,
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
        text = extracted_text if extracted_text is not None else self._extract_text_from_file(file_path)
        
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

    def extract_text(self, file_path: str) -> str:
        """Public helper to extract raw text from a supported CV document."""
        return self._extract_text_from_file(file_path)
    
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
        skills_data = self._parse_skills(sections.get("skills", ""), text)
        parsed_data = {
            "personal_info": self._parse_personal_info(sections.get("header", ""), text),
            "summary": self._parse_summary(sections.get("summary", ""), text),
            "experience": self._parse_experience(sections.get("experience", ""), text),
            "education": self._parse_education(sections.get("education", ""), text),
            "skills": skills_data,
            "certifications": self._parse_certifications(sections.get("certifications", ""), text),
            "projects": self._parse_projects(sections.get("projects", ""), text),
            "languages": self._parse_languages(sections.get("languages", ""), text),
            "domainExperience": skills_data.get("domainExperience", []) if isinstance(skills_data, dict) else [],
        }
        
        return parsed_data
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for parsing"""
        # Preserve line boundaries; section detection and entity extraction rely on them.
        text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\x07", " ")
        text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E]', ' ', text)

        cleaned_lines = []
        for raw_line in text.split("\n"):
            line = re.sub(r'\s+', ' ', raw_line).strip()
            if not line:
                cleaned_lines.append("")
                continue

            line = re.sub(r'(?i)^bjbj\s*', '', line).strip()
            line = re.sub(r'(?i)^resume\s+format\s*', '', line).strip()

            # Remove noisy footer tail that appears after resume content.
            if re.search(r'(?i)resume\s+format\s+ntt\s+data\s+protected', line):
                line = line.split('Resume Format')[0].strip()

            if re.search(r'(?i)\b(h;\|x|yt#9n|0j:|h66|ntt data\s+protected\s+page\s+page)\b', line):
                continue

            if line:
                cleaned_lines.append(line)

        text = "\n".join(cleaned_lines)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    
    def _segment_document(self, text: str) -> Dict[str, str]:
        """
        Segment CV document into sections (header, summary, experience, education, etc.)
        
        Args:
            text: Full CV text
            
        Returns:
            Dict mapping section names to section text
        """
        section_aliases = {
            "summary": SUMMARY_SECTION_ALIASES,
            "experience": [
                "professional experience", "work experience", "experience", "employment history", "work history"
            ],
            "education": [
                "education", "educational qualifications", "education background", "academic background", "qualifications", "qualification details"
            ],
            "skills": TECHNICAL_SECTION_ALIASES,
            "certifications": [
                "certification", "certifications", "license", "licenses", "professional certifications"
            ],
            "projects": PROJECT_SECTION_ALIASES,
            "languages": [
                "language", "languages", "language proficiency"
            ],
        }

        def resolve_section(line: str) -> Optional[str]:
            cleaned = re.sub(r'\s+', ' ', str(line or '').strip().lower()).rstrip(':').strip()
            cleaned = re.sub(r'^[^a-z0-9]+', '', cleaned)
            if not cleaned:
                return None
            for section_name, aliases in section_aliases.items():
                for alias in aliases:
                    if cleaned == alias:
                        return section_name

                    if cleaned.startswith(alias + ':'):
                        trailing = cleaned[len(alias) + 1:].strip()
                        # Treat as section header only when it's a true heading,
                        # not content such as "Project: Revenue Optimizer ...".
                        if not trailing or len(trailing.split()) <= 2:
                            return section_name
                        continue

                    if cleaned.startswith(alias + ' -'):
                        trailing = cleaned[len(alias) + 2:].strip()
                        if not trailing or len(trailing.split()) <= 2:
                            return section_name
                        continue

                    if cleaned.startswith(alias + ' |'):
                        trailing = cleaned[len(alias) + 2:].strip()
                        if not trailing or len(trailing.split()) <= 2:
                            return section_name
                        continue

                    if cleaned == alias + ' details':
                        return section_name
            return None

        sections: Dict[str, str] = {"header": ""}
        current_section = "header"

        for raw_line in text.split('\n'):
            line = raw_line.rstrip()
            matched_section = resolve_section(line)
            if matched_section:
                current_section = matched_section
                sections.setdefault(current_section, "")
                continue

            sections[current_section] = f"{sections[current_section]}\n{line}" if sections[current_section] else line

        return {name: value.strip() for name, value in sections.items() if value and value.strip()}
    
    def _parse_personal_info(self, header_text: str, full_text: str) -> Dict[str, Any]:
        """Parse personal information from document header"""
        personal_info = {
            "name": self._extract_name(header_text, full_text),
            "email": self._extract_email(full_text),
            "phone": self._extract_phone(full_text),
            "current_designation": self._extract_designation(header_text, full_text),
            "location": self._extract_location(header_text, full_text),
            "linkedin": self._extract_linkedin(full_text),
            "github": self._extract_github(full_text),
            "portal_id": self._extract_emp_id(full_text),
            "current_grade": self._extract_current_grade(full_text),
        }
        return personal_info
    
    def _extract_name(self, header_text: str, full_text: str) -> Optional[str]:
        """Extract candidate name (usually first line or prominently displayed)"""
        label_match = re.search(
            r'(?i)(?:^|\n).*?\bname\b\s*[:\-]\s*([A-Za-z][A-Za-z .\'\-]{1,60})',
            f"{header_text}\n{full_text[:1000]}",
            re.IGNORECASE | re.MULTILINE,
        )
        if label_match:
            name = label_match.group(1).strip()
            name = re.split(r'(?i)\b(?:emp\s*id|employee\s*id|current\s*grade)\b', name)[0].strip(' ,:-')
            if 2 <= len(name) <= 60:
                return name

        # Try first line of header
        lines = header_text.strip().split('\n')
        for line in lines[:8]:
            candidate = re.sub(r'(?i)^name\s*[:\-]\s*', '', line).strip()
            candidate = re.sub(r'(?i)^.*?\bname\b\s*[:\-]\s*', '', candidate).strip()
            candidate = re.split(r'(?i)\b(?:emp\s*id|employee\s*id|current\s*grade)\b', candidate)[0].strip(' ,:-')
            if not candidate:
                continue
            if any(token in candidate.lower() for token in ['@', 'http', 'www', 'resume', 'curriculum vitae', 'cv']):
                continue
            if re.search(r'\d', candidate):
                continue
            if re.match(r'^[A-Za-z][A-Za-z .\'\-]{1,60}$', candidate):
                return candidate
        
        # Try pattern matching in full text
        name_patterns = [
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # Start of text
            r'Name[:\s]+([A-Za-z][A-Za-z .\'\-]{1,60})',  # "Name: John Doe"
            r'^([A-Z][A-Z\s]+)$',  # ALL CAPS NAME
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, full_text[:500], re.MULTILINE | re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if 2 <= len(name) <= 60:
                    return name
        
        return None

    def _extract_emp_id(self, text: str) -> Optional[str]:
        match = re.search(r'(?i)\b(?:emp\s*id|employee\s*id|portal\s*id)\b\s*[:\-]?\s*([A-Za-z0-9\-/]+)', text)
        return match.group(1).strip() if match else None

    def _extract_current_grade(self, text: str) -> Optional[str]:
        match = re.search(r'(?i)\bcurrent\s+grade\b\s*[:\-]?\s*([A-Za-z0-9\-./]+)', text)
        return match.group(1).strip() if match else None

    def _extract_designation(self, header_text: str, full_text: str) -> Optional[str]:
        """Extract current designation/title with deterministic fallback matching."""
        scan_text = f"{header_text or ''}\n{full_text or ''}"

        explicit_patterns = [
            r'(?im)^\s*(?:current\s+designation|designation|current\s+role|role|title|current\s+title)\s*[:\-]\s*([^\n|]{3,100})',
            r'(?im)^\s*(?:position)\s*[:\-]\s*([^\n|]{3,100})',
        ]

        for pattern in explicit_patterns:
            match = re.search(pattern, scan_text)
            if not match:
                continue
            candidate = re.split(r'(?i)\b(?:organization|company|email|phone|emp\s*id|employee\s*id)\b', match.group(1))[0]
            candidate = re.sub(r'\s+', ' ', candidate).strip(' ,.;:-')
            if len(candidate) >= 3:
                return self._match_designation_fallback(candidate) or candidate

        lowered_full_text = (full_text or '').lower()
        for title in DESIGNATION_FALLBACKS:
            if title.lower() in lowered_full_text:
                return title

        # Fuzzy fallback against known designation taxonomy.
        line_candidates = []
        for line in (header_text or '').splitlines()[:20]:
            cleaned = re.sub(r'\s+', ' ', line).strip(' ,.;:-')
            if 4 <= len(cleaned) <= 80 and not re.search(r'@|\d{5,}|http', cleaned):
                line_candidates.append(cleaned)
        for candidate in line_candidates:
            matched = self._match_designation_fallback(candidate)
            if matched:
                return matched

        return None

    def _match_designation_fallback(self, value: str) -> Optional[str]:
        """Match free text to the closest known designation if similarity is adequate."""
        source = re.sub(r'\s+', ' ', str(value or '').strip()).lower()
        if not source:
            return None

        best_ratio = 0.0
        best_match = None
        for title in DESIGNATION_FALLBACKS:
            ratio = difflib.SequenceMatcher(a=source, b=title.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = title

        if best_match and best_ratio >= 0.62:
            return best_match
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

        # Prefer explicit location/address labels from the top of the document.
        header_window = "\n".join(str(header_text or "").split("\n")[:20])
        labeled_match = re.search(r'(?i)(?:^|\n)\s*(?:location|address)\s*[:\-]\s*([^\n|]+)', header_window)
        if labeled_match:
            location_text = labeled_match.group(1).strip()
            parts = [p.strip() for p in location_text.split(',') if p.strip()]
            if len(parts) >= 1:
                location["city"] = parts[0]
            if len(parts) >= 2:
                location["state"] = parts[1]
            if len(parts) >= 3:
                location["country"] = parts[2]
            return location

        # Conservative fallback: City, ST pattern only.
        city_state = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2})\b', header_window)
        if city_state:
            location["city"] = city_state.group(1).strip()
            location["state"] = city_state.group(2).strip()
        
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
    
    def _parse_summary(self, summary_text: str, full_text: str) -> Optional[str]:
        """Parse professional summary"""
        if not summary_text or not summary_text.strip():
            summary_text = self._slice_text_between_any_markers(
                full_text,
                SUMMARY_SECTION_ALIASES,
                TECHNICAL_SECTION_ALIASES + PROJECT_SECTION_ALIASES,
            )
            if not summary_text:
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
            experience = self._parse_experience_details_table(full_text)
            return experience
        
        # Split into individual job entries
        job_entries = self._split_job_entries(experience_text)
        
        for entry in job_entries:
            job = self._parse_job_entry(entry)
            if job:
                experience.append(job)

        if not experience:
            experience = self._parse_experience_details_table(full_text)
        
        return experience

    def _parse_experience_details_table(self, full_text: str) -> List[Dict[str, Any]]:
        block = self._slice_text_between_markers(
            full_text,
            "Experience Details",
            "Project Details",
        )
        if not block:
            return []

        compact = re.sub(r'\s+', ' ', block.replace('\x07', ' ')).strip()
        compact = re.sub(r'(?i)^.*?joining\s+date\s+relieving\s+date\s*', '', compact)
        date_pairs = list(re.finditer(r'(\d{2}-[A-Za-z]{3}-\d{4})\s+(Till\s+Date|\d{2}-[A-Za-z]{3}-\d{4})', compact, re.IGNORECASE))
        if not date_pairs:
            return []

        items = []
        cursor = 0
        for idx, match in enumerate(date_pairs):
            prefix = compact[cursor:match.start()].strip(' ,;:-')
            prefix = re.sub(r'^\d+\s+', '', prefix).strip()
            if prefix:
                items.append({
                    "company": prefix,
                    "title": "",
                    "startDate": match.group(1).strip(),
                    "endDate": match.group(2).strip(),
                    "description": "",
                    "responsibilities": [],
                })
            cursor = match.end()

        return items
    
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

        source_text = education_text or self._slice_text_between_markers(
            full_text,
            "Qualification Details",
            "",
        )
        if not source_text:
            source_text = full_text

        source_text = self._truncate_at_first_marker(
            source_text,
            [
                "Domain Expertise",
                "Technical Expertise",
                "Experience Details",
                "Professional Experience",
                "Project Name",
                "Training Attended / Certifications Done",
                "Personal Details",
                "Declaration",
                "EMP ID",
            ],
        )

        # --- STEP 1: NTT DATA row-numbered table format (highest priority) ---
        education = self._parse_education_table_rows(source_text)

        # --- STEP 1b: Label-paired format (Institution + Specialization rows) ---
        if len(education) < 2:
            labeled_entries = self._parse_labeled_education_entries(source_text)
            if len(labeled_entries) > len(education):
                education = labeled_entries

        # --- STEP 2: Entry-split approach (fallback) ---
        if not education:
            entries = self._split_education_entries(source_text)
            for entry in entries:
                edu = self._parse_education_entry(entry)
                if edu:
                    education.append(edu)

        # --- STEP 3: Digit-line fallback ---
        if not education:
            for line in self._clean_lines_from_text(source_text):
                if not re.match(r'^\d+\s*', line):
                    continue
                degree = self._extract_degree(line)
                year = self._extract_year(line)
                if not degree and not year:
                    continue

                degree_match = re.search(re.escape(degree), line, re.IGNORECASE) if degree else None
                year_match = re.search(r'\b(19\d{2}|20[0-3]\d)\b', line)
                specialization = None
                institution = None

                if degree_match and year_match and degree_match.end() < year_match.start():
                    mid = line[degree_match.end():year_match.start()].strip(' ,:-')
                    specialization = mid or None
                    tail = line[year_match.end():].strip(' ,:-')
                    institution = tail or None

                education.append({
                    "degree": degree,
                    "field": specialization,
                    "institution": institution,
                    "year": year,
                    "gpa": self._extract_gpa(line),
                })

        # --- STEP 4: Compact regex fallback ---
        if len(education) < 2:
            compact = re.sub(r'\s+', ' ', source_text.replace('\x07', ' ')).strip()
            # Strip table header row before applying compact regex
            compact = re.sub(
                r'(?i)(?:sl\.?\s*no\.?|s\.?\s*no\.?)\s+(?:degree|qualification)\s+\S[^0-9]{0,300}(?=\d+\s+(?:MBA|MCA|M\.?Tech|Bachelor|Master|PhD|B\.?E|B\.?Tech))',
                '',
                compact,
            ).strip()
            degree_pattern = re.compile(
                r"(?i)(MBA|M\.?Tech|MCA|PhD|Doctorate|Master\s+of\s+[A-Za-z ]+|Bachelor\s+of\s+[A-Za-z ]+|B\.?E\.?|B\.?Tech)"
                r"\s+(.+?)\s+(19\d{2}|20[0-3]\d)\s+(.+?)"
                r"(?=(?:\bMBA\b|\bMaster\s+of\b|\bBachelor\s+of\b|\bB\.?E\.?\b|\bB\.?Tech\b|\bM\.?Tech\b|\bMCA\b|\bPhD\b|\bDoctorate\b|$))"
            )
            for match in degree_pattern.finditer(compact):
                degree = match.group(1).strip()
                field = match.group(2).strip(' ,:-')
                year = match.group(3).strip()
                raw_tail = match.group(4).strip()
                # Remove trailing row-number artifact (e.g., "...Kozhikode 3.2 2")
                raw_tail = re.sub(r'\s+\d+\s*$', '', raw_tail).strip(' ,:-')
                grade, college, university = self._split_institution_grade(raw_tail)
                record = {
                    "degree": degree,
                    "field": field or None,
                    "institution": college or university or raw_tail or None,
                    "university": university or college or None,
                    "year": year,
                    "gpa": grade or self._extract_gpa(match.group(0)) or None,
                }
                dedupe_key = f"{record['degree']}|{record['year']}|{(record.get('institution') or '')}".lower()
                if not any(
                    f"{(e.get('degree') or '')}|{(e.get('year') or '')}|{(e.get('institution') or '')}".lower() == dedupe_key
                    for e in education
                ):
                    education.append(record)

        education = self._normalize_education_records(education)
        education.sort(key=self._education_sort_key)
        return education

    def _parse_labeled_education_entries(self, text: str) -> List[Dict[str, Any]]:
        """Parse education in alternating label format (Institution + Specialization)."""
        entries: List[Dict[str, Any]] = []
        lines = self._clean_lines_from_text(text)
        current_institution: Optional[str] = None

        for line in lines:
            inst_match = re.match(r'(?i)^institution\s*:\s*\|?\s*(.+)$', line)
            if inst_match:
                current_institution = inst_match.group(1).strip(' ,.;:-|')
                continue

            spec_match = re.match(r'(?i)^specialization\s*:\s*(.+)$', line)
            if not spec_match:
                continue

            specialization_text = spec_match.group(1).strip(' ,.;:-')
            degree = self._extract_degree(specialization_text)
            if not degree:
                if re.search(r'(?i)\b12th\s+standard\b|\bintermediate\b', specialization_text):
                    degree = "12th Standard"
                elif re.search(r'(?i)\b10th\s+standard\b|\bsecondary\b', specialization_text):
                    degree = "10th Standard"
                else:
                    degree = specialization_text

            year = self._extract_year(specialization_text)
            board = None
            board_match = re.search(r'(?i)\b(CBSE|ICSE|State\s+Board)\b', specialization_text)
            if board_match:
                board = board_match.group(1).upper()

            field = specialization_text
            if degree:
                field = re.sub(re.escape(degree), '', field, flags=re.IGNORECASE).strip(' ,.;:-()')

            if not current_institution and not specialization_text:
                continue

            entries.append(
                {
                    "degree": degree,
                    "field": field or None,
                    "institution": current_institution,
                    "university": board,
                    "board": board,
                    "year": year,
                    "gpa": self._extract_gpa(specialization_text),
                }
            )

        return entries

    def _parse_education_table_rows(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse education from NTT DATA style table flattened to plain text.
        Expected columns (after header strip):
          Sl.No | Degree | Branch | Year of Passing | College/Institute | University | Grade
        Rows are delimited by a leading row-number followed by a degree keyword.
        """
        # Used to find row boundaries — must not include trailing [A-Za-z ]* so the branch
        # stays separate from the core degree name.
        _DEGREE_BOUNDARY = (
            r"MBA|MCA|M\.?Tech|PhD|Doctorate"
            r"|Master\s+of\s+(?:Business|Science|Engineering|Arts|Technology|Computer|Management)"
            r"|Bachelor\s+of\s+(?:Engineering|Science|Technology|Arts|Commerce|Computer)"
            r"|B\.?E\.|B\.?Tech|B\.?Sc|B\.?Com"
        )
        # Flatten whitespace for uniform matching
        compact = re.sub(r'\s+', ' ', text.replace('\x07', ' ')).strip()
        compact = self._truncate_at_first_marker(
            compact,
            [
                "Domain Expertise",
                "Technical Expertise",
                "Experience Details",
                "Professional Experience",
                "Project Name",
                "Training Attended / Certifications Done",
                "Personal Details",
                "Declaration",
                "EMP ID",
            ],
        )
        # Strip table header row (everything up to first row-number + degree keyword)
        compact = re.sub(
            r'^.{0,400}?(?=\b\d+\s+(?:MBA|MCA|M\.?Tech|PhD|Doctorate|Bachelor|Master|B\.E|B\.Tech|B\.Sc))',
            '',
            compact,
            flags=re.IGNORECASE,
        ).strip()

        # Find row boundaries: positions where "{number} {degree_keyword}" starts
        boundary_re = re.compile(rf'\b(\d+)\s+({_DEGREE_BOUNDARY})', re.IGNORECASE)
        boundaries = [(m.start(), m.group(1), m.group(2)) for m in boundary_re.finditer(compact)]
        if not boundaries:
            return []

        results: List[Dict[str, Any]] = []
        for i, (start, row_num, _degree_token) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(compact)
            row_segment = compact[start:end].strip()
            # Remove leading row number
            row_segment = re.sub(rf'^\s*\d+\s+', '', row_segment).strip()

            # Find year as the divider between "degree branch" and "college university grade"
            year_match = re.search(r'\b((?:19|20)\d{2})\b', row_segment)
            if not year_match:
                continue
            year = year_match.group(1)
            before_year = row_segment[: year_match.start()].strip()
            after_year = row_segment[year_match.end() :].strip().strip(' ,:-')

            # before_year = "{degree} {branch}"
            # Use core (non-greedy) degree pattern so branch is NOT consumed
            deg_match = re.match(rf'(?i)({_DEGREE_BOUNDARY})\s*(.*)', before_year)
            if deg_match:
                degree = deg_match.group(1).strip()
                branch = deg_match.group(2).strip().strip(' ,:-')
            else:
                degree = self._extract_degree(before_year) or before_year.strip()
                branch = ''

            # after_year = "{college} {university} {grade}"
            grade, college, university = self._split_institution_grade(after_year)

            results.append({
                "degree": degree,
                "field": branch or None,
                "institution": college or university or None,
                "university": university or college or None,
                "year": year,
                "gpa": grade or None,
            })
        return results

    def _split_institution_grade(self, text: str) -> tuple:
        """
        Split a string of the form "{college} {university} {grade}" into three parts.
        Returns (grade, college_short_name, university_full_name).
        """
        if not text:
            return '', '', ''
        text = text.strip()
        # Remove common trailing labels that belong to other resume sections.
        text = re.sub(
            r'(?i)\b(?:emp\s*id|current\s*grade|project\s+name|projects?|domain\s+expertise|experience\s+details|technical\s+expertise|training\s+attended|personal\s+details)\b.*$',
            '',
            text,
        ).strip()
        text = re.sub(r'(?i)\bname\s*:\s*.*$', '', text).strip()

        # Extract trailing grade (number, optionally followed by % / CGPA / GPA)
        grade_match = re.search(r'(\d+(?:\.\d+)?\s*(?:CGPA|GPA|%)?)$', text, re.IGNORECASE)
        grade = ''
        if grade_match:
            grade = grade_match.group(1).strip()
            text = text[: grade_match.start()].strip()

        if not text:
            return grade, '', ''

        # Recognise a long institution name via keyword indicators
        long_name_indicators = [
            r'Indian\s+Institute',
            r'National\s+Institute',
            r'Jawaharlal',
            r'Visvesvaraya',
            r'University\s+of',
            r'Institute\s+of',
            r'College\s+of',
            r'\bUniversity\b',
            r'\bInstitute\b',
        ]
        for indicator in long_name_indicators:
            m = re.search(indicator, text, re.IGNORECASE)
            if m and m.start() > 0:
                college = text[: m.start()].strip().strip(' ,:-')
                university = text[m.start() :].strip()
                return grade, college, university

        # Fallback: if first token is a short all-caps abbreviation (2-6 chars), that's the college
        words = text.split()
        if words and re.match(r'^[A-Z]{2,6}$', words[0]):
            college = words[0]
            university = ' '.join(words[1:])
            return grade, college, university

        # Last resort: whole text is institution
        return grade, text, text
    
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
            r'\b(Bachelor\s+of\s+[A-Za-z ]+)\b',
            r'\b(Master\s+of\s+[A-Za-z ]+)\b',
            r'\b(B\.?E\.?|B\.?Tech|M\.?Tech|MBA|MCA|PhD|Doctorate|B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?)\b',
            r'\b(Bachelor\'?s?|Master\'?s?)\b',
        ]
        
        for pattern in degree_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
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
        """Extract institution name, skipping table header rows."""
        _HEADER_SKIP_PHRASES = (
            'sl. no', 'sl.no', 'year of passing', 'percentage', 'cgpa', 'grade',
            'name of the', 'branch', 'qualification details',
        )
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) <= 10:
                continue
            line_lower = line.lower()
            if any(phrase in line_lower for phrase in _HEADER_SKIP_PHRASES):
                continue
            if re.search(r'(?:University|College|Institute|School)', line, re.IGNORECASE):
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
    
    def _parse_skills(self, skills_text: str, full_text: str) -> Dict[str, Any]:
        """Parse skills/technical expertise section"""
        result: Dict[str, Any] = {
            "primarySkills": [],
            "technicalSkills": [],
            "toolsAndPlatforms": [],
            "operatingSystems": [],
            "databases": [],
            "domainExperience": [],
        }

        source_text = skills_text or self._slice_text_between_markers(
            full_text,
            "Technical Expertise",
            "Experience Details",
        )
        if not source_text:
            source_text = self._slice_text_between_any_markers(
                full_text,
                TECHNICAL_SECTION_ALIASES,
                ["experience details", "experience", "project details"] + PROJECT_SECTION_ALIASES,
            )
        if not source_text:
            return result

        normalized = re.sub(r'\s+', ' ', source_text.replace('\x07', ' ')).strip()
        labels = [
            ("Primary Skills", "primarySkills"),
            ("Operating Systems", "operatingSystems"),
            ("Languages", "technicalSkills"),
            ("Development Tools", "toolsAndPlatforms"),
            ("Middleware", "toolsAndPlatforms"),
            ("Scripts", "technicalSkills"),
            ("Databases", "databases"),
            ("Domain Knowledge", "domainExperience"),
            ("Foreign Language known", "technicalSkills"),
        ]

        keys_regex = "|".join(re.escape(label) for label, _ in labels)
        pattern = re.compile(rf'({keys_regex})\s*[:\-]?\s*(.+?)(?=(?:{keys_regex})\s*[:\-]?|$)', re.IGNORECASE)

        def split_items(text: str) -> List[str]:
            return [item.strip(' .:-') for item in re.split(r',|;|\|', text) if item.strip(' .:-')]

        for match in pattern.finditer(normalized):
            label_text = match.group(1).strip().lower()
            value_text = match.group(2).strip()
            target_key = next((target for label, target in labels if label.lower() == label_text), None)
            if not target_key:
                continue
            values = split_items(value_text)
            existing = result.setdefault(target_key, [])
            for value in values:
                if value and value not in existing:
                    existing.append(value)

        # Targeted extraction for labels that are often flattened on one line.
        def extract_between(start_label: str, end_label: str) -> List[str]:
            rx = re.compile(rf'{re.escape(start_label)}\s*[:\-]?\s*(.+?)(?={re.escape(end_label)}\s*[:\-]?|$)', re.IGNORECASE)
            m = rx.search(normalized)
            if not m:
                return []
            return split_items(m.group(1))

        if not result.get("databases"):
            result["databases"] = extract_between("Databases", "Configuration Tools")
        if not result.get("domainExperience"):
            result["domainExperience"] = extract_between("Domain Knowledge", "Testing Tools")
        if not result.get("toolsAndPlatforms"):
            result["toolsAndPlatforms"] = extract_between("Development Tools", "Middleware")

        trailing_label_pattern = re.compile(
            r'\b(?:Configuration\s+Tools|Domain\s+Knowledge|Testing\s+Tools|Documentation|Client\s*/\s*Server\s+Technologies|Foreign\s+Language\s+known)\b.*$',
            re.IGNORECASE,
        )

        def cleanup_values(values: List[str]) -> List[str]:
            cleaned = []
            for value in values or []:
                text = trailing_label_pattern.sub('', str(value or '')).strip(' ,.;:-')
                if text and text.lower() not in {"none", "na", "n/a"} and text not in cleaned:
                    cleaned.append(text)
            return cleaned

        result["primarySkills"] = cleanup_values(result.get("primarySkills", []))
        result["technicalSkills"] = cleanup_values(result.get("technicalSkills", []))
        result["toolsAndPlatforms"] = cleanup_values(result.get("toolsAndPlatforms", []))
        result["operatingSystems"] = cleanup_values(result.get("operatingSystems", []))
        result["databases"] = cleanup_values(result.get("databases", []))
        result["domainExperience"] = cleanup_values(result.get("domainExperience", []))

        # Keep domain list normalized.
        result["domainExperience"] = [item for item in result.get("domainExperience", []) if item and item.lower() not in {"none", "na", "n/a"}]

        # Fallback: many resumes keep skills in summary sentences instead of a structured skills section.
        if not result.get("technicalSkills") and not result.get("primarySkills"):
            inferred = self._extract_skills_from_summary_lines(full_text)
            if inferred:
                result["technicalSkills"] = inferred
                result["primarySkills"] = inferred[: min(6, len(inferred))]

        return result

    def _extract_skills_from_summary_lines(self, full_text: str) -> List[str]:
        lines = self._clean_lines_from_text(full_text)
        inferred: List[str] = []

        for line in lines[:80]:
            if re.search(r'(?i)^work\s+experience\b', line):
                break

            match = re.search(
                r'(?i)(?:technical\s+knowledge\s+on|expertise\s+in|skills?\s+in)\s+(.+)$',
                line,
            )
            if not match:
                continue

            payload = match.group(1)
            payload = re.split(r'(?i)\b(?:experienced|with\s+good\s+technical|and\s+application\s+deployment)\b', payload)[0]
            raw_items = re.split(r',|;|\||\s+&\s+|\s+and\s+', payload)
            for item in raw_items:
                skill = item.strip(' .,:;-')
                if len(skill) < 2:
                    continue
                if skill.lower() in {"i have", "good", "knowledge", "development"}:
                    continue
                if skill not in inferred:
                    inferred.append(skill)

        return inferred
    
    def _parse_certifications(self, cert_text: str, full_text: str) -> List[Dict[str, Any]]:
        """Parse certifications section"""
        certifications = []

        source_text = cert_text or self._slice_text_between_markers(
            full_text,
            "Training Attended / Certifications Done",
            "Qualification Details",
        )
        if not source_text:
            return certifications

        # Split by lines or common separators
        cert_lines = re.split(r'\n|;', source_text.replace('\x07', ' '))
        
        for line in cert_lines:
            line = re.sub(r'\s+', ' ', line.strip())
            # Clean up bullets
            line = re.sub(r'^[-•]\s*', '', line)

            if not line:
                continue
            if re.search(r'course\s+details|duration|training attended|certifications done', line, re.IGNORECASE):
                continue

            numbered_match = re.match(r'^(\d+)\s*[\.)-]?\s*(.+)$', line)
            if numbered_match:
                line = numbered_match.group(2).strip()

            # Remove trailing duration/date fragments while keeping cert name text.
            line = re.sub(r'\s+\d{1,2}[/-]\d{2}(?:\s*[-–]\s*\d{1,2}[/-]\d{2})?.*$', '', line).strip(' .,:;-')
            
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
                
                if not any(existing.get("name", "").lower() == cert["name"].lower() for existing in certifications):
                    certifications.append(cert)

        # Fallback for flattened one-line numbered certifications.
        if not certifications:
            compact = re.sub(r'\s+', ' ', source_text.replace('\x07', ' ')).strip()
            start = re.search(r'\b1\s*[\.)-]?\s+', compact)
            if start:
                compact = compact[start.start():]
                numbered = re.finditer(
                    r'(?:^|\s)(\d{1,2})\s*[\.)-]?\s*([A-Za-z][A-Za-z0-9\s()&./-]{2,}?)'
                    r'(?=(?:\s+\d{1,2}\s*[\.)-]?\s+[A-Za-z]|$))',
                    compact,
                )
                for item in numbered:
                    raw = item.group(2).strip()
                    raw = re.sub(r'\s+\d{1,2}/\d{2}(?:\s+\d{1,2}/\d{2})?\s*$', '', raw).strip(' .,:;-')
                    if not raw or len(raw) < 3:
                        continue
                    cert = {"name": raw, "issuer": None, "date": None}
                    issuer_match = re.search(r'\(([^)]+)\)|by\s+(\w+)', raw, re.IGNORECASE)
                    if issuer_match:
                        cert["issuer"] = issuer_match.group(1) or issuer_match.group(2)
                    if not any(existing.get("name", "").lower() == cert["name"].lower() for existing in certifications):
                        certifications.append(cert)

        # Cleanup: split accidentally merged entries like "SAFe Agilist 04/21 5.SAFe Agile practitioner".
        normalized_certs = []
        for cert in certifications:
            name = str(cert.get("name") or "").strip()
            if not name:
                continue

            chunks = re.split(r'\s+\d+\.\s*', name)
            if len(chunks) > 1:
                for chunk in chunks:
                    cleaned = re.sub(r'\s+\d{1,2}/\d{2}(?:\s+\d{1,2}/\d{2})?\s*$', '', chunk).strip(' .,:;-')
                    if cleaned and len(cleaned) >= 3:
                        normalized_certs.append({"name": cleaned, "issuer": cert.get("issuer"), "date": cert.get("date")})
            else:
                cleaned = re.sub(r'\s+\d{1,2}/\d{2}(?:\s+\d{1,2}/\d{2})?\s*$', '', name).strip(' .,:;-')
                if cleaned and len(cleaned) >= 3:
                    normalized_certs.append({"name": cleaned, "issuer": cert.get("issuer"), "date": cert.get("date")})

        deduped = []
        seen = set()
        for cert in normalized_certs:
            key = cert.get("name", "").lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(cert)

        # Remove header artifacts and restore obvious dropped cert names.
        deduped = [
            cert for cert in deduped
            if not re.fullmatch(r'(?i)(from\s*\(mm/yy\)|to\s*\(mm/yy\)|course\s*details|duration)', cert.get("name", "").strip())
        ]
        if not any((cert.get("name", "").strip().lower() == "pmp") for cert in deduped):
            if re.search(r'(?i)\b1\s*[\.)-]?\s*pmp\b', source_text):
                deduped.insert(0, {"name": "PMP", "issuer": None, "date": None})

        return deduped
    
    def _parse_projects(self, projects_text: str, full_text: str) -> List[Dict[str, Any]]:
        """Parse projects section"""
        projects = []

        source_text = projects_text or self._slice_text_between_markers(
            full_text,
            "Project Details",
            "Training Attended / Certifications Done",
        )
        if not source_text:
            source_text = full_text

        # Parse common line-based project formats first.
        lines = self._clean_lines_from_text(source_text)
        current_project: Optional[Dict[str, Any]] = None

        def finalize_project(project_obj: Optional[Dict[str, Any]]) -> None:
            if not project_obj:
                return
            name = str(project_obj.get("name") or "").strip()
            description = str(project_obj.get("description") or "").strip()
            if not name and not description:
                return
            projects.append(
                {
                    "name": name or "Project",
                    "description": description,
                    "technologies": project_obj.get("technologies", []),
                    "role": project_obj.get("role"),
                    "duration": project_obj.get("duration"),
                    "responsibilities": project_obj.get("responsibilities", []),
                }
            )

        for line in lines:
            start_match = re.match(r'(?i)^(?:project\s*name|project)\s*[:\-]\s*(.+)$', line)
            if start_match:
                finalize_project(current_project)
                value = start_match.group(1).strip()
                project_name = re.split(r'(?i)\brole\s*[:\-]|\bduration\s*[:\-]|\bkey\s+responsibilities\s*[:\-]|\bresponsibilities\s*[:\-]|\bclient\s*[:\-]', value)[0].strip(' ,.;:|-')
                current_project = {
                    "name": project_name,
                    "description": "",
                    "technologies": [],
                    "role": self._extract_project_inline_field(value, r'(?i)\brole\s*[:\-]\s*([^|]+)'),
                    "duration": self._extract_project_inline_field(value, r'(?i)\bduration\s*[:\-]\s*([^|]+)'),
                    "responsibilities": self._split_responsibility_text(
                        self._extract_project_inline_field(
                            value,
                            r'(?i)\b(?:key\s+responsibilities|responsibilities)\s*[:\-]\s*(.+)$',
                        )
                    ),
                }
                continue

            if current_project is None:
                continue

            role_match = re.match(r'(?i)^role\s*[:\-]\s*(.+)$', line)
            if role_match:
                current_project["role"] = role_match.group(1).strip(' ,.;:-')
                continue

            duration_match = re.match(r'(?i)^duration\s*[:\-]\s*(.+)$', line)
            if duration_match:
                current_project["duration"] = duration_match.group(1).strip(' ,.;:-')
                continue

            tech_match = re.match(r'(?i)^(?:technologies|environment|tools\s+used)\s*[:\-]\s*(.+)$', line)
            if tech_match:
                tech_values = [item.strip(' .,:;-') for item in re.split(r',|\|', tech_match.group(1)) if item.strip(' .,:;-')]
                current_project["technologies"] = list(dict.fromkeys((current_project.get("technologies") or []) + tech_values))
                continue

            resp_match = re.match(r'(?i)^(?:key\s+responsibilities|responsibilities)\s*[:\-]\s*(.+)$', line)
            if resp_match:
                current_project["responsibilities"] = self._split_responsibility_text(resp_match.group(1))
                continue

            if line.startswith("-") or line.startswith("*") or line.startswith("•"):
                bullet_text = line.lstrip("-*• ").strip()
                if bullet_text:
                    current_project.setdefault("responsibilities", []).append(bullet_text)
                continue

            if len(line) > 20:
                existing_description = current_project.get("description", "")
                current_project["description"] = f"{existing_description} {line}".strip() if existing_description else line

        finalize_project(current_project)

        normalized = self._normalize_text(source_text).replace('\x07', ' ')
        compact = re.sub(r'\s+', ' ', normalized)

        if not projects:
            projects = self._parse_numbered_project_blocks(source_text)
        if not projects and source_text is not full_text:
            projects = self._parse_numbered_project_blocks(full_text)

        if not projects:
            block_pattern = re.compile(
                r'Project\s*Name\s*[:\-]?\s*(.+?)(?=(?:\s+Project\s*Name\s*[:\-]?|\s+Projects\s+Managed\s+prior\s+to\s+joining|\s+Training\s+Attended|\s+Qualification\s+Details|$))',
                re.IGNORECASE | re.DOTALL,
            )

            for match in block_pattern.finditer(compact):
                block = match.group(1).strip()
                if not block:
                    continue

                date_text = ""
                description_text = block
                date_match = re.search(r'\bDate\s*[:\-]?\s*([^\n]+)$', block, re.IGNORECASE)
                if date_match:
                    date_text = date_match.group(1).strip()
                    description_text = block[:date_match.start()].strip()

                name_match = re.match(
                    r'(.+?)(?=\s+(?:I\s+|Program\s+managed|Managed\s+|Worked\s+|Led\s+|Coordinated\s+|Delivered\s+))',
                    description_text,
                    re.IGNORECASE,
                )
                if name_match:
                    project_name = name_match.group(1).strip(' .:-')
                    description = description_text[name_match.end():].strip(' .:-')
                else:
                    project_name = description_text[:120].strip(' .:-')
                    description = description_text[120:].strip(' .:-') if len(description_text) > 120 else ""

                projects.append({
                    "name": project_name,
                    "description": description,
                    "technologies": [],
                    "role": None,
                    "duration": date_text,
                })

        # Fallback from summary bullets when explicit Project Name blocks are absent.
        if not projects:
            lines = self._clean_lines_from_text(full_text)
            start_idx = next((i for i, ln in enumerate(lines) if 'projects that i have managed' in ln.lower()), None)
            if start_idx is not None:
                for ln in lines[start_idx + 1:start_idx + 10]:
                    if len(ln) < 30:
                        continue
                    if re.search(r'technical expertise|training attended|qualification details', ln, re.IGNORECASE):
                        break
                    projects.append({
                        "name": "Managed Project",
                        "description": ln,
                        "technologies": [],
                        "role": None,
                    })

        # Deduplicate repeated project blocks while keeping the richer entry.
        deduped_by_key: Dict[str, Dict[str, Any]] = {}
        for project in projects:
            name = str(project.get("name") or "").strip()
            duration = str(project.get("duration") or "").strip()
            key = f"{name.lower()}|{duration.lower()}"
            if not key.strip("|"):
                continue

            existing = deduped_by_key.get(key)
            if not existing:
                deduped_by_key[key] = project
                continue

            existing_score = len(str(existing.get("description") or "")) + len(existing.get("responsibilities") or []) * 10
            current_score = len(str(project.get("description") or "")) + len(project.get("responsibilities") or []) * 10
            if current_score > existing_score:
                deduped_by_key[key] = project

        projects = list(deduped_by_key.values())
        
        return projects

    def _parse_numbered_project_blocks(self, text: str) -> List[Dict[str, Any]]:
        """Parse projects listed as numbered headings with optional tenure in parentheses."""
        lines = self._clean_lines_from_text(text)
        projects: List[Dict[str, Any]] = []

        current: Optional[Dict[str, Any]] = None
        current_desc: List[str] = []
        current_resp: List[str] = []
        in_responsibilities = False

        def flush_current() -> None:
            nonlocal current, current_desc, current_resp, in_responsibilities
            if not current:
                return

            project_name = str(current.get("name") or "").strip(' ,.;:-')
            if not project_name:
                current = None
                current_desc = []
                current_resp = []
                in_responsibilities = False
                return

            projects.append(
                {
                    "name": project_name,
                    "description": " ".join(current_desc).strip(),
                    "technologies": [],
                    "role": None,
                    "duration": current.get("duration"),
                    "responsibilities": current_resp,
                }
            )

            current = None
            current_desc = []
            current_resp = []
            in_responsibilities = False

        for line in lines:
            title_match = re.match(r'^\s*(\d+)\)\s*(.+)$', line)
            if title_match:
                flush_current()
                title_payload = title_match.group(2).strip()
                duration = None
                tenure_match = re.search(r'(?i)\(\s*tenure\s+([^)]+)\)', title_payload)
                if tenure_match:
                    duration = tenure_match.group(1).strip(' ,.;:-')

                project_name = re.sub(r'(?i)\(\s*tenure\s+[^)]*\)', '', title_payload).strip(' ,.;:-')
                current = {"name": project_name, "duration": duration}
                continue

            if current is None:
                continue

            if re.match(r'(?i)^primary\s+responsibilities\s*:?\s*$', line):
                in_responsibilities = True
                continue

            if re.match(r'(?i)^education\b|^certification\b|^qualification\b|^declaration\b', line):
                flush_current()
                break

            if in_responsibilities:
                if line:
                    current_resp.append(line.strip(' -•*'))
                continue

            if line and len(line) > 15:
                current_desc.append(line)

        flush_current()
        return projects

    def _extract_project_inline_field(self, text: str, pattern: str) -> Optional[str]:
        match = re.search(pattern, text)
        if not match:
            return None
        return match.group(1).strip(' ,.;:-')

    def _split_responsibility_text(self, text: Optional[str]) -> List[str]:
        if not text:
            return []
        parts = [item.strip(' .,:;-') for item in re.split(r'\s*[•\-]\s*|\.|;', str(text)) if item.strip(' .,:;-')]
        return parts

    def _slice_text_between_markers(self, text: str, start_marker: str, end_marker: str) -> str:
        source = self._normalize_text(text or "")
        start_match = re.search(re.escape(start_marker), source, re.IGNORECASE)
        if not start_match:
            return ""
        remainder = source[start_match.end():]
        if not end_marker:
            return remainder
        end_match = re.search(re.escape(end_marker), remainder, re.IGNORECASE)
        return remainder[:end_match.start()] if end_match else remainder

    def _slice_text_between_any_markers(self, text: str, start_markers: List[str], end_markers: List[str]) -> str:
        source = self._normalize_text(text or "")
        if not source:
            return ""

        start_index = None
        for marker in start_markers or []:
            marker_text = str(marker or '').strip()
            if not marker_text:
                continue
            match = re.search(re.escape(marker_text), source, re.IGNORECASE)
            if match and (start_index is None or match.start() < start_index):
                start_index = match.end()

        if start_index is None:
            return ""

        remainder = source[start_index:]
        end_index = None
        for marker in end_markers or []:
            marker_text = str(marker or '').strip()
            if not marker_text:
                continue
            match = re.search(re.escape(marker_text), remainder, re.IGNORECASE)
            if match and (end_index is None or match.start() < end_index):
                end_index = match.start()

        if end_index is None:
            return remainder.strip()
        return remainder[:end_index].strip()

    def _truncate_at_first_marker(self, text: str, markers: List[str]) -> str:
        """Return text up to the first occurrence of any marker (case-insensitive)."""
        source = text or ""
        if not source or not markers:
            return source

        first_index: Optional[int] = None
        for marker in markers:
            if not marker:
                continue
            match = re.search(re.escape(marker), source, re.IGNORECASE)
            if not match:
                continue
            if first_index is None or match.start() < first_index:
                first_index = match.start()

        if first_index is None:
            return source
        return source[:first_index].strip()

    def _clean_lines_from_text(self, text: str) -> List[str]:
        normalized = self._normalize_text(text or "").replace('\x07', ' ')
        return [re.sub(r'\s+', ' ', line).strip() for line in normalized.split('\n') if line.strip()]

    def _normalize_education_records(self, education: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not education:
            return []

        # Preserve all education records; only remove exact duplicates.
        normalized: List[Dict[str, Any]] = []
        seen = set()
        for record in education:
            institution = str(record.get("institution") or record.get("university") or "")
            institution = re.sub(r'(?i)^institution\s*:\s*\|?\s*', '', institution).strip(' ,.;:-|')
            record["institution"] = institution or record.get("institution")

            degree = str(record.get("degree") or "").strip().lower()
            field = str(record.get("field") or record.get("specialization") or "").strip().lower()
            institution = str(record.get("institution") or record.get("university") or "").strip().lower()
            year = str(record.get("year") or record.get("yearOfPassing") or "").strip().lower()
            key = f"{degree}|{field}|{institution}|{year}"
            if key in seen:
                continue
            seen.add(key)
            normalized.append(record)

        return normalized

    def _education_sort_key(self, edu: Dict[str, Any]) -> Any:
        degree_text = str(edu.get("degree") or "").lower()
        if any(token in degree_text for token in ["phd", "doctorate"]):
            rank = 0
        elif any(token in degree_text for token in ["master", "mba", "m.tech", "mtech", "mca", "m.s", "ms"]):
            rank = 1
        elif any(token in degree_text for token in ["bachelor", "b.e", "be", "b.tech", "btech", "b.s", "bs"]):
            rank = 2
        else:
            rank = 3

        year_text = str(edu.get("year") or "")
        year_match = re.search(r'(19\d{2}|20[0-3]\d)', year_text)
        year_num = int(year_match.group(1)) if year_match else 0
        return (rank, -year_num)
    
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
