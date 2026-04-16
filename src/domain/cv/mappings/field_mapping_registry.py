"""
Field Mapping Registry

Centralized registry for mapping extractor outputs to Canonical CV Schema fields.
Supports all 4 input modes: Audio Upload, Bot Conversation, Start Recording, DOCX/PDF.

This module defines how each extractor's output should map to canonical schema fields.
"""

from typing import Dict, Any, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# MAPPING CONFIGURATION TYPES
# ============================================================================

class FieldMappingRule:
    """
    Represents a mapping rule from source field to canonical field.
    
    Attributes:
        source_path: Path in source data (e.g., "contact.phone")
        canonical_path: Path in canonical schema (e.g., "candidate.phoneNumber")
        transform_fn: Optional transformation function
        default_value: Default value if source is missing
        is_mandatory: Whether field is required for validation
    """
    
    def __init__(
        self,
        source_path: str,
        canonical_path: str,
        transform_fn: Optional[Callable] = None,
        default_value: Any = None,
        is_mandatory: bool = False
    ):
        self.source_path = source_path
        self.canonical_path = canonical_path
        self.transform_fn = transform_fn
        self.default_value = default_value
        self.is_mandatory = is_mandatory


# ============================================================================
# TRANSFORMATION FUNCTIONS
# ============================================================================

def transform_location(location_data: Any) -> Dict[str, str]:
    """
    Transform location data to canonical format.
    
    Handles various input formats:
    - String: "Mumbai, India"
    - Dict: {"city": "Mumbai", "country": "India"}
    - Dict with fullAddress: {"fullAddress": "Mumbai, Maharashtra, India"}
    """
    if isinstance(location_data, str):
        # Parse string format
        parts = [p.strip() for p in location_data.split(',')]
        return {
            "city": parts[0] if len(parts) > 0 else "",
            "state": parts[1] if len(parts) > 2 else "",
            "country": parts[-1] if len(parts) > 1 else "",
            "fullAddress": location_data
        }
    elif isinstance(location_data, dict):
        return {
            "city": location_data.get("city", ""),
            "state": location_data.get("state", ""),
            "country": location_data.get("country", ""),
            "fullAddress": location_data.get("fullAddress", "")
        }
    return {"city": "", "state": "", "country": "", "fullAddress": ""}


def transform_experience_duration(duration_str: str) -> Dict[str, int]:
    """
    Transform experience duration string to years and months.
    
    Examples:
        "5 years 6 months" -> {"years": 5, "months": 6}
        "3.5 years" -> {"years": 3, "months": 6}
        "18 months" -> {"years": 1, "months": 6}
    """
    years = 0
    months = 0
    
    if not duration_str:
        return {"years": 0, "months": 0}
    
    duration_str = duration_str.lower()
    
    # Extract years
    if "year" in duration_str:
        try:
            year_part = duration_str.split("year")[0].strip().split()[-1]
            years = int(float(year_part))
            # Handle decimal years
            if '.' in year_part:
                decimal_part = float(year_part) - years
                months += int(decimal_part * 12)
        except (ValueError, IndexError):
            pass
    
    # Extract months
    if "month" in duration_str:
        try:
            month_part = duration_str.split("month")[0].strip().split()[-1]
            if "year" not in month_part:
                months += int(month_part)
        except (ValueError, IndexError):
            pass
    
    # Normalize months to years if >= 12
    if months >= 12:
        years += months // 12
        months = months % 12
    
    return {"years": years, "months": months}


def transform_skills_list(skills_data: Any) -> List[str]:
    """
    Transform skills data to list format.
    
    Handles:
    - Comma-separated string: "Python, Java, SQL"
    - List: ["Python", "Java", "SQL"]
    - Dict with categories: {"primary": ["Python"], "secondary": ["Java"]}
    """
    if isinstance(skills_data, str):
        return [s.strip() for s in skills_data.split(',') if s.strip()]
    elif isinstance(skills_data, list):
        return [str(s).strip() for s in skills_data if s]
    elif isinstance(skills_data, dict):
        # Flatten all skill categories
        all_skills = []
        for key, value in skills_data.items():
            if isinstance(value, list):
                all_skills.extend(value)
            elif isinstance(value, str):
                all_skills.extend(value.split(','))
        return [s.strip() for s in all_skills if s.strip()]
    return []


