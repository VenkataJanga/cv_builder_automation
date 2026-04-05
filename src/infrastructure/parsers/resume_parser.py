import re
from typing import Dict, Any, List, Tuple


class ResumeParser:
    """
    Comprehensive deterministic parser for CV extraction.
    Extracts: personal details, experience, education, skills, certifications, etc.
    Enhanced to handle table-formatted CVs.
    """

    def parse(self, text: str) -> Dict[str, Any]:
        """Parse CV text and extract all sections."""
        result: Dict[str, Any] = {
            "personal_details": {},
            "summary": {},
            "skills": {
                "technical_skills": [],
                "soft_skills": [],
                "domains": []
            },
            "experience": [],
            "project_experience": [],
            "education": [],
            "certifications": [],
            "publications": [],
            "awards": [],
            "languages": [],
            "leadership": {}
        }

        if not text or not text.strip():
            return result

        # Extract personal details
        self._extract_personal_details(text, result)
        
        # Extract summary
        self._extract_summary(text, result)
        
        # Extract skills
        self._extract_skills(text, result)
        
        # Extract work experience (employer table)
        self._extract_work_experience(text, result)
        
        # Extract project experience
        self._extract_project_experience(text, result)
        
        # Extract education
        self._extract_education(text, result)
        
        # Extract certifications/training
        self._extract_certifications(text, result)
        
        # Extract languages
        self._extract_languages(text, result)
        
        # Extract publications
        self._extract_publications(text, result)
        
        # Extract awards
        self._extract_awards(text, result)
        
        # Extract leadership
        self._extract_leadership(text, result)
        
        # If no work experience but has projects, convert first project to work experience
        if not result["experience"] and result["project_experience"]:
            self._convert_projects_to_experience(result)

        return result

    def _extract_personal_details(self, text: str, result: Dict[str, Any]) -> None:
        """Extract name, phone, email, portal ID, etc."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        
        # Extract name - look for "NAME:" pattern (handle both POTAL and PORTAL typo)
        name_match = re.search(r"NAME\s*:\s*([A-Za-z\s]+?)\s*,", text, re.IGNORECASE)
        if name_match:
            result["personal_details"]["full_name"] = name_match.group(1).strip()
        elif lines and self._looks_like_name(lines[0]):
            result["personal_details"]["full_name"] = lines[0]
        
        # Extract phone - look for contact details with numbers
        phone_match = re.search(r"(?:Contact\s+Details?|phone|mobile|tel)[\s:]*(\+?\d[\d\s\-\(\)]{8,})", text, re.IGNORECASE)
        if phone_match:
            result["personal_details"]["phone"] = re.sub(r"[\s\-\(\)]", "", phone_match.group(1))
        
        # Extract email - anywhere in the document
        email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        if email_match:
            result["personal_details"]["email"] = email_match.group(0)
        
        # Extract portal ID (handle POTAL typo)
        portal_match = re.search(r"(?:POTAL|PORTAL)\s+ID\s*:\s*(\d+)", text, re.IGNORECASE)
        if portal_match:
            result["personal_details"]["employee_id"] = portal_match.group(1)
        
        # Extract grade
        grade_match = re.search(r"CURRENT\s+GRADE\s*:\s*(\d+)", text, re.IGNORECASE)
        if grade_match:
            result["personal_details"]["grade"] = grade_match.group(1)
        
        # Extract total experience - improved pattern (structured CVs)
        exp_match = re.search(
            r"(?:have\s+)?(\d+\.?\d*)\s*\+?\s*(?:Years?|Yrs?)\s+(?:IT\s+)?(?:of\s+)?experience",
            text,
            re.IGNORECASE,
        )
        if exp_match:
            result["personal_details"]["total_experience_years"] = float(exp_match.group(1))
        else:
            # Fallback: generic "X years" anywhere (more robust for voice transcripts)
            generic_exp_match = re.search(
                r"(\d+\.?\d*)\s*\+?\s*(years|yrs|year|yr)",
                text,
                re.IGNORECASE,
            )
            if generic_exp_match:
                result["personal_details"]["total_experience_years"] = float(generic_exp_match.group(1))

        # Fallback: current organization / company for less structured inputs
        if "current_organization" not in result["personal_details"]:
            org = self._extract_inline_value(
                text,
                ["current company", "organization", "company"],
            )
            if org:
                result["personal_details"]["current_organization"] = org

    def _extract_summary(self, text: str, result: Dict[str, Any]) -> None:
        """Extract professional summary - enhanced for bullet-point format."""
        # Look for "Experience Summary" section
        summary_match = re.search(r"Experience\s+Summary\s*[\r\n]+(.*?)(?=\n\s*(?:Technical|Primary|Skills|Experience Details|Qualification|Project Name|\Z))", text, re.IGNORECASE | re.DOTALL)
        
        if summary_match:
            summary_text = summary_match.group(1).strip()
            # Clean up the summary
            summary_text = re.sub(r'\s+', ' ', summary_text)
            result["summary"]["professional_summary"] = summary_text
        else:
            # Fallback to generic summary extraction
            summary = self._extract_section_block(
                text, 
                ["experience summary", "summary", "profile", "professional summary", "about"]
            )
            if summary:
                result["summary"]["professional_summary"] = summary

    def _extract_skills(self, text: str, result: Dict[str, Any]) -> None:
        """Extract technical skills into array of single-key objects."""
        skills_array = []
        
        # Look for "Technical Expertise" section - this contains all skills
        tech_section_match = re.search(
            r"Technical\s+Expertise(.*?)(?=Experience Details|Qualification|Project Details|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        
        if tech_section_match:
            tech_text = tech_section_match.group(1).strip()
            
            # Split by \x07 (bell character) which is used as separator in DOC files
            parts = [p.strip() for p in re.split(r'[\x07\n\r]+', tech_text) if p.strip()]
            
            # Process in pairs: category name + skills list
            i = 0
            while i < len(parts):
                part = parts[i].strip()
                
                # Skip empty parts
                if not part or len(part) < 3:
                    i += 1
                    continue
                
                # Check if this is a category header
                # Categories typically end with ":" or are followed by a value
                if i + 1 < len(parts):
                    # Check common category patterns
                    category_patterns = [
                        r'^(Primary\s+Skills?)\s*:?$',
                        r'^(Operating\s+Systems?)\s*:?$',
                        r'^(Languages?)\s*:?$',
                        r'^(Development\s+Tools?)\s*:?$',
                        r'^(CRM\s+tools?)\s*:?$',
                        r'^(Database\s+Connectivity)\s*:?$',
                        r'^(Databases?)\s*:?$',
                        r'^(SQL\s+Skills?)\s*:?$',
                        r'^(Domain\s+Knowledge)\s*:?$',
                        r'^(ERP)\s*:?$',
                        r'^(Networking)\s*:?$',
                        r'^(Testing\s+Tools?)\s*:?$',
                        r'^(Documentation)\s*:?$',
                        r'^(Configuration\s+Management)\s*:?$',
                    ]
                    
                    matched_category = None
                    for pattern in category_patterns:
                        match = re.search(pattern, part, re.IGNORECASE)
                        if match:
                            matched_category = match.group(1)
                            break
                    
                    if matched_category:
                        # Next part should be the skills list
                        skills_text = parts[i + 1].strip()
                        
                        # Clean up the skills text
                        skills_text = skills_text.replace('\x07', '').strip()
                        skills_text = re.sub(r'^[\s:\-,]+|[\s,]+$', '', skills_text)
                        
                        if skills_text and len(skills_text) > 1:
                            skills_array.append({matched_category: skills_text})
                        
                        i += 2  # Skip both category and value
                        continue
                
                i += 1
        
        # Fallback: Try to extract Primary Skills separately if Technical Expertise section not found
        if not skills_array:
            primary_skills_match = re.search(r"Primary\s+Skills\s+([^\n\r]+)", text, re.IGNORECASE)
            if primary_skills_match:
                skills_text = primary_skills_match.group(1).strip().replace('\x07', '')
                if skills_text and len(skills_text) > 1:
                    skills_array.append({"Primary Skills": skills_text})

        # Additional fallback for more free-form / voice-transcript style CVs
        # e.g. "Skills: Python, Azure, Docker | Kubernetes"
        if not skills_array:
            skills_line = self._extract_inline_value(
                text,
                ["skills", "technical skills", "technologies", "tech stack"],
            )
            if skills_line:
                split_skills = [
                    s.strip()
                    for s in re.split(r",|\||;", skills_line)
                    if s.strip()
                ]
                if split_skills:
                    # Store as a single entry; downstream can further split if needed
                    skills_array.append({"Primary Skills": ", ".join(split_skills)})
        
        result["skills"]["technical_skills"] = skills_array

    def _extract_work_experience(self, text: str, result: Dict[str, Any]) -> None:
        """Extract work experience from 'Experience Details' table."""
        # Look for "Experience Details" table
        exp_match = re.search(r"Experience\s+Details.*?Relieving\s+Date(.*?)(?=Project\s+Details|Project\s+Name|Qualification|\Z)", text, re.IGNORECASE | re.DOTALL)
        
        if exp_match:
            exp_text = exp_match.group(1).strip()
            
            # Split by \x07 (bell character)
            parts = [p.strip() for p in exp_text.split('\x07') if p.strip()]
            
            # Process rows - skip row numbers, group into sets of 4 fields
            i = 0
            while i < len(parts):
                # Skip number-only entries (row numbers)
                if parts[i].isdigit() and len(parts[i]) <= 2:
                    i += 1
                    continue
                
                # Need at least 4 fields for a complete entry
                if i + 3 < len(parts):
                    company = parts[i].strip()
                    designation = parts[i + 1].strip()
                    join_date = parts[i + 2].strip()
                    relieve_date = parts[i + 3].strip()
                    
                    # Validate this looks like an experience entry (has a date)
                    if re.search(r'\d{4}|Till Date', join_date, re.IGNORECASE):
                        exp_entry = {
                            "company_name": company,
                            "designation": designation,
                            "start_date": join_date,
                            "end_date": relieve_date,
                            "responsibilities": []
                        }
                        result["experience"].append(exp_entry)
                        i += 4
                    else:
                        i += 1
                else:
                    break

    def _extract_project_experience(self, text: str, result: Dict[str, Any]) -> None:
        """Extract detailed project experience."""
        # Split text into project sections
        project_splits = re.split(r'(?=Project\s+Name)', text, flags=re.IGNORECASE)
        
        for project_text in project_splits:
            if 'Project Name' not in project_text and 'PROJECT NAME' not in project_text.upper():
                continue
            
            project = {}
            
            # Extract Project Name - clean \x07
            name_match = re.search(r"Project\s+Name\s+([^\n\r]+)", project_text, re.IGNORECASE)
            if name_match:
                project["project_name"] = name_match.group(1).strip().replace('\x07', '').strip()
            
            # Extract Client - clean \x07
            client_match = re.search(r"Client\s+([^\n\r]+)", project_text, re.IGNORECASE)
            if client_match:
                project["client"] = client_match.group(1).strip().replace('\x07', '').strip()
            
            # Extract Project Description - clean \x07
            desc_match = re.search(r"Project\s+Description\s+(.*?)(?=Duration|Environment|Role|Team Size|Project Name|$)", project_text, re.IGNORECASE | re.DOTALL)
            if desc_match:
                desc = desc_match.group(1).strip().replace('\x07', '')
                # Clean up description
                desc = re.sub(r'\s+', ' ', desc)
                project["description"] = desc.strip()[:1000]  # Longer limit for descriptions
            
            # Extract Duration
            duration_match = re.search(r"Duration\s+From\s+\(mm/yy\)\s+(\d{2}/\d{2,4})\s+To\s+\(mm/yy\)\s+(\d{2}/\d{2,4}|tilldate)", project_text, re.IGNORECASE)
            if duration_match:
                project["start_date"] = duration_match.group(1)
                project["end_date"] = duration_match.group(2)
            
            # Extract Role - clean \x07
            role_match = re.search(r"Role\s*/\s*Responsibility\s+([^\n\r]+)", project_text, re.IGNORECASE)
            if role_match:
                project["role"] = role_match.group(1).strip().replace('\x07', '').strip()
            
            # Extract Environment/Technologies - clean \x07
            env_match = re.search(r"Environment\s+(.*?)(?=Duration|Role|Contributions|Team Size|Project Name|$)", project_text, re.IGNORECASE | re.DOTALL)
            if env_match:
                env = env_match.group(1).strip().replace('\x07', '')
                env = re.sub(r'\s+', ' ', env)
                project["technologies"] = env.strip()[:500]
            
            # Extract Contributions - clean \x07
            contrib_match = re.search(r"Contributions?\s+(.*?)(?=Team Size|Project Name|Training|Qualification|$)", project_text, re.IGNORECASE | re.DOTALL)
            if contrib_match:
                contrib = contrib_match.group(1).strip().replace('\x07', '')
                # Split by bullet points or newlines
                responsibilities = []
                for line in contrib.split('\r'):
                    clean_line = line.strip()
                    if clean_line and len(clean_line) > 10:
                        # Remove bullet points and clean up
                        clean_line = re.sub(r'^[•·\-\*]\s*', '', clean_line)
                        responsibilities.append(clean_line[:500])
                project["responsibilities"] = responsibilities[:10]  # Allow more responsibilities
            
            if project.get("project_name"):
                result["project_experience"].append(project)

    def _extract_education(self, text: str, result: Dict[str, Any]) -> None:
        """Extract education details from Qualification/Education section."""
        # Look for "Qualification" section - data is tab-separated with \x07
        edu_match = re.search(r"Qualification\s+Details.*?(?:Percentage|cgpa|Grade)(.*?)(?=NAME:|Resume Format|NTT DATA|\Z)", text, re.IGNORECASE | re.DOTALL)
        
        if edu_match:
            edu_text = edu_match.group(1).strip()
            
            # Split by \x07 (bell character used as tab separator in DOC files)
            parts = [p.strip() for p in edu_text.split('\x07') if p.strip()]
            
            # Process rows - skip row numbers, group into sets of 6 fields
            i = 0
            while i < len(parts):
                # Skip number-only entries (row numbers)
                if parts[i].isdigit() and len(parts[i]) <= 2:
                    i += 1
                    continue
                
                # Need at least 6 fields for a complete entry
                if i + 5 < len(parts):
                    degree = parts[i].strip()
                    branch = parts[i + 1].strip()
                    year = parts[i + 2].strip()
                    college = parts[i + 3].strip()
                    university = parts[i + 4].strip()
                    grade = parts[i + 5].strip()
                    
                    # Validate this looks like an education entry
                    if year.isdigit() and len(year) == 4:
                        edu_entry = {
                            "degree": degree,
                            "field_of_study": branch,
                            "institution": college,
                            "university": university,
                            "graduation_year": year,
                            "grade": grade
                        }
                        result["education"].append(edu_entry)
                        i += 6
                    else:
                        i += 1
                else:
                    break

    def _extract_certifications(self, text: str, result: Dict[str, Any]) -> None:
        """Extract training and certifications."""
        # Look for "Training Attended / Certifications Done" section
        cert_match = re.search(r"Training\s+Attended.*?Certifications.*?To\s+\(mm/yy\)(.*?)(?=Qualification|Education|Resume Format|NTT DATA|\Z)", text, re.IGNORECASE | re.DOTALL)
        
        if cert_match:
            cert_text = cert_match.group(1).strip()
            
            # Split by \x07 (bell character)
            parts = [p.strip() for p in cert_text.split('\x07') if p.strip()]
            
            # Process entries - pattern: number.course_name, start_date, end_date
            i = 0
            while i < len(parts):
                # Look for numbered course entry
                course_match = re.match(r'(\d+)\.([\w\s/,]+)', parts[i])
                if course_match and i + 2 < len(parts):
                    course_name = course_match.group(2).strip()
                    start_date = parts[i + 1].strip()
                    end_date = parts[i + 2].strip()
                    
                    # Validate dates
                    if re.match(r'\d{2}/\d{2}/\d{2,4}', start_date):
                        cert_entry = {
                            "name": course_name,
                            "issuing_organization": "Training",
                            "issue_date": start_date,
                            "expiry_date": end_date
                        }
                        result["certifications"].append(cert_entry)
                        i += 3
                    else:
                        i += 1
                else:
                    i += 1

    def _extract_section_block(self, text: str, keywords: List[str]) -> str:
        """Generic section extractor using keywords.
        
        First tries a pattern-based extraction suited for structured CVs,
        then falls back to a line-oriented scan which works better for
        more free-form text and voice transcripts.
        """
        # Primary pattern-based extraction
        for keyword in keywords:
            pattern = rf"{keyword}\s*[:\-]?\s*(.*?)(?=\n\s*[A-Z][a-z]+\s*:|$)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                section_text = match.group(1).strip()
                section_text = re.sub(r'\s+', ' ', section_text)
                return section_text[:500]

        # Fallback: line-by-line style (from simpler parser), more robust for transcripts
        lines = text.splitlines()
        capture = False
        buffer: List[str] = []

        lower_headings = [h.lower() for h in keywords]

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if capture and buffer:
                    break
                continue

            # If this line starts with any of the headings, start capturing
            if any(stripped.lower().startswith(h) for h in lower_headings):
                capture = True
                parts = stripped.split(":", 1)
                if len(parts) == 2 and parts[1].strip():
                    buffer.append(parts[1].strip())
                continue

            if capture:
                # Stop when a new heading-like line appears
                if re.match(r"^[A-Z][A-Za-z\s]{1,40}:?$", stripped):
                    break
                buffer.append(stripped)

        return " ".join(buffer).strip()[:500]

    def _extract_inline_value(self, text: str, keywords: List[str]) -> str:
        """Extract single-line 'Key: Value' style fields for less structured CVs/transcripts."""
        pattern = r"(?im)^\s*(" + "|".join([re.escape(k) for k in keywords]) + r")\s*[:\-]\s*(.+)$"
        match = re.search(pattern, text)
        if match:
            return match.group(2).strip()
        return ""

    def _extract_languages(self, text: str, result: Dict[str, Any]) -> None:
        """Extract languages known."""
        # Look for language patterns
        lang_match = re.search(r"(?:Languages?|Foreign Language)[\s:]*known[\s:]*([^\n\r]+)", text, re.IGNORECASE)
        if lang_match:
            langs = re.split(r'[,;/&]', lang_match.group(1))
            for lang in langs:
                clean_lang = lang.strip()
                if clean_lang and len(clean_lang) > 1:
                    result["languages"].append(clean_lang)
    
    def _extract_publications(self, text: str, result: Dict[str, Any]) -> None:
        """Extract publications if any."""
        pub_match = re.search(r"(?:Publications?|Research Papers?|Articles)[\s:]*(.*?)(?=\n\s*[A-Z][a-z]+:|$)", text, re.IGNORECASE | re.DOTALL)
        if pub_match:
            pub_text = pub_match.group(1).strip()
            # Split by lines or bullet points
            pubs = re.split(r'\n|\r|•|·', pub_text)
            for pub in pubs:
                clean_pub = pub.strip()
                if clean_pub and len(clean_pub) > 10:
                    result["publications"].append({"title": clean_pub})
    
    def _extract_awards(self, text: str, result: Dict[str, Any]) -> None:
        """Extract awards and recognitions."""
        award_match = re.search(r"(?:Awards?|Recognitions?|Achievements?|Honors?)[\s:]*(.*?)(?=\n\s*[A-Z][a-z]+:|$)", text, re.IGNORECASE | re.DOTALL)
        if award_match:
            award_text = award_match.group(1).strip()
            # Split by lines or bullet points
            awards = re.split(r'\n|\r|•|·', award_text)
            for award in awards:
                clean_award = award.strip()
                if clean_award and len(clean_award) > 5:
                    result["awards"].append({"title": clean_award})
    
    def _extract_leadership(self, text: str, result: Dict[str, Any]) -> None:
        """Extract leadership experience."""
        leader_match = re.search(r"(?:Leadership|Team Lead|Management)[\s:]*(.*?)(?=\n\s*[A-Z][a-z]+:|$)", text, re.IGNORECASE | re.DOTALL)
        if leader_match:
            result["leadership"]["experience"] = leader_match.group(1).strip()
    
    def _convert_projects_to_experience(self, result: Dict[str, Any]) -> None:
        """Convert project experience to work experience when no work experience exists."""
        for project in result["project_experience"]:
            # Extract company from project name or client
            company = "NTT DATA GDS"  # Default
            if project.get("client"):
                # Extract company name from client field
                client_parts = project["client"].split(",")
                if len(client_parts) > 0:
                    company = client_parts[0].strip()
            
            # Extract role from project
            role = project.get("role", "System Integration Specialist")
            if "Contributions" in role:
                # Extract just the role title
                role_match = re.search(r"(System Integration|Software Engineer|ETL Developer|Sr\. Software Engineer|Analyst)", role, re.IGNORECASE)
                if role_match:
                    role = role_match.group(1)
            
            exp_entry = {
                "company_name": company,
                "designation": role,
                "start_date": project.get("start_date", ""),
                "end_date": project.get("end_date", ""),
                "responsibilities": project.get("responsibilities", [])
            }
            result["experience"].append(exp_entry)
    
    def _looks_like_name(self, line: str) -> bool:
        """Check if a line looks like a person's name."""
        if not line or len(line) > 50:
            return False
        words = line.split()
        if len(words) < 2 or len(words) > 5:
            return False
        if any(char.isdigit() for char in line):
            return False
        if '@' in line or 'http' in line.lower():
            return False
        return True
