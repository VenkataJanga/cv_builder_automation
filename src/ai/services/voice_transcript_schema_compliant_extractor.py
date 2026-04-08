"""
Voice Transcript Extractor - Schema Compliant Version
Extracts CV data from voice transcripts matching the expected JSON schema
"""

import re
from typing import Dict, List, Any


def extract_from_voice_transcript(transcript: str) -> Dict[str, Any]:
    """
    Extract structured CV data from voice transcript
    Returns data matching the expected JSON schema
    """
    text = transcript.lower()
    
    # Initialize result structure matching expected schema
    result = {
        "header": {},
        "personal_details": {},
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
    
    # Extract all sections
    result["header"] = extract_header(text)
    result["summary"] = extract_summary(text)
    result["skills"] = {
        "primary_skills": extract_primary_skills(text),
        "secondary_skills": extract_secondary_skills(text)
    }
    result["ai_frameworks"] = extract_ai_frameworks(text)
    result["cloud_platforms"] = extract_cloud_platforms(text)
    result["operating_systems"] = extract_operating_systems(text)
    result["databases"] = extract_databases(text)
    result["domain_expertise"] = extract_domains(text)
    result["employment"] = extract_employment(text)
    result["project_experience"] = extract_projects(text, transcript)
    result["education"] = extract_education(text, transcript)
    
    return result


def extract_header(text: str) -> Dict[str, Any]:
    """Extract header information"""
    header = {
        "full_name": "",
        "current_title": "",
        "location": "",
        "current_organization": "",
        "total_experience": "",
        "target_role": None,
        "email": "",
        "employee_id": "",
        "contact_number": "",
        "grade": ""
    }
    
    # Full Name
    name_match = re.search(r'my name is ([a-z\s]+?)(?:\s+my|\s+portal)', text)
    if name_match:
        header["full_name"] = name_match.group(1).strip().title()
    
    # Employee ID
    id_match = re.search(r'portal id is (\d+)', text)
    if id_match:
        header["employee_id"] = id_match.group(1)
    
    # Grade
    grade_match = re.search(r'(?:current )?grade is (\d+)', text)
    if grade_match:
        header["grade"] = grade_match.group(1)
    
    # Contact Number
    contact_match = re.search(r'(?:reach at|contact number|number is) (\d{10})', text)
    if contact_match:
        header["contact_number"] = contact_match.group(1)
    
    # Email
    email_match = re.search(r'email address is ([a-z\.]+)\s*(?:at the rate of|@)\s*(\d+)', text)
    if email_match:
        username = email_match.group(1)
        header["email"] = f"{username}@nttdata.com"
    
    # Location
    location_match = re.search(r'based in (?:the )?([a-z]+)', text)
    if location_match:
        header["location"] = location_match.group(1).title()
    
    # Organization
    org_match = re.search(r'(?:at|with) (ntt data|ntt)', text)
    if org_match:
        header["current_organization"] = "NTT Data" if "data" in org_match.group(1) else "NTT"
    
    # Experience
    exp_match = re.search(r'(\d+) years of experience', text)
    if exp_match:
        header["total_experience"] = f"{exp_match.group(1)} years"
    
    # Title
    title_match = re.search(r'current role is ([^\.]+?)(?:at|based)', text)
    if title_match:
        header["current_title"] = title_match.group(1).strip().title()
    
    return header


def extract_summary(text: str) -> str:
    """Extract professional summary"""
    parts = []
    
    # Get main expertise
    if 'specializing in' in text:
        spec_match = re.search(r'specializing in ([^\.]+?)(?:my expertise|with strong|coming to)', text)
        if spec_match:
            parts.append(f"specializing in {spec_match.group(1).strip()}")
    
    # Get expertise details
    if 'expertise span' in text:
        exp_match = re.search(r'expertise span across ([^\.]+?)(?:with strong focus|coming to)', text)
        if exp_match:
            parts.append(f"with strong expertise in {exp_match.group(1).strip()}")
    
    return ". ".join(parts) if parts else ""


def extract_primary_skills(text: str) -> List[str]:
    """Extract primary skills"""
    skills = []
    primary_match = re.search(r'primary skill(?:s)? is ([^\.]+?)(?:secondary skill|my secondary)', text)
    if primary_match:
        skills_text = primary_match.group(1)
        for skill in skills_text.split(','):
            skill = skill.strip().title()
            if skill and len(skill) > 1:
                skills.append(skill)
    return skills


def extract_secondary_skills(text: str) -> List[str]:
    """Extract secondary skills"""
    skills = []
    secondary_match = re.search(r'secondary skill(?:s)? includes ([^\.]+?)(?:i have also|i well)', text)
    if secondary_match:
        skills_text = secondary_match.group(1)
        for skill in re.split(r',|\s+and\s+', skills_text):
            skill = skill.strip().title()
            if skill and len(skill) > 1:
                skills.append(skill)
    return skills


def extract_ai_frameworks(text: str) -> List[str]:
    """Extract AI frameworks"""
    frameworks = []
    ai_match = re.search(r'ai frameworks such as ([^\.]+?)(?:i well|i am)', text)
    if ai_match:
        fw_text = ai_match.group(1)
        for fw in re.split(r'\s+and\s+', fw_text):
            fw = fw.strip().title()
            if fw and len(fw) > 1:
                frameworks.append(fw)
    return frameworks


def extract_cloud_platforms(text: str) -> List[str]:
    """Extract cloud platforms"""
    platforms = []
    if 'aws' in text:
        platforms.append("AWS")
    if 'azure' in text:
        platforms.append("Azure")
    return platforms


def extract_operating_systems(text: str) -> List[str]:
    """Extract operating systems"""
    os_list = []
    os_match = re.search(r'(?:with|versed in) (linux and windows|linux|windows) operating', text)
    if os_match:
        if 'linux' in os_match.group(1):
            os_list.append("Linux")
        if 'windows' in os_match.group(1):
            os_list.append("Windows")
    return os_list


def extract_databases(text: str) -> List[str]:
    """Extract databases"""
    databases = []
    db_match = re.search(r'database side[^\.]*?with ([^\.]+?)(?:over the course)', text)
    if db_match:
        db_text = db_match.group(1).lower()
        if 'mysql' in db_text:
            databases.append("MySQL")
        if 'postgresql' in db_text:
            databases.append("PostgreSQL")
        if 'db2' in db_text:
            databases.append("DB2")
        if 'oracle' in db_text:
            databases.append("Oracle")
    return databases


def extract_domains(text: str) -> List[str]:
    """Extract domain expertise"""
    domains = []
    domain_match = re.search(r'domains including ([^\.]+?)(?:my current|domains my)', text)
    if domain_match:
        domain_text = domain_match.group(1)
        for domain in re.split(r',|\s+and\s+', domain_text):
            domain = domain.strip().title()
            if domain and len(domain) > 2:
                domains.append(domain)
    return domains


def extract_employment(text: str) -> Dict[str, Any]:
    """Extract employment information"""
    employment = {
        "current_company": "",
        "years_with_current_company": 0,
        "clients": []
    }
    
    # Company
    comp_match = re.search(r'at (ntt data|ntt)', text)
    if comp_match:
        employment["current_company"] = "NTT Data" if "data" in comp_match.group(1) else "NTT"
    
    # Years
    years_match = re.search(r'past (\d+) years', text)
    if years_match:
        employment["years_with_current_company"] = int(years_match.group(1))
    
    # Clients
    clients_match = re.search(r'clients such as ([^\.]+?)(?:now coming)', text)
    if clients_match:
        for client in re.split(r',|\s+and\s+', clients_match.group(1)):
            client = client.strip().title()
            if client and len(client) > 1:
                employment["clients"].append(client)
    
    return employment


def extract_projects(text: str, original: str) -> List[Dict[str, Any]]:
    """Extract all projects with COMPLETE details"""
    projects = []
    
    # Find project boundaries using multiple markers
    project_markers = [
        (r'my first project', r'my second project'),
        (r'my second project', r'coming to my educational')
    ]
    
    for start_marker, end_marker in project_markers:
        start_match = re.search(start_marker, text)
        if start_match:
            start_pos = start_match.end()
            end_match = re.search(end_marker, text[start_pos:])
            if end_match:
                project_text = text[start_pos:start_pos + end_match.start()]
            else:
                project_text = text[start_pos:start_pos + 1000]  # Get substantial chunk
            
            project = extract_single_project(project_text)
            if project.get("project_name"):
                projects.append(project)
    
    return projects


def extract_single_project(text: str) -> Dict[str, Any]:
    """Extract single project with ALL fields"""
    project = {
        "project_name": "",
        "client": "",
        "domain": "",
        "technologies_used": [],
        "project_description": "",
        "role": "",
        "responsibilities": []
    }
    
    # Project Name
    name_match = re.search(r'(?:project name is|the project name is) ([^\.]+?)(?:client)', text)
    if name_match:
        project["project_name"] = name_match.group(1).strip().title()
    
    # Client
    client_match = re.search(r'client (?:is|name is) ([^\.]+?)(?:the project|project description)', text)
    if client_match:
        project["client"] = client_match.group(1).strip().title()
    
    # Project Description - get FULL description
    desc_match = re.search(r'project description is (.+?)(?:coming to my roles)', text, re.DOTALL)
    if desc_match:
        project["project_description"] = desc_match.group(1).strip()
    
    # Technologies - comprehensive extraction
    tech_keywords = {
        'jenkins': 'Jenkins', 'cicd': 'CICD', 'ci/cd': 'CICD',
        'azure': 'Azure', 'adf': 'ADF', 'adls': 'ADLS',
        'key vault': 'Key Vault', 'sql': 'SQL', 'dto': 'DTO'
    }
    for keyword, tech_name in tech_keywords.items():
        if keyword in text and tech_name not in project["technologies_used"]:
            project["technologies_used"].append(tech_name)
    
    # Responsibilities - extract ALL
    resp_section = re.search(r'roles and responsibilities[^\.]*?(?:is |:)(.+?)(?:my second project|my educational|coming to)', text, re.DOTALL)
    if resp_section:
        resp_text = resp_section.group(1)
        # Split by "I" statements
        for sentence in re.split(r'(?:^|\s)i\s+', resp_text):
            sentence = sentence.strip()
            if len(sentence) > 10:
                # Clean and capitalize
                sentence = sentence[0].upper() + sentence[1:] if sentence else sentence
                if not sentence.startswith('I'):
                    sentence = 'I ' + sentence
                project["responsibilities"].append(sentence.strip())
    
    return project


def extract_education(text: str, original: str) -> List[Dict[str, Any]]:
    """Extract ALL education entries"""
    education = []
    
    # Find education section
    edu_start = re.search(r'coming to my educational', text)
    if not edu_start:
        return education
    
    edu_text = text[edu_start.end():]
    
    # Pattern for each education level
    patterns = [
        # Master's
        (r'master of computer applications in ([^\.]+?)(?:from|at) ([^\.]+?)(?:university|the year) ([^\.]+?)(?:the year of passing is|passing is) (\d+)[^\.]*?(\d+)%', 
         'Master of Computer Applications', 'Computers'),
        # Bachelor's
        (r'bachelor of science branches computers[^\.]+?college name is ([^\.]+?)(?:at|from) ([^\.]+?)(?:university|in the year) ([^\.]+?)(?:year of|in the year of) (\d+)[^\.]*?(\d+)%',
         'Bachelor of Science', 'Computers'),
        # Intermediate
        (r'intermediate education that is 12th standard[^\.]+?branch is ([a-z]+)[^\.]+?college name is ([^\.]+?)(?:university name is|at) ([^\.]+?)(?:my percentage is|percentage is) (\d+)',
         '12th Standard', None),
        # 10th
        (r'secondary school that is 10th standard[^\.]+?school name is ([^\.]+?)(?:secondary educational board|board) year of passing (\d+)[^\.]*?(?:got |and got )(\d+)%',
         '10th Standard', 'General')
    ]
    
    # Master's degree
    master_match = re.search(r'master of computer applications in ([^\.]+?)from ([^\.]+?)university[^\.]*?year of passing is (\d+)[^\.]*?(\d+)%', edu_text)
    if master_match:
        education.append({