def transform_date_format(date_str: str) -> str:
    """
    Normalize date to YYYY-MM-DD or YYYY-MM format.
    
    Handles various formats:
    - "2020-01-15"
    - "Jan 2020"
    - "2020"
    - "15/01/2020"
    """
    if not date_str:
        return ""
    
    # Try to parse and normalize
    # This is a simple implementation; enhance as needed
    date_str = str(date_str).strip()
    
    # Already in correct format
    if len(date_str) == 10 and date_str.count('-') == 2:
        return date_str
    if len(date_str) == 7 and date_str.count('-') == 1:
        return date_str
    
    # Add more sophisticated parsing if needed
    return date_str


# ============================================================================
# AUDIO UPLOAD MAPPING (voice_transcript_production_extractor.py)
# ============================================================================

AUDIO_UPLOAD_MAPPING = [
    # Candidate Basic Info
    FieldMappingRule("full_name", "candidate.fullName", is_mandatory=True),
    FieldMappingRule("first_name", "candidate.firstName"),
    FieldMappingRule("middle_name", "candidate.middleName"),
    FieldMappingRule("last_name", "candidate.lastName"),
    
    # Contact Info
    FieldMappingRule("phone_number", "candidate.phoneNumber", is_mandatory=True),
    FieldMappingRule("alternate_phone", "candidate.alternatePhoneNumber"),
    FieldMappingRule("email", "candidate.email", is_mandatory=True),
    FieldMappingRule("portal_id", "candidate.portalId"),
    FieldMappingRule("employee_id", "candidate.portalId"),  # Alias
    
    # Personal Details
    FieldMappingRule("date_of_birth", "candidate.dateOfBirth", transform_fn=transform_date_format),
    FieldMappingRule("gender", "candidate.gender"),
    FieldMappingRule("nationality", "candidate.nationality"),
    
    # Location
    FieldMappingRule("current_location", "candidate.currentLocation", 
                    transform_fn=transform_location, is_mandatory=True),
    FieldMappingRule("location", "candidate.currentLocation", 
                    transform_fn=transform_location),  # Alias
    FieldMappingRule("preferred_locations", "candidate.preferredLocation"),
    
    # Experience
    FieldMappingRule("total_experience", "candidate.totalExperienceYears", 
                    transform_fn=lambda x: transform_experience_duration(x)["years"]),
    FieldMappingRule("total_experience_months", "candidate.totalExperienceMonths", 
                    transform_fn=lambda x: transform_experience_duration(x)["months"]),
    FieldMappingRule("relevant_experience", "candidate.relevantExperienceYears",
                    transform_fn=lambda x: transform_experience_duration(x)["years"]),
    FieldMappingRule("relevant_experience_months", "candidate.relevantExperienceMonths",
                    transform_fn=lambda x: transform_experience_duration(x)["months"]),
    
    # Current Employment
    FieldMappingRule("current_organization", "candidate.currentOrganization", is_mandatory=True),
    FieldMappingRule("current_company", "candidate.currentOrganization"),  # Alias
    FieldMappingRule("current_designation", "candidate.currentDesignation", is_mandatory=True),
    FieldMappingRule("current_role", "candidate.currentDesignation"),  # Alias
    FieldMappingRule("current_ctc", "candidate.currentCTC"),
    FieldMappingRule("expected_ctc", "candidate.expectedCTC"),
    FieldMappingRule("notice_period", "candidate.noticePeriod"),
    FieldMappingRule("employment_type", "candidate.employmentType"),
    
    # Summary
    FieldMappingRule("professional_summary", "candidate.summary"),
    FieldMappingRule("summary", "candidate.summary"),
    FieldMappingRule("career_objective", "candidate.careerObjective"),
    
    # Skills
    FieldMappingRule("primary_skills", "skills.primarySkills", transform_fn=transform_skills_list),
    FieldMappingRule("secondary_skills", "skills.secondarySkills", transform_fn=transform_skills_list),
    FieldMappingRule("technical_skills", "skills.technicalSkills", transform_fn=transform_skills_list),
    FieldMappingRule("functional_skills", "skills.functionalSkills", transform_fn=transform_skills_list),
    FieldMappingRule("soft_skills", "skills.softSkills", transform_fn=transform_skills_list),
    FieldMappingRule("tools_and_platforms", "skills.toolsAndPlatforms", transform_fn=transform_skills_list),
    FieldMappingRule("operating_systems", "skills.operatingSystems", transform_fn=transform_skills_list),
    FieldMappingRule("databases", "skills.databases", transform_fn=transform_skills_list),
    FieldMappingRule("cloud_technologies", "skills.cloudTechnologies", transform_fn=transform_skills_list),
    FieldMappingRule("frameworks", "skills.frameworks", transform_fn=transform_skills_list),
    FieldMappingRule("libraries", "skills.libraries", transform_fn=transform_skills_list),
    FieldMappingRule("ai_tools", "skills.aiToolsAndFrameworks", transform_fn=transform_skills_list),
    
    # Work History & Projects (handled separately as arrays)
    FieldMappingRule("work_history", "experience.workHistory"),
    FieldMappingRule("projects", "experience.projects"),
    FieldMappingRule("domain_experience", "experience.domainExperience", transform_fn=transform_skills_list),
    FieldMappingRule("industries_worked", "experience.industriesWorked", transform_fn=transform_skills_list),
    
    # Education (handled separately as array)
    FieldMappingRule("education", "education"),
    
    # Certifications (handled separately as array)
    FieldMappingRule("certifications", "certifications"),
    
    # Achievements
    FieldMappingRule("achievements", "achievements"),
    
    # Personal Details
    FieldMappingRule("languages_known", "personalDetails.languagesKnown", transform_fn=transform_skills_list),
    FieldMappingRule("marital_status", "personalDetails.maritalStatus"),
    FieldMappingRule("passport_number", "personalDetails.passportNumber"),
    FieldMappingRule("linkedin_url", "personalDetails.linkedinUrl"),
    FieldMappingRule("github_url", "personalDetails.githubUrl"),
    FieldMappingRule("portfolio_url", "personalDetails.portfolioUrl"),
]


