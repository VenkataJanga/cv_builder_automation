"""
Schema Mapper Service

This service maps data from various input sources to the Canonical CV Schema.
It provides centralized transformation logic for all CV input modes.

Purpose:
- Convert raw input data (audio, bot, docx, pdf) to Canonical CV Schema
- Apply field mappings and transformations
- Handle nested data structures
- Preserve data integrity during mapping

Author: CV Builder Team
Date: 2026-04-12
Version: 1.1
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.domain.cv.models.canonical_cv_schema import (
    CanonicalCVSchema,
    CandidateModel,
    LocationModel,
    SkillsModel,
    ExperienceModel,
    WorkHistoryModel,
    ProjectModel,
    EducationModel,
    CertificationModel,
    AchievementModel,
    PersonalDetailsModel,
    AttachmentsMetadataModel,
    AuditModel,
    create_empty_canonical_cv
)
from src.domain.cv.field_mapping_registry import get_field_mapping_registry, FieldMapping
from src.domain.cv.enums import SourceType

logger = logging.getLogger(__name__)


class SchemaMapperService:
    """
    Service for mapping input data to Canonical CV Schema.
    
    This service:
    - Maps any input format to Canonical CV Schema
    - Handles field name variations
    - Preserves all available data
    - Creates properly structured canonical CV documents
    
    Usage:
        mapper = SchemaMapperService()
        canonical_cv = mapper.map_to_canonical(
            source_data=extracted_data,
            source_type="audio_upload",
            cv_id="cv_12345"
        )
    """
    
    def __init__(self):
        """Initialize the schema mapper service"""
        self.registry = get_field_mapping_registry()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def map_to_canonical(
        self,
        source_data: Dict[str, Any],
        source_type: str,
        cv_id: Optional[str] = None,
        existing_cv: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Map source data to Canonical CV Schema.
        
        Args:
            source_data: Raw extracted data from any input source
            source_type: Type of input (audio_upload, bot_conversation, etc.)
            cv_id: Unique CV identifier
            existing_cv: Existing canonical CV to merge with (optional)
            
        Returns:
            Dict containing Canonical CV Schema compliant data
        """
        try:
            self.logger.info(f"DEBUG MAPPER ENTRY: Mapping data to canonical schema from source: {source_type}")
            self.logger.info(f"DEBUG MAPPER ENTRY: source_data top-level keys: {list(source_data.keys())}")
            self.logger.info(f"DEBUG MAPPER ENTRY: source_data personal_info: {source_data.get('personal_info')}")
            self.logger.info(f"DEBUG MAPPER ENTRY: source_data summary: {source_data.get('summary')}")
            
            # Start with empty canonical CV or existing CV
            if existing_cv:
                canonical_cv = existing_cv.copy()
                self.logger.info("Merging with existing CV data")
            else:
                canonical_cv = create_empty_canonical_cv(cv_id=cv_id or "", source_type=source_type)
                self.logger.info("Creating new canonical CV")
            
            # Update root metadata
            canonical_cv["schema_version"] = "1.1"
            canonical_cv["cvId"] = cv_id or canonical_cv.get("cvId", "")
            canonical_cv["sourceType"] = source_type
            
            # Map candidate information
            self._map_candidate_section(source_data, canonical_cv)
            
            # Map skills
            self._map_skills_section(source_data, canonical_cv)
            
            # Map experience
            self._map_experience_section(source_data, canonical_cv)
            
            # Map education
            self._map_education_section(source_data, canonical_cv)
            
            # Map certifications
            self._map_certifications_section(source_data, canonical_cv)
            
            # Map achievements
            self._map_achievements_section(source_data, canonical_cv)
            
            # Map personal details
            self._map_personal_details_section(source_data, canonical_cv)
            
            # Update audit trail
            self._update_audit_trail(canonical_cv, source_type)
            
            self.logger.info("Successfully mapped data to canonical schema")
            return canonical_cv
            
        except Exception as e:
            self.logger.error(f"Error mapping to canonical schema: {str(e)}", exc_info=True)
            raise
    
    def _map_candidate_section(self, source_data: Dict[str, Any], canonical_cv: Dict[str, Any]):
        """Map candidate information to canonical schema"""
        try:
            self.logger.info(f"DEBUG MAPPER: source_data keys: {list(source_data.keys())}")
            if "personal_info" in source_data:
                self.logger.info(f"DEBUG MAPPER: personal_info keys: {list(source_data['personal_info'].keys())}")
                self.logger.info(f"DEBUG MAPPER: name value: {source_data['personal_info'].get('name')}")
            
            candidate = canonical_cv.setdefault("candidate", {})
            
            # Check for personal_info structure from document parser
            if "personal_info" in source_data and isinstance(source_data["personal_info"], dict):
                personal_info = source_data["personal_info"]
                # Map directly from personal_info structure
                if personal_info.get("name"):
                    candidate["fullName"] = personal_info["name"]
                if personal_info.get("email"):
                    candidate["email"] = personal_info["email"]
                if personal_info.get("phone"):
                    candidate["phoneNumber"] = personal_info["phone"]
                if personal_info.get("linkedin"):
                    canonical_cv.setdefault("personalDetails", {})["linkedinUrl"] = personal_info["linkedin"]
                if personal_info.get("github"):
                    canonical_cv.setdefault("personalDetails", {})["githubUrl"] = personal_info["github"]
                if personal_info.get("location") and isinstance(personal_info["location"], dict):
                    loc = personal_info["location"]
                    candidate["currentLocation"] = {
                        "city": loc.get("city", ""),
                        "state": loc.get("state", ""),
                        "country": loc.get("country", ""),
                        "fullAddress": f"{loc.get('city', '')}, {loc.get('state', '')}, {loc.get('country', '')}".strip(", ")
                    }
            
            # Basic identity fields (fallback to field mapping)
            self._map_field(source_data, candidate, "candidate.fullName", "fullName")
            self._map_field(source_data, candidate, "candidate.firstName", "firstName")
            self._map_field(source_data, candidate, "candidate.middleName", "middleName")
            self._map_field(source_data, candidate, "candidate.lastName", "lastName")
            
            # Contact information
            self._map_field(source_data, candidate, "candidate.phoneNumber", "phoneNumber")
            self._map_field(source_data, candidate, "candidate.alternatePhoneNumber", "alternatePhoneNumber")
            self._map_field(source_data, candidate, "candidate.email", "email")
            self._map_field(source_data, candidate, "candidate.portalId", "portalId")
            
            # Personal details
            self._map_field(source_data, candidate, "candidate.dateOfBirth", "dateOfBirth")
            self._map_field(source_data, candidate, "candidate.gender", "gender")
            self._map_field(source_data, candidate, "candidate.nationality", "nationality")
            
            # Location mapping
            self._map_location(source_data, candidate)
            
            # Experience summary
            self._map_field(source_data, candidate, "candidate.totalExperienceYears", "totalExperienceYears")
            self._map_field(source_data, candidate, "candidate.totalExperienceMonths", "totalExperienceMonths")
            self._map_field(source_data, candidate, "candidate.relevantExperienceYears", "relevantExperienceYears")
            self._map_field(source_data, candidate, "candidate.relevantExperienceMonths", "relevantExperienceMonths")
            
            # Current employment
            self._map_field(source_data, candidate, "candidate.currentOrganization", "currentOrganization")
            self._map_field(source_data, candidate, "candidate.currentDesignation", "currentDesignation")
            self._map_field(source_data, candidate, "candidate.currentCTC", "currentCTC")
            self._map_field(source_data, candidate, "candidate.expectedCTC", "expectedCTC")
            self._map_field(source_data, candidate, "candidate.noticePeriod", "noticePeriod")
            self._map_field(source_data, candidate, "candidate.employmentType", "employmentType")
            
            # Professional summary - check both candidate.summary and top-level summary
            if "summary" in source_data and source_data["summary"]:
                candidate["summary"] = source_data["summary"]
            else:
                self._map_field(source_data, candidate, "candidate.summary", "summary")
            self._map_field(source_data, candidate, "candidate.careerObjective", "careerObjective")
            
            # Preferred locations (list field)
            self._map_list_field(source_data, candidate, "candidate.preferredLocation", "preferredLocation")
            
            self.logger.debug("Candidate section mapped successfully")
            
        except Exception as e:
            self.logger.error(f"Error mapping candidate section: {str(e)}")
            raise
    
    def _map_location(self, source_data: Dict[str, Any], candidate: Dict[str, Any]):
        """Map location information"""
        try:
            location = candidate.setdefault("currentLocation", {})
            
            # Check if location data is provided as a nested object
            location_source = None
            for key in ["location", "currentLocation", "current_location"]:
                if key in source_data and source_data[key]:
                    location_source = source_data[key]
                    break
            
            if location_source and isinstance(location_source, dict):
                # Map from nested location object
                location["city"] = location_source.get("city", "")
                location["state"] = location_source.get("state", "")
                location["country"] = location_source.get("country", "")
                location["fullAddress"] = location_source.get("fullAddress", location_source.get("city", ""))
            else:
                # Try flat structure using field mappings
                self._map_field(source_data, location, "candidate.currentLocation.city", "city")
                self._map_field(source_data, location, "candidate.currentLocation.state", "state")
                self._map_field(source_data, location, "candidate.currentLocation.country", "country")
                self._map_field(source_data, location, "candidate.currentLocation.fullAddress", "fullAddress")
            
        except Exception as e:
            self.logger.error(f"Error mapping location: {str(e)}")
    
    def _map_skills_section(self, source_data: Dict[str, Any], canonical_cv: Dict[str, Any]):
        """Map skills information to canonical schema"""
        try:
            skills = canonical_cv.setdefault("skills", {})
            
            # Map all skill categories
            self._map_list_field(source_data, skills, "skills.primarySkills", "primarySkills")
            self._map_list_field(source_data, skills, "skills.secondarySkills", "secondarySkills")
            self._map_list_field(source_data, skills, "skills.technicalSkills", "technicalSkills")
            self._map_list_field(source_data, skills, "skills.functionalSkills", "functionalSkills")
            self._map_list_field(source_data, skills, "skills.softSkills", "softSkills")
            self._map_list_field(source_data, skills, "skills.toolsAndPlatforms", "toolsAndPlatforms")
            self._map_list_field(source_data, skills, "skills.operatingSystems", "operatingSystems")
            self._map_list_field(source_data, skills, "skills.databases", "databases")
            self._map_list_field(source_data, skills, "skills.cloudTechnologies", "cloudTechnologies")
            self._map_list_field(source_data, skills, "skills.frameworks", "frameworks")
            self._map_list_field(source_data, skills, "skills.libraries", "libraries")
            self._map_list_field(source_data, skills, "skills.aiToolsAndFrameworks", "aiToolsAndFrameworks")
            
            self.logger.debug("Skills section mapped successfully")
            
        except Exception as e:
            self.logger.error(f"Error mapping skills section: {str(e)}")
    
    def _map_experience_section(self, source_data: Dict[str, Any], canonical_cv: Dict[str, Any]):
        """Map experience information to canonical schema"""
        try:
            experience = canonical_cv.setdefault("experience", {})
            
            # Map summary fields
            self._map_field(source_data, experience, "experience.totalProjects", "totalProjects")
            self._map_list_field(source_data, experience, "experience.domainExperience", "domainExperience")
            self._map_list_field(source_data, experience, "experience.industriesWorked", "industriesWorked")
            
            # Check if experience data is directly in source_data (from document parser)
            if "experience" in source_data and isinstance(source_data["experience"], list):
                # Document parser format: experience is a list of job entries
                work_history = []
                for job in source_data["experience"]:
                    if isinstance(job, dict):
                        work_entry = {
                            "organization": job.get("company", ""),
                            "designation": job.get("title", ""),
                            "employmentStartDate": job.get("startDate", ""),
                            "employmentEndDate": job.get("endDate", ""),
                            "isCurrentCompany": job.get("endDate", "").lower() in ["present", "current"],
                            "location": "",
                            "responsibilities": job.get("responsibilities", []),
                            "achievements": [],
                            "technologiesUsed": []
                        }
                        work_history.append(work_entry)
                experience["workHistory"] = work_history
            else:
                # Standard format: map work history
                self._map_work_history(source_data, experience)
            
            # Check if projects data is directly in source_data (from document parser)
            if "projects" in source_data and isinstance(source_data["projects"], list):
                # Document parser format: projects is a list
                projects = []
                for proj in source_data["projects"]:
                    if isinstance(proj, dict):
                        project_entry = {
                            "projectName": proj.get("name", ""),
                            "clientName": "",
                            "organization": "",
                            "role": proj.get("role", ""),
                            "durationFrom": "",
                            "durationTo": "",
                            "isCurrentProject": False,
                            "projectLocation": "",
                            "projectDescription": proj.get("description", ""),
                            "responsibilities": [],
                            "outcomes": [],
                            "environment": proj.get("technologies", []),
                            "toolsUsed": [],
                            "teamSize": "",
                            "methodology": "",
                            "domain": "",
                            "hardwareDetails": "",
                            "softwareDetails": ""
                        }
                        projects.append(project_entry)
                experience["projects"] = projects
            else:
                # Standard format: map projects
                self._map_projects(source_data, experience)
            
            self.logger.debug("Experience section mapped successfully")
            
        except Exception as e:
            self.logger.error(f"Error mapping experience section: {str(e)}")
    
    def _map_work_history(self, source_data: Dict[str, Any], experience: Dict[str, Any]):
        """Map work history entries"""
        try:
            # Look for work history in various formats
            work_history_source = None
            for key in ["workHistory", "work_history", "employmentHistory", "jobs", "employment"]:
                if key in source_data and source_data[key]:
                    work_history_source = source_data[key]
                    break
            
            if not work_history_source:
                experience.setdefault("workHistory", [])
                return
            
            # Ensure work_history_source is a list
            if not isinstance(work_history_source, list):
                work_history_source = [work_history_source]
            
            work_history = []
            for item in work_history_source:
                if isinstance(item, dict):
                    work_entry = {
                        "organization": item.get("organization", item.get("company", "")),
                        "designation": item.get("designation", item.get("title", item.get("jobTitle", ""))),
                        "employmentStartDate": item.get("employmentStartDate", item.get("startDate", "")),
                        "employmentEndDate": item.get("employmentEndDate", item.get("endDate", "")),
                        "isCurrentCompany": item.get("isCurrentCompany", item.get("isCurrent", False)),
                        "location": item.get("location", ""),
                        "responsibilities": item.get("responsibilities", []),
                        "achievements": item.get("achievements", []),
                        "technologiesUsed": item.get("technologiesUsed", item.get("technologies", []))
                    }
                    work_history.append(work_entry)
            
            experience["workHistory"] = work_history
            self.logger.debug(f"Mapped {len(work_history)} work history entries")
            
        except Exception as e:
            self.logger.error(f"Error mapping work history: {str(e)}")
            experience.setdefault("workHistory", [])
    
    def _map_projects(self, source_data: Dict[str, Any], experience: Dict[str, Any]):
        """Map project entries"""
        try:
            # Look for projects in various formats
            projects_source = None
            for key in ["projects", "projectDetails", "project_details", "projectHistory"]:
                if key in source_data and source_data[key]:
                    projects_source = source_data[key]
                    break
            
            if not projects_source:
                experience.setdefault("projects", [])
                return
            
            # Ensure projects_source is a list
            if not isinstance(projects_source, list):
                projects_source = [projects_source]
            
            projects = []
            for item in projects_source:
                if isinstance(item, dict):
                    project_entry = {
                        "projectName": item.get("projectName", item.get("name", "")),
                        "clientName": item.get("clientName", item.get("client", "")),
                        "organization": item.get("organization", item.get("company", "")),
                        "role": item.get("role", ""),
                        "durationFrom": item.get("durationFrom", item.get("startDate", "")),
                        "durationTo": item.get("durationTo", item.get("endDate", "")),
                        "isCurrentProject": item.get("isCurrentProject", item.get("isCurrent", False)),
                        "projectLocation": item.get("projectLocation", item.get("location", "")),
                        "projectDescription": item.get("projectDescription", item.get("description", "")),
                        "responsibilities": item.get("responsibilities", []),
                        "outcomes": item.get("outcomes", []),
                        "environment": item.get("environment", item.get("technologies", [])),
                        "toolsUsed": item.get("toolsUsed", item.get("tools", [])),
                        "teamSize": str(item.get("teamSize", "")),
                        "methodology": item.get("methodology", ""),
                        "domain": item.get("domain", ""),
                        "hardwareDetails": item.get("hardwareDetails", ""),
                        "softwareDetails": item.get("softwareDetails", "")
                    }
                    projects.append(project_entry)
            
            experience["projects"] = projects
            self.logger.debug(f"Mapped {len(projects)} project entries")
            
        except Exception as e:
            self.logger.error(f"Error mapping projects: {str(e)}")
            experience.setdefault("projects", [])
    
    def _map_education_section(self, source_data: Dict[str, Any], canonical_cv: Dict[str, Any]):
        """Map education information to canonical schema"""
        try:
            # Look for education in various formats
            education_source = None
            for key in ["education", "educationDetails", "education_details", "qualifications"]:
                if key in source_data and source_data[key]:
                    education_source = source_data[key]
                    break
            
            if not education_source:
                canonical_cv.setdefault("education", [])
                return
            
            # Ensure education_source is a list
            if not isinstance(education_source, list):
                education_source = [education_source]
            
            education = []
            for item in education_source:
                if isinstance(item, dict):
                    edu_entry = {
                        "degree": item.get("degree", ""),
                        "specialization": item.get("specialization", item.get("major", "")),
                        "institution": item.get("institution", item.get("college", item.get("school", ""))),
                        "university": item.get("university", item.get("board", "")),
                        "board": item.get("board", ""),
                        "yearOfPassing": str(item.get("yearOfPassing", item.get("year", ""))),
                        "percentage": str(item.get("percentage", "")),
                        "cgpa": str(item.get("cgpa", "")),
                        "grade": item.get("grade", ""),
                        "location": item.get("location", "")
                    }
                    education.append(edu_entry)
            
            canonical_cv["education"] = education
            self.logger.debug(f"Mapped {len(education)} education entries")
            
        except Exception as e:
            self.logger.error(f"Error mapping education section: {str(e)}")
            canonical_cv.setdefault("education", [])
    
    def _map_certifications_section(self, source_data: Dict[str, Any], canonical_cv: Dict[str, Any]):
        """Map certifications to canonical schema"""
        try:
            # Look for certifications in various formats
            certs_source = None
            for key in ["certifications", "certificates", "certification"]:
                if key in source_data and source_data[key]:
                    certs_source = source_data[key]
                    break
            
            if not certs_source:
                canonical_cv.setdefault("certifications", [])
                return
            
            # Ensure certs_source is a list
            if not isinstance(certs_source, list):
                certs_source = [certs_source]
            
            certifications = []
            for item in certs_source:
                if isinstance(item, dict):
                    cert_entry = {
                        "name": item.get("name", item.get("certificationName", "")),
                        "issuingOrganization": item.get("issuingOrganization", item.get("issuer", "")),
                        "issueDate": item.get("issueDate", item.get("dateIssued", "")),
                        "expiryDate": item.get("expiryDate", item.get("dateExpiry", "")),
                        "credentialId": item.get("credentialId", item.get("certId", "")),
                        "credentialUrl": item.get("credentialUrl", item.get("url", ""))
                    }
                    certifications.append(cert_entry)
            
            canonical_cv["certifications"] = certifications
            self.logger.debug(f"Mapped {len(certifications)} certification entries")
            
        except Exception as e:
            self.logger.error(f"Error mapping certifications section: {str(e)}")
            canonical_cv.setdefault("certifications", [])
    
    def _map_achievements_section(self, source_data: Dict[str, Any], canonical_cv: Dict[str, Any]):
        """Map achievements to canonical schema"""
        try:
            # Look for achievements in various formats
            achievements_source = None
            for key in ["achievements", "awards", "accomplishments"]:
                if key in source_data and source_data[key]:
                    achievements_source = source_data[key]
                    break
            
            if not achievements_source:
                canonical_cv.setdefault("achievements", [])
                return
            
            # Ensure achievements_source is a list
            if not isinstance(achievements_source, list):
                achievements_source = [achievements_source]
            
            achievements = []
            for item in achievements_source:
                if isinstance(item, dict):
                    achievement_entry = {
                        "title": item.get("title", item.get("name", "")),
                        "description": item.get("description", ""),
                        "date": item.get("date", item.get("year", ""))
                    }
                    achievements.append(achievement_entry)
            
            canonical_cv["achievements"] = achievements
            self.logger.debug(f"Mapped {len(achievements)} achievement entries")
            
        except Exception as e:
            self.logger.error(f"Error mapping achievements section: {str(e)}")
            canonical_cv.setdefault("achievements", [])
    
    def _map_personal_details_section(self, source_data: Dict[str, Any], canonical_cv: Dict[str, Any]):
        """Map personal details to canonical schema"""
        try:
            personal_details = canonical_cv.setdefault("personalDetails", {})
            
            # Languages
            self._map_list_field(source_data, personal_details, "personalDetails.languagesKnown", "languagesKnown")
            
            # Other personal fields
            for source_key, target_key in [
                ("maritalStatus", "maritalStatus"),
                ("passportNumber", "passportNumber"),
                ("linkedinUrl", "linkedinUrl"),
                ("linkedin_url", "linkedinUrl"),
                ("githubUrl", "githubUrl"),
                ("github_url", "githubUrl"),
                ("portfolioUrl", "portfolioUrl"),
                ("portfolio_url", "portfolioUrl")
            ]:
                if source_key in source_data and source_data[source_key]:
                    personal_details[target_key] = source_data[source_key]
            
            self.logger.debug("Personal details section mapped successfully")
            
        except Exception as e:
            self.logger.error(f"Error mapping personal details section: {str(e)}")
    
    def _map_field(self, source_data: Dict[str, Any], target: Dict[str, Any], 
                   canonical_path: str, target_key: str):
        """
        Map a single field from source to target using field mapping registry.
        
        Args:
            source_data: Source data dictionary
            target: Target dictionary to update
            canonical_path: Canonical field path for lookup
            target_key: Key to set in target dictionary
        """
        try:
            mapping = self.registry.get_mapping(canonical_path)
            if not mapping:
                return
            
            # Try all possible source paths
            value = None
            for source_key in mapping.source_paths:
                # First try flat key
                if source_key in source_data and source_data[source_key] not in [None, "", []]:
                    value = source_data[source_key]
                    break
                
                # Try nested paths (e.g., personal_details.full_name)
                nested_value = self._get_nested_value(source_data, source_key)
                if nested_value not in [None, "", []]:
                    value = nested_value
                    break
            
            # Set value if found, otherwise use default
            if value is not None:
                target[target_key] = value
            elif mapping.default_value is not None and target_key not in target:
                target[target_key] = mapping.default_value
            elif target_key not in target:
                # Initialize with empty value based on type
                target[target_key] = ""
                
        except Exception as e:
            self.logger.debug(f"Error mapping field {canonical_path}: {str(e)}")
    
    def _map_list_field(self, source_data: Dict[str, Any], target: Dict[str, Any],
                       canonical_path: str, target_key: str):
        """
        Map a list field from source to target.
        
        Args:
            source_data: Source data dictionary
            target: Target dictionary to update
            canonical_path: Canonical field path for lookup
            target_key: Key to set in target dictionary
        """
        try:
            mapping = self.registry.get_mapping(canonical_path)
            if not mapping:
                target.setdefault(target_key, [])
                return
            
            # Try all possible source paths
            value = None
            for source_key in mapping.source_paths:
                # First try flat key
                if source_key in source_data and source_data[source_key]:
                    value = source_data[source_key]
                    break
                
                # Try nested paths
                nested_value = self._get_nested_value(source_data, source_key)
                if nested_value:
                    value = nested_value
                    break
            
            # Ensure value is a list
            if value is not None:
                if isinstance(value, list):
                    target[target_key] = value
                else:
                    target[target_key] = [value]
            else:
                target.setdefault(target_key, [])
                
        except Exception as e:
            self.logger.debug(f"Error mapping list field {canonical_path}: {str(e)}")
            target.setdefault(target_key, [])
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        Get a value from nested dictionary using dot notation.
        
        Args:
            data: Source dictionary
            path: Path to value (e.g., "personal_details.full_name")
            
        Returns:
            Value if found, None otherwise
        """
        try:
            # Split path by dots or underscores followed by another word
            parts = path.replace(".", "_").split("_")
            
            # Try to find nested structure
            # Check for personal_details, skills, etc.
            for section_key in ["personal_details", "personalDetails", "skills", "experience", "education"]:
                if section_key in data and isinstance(data[section_key], dict):
                    section_data = data[section_key]
                    # Try the full path without section prefix
                    for key in [path, path.replace("_", ""), path.replace("_", ".")]:
                        if key in section_data:
                            return section_data[key]
                    
                    # Try individual parts
                    for part in parts:
                        if part in section_data:
                            return section_data[part]
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error getting nested value for path {path}: {str(e)}")
            return None
    
    def _update_audit_trail(self, canonical_cv: Dict[str, Any], source_type: str):
        """Update audit trail with current operation"""
        try:
            audit = canonical_cv.setdefault("audit", {})
            
            current_time = datetime.now().isoformat()
            
            # Set creation time if not exists
            if not audit.get("createdAt"):
                audit["createdAt"] = current_time
                audit["createdBy"] = "system"
            
            # Update modification time
            audit["updatedAt"] = current_time
            audit["sourceChannel"] = source_type
            
            # Initialize manual edits list if not exists
            audit.setdefault("manualEdits", [])
            
        except Exception as e:
            self.logger.error(f"Error updating audit trail: {str(e)}")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_schema_mapper() -> SchemaMapperService:
    """
    Get a schema mapper service instance.
    
    Returns:
        SchemaMapperService: Mapper service instance
    """
    return SchemaMapperService()


def get_schema_mapper_service() -> SchemaMapperService:
    """
    Get a schema mapper service instance (alias for get_schema_mapper).
    
    Returns:
        SchemaMapperService: Mapper service instance
    """
    return SchemaMapperService()
