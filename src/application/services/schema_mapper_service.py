"""
Schema Mapper Service

This service provides centralized mapping logic to convert data from various input sources
(audio, bot, recording, DOCX/PDF) into the Canonical CV Schema v1.1.

Key Responsibilities:
1. Map raw extracted data to canonical schema
2. Handle partial data gracefully
3. Preserve data consistency across all input modes
4. Support merge operations for updates
5. Track data sources and transformations

Author: CV Builder Team
Last Updated: 2026-04-12
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from src.domain.cv.models.canonical_cv_schema import (
    CanonicalCVSchema,
    Candidate,
    CurrentLocation,
    Skills,
    Experience,
    WorkHistory,
    Project,
    Education,
    Certification,
    Achievement,
    PersonalDetails,
    AttachmentsMetadata,
    Audit,
    create_empty_canonical_cv,
    merge_partial_data,
    get_empty_schema
)
from src.domain.cv.enums import SourceType

logger = logging.getLogger(__name__)


class SchemaMapperService:
    """
    Centralized service for mapping data to Canonical CV Schema.
    
    This service ensures that all input sources produce consistent canonical schema output.
    """
    
    def __init__(self):
        """Initialize the schema mapper service"""
        self.logger = logging.getLogger(__name__)
    
    # ============================================================================
    # MAIN MAPPING METHODS
    # ============================================================================
    
    def map_to_canonical(
        self,
        raw_data: Dict[str, Any],
        source_type: str,
        cv_id: Optional[str] = None
    ) -> CanonicalCVSchema:
        """
        Map raw extracted data to Canonical CV Schema.
        
        This is the main entry point for converting data from any source.
        
        Args:
            raw_data: Raw data from extractor (audio/bot/recording/docx)
            source_type: Source type (audio_upload, bot_conversation, etc.)
            cv_id: Optional CV identifier
            
        Returns:
            CanonicalCVSchema: Fully mapped canonical schema
        """
        try:
            self.logger.info(f"Mapping {source_type} data to canonical schema")
            
            # Start with empty schema
            cv_id = cv_id or raw_data.get("cvId", f"cv_{datetime.now().strftime('%Y%m%d%H%M%S')}")
            canonical_cv = get_empty_schema(cv_id=cv_id, source_type=source_type)
            
            # Map each section
            canonical_cv.candidate = self._map_candidate(raw_data)
            canonical_cv.skills = self._map_skills(raw_data)
            canonical_cv.experience = self._map_experience(raw_data)
            canonical_cv.education = self._map_education(raw_data)
            canonical_cv.certifications = self._map_certifications(raw_data)
            canonical_cv.achievements = self._map_achievements(raw_data)
            canonical_cv.personalDetails = self._map_personal_details(raw_data)
            canonical_cv.attachmentsMetadata = self._map_attachments_metadata(raw_data, source_type)
            canonical_cv.audit = self._map_audit(raw_data, source_type)
            
            self.logger.info(f"Successfully mapped {source_type} data to canonical schema")
            return canonical_cv
            
        except Exception as e:
            self.logger.error(f"Error mapping to canonical schema: {str(e)}", exc_info=True)
            raise
    
    def merge_update(
        self,
        existing_cv: CanonicalCVSchema,
        updates: Dict[str, Any]
    ) -> CanonicalCVSchema:
        """
        Merge updates into existing canonical CV without losing data.
        
        Args:
            existing_cv: Existing canonical CV schema
            updates: New data to merge
            
        Returns:
            CanonicalCVSchema: Updated canonical CV
        """
        try:
            self.logger.info("Merging updates into existing CV")
            
            # Use the built-in merge function
            merged_cv = merge_partial_data(existing_cv, updates)
            
            # Update audit trail
            merged_cv.audit.updatedAt = datetime.now().isoformat()
            
            return merged_cv
            
        except Exception as e:
            self.logger.error(f"Error merging CV updates: {str(e)}", exc_info=True)
            raise
    
    # ============================================================================
    # CANDIDATE MAPPING
    # ============================================================================
    
    def _map_candidate(self, raw_data: Dict[str, Any]) -> Candidate:
        """Map candidate information"""
        candidate_data = raw_data.get("candidate", {})
        
        # Handle both nested and flat structures
        if not candidate_data and "fullName" in raw_data:
            candidate_data = raw_data
        
        return Candidate(
            # Basic Identity
            fullName=candidate_data.get("fullName", candidate_data.get("full_name", "")),
            firstName=candidate_data.get("firstName", candidate_data.get("first_name", "")),
            middleName=candidate_data.get("middleName", candidate_data.get("middle_name", "")),
            lastName=candidate_data.get("lastName", candidate_data.get("last_name", "")),
            
            # Contact Information
            phoneNumber=candidate_data.get("phoneNumber", candidate_data.get("phone_number", "")),
            alternatePhoneNumber=candidate_data.get("alternatePhoneNumber", candidate_data.get("alternate_phone_number", "")),
            email=candidate_data.get("email", ""),
            
            # Professional Identity
            portalId=candidate_data.get("portalId", candidate_data.get("portal_id", "")),
            
            # Personal Details
            dateOfBirth=candidate_data.get("dateOfBirth", candidate_data.get("date_of_birth", "")),
            gender=candidate_data.get("gender", ""),
            nationality=candidate_data.get("nationality", ""),
            
            # Location
            currentLocation=self._map_location(candidate_data.get("currentLocation", candidate_data.get("current_location", {}))),
            preferredLocation=candidate_data.get("preferredLocation", candidate_data.get("preferred_location", [])),
            
            # Experience Summary
            totalExperienceYears=candidate_data.get("totalExperienceYears", candidate_data.get("total_experience_years", 0)),
            totalExperienceMonths=candidate_data.get("totalExperienceMonths", candidate_data.get("total_experience_months", 0)),
            relevantExperienceYears=candidate_data.get("relevantExperienceYears", candidate_data.get("relevant_experience_years", 0)),
            relevantExperienceMonths=candidate_data.get("relevantExperienceMonths", candidate_data.get("relevant_experience_months", 0)),
            
            # Current Employment
            currentOrganization=candidate_data.get("currentOrganization", candidate_data.get("current_organization", "")),
            currentDesignation=candidate_data.get("currentDesignation", candidate_data.get("current_designation", "")),
            currentCTC=candidate_data.get("currentCTC", candidate_data.get("current_ctc", "")),
            expectedCTC=candidate_data.get("expectedCTC", candidate_data.get("expected_ctc", "")),
            noticePeriod=candidate_data.get("noticePeriod", candidate_data.get("notice_period", "")),
            employmentType=candidate_data.get("employmentType", candidate_data.get("employment_type", "")),
            
            # Professional Summary
            summary=candidate_data.get("summary", ""),
            careerObjective=candidate_data.get("careerObjective", candidate_data.get("career_objective", ""))
        )
    
    def _map_location(self, location_data: Dict[str, Any]) -> CurrentLocation:
        """Map location information"""
        if not location_data:
            return CurrentLocation()
        
        return CurrentLocation(
            city=location_data.get("city", ""),
            state=location_data.get("state", ""),
            country=location_data.get("country", ""),
            fullAddress=location_data.get("fullAddress", location_data.get("full_address", ""))
        )
    
    # ============================================================================
    # SKILLS MAPPING
    # ============================================================================
    
    def _map_skills(self, raw_data: Dict[str, Any]) -> Skills:
        """Map skills information"""
        skills_data = raw_data.get("skills", {})
        
        return Skills(
            primarySkills=self._ensure_list(skills_data.get("primarySkills", skills_data.get("primary_skills", []))),
            secondarySkills=self._ensure_list(skills_data.get("secondarySkills", skills_data.get("secondary_skills", []))),
            technicalSkills=self._ensure_list(skills_data.get("technicalSkills", skills_data.get("technical_skills", []))),
            functionalSkills=self._ensure_list(skills_data.get("functionalSkills", skills_data.get("functional_skills", []))),
            softSkills=self._ensure_list(skills_data.get("softSkills", skills_data.get("soft_skills", []))),
            
            toolsAndPlatforms=self._ensure_list(skills_data.get("toolsAndPlatforms", skills_data.get("tools_and_platforms", []))),
            operatingSystems=self._ensure_list(skills_data.get("operatingSystems", skills_data.get("operating_systems", []))),
            databases=self._ensure_list(skills_data.get("databases", [])),
            cloudTechnologies=self._ensure_list(skills_data.get("cloudTechnologies", skills_data.get("cloud_technologies", []))),
            frameworks=self._ensure_list(skills_data.get("frameworks", [])),
            libraries=self._ensure_list(skills_data.get("libraries", [])),
            aiToolsAndFrameworks=self._ensure_list(skills_data.get("aiToolsAndFrameworks", skills_data.get("ai_tools_and_frameworks", []))),
            certificationsSkillsTagged=self._ensure_list(skills_data.get("certificationsSkillsTagged", skills_data.get("certifications_skills_tagged", [])))
        )
    
    # ============================================================================
    # EXPERIENCE MAPPING
    # ============================================================================
    
    def _map_experience(self, raw_data: Dict[str, Any]) -> Experience:
        """Map experience information"""
        experience_data = raw_data.get("experience", {})
        
        return Experience(
            totalProjects=experience_data.get("totalProjects", experience_data.get("total_projects", 0)),
            domainExperience=self._ensure_list(experience_data.get("domainExperience", experience_data.get("domain_experience", []))),
            industriesWorked=self._ensure_list(experience_data.get("industriesWorked", experience_data.get("industries_worked", []))),
            
            workHistory=self._map_work_history(experience_data.get("workHistory", experience_data.get("work_history", []))),
            projects=self._map_projects(experience_data.get("projects", []))
        )
    
    def _map_work_history(self, work_history_data: List[Dict[str, Any]]) -> List[WorkHistory]:
        """Map work history entries"""
        if not work_history_data:
            return []
        
        work_history = []
        for entry in work_history_data:
            work_history.append(WorkHistory(
                organization=entry.get("organization", ""),
                designation=entry.get("designation", ""),
                employmentStartDate=entry.get("employmentStartDate", entry.get("employment_start_date", "")),
                employmentEndDate=entry.get("employmentEndDate", entry.get("employment_end_date", "")),
                isCurrentCompany=entry.get("isCurrentCompany", entry.get("is_current_company", False)),
                location=entry.get("location", ""),
                responsibilities=self._ensure_list(entry.get("responsibilities", [])),
                achievements=self._ensure_list(entry.get("achievements", [])),
                technologiesUsed=self._ensure_list(entry.get("technologiesUsed", entry.get("technologies_used", [])))
            ))
        
        return work_history
    
    def _map_projects(self, projects_data: List[Dict[str, Any]]) -> List[Project]:
        """Map project entries"""
        if not projects_data:
            return []
        
        projects = []
        for entry in projects_data:
            projects.append(Project(
                projectName=entry.get("projectName", entry.get("project_name", "")),
                clientName=entry.get("clientName", entry.get("client_name", "")),
                organization=entry.get("organization", ""),
                role=entry.get("role", ""),
                
                durationFrom=entry.get("durationFrom", entry.get("duration_from", "")),
                durationTo=entry.get("durationTo", entry.get("duration_to", "")),
                isCurrentProject=entry.get("isCurrentProject", entry.get("is_current_project", False)),
                projectLocation=entry.get("projectLocation", entry.get("project_location", "")),
                
                projectDescription=entry.get("projectDescription", entry.get("project_description", "")),
                responsibilities=self._ensure_list(entry.get("responsibilities", [])),
                outcomes=self._ensure_list(entry.get("outcomes", [])),
                
                environment=self._ensure_list(entry.get("environment", [])),
                toolsUsed=self._ensure_list(entry.get("toolsUsed", entry.get("tools_used", []))),
                teamSize=entry.get("teamSize", entry.get("team_size", "")),
                methodology=entry.get("methodology", ""),
                domain=entry.get("domain", ""),
                
                hardwareDetails=entry.get("hardwareDetails", entry.get("hardware_details", "")),
                softwareDetails=entry.get("softwareDetails", entry.get("software_details", ""))
            ))
        
        return projects
    
    # ============================================================================
    # EDUCATION MAPPING
    # ============================================================================
    
    def _map_education(self, raw_data: Dict[str, Any]) -> List[Education]:
        """Map education entries"""
        education_data = raw_data.get("education", [])
        
        if not education_data:
            return []
        
        education = []
        for entry in education_data:
            education.append(Education(
                degree=entry.get("degree", ""),
                specialization=entry.get("specialization", ""),
                institution=entry.get("institution", ""),
                university=entry.get("university", ""),
                board=entry.get("board", ""),
                
                yearOfPassing=entry.get("yearOfPassing", entry.get("year_of_passing", "")),
                percentage=entry.get("percentage", ""),
                cgpa=entry.get("cgpa", ""),
                grade=entry.get("grade", ""),
                location=entry.get("location", "")
            ))
        
        return education
    
    # ============================================================================
    # CERTIFICATIONS MAPPING
    # ============================================================================
    
    def _map_certifications(self, raw_data: Dict[str, Any]) -> List[Certification]:
        """Map certification entries"""
        cert_data = raw_data.get("certifications", [])
        
        if not cert_data:
            return []
        
        certifications = []
        for entry in cert_data:
            certifications.append(Certification(
                name=entry.get("name", ""),
                issuingOrganization=entry.get("issuingOrganization", entry.get("issuing_organization", "")),
                issueDate=entry.get("issueDate", entry.get("issue_date", "")),
                expiryDate=entry.get("expiryDate", entry.get("expiry_date", "")),
                credentialId=entry.get("credentialId", entry.get("credential_id", "")),
                credentialUrl=entry.get("credentialUrl", entry.get("credential_url", ""))
            ))
        
        return certifications
    
    # ============================================================================
    # ACHIEVEMENTS MAPPING
    # ============================================================================
    
    def _map_achievements(self, raw_data: Dict[str, Any]) -> List[Achievement]:
        """Map achievement entries"""
        achievement_data = raw_data.get("achievements", [])
        
        if not achievement_data:
            return []
        
        achievements = []
        for entry in achievement_data:
            achievements.append(Achievement(
                title=entry.get("title", ""),
                description=entry.get("description", ""),
                date=entry.get("date", "")
            ))
        
        return achievements
    
    # ============================================================================
    # PERSONAL DETAILS MAPPING
    # ============================================================================
    
    def _map_personal_details(self, raw_data: Dict[str, Any]) -> PersonalDetails:
        """Map personal details"""
        personal_data = raw_data.get("personalDetails", raw_data.get("personal_details", {}))
        
        return PersonalDetails(
            languagesKnown=self._ensure_list(personal_data.get("languagesKnown", personal_data.get("languages_known", []))),
            maritalStatus=personal_data.get("maritalStatus", personal_data.get("marital_status", "")),
            passportNumber=personal_data.get("passportNumber", personal_data.get("passport_number", "")),
            
            linkedinUrl=personal_data.get("linkedinUrl", personal_data.get("linkedin_url", "")),
            githubUrl=personal_data.get("githubUrl", personal_data.get("github_url", "")),
            portfolioUrl=personal_data.get("portfolioUrl", personal_data.get("portfolio_url", ""))
        )
    
    # ============================================================================
    # METADATA MAPPING
    # ============================================================================
    
    def _map_attachments_metadata(self, raw_data: Dict[str, Any], source_type: str) -> AttachmentsMetadata:
        """Map attachments metadata"""
        metadata = raw_data.get("attachmentsMetadata", raw_data.get("attachments_metadata", {}))
        
        return AttachmentsMetadata(
            inputFileName=metadata.get("inputFileName", metadata.get("input_file_name", "")),
            inputFileType=metadata.get("inputFileType", metadata.get("input_file_type", source_type)),
            audioTranscriptId=metadata.get("audioTranscriptId", metadata.get("audio_transcript_id", "")),
            documentParserVersion=metadata.get("documentParserVersion", metadata.get("document_parser_version", "1.0")),
            extractionConfidence=metadata.get("extractionConfidence", metadata.get("extraction_confidence", ""))
        )
    
    def _map_audit(self, raw_data: Dict[str, Any], source_type: str) -> Audit:
        """Map audit information"""
        audit_data = raw_data.get("audit", {})
        
        now = datetime.now().isoformat()
        
        return Audit(
            createdBy=audit_data.get("createdBy", audit_data.get("created_by", "")),
            createdAt=audit_data.get("createdAt", audit_data.get("created_at", now)),
            updatedAt=audit_data.get("updatedAt", audit_data.get("updated_at", now)),
            lastValidatedAt=audit_data.get("lastValidatedAt", audit_data.get("last_validated_at", "")),
            sourceChannel=audit_data.get("sourceChannel", audit_data.get("source_channel", source_type)),
            manualEdits=[]
        )
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def _ensure_list(self, value: Any) -> List[str]:
        """
        Ensure value is a list of strings.
        
        Args:
            value: Value to convert to list
            
        Returns:
            List[str]: Converted list
        """
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item]
        if isinstance(value, str) and value:
            return [value]
        return []
    
    def _safe_get(self, data: Dict[str, Any], *keys: str, default: Any = "") -> Any:
        """
        Safely get nested dictionary values.
        
        Args:
            data: Dictionary to query
            keys: Keys to try in order
            default: Default value if none found
            
        Returns:
            Any: Found value or default
        """
        for key in keys:
            if key in data and data[key]:
                return data[key]
        return default
    
    def convert_to_dict(self, canonical_cv: CanonicalCVSchema) -> Dict[str, Any]:
        """
        Convert Canonical CV Schema to dictionary.
        
        Args:
            canonical_cv: Canonical CV schema instance
            
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return canonical_cv.model_dump()
    
    def convert_from_dict(self, cv_dict: Dict[str, Any]) -> CanonicalCVSchema:
        """
        Convert dictionary to Canonical CV Schema.
        
        Args:
            cv_dict: Dictionary representation
            
        Returns:
            CanonicalCVSchema: Canonical CV schema instance
        """
        return CanonicalCVSchema(**cv_dict)
    
    def get_mandatory_fields(self) -> List[str]:
        """
        Get list of mandatory field paths for validation.
        
        Returns:
            List[str]: Dot-notation paths of mandatory fields
        """
        return [
            "candidate.fullName",
            "candidate.email",
            "candidate.currentLocation.city",
            "candidate.currentLocation.country"
        ]
    
    def validate_mandatory_fields(self, canonical_cv: CanonicalCVSchema) -> Dict[str, List[str]]:
        """
        Validate that mandatory fields are populated.
        
        Args:
            canonical_cv: Canonical CV to validate
            
        Returns:
            Dict with 'valid' (bool) and 'missing_fields' (List[str])
        """
        missing_fields = []
        
        # Check mandatory fields
        if not canonical_cv.candidate.fullName:
            missing_fields.append("candidate.fullName")
        
        if not canonical_cv.candidate.email:
            missing_fields.append("candidate.email")
        
        if not canonical_cv.candidate.currentLocation.city:
            missing_fields.append("candidate.currentLocation.city")
        
        if not canonical_cv.candidate.currentLocation.country:
            missing_fields.append("candidate.currentLocation.country")
        
        return {
            "valid": len(missing_fields) == 0,
            "missing_fields": missing_fields
        }


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

# Create singleton instance for easy import
schema_mapper_service = SchemaMapperService()