# ============================================================================
# BOT CONVERSATION MAPPING (conversational_text_extractor.py)
# ============================================================================

BOT_CONVERSATION_MAPPING = [
    # Uses similar mapping as audio, but different source keys
    FieldMappingRule("candidateName", "candidate.fullName", is_mandatory=True),
    FieldMappingRule("name", "candidate.fullName"),
    FieldMappingRule("contactNumber", "candidate.phoneNumber", is_mandatory=True),
    FieldMappingRule("phone", "candidate.phoneNumber"),
    FieldMappingRule("emailAddress", "candidate.email", is_mandatory=True),
    FieldMappingRule("email", "candidate.email"),
    FieldMappingRule("employeeId", "candidate.portalId"),
    FieldMappingRule("portalId", "candidate.portalId"),
    
    FieldMappingRule("currentLocation", "candidate.currentLocation", 
                    transform_fn=transform_location, is_mandatory=True),
    FieldMappingRule("totalExperience", "candidate.totalExperienceYears",
                    transform_fn=lambda x: transform_experience_duration(str(x))["years"]),
    FieldMappingRule("organization", "candidate.currentOrganization", is_mandatory=True),
    FieldMappingRule("currentOrganization", "candidate.currentOrganization"),
    FieldMappingRule("designation", "candidate.currentDesignation", is_mandatory=True),
    FieldMappingRule("currentDesignation", "candidate.currentDesignation"),
    
    FieldMappingRule("skills", "skills.primarySkills", transform_fn=transform_skills_list),
    FieldMappingRule("primarySkills", "skills.primarySkills", transform_fn=transform_skills_list),
    FieldMappingRule("secondarySkills", "skills.secondarySkills", transform_fn=transform_skills_list),
    FieldMappingRule("technicalSkills", "skills.technicalSkills", transform_fn=transform_skills_list),
    
    FieldMappingRule("workExperience", "experience.workHistory"),
    FieldMappingRule("projectDetails", "experience.projects"),
    FieldMappingRule("projects", "experience.projects"),
    FieldMappingRule("education", "education"),
    FieldMappingRule("educationDetails", "education"),
    FieldMappingRule("certifications", "certifications"),
]


# ============================================================================
# START RECORDING MAPPING (Similar to Audio Upload)
# ============================================================================

START_RECORDING_MAPPING = AUDIO_UPLOAD_MAPPING  # Same structure


