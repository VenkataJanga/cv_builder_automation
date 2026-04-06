import re
from typing import Dict, Any, List, Optional


class TranscriptCVParser:
    """
    Comprehensive transcript parser for voice-based CV input.
    Extracts structured CV data from natural language voice transcripts.
    FIXED VERSION - Addresses all known extraction issues
    """
    
    def parse(self, transcript: str) -> Dict[str, Any]:
        """Parse a voice transcript into structured CV data"""
        result: Dict[str, Any] = {
            "header": {},
            "summary": "",
            "skills": [],
            "secondary_skills": [],
            "tools_and_platforms": [],
            "ai_frameworks": [],
            "cloud_platforms": [],
            "operating_systems": [],
            "databases": [],
            "domain_expertise": [],
            "employment": {},
            "leadership": {},
            "work_experience": [],
            "project_experience": [],
            "certifications": [],
            "education": [],
            "publications": [],
            "awards": [],
            "languages": [],
            "schema_version": "1.0"
        }

        if not transcript.strip():
            return result

        # Extract each section
        result["header"] = self._extract_header(transcript)
        result["skills"] = self._extract_primary_skills(transcript)
        result["secondary_skills"] = self._extract_secondary_skills(transcript)
        result["ai_frameworks"] = self._extract_ai_frameworks(transcript)
        result["cloud_platforms"] = self._extract_cloud_platforms(transcript)
        result["operating_systems"] = self._extract_operating_systems(transcript)
        result["databases"] = self._extract_databases(transcript)
        result["domain_expertise"] = self._extract_domains(transcript)
        result["employment"] = self._extract_employment(transcript)
        result["project_experience"] = self._extract_projects(transcript)
        result["education"] = self._extract_education(transcript)
        result["summary"] = self._generate_summary(result)

        return result

    def low_confidence(self, parsed: Dict[str, Any]) -> bool:
        """Check if parsing confidence is low"""
        header = parsed.get("header", {})
        has_name = bool(header.get("full_name"))
        has_skills = bool(parsed.get("skills") or parsed.get("secondary_skills"))
        return not (has_name and has_skills)

    def _extract_header(self, text: str) -> Dict[str, Any]:
        """Extract header/personal information - FIXED VERSION"""
        header = {
            "full_name": "",
            "current_title": "",
            "location": "",
            "current_organization": "NTT",
            "total_experience": "",
            "target_role": None,
            "email": "",
            "employee_id": "",
            "contact_number": "",
            "grade": ""
        }

        # Extract name
        name_match = re.search(
            r"(?:my name is|i am|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})",
            text,
            re.IGNORECASE
        )
        if name_match:
            header["full_name"] = name_match.group(1).strip()

        # Extract portal ID / employee ID
        portal_match = re.search(r"portal\s+id\s+is\s+(\d+)", text, re.IGNORECASE)
        if portal_match:
            header["employee_id"] = portal_match.group(1)

        # Extract grade
        grade_match = re.search(r"(?:current\s+)?grade\s+is\s+(\d+)", text, re.IGNORECASE)
        if grade_match:
            header["grade"] = grade_match.group(1)

        # FIXED: Extract contact number - handle various formats
        contact_patterns = [
            r"contact\s+number\s+is\s+([\d\-]{10,})",  # With dashes
            r"contact\s+number\s+is\s+(\d{3})\-(\d{3})\-(\d{4})",  # XXX-XXX-XXXX
            r"contact\s+number\s+is\s+(\d{10,})",  # Plain digits
            r"reach\s+at[,\s]+or\s+my\s+contact\s+number\s+is\s+([\d\-]+)",  # Alternative phrasing
        ]
        
        for pattern in contact_patterns:
            contact_match = re.search(pattern, text, re.IGNORECASE)
            if contact_match:
                # Get all captured groups
                if len(contact_match.groups()) > 1:
                    # Multiple groups (e.g., XXX-XXX-XXXX)
                    header["contact_number"] = "".join(contact_match.groups())
                else:
                    # Single group
                    number = contact_match.group(1).replace("-", "").replace(" ", "")
                    header["contact_number"] = number
                break

        # Extract email
        email_match = re.search(r"email\s+(?:address\s+)?is\s+([\w\.\-]+@[\w\.\-]+)", text, re.IGNORECASE)
        if email_match:
            header["email"] = email_match.group(1).strip()
        else:
            # Try without @ symbol (voice recognition issue)
            email_match2 = re.search(r"email\s+(?:address\s+)?is\s+([\w\.]+\.com)", text, re.IGNORECASE)
            if email_match2:
                email = email_match2.group(1).strip()
                # Add @nttdata if missing
                if "@" not in email:
                    email = email.replace(".com", "@nttdata.com")
                header["email"] = email

        # FIXED: Extract location - look in multiple places
        location_patterns = [
            r"based\s+in\s+the\s+([A-Za-z]+)\s+location",
            r"location\s+is\s+([A-Za-z]+)",
            r"based\s+in\s+([A-Za-z]+)",
        ]
        
        for pattern in location_patterns:
            location_match = re.search(pattern, text, re.IGNORECASE)
            if location_match:
                header["location"] = location_match.group(1).strip().title()
                break

        # FIXED: Extract years of experience - multiple patterns
        exp_patterns = [
            r"over\s+past\s+(\d+)\s+years",
            r"(\d+)\s+years\s+(?:of\s+)?experience",
            r"(\d+)\s+years\s+in\s+the\s+IT",
        ]
        
        for pattern in exp_patterns:
            exp_match = re.search(pattern, text, re.IGNORECASE)
            if exp_match:
                header["total_experience"] = f"{exp_match.group(1)} years"
                break

        # FIXED: Extract designation/title
        desig_patterns = [
            r"current\s+role\s+is\s+([A-Z][A-Za-z\s]+?)(?:\s+at\s+|\.)",
            r"designation\s+is\s+([A-Za-z\s]+?)(?:\.|,|\s+at\s+)",
        ]
        
        for pattern in desig_patterns:
            desig_match = re.search(pattern, text, re.IGNORECASE)
            if desig_match:
                title = desig_match.group(1).strip()
                if len(title) > 3:
                    header["current_title"] = title
                    break

        return header

    def _extract_primary_skills(self, text: str) -> List[str]:
        """Extract primary skills"""
        skills = []
        
        # Look for primary skill markers
        match = re.search(
            r"primary\s+skill(?:s)?\s+(?:is|are)\s+([^.]+?)(?:\.|my\s+secondary|coming\s+to)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if match:
            skill_text = match.group(1)
            # Split by commas and 'and'
            parts = re.split(r',|\s+and\s+', skill_text)
            for part in parts:
                skill = part.strip()
                # Remove trailing periods or extra words
                skill = re.sub(r'\.$', '', skill)
                skill = re.sub(r'\s+(?:and|or)\s*$', '', skill, flags=re.IGNORECASE)
                
                if skill and len(skill) > 2:
                    skills.append(skill)
        
        return skills

    def _extract_secondary_skills(self, text: str) -> List[str]:
        """Extract secondary skills"""
        skills = []
        
        match = re.search(
            r"secondary\s+skill(?:s)?\s+(?:is|are)\s+([^.]+?)(?:\.|i\s+have\s+also|coming\s+to)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if match:
            skill_text = match.group(1)
            parts = re.split(r',|\s+and\s+', skill_text)
            for part in parts:
                skill = part.strip()
                skill = re.sub(r'\.$', '', skill)
                
                if skill and len(skill) > 2:
                    skills.append(skill)
        
        return skills

    def _extract_ai_frameworks(self, text: str) -> List[str]:
        """Extract AI frameworks - FIXED VERSION"""
        frameworks = []
        
        # Multiple patterns to catch AI frameworks
        patterns = [
            r"(?:hands[\-\s]on\s+)?experience\s+in\s+ai\s+frameworks?\s+such\s+as\s+([^.]+?)(?:\.|i\s+(?:well|am)|coming\s+to)",
            r"ai\s+frameworks?\s+(?:like|such\s+as)\s+([^.]+?)(?:\.|coming\s+to)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                fw_text = match.group(1)
                # Split by 'and' and commas
                parts = re.split(r',|\s+and\s+', fw_text)
                for part in parts:
                    fw = part.strip()
                    # Clean up
                    fw = re.sub(r'\s+frameworks?$', '', fw, flags=re.IGNORECASE)
                    fw = re.sub(r'\.$', '', fw)
                    
                    if fw and len(fw) > 2 and 'framework' not in fw.lower():
                        frameworks.append(fw.title())
                break
        
        return frameworks

    def _extract_cloud_platforms(self, text: str) -> List[str]:
        """Extract cloud platforms"""
        platforms = []
        
        # Look for explicit cloud mentions
        cloud_keywords = ['AWS', 'Azure', 'GCP', 'Google Cloud', 'IBM Cloud']
        text_upper = text.upper()
        
        for keyword in cloud_keywords:
            if keyword.upper() in text_upper:
                platforms.append(keyword)
        
        return platforms

    def _extract_operating_systems(self, text: str) -> List[str]:
        """Extract operating systems - FIXED VERSION"""
        os_list = []
        
        # Multiple patterns to catch OS mentions
        patterns = [
            r"(?:well\s+versed\s+)?working\s+in\s+([^.]+?)\s+operating\s+systems?",
            r"operating\s+systems?\s+(?:like|such\s+as)\s+([^.]+?)(?:\.|coming\s+to)",
            r"(?:experience\s+in|worked\s+on)\s+([^.]+?)\s+(?:and\s+)?(?:windows|linux)\s+operating\s+systems?",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                os_text = match.group(1)
                # Split by 'and'
                parts = re.split(r'\s+and\s+', os_text)
                for part in parts:
                    os_name = part.strip()
                    os_name = re.sub(r'\.$', '', os_name)
                    
                    if os_name and len(os_name) > 2:
                        os_list.append(os_name.title())
                break
        
        return os_list

    def _extract_databases(self, text: str) -> List[str]:
        """Extract databases - FIXED VERSION"""
        databases = []
        
        # Multiple patterns to catch database mentions
        patterns = [
            r"coming\s+to\s+the\s+database,?\s+i\s+have\s+strong\s+experience\s+with\s+([^.]+?)(?:\s+over\s+the\s+course|\.|$)",
            r"database\s+(?:side|experience)[,\s]+i\s+have\s+(?:good|strong)\s+experience\s+(?:with|in)\s+([^.]+?)(?:\.|over\s+the|coming\s+to)",
            r"databases?\s+(?:like|such\s+as|are)\s+([^.]+?)(?:\.|coming\s+to)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                db_text = match.group(1)
                # Split by commas and 'and'
                parts = re.split(r',|\s+and\s+', db_text)
                for part in parts:
                    db = part.strip()
                    db = re.sub(r'\.$', '', db)
                    
                    # Filter out filler words
                    if (db and len(db) > 2 and 
                        'experience' not in db.lower() and 
                        'strong' not in db.lower() and
                        'good' not in db.lower()):
                        
                        # Standardize common database names
                        if 'mysql' in db.lower():
                            db = 'MySQL'
                        elif 'postgres' in db.lower() or 'postgresql' in db.lower():
                            db = 'PostgreSQL'
                        elif db.upper() in ['DB2', 'ORACLE']:
                            db = db.upper()
                        else:
                            db = db.title()
                        
                        databases.append(db)
                break
        
        return databases

    def _extract_domains(self, text: str) -> List[str]:
        """Extract domain expertise"""
        domains = []
        
        # Look for "worked on domains" pattern
        match = re.search(
            r"worked\s+on\s+domains?,?\s+([^.]+?)(?:\.|currently|my\s+designation)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if match:
            domain_text = match.group(1)
            # Split by commas and 'and'
            parts = re.split(r',|\s+and\s+', domain_text)
            for part in parts:
                domain = part.strip()
                if domain and len(domain) > 3:
                    domains.append(domain.title())
        
        return domains

    def _extract_employment(self, text: str) -> Dict[str, Any]:
        """Extract employment information - FIXED VERSION"""
        employment = {
            "current_company": "NTT",
            "years_with_current_company": 0,
            "clients": []
        }
        
        # Extract years with company
        years_match = re.search(
            r"(?:worked\s+for\s+[\w\s]+\s+for\s+(?:first\s+)?(\d+)\s+years)",
            text,
            re.IGNORECASE
        )
        if years_match:
            employment["years_with_current_company"] = int(years_match.group(1))
        
        # FIXED: Extract clients - multiple patterns
        client_patterns = [
            r"worked\s+with\s+(?:key\s+)?clients?\s+(?:like|such\s+as)\s+([^.]+?)(?:\.|coming\s+to)",
            r"clients?\s+(?:include|are)\s+([^.]+?)(?:\.|coming\s+to)",
        ]
        
        for pattern in client_patterns:
            clients_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if clients_match:
                client_text = clients_match.group(1)
                parts = re.split(r',|\s+and\s+', client_text)
                for part in parts:
                    client = part.strip()
                    client = re.sub(r'\.$', '', client)
                    
                    if client and len(client) > 2:
                        employment["clients"].append(client.title())
                break
        
        return employment

    def _extract_projects(self, text: str) -> List[Dict[str, Any]]:
        """Extract project experience - FIXED VERSION"""
        projects = []
        
        # FIXED: Better project splitting - capture ALL projects
        # Look for project markers: "first project", "second project", etc.
        project_markers = [
            r"my\s+first\s+project\s+is",
            r"my\s+second\s+project\s+is",
            r"my\s+third\s+project\s+is",
            r"my\s+next\s+project\s+is",
        ]
        
        # Find all project positions
        project_positions = []
        for marker in project_markers:
            for match in re.finditer(marker, text, re.IGNORECASE):
                project_positions.append(match.start())
        
        # Sort positions
        project_positions.sort()
        
        # Extract each project section
        for i, start_pos in enumerate(project_positions):
            # Determine end position (start of next project or end of text)
            if i + 1 < len(project_positions):
                end_pos = project_positions[i + 1]
            else:
                # Last project - find "educational qualifications" or end
                edu_match = re.search(r"coming\s+to\s+(?:my\s+)?educational", text[start_pos:], re.IGNORECASE)
                end_pos = start_pos + edu_match.start() if edu_match else len(text)
            
            section = text[start_pos:end_pos]
            
            project = {
                "project_name": "",
                "client": "",
                "domain": "",
                "technologies_used": [],
                "project_description": "",
                "role": "",
                "responsibilities": []
            }
            
            # Extract project name
            name_match = re.search(r"project\s+is\s+([^.,]+?)(?:\.|,|\s+client)", section, re.IGNORECASE)
            if name_match:
                project["project_name"] = name_match.group(1).strip().title()
            
            # FIXED: Extract client - better pattern
            client_match = re.search(r"client\s+is\s+([^.,]+?)(?:\.|,|\s+the\s+project|\s+my\s+project)", section, re.IGNORECASE)
            if client_match:
                client = client_match.group(1).strip()
                client = re.sub(r'\s+and$', '', client)  # Remove trailing 'and'
                project["client"] = client.title()
            
            # FIXED: Extract project description - comprehensive approach
            desc_patterns = [
                r"project\s+description\s+(?:here\s+)?is\s+(.+?)(?:coming\s+to\s+my\s+role|my\s+role|roles?\s+and\s+responsibilit)",
                r"(?:client\s+is\s+[^.]+?\.\s+)?(.+?)(?:coming\s+to\s+my\s+role|my\s+role|roles?\s+and\s+responsibilit)",
            ]
            
            for pattern in desc_patterns:
                desc_match = re.search(pattern, section, re.IGNORECASE | re.DOTALL)
                if desc_match:
                    description = desc_match.group(1).strip()
                    # Clean up
                    description = re.sub(r'\s+', ' ', description)
                    description = re.sub(r'\s*\.\s*$', '', description)
                    description = re.sub(r'here\s+is\s+the\s+', '', description, flags=re.IGNORECASE)
                    
                    # Only use if it's a real description
                    if len(description) > 30 and 'my role' not in description.lower():
                        project["project_description"] = description
                        break
            
            # FIXED: Extract role
            role_patterns = [
                r"my\s+role\s+is\s+([^.,]+?)(?:\.|,)",
                r"roles?\s+and\s+responsibilit[iy]+.*?i\s+am\s+(?:a\s+)?([^.,]+?)(?:\.|,)",
            ]
            
            for pattern in role_patterns:
                role_match = re.search(pattern, section, re.IGNORECASE)
                if role_match:
                    role_text = role_match.group(1).strip()
                    if len(role_text) > 3 and 'responsibilit' not in role_text.lower():
                        project["role"] = role_text.title()
                        break
            
            # FIXED: Extract responsibilities - better parsing
            resp_patterns = [
                r"responsibilit(?:ies|y)[^.]*?[,:]\s*(.+?)(?:my\s+(?:second|third|next)\s+project|coming\s+to\s+my\s+educational|$)",
                r"my\s+(?:main\s+)?responsibilit(?:ies|y)\s+(?:are|include)\s+(.+?)(?:my\s+(?:second|third)\s+project|coming\s+to|$)",
            ]
            
            for pattern in resp_patterns:
                resp_match = re.search(pattern, section, re.IGNORECASE | re.DOTALL)
                if resp_match:
                    resp_text = resp_match.group(1)
                    # Split by sentences or major delimiters
                    resp_parts = re.split(r'(?:\.|\s+and\s+i\s+|\s+i\s+also\s+)', resp_text)
                    for resp in resp_parts:
                        resp_clean = resp.strip()
                        resp_clean = re.sub(r'\s+', ' ', resp_clean)
                        
                        if resp_clean and len(resp_clean) > 10 and 'project' not in resp_clean.lower():
                            project["responsibilities"].append(resp_clean)
                    break
            
            # Extract technologies
            tech_keywords = ['Jenkins', 'CICD', 'CI/CD', 'Azure', 'AWS', 'Docker', 'Kubernetes',
                           'Python', 'Java', 'Spring', 'React', 'Angular', 'Databricks', 'Spark',
                           'Terraform', 'Git', 'Linux', 'Windows']
            for keyword in tech_keywords:
                if keyword.lower() in section.lower():
                    if keyword not in project["technologies_used"]:
                        project["technologies_used"].append(keyword)
            
            if project["project_name"]:
                projects.append(project)
        
        return projects

    def _extract_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract education details - FIXED VERSION"""
        education = []
        
        # Look for educational qualifications section
        edu_match = re.search(
            r"(?:coming\s+to\s+)?(?:my\s+)?educational\s+qualifications?(.+?)(?:thank\s+you|$)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if not edu_match:
            return education
        
        edu_text = edu_match.group(1)
        
        # FIXED: Extract Master's degree with better pattern matching
        master_patterns = [
            r"completed\s+(?:a\s+)?master(?:'s)?\s+(?:degree\s+)?in\s+computer\s+applications.*?branch\s+is\s+([^.,]+)[.,].*?(?:year|passing).*?(\d{4}).*?college.*?is\s+([^.,]+)[.,].*?university.*?is\s+([^.,]+)[.,].*?(?:i\s+got|percentage|marks).*?(\d+)",
            r"first.*?master.*?computer\s+applications.*?branch[:\s]+([^.,]+).*?college[:\s]+([^.,]+).*?university[:\s]+([^.,]+).*?year.*?(\d{4}).*?(\d+)\s*%",
        ]
        
        for pattern in master_patterns:
            master_match = re.search(pattern, edu_text, re.IGNORECASE | re.DOTALL)
            if master_match:
                groups = master_match.groups()
                education.append({
                    "qualification": "Master's Degree (MCA)",
                    "specialization": groups[0].strip().title() if groups[0] else "",
                    "college": groups[2].strip() if len(groups) > 2 else groups[1].strip(),
                    "university": groups[3].strip() if len(groups) > 3 else groups[2].strip(),
                    "year_of_passing": groups[1].strip() if len(groups) > 4 else groups[3].strip(),
                    "percentage": f"{groups[4].strip() if len(groups) > 4 else groups[4].strip()}%"
                })
                break
        
        # FIXED: Extract Bachelor's degree
        bachelor_patterns = [
            r"(?:second|bachelor).*?bachelor(?:'s)?\s+of\s+science.*?branch\s+is\s+([^.,]+)[.,].*?college.*?is\s+([^.,]+)[.,].*?university.*?is\s+([^.,]+)[.,].*?(?:i\s+got|percentage).*?(\d+)",
            r"bachelor.*?(?:science|engineering).*?branch[:\s]+([^.,]+).*?college[:\s]+([^.,]+).*?university[:\s]+([^.,]+).*?(\d+)\s*%",
        ]
        
        for pattern in bachelor_patterns:
            bachelor_match = re.search(pattern, edu_text, re.IGNORECASE | re.DOTALL)
            if bachelor_match:
                groups = bachelor_match.groups()
                education.append({
                    "qualification": "Bachelor's Degree (B.Sc)",
                    "specialization": groups[0].strip().title(),
                    "college": groups[1].strip(),
                    "university": groups[2].strip(),
                    "year_of_passing": "",
                    "percentage": f"{groups[3].strip()}%"
                })
                break
        
        # FIXED: Extract 12th standard
        twelfth_patterns = [
            r"(?:before|third).*?12th\s+standard.*?branch\s+is\s+([^.,]+)[.,].*?college.*?is\s+([^.,]+)[.,].*?university.*?is\s+([^.,]+)[.,].*?(?:i\s+got|percentage).*?(\d+)",
            r"12th.*?branch[:\s]+([^.,]+).*?college[:\s]+([^.,]+).*?university[:\s]+([^.,]+).*?(\d+)\s*%",
        ]
        
        for pattern in twelfth_patterns:
            twelfth_match = re.search(pattern, edu_text, re.IGNORECASE | re.DOTALL)
            if twelfth_match:
                groups = twelfth_match.groups()
                education.append({
                    "qualification": "12th Standard (Intermediate)",
                    "specialization": groups[0].strip().upper(),
                    "college": groups[1].strip(),
                    "university": groups[2].strip(),
                    "year_of_passing": "",
                    "percentage": f"{groups[3].strip()}%"
                })
                break
        
        # FIXED: Extract 10th standard
        tenth_patterns = [
            r"(?:last|10th).*?10th\s+standard.*?(?:school|college).*?is\s+([^.,]+)[.,].*?university.*?is\s+([^.,]+)[.,].*?(?:passing\s+)?year.*?(\d{4})",
            r"10th.*?school[:\s]+([^.,]+).*?university[:\s]+([^.,]+).*?year[:\s]+(\d{4})",
        ]
        
        for pattern in tenth_patterns:
            tenth_match = re.search(pattern, edu_text, re.IGNORECASE | re.DOTALL)
            if tenth_match:
                groups = tenth_match.groups()
                education.append({
                    "qualification": "10th Standard (SSC)",
                    "specialization": "",
                    "college": groups[0].strip(),
                    "university": groups[1].strip(),
                    "year_of_passing": groups[2].strip(),
                    "percentage": ""
                })
                break
        
        return education

    def _generate_summary(self, parsed_data: Dict[str, Any]) -> str:
        """Generate professional summary from parsed data"""
        summary_parts = []
        
        header = parsed_data.get("header", {})
        name = header.get("full_name", "")
        experience = header.get("total_experience", "")
        title = header.get("current_title", "")
        
        # Build comprehensive summary
        if name and experience:
            summary_parts.append(f"{name} is a seasoned IT professional with {experience} of experience")
        
        # Add technology expertise
        skills = parsed_data.get("skills", [])
        secondary_skills = parsed_data.get("secondary_skills", [])
        all_skills = skills + secondary_skills[:3]  # Include some secondary skills
        
        if all_skills:
            skill_str = ", ".join(all_skills[:5])
            summary_parts.append(f"specializing in developing, deploying and providing operational support for enterprise applications using {skill_str}")
        
        # Add cloud platforms
        cloud = parsed_data.get("cloud_platforms", [])
        if cloud:
            cloud_str = ", ".join(cloud)
            summary_parts.append(f"with strong expertise in {cloud_str} cloud services")
        
        # Add domains
        domains = parsed_data.get("domain_expertise", [])
        if domains:
            domain_str = ", ".join(domains[:4])
            summary_parts.append(f"Experience spans across {domain_str} domains")
        
        # Add current role
        if title:
            summary_parts.append(f"Currently serving as {title}")
        
        # Join all parts
        if summary_parts:
            summary = ". ".join(summary_parts)
            if not summary.endswith("."):
                summary += "."
            return summary
        
        return ""
