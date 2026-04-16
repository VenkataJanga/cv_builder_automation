"""
Voice Transcript Production Extractor

Production-ready extractor that uses Canonical CV Schema for all audio input modes:
- Audio Upload
- Start Recording

Key Features:
1. Multiple project detection (all projects)
2. Complete skills extraction (primary, secondary, tools, OS, DB, cloud)
3. Complete education details with university and grades
4. Enhanced field extraction for all personal details
5. Integrates with SchemaMapperService for canonical format

Author: CV Builder Automation Team
Last Updated: 2026
"""

import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.domain.cv.models.canonical_cv_schema import SourceType
from src.domain.cv.services.schema_mapper_service import get_schema_mapper_service

logger = logging.getLogger(__name__)


def extract_from_voice_transcript(
    transcript: str, 
    source_type: str = "audio_upload",
    cv_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract structured CV data from voice transcript and map to Canonical CV Schema.
    
    This is the main entry point for audio-based CV extraction.
    Supports both 'audio_upload' and 'start_recording' source types.
    
    Args:
        transcript: Voice transcript text to extract from
        source_type: Type of audio input ('audio_upload' or 'start_recording')
        cv_id: Optional CV identifier
    
    Returns:
        Dictionary conforming to Canonical CV Schema (v1.1)
    
    Process Flow:
        1. Extract raw data from transcript using pattern matching
        2. Structure data in intermediate format
        3. Map to Canonical CV Schema via SchemaMapperService
        4. Return canonical format for downstream processing
    """
    logger.info(f"Starting voice transcript extraction for source_type: {source_type}")
    
    try:
        text = transcript.lower()
        
        # Step 1: Extract raw data from transcript using pattern matching
        logger.debug("Extracting raw data from transcript...")
        header_data = extract_header(text)
        summary_data = extract_summary(text)
        primary_skills = extract_primary_skills(text)
        secondary_skills = extract_secondary_skills(text)
        ai_frameworks = extract_ai_frameworks(text)
        cloud_platforms = extract_cloud_platforms(text)
        operating_systems = extract_operating_systems(text)
        databases = extract_databases(text)
        domain_expertise = extract_domains(text)
        projects = extract_all_projects(text)
        education_data = extract_all_education(text)
        experience_years, experience_months = extract_experience_years_months(text)
        
        # Step 2: Structure data in intermediate format for mapping
        logger.debug("Structuring extracted data...")
        intermediate_data = {
            # Candidate information
            "candidate": {
                "fullName": header_data.get("full_name", ""),
                "firstName": header_data.get("full_name", "").split()[0] if header_data.get("full_name") else "",
                "lastName": header_data.get("full_name", "").split()[-1] if header_data.get("full_name") and len(header_data.get("full_name", "").split()) > 1 else "",
                "email": header_data.get("email", ""),
                "phoneNumber": header_data.get("contact_number", ""),
                "portalId": header_data.get("portal_id", ""),
                "currentLocation": {
                    "city": header_data.get("location", ""),
                    "fullAddress": header_data.get("location", "")
                },
                "totalExperienceYears": experience_years,
                "totalExperienceMonths": experience_months,
                "currentOrganization": header_data.get("current_organization", ""),
                "currentDesignation": header_data.get("current_title", ""),
                "summary": summary_data,
                "grade": header_data.get("grade", "")
            },
            
            # Skills
            "skills": {
                "primarySkills": primary_skills,
                "secondarySkills": secondary_skills,
                "technicalSkills": primary_skills + secondary_skills,
                "toolsAndPlatforms": ai_frameworks,
                "operatingSystems": operating_systems,
                "databases": databases,
                "cloudTechnologies": cloud_platforms,
                "aiToolsAndFrameworks": ai_frameworks
            },
            
            # Experience
            "experience": {
                "projects": projects,
                "domainExperience": domain_expertise,
                "totalProjects": len(projects)
            },
            
            # Education
            "education": education_data,
            
            # Metadata
            "sourceType": source_type,
            "extractionTimestamp": datetime.now().isoformat()
        }
        
        # Step 3: Map to Canonical CV Schema using SchemaMapperService
        logger.debug("Mapping to Canonical CV Schema...")
        schema_mapper = get_schema_mapper_service()
        canonical_cv = schema_mapper.map_to_canonical(
            source_data=intermediate_data,
            source_type=source_type,
            cv_id=cv_id
        )
        
        logger.info(f"Successfully extracted and mapped {source_type} data to Canonical CV Schema")
        return canonical_cv
        
    except Exception as e:
        logger.error(f"Error during voice transcript extraction: {e}", exc_info=True)
        # Return empty canonical schema on error
        from src.domain.cv.models.canonical_cv_schema import create_empty_canonical_cv
        return create_empty_canonical_cv(cv_id=cv_id or "", source_type=source_type)


def extract_experience_years_months(text: str) -> tuple:
    """
    Extract total experience as years and months separately.
    
    Args:
        text: Transcript text
    
    Returns:
        Tuple of (years, months)
    
    Examples:
        "5 years" -> (5, 0)
        "3 years 6 months" -> (3, 6)
        "18 months" -> (1, 6)
    """
    years = 0
    months = 0
    
    # Try to find years
    years_match = re.search(r'(\d+)\s+years?', text)
    if years_match:
        years = int(years_match.group(1))
    
    # Try to find months
    months_match = re.search(r'(\d+)\s+months?', text)
    if months_match:
        months = int(months_match.group(1))
        # Convert excess months to years
        if months >= 12:
            years += months // 12
            months = months % 12
    
    return years, months




def extract_header(text: str) -> Dict[str, Any]:
    """Extract header information with enhanced patterns"""
    header = {
        "full_name": "",
        "current_title": "",
        "location": "",
        "current_organization": "",
        "total_experience": "",
        "target_role": None,
        "email": "",
        "employee_id": "",
        "portal_id": "",  # Add explicit portal_id field
        "contact_number": "",
        "phone": "",  # Add phone alias
        "grade": ""
    }
    
    # Full Name
    name_match = re.search(r'my name is ([a-z\s]+?)(?:\.|my portal|portal)', text)
    if name_match:
        header["full_name"] = name_match.group(1).strip().title()
    
    # Employee ID / Portal ID - Enhanced patterns
    id_patterns = [
        r'portal id is ([A-Za-z0-9]+)',
        r'employee id is ([A-Za-z0-9]+)',
        r'(?:my )?id is ([A-Za-z0-9]+)',
        r'staff id is ([A-Za-z0-9]+)'
    ]
    for pattern in id_patterns:
        id_match = re.search(pattern, text)
        if id_match:
            emp_id = id_match.group(1).strip()
            header["employee_id"] = emp_id
            header["portal_id"] = emp_id  # Duplicate for compatibility
            break
    
    # Grade
    grade_match = re.search(r'(?:current )?grade is (\d+)', text)
    if grade_match:
        header["grade"] = grade_match.group(1)
    
    # Contact Number - Enhanced patterns
    contact_patterns = [
        r'contact number is (\d{10})',
        r'contact (?:number )?is (\d{10})',
        r'phone (?:number )?is (\d{10})',
        r'mobile (?:number )?is (\d{10})',
        r'(?:call|reach) me (?:at|on) (\d{10})'
    ]
    for pattern in contact_patterns:
        contact_match = re.search(pattern, text)
        if contact_match:
            phone_num = contact_match.group(1)
            header["contact_number"] = phone_num
            header["phone"] = phone_num  # Add phone alias
            break
    
    # Email
    email_match = re.search(r'email address is ([a-z\.]+)\.ntt\.com', text)
    if email_match:
        header["email"] = f"{email_match.group(1)}@nttdata.com"
    
    # Location - Enhanced patterns
    location_patterns = [
        r'based in (?:the )?([a-z]+) location',
        r'(?:my )?location is ([a-z, ]+)',
        r'(?:from|living in|located in) ([a-z, ]+)',
        r'(?:i am|currently) in ([a-z, ]+)'
    ]
    for pattern in location_patterns:
        location_match = re.search(pattern, text)
        if location_match:
            header["location"] = location_match.group(1).strip().title()
            break
    
    # Organization - Enhanced patterns
    org_patterns = [
        r'working (?:at|with|for) ([a-z\s]+?)(?:for|since)',
        r'currently (?:at|with) ([a-z\s]+)',
        r'(?:my )?(?:company|organization) is ([a-z\s]+)'
    ]
    for pattern in org_patterns:
        org_match = re.search(pattern, text)
        if org_match:
            header["current_organization"] = org_match.group(1).strip().title()
            break
    
    # Fallback for NTT Data mentions
    if not header["current_organization"]:
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
    """Extract secondary skills - Enhanced patterns"""
    skills = []
    # Try multiple patterns for better extraction
    secondary_patterns = [
        r'secondary skill(?:s)? is ([^\.]+?)(?:\.|i have also|i well|coming to)',
        r'secondary skill(?:s)?[:\s]+([^\.]+?)(?:\.|i have also|i well|coming to)',
        r'(?:and )?secondary skills? (?:are|include) ([^\.]+?)(?:\.|i have also|i well|coming to)'
    ]
    
    for pattern in secondary_patterns:
        secondary_match = re.search(pattern, text)
        if secondary_match:
            skills_text = secondary_match.group(1)
            for skill in re.split(r',|\s+and\s+', skills_text):
                skill = skill.strip().title()
                if skill and len(skill) > 1 and skill.lower() not in ['is', 'are', 'the']:
                    skills.append(skill)
            break
    
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
    # Look for multiple patterns with broader matching
    patterns = [
        r'(?:working|experience) (?:in|with|on) (linux and windows|linux|windows) operating',
        r'(?:versed in|experience with|i have experience with) (linux and windows|linux|windows)',
        r'(linux and windows|linux|windows) operating systems',
        r'coming to operating systems[^\.]*?(linux and windows|linux|windows)'
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
    # Enhanced patterns to match various domain mentions
    patterns = [
        r'(?:my )?domains including ([^\.]+?)(?:\.|currently|my current|my first)',
        r'domain expertise[^\.]*?(?:in|include) ([^\.]+)',
        r'worked in ([^\.]+?) domain'
    ]
    
    for pattern in patterns:
        domain_match = re.search(pattern, text)
        if domain_match:
            domain_text = domain_match.group(1)
            for domain in re.split(r',|\s+and\s+', domain_text):
                domain = domain.strip().title()
                if domain and len(domain) > 1:
                    domains.append(domain)
            break
    
    return domains


def extract_employment(text: str) -> Dict[str, Any]:
    """Extract employment information"""
    return {
        "current_employer": "",
        "total_experience": ""
    }


def extract_all_projects(text: str) -> List[Dict[str, Any]]:
    """
    Extract ALL projects from transcript - FIXED
    This function now detects BOTH first and second projects
    """
    projects = []
    
    # FIRST PROJECT - Enhanced detection
    first_project_patterns = [
        r'(?:my first project|first project)[^\.]*?project name is ([^\.]+?)\..*?(?:the )?client is ([^\.]+?)\..*?role[^\.]*?([^\.]+?)\..*?duration[^\.]*?(\d+\s+\w+)',
        r'project name is ([^\.]+?)\..*?client (?:is|was) ([^\.]+?)\..*?(?:my )?role[^\.]*?([^\.]+?)\..*?duration[^\.]*?(\d+\s+\w+)'
    ]
    
    for pattern in first_project_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            project = {
                "project_name": match.group(1).strip().title(),
                "client": match.group(2).strip().title(),
                "role": match.group(3).strip().title(),
                "duration": match.group(4).strip(),
                "technologies_used": extract_project_technologies(text, "first"),
                "responsibilities": extract_project_responsibilities(text, "first")
            }
            projects.append(project)
            break
    
    # SECOND PROJECT - Enhanced detection
    second_project_patterns = [
        r'(?:my second project|second project|coming to second project)[^\.]*?project name is ([^\.]+?)\..*?(?:the )?client (?:is|was) ([^\.]+?)\..*?(?:my )?role[^\.]*?([^\.]+?)\..*?duration[^\.]*?(\d+\s+\w+)',
        r'second project[^\.]*?([^\.]+?)\..*?client (?:is|was) ([^\.]+?)\..*?role[^\.]*?([^\.]+?)\..*?(\d+\s+\w+)'
    ]
    
    for pattern in second_project_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            project = {
                "project_name": match.group(1).strip().title(),
                "client": match.group(2).strip().title(),
                "role": match.group(3).strip().title(),
                "duration": match.group(4).strip(),
                "technologies_used": extract_project_technologies(text, "second"),
                "responsibilities": extract_project_responsibilities(text, "second")
            }
            projects.append(project)
            break
    
    return projects


def extract_project_technologies(text: str, project_number: str) -> List[str]:
    """Extract technologies for a specific project"""
    technologies = []
    
    if project_number == "first":
        tech_patterns = [
            r'(?:technologies used|tech stack)[^\.]*?(?:are |include )?([^\.]+?)(?:\.|my responsibilities)',
            r'using ([^\.]+?) (?:technologies|tech stack)'
        ]
    else:  # second
        tech_patterns = [
            r'second project[^\.]*?technologies[^\.]*?([^\.]+?)(?:\.|responsibilities)',
            r'(?:in this project|for second project)[^\.]*?(?:used|using) ([^\.]+)'
        ]
    
    for pattern in tech_patterns:
        tech_match = re.search(pattern, text)
        if tech_match:
            tech_text = tech_match.group(1)
            for tech in re.split(r',|\s+and\s+', tech_text):
                tech = tech.strip().title()
                if tech and len(tech) > 1:
                    technologies.append(tech)
            break
    
    return technologies


def extract_project_responsibilities(text: str, project_number: str) -> List[str]:
    """Extract responsibilities for a specific project"""
    responsibilities = []
    
    if project_number == "first":
        resp_patterns = [
            r'(?:my )?responsibilities[^\.]*?(?:include |are )?([^\.]+?)(?:\.|coming to|second project)',
        ]
    else:  # second
        resp_patterns = [
            r'second project[^\.]*?responsibilities[^\.]*?([^\.]+?)(?:\.|coming to|education)',
        ]
    
    for pattern in resp_patterns:
        resp_match = re.search(pattern, text)
        if resp_match:
            resp_text = resp_match.group(1)
            # Split by common delimiters
            for resp in re.split(r'(?:,|\s+and\s+)', resp_text):
                resp = resp.strip()
                if resp and len(resp) > 5:
                    responsibilities.append(resp.capitalize())
            break
    
    return responsibilities


def extract_all_education(text: str) -> List[Dict[str, Any]]:
    """
    Extract ALL education details - FIXED
    Now extracts university name and grade/percentage properly
    """
    education_list = []
    
    # Pattern for bachelor's degree with university and percentage
    bachelor_patterns = [
        r"(?:bachelor'?s?|b\.?tech|btech|graduation).*?(?:from |at )?([^\.]+?university[^\.]*?)(?:in |with |, )(\d+(?:\.\d+)?)\s*(?:percent|%|percentage)",
        r"(?:bachelor'?s?|b\.?tech|btech).*?(?:from |at )?([^,\.]+?),?.*?(?:with |got |secured )?(\d+(?:\.\d+)?)\s*(?:percent|%|percentage)",
        r"graduation.*?(?:from |at )?([^\.]+?university[^\.]*?).*?(\d+(?:\.\d+)?)\s*(?:percent|%|percentage)"
    ]
    
    for pattern in bachelor_patterns:
        match = re.search(pattern, text)
        if match:
            university = match.group(1).strip().title()
            grade = match.group(2).strip()
            
            education_list.append({
                "degree": "Bachelor of Technology",
                "institution": university,
                "university": university,
                "year": extract_bachelor_year(text),
                "grade": f"{grade}%",
                "percentage": f"{grade}%"
            })
            break
    
    # Pattern for master's degree
    master_patterns = [
        r"(?:master'?s?|mtech|m\.?tech|post graduation).*?(?:from |at )?([^\.]+?university[^\.]*?)(?:in |with )(\d+(?:\.\d+)?)\s*(?:percent|%|percentage)",
        r"(?:master'?s?|mtech|m\.?tech).*?(?:from |at )?([^,\.]+?).*?(\d+(?:\.\d+)?)\s*(?:percent|%|percentage)"
    ]
    
    for pattern in master_patterns:
        match = re.search(pattern, text)
        if match:
            university = match.group(1).strip().title()
            grade = match.group(2).strip()
            
            education_list.append({
                "degree": "Master of Technology",
                "institution": university,
                "university": university,
                "year": extract_master_year(text),
                "grade": f"{grade}%",
                "percentage": f"{grade}%"
            })
            break
    
    return education_list


def extract_bachelor_year(text: str) -> str:
    """Extract bachelor's graduation year"""
    # Look for year near bachelor mention
    bachelor_year_patterns = [
        r"(?:bachelor|b\.?tech|btech|graduation).*?(?:in |year |completed in )(\d{4})",
        r"graduated.*?(?:in |year )(\d{4})",
        r"(?:completed|finished).*?graduation.*?(\d{4})"
    ]
    
    for pattern in bachelor_year_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return ""


def extract_master_year(text: str) -> str:
    """Extract master's graduation year"""
    # Look for year near master mention
    master_year_patterns = [
        r"(?:master|m\.?tech|mtech|post graduation).*?(?:in |year |completed in )(\d{4})",
        r"(?:completed|finished).*?(?:master|mtech).*?(\d{4})"
    ]
    
    for pattern in master_year_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return ""