# ============================================================================
# DOCX/PDF UPLOAD MAPPING (document_parser service)
# ============================================================================

DOCX_PDF_MAPPING = [
    # Document parsers typically extract with different key names
    FieldMappingRule("Name", "candidate.fullName", is_mandatory=True),
    FieldMappingRule("Full Name", "candidate.fullName"),
    FieldMappingRule("Phone", "candidate.phoneNumber", is_mandatory=True),
    FieldMappingRule("Mobile", "candidate.phoneNumber"),
    FieldMappingRule("Email", "candidate.email", is_mandatory=True),
    FieldMappingRule("Employee ID", "candidate.portalId"),
    FieldMappingRule("Portal ID", "candidate.portalId"),
    
    FieldMappingRule("Location", "candidate.currentLocation", 
                    transform_fn=transform_location, is_mandatory=True),
    FieldMappingRule("Current Location", "candidate.currentLocation", 
                    transform_fn=transform_location),
    
    FieldMappingRule("Total Experience", "candidate.totalExperienceYears",
                    transform_fn=lambda x: transform_experience_duration(str(x))["years"]),
    FieldMappingRule("Experience", "candidate.totalExperienceYears",
                    transform_fn=lambda x: transform_experience_duration(str(x))["years"]),
    
    FieldMappingRule("Current Organization", "candidate.currentOrganization", is_mandatory=True),
    FieldMappingRule("Organization", "candidate.currentOrganization"),
    FieldMappingRule("Company", "candidate.currentOrganization"),
    FieldMappingRule("Current Designation", "candidate.currentDesignation", is_mandatory=True),
    FieldMappingRule("Designation", "candidate.currentDesignation"),
    FieldMappingRule("Role", "candidate.currentDesignation"),
    
    FieldMappingRule("Skills", "skills.primarySkills", transform_fn=transform_skills_list),
    FieldMappingRule("Primary Skills", "skills.primarySkills", transform_fn=transform_skills_list),
    FieldMappingRule("Secondary Skills", "skills.secondarySkills", transform_fn=transform_skills_list),
    FieldMappingRule("Technical Skills", "skills.technicalSkills", transform_fn=transform_skills_list),
    
    FieldMappingRule("Work History", "experience.workHistory"),
    FieldMappingRule("Employment History", "experience.workHistory"),
    FieldMappingRule("Projects", "experience.projects"),
    FieldMappingRule("Project Details", "experience.projects"),
    FieldMappingRule("Education", "education"),
    FieldMappingRule("Educational Qualifications", "education"),
    FieldMappingRule("Certifications", "certifications"),
]


# ============================================================================
# MAPPING REGISTRY
# ============================================================================

MAPPING_REGISTRY: Dict[str, List[FieldMappingRule]] = {
    "audio_upload": AUDIO_UPLOAD_MAPPING,
    "bot_conversation": BOT_CONVERSATION_MAPPING,
    "start_recording": START_RECORDING_MAPPING,
    "docx_upload": DOCX_PDF_MAPPING,
    "pdf_upload": DOCX_PDF_MAPPING,
}


def get_mapping_for_source(source_type: str) -> List[FieldMappingRule]:
    """
    Get field mapping rules for a specific source type.
    
    Args:
        source_type: One of "audio_upload", "bot_conversation", "start_recording", 
                    "docx_upload", "pdf_upload"
    
    Returns:
        List of FieldMappingRule objects
    
    Raises:
        ValueError: If source_type is not supported
    """
    if source_type not in MAPPING_REGISTRY:
        raise ValueError(
            f"Unsupported source type: {source_type}. "
            f"Supported types: {list(MAPPING_REGISTRY.keys())}"
        )
    
    return MAPPING_REGISTRY[source_type]


def get_mandatory_fields_for_source(source_type: str) -> List[str]:
    """
    Get list of mandatory canonical field paths for a source.
    
    Args:
        source_type: Input source type
    
    Returns:
        List of canonical field paths that are mandatory
    """
    mapping = get_mapping_for_source(source_type)
    return [rule.canonical_path for rule in mapping if rule.is_mandatory]


def get_all_supported_sources() -> List[str]:
    """Get list of all supported source types"""
    return list(MAPPING_REGISTRY.keys())
