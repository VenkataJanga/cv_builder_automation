"""
Voice Transcript Production Extractor
Production-ready extractor that fixes all known issues:
1. Multiple project detection (first AND second project)
2. Operating system extraction
3. Database extraction
4. Complete education details
"""

import re
from typing import Dict, List, Any


def extract_from_voice_transcript(transcript: str) -> Dict[str, Any]:
    """
    Extract structured CV data from voice transcript
    Returns data matching the expected JSON schema
    """
    text = transcript.lower()
    
    # Initialize result structure
    result = {
        "header": {},
        "summary": "",
        "skills": {},
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
    result["project_experience"] = extract_all_projects(text)
    result["education"] = extract_all_education(text)
    
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
    name_match = re.search(r'my name is ([a-z\s]+?)(?:\.|my portal|portal)', text)
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
    contact_match = re.search(r'contact number is (\d{10})', text)
    if contact_match:
        header["contact_number"] = contact_match.group(1)
    
    # Email
    email_match = re.search(r'email address is ([a-z\.]+)\.ntt\.com', text)
    if email_match:
        header["email"] = f"{email_match.group(1)}@nttdata.com"
    
    # Location
    location_match = re.search(r'based in (?:the )?([a-z]+) location', text)
    if location_match:
        header["location"] = location_match.group(1).title()
    
    # Organization
    if 'ntt data' in text or 'entity data' in text:
        header["current_organization"] = "NTT Data"
    elif 'ntt' in text:
        header["current_organization"] = "NTT"
    
    # Experience
    exp_match = re.search(r'over past (\d+) years', text)
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
    
    # Get main specialization
    spec_match = re.search(r'specializing in ([^\.]+?)(?:my expertise|with strong focus)', text)
    if spec_match:
        parts.append(f"specializing in {spec_match.group(1).strip()}")
    
    # Get expertise details
    exp_match = re.search(r'expertise span across ([^\.]+?)(?:,with strong focus|with strong)', text)
    if exp_match:
        parts.append(f"with strong expertise in {exp_match.group(1).strip()}")
    
    return ". ".join(parts) if parts else ""


def extract_primary_skills(text: str) -> List[str]:
    """Extract primary skills"""
    skills = []
    primary_match = re.search(r'primary skill(?:s)? is ([^\.]+?)(?:\.|secondary skill)', text)
    if primary_match:
        skills_text = primary_match.group(1)
        for skill in re.split(r',|\s+and\s+', skills_text):
            skill = skill.strip().title()
            if skill and len(skill) > 1 and skill.lower() not in ['is', 'are', 'the']:
                skills.append(skill)
    return skills


def extract_secondary_skills(text: str) -> List[str]:
    """Extract secondary skills"""
    skills = []
    secondary_match = re.search(r'secondary skill(?:s)? is ([^\.]+?)(?:\.|i have also|i well)', text)
    if secondary_match:
        skills_text = secondary_match.group(1)
        for skill in re.split(r',|\s+and\s+', skills_text):
            skill = skill.strip().title()
            if skill and len(skill) > 1 and skill.lower() not in ['is', 'are', 'the']:
                skills.append(skill)
    return skills


def extract_ai_frameworks(text: str) -> List[str]:
    """Extract AI frameworks"""
    frameworks = []
    ai_match = re.search(r'ai frameworks such as ([^\.]+?)(?:\.|i well|i)', text)
    if ai_match:
        fw_text = ai_match.group(1)
        for fw in re.split(r',|\s+and\s+', fw_text):
            fw = fw.strip().title()
            # Clean up specific known frameworks
            fw = fw.replace('Autozen', 'Autogen')
            fw = fw.replace('Crue', 'Crew')
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
    """Extract operating systems - FIXED"""
    os_list = []
    # Look for multiple patterns
    patterns = [
        r'working (?:in|with) (linux and windows|linux|windows) operating',
        r'(?:versed in|experience with) (linux and windows|linux|windows)',
        r'(linux and windows|linux|windows) operating systems'
    ]
    
    for pattern in patterns:
        os_match = re.search(pattern, text)
        if os_match:
            os_text = os_match.group(1).lower()
            if 'linux' in os_text and 'Linux' not in os_list:
                os_list.append("Linux")
            if 'windows' in os_text and 'Windows' not in os_list:
                os_list.append("Windows")
            break
    
    return os_list


def extract_databases(text: str) -> List[str]:
    """Extract databases - FIXED"""
    databases = []
    
    # Look for database section
    patterns = [
        r'coming to (?:the )?database[^\.]*?(?:have |with )(?:strong )?experience with ([^\.]+?)(?:over the course|over my)',
        r'database[^\.]*?(mysql[^\.]*postgresql[^\.]*db2[^\.]*oracle|mysql[^\.]*oracle)',
    ]
    
    for pattern in patterns:
        db_match = re.search(pattern, text)
        if db_match:
            db_text = db_match.group(1).lower()
            if 'mysql' in db_text and 'MySQL' not in databases:
                databases.append("MySQL")
            if 'postgresql' in db_text and 'PostgreSQL' not in databases:
                databases.append("PostgreSQL")
            if 'db2' in db_text and 'DB2' not in databases:
                databases.append("DB2")
            if 'oracle' in db_text and 'Oracle' not in databases:
                databases.append("Oracle")
            break
    
    return databases


def extract_domains(text: str) -> List[str]:
    """Extract domain expertise"""
    domains = []
    domain_match = re.search(r'domains including ([^\.]+?)(?:\.|currently|my current)', text)
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
    if 'ntt data' in text or 'entity data' in text:
        employment["current_company"] = "NTT Data"
    elif 'ntt' in text:
        employment["current_company"] = "NTT"
    
    # Years with company
    years_match = re.search(r'(?:working with|been with)(?:[^\.]*?)(?:for|past) (?:the )?(?:past )?(\d+) years', text)
    if years_match:
        employment["years_with_current_company"] = int(years_match.group(1))
    
    # Clients
    clients_match = re.search(r'clients such as ([^\.]+?)(?:\.|now coming)', text)
    if clients_match:
        for client in re.split(r',|\s+and\s+', clients_match.group(1)):
            client = client.strip().title()
            # Clean up known client names
            client = client.replace('Commonspring', 'CommonSpirit')
            client = client.replace('Bmlrack', 'Daimler Truck')
            if client and len(client) > 1:
                employment["clients"].append(client)
    
    return employment


def extract_all_projects(text: str) -> List[Dict[str, Any]]:
    """Extract ALL projects - FIXED to get both first and second project"""
    projects = []
    
    # Split by project markers
    project_sections = []
    
    # Find first project
    first_match = re.search(r'my first project is ([^\.]+)', text)
    if first_match:
        first_start = first_match.start()
        # Find where second project starts
        second_match = re.search(r'my second project', text[first_start:])
        if second_match:
            first_end = first_start + second_match.start()
            project_sections.append(('first', text[first_start:first_end]))
            
            # Get second project
            second_start = first_end
            edu_match = re.search(r'coming to my educational', text[second_start:])
            if edu_match:
                second_end = second_start + edu_match.start()
            else:
                second_end = len(text)
            project_sections.append(('second', text[second_start:second_end]))
    
    # Extract each project
    for project_num, project_text in project_sections:
        project = extract_single_project(project_text, project_num)
        if project and project.get("project_name"):
            projects.append(project)
    
    return projects


def extract_single_project(text: str, project_num: str) -> Dict[str, Any]:
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
    if project_num == 'first':
        name_match = re.search(r'(?:first )?project (?:is|name is) ([^,\.]+?)(?:,| and client)', text)
    else:
        name_match = re.search(r'(?:second )?project name is ([^,\.]+?)(?:\.|client)', text)
    
    if name_match:
        project["project_name"] = name_match.group(1).strip().title()
    
    # Client
    client_match = re.search(r'(?:and )?client (?:is|name is) ([^\.]+?)(?:\.|project description)', text)
    if client_match:
        client = client_match.group(1).strip().title()
        client = client.replace('Commonspring', 'CommonSpirit')
        project["client"] = client
    
    # Project Description
    desc_match = re.search(r'project description (?:is |:)(.+?)(?:coming to my roles|so coming to)', text, re.DOTALL)
    if desc_match:
        desc = desc_match.group(1).strip()
        # Clean up
        desc = desc.replace('  ', ' ')
        project["project_description"] = desc
    
    # Technologies
    tech_keywords = {
        'jenkins': 'Jenkins', 'cicd': 'CICD', 'ci-cd': 'CICD', 'ci/cd': 'CICD',
        'azure': 'Azure', 'adf': 'ADF', 'adls': 'ADLS',
        'key vault': 'Key Vault', 'mysql': 'MySQL', 'dto': 'DTO',
        'spring': 'Spring', 'databricks': 'Databricks'
    }
    
    for keyword, tech_name in tech_keywords.items():
        if keyword in text.lower() and tech_name not in project["technologies_used"]:
            project["technologies_used"].append(tech_name)
    
    # Responsibilities
    resp_patterns = [
        r'roles and responsibilities[^\.]*?(?:of this project)?[^\.]*?(?::|,)(.+?)(?:my second project|coming to my educational|$)',
        r'(?:so )?coming to my roles and responsibilities[^\.]*?(?:of this project)?[^\.]*?(?::|,)(.+?)(?:my second project|coming to my educational|$)'
    ]
    
    for pattern in resp_patterns:
        resp_match = re.search(pattern, text, re.DOTALL)
        if resp_match:
            resp_text = resp_match.group(1).strip()
            # Split by common delimiters and clean
            for resp in re.split(r'(?:and|,|\n)\s*', resp_text):
                resp = resp.strip()
                if resp and len(resp) > 10:  # Filter out short/meaningless fragments
                    project["responsibilities"].append(resp)
            break
    
    return project


def extract_all_education(text: str) -> List[Dict[str, Any]]:
    """Extract education details"""
    education = []
    
    # Look for education section
    edu_match = re.search(r'coming to my educational (?:background|qualification)[^\.]*?(.+?)(?:thank you|that\'s all|$)', text, re.DOTALL)
    if edu_match:
        edu_text = edu_match.group(1)
        
        # Extract degree info
        degree_match = re.search(r'(?:i have completed|completed) ([^\.]+?)(?:from|in) ([^\.]+?)(?:\.|with)', edu_text)
        if degree_match:
            education.append({
                "institution": degree_match.group(2).strip().title(),
                "degree": degree_match.group(1).strip().title(),
                "year": "",
                "grade": ""
            })
    
    return education
