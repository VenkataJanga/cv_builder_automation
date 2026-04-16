"""
Field Mapping Registry

This module defines mappings between various input formats and the Canonical CV Schema.
It provides a centralized registry for field transformations across all input modes.

Purpose:
- Map legacy field names to canonical schema fields
- Provide field path resolution for nested structures
- Support data transformation rules
- Enable consistent field handling across extractors

Author: CV Builder Team
Date: 2026-04-12
Version: 1.1
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass


@dataclass
class FieldMapping:
    """
    Represents a single field mapping configuration.
    
    Attributes:
        canonical_path: Path in Canonical CV Schema (e.g., "candidate.fullName")
        source_paths: List of possible source field names/paths
        transform_fn: Optional transformation function
        is_required: Whether this field is mandatory
        default_value: Default value if field is missing
    """
    canonical_path: str
    source_paths: List[str]
    transform_fn: Optional[Callable[[Any], Any]] = None
    is_required: bool = False
    default_value: Any = None


class FieldMappingRegistry:
    """
    Centralized registry for field mappings between input sources and Canonical CV Schema.
    
    This class provides:
    - Mapping configurations for all CV fields
    - Support for multiple source formats (audio, bot, docx, pdf)
    - Field transformation rules
    - Required field validation
    
    Usage:
        registry = FieldMappingRegistry()
        mapping = registry.get_mapping("candidate.fullName")
        canonical_data = registry.map_to_canonical(source_data, source_type="audio")
    """
    
    def __init__(self):
        """Initialize the field mapping registry"""
        self._mappings: Dict[str, FieldMapping] = {}
        self._initialize_mappings()
    
    def _initialize_mappings(self):
        """Initialize all field mappings for Canonical CV Schema v1.1"""
        
        # ====================================================================
        # CANDIDATE FIELDS
        # ====================================================================
        
        # Basic Identity
        self._add_mapping(FieldMapping(
            canonical_path="candidate.fullName",
            source_paths=["fullName", "full_name", "name", "candidate_name", "candidateName"],
            is_required=True
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.firstName",
            source_paths=["firstName", "first_name", "fname"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.middleName",
            source_paths=["middleName", "middle_name", "mname"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.lastName",
            source_paths=["lastName", "last_name", "lname", "surname"]
        ))
        
        # Contact Information
        self._add_mapping(FieldMapping(
            canonical_path="candidate.phoneNumber",
            source_paths=["phoneNumber", "phone_number", "phone", "mobile", "mobileNumber", "contact"],
            is_required=True
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.alternatePhoneNumber",
            source_paths=["alternatePhoneNumber", "alternate_phone", "alternatePhone", "secondaryPhone"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.email",
            source_paths=["email", "emailAddress", "email_address", "mail"],
            is_required=True
        ))
        
        # Professional Identity
        self._add_mapping(FieldMapping(
            canonical_path="candidate.portalId",
            source_paths=["portalId", "portal_id", "employeeId", "employee_id", "empId", "id"]
        ))
        
        # Personal Details
        self._add_mapping(FieldMapping(
            canonical_path="candidate.dateOfBirth",
            source_paths=["dateOfBirth", "date_of_birth", "dob", "birthDate"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.gender",
            source_paths=["gender", "sex"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.nationality",
            source_paths=["nationality", "nation", "citizenship"]
        ))
        
        # Location
        self._add_mapping(FieldMapping(
            canonical_path="candidate.currentLocation.city",
            source_paths=["city", "currentCity", "location_city", "locationCity"],
            is_required=True
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.currentLocation.state",
            source_paths=["state", "currentState", "location_state", "province"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.currentLocation.country",
            source_paths=["country", "currentCountry", "location_country"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.currentLocation.fullAddress",
            source_paths=["fullAddress", "address", "full_address", "completeAddress"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.preferredLocation",
            source_paths=["preferredLocation", "preferred_location", "preferredLocations", "targetLocations"]
        ))
        
        # Experience Summary
        self._add_mapping(FieldMapping(
            canonical_path="candidate.totalExperienceYears",
            source_paths=["totalExperienceYears", "total_experience_years", "experienceYears", "yearsOfExperience"],
            default_value=0
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.totalExperienceMonths",
            source_paths=["totalExperienceMonths", "total_experience_months", "experienceMonths"],
            default_value=0
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.relevantExperienceYears",
            source_paths=["relevantExperienceYears", "relevant_experience_years", "relevantYears"],
            default_value=0
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.relevantExperienceMonths",
            source_paths=["relevantExperienceMonths", "relevant_experience_months", "relevantMonths"],
            default_value=0
        ))
        
        # Current Employment
        self._add_mapping(FieldMapping(
            canonical_path="candidate.currentOrganization",
            source_paths=["currentOrganization", "current_organization", "currentCompany", "organization", "company"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.currentDesignation",
            source_paths=["currentDesignation", "current_designation", "designation", "jobTitle", "title", "role"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.currentCTC",
            source_paths=["currentCTC", "current_ctc", "currentSalary", "salary", "ctc"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.expectedCTC",
            source_paths=["expectedCTC", "expected_ctc", "expectedSalary", "expectedCompensation"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.noticePeriod",
            source_paths=["noticePeriod", "notice_period", "noticePeriodDays", "availability"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.employmentType",
            source_paths=["employmentType", "employment_type", "jobType", "contractType"]
        ))
        
        # Professional Summary
        self._add_mapping(FieldMapping(
            canonical_path="candidate.summary",
            source_paths=["summary", "professionalSummary", "professional_summary", "profile", "about"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="candidate.careerObjective",
            source_paths=["careerObjective", "career_objective", "objective", "goals"]
        ))
        
        # ====================================================================
        # SKILLS FIELDS
        # ====================================================================
        
        self._add_mapping(FieldMapping(
            canonical_path="skills.primarySkills",
            source_paths=["primarySkills", "primary_skills", "coreSkills", "mainSkills"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="skills.secondarySkills",
            source_paths=["secondarySkills", "secondary_skills", "additionalSkills"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="skills.technicalSkills",
            source_paths=["technicalSkills", "technical_skills", "techSkills", "skills"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="skills.functionalSkills",
            source_paths=["functionalSkills", "functional_skills", "domainSkills"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="skills.softSkills",
            source_paths=["softSkills", "soft_skills", "interpersonalSkills"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="skills.toolsAndPlatforms",
            source_paths=["toolsAndPlatforms", "tools_and_platforms", "tools", "platforms"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="skills.operatingSystems",
            source_paths=["operatingSystems", "operating_systems", "os", "operatingSystemsUsed"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="skills.databases",
            source_paths=["databases", "database", "db", "databaseTechnologies"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="skills.cloudTechnologies",
            source_paths=["cloudTechnologies", "cloud_technologies", "cloud", "cloudPlatforms"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="skills.frameworks",
            source_paths=["frameworks", "framework"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="skills.libraries",
            source_paths=["libraries", "library", "libs"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="skills.aiToolsAndFrameworks",
            source_paths=["aiToolsAndFrameworks", "ai_tools", "mlTools", "aiFrameworks"]
        ))
        
        # ====================================================================
        # EXPERIENCE FIELDS
        # ====================================================================
        
        self._add_mapping(FieldMapping(
            canonical_path="experience.totalProjects",
            source_paths=["totalProjects", "total_projects", "projectCount"],
            default_value=0
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="experience.domainExperience",
            source_paths=["domainExperience", "domain_experience", "domains", "expertise"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="experience.industriesWorked",
            source_paths=["industriesWorked", "industries_worked", "industries", "sectors"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="experience.workHistory",
            source_paths=["workHistory", "work_history", "employmentHistory", "jobs", "employment"]
        ))
        
        self._add_mapping(FieldMapping(
            canonical_path="experience.projects",
            source_paths=["projects", "projectDetails", "project_details", "projectHistory"]
        ))
    
    def _add_mapping(self, mapping: FieldMapping):
        """Add a field mapping to the registry"""
        self._mappings[mapping.canonical_path] = mapping
    
    def get_mapping(self, canonical_path: str) -> Optional[FieldMapping]:
        """
        Get mapping configuration for a canonical field path.
        
        Args:
            canonical_path: Canonical field path (e.g., "candidate.fullName")
            
        Returns:
            FieldMapping if found, None otherwise
        """
        return self._mappings.get(canonical_path)
    
    def get_all_mappings(self) -> Dict[str, FieldMapping]:
        """Get all field mappings"""
        return self._mappings.copy()
    
    def get_required_fields(self) -> List[str]:
        """
        Get list of required canonical field paths.
        
        Returns:
            List of canonical paths for required fields
        """
        return [
            path for path, mapping in self._mappings.items()
            if mapping.is_required
        ]
    
    def find_canonical_path(self, source_field: str) -> Optional[str]:
        """
        Find canonical path for a given source field name.
        
        Args:
            source_field: Source field name from input data
            
        Returns:
            Canonical path if found, None otherwise
        """
        for canonical_path, mapping in self._mappings.items():
            if source_field in mapping.source_paths:
                return canonical_path
        return None


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

# Global singleton instance
_registry_instance = None


def get_field_mapping_registry() -> FieldMappingRegistry:
    """
    Get the global field mapping registry instance (singleton).
    
    Returns:
        FieldMappingRegistry: Global registry instance
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = FieldMappingRegistry()
    return _registry_instance
