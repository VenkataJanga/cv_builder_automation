"""
Conversational Text Extractor

Extracts structured CV data from Bot Conversation input and maps to Canonical CV Schema.

Key Features:
1. Handles natural conversational text from users
2. Extracts all CV fields (personal details, skills, experience, education)
3. Integrates with SchemaMapperService for canonical format
4. Ensures consistency across all input modes

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


_INVALID_LOCATION_TOKENS = {
    "and",
    "na",
    "n/a",
    "none",
    "null",
    "nil",
    "unknown",
    "not available",
    "not applicable",
}


def extract_from_conversational_text(
    text: str, 
    source_type: str = "bot_conversation",
    cv_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract structured CV data from bot conversation and map to Canonical CV Schema.
    
    This is the main entry point for bot conversation-based CV extraction.
    
    Args:
        text: Natural conversational text from user
        source_type: Type of input (default: 'bot_conversation')
        cv_id: Optional CV identifier
        
    Returns:
        Dictionary conforming to Canonical CV Schema (v1.1)
    
    Process Flow:
        1. Extract raw data from conversational text using pattern matching
        2. Structure data in intermediate format
        3. Map to Canonical CV Schema via SchemaMapperService
        4. Return canonical format for downstream processing
    """
    logger.info(f"Starting conversational text extraction for source_type: {source_type}")
    
    try:
        text_lower = text.lower()
        
        # Step 1: Extract raw data from conversational text
        logger.debug("Extracting raw data from conversational text...")
        personal_details = extract_personal_details(text, text_lower)
        skills = extract_skills(text, text_lower)
        education_data = extract_education_details(text, text_lower)
        employment_data = extract_employment_details(text, text_lower)
        operating_systems = extract_operating_systems_conversational(text, text_lower)
        databases = extract_databases_conversational(text, text_lower)
        domains = extract_domains_conversational(text, text_lower)
        cloud_platforms = extract_cloud_platforms_conversational(text, text_lower)
        experience_years, experience_months = extract_experience_from_text(text_lower)
        
        # Step 2: Structure data in intermediate format for mapping
        logger.debug("Structuring extracted data...")
        intermediate_data = {
            # Candidate information
            "candidate": {
                "fullName": personal_details.get("full_name", ""),
                "firstName": personal_details.get("full_name", "").split()[0] if personal_details.get("full_name") else "",
                "lastName": personal_details.get("full_name", "").split()[-1] if personal_details.get("full_name") and len(personal_details.get("full_name", "").split()) > 1 else "",
                "email": personal_details.get("email", ""),
                "phoneNumber": personal_details.get("contact_number", ""),
                "portalId": personal_details.get("employee_id", ""),
                "currentLocation": {
                    "city": personal_details.get("location", ""),
                    "fullAddress": personal_details.get("location", "")
                },
                "totalExperienceYears": experience_years,
                "totalExperienceMonths": experience_months,
                "currentOrganization": personal_details.get("current_organization", ""),
                "currentDesignation": personal_details.get("current_title", ""),
                "summary": personal_details.get("summary", "")
            },
            
            # Skills
            "skills": {
                "primarySkills": skills.get("primary_skills", []),
                "secondarySkills": skills.get("secondary_skills", []),
                "technicalSkills": skills.get("primary_skills", []) + skills.get("secondary_skills", []),
                "toolsAndPlatforms": skills.get("tools_and_platforms", []),
                "operatingSystems": operating_systems,
                "databases": databases,
                "cloudTechnologies": cloud_platforms
            },
            
            # Experience
            "experience": {
                "domainExperience": domains,
                "workHistory": []
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
        logger.error(f"Error during conversational text extraction: {e}", exc_info=True)
        # Return empty canonical schema on error
        from src.domain.cv.models.canonical_cv_schema import create_empty_canonical_cv
        return create_empty_canonical_cv(cv_id=cv_id or "", source_type=source_type)


def extract_experience_from_text(text_lower: str) -> tuple:
    """
    Extract total experience as years and months from conversational text.
    
    Args:
        text_lower: Lowercase transcript text
    
    Returns:
        Tuple of (years, months)
    """
    years = 0
    months = 0
    
    # Try to find years
    years_patterns = [
        r'(\d+)\s+years?\s+of\s+experience',
        r'experience\s+of\s+(\d+)\s+years?',
        r'(\d+)\s+years?\s+experience'
    ]
    
    for pattern in years_patterns:
        years_match = re.search(pattern, text_lower)
        if years_match:
            years = int(years_match.group(1))
            break
    
    # Try to find months
    months_match = re.search(r'(\d+)\s+months?\s+(?:of\s+)?experience', text_lower)
    if months_match:
        months = int(months_match.group(1))
        # Convert excess months to years
        if months >= 12:
            years += months // 12
            months = months % 12
    
    return years, months


def extract_personal_details(text: str, text_lower: str) -> Dict[str, Any]:
    """
    Extract personal details from conversational text.
    
    Args:
        text: Original text (with case preserved)
        text_lower: Lowercase text for pattern matching
    
    Returns:
        Dictionary with personal details (name, phone, location, etc.)
    """
    details = {}
    
    # Full Name - multiple patterns
    name_patterns = [
        r'my name is ([a-zA-Z\s]+?)(?:\.|,|\s+my\s+|\s+i\s+)',
        r'i am ([a-zA-Z\s]+?)(?:\.|,|\s+my\s+|\s+i\s+)',
        r'name:\s*([a-zA-Z\s]+?)(?:\.|,|$)',
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, text_lower)
        if match:
            name = match.group(1).strip()
            # Clean up name (remove common words that might be captured)
            name_words = []
            for word in name.split():
                if word.lower() not in ['phone', 'number', 'portal', 'id', 'located', 'work', 'currently']:
                    name_words.append(word.title())
            if name_words:
                details["full_name"] = " ".join(name_words)
                break
    
    # Phone Number
    phone_patterns = [
        r'phone number is ([+\-\d\s\(\)]+?)(?:\.|,|\s+[a-zA-Z])',
        r'phone:\s*([+\-\d\s\(\)]+?)(?:\.|,|\s+[a-zA-Z]|$)',
        r'contact:\s*([+\-\d\s\(\)]+?)(?:\.|,|\s+[a-zA-Z]|$)',
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, text_lower)
        if match:
            phone = match.group(1).strip()
            details["contact_number"] = phone
            break
    
    # Portal/Employee ID
    id_patterns = [
        r'portal id is ([a-zA-Z0-9]+?)(?:\.|,|\s+[a-zA-Z])',
        r'employee id is ([a-zA-Z0-9]+?)(?:\.|,|\s+[a-zA-Z])',
        r'portal id:\s*([a-zA-Z0-9]+?)(?:\.|,|\s+[a-zA-Z]|$)',
        r'employee id:\s*([a-zA-Z0-9]+?)(?:\.|,|\s+[a-zA-Z]|$)',
    ]
    
    for pattern in id_patterns:
        match = re.search(pattern, text_lower)
        if match:
            emp_id = match.group(1).strip().upper()
            details["employee_id"] = emp_id
            break
    
    # Location
    location_patterns = [
        r'located in ([a-zA-Z\s,]+?)(?:\.|,|\s+i\s+|\s+my\s+)',
        r'location is ([a-zA-Z\s,]+?)(?:\.|,|\s+i\s+|\s+my\s+)',
        r'from ([a-zA-Z\s,]+?)(?:\.|,|\s+i\s+|\s+my\s+)',
        r'based in ([a-zA-Z\s,]+?)(?:\.|,|\s+i\s+|\s+my\s+)',
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, text_lower)
        if match:
            location = _sanitize_location(match.group(1))
            # Clean up location
            location = location.replace(' Ny', ', NY').replace(' Ca', ', CA')
            if location:
                details["location"] = location
                break
    
    # Current Organization
    org_patterns = [
        r'work at ([a-zA-Z\s]+?)(?:\s+as\s+|\.|,|\s+i\s+|\s+my\s+)',
        r'currently work at ([a-zA-Z\s]+?)(?:\s+as\s+|\.|,|\s+i\s+|\s+my\s+)',
        r'employed at ([a-zA-Z\s]+?)(?:\s+as\s+|\.|,|\s+i\s+|\s+my\s+)',
    ]
    
    for pattern in org_patterns:
        match = re.search(pattern, text_lower)
        if match:
            org = match.group(1).strip().title()
            if 'ntt data' in org.lower():
                org = 'NTT DATA'
            details["current_organization"] = org
            break
    
    # Current Title/Role
    title_patterns = [
        r'work at [^.]+?as a ([a-zA-Z\s]+?)(?:\.|,|\s+my\s+|\s+i\s+)',
        r'i am a ([a-zA-Z\s]+?)(?:\.|,|\s+my\s+|\s+i\s+)',
        r'role is ([a-zA-Z\s]+?)(?:\.|,|\s+my\s+|\s+i\s+)',
        r'title is ([a-zA-Z\s]+?)(?:\.|,|\s+my\s+|\s+i\s+)',
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, text_lower)
        if match:
            title = match.group(1).strip().title()
            details["current_title"] = title
            break
    
    # Experience
    exp_patterns = [
        r'(\d+)\s+years?\s+of\s+experience',
        r'experience\s+of\s+(\d+)\s+years?',
        r'(\d+)\s+years?\s+experience',
    ]
    
    for pattern in exp_patterns:
        match = re.search(pattern, text_lower)
        if match:
            years = match.group(1)
            details["total_experience"] = f"{years} years"
            break
    
    return details


def extract_skills(text: str, text_lower: str) -> Dict[str, List[str]]:
    """Extract skills from conversational text"""
    skills = {
        "primary_skills": [],
        "secondary_skills": []
    }
    
    # Primary Skills
    primary_patterns = [
        r'primary skills include ([^.]+?)(?:\.|my secondary|\s+secondary)',
        r'main skills are ([^.]+?)(?:\.|my secondary|\s+secondary)',
        r'core skills include ([^.]+?)(?:\.|my secondary|\s+secondary)',
        r'skills include ([^.]+?)(?:\.|my secondary|\s+secondary)',
    ]
    
    for pattern in primary_patterns:
        match = re.search(pattern, text_lower)
        if match:
            skills_text = match.group(1).strip()
            primary_skills = parse_skills_list(skills_text)
            skills["primary_skills"] = primary_skills
            break
    
    # Secondary Skills
    secondary_patterns = [
        r'secondary skills are ([^.]+?)(?:\.|i have|\s+i\s+|operating systems?|databases?|domain(?: expertise| experience)?|tools? and platforms?)',
        r'secondary skills include ([^.]+?)(?:\.|i have|\s+i\s+|operating systems?|databases?|domain(?: expertise| experience)?|tools? and platforms?)',
        r'supporting skills are ([^.]+?)(?:\.|i have|\s+i\s+|operating systems?|databases?|domain(?: expertise| experience)?|tools? and platforms?)',
    ]
    
    for pattern in secondary_patterns:
        match = re.search(pattern, text_lower)
        if match:
            skills_text = match.group(1).strip()
            secondary_skills = _sanitize_skill_items(parse_skills_list(skills_text))
            skills["secondary_skills"] = secondary_skills
            break
    
    return skills


def extract_education_details(text: str, text_lower: str) -> List[Dict[str, Any]]:
    """Extract education details from conversational text"""
    education = []
    
    # Look for degree mentions with university and grade
    degree_patterns = [
        r'(bachelor\'?s?\s+degree\s+in\s+[^.]+?)\s+from\s+([^.]+?)\s+with\s+(\d+%|\d+\.\d+%|\d+\s*percent)',
        r'(master\'?s?\s+degree\s+in\s+[^.]+?)\s+from\s+([^.]+?)\s+with\s+(\d+%|\d+\.\d+%|\d+\s*percent)',
        r'(bachelor\'?s?\s+degree\s+in\s+[^.]+?)\s+from\s+([^.]+?)\s+.*?completed\s+in\s+(\d{4})',
        r'(master\'?s?\s+degree\s+in\s+[^.]+?)\s+from\s+([^.]+?)\s+.*?completed\s+in\s+(\d{4})',
    ]
    
    for pattern in degree_patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            degree = match.group(1).strip().title()
            institution = match.group(2).strip().title()
            grade_or_year = match.group(3).strip()
            
            # Determine if third group is grade or year
            if grade_or_year.isdigit() and len(grade_or_year) == 4:
                year = grade_or_year
                grade = ""
            else:
                year = ""
                grade = grade_or_year
            
            education.append({
                "degree": degree,
                "institution": institution,
                "year": year,
                "grade": grade
            })
    
    return education


def extract_employment_details(text: str, text_lower: str) -> Dict[str, Any]:
    """Extract employment details from conversational text"""
    employment = {
        "current_company": "",
        "years_with_current_company": 0,
        "clients": []
    }
    
    # Current company
    if 'ntt data' in text_lower:
        employment["current_company"] = "NTT DATA"
    elif 'ntt' in text_lower:
        employment["current_company"] = "NTT"
    
    return employment


def extract_operating_systems_conversational(text: str, text_lower: str) -> List[str]:
    """Extract operating systems from conversational text"""
    os_list = []
    patterns = [
        r'operating systems?[^.]*?(linux and windows|linux|windows)',
        r'(?:experience with|familiar with|work with) (linux and windows|linux|windows)',
        r'(linux and windows|linux|windows) operating systems?'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            os_text = match.group(1).lower()
            if 'linux' in os_text and 'Linux' not in os_list:
                os_list.append("Linux")
            if 'windows' in os_text and 'Windows' not in os_list:
                os_list.append("Windows")
            break
    
    return os_list


def extract_databases_conversational(text: str, text_lower: str) -> List[str]:
    """Extract databases from conversational text"""
    databases = []
    
    # Common database names to look for
    db_mapping = {
        'mysql': 'MySQL',
        'postgresql': 'PostgreSQL', 
        'postgres': 'PostgreSQL',
        'oracle': 'Oracle',
        'sql server': 'SQL Server',
        'mongodb': 'MongoDB',
        'db2': 'DB2'
    }
    
    for db_key, db_name in db_mapping.items():
        if db_key in text_lower and db_name not in databases:
            databases.append(db_name)
    
    return databases


def extract_domains_conversational(text: str, text_lower: str) -> List[str]:
    """Extract domain expertise from conversational text"""
    domains = []
    patterns = [
        r'domain(?:s)? (?:expertise )?(?:include|are|is) ([^.]+?)(?:\.|i have|my)',
        r'worked in ([^.]*?domain[^.]*?)(?:\.|i have|my)',
        r'experience in ([^.]*?(?:healthcare|finance|retail|banking)[^.]*?)(?:\.|i have|my)',
        r'(?:it\s+is|its|it\'s)\s+having\s+([^.]+?)(?:\.|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            domain_text = match.group(1)
            for domain in re.split(r',|\s+and\s+', domain_text):
                domain = domain.strip().strip('.').strip()
                domain = re.sub(r'\betc\b', '', domain, flags=re.IGNORECASE).strip()
                domain = domain.title()
                if domain and len(domain) > 2:
                    domains.append(domain)
            break

    # Fallback: pick known domains if they appear anywhere in text.
    if not domains:
        known_domains = [
            "Healthcare",
            "Insurance",
            "Banking",
            "Finance",
            "Retail",
            "Telecom",
            "Manufacturing",
            "Pharma",
            "Energy",
            "Education",
        ]
        for domain in known_domains:
            if re.search(rf'\b{re.escape(domain.lower())}\b', text_lower):
                domains.append(domain)
    
    return domains


def extract_cloud_platforms_conversational(text: str, text_lower: str) -> List[str]:
    """Extract cloud platforms from conversational text"""
    platforms = []
    if 'aws' in text_lower or 'amazon web services' in text_lower:
        platforms.append("AWS")
    if 'azure' in text_lower:
        platforms.append("Azure")
    if 'gcp' in text_lower or 'google cloud' in text_lower:
        platforms.append("GCP")
    
    return platforms


def parse_skills_list(skills_text: str) -> List[str]:
    """Parse a comma-separated or and-separated list of skills"""
    # Replace common separators with commas
    skills_text = re.sub(r'\s+and\s+', ', ', skills_text)
    skills_text = re.sub(r'\s*,\s*', ', ', skills_text)
    
    # Split and clean
    skills = []
    for skill in skills_text.split(','):
        skill = skill.strip().rstrip('.')
        if skill and len(skill) > 1:
            # Capitalize properly
            skill = skill.title()
            # Handle special cases
            skill = skill.replace('Javascript', 'JavaScript')
            skill = skill.replace('Nodejs', 'Node.js')
            skill = skill.replace('Reactjs', 'React')
            skills.append(skill)
    
    return skills


def _sanitize_skill_items(skills: List[str]) -> List[str]:
    """Remove non-skill noise that may leak into skill lists from long dictation sentences."""
    if not skills:
        return []

    noise_markers = [
        "operating system",
        "operating systems",
        "database",
        "databases",
        "domain",
        "cloud",
        "tools and platforms",
        "tool and platform",
    ]

    cleaned = []
    for item in skills:
        text = (item or "").strip()
        if not text:
            continue
        lowered = text.lower()
        if any(marker in lowered for marker in noise_markers):
            continue
        if text not in cleaned:
            cleaned.append(text)
    return cleaned


def _sanitize_location(raw_location: str) -> str:
    """Normalize location and drop placeholder/filler values like 'and'."""
    location = (raw_location or "").strip(" ,.;:-")
    if not location:
        return ""

    lowered = location.lower().strip()
    if lowered in _INVALID_LOCATION_TOKENS:
        return ""

    # Remove common filler prefixes captured by regex in dictation.
    lowered = re.sub(r'^(and|is|in)\s+', '', lowered)
    lowered = lowered.strip(" ,.;:-")
    if not lowered or lowered in _INVALID_LOCATION_TOKENS:
        return ""

    return lowered.title()
