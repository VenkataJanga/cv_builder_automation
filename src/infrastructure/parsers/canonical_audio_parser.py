"""
Canonical Audio Parser for Voice Transcripts
Parses audio transcripts directly into Canonical CV Schema v1.1
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.infrastructure.parsers.enhanced_transcript_parser import EnhancedTranscriptParser


class CanonicalAudioParser:
    """
    Parser that outputs Canonical CV Schema v1.1 from audio transcripts
    Handles both structured enhanced transcripts and natural language voice inputs
    """
    
    def __init__(self):
        self.schema_version = "1.1.0"
        self.enhanced_transcript_parser = EnhancedTranscriptParser()
        self._invalid_project_names = {
            "operating",
            "operating system",
            "operating systems",
            "current role",
            "project experience",
            "responsibilities",
            "education",
            "skills",
            "summary",
        }
    
    def parse(self, enhanced_transcript: str, session_id: Optional[str] = None, audio_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parse enhanced transcript into Canonical CV Schema v1.1
        
        Args:
            enhanced_transcript: Audio transcript text
            session_id: Optional session ID
            audio_metadata: Optional audio file metadata
            
        Returns:
            Dict following Canonical CV Schema v1.1
            
        Raises:
            ValueError: If transcript is empty or None
        """
        if not enhanced_transcript or not enhanced_transcript.strip():
            # Return minimal valid structure for empty transcript
            return self._create_empty_canonical()
        
        parser_text = self._normalize_parser_text(enhanced_transcript)

        personal_info = self._extract_personal_info(parser_text)
        years_exp = self._extract_years_of_experience(parser_text)
        experience = self._extract_experience_canonical(parser_text)
        education = self._deduplicate_education_entries(self._extract_education_canonical(parser_text))

        supplemental_experience = self._extract_structured_projects(enhanced_transcript)
        if self._score_projects(supplemental_experience) > self._score_projects(experience.get("projects", [])):
            experience["projects"] = supplemental_experience

        supplemental_education = self._deduplicate_education_entries(self._extract_structured_education(enhanced_transcript))
        if len(supplemental_education) >= 2 and self._has_low_quality_education_entries(education):
            education = supplemental_education
        elif len(supplemental_education) >= 2 and self._score_education(supplemental_education) >= self._score_education(education):
            education = supplemental_education
        elif self._score_education(supplemental_education) > self._score_education(education):
            education = supplemental_education
        
        canonical_cv = {
            "candidate": {
                "fullName": personal_info.get("fullName"),
                "email": personal_info.get("email"),
                "phoneNumber": personal_info.get("phone"),
                "portalId": personal_info.get("portalId"),
                "currentOrganization": self._extract_organization(parser_text),
                "currentDesignation": self._extract_current_role(parser_text),
                "totalExperienceYears": years_exp,
                "totalExperienceMonths": 0,
                "summary": self._extract_professional_summary(parser_text) or "",
                "currentLocation": personal_info.get("location", {})
            },
            "skills": self._extract_skills_canonical(parser_text),
            "experience": experience,
            "education": education,
            "certifications": self._extract_certifications_canonical(parser_text),
            "personalDetails": {
                "languagesKnown": self._extract_languages(parser_text),
                "dateOfBirth": None,
                "nationality": None,
                "maritalStatus": None
            },
            "metadata": {
                "schemaVersion": "1.1",
                "sources": ["audio_upload"],
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
                "audioMetadata": audio_metadata
            }
        }
        
        return canonical_cv

    def _normalize_parser_text(self, text: str) -> str:
        """Normalize enhanced transcript formatting back into parser-friendly plain text."""
        normalized = text or ""
        normalized = normalized.replace("\r\n", "\n")
        normalized = re.sub(r'\*\*([^*]+)\*\*', r'\1', normalized)
        normalized = re.sub(r'(?m)^\s*#+\s*', '', normalized)
        normalized = re.sub(r'(?m)^\s*[-*]\s+', '- ', normalized)
        normalized = re.sub(r'\u2013|\u2014', '-', normalized)
        normalized = re.sub(r'\n{3,}', '\n\n', normalized)
        return normalized

    def _extract_structured_projects(self, text: str) -> List[Dict[str, Any]]:
        """Use the enhanced transcript parser when the LLM returns structured markdown-like content."""
        if "**" not in text and "(Client:" not in text and "Responsibilities:" not in text:
            return []

        try:
            parsed = self.enhanced_transcript_parser.parse(text)
        except Exception:
            return []

        projects = []
        for project in parsed.get("project_experience", []) or []:
            project_name = self._clean_markup(project.get("project_name", ""))
            if not project_name:
                continue

            description = self._clean_markup(project.get("project_description", ""))
            responsibilities = [
                self._clean_markup(resp) for resp in (project.get("responsibilities") or []) if self._clean_markup(resp)
            ]
            technologies = [
                self._clean_markup(tech) for tech in (project.get("technologies_used") or []) if self._clean_markup(tech)
            ]

            projects.append({
                "projectName": project_name,
                "clientName": self._clean_markup(project.get("client", "")) or None,
                "client": self._clean_markup(project.get("client", "")) or None,
                "role": self._clean_markup(project.get("role", "")) or None,
                "projectDescription": description,
                "description": description,
                "startDate": None,
                "endDate": None,
                "durationMonths": None,
                "toolsUsed": technologies,
                "technologies": technologies,
                "environment": technologies,
                "teamSize": None,
                "responsibilities": responsibilities,
                "outcomes": [],
                "achievements": []
            })

        return projects

    def _extract_structured_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract education from structured enhanced transcripts and map to preview-compatible canonical keys."""
        if "**Education" not in text and "Education:" not in text and "education" not in text.lower():
            return []

        structured_section = re.search(r'(?is)\*\*Education\*\*\s*(.*?)(?=\n\*\*|\Z)', text)
        if structured_section:
            lines = []
            for line in structured_section.group(1).splitlines():
                stripped = line.strip()
                if stripped.startswith('-') and len(stripped) > 5:
                    lines.append(stripped[1:].strip())

            parsed_lines = []
            for line in lines:
                parts = [part.strip() for part in line.split(',') if part.strip()]
                if len(parts) < 4:
                    continue

                degree = self._clean_markup(parts[0])
                specialization_token = self._clean_markup(parts[1]) if len(parts) > 1 else ""
                institution_index = 1
                university_index = 2
                specialization = "General"

                if re.fullmatch(r'(computers?|mpc|general)', specialization_token, re.IGNORECASE):
                    specialization = specialization_token
                    institution_index = 2
                    university_index = 3

                institution = self._clean_markup(parts[institution_index]) if len(parts) > institution_index else ""
                university = self._clean_markup(parts[university_index]) if len(parts) > university_index else ""
                university = re.sub(r'\s*\(?\d{4}(?:\s*-\s*\d{4})?\)?\s*$', '', university).strip(' ,')
                year_matches = re.findall(r'(19\d{2}|20[0-3]\d)', line)
                year = year_matches[-1] if year_matches else None
                score_text = self._clean_markup(parts[-1])

                percentage = None
                grade = None
                if re.search(r'gpa', score_text, re.IGNORECASE):
                    grade = score_text
                elif re.match(r'^\d+(?:\.\d+)?%?$', score_text):
                    numeric_score = score_text.rstrip('%')
                    if '.' in numeric_score and float(numeric_score) <= 10:
                        grade = f"{numeric_score} GPA"
                    else:
                        percentage = f"{numeric_score}%"

                if specialization == "General" and 'computer' in degree.lower():
                    specialization = "Computers"
                elif specialization == "General" and 'mpc' in degree.lower():
                    specialization = "MPC"

                parsed_lines.append({
                    "degree": degree,
                    "specialization": specialization,
                    "field": specialization,
                    "institution": institution,
                    "university": university,
                    "yearOfPassing": year,
                    "graduationYear": year,
                    "percentage": percentage,
                    "grade": grade,
                    "gpa": grade or percentage
                })

            if parsed_lines:
                return parsed_lines

        try:
            parsed = self.enhanced_transcript_parser.parse(text)
        except Exception:
            return []

        education_entries = []
        for edu in parsed.get("education", []) or []:
            degree = self._clean_markup(edu.get("qualification", "") or edu.get("degree", ""))
            institution = self._clean_markup(edu.get("college", "") or edu.get("institution", ""))
            university = self._clean_markup(edu.get("university", ""))
            specialization = self._clean_markup(edu.get("specialization", "")) or None
            year = str(edu.get("year_of_passing", "") or edu.get("year", "")).strip() or None
            percentage = self._clean_markup(edu.get("percentage", "")) or None

            if not (degree or institution or university):
                continue

            education_entries.append({
                "degree": degree,
                "specialization": specialization,
                "field": specialization,
                "institution": institution,
                "university": university,
                "yearOfPassing": year,
                "graduationYear": year,
                "percentage": percentage if percentage and percentage.endswith('%') else None,
                "grade": percentage if percentage and not percentage.endswith('%') else None,
                "gpa": percentage
            })

        return education_entries

    def _deduplicate_education_entries(self, education: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove low-quality duplicate education entries while preserving richer records."""
        deduplicated: Dict[str, Dict[str, Any]] = {}

        for entry in education or []:
            degree = (entry.get("degree") or "").strip().lower()
            institution = (entry.get("institution") or entry.get("university") or "").strip().lower()
            year = str(entry.get("yearOfPassing") or entry.get("graduationYear") or "").strip()

            key = "|".join([degree, institution, year])
            if not key.strip("|"):
                continue

            current = deduplicated.get(key)
            if current is None or self._score_education([entry]) > self._score_education([current]):
                deduplicated[key] = entry

        return list(deduplicated.values())

    def _has_low_quality_education_entries(self, education: List[Dict[str, Any]]) -> bool:
        for entry in education or []:
            if not entry.get("institution"):
                return True
            if not (entry.get("yearOfPassing") or entry.get("graduationYear")):
                return True
        return False

    def _score_projects(self, projects: List[Dict[str, Any]]) -> int:
        score = 0
        for project in projects or []:
            score += 5 if project.get("projectName") else 0
            score += 3 if project.get("projectDescription") or project.get("description") else 0
            score += len(project.get("responsibilities") or [])
            score += min(len(project.get("toolsUsed") or project.get("technologies") or []), 5)
        return score

    def _score_education(self, education: List[Dict[str, Any]]) -> int:
        score = 0
        for edu in education or []:
            score += 4 if edu.get("degree") else 0
            score += 3 if edu.get("institution") else 0
            score -= 2 if not edu.get("institution") else 0
            score += 2 if edu.get("yearOfPassing") or edu.get("graduationYear") else 0
            score += 1 if edu.get("percentage") or edu.get("grade") or edu.get("gpa") else 0
        return score

    def _clean_markup(self, value: Optional[str]) -> str:
        if not value:
            return ""
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', value)
        cleaned = re.sub(r'(?m)^\s*[-*]\s*', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip(" .*")
    
    def parse_transcript_to_canonical(self, transcript: str, session_id: Optional[str] = None, audio_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Alias for parse() method to maintain compatibility
        """
        return self.parse(transcript, session_id, audio_metadata)
    
    def _create_empty_canonical(self) -> Dict[str, Any]:
        """Create minimal valid canonical structure for empty/failed transcripts"""
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
                "currentLocation": {}
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
                "schemaVersion": "1.1",
                "sources": ["audio_upload"],
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "lastUpdated": datetime.now(timezone.utc).isoformat()
            }
        }
    
    def _create_metadata(self) -> Dict[str, Any]:
        """Create metadata section"""
        return {
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "lastModifiedAt": datetime.now(timezone.utc).isoformat(),
            "completenessScore": 0.0,  # Will be calculated by validation service
            "dataQuality": {
                "overall": "incomplete"
            }
        }
    
    def _extract_personal_info(self, text: str) -> Dict[str, Any]:
        """Extract personal information including portal ID"""
        personal_info = {
            "fullName": None,
            "email": None,
            "phone": None,
            "portalId": None,
            "location": {
                "city": None,
                "state": None,
                "country": None
            }
        }
        
        # Clean text first
        cleaned_text = re.sub(r'\b(uhh?|umm?|like|you\s+know|yeah)\b[.,\s]*', ' ', text, flags=re.IGNORECASE)
        
        # Extract full name - more flexible patterns (case-insensitive)
        name_patterns = [
            r'(?:my\s+name\s+is[.,\s]*(?:uh\s+)?|I\'m|I\s+am)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})(?=\s+and\s+(?:portal|employee|email|contact)|[\.,\n]|$)',
            r'\*\*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\*\*',
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})',  # Name at start of text
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                # Additional cleanup
                name = ' '.join(name.split())  # Normalize whitespace
                name = re.sub(r'\s+(?:Portal|Employee)\s+ID.*$', '', name, flags=re.IGNORECASE).strip()
                # Strip trailing field labels accidentally captured in compact transcripts.
                name = re.sub(r'\s+(?:Email|Contact|Phone|Mobile|Location|Role|Current)\b.*$', '', name, flags=re.IGNORECASE).strip()
                # Remove any remaining filler words
                name = re.sub(r'\b(uh|um|yeah)\b', '', name, flags=re.IGNORECASE).strip()
                name = ' '.join(name.split())  # Clean again
                if len(name.split()) >= 2:
                    personal_info["fullName"] = name
                    break
        
        # Extract portal/employee ID
        portal_id_patterns = [
            r'(?:portal\s+id\s+is|employee\s+id\s+is|id\s+is)\s*[:\s]*(\d{5,})',
            r'(?:portal\s+id|employee\s+id)[:\s]+(\d{5,})',
        ]
        
        for pattern in portal_id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                personal_info["portalId"] = match.group(1).strip()
                break
        
        # Extract email
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        email_match = re.search(email_pattern, text)
        if email_match:
            personal_info["email"] = email_match.group(0)
        else:
            personal_info["email"] = self._extract_spoken_email(text)
        
        # Extract phone
        phone_pattern = r'\+?[\d\s\-\(\)]{10,}'
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            phone = phone_match.group(0).strip()
            if len(re.sub(r'\D', '', phone)) >= 10:
                personal_info["phone"] = phone
        
        # Extract location - limit search to beginning of text BEFORE domain expertise section
        # This prevents grabbing domain names as locations
        domain_section_start = text.lower().find('domain expertise')
        search_text = text[:domain_section_start] if domain_section_start > 0 else text
        
        location_patterns = [
            # Supports "Location: Bangalore, India" while still handling city-only formats.
            r'(?:current\s+location|location)\s*[:\-][ \t]*([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)?(?:\s*,\s*[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+)?)?)',
            r'(?:based\s+in|living\s+in|from|located\s+in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)?)',
            r'(?:at\s+\w+(?:\s+\w+)?,\s+)([A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+)?)',  # "at Organization, City[, Country]"
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                location = location.splitlines()[0].strip()
                # Verify it looks like a real location (not a skill, domain, or random word)
                excluded_words = r'\b(java|python|spring|experience|years|data|system|healthcare|financial|services|insurance|retail|banking)\b'
                if not re.search(excluded_words, location, re.IGNORECASE):
                    parts = [p.strip() for p in location.split(",") if p.strip()]
                    if len(parts) >= 2:
                        personal_info["location"]["city"] = parts[0]
                        personal_info["location"]["country"] = parts[-1]
                    else:
                        personal_info["location"]["city"] = location
                    personal_info["location"]["fullAddress"] = location
                    break
        
        return personal_info
    
    # Patterns that mark the END of the professional summary block
    _SUMMARY_STOP_PATTERN = (
        r'(?=\n\s*(?:'
        r'Primary\s+Skills?|Secondary\s+Skills?|Additional\s+Skills?|'
        r'Core\s+Competencies|Skills?|Technologies|AI\s+(?:Tools|Frameworks)|'
        r'Operating\s+Systems?|Database[s\s]|Industry\s+Experience|'
        r'Domain\s+Expertise|Experience|Education|Certifications?|Projects?'
        r')[:\s\-]|$)'
    )

    # Education-line sniffer — used to filter responsibility lines
    _EDU_LINE_RE = re.compile(
        r'^(?:'
        r'master|bachelor|b\.?tech|m\.?tech|b\.?e\b|m\.?e\b|bsc|msc|b\.?sc|m\.?sc|'
        r'mca|bca|intermediate|secondary\s+school|10th|12th|ssc|hsc|'
        r'diploma|ph\.?d|doctorate|degree'
        r')',
        re.IGNORECASE,
    )

    # Stop marker for responsibility extraction
    _RESP_STOP = (
        r'(?=\s*(?:\d+\.\s+[A-Z]|Technologies?[:\s]|Skills?[:\s]|Client[:\s]|'
        r'Education[:\s]|\*\*Education|Certifications?[:\s]|'
        r'My\s+(?:second|third|next)\s+project|$))'
    )

    def _is_education_line(self, line: str) -> bool:
        """Return True if a line looks like an education entry rather than a responsibility."""
        stripped = line.strip().lstrip('-•* ').strip()
        if self._EDU_LINE_RE.match(stripped):
            return True
        # Pattern: contains institution keywords AND a year AND a grade/percentage
        if re.search(r'(?:university|college|institute|board|school)', stripped, re.IGNORECASE):
            if re.search(r'\b(?:19|20)\d{2}\b', stripped) and re.search(
                r'\d+\s*%|\d+\.\d+\s*gpa|\d+\s*cgpa', stripped, re.IGNORECASE
            ):
                return True
        return False

    def _extract_professional_summary(self, text: str) -> Optional[str]:
        """Extract professional summary — stops before skills / competencies sections."""
        stop = self._SUMMARY_STOP_PATTERN
        summary_patterns = [
            r'(?:professional\s+summary|about\s+me)[:\-\s]+(.+?)' + stop,
        ]

        for pattern in summary_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                summary = match.group(1).strip()
                # Strip trailing skill/competency lines that crept in
                summary = re.sub(
                    r'(?is)\s*(?:core\s+competencies|primary\s+skills?|secondary\s+skills?|'
                    r'AI\s+frameworks?|operating\s+systems?|database\s+management|'
                    r'industry\s+experience|domain\s+expertise)[:\-].*$',
                    '',
                    summary,
                ).strip()
                summary = re.sub(r'\n\s*\n', '\n\n', summary)
                summary = re.sub(r'[ \t]+', ' ', summary)
                if len(summary) > 20:
                    return summary

        # Fallback: infer a short summary from candidate profile and introduction text
        return self._extract_summary_from_lead_paragraph(text)
    
    def _extract_current_role(self, text: str) -> Optional[str]:
        """Extract current role/title - handles 'Role at Organization' pattern"""
        role_patterns = [
            r'(?:currently\s+serving\s+as\s+(?:a\s+)?)\s*([^,\.\n]{5,60})(?=\s+at|\.|,|$)',
            r'(?:Current\s+Role[:\s]+)([^,\n]+?)(?:\s+at\s+)',
            r'(?:working\s+at\s+\w+\s+as\s+a?)\s+([^,\.\n]{5,60})',
            r'(?:I\'m\s+a|I\s+am\s+a|currently\s+working\s+as\s+a?)\s+([^,\.\n]{5,60})',
            r'((?:[A-Z][a-z]+\s+){0,3}(?:System\s+)?(?:Senior|Junior|Lead|Principal|Staff|Chief|Head)?\s*(?:Software\s+)?(?:Developer|Engineer|Architect|Consultant|Advisor|Analyst|Manager|Specialist|Director|Strategist))',
            r'(?:as\s+a?)\s+([A-Z][A-Za-z\s]{5,60}?)(?=\s+at|\s+for|\.|,|$)',
        ]
        
        for pattern in role_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                role = self._sanitize_current_role(match.group(1))
                # Remove trailing "at" or other prepositions
                role = re.sub(r'\s+(at|in|for)$', '', role, flags=re.IGNORECASE)
                if len(role) > 3:
                    return role
        
        return None

    def _sanitize_current_role(self, role: Optional[str]) -> str:
        """Normalize designation text and strip leaked section headers."""
        cleaned = str(role or "")
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = re.sub(r'^(?:experience|current\s+role|role)\s*[:\-]?\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ,.;:-')

        if cleaned.lower() in {
            "experience",
            "current role",
            "role",
            "project experience",
            "responsibilities",
            "education",
            "skills",
            "summary",
        }:
            return ""

        return cleaned

    def _extract_domain_expertise(self, text: str) -> List[str]:
        """Extract domain/industry expertise from transcript sections."""
        # Patterns that handle labeled markdown sections and conversational phrasing.
        domain_patterns = [
            # Pattern 1: "**Domain Expertise**\nHealthcare, Banking" and "Domain Expertise: ..."
            r'(?:\*\*)?domain\s+expertise(?:\*\*)?\s*[:\-]?\s*(?:\n\s*)?([^\n\*]+)',
            # Pattern 2: "Domains worked in: Healthcare, Banking"
            r'domains?\s+(?:worked\s+in|include|are)\s*[:\-]?\s*([^\n\*]+)',
            # Pattern 3: Conversational "its having healthcare, insurance, banking"
            r'(?:as\s+per\s+my\s+profile[\s,]*)?(?:it(?:\'s|\s+is)?\s+having|its\s+having|having)\s+([^\n\*]+)',
        ]

        extracted: List[str] = []
        for pattern in domain_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if not match:
                continue

            raw_domains = re.sub(r'\s+', ' ', match.group(1)).strip(' .;:-*')
            if not raw_domains:
                continue
                
            # Normalize conjunctions into delimiters for split
            raw_domains = re.sub(r'\s+(?:and|&)\s+', ',', raw_domains, flags=re.IGNORECASE)

            for token in re.split(r'[,;/|]', raw_domains):
                item = token.strip(' .;:-*')
                # Remove trailing filler words
                item = re.sub(r'\b(?:etc|etc\.|et\s+cetera)\b\s*$', '', item, flags=re.IGNORECASE).strip(' .;:-')
                if len(item) < 3:
                    continue
                # Filter out common section keywords or heading remnants.
                if re.search(r'\b(project|education|certification|responsibilities|skills?|primary|secondary|domain\s+expertise|domain|domains)\b', item, re.IGNORECASE):
                    continue
                normalized = item.title()
                if normalized not in extracted:
                    extracted.append(normalized)

            if extracted:
                break

        return extracted

    def _extract_summary_from_lead_paragraph(self, text: str) -> Optional[str]:
        """Infer a summary from the opening sentences if no explicit summary section exists."""
        # Look for the first meaningful sentence excluding contact info and ID statements.
        sentences = re.split(r'(?<=[\.\!\?])\s+', text)
        for sentence in sentences:
            cleaned = sentence.strip()
            if len(cleaned) < 40:
                continue
            if re.search(r'\b(portal\s+id|employee\s+id|email\s+address|contact\s+number|phone\s+number|my\s+name\s+is|I\s+can\s+reach|grade\s+is)\b', cleaned, re.IGNORECASE):
                continue
            if re.search(r'\b(I\s+am|I\'m|my\s+name|portal\s+id|email\s+address|contact\s+number)\b', cleaned, re.IGNORECASE):
                continue
            cleaned = re.sub(r'\s+', ' ', cleaned)
            if len(cleaned) > 20:
                return cleaned
        return None

    def _extract_spoken_email(self, text: str) -> Optional[str]:
        """Capture spoken or malformed email forms from transcript text."""
        # Direct spoken pattern: username at domain dot com
        spoken_pattern = r'([\w\.\-]+)\s+(?:at|@)\s+([\w\.\-]+)\s+(?:dot|\.)\s+(com|org|net|io|in|co|edu)'
        match = re.search(spoken_pattern, text, re.IGNORECASE)
        if match:
            local = match.group(1).replace(' ', '').strip()
            domain = match.group(2).replace(' ', '').strip()
            suffix = match.group(3).strip().lower()
            return f"{local}@{domain}.{suffix}"

        # Common malformed email without @ but with domain parts
        email_like = re.search(r'([\w\.-]+)\.([\w\.-]+)\.(com|org|net|io|in|co|edu)', text, re.IGNORECASE)
        if email_like:
            local = email_like.group(1).replace(' ', '')
            domain = email_like.group(2).replace(' ', '')
            suffix = email_like.group(3).lower()
            return f"{local}@{domain}.{suffix}"

        return None

    def _extract_years_of_experience(self, text: str) -> Optional[int]:
        """Extract years of experience"""
        exp_patterns = [
            r'(\d+)\s+years?\s+(?:of\s+)?experience',
            r'experience\s+of\s+(\d+)\s+years?',
            r'(?:have|had)\s+(?:like\s+)?(\d+)\s+years',
            r'(?:I\s+have)\s+(\d+)\s+years',
            r'(?:worked|working)\s+.*?\s+for\s+(\d+)\s+years',
            r'for\s+(\d+)\s+years',
        ]
        
        for pattern in exp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    years = int(match.group(1))
                    if 0 <= years <= 60:
                        return years
                except ValueError:
                    pass
        
        return None
    
    def _extract_organization(self, text: str) -> Optional[str]:
        """Extract current organization - handles 'Role at Organization' pattern"""
        # Clean text first
        cleaned_text = re.sub(r'\b(uhh?|umm?\.{0,3}|like|you\s+know|yeah)\b[.,\s]*', ' ', text, flags=re.IGNORECASE)
        cleaned_text = ' '.join(cleaned_text.split())  # Normalize whitespace
        
        org_patterns = [
            r'(?:Current\s+Role[:\s]+[^,\n]+?\s+at\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "Current Role: X at Organization"
            r'(?:working\s+at|currently\s+at|employed\s+at|worked\s+at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'\bat\s+([A-Z][a-z]+(?:\s+Inc\.?|Corp\.?|Ltd\.?|LLC|Data))',
            r'(?:at\s+)([A-Z][a-z]+(?:Data|Systems|Solutions|Technologies))',
        ]
        
        for pattern in org_patterns:
            match = re.search(pattern, cleaned_text, re.IGNORECASE)
            if match:
                org = match.group(1).strip()
                # Remove trailing "as" or location if present
                org = re.sub(r'\s+(?:as|in),?\s*\w+\s*$', '', org, flags=re.IGNORECASE)
                org = re.sub(r',.*$', '', org).strip()
                if len(org) > 2:
                    return org
        
        return None
    
    def _extract_skills_canonical(self, text: str) -> Dict[str, Any]:
        """Extract skills in canonical schema format - supports dynamic categorization and AI/ML frameworks"""
        primary_skills = []
        secondary_skills = []
        additional_skills = []
        frameworks = []
        tools = []
        
        # Check if skills are explicitly categorized in transcript
        has_primary = re.search(r'\b(?:Primary\s+(?:Skills?|Technologies))[:\s]', text, re.IGNORECASE)
        has_secondary = re.search(r'\b(?:Secondary\s+(?:Skills?|Technologies))[:\s]', text, re.IGNORECASE)
        has_additional = re.search(r'\b(?:Additional\s+(?:Skills?|Technologies))[:\s]', text, re.IGNORECASE)
        
        if has_primary or has_secondary or has_additional:
            # Extract skills from explicit sections
            if has_primary:
                primary_skills = self._extract_skills_from_section(text, r'Primary\s+(?:Skills?|Technologies)[:\s]+([^.]+?)(?=(?:Secondary|Additional|Experience|Projects?|Education|\n\n|$))')
            if has_secondary:
                secondary_skills = self._extract_skills_from_section(text, r'Secondary\s+(?:Skills?|Technologies)[:\s]+([^.]+?)(?=(?:Primary|Additional|Experience|Projects?|Education|\n\n|$))')
            if has_additional:
                additional_skills = self._extract_skills_from_section(text, r'Additional\s+(?:Skills?|Technologies)[:\s]+([^.]+?)(?=(?:Primary|Secondary|Experience|Projects?|Education|\n\n|$))')
        else:
            # Fallback to automatic extraction and categorization
            primary_skills, frameworks, tools = self._auto_extract_skills(text)
        
        return {
            "primarySkills": primary_skills,
            "secondarySkills": secondary_skills if secondary_skills else additional_skills,
            "frameworks": frameworks,
            "toolsAndPlatforms": tools
        }
    
    def _extract_skills_from_section(self, text: str, pattern: str) -> List[str]:
        """Extract comma-separated skills from a specific section"""
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if not match:
            return []
        
        skills_text = match.group(1).strip()
        # Split by commas and clean
        skills = [s.strip() for s in re.split(r'[,;]', skills_text) if s.strip()]
        # Filter out empty or very short items
        skills = [s for s in skills if len(s) > 1]
        return skills
    
    def _auto_extract_skills(self, text: str) -> tuple:
        """Automatically extract and categorize skills"""
        primary_skills = []
        frameworks = []
        tools = []
        
        # Enhanced technical skills list
        tech_skills = [
            'Python', 'Java', 'JavaScript', 'TypeScript', 'C#', 'C++', 'Ruby', 'Go', 'Rust', 'PHP', 'Swift', 'Kotlin',
            'SQL', 'R', 'Scala', 'Perl', 'Shell', 'Bash', 'PowerShell'
        ]
        
        # Enhanced frameworks list with AI/ML frameworks
        frameworks_list = [
            # Web Frameworks
            'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring', 'Express',
            '.NET', 'FastAPI', 'Laravel', 'Rails', 'Spring Boot', 'ASP.NET',
            # AI/ML Frameworks
            'LangChain', 'LangGraph', 'LangSmith', 'TensorFlow', 'PyTorch', 'Keras',
            'scikit-learn', 'Scikit-Learn', 'AutoGen', 'Crew AI', 'CrewAI',
            # Data Frameworks
            'NumPy', 'Pandas', 'PySpark', 'Apache Spark', 'Databricks', 'Hadoop',
            'Kafka', 'Airflow', 'Apache Airflow'
        ]
        
        # Enhanced tools list
        tools_list = [
            # Cloud Platforms
            'AWS', 'Azure', 'GCP', 'Google Cloud', 'IBM Cloud', 'Oracle Cloud',
            # Azure Specific
            'ADF', 'Azure Data Factory', 'ADLS', 'Azure Data Lake', 'Azure Key Vault',
            'Key Vault', 'Azure Functions', 'Azure DevOps',
            # DevOps Tools
            'Docker', 'Kubernetes', 'Jenkins', 'CI/CD', 'Git', 'Terraform', 'Ansible',
            'GitLab', 'GitHub', 'GitHub Actions', 'CircleCI', 'Travis CI',
            # Databases
            'MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'Cassandra', 'DynamoDB',
            'SQL Server', 'Oracle', 'NoSQL', 'Elasticsearch',
            # Other Tools
            'REST API', 'GraphQL', 'Microservices', 'Jira', 'Confluence'
        ]
        
        # Extract primary skills (languages)
        for skill in tech_skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
                if skill not in primary_skills:
                    primary_skills.append(skill)
        
        # Extract frameworks
        for framework in frameworks_list:
            if re.search(r'\b' + re.escape(framework) + r'\b', text, re.IGNORECASE):
                if framework not in frameworks:
                    frameworks.append(framework)
        
        # Extract tools and platforms
        for tool in tools_list:
            if re.search(r'\b' + re.escape(tool) + r'\b', text, re.IGNORECASE):
                if tool not in tools:
                    tools.append(tool)
        
        return primary_skills, frameworks, tools
    
    def _extract_languages(self, text: str) -> List[str]:
        """Extract spoken languages"""
        languages = []
        
        language_patterns = [
            r'(?:I\s+speak|languages?[:\s]+|fluent\s+in)([^\n\.]{5,100})',
        ]
        
        for pattern in language_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                lang_text = match.group(1)
                common_languages = ['English', 'Spanish', 'French', 'German', 'Hindi', 'Chinese', 'Japanese', 'Arabic', 'Portuguese', 'Russian']
                for lang in common_languages:
                    if lang.lower() in lang_text.lower() and lang not in languages:
                        languages.append(lang)
        
        return languages
    
    def _extract_experience_canonical(self, text: str) -> Dict[str, Any]:
        """Extract experience in canonical schema format"""
        experience = {
            "projects": [],
            "workHistory": [],
            "domainExperience": self._extract_domain_expertise(text),
        }

        # Keep project extraction tightly scoped to the project experience portion of transcript.
        explicit_project_section = re.search(
            r'(?is)(?:\*\*)?project\s+experience(?:\*\*)?\s*[:\-]?\s*(.+?)'
            r'(?=\n\s*(?:\*\*)?(?:education|certifications?|languages?|operating\s+systems?|databases?|current\s+role)(?:\*\*)?\s*[:\-]?|\Z)',
            text,
        )
        if explicit_project_section:
            project_text = explicit_project_section.group(1).strip()
        else:
            project_text = re.split(
                r'\b(?:education|certifications?|languages?)\b\s*[:\-]?',
                text,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0]
        
        # First try structured project extraction (e.g., "my first project is...", "my second project name is...")
        structured_projects = self._extract_structured_projects(project_text)
        
        if structured_projects:
            experience["projects"] = structured_projects
        else:
            # Fallback to simple pattern matching
            experience["projects"] = self._extract_simple_projects(project_text)
        
        return experience
    
    def _extract_structured_projects(self, text: str) -> List[Dict[str, Any]]:
        """Extract projects from structured audio transcript"""
        markdown_projects = self._extract_markdown_projects(text)
        if markdown_projects:
            return [p for p in markdown_projects if not self._is_placeholder_project_entry(p)]

        projects = []
        
        # Split text into project segments based on ordinal patterns
        project_segments = self._segment_projects(text)
        
        for segment in project_segments:
            project = self._parse_project_segment(segment)
            if project and not self._is_placeholder_project_entry(project):
                projects.append(project)
        
        return projects

    def _extract_markdown_projects(self, text: str) -> List[Dict[str, Any]]:
        """Extract projects from markdown-style enhanced transcript blocks."""
        lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
        if not lines:
            return []

        projects: List[Dict[str, Any]] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if not re.match(r'^\*\*Project\s+Experience:?\*\*$', line, re.IGNORECASE):
                i += 1
                continue

            # Next bold line after "Project Experience" is usually project name.
            i += 1
            project_name = ""
            while i < len(lines):
                candidate = lines[i]
                name_match = re.match(r'^\*\*([^*]+)\*\*$', candidate)
                if name_match:
                    value = self._clean_markup(name_match.group(1))
                    if not re.match(r'^(client|project\s+description|responsibilities|technologies)\s*:?', value, re.IGNORECASE):
                        project_name = value
                        i += 1
                        break
                i += 1

            if not project_name or self._is_invalid_project_name(project_name):
                continue

            client = ""
            description = ""
            responsibilities: List[str] = []
            technologies: List[str] = []

            while i < len(lines):
                current = lines[i]
                if re.match(r'^\*\*Project\s+Experience:?\*\*$', current, re.IGNORECASE):
                    break

                client_match = re.match(r'^\*\*Client:?\*\*\s*(.+)$', current, re.IGNORECASE)
                if client_match:
                    client = self._clean_markup(client_match.group(1))
                    i += 1
                    continue

                desc_match = re.match(r'^\*\*Project\s+Description:?\*\*\s*(.+)$', current, re.IGNORECASE)
                if desc_match:
                    description = self._clean_markup(desc_match.group(1))
                    i += 1
                    continue

                resp_match = re.match(r'^\*\*Responsibilities:?\*\*\s*(.+)$', current, re.IGNORECASE)
                if resp_match:
                    resp = self._clean_markup(resp_match.group(1))
                    if resp:
                        responsibilities.append(resp if resp.endswith('.') else f"{resp}.")
                    i += 1
                    continue

                tech_match = re.match(r'^\*\*Technologies:?\*\*\s*(.+)$', current, re.IGNORECASE)
                if tech_match:
                    raw = self._clean_markup(tech_match.group(1))
                    technologies = [item.strip() for item in raw.split(',') if item.strip()]
                    i += 1
                    continue

                i += 1

            project = {
                "projectName": project_name,
                "clientName": client or None,
                "client": client or None,
                "role": None,
                "projectDescription": description,
                "description": description,
                "startDate": None,
                "endDate": None,
                "durationMonths": None,
                "toolsUsed": technologies,
                "technologies": technologies,
                "environment": technologies,
                "teamSize": None,
                "responsibilities": responsibilities,
                "outcomes": [],
                "achievements": [],
            }
            projects.append(project)

        return projects
    
    def _segment_projects(self, text: str) -> List[str]:
        """Segment text into individual project blocks - handles numbered lists"""
        segments = []

        numbered_boundaries = list(re.finditer(r'(?m)^\s*\d+\.\s+(?:\*\*)?.+', text))
        if numbered_boundaries:
            for index, boundary in enumerate(numbered_boundaries):
                start = boundary.start()
                end = numbered_boundaries[index + 1].start() if index + 1 < len(numbered_boundaries) else len(text)
                section = text[start:end].strip()
                section = re.split(r'(?im)^\s*education\b', section, maxsplit=1)[0].strip()
                if section:
                    segments.append(section)
            return segments
        
        # Pattern to detect project boundaries - includes numbered list format
        project_boundary_patterns = [
            r'(?:my\s+first\s+project)',
            r'(?:my\s+second\s+project)',
            r'(?:my\s+third\s+project)',
            r'(?:my\s+next\s+project)',
            r'(?:another\s+project)',
            r'(?:project\s+one|project\s+two|project\s+three|project\s+four|project\s+five)',
            r'(?:I\s+(?:also\s+)?worked\s+on)',
            r'(?:project\s+\d+)',
            r'(?:^\d+\.\s+)',
        ]
        
        combined_pattern = '(' + '|'.join(project_boundary_patterns) + ')'
        
        # Find all boundaries
        parts = re.split(combined_pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        
        current_segment = ""
        for i, part in enumerate(parts):
            if part and part.strip():
                # If it's a boundary marker, start new segment
                if re.match(combined_pattern, part.strip(), re.IGNORECASE | re.MULTILINE):
                    if current_segment.strip():
                        segments.append(current_segment.strip())
                    current_segment = part
                else:
                    current_segment += part
        
        # Add last segment
        if current_segment.strip():
            segments.append(current_segment.strip())
        
        return segments if segments else []
    
    def _parse_project_segment(self, segment: str) -> Optional[Dict[str, Any]]:
        """Parse a single project segment into project dict"""
        
        # Extract project name
        project_name = self._extract_project_name(segment)
        if not project_name:
            project_name = self._extract_generic_project_name(segment)
            if not project_name:
                return None
        if self._is_invalid_project_name(project_name):
            return None
        
        # Extract client
        client = self._extract_client(segment)
        
        # Extract description
        description = self._extract_project_description(segment)
        
        # Extract role
        role = self._extract_project_role(segment)
        
        # Extract responsibilities
        responsibilities = self._extract_responsibilities(segment)
        
        # Extract technologies
        technologies = self._extract_project_technologies(segment)
        
        return {
            "projectName": project_name,
            "clientName": client,
            "client": client,
            "role": role,
            "projectDescription": description,
            "description": description,
            "startDate": None,
            "endDate": None,
            "durationMonths": None,
            "toolsUsed": technologies,
            "technologies": technologies,
            "environment": technologies,
            "teamSize": None,
            "responsibilities": responsibilities,
            "outcomes": [],
            "achievements": []
        }
    
    def _extract_project_name(self, text: str) -> Optional[str]:
        """Extract project name from segment - handles numbered list with (Client: X) format"""
        name_patterns = [
            # Numbered list format: "1. Project Name (Client: X)"
            r'^\d+\.\s+([^(\n]+)\s*(?:\(Client:|\()',
            r'(?:project\s+(?:name\s+)?is)\s+([A-Z][^,\.]{3,60}?)(?:\s+and|\.|,)',
            r'(?:called|named)\s+([A-Z][^,\.]{3,60}?)(?:\s+and|\.|,)',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                # Clean up
                name = re.sub(r'\*\*([^*]+)\*\*', r'\1', name)
                name = re.sub(r'\s+(?:and|client|with)$', '', name, flags=re.IGNORECASE).strip()
                name = re.sub(r'^\s*(?:is|called|named)\s+', '', name, flags=re.IGNORECASE).strip()
                if len(name) > 3:
                    return name
        
        return None

    def _extract_generic_project_name(self, text: str) -> Optional[str]:
        """Fallback project name extraction when no explicit name pattern is found."""
        match = re.search(r'(?:project\s+is\s+called|project\s+is|called|named)\s+([A-Z][^,\.]{3,80})', text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            name = re.sub(r'\s+(?:and|for|with)$', '', name, flags=re.IGNORECASE).strip()
            if len(name) > 3:
                return name
        return None
    
    def _extract_client(self, text: str) -> Optional[str]:
        """Extract client name from segment - handles (Client: X) format"""
        client_patterns = [
            # Parenthetical format: "(Client: Volkswagen)"
            r'\(Client:\s*([^)]+)\)',
            r'(?:client\s+is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'(?:for|client[:\s]+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        ]
        
        for pattern in client_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                client = match.group(1).strip()
                # Clean up
                client = re.sub(r'[,\.]$', '', client).strip()
                if len(client) > 2:
                    return client
        
        return None
    
    def _extract_project_description(self, text: str) -> str:
        """Extract project description from segment"""
        desc_patterns = [
            r'(?:project\s+description\s+is)\s+(.+?)(?=\s*(?:coming\s+to\s+my\s+roles|roles\s+and\s+responsibilities|my\s+(?:second|third|next)\s+project|\d+\.\s+|education\s*[:\-]|i\s+have\s+completed\s+(?:a|my)\s+(?:master|bachelor)|$))',
            r'(?:description[:\s]+)\s*(.+?)(?=\s*(?:coming\s+to\s+my\s+roles|roles\s+and\s+responsibilities|my\s+(?:second|third|next)\s+project|\d+\.\s+|education\s*[:\-]|i\s+have\s+completed\s+(?:a|my)\s+(?:master|bachelor)|$))',
        ]
        
        for pattern in desc_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                description = match.group(1).strip()
                # Clean up - stop at "coming to my roles" or similar transitions
                description = re.sub(
                    r'\s*(?:coming\s+to\s+my\s+roles|my\s+role|roles\s+and\s+responsibilities).*$',
                    '',
                    description,
                    flags=re.IGNORECASE | re.DOTALL
                ).strip()
                
                # Clean up filler words
                description = re.sub(r'\s+', ' ', description)
                
                if len(description) > 10:
                    return description

        # Fallback: derive a description by removing intro/client/responsibility clauses.
        simplified = text
        simplified = re.sub(r'(?is)^.*?(?:project\s+(?:name\s+)?is|my\s+(?:first|second|third|next)\s+project\s+is)\s+[A-Z][^\.\n]{0,120}[\.,]?', '', simplified)
        simplified = re.sub(r'(?is)client\s+is\s+[A-Z][^\.\n]{0,80}[\.,]?', '', simplified)
        simplified = re.sub(r'(?is)\beducation\b\s*[:\-].*$', '', simplified)
        simplified = re.sub(r'(?is)\bi\s+have\s+completed\s+(?:a|my)\s+(?:master|bachelor).*$', '', simplified)
        simplified = re.sub(r'(?is)\b(?:coming\s+to\s+my\s+roles|roles\s+and\s+responsibilities|responsibilities)\b.*$', '', simplified)
        simplified = re.sub(r'\s+', ' ', simplified).strip(' .')
        if len(simplified) > 15:
            return simplified

        # Return empty instead of synthetic placeholder text to avoid noisy preview entries.
        return ""
    
    def _extract_project_role(self, text: str) -> Optional[str]:
        """Extract project role from segment"""
        role_patterns = [
            r'(?:I\s+worked\s+as\s+a?)\s+([^,\.]{5,40})',
            r'(?:role\s+was|role\s+is)\s+([^,\.]{5,40})',
            r'(?:as\s+a?)\s+(developer|engineer|architect|consultant|analyst)',
        ]
        
        for pattern in role_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                role = match.group(1).strip()
                if len(role) > 3:
                    return role
        
        return None
    
    def _extract_responsibilities(self, text: str) -> List[str]:
        """Extract responsibilities from segment - handles bullet points and sections"""
        responsibilities = []

        # Pre-truncate the segment at any education section header or first education bullet
        text = re.split(
            r'(?im)^\s*(?:\*\*)?education(?:\*\*)?\s*[:\-]?\s*$',
            text, maxsplit=1
        )[0]
        text = re.split(
            r'(?im)^\s*[-•*]\s+(?:master|bachelor|b\.?tech|m\.?tech|mca|bca|'
            r'intermediate|secondary\s+school|10th|12th|diploma)',
            text, maxsplit=1
        )[0]

        # Find the responsibilities section
        stop = self._RESP_STOP
        resp_section_patterns = [
            r'(?:Responsibilities[:\s]+)(.+?)' + stop,
            r'(?:roles\s+and\s+responsibilities[^\.]*?[:\.])\\s*(.+?)' + stop,
            r'(?:responsibilities[:\s]+)(.+?)' + stop,
        ]
        
        resp_text = None
        for pattern in resp_section_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                resp_text = match.group(1).strip()
                break
        
        if not resp_text:
            return responsibilities
        
        # Try to extract bullet points or numbered items first
        bullet_patterns = [
            r'[-•]\s*(.+?)(?=[-•]|\n\n|$)',  # Bullet points
            r'\d+\)\s*(.+?)(?=\d+\)|\n\n|$)',  # Numbered with parentheses: "1) "
        ]
        
        for bullet_pattern in bullet_patterns:
            matches = re.finditer(bullet_pattern, resp_text, re.DOTALL)
            for match in matches:
                resp = match.group(1).strip()
                resp = re.sub(r'\s+', ' ', resp)
                if len(resp) > 15:
                    # Skip lines that look like education entries
                    if self._is_education_line(resp):
                        continue
                    resp = resp[0].upper() + resp[1:] if resp else resp
                    if not resp.endswith('.'):
                        resp += '.'
                    responsibilities.append(resp)
        
        # If no bullet points found, split by sentences
        if not responsibilities:
            sentences = re.split(r'(?:\.\s+I\s+|\.\s+)', resp_text)
            
            for sentence in sentences:
                sentence = sentence.strip()
                # Clean up
                sentence = re.sub(r'^(?:and\s+)?I\s+', 'I ', sentence, flags=re.IGNORECASE)
                sentence = re.sub(r'\s+', ' ', sentence)
                
                # Only include substantial sentences
                if len(sentence) > 15 and not re.match(r'^(?:coming|my|the|this)', sentence, re.IGNORECASE):
                    # Capitalize first letter
                    sentence = sentence[0].upper() + sentence[1:] if sentence else sentence
                    # Add period if missing
                    if not sentence.endswith('.'):
                        sentence += '.'
                    responsibilities.append(sentence)

        # Secondary fallback: split combined responsibility text into multiple sentences
        if len(responsibilities) <= 1 and resp_text:
            fallback = []
            fallback_sentences = [s.strip() for s in re.split(r'(?<=[\.\?\!])\s+', resp_text) if s.strip()]
            for sentence in fallback_sentences:
                sentence = re.sub(r'^(?:and\s+)?I\s+', 'I ', sentence, flags=re.IGNORECASE)
                sentence = re.sub(r'\s+', ' ', sentence).strip()
                if len(sentence) > 15 and sentence.lower() not in [r'coming to my roles and responsibilities of this project, i worked as a developer.', 'i worked as a developer.']:
                    if not sentence.endswith('.'):
                        sentence += '.'
                    if sentence not in fallback:
                        fallback.append(sentence)
            if len(fallback) > 1:
                responsibilities = fallback

        return responsibilities
    
    def _extract_project_technologies(self, text: str) -> List[str]:
        """Extract technologies mentioned in project segment"""
        technologies = []
        
        # Comprehensive technology list
        tech_list = [
            # Languages
            'Python', 'Java', 'JavaScript', 'TypeScript', 'C#', 'C++', 'Go', 'Rust', 'Ruby', 'PHP',
            # Web Frameworks
            'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring', 'Express', '.NET',
            # Cloud Platforms
            'AWS', 'Azure', 'GCP', 'Google Cloud',
            # Azure Services
            'ADF', 'Azure Data Factory', 'ADLS', 'Azure Data Lake', 'Key Vault', 'Azure Key Vault',
            # DevOps Tools
            'Docker', 'Kubernetes', 'Jenkins', 'GitLab', 'GitHub', 'CI/CD', 'Terraform', 'Ansible',
            # Databases
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'SQL Server', 'Oracle', 'Cassandra',
            'NoSQL', 'SQL',
            # Data Tools
            'Spark', 'Hadoop', 'Kafka', 'Airflow', 'ETL',
            # Others
            'REST API', 'GraphQL', 'Microservices', 'Git'
        ]
        
        for tech in tech_list:
            # Use word boundary for exact matches
            pattern = r'\b' + re.escape(tech) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                # Avoid duplicates
                if tech not in technologies:
                    technologies.append(tech)
        
        return technologies
    
    def _extract_simple_projects(self, text: str) -> List[Dict[str, Any]]:
        """Fallback: Extract projects using simple pattern matching"""
        projects = []
        
        project_patterns = [
            r'(?:worked\s+on|project[:\s]+)([^\.]+?)(?:project|using|with)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4})\s+(?:project|platform|system)',
        ]
        
        projects_found = set()
        for idx, pattern in enumerate(project_patterns):
            flags = re.IGNORECASE if idx == 0 else 0
            matches = re.finditer(pattern, text, flags)
            for match in matches:
                project_name = match.group(1).strip()
                nearby_prefix = text[max(0, match.start() - 30):match.start()]
                if re.search(r'client\s*:\s*$', nearby_prefix, re.IGNORECASE):
                    continue
                # Clean up project name
                project_name = re.sub(r'\s+(?:using|with|for|on|the)$', '', project_name, flags=re.IGNORECASE).strip()
                project_name = re.sub(r'^[\-*•\s]+', '', project_name).strip()

                if self._is_invalid_project_name(project_name):
                    continue
                
                if len(project_name) > 5 and project_name not in projects_found:
                    projects_found.add(project_name)
                    
                    # Extract description from context
                    desc_match = re.search(
                        rf'{re.escape(project_name)}[^\.]*?[,\.]([^\.]{20,200})',
                        text,
                        re.IGNORECASE
                    )
                    description = desc_match.group(1).strip() if desc_match else ""
                    
                    # Extract technologies for this project
                    project_context = text[max(0, match.start()-100):min(len(text), match.end()+300)]
                    tech_skills = ['Python', 'Java', 'React', 'AWS', 'Azure', 'Docker', 'Node.js', 'Kubernetes', 'MongoDB']
                    technologies = []
                    for skill in tech_skills:
                        if re.search(r'\b' + re.escape(skill) + r'\b', project_context, re.IGNORECASE):
                            technologies.append(skill)
                    
                    project = {
                        "projectName": project_name,
                        "clientName": None,
                        "client": None,
                        "role": None,
                        "projectDescription": description,
                        "description": description,
                        "startDate": None,
                        "endDate": None,
                        "durationMonths": None,
                        "toolsUsed": technologies,
                        "technologies": technologies,
                        "environment": technologies,
                        "teamSize": None,
                        "responsibilities": [description] if description else [],
                        "achievements": []
                    }

                    if not self._is_placeholder_project_entry(project):
                        projects.append(project)
        
        return projects

    def _is_invalid_project_name(self, name: Optional[str]) -> bool:
        if not name:
            return True

        normalized = re.sub(r'\s+', ' ', str(name).strip().lower()).strip(' .,:;')
        if not normalized:
            return True
        if normalized in self._invalid_project_names:
            return True
        if normalized.startswith('worked on '):
            return True
        if normalized.startswith('responsibilities'):
            return True
        return False

    def _is_placeholder_project_entry(self, project: Dict[str, Any]) -> bool:
        """Detect low-information project entries that should not appear in preview."""
        name = str(project.get("projectName") or "").strip()
        normalized_name = re.sub(r'\s+', ' ', name.lower()).strip(' .,:;')
        if not normalized_name:
            return True

        description = str(project.get("projectDescription") or project.get("description") or "").strip()
        normalized_description = re.sub(r'\s+', ' ', description.lower()).strip(' .,:;')
        responsibilities = [
            re.sub(r'\s+', ' ', str(resp).strip().lower()).strip(' .,:;')
            for resp in (project.get("responsibilities") or [])
            if str(resp).strip()
        ]
        technologies = [
            str(tech).strip()
            for tech in (project.get("toolsUsed") or project.get("technologies") or [])
            if str(tech).strip()
        ]
        client = str(project.get("clientName") or project.get("client") or "").strip()
        role = str(project.get("role") or "").strip()

        # Treat template/fallback phrasings as placeholder content.
        generic_desc = {
            "project details not specified",
            f"worked on {normalized_name}",
            f"worked on the {normalized_name}",
        }
        has_only_generic_description = normalized_description in generic_desc or not normalized_description
        has_only_generic_responsibility = (
            len(responsibilities) <= 1 and
            (not responsibilities or responsibilities[0] in {f"worked on {normalized_name}", f"worked on the {normalized_name}"})
        )

        if has_only_generic_description and has_only_generic_responsibility and not technologies and not client and not role:
            return True

        return False
    
    def _extract_education_canonical(self, text: str) -> List[Dict[str, Any]]:
        """Extract education"""
        education = []
        
        # Split text into potential education sections
        # Look for degree/education keywords to segment
        edu_segments = self._segment_education_text(text)
        
        for segment in edu_segments:
            edu_entry = self._parse_education_segment(segment)
            if edu_entry:
                education.append(edu_entry)
        
        return education
    
    def _segment_education_text(self, text: str) -> List[str]:
        """Segment text into individual education entries"""
        segments = []
        
        # Split on common education entry delimiters
        # Look for phrases like "Next,", "I have completed", "I completed my"
        split_patterns = [
            r'(?:Next[,\s]+)',
            r'(?:I\s+have\s+completed(?:\s+(?:a|my))?)',
            r'(?:I\s+completed\s+(?:my)?)',
            r'(?:My\s+(?:first|second|third|next)\s+(?:educational\s+qualification|qualification|education))',
            r'(?:My\s+(?:secondary|higher\s+secondary)\s+education)',
            r'(?:My\s+(?:secondary\s+)?school)',
        ]
        
        combined_pattern = '|'.join(f'({p})' for p in split_patterns)
        parts = re.split(combined_pattern, text, flags=re.IGNORECASE)
        
        current_segment = ""
        for part in parts:
            if part and part.strip():
                # If it's a delimiter, start new segment
                if any(re.match(p, part.strip(), re.IGNORECASE) for p in split_patterns):
                    if current_segment.strip():
                        segments.append(current_segment.strip())
                    current_segment = part
                else:
                    current_segment += part
        
        # Add last segment
        if current_segment.strip():
            segments.append(current_segment.strip())

        segmented = segments if segments else [text]

        # Fallback segmentation for transcripts where multiple qualifications appear in one block.
        if len(segmented) <= 1:
            marker_pattern = r'(?=\b(?:master\s+of|bachelor\s+of|mca\b|b\.?sc\b|b\.?tech\b|intermediate\s+education|12th\s+standard|10th\s+standard|secondary\s+school)\b)'
            marker_split = [s.strip() for s in re.split(marker_pattern, text, flags=re.IGNORECASE) if s and s.strip()]
            if len(marker_split) > 1:
                segmented = marker_split

        return segmented
    
    def _parse_education_segment(self, segment: str) -> Optional[Dict[str, Any]]:
        """Parse a single education segment"""
        
        # Extract degree type
        degree = self._extract_degree_type(segment)
        if not degree:
            return None
        
        # Extract field of study
        field = self._extract_field_of_study(segment)
        
        # Extract institution (college/school/university)
        institution = self._extract_institution(segment)
        
        # Extract graduation year
        year = self._extract_graduation_year(segment)
        
        # Extract GPA/percentage
        gpa = self._extract_gpa_percentage(segment)
        
        # Only return if we have meaningful data
        if degree or field or institution:
            degree = self._normalize_degree_name(degree, field)
            percentage_value = gpa if gpa and gpa.endswith('%') else None
            grade_value = gpa if gpa and not gpa.endswith('%') else None
            return {
                "degree": degree,
                "specialization": field,
                "field": field,
                "institution": institution,
                "yearOfPassing": year,
                "graduationYear": year,
                "percentage": percentage_value,
                "grade": grade_value,
                "gpa": gpa
            }
        
        return None
    
    def _extract_degree_type(self, text: str) -> Optional[str]:
        """Extract degree type from text"""
        degree_patterns = [
            # Western style degrees
            r'\b(Bachelor\'?s?|Master\'?s?|PhD|Doctorate)\b',
            r'\b(B\.?Tech|M\.?Tech|B\.?E\.?|M\.?E\.?|B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?|MBA|MCA)\b',
            # Indian style descriptions
            r'\b(Master\s+of\s+Computer\s+Applications)\b',
            r'\b(Bachelor\s+of\s+(?:Science|Technology|Engineering|Arts))\b',
            r'\b(Intermediate(?:\s+education)?)\b',
            r'\b((?:10th|tenth)\s+standard)\b',
            r'\b((?:12th|twelfth)\s+standard)\b',
            r'\b(secondary\s+school)\b',
        ]
        
        for pattern in degree_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                degree = match.group(1)
                # Normalize common abbreviations
                degree_map = {
                    'MCA': 'Master of Computer Applications',
                    'B.Sc': 'Bachelor of Science',
                    'BSc': 'Bachelor of Science',
                    'B.Tech': 'Bachelor of Technology',
                    'BTech': 'Bachelor of Technology',
                    'M.Tech': 'Master of Technology',
                    'MTech': 'Master of Technology',
                }
                return degree_map.get(degree.replace('.', '').replace(' ', ''), degree)
        
        return None

    def _normalize_degree_name(self, degree: Optional[str], field: Optional[str]) -> Optional[str]:
        """Normalize incomplete degree names using field of study."""
        if not degree:
            return degree

        degree_str = degree.strip()
        if not field:
            return degree_str

        normalized_field = field if field.isupper() else field.title()
        if re.search(r'\bmaster\b', degree_str, re.IGNORECASE) and not re.search(r'\bof\b', degree_str, re.IGNORECASE):
            return f"Master of {normalized_field}"
        if re.search(r'\bbachelor\b', degree_str, re.IGNORECASE) and not re.search(r'\bof\b', degree_str, re.IGNORECASE):
            return f"Bachelor of {normalized_field}"
        return degree_str
    
    def _extract_field_of_study(self, text: str) -> Optional[str]:
        """Extract field of study"""
        field_patterns = [
            r'(?:branch\s+is|field\s+is|major\s+is)\s+([^,\.]{2,60})',
            r'(?:(?:Master|Bachelor|B\.?Tech|M\.?Tech|B\.?E\.?|M\.?E\.?|MBA|MCA)\s+(?:in|of))\s+([^,\.]{2,60})',
            r'\b(Computer\s+(?:Science|Applications|Engineering))\b',
            r'\b(Computers)\b',
            r'\b(MPC)\b',  # Mathematics, Physics, Chemistry
        ]
        
        for pattern in field_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                field = match.group(1).strip()
                # Clean up
                field = re.sub(r'\s+(?:from|at|in)\s+.*$', '', field, flags=re.IGNORECASE).strip()
                field = re.sub(r'\s+(from|at|in|is)$', '', field, flags=re.IGNORECASE).strip()
                if len(field) > 2:
                    return field
        
        return None
    
    def _extract_institution(self, text: str) -> Optional[str]:
        """Extract institution name"""
        institution_patterns = [
            r'(?:college\s+name\s+is|school\s+name\s+is)\s+([A-Z][^,\.]{5,60})',
            r'(?:from|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,7}(?:\s+(?:College|University|School|Institute))?)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5}\s+(?:College|University|School|Institute))\b',
        ]
        
        for pattern in institution_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                institution = match.group(1).strip()
                # Clean up
                institution = re.sub(r'\s+(?:at|from|in)\s+.*$', '', institution, flags=re.IGNORECASE).strip()
                institution = re.sub(r'[,\.]$', '', institution).strip()
                # Remove university name from college name if both present
                institution = re.sub(r'\s+(?:at|from)\s+\w+.*(?:University|Board).*$', '', institution, flags=re.IGNORECASE).strip()
                if self._is_valid_institution_candidate(institution):
                    return institution

        # Keyword-based fallback to capture lower/mixed-case institutions robustly.
        keyword_match = re.search(
            r'([A-Za-z][A-Za-z\.\-&\s]{3,90}(?:University|College|School|Institute))',
            text,
            re.IGNORECASE,
        )
        if keyword_match:
            institution = re.sub(r'\s+', ' ', keyword_match.group(1)).strip(' .,')
            if self._is_valid_institution_candidate(institution):
                return institution
        
        return None

    def _is_valid_institution_candidate(self, institution: Optional[str]) -> bool:
        """Filter out noisy institution captures like 'the development' or year fragments."""
        if not institution:
            return False

        candidate = institution.strip()
        if len(candidate) < 4:
            return False

        # Reject common noisy starts from transcript narration.
        if candidate.lower().startswith(("the ", "my ", "in the ", "and ")):
            return False

        # Reject phrases that look like metadata instead of institutions.
        if re.search(r'\b(year|percentage|grade|branch|passing|responsibilities|project|developed|development)\b', candidate, re.IGNORECASE):
            return False

        return True
    
    def _extract_graduation_year(self, text: str) -> Optional[str]:
        """Extract graduation year - handles year ranges with '–' delimiter"""
        year_patterns = [
            # Year range with various delimiters: "2019 – 2022", "2019-2022", "2019 to 2022"
            r'(?:year\s+of\s+passing\s+is|passing\s+year\s+is|in\s+the\s+year\s+of)\s+(\d{4})\s*[–\-—]\s*(\d{4})',
            r'(\d{4})\s*[–\-—]\s*(\d{4})',
            r'(\d{4})\s+to\s+(\d{4})',
            # Single year
            r'(?:year\s+of\s+passing\s+is|passing\s+year\s+is|in\s+the\s+year\s+of)\s+(\d{4})',
            r'\b(19\d{2}|20[0-2]\d)\b',  # Years from 1900-2029
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if match.lastindex >= 2:
                    # Year range - return the end year (graduation year)
                    end_year = match.group(2)
                    year_int = int(end_year)
                    if 1950 <= year_int <= 2030:
                        return end_year
                else:
                    # Single year
                    year = match.group(1)
                    year_int = int(year)
                    if 1950 <= year_int <= 2030:
                        return year
        
        return None
    
    def _extract_gpa_percentage(self, text: str) -> Optional[str]:
        """Extract GPA or percentage - handles inline format like 'with a percentage of 83%'"""
        gpa_patterns = [
            # "with a percentage of 83%"
            r'(?:with\s+a\s+percentage\s+of)\s+(\d+(?:\.\d+)?)\s*%?',
            r'(?:percentage\s+is|got|scored)\s+(\d+(?:\.\d+)?)\s*(?:percent(?:age|ile)?|%)?',
            r'(?:with|got)\s+(\d+(?:\.\d+)?)\s*(?:percent(?:age|ile)?|%)',
            r'(?:GPA|CGPA)[\s:]+(\d+(?:\.\d+)?)',
            # Just a percentage number followed by %
            r'(\d+(?:\.\d+)?)\s*%',
        ]
        
        for pattern in gpa_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1)
                # If it's a percentage, format it
                num = float(value)
                if num <= 10:  # Probably GPA
                    return f"{value} GPA"
                else:  # Probably percentage
                    return f"{value}%"
        
        return None
    
    def _extract_certifications_canonical(self, text: str) -> List[Dict[str, Any]]:
        """Extract certifications"""
        certifications = []
        
        # More specific patterns
        cert_patterns = [
            r'(AWS\s+(?:Certified\s+)?(?:Solutions\s+Architect|Developer|SysOps|Administrator))',
            r'(Azure\s+(?:Certified\s+)?(?:Administrator|Developer|Architect))',
            r'(Kubernetes\s+(?:Certified\s+)?Administrator)',
            r'((?:have|earned|obtained)\s+(?:an?\s+)?(\w+(?:\s+\w+){0,3})\s+certification)',
            r'Certifications?[:\s]+([\w\s,]+)',
        ]
        
        for pattern in cert_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                cert_text = match.group(1).strip() if match.lastindex and match.lastindex >= 1 else match.group(0).strip()
                # Clean up
                cert_text = re.sub(r'^Certifications?[:\s]+', '', cert_text, flags=re.IGNORECASE)
                cert_text = cert_text.strip('.,')
                
                if len(cert_text) > 3 and cert_text.lower() not in ['have', 'earned', 'obtained']:
                    cert = {
                        "name": cert_text,
                        "issuer": None,
                        "dateObtained": None,
                        "expiryDate": None
                    }
                    certifications.append(cert)
        
        return certifications
