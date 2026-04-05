from typing import Dict, Any, List
import json
import os
import re


class TranscriptCVParser:
    """AI-powered parser for converting voice transcript text into structured CV data."""

    def __init__(self):
        self.openai_available = False
        try:
            import openai
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = openai.OpenAI(api_key=api_key)
                self.openai_available = True
        except ImportError:
            pass

    def parse(self, transcript: str) -> Dict[str, Any]:
        """Parse transcript into structured CV data using AI."""
        if not transcript or not transcript.strip():
            return self._empty_result()

        if not self.openai_available:
            print("Warning: OpenAI not available, using regex-based extraction")
            return self._regex_extract(transcript)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert CV data extraction assistant. Extract structured information from voice transcripts.

IMPORTANT RULES:
1. Extract ALL information mentioned in the transcript
2. Preserve exact names, numbers, and details
3. Handle voice-to-text errors (e.g., "at the rate" means "@")
4. Organize skills into proper categories
5. Extract complete project details including responsibilities
6. Extract all education qualifications with complete details
7. Return valid JSON only, no markdown or code blocks

Output Format:
{
  "personal_information": {
    "full_name": "Full Name",
    "portal_id": "ID",
    "grade": "Grade",
    "contact_number": "Phone",
    "email": "email@domain.com",
    "current_location": "City",
    "designation": "Title"
  },
  "professional_summary": {
    "total_experience_years": 0,
    "summary": "Professional summary text"
  },
  "skills": {
    "primary_skills": ["skill1", "skill2"],
    "secondary_skills": ["skill1", "skill2"],
    "ai_frameworks": ["framework1"],
    "cloud_platforms": ["AWS", "Azure"],
    "operating_systems": ["Windows", "Linux"],
    "databases": ["MySQL", "PostgreSQL"]
  },
  "domain_expertise": ["domain1", "domain2"],
  "employment_details": {
    "current_company": "Company Name",
    "years_with_current_company": 0,
    "clients": ["Client1", "Client2"]
  },
  "project_experience": [{
    "project_name": "Name",
    "client": "Client",
    "domain": "Domain",
    "technologies_used": ["tech1", "tech2"],
    "project_description": "Description",
    "role": "Role",
    "responsibilities": ["resp1", "resp2"]
  }],
  "certifications_and_trainings": [{
    "name": "Certification Name",
    "duration": {
      "from": "YYYY-MM-DD",
      "to": "YYYY-MM-DD"
    }
  }],
  "education": [{
    "qualification": "Degree Name",
    "specialization": "Branch/Stream",
    "college": "College Name",
    "university": "University Name",
    "year_of_passing": "YYYY",
    "percentage": "XX%"
  }]
}"""
                    },
                    {
                        "role": "user",
                        "content": f"Extract CV information from this transcript:\n\n{transcript}"
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            parsed_data = json.loads(result_text)
            
            # Ensure all required keys exist
            result = self._empty_result()
            for key in result.keys():
                if key in parsed_data:
                    result[key] = parsed_data[key]
            
            return result

        except Exception as e:
            print(f"Error parsing transcript with AI: {e}")
            return self._empty_result()

    def _regex_extract(self, transcript: str) -> Dict[str, Any]:
        """Fallback regex-based extraction when AI is not available."""
        text = transcript.lower()
        result = self._empty_result()
        
        # Extract personal information
        personal = result["personal_information"]
        
        # Name extraction
        name_patterns = [
            r"my name is ([a-z\s]+?)(?:\.|,|my|portal|contact|email|grade)",
            r"(?:i am|i'm) ([a-z\s]+?)(?:\.|,|my|portal|contact|email|grade)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                personal["full_name"] = match.group(1).strip().title()
                break
        
        # Portal ID / Employee ID
        portal_patterns = [
            r"portal id is (\d+)",
            r"employee id is (\d+)",
            r"id is (\d+)"
        ]
        for pattern in portal_patterns:
            match = re.search(pattern, text)
            if match:
                personal["portal_id"] = match.group(1)
                break
        
        # Grade
        grade_match = re.search(r"grade is (\d+)", text)
        if grade_match:
            personal["grade"] = grade_match.group(1)
        
        # Contact number
        contact_patterns = [
            r"contact number is (\d+)",
            r"phone number is (\d+)",
            r"mobile is (\d+)"
        ]
        for pattern in contact_patterns:
            match = re.search(pattern, text)
            if match:
                personal["contact_number"] = match.group(1)
                break
        
        # Email - handle "at the rate" voice-to-text
        email_patterns = [
            r"email (?:id )?is ([a-z0-9.]+) at the rate ([a-z0-9.]+)\.com",
            r"email (?:id )?is ([a-z0-9.]+)@([a-z0-9.]+)\.com"
        ]
        for pattern in email_patterns:
            match = re.search(pattern, text)
            if match:
                personal["email"] = f"{match.group(1)}@{match.group(2)}.com"
                break
        
        # Location
        location_patterns = [
            r"(?:current )?location is (?:in )?([a-z]+)",
            r"based in ([a-z]+)",
            r"working from ([a-z]+)"
        ]
        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                personal["current_location"] = match.group(1).title()
                break
        
        # Designation
        designation_patterns = [
            r"(?:current )?designation is ([a-z\s]+?)(?:\.|,|my|location|working)",
            r"working as (?:a )?([a-z\s]+?)(?:\.|,|my|location)"
        ]
        for pattern in designation_patterns:
            match = re.search(pattern, text)
            if match:
                personal["designation"] = match.group(1).strip().title()
                break
        
        # Professional summary
        exp_match = re.search(r"(\d+) years of experience", text)
        if exp_match:
            result["professional_summary"]["total_experience_years"] = int(exp_match.group(1))
        
        # Extract summary text - handle multiple formats
        summary_patterns = [
            r"professional summary[,:]? (.+?)(?:my primary|my secondary|coming to|my first|primary skill|secondary skill|$)",
            r"my professional summary[,:]? (.+?)(?:my primary|my secondary|coming to|my first|primary skill|secondary skill|$)",
            r"summary[,:]? (.+?)(?:my primary|my secondary|coming to|my first|primary skill|secondary skill|$)"
        ]
        for pattern in summary_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                summary = match.group(1).strip()
                # Clean up and capitalize
                summary = re.sub(r'\s+', ' ', summary)
                # Remove trailing incomplete sentences
                summary = summary.rstrip(',.')
                if len(summary) > 20:  # Only use if substantial
                    result["professional_summary"]["summary"] = summary[:800]  # Allow longer summaries
                    break
        
        # Extract skills
        skills = result["skills"]
        
        # Primary skills
        primary_match = re.search(r"primary skill(?:s)? (?:is|are) (.+?)(?:\.|my secondary|coming to|$)", text, re.DOTALL)
        if primary_match:
            skills_text = primary_match.group(1)
            skills["primary_skills"] = self._extract_skill_list(skills_text)
        
        # Secondary skills
        secondary_match = re.search(r"secondary skill(?:s)? (?:is|are) (.+?)(?:\.|my ai|operating system|database|coming to|$)", text, re.DOTALL)
        if secondary_match:
            skills_text = secondary_match.group(1)
            skills["secondary_skills"] = self._extract_skill_list(skills_text)
        
        # AI frameworks
        ai_match = re.search(r"ai framework(?:s)? (?:is|are) (.+?)(?:\.|operating system|database|coming to|$)", text, re.DOTALL)
        if ai_match:
            skills_text = ai_match.group(1)
            skills["ai_frameworks"] = self._extract_skill_list(skills_text)
        
        # Operating systems
        os_match = re.search(r"operating system(?:s)?(?: side)? (?:i|i'm|i am)? (?:well-versed |versed in |know )?(.+?)(?:\.|database|coming to|$)", text, re.DOTALL)
        if os_match:
            skills_text = os_match.group(1)
            skills["operating_systems"] = self._extract_skill_list(skills_text)
        
        # Databases
        db_match = re.search(r"database(?: side)? (?:i|i'm|i have)? (?:have )?(?:good )?(?:experience in |know )?(.+?)(?:\.|i worked|domains|coming to|$)", text, re.DOTALL)
        if db_match:
            skills_text = db_match.group(1)
            skills["databases"] = self._extract_skill_list(skills_text)
        
        # Cloud platforms (extract from summary or skills)
        cloud_keywords = ["aws", "azure", "gcp", "google cloud"]
        for keyword in cloud_keywords:
            if keyword in text:
                skills["cloud_platforms"].append(keyword.upper() if keyword == "aws" else keyword.title())
        
        # Domain expertise
        domain_match = re.search(r"(?:worked on )?domains? (?:in |are )?(.+?)(?:\.|currently|coming to|$)", text, re.DOTALL)
        if domain_match:
            domain_text = domain_match.group(1)
            result["domain_expertise"] = self._extract_skill_list(domain_text)
        
        # Employment details
        company_match = re.search(r"(?:worked for|working with|working at) ([a-z\s]+?)(?: for| past| since)", text)
        if company_match:
            result["employment_details"]["current_company"] = company_match.group(1).strip().upper()
        
        years_match = re.search(r"(?:for |past )(\d+) years", text)
        if years_match:
            result["employment_details"]["years_with_current_company"] = int(years_match.group(1))
        
        # Extract clients
        clients_match = re.search(r"(?:with )?clients? (?:like )?(.+?)(?:\.|now|coming to|$)", text, re.DOTALL)
        if clients_match:
            clients_text = clients_match.group(1)
            result["employment_details"]["clients"] = self._extract_skill_list(clients_text)
        
        # Extract education
        education = []
        
        # Master's degree
        masters_patterns = [
            r"(?:completed )?master(?:'s)? of ([a-z\s]+?)(?:,|\.|\sbranch)",
            r"(?:completed )?m\.?(?:sc|tech|s)\.? (?:in )?([a-z\s]+?)(?:,|\.|\sbranch)"
        ]
        for pattern in masters_patterns:
            match = re.search(pattern, text)
            if match:
                edu_entry = {
                    "qualification": f"Master of {match.group(1).strip().title()}",
                    "specialization": "Computers",
                    "college": "",
                    "university": "",
                    "year_of_passing": "",
                    "percentage": ""
                }
                # Try to find associated details
                context_start = match.start()
                context_end = min(context_start + 300, len(text))
                context = text[context_start:context_end]
                
                year_match = re.search(r"year of passing is (\d{4})", context)
                if year_match:
                    edu_entry["year_of_passing"] = year_match.group(1)
                
                college_match = re.search(r"college (?:name )?is ([a-z\s.]+?)(?:\.|university)", context)
                if college_match:
                    edu_entry["college"] = college_match.group(1).strip().upper()
                
                univ_match = re.search(r"university (?:name )?is ([a-z\s]+?)(?:\.|i got|year|$)", context)
                if univ_match:
                    edu_entry["university"] = univ_match.group(1).strip().title()
                
                education.append(edu_entry)
                break
        
        # Bachelor's degree
        bachelor_patterns = [
            r"bachelor(?:'s)? of ([a-z\s]+?)(?:,|\.|\sbranch)",
            r"b\.?(?:sc|tech|s|a|com)\.? (?:in )?([a-z\s]+?)(?:,|\.|\sbranch)"
        ]
        for pattern in bachelor_patterns:
            match = re.search(pattern, text)
            if match:
                edu_entry = {
                    "qualification": f"Bachelor of {match.group(1).strip().title()}",
                    "specialization": "Computers",
                    "college": "",
                    "university": "",
                    "year_of_passing": "",
                    "percentage": ""
                }
                # Try to find associated details
                context_start = match.start()
                context_end = min(context_start + 300, len(text))
                context = text[context_start:context_end]
                
                college_match = re.search(r"college (?:name )?is ([a-z\s.]+?)(?:\.|university)", context)
                if college_match:
                    edu_entry["college"] = college_match.group(1).strip().title()
                
                univ_match = re.search(r"university (?:name )?is ([a-z\s]+?)(?:\.|i got|year|$)", context)
                if univ_match:
                    edu_entry["university"] = univ_match.group(1).strip().title()
                
                percent_match = re.search(r"i got (?:the )?(\d+)%", context)
                if percent_match:
                    edu_entry["percentage"] = f"{percent_match.group(1)}%"
                
                education.append(edu_entry)
                break
        
        # 12th standard
        inter_match = re.search(r"(?:completed my )?12th standard", text)
        if inter_match:
            edu_entry = {
                "qualification": "12th Standard",
                "specialization": "",
                "college": "",
                "university": "",
                "year_of_passing": "",
                "percentage": ""
            }
            context_start = inter_match.start()
            context_end = min(context_start + 250, len(text))
            context = text[context_start:context_end]
            
            branch_match = re.search(r"branch is ([a-z]+)", context)
            if branch_match:
                edu_entry["specialization"] = branch_match.group(1).upper()
            
            college_match = re.search(r"college is ([a-z\s.]+?)(?:\.|university)", context)
            if college_match:
                edu_entry["college"] = college_match.group(1).strip().title()
            
            univ_match = re.search(r"university (?:name )?is ([a-z\s]+?)(?:\.|i got|year|$)", context)
            if univ_match:
                edu_entry["university"] = univ_match.group(1).strip().title()
            
            percent_match = re.search(r"i got (?:the )?(\d+)%", context)
            if percent_match:
                edu_entry["percentage"] = f"{percent_match.group(1)}%"
            
            education.append(edu_entry)
        
        # 10th standard
        tenth_match = re.search(r"(?:completed )?10th standard", text)
        if tenth_match:
            edu_entry = {
                "qualification": "10th Standard",
                "specialization": "General",
                "college": "",
                "university": "",
                "year_of_passing": "",
                "percentage": ""
            }
            context_start = tenth_match.start()
            context_end = min(context_start + 250, len(text))
            context = text[context_start:context_end]
            
            school_match = re.search(r"school (?:name )?is ([a-z\s.]+?)(?:\.|university)", context)
            if school_match:
                edu_entry["college"] = school_match.group(1).strip().upper()
            
            univ_match = re.search(r"university (?:name )?is ([a-z\s]+?)(?:\.|year|i got|$)", context)
            if univ_match:
                edu_entry["university"] = univ_match.group(1).strip().title()
            
            year_match = re.search(r"year of passing is (\d{4})", context)
            if year_match:
                edu_entry["year_of_passing"] = year_match.group(1)
            
            percent_match = re.search(r"i got (?:the )?(\d+)%", context)
            if percent_match:
                edu_entry["percentage"] = f"{percent_match.group(1)}%"
            
            education.append(edu_entry)
        
        result["education"] = education
        
        # Extract project experience
        projects = []
        
        # Find project mentions - look for patterns like "my first project", "my second project", "coming to my project"
        project_patterns = [
            r"(?:my )?(?:first|second|third|1st|2nd|3rd) project (?:is|name is) ([a-z\s]+?)(?:\.|,|current client|client is|project description)",
            r"project (?:name )?is ([a-z\s]+?)(?:\.|,|current client|client is|project description)",
            r"coming to (?:my )?project(?: details)?\s*(?:,|is)?\s*(?:my )?(?:first|second)? project (?:is )?([a-z\s]+?)(?:\.|client|project description)"
        ]
        
        # Split transcript into project sections
        project_sections = []
        
        # Find all occurrences of project mentions
        project_starts = []
        for match in re.finditer(r"(?:my |coming to (?:my )?)?(?:first|second|third|1st|2nd|3rd) project", text):
            project_starts.append(match.start())
        
        # Extract each project section
        for i, start_pos in enumerate(project_starts):
            end_pos = project_starts[i + 1] if i + 1 < len(project_starts) else len(text)
            section = text[start_pos:end_pos]
            project_sections.append(section)
        
        # If no numbered projects found, look for generic project mentions
        if not project_sections:
            # Check for patterns like "coming to my project details"
            project_detail_match = re.search(r"coming to (?:my )?project details(.+?)(?:coming to|qualifications|educational|thank you|$)", text, re.DOTALL)
            if project_detail_match:
                section = project_detail_match.group(1)
                # Try to split by project indicators
                parts = re.split(r"(?:my |the )?(?:first|second|third) project", section)
                for part in parts:
                    if len(part.strip()) > 50:
                        project_sections.append(part)
        
        # Parse each project section
        for section in project_sections:
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
            name_patterns = [
                r"project (?:is |name is )?([a-z\s]+?)(?:\.|,|current client|client)",
                r"(?:first|second|third) project (?:is )?([a-z\s]+?)(?:\.|client)"
            ]
            for pattern in name_patterns:
                match = re.search(pattern, section)
                if match:
                    project["project_name"] = match.group(1).strip().title()
                    break
            
            # Extract client
            client_patterns = [
                r"(?:current )?client is ([a-z\s]+?)(?:\.|,|my project|project description)",
                r"(?:for )?client ([a-z\s]+?)(?:\.|,|my project|project description)"
            ]
            for pattern in client_patterns:
                match = re.search(pattern, section)
                if match:
                    project["client"] = match.group(1).strip().title()
                    break
            
            # Extract domain (if mentioned in project section)
            domain_match = re.search(r"domain (?:is )?([a-z\s]+?)(?:\.|,|project)", section)
            if domain_match:
                project["domain"] = domain_match.group(1).strip().title()
            
            # Extract project description
            desc_patterns = [
                r"project description is (.+?)(?:my role|role in|role here|coming to)",
                r"description is (.+?)(?:my role|role in|role here|coming to)",
                r"(?:current client is [a-z\s]+?\. )(.+?)(?:my role|role in|role here|coming to)"
            ]
            for pattern in desc_patterns:
                match = re.search(pattern, section, re.DOTALL)
                if match:
                    desc = match.group(1).strip()
                    # Clean up description
                    desc = re.sub(r'\s+', ' ', desc)
                    # Remove "so" repetitions at start
                    desc = re.sub(r'^(?:so )+', '', desc)
                    # Remove trailing "my role" or similar
                    desc = re.sub(r'(?:my role|role in|role here|coming to).*$', '', desc, flags=re.IGNORECASE)
                    desc = desc.strip().rstrip('.')
                    if len(desc) > 30:  # Only use if substantial
                        project["project_description"] = desc[:500]  # Limit length
                        break
            
            # Extract role
            role_patterns = [
                r"my role (?:in this project )?(?:is |was )?(?:as )?(?:a )?([a-z\s]+?)(?:\.|,|i |and |developed|designed)",
                r"role (?:is |was )?(?:as )?(?:a )?([a-z\s]+?)(?:\.|,|i |and |developed|designed)",
                r"working as (?:a )?([a-z\s]+?)(?:\.|,|i |and |in this)"
            ]
            for pattern in role_patterns:
                match = re.search(pattern, section)
                if match:
                    project["role"] = match.group(1).strip().title()
                    break
            
            # Extract responsibilities (look for action verbs)
            responsibilities = []
            action_patterns = [
                r"i (developed [^\.]+)",
                r"i (designed [^\.]+)",
                r"i (created [^\.]+)",
                r"i (implemented [^\.]+)",
                r"i (deployed [^\.]+)",
                r"i (wrote [^\.]+)",
                r"i (managed [^\.]+)",
                r"i (keep tracking [^\.]+)"
            ]
            for pattern in action_patterns:
                matches = re.finditer(pattern, section)
                for match in matches:
                    resp = match.group(1).strip()
                    if resp and len(resp) > 10:
                        responsibilities.append(resp.capitalize())
            
            project["responsibilities"] = responsibilities[:10]  # Limit to 10 responsibilities
            
            # Extract technologies (look for technical terms)
            tech_keywords = ["java", "python", "pyspark", "databricks", "jenkins", "cicd", "ci/cd", 
                           "aws", "azure", "spring", "microservices", "docker", "kubernetes"]
            technologies = []
            for keyword in tech_keywords:
                if keyword in section:
                    tech_name = keyword.upper() if keyword in ["aws", "cicd", "ci/cd"] else keyword.title()
                    if tech_name not in technologies:
                        technologies.append(tech_name)
            project["technologies_used"] = technologies
            
            # Only add project if we have at least a name or description
            if project["project_name"] or project["project_description"]:
                projects.append(project)
        
        result["project_experience"] = projects
        
        return result
    
    def _extract_skill_list(self, text: str) -> List[str]:
        """Extract a list of skills from comma-separated or natural language text."""
        # Clean up the text
        text = text.strip().rstrip('.')
        
        # Split by common separators
        skills = []
        separators = [',', ' and ', '&']
        
        # Try comma-separated first
        if ',' in text:
            skills = [s.strip() for s in text.split(',') if s.strip()]
        # Try "and" separator
        elif ' and ' in text:
            skills = [s.strip() for s in text.split(' and ') if s.strip()]
        # Single skill or space-separated
        else:
            # Try to identify individual skills by capitalizing words
            skills = [text.strip()]
        
        # Clean up and capitalize each skill
        cleaned_skills = []
        for skill in skills:
            skill = skill.strip()
            if skill and len(skill) > 1:
                # Capitalize properly (handle special cases like MySQL, PostgreSQL, etc.)
                if skill.lower() in ['mysql', 'postgresql', 'mongodb', 'db2', 'nosql']:
                    skill = skill.upper() if skill.lower() == 'db2' else skill.title()
                elif skill.lower() in ['aws', 'gcp', 'ci/cd', 'cicd', 'api', 'ui', 'dto']:
                    skill = skill.upper()
                else:
                    skill = skill.title()
                cleaned_skills.append(skill)
        
        return cleaned_skills
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty CV data structure."""
        return {
            "personal_information": {
                "full_name": "",
                "portal_id": "",
                "grade": "",
                "contact_number": "",
                "email": "",
                "current_location": "",
                "designation": ""
            },
            "professional_summary": {
                "total_experience_years": 0,
                "summary": ""
            },
            "skills": {
                "primary_skills": [],
                "secondary_skills": [],
                "ai_frameworks": [],
                "cloud_platforms": [],
                "operating_systems": [],
                "databases": []
            },
            "domain_expertise": [],
            "employment_details": {
                "current_company": "",
                "years_with_current_company": 0,
                "clients": []
            },
            "project_experience": [],
            "certifications_and_trainings": [],
            "education": []
        }
