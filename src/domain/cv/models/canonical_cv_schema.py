"""
Canonical CV Schema v1.1

This module defines the single source of truth for CV data across all input modes.
All extractors (audio, bot, recording, DOCX/PDF) must map to this schema.

Schema Version: 1.1
Last Updated: 2026-04-12
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import AliasChoices, BaseModel, Field, ConfigDict
from src.domain.cv.enums import SourceType


# ============================================================================
# LOCATION MODELS
# ============================================================================

class LocationModel(BaseModel):
    """Location information"""
    city: Optional[str] = Field(default="", description="City name")
    state: Optional[str] = Field(default="", description="State/Province")
    country: Optional[str] = Field(default="", description="Country name")
    fullAddress: Optional[str] = Field(default="", description="Complete address")


# ============================================================================
# CANDIDATE INFORMATION
# ============================================================================

class CandidateModel(BaseModel):
    """Core candidate personal and professional information"""
    
    # Basic Identity
    fullName: Optional[str] = Field(default="", description="Complete name")
    firstName: Optional[str] = Field(default="", description="First name")
    middleName: Optional[str] = Field(default="", description="Middle name")
    lastName: Optional[str] = Field(default="", description="Last name")
    
    # Contact Information
    phoneNumber: Optional[str] = Field(default="", description="Primary phone")
    alternatePhoneNumber: Optional[str] = Field(default="", description="Alternate phone")
    email: Optional[str] = Field(default="", description="Email address")
    
    # Professional Identity
    portalId: Optional[str] = Field(default="", description="Employee/Portal ID")
    
    # Personal Details
    dateOfBirth: Optional[str] = Field(default="", description="Date of birth (YYYY-MM-DD)")
    gender: Optional[str] = Field(default="", description="Gender")
    nationality: Optional[str] = Field(default="", description="Nationality")
    
    # Location
    currentLocation: LocationModel = Field(default_factory=LocationModel, description="Current location")
    preferredLocation: List[str] = Field(default_factory=list, description="Preferred work locations")
    
    # Experience Summary
    totalExperienceYears: Optional[int] = Field(default=0, description="Total years of experience")
    totalExperienceMonths: Optional[int] = Field(default=0, description="Total months (additional)")
    relevantExperienceYears: Optional[int] = Field(default=0, description="Relevant years")
    relevantExperienceMonths: Optional[int] = Field(default=0, description="Relevant months")
    
    # Current Employment
    currentOrganization: Optional[str] = Field(default="", description="Current employer")
    currentDesignation: Optional[str] = Field(default="", description="Current job title")
    currentCTC: Optional[str] = Field(default="", description="Current compensation")
    expectedCTC: Optional[str] = Field(default="", description="Expected compensation")
    noticePeriod: Optional[str] = Field(default="", description="Notice period")
    employmentType: Optional[str] = Field(default="", description="Full-time/Contract/etc")
    
    # Professional Summary
    summary: Optional[str] = Field(
        default="",
        description="Professional summary",
        validation_alias=AliasChoices("summary", "professionalSummary", "Professional Summary"),
    )
    careerObjective: Optional[str] = Field(default="", description="Career objective")


# ============================================================================
# SKILLS INFORMATION
# ============================================================================

class SkillsModel(BaseModel):
    """Comprehensive skills categorization"""
    
    primarySkills: List[str] = Field(default_factory=list, description="Primary/Core skills")
    secondarySkills: List[str] = Field(default_factory=list, description="Secondary skills")
    technicalSkills: List[str] = Field(default_factory=list, description="Technical skills")
    functionalSkills: List[str] = Field(default_factory=list, description="Functional/Domain skills")
    softSkills: List[str] = Field(default_factory=list, description="Soft skills")
    
    toolsAndPlatforms: List[str] = Field(default_factory=list, description="Tools and platforms")
    operatingSystems: List[str] = Field(default_factory=list, description="Operating systems")
    databases: List[str] = Field(default_factory=list, description="Database technologies")
    cloudTechnologies: List[str] = Field(default_factory=list, description="Cloud platforms")
    frameworks: List[str] = Field(default_factory=list, description="Frameworks")
    libraries: List[str] = Field(default_factory=list, description="Libraries")
    aiToolsAndFrameworks: List[str] = Field(default_factory=list, description="AI/ML tools")
    certificationsSkillsTagged: List[str] = Field(default_factory=list, description="Skills from certifications")


# ============================================================================
# WORK HISTORY
# ============================================================================

class WorkHistoryModel(BaseModel):
    """Employment history entry"""
    
    organization: Optional[str] = Field(default="", description="Company name")
    designation: Optional[str] = Field(default="", description="Job title")
    employmentStartDate: Optional[str] = Field(default="", description="Start date (YYYY-MM)")
    employmentEndDate: Optional[str] = Field(default="", description="End date (YYYY-MM)")
    isCurrentCompany: bool = Field(default=False, description="Is this current employer")
    location: Optional[str] = Field(default="", description="Work location")
    
    responsibilities: List[str] = Field(default_factory=list, description="Key responsibilities")
    achievements: List[str] = Field(default_factory=list, description="Achievements")
    technologiesUsed: List[str] = Field(default_factory=list, description="Technologies used")


# ============================================================================
# PROJECT INFORMATION
# ============================================================================

class ProjectModel(BaseModel):
    """Project details"""
    
    projectName: Optional[str] = Field(default="", description="Project name")
    clientName: Optional[str] = Field(default="", description="Client name")
    organization: Optional[str] = Field(default="", description="Organization")
    role: Optional[str] = Field(default="", description="Role in project")
    
    durationFrom: Optional[str] = Field(default="", description="Start date (YYYY-MM)")
    durationTo: Optional[str] = Field(default="", description="End date (YYYY-MM)")
    isCurrentProject: bool = Field(default=False, description="Is this current project")
    projectLocation: Optional[str] = Field(default="", description="Project location")
    
    projectDescription: Optional[str] = Field(default="", description="Project description")
    responsibilities: List[str] = Field(default_factory=list, description="Responsibilities")
    outcomes: List[str] = Field(default_factory=list, description="Project outcomes")
    
    environment: List[str] = Field(default_factory=list, description="Technical environment")
    toolsUsed: List[str] = Field(default_factory=list, description="Tools used")
    teamSize: Optional[str] = Field(default="", description="Team size")
    methodology: Optional[str] = Field(default="", description="Methodology (Agile/Waterfall)")
    domain: Optional[str] = Field(default="", description="Domain/Industry")
    
    hardwareDetails: Optional[str] = Field(default="", description="Hardware specifications")
    softwareDetails: Optional[str] = Field(default="", description="Software details")


# ============================================================================
# EXPERIENCE INFORMATION
# ============================================================================

class ExperienceModel(BaseModel):
    """Consolidated experience information"""
    
    totalProjects: int = Field(default=0, description="Total number of projects")
    domainExperience: List[str] = Field(default_factory=list, description="Domain expertise areas")
    industriesWorked: List[str] = Field(default_factory=list, description="Industries worked in")
    
    workHistory: List[WorkHistoryModel] = Field(default_factory=list, description="Employment history")
    projects: List[ProjectModel] = Field(default_factory=list, description="Project details")


# ============================================================================
# EDUCATION
# ============================================================================

class EducationModel(BaseModel):
    """Education qualification"""
    
    degree: Optional[str] = Field(default="", description="Degree name")
    specialization: Optional[str] = Field(default="", description="Specialization/Major")
    institution: Optional[str] = Field(default="", description="Institution name")
    university: Optional[str] = Field(default="", description="University/Board")
    board: Optional[str] = Field(default="", description="Board (for school)")
    
    yearOfPassing: Optional[str] = Field(default="", description="Year of passing")
    percentage: Optional[str] = Field(
        default="",
        description="Percentage",
        validation_alias=AliasChoices("percentage", "Percentile"),
    )
    percentile: Optional[str] = Field(default="", description="Percentile")
    cgpa: Optional[str] = Field(default="", description="CGPA")
    grade: Optional[str] = Field(default="", description="Grade")
    location: Optional[str] = Field(default="", description="Location")


# ============================================================================
# CERTIFICATIONS
# ============================================================================

class CertificationModel(BaseModel):
    """Professional certification"""
    
    name: Optional[str] = Field(default="", description="Certification name")
    issuingOrganization: Optional[str] = Field(default="", description="Issuing organization")
    issueDate: Optional[str] = Field(default="", description="Issue date (YYYY-MM)")
    expiryDate: Optional[str] = Field(default="", description="Expiry date (YYYY-MM)")
    credentialId: Optional[str] = Field(default="", description="Credential ID")
    credentialUrl: Optional[str] = Field(default="", description="Credential URL")


# ============================================================================
# ACHIEVEMENTS
# ============================================================================

class AchievementModel(BaseModel):
    """Professional achievement"""
    
    title: Optional[str] = Field(default="", description="Achievement title")
    description: Optional[str] = Field(default="", description="Description")
    date: Optional[str] = Field(default="", description="Date (YYYY-MM)")


# ============================================================================
# PERSONAL DETAILS
# ============================================================================

class PersonalDetailsModel(BaseModel):
    """Additional personal information"""
    
    languagesKnown: List[str] = Field(default_factory=list, description="Languages known")
    maritalStatus: Optional[str] = Field(default="", description="Marital status")
    passportNumber: Optional[str] = Field(default="", description="Passport number")
    
    linkedinUrl: Optional[str] = Field(default="", description="LinkedIn profile URL")
    githubUrl: Optional[str] = Field(default="", description="GitHub profile URL")
    portfolioUrl: Optional[str] = Field(default="", description="Portfolio URL")


# ============================================================================
# ATTACHMENTS METADATA
# ============================================================================

class AttachmentsMetadataModel(BaseModel):
    """Metadata about input files and extraction process"""
    
    inputFileName: Optional[str] = Field(default="", description="Original input filename")
    inputFileType: Optional[str] = Field(default="", description="File type (audio/docx/pdf)")
    audioTranscriptId: Optional[str] = Field(default="", description="Transcript ID for audio")
    documentParserVersion: Optional[str] = Field(default="", description="Parser version")
    extractionConfidence: Optional[str] = Field(default="", description="Confidence score")


# ============================================================================
# AUDIT TRAIL
# ============================================================================

class ManualEditModel(BaseModel):
    """Record of manual edits"""
    
    field: str = Field(description="Field path that was edited")
    previousValue: Optional[str] = Field(default=None, description="Previous value")
    newValue: Optional[str] = Field(default=None, description="New value")
    editedBy: Optional[str] = Field(default="", description="User who made edit")
    editedAt: Optional[str] = Field(default="", description="Timestamp of edit")
    editReason: Optional[str] = Field(default="", description="Reason for edit")


class AuditModel(BaseModel):
    """Audit trail for tracking changes"""
    
    createdBy: Optional[str] = Field(default="", description="Creator user ID")
    createdAt: Optional[str] = Field(default="", description="Creation timestamp")
    updatedAt: Optional[str] = Field(default="", description="Last update timestamp")
    lastValidatedAt: Optional[str] = Field(default="", description="Last validation timestamp")
    sourceChannel: Optional[str] = Field(default="", description="Input source (audio/bot/recording/docx)")
    
    manualEdits: List[ManualEditModel] = Field(default_factory=list, description="History of manual edits")


# ============================================================================
# CANONICAL CV SCHEMA (ROOT)
# ============================================================================

class CanonicalCVSchema(BaseModel):
    """
    Canonical CV Schema v1.1
    
    This is the SINGLE SOURCE OF TRUTH for all CV data across the application.
    All input channels (audio upload, recording, bot conversation, DOCX/PDF)
    must map to this schema, and all outputs must read from it.
    
    Usage:
        # Create new CV
        cv = CanonicalCVSchema(
            cvId="12345",
            sourceType="audio_upload",
            candidate=CandidateModel(fullName="John Doe", ...)
        )
        
        # Convert to dict for session storage
        cv_dict = cv.model_dump()
        
        # Load from dict
        cv = CanonicalCVSchema(**cv_dict)
    """
    
    # Root Metadata
    schema_version: str = Field(default="1.1", description="Schema version")
    cvId: Optional[str] = Field(default="", description="Unique CV identifier")
    sourceType: Optional[str] = Field(default="", description="Input source (audio/bot/recording/docx)")
    
    # Main Sections
    candidate: CandidateModel = Field(default_factory=CandidateModel, description="Candidate information")
    skills: SkillsModel = Field(default_factory=SkillsModel, description="Skills information")
    experience: ExperienceModel = Field(default_factory=ExperienceModel, description="Experience details")
    education: List[EducationModel] = Field(default_factory=list, description="Education qualifications")
    certifications: List[CertificationModel] = Field(default_factory=list, description="Certifications")
    achievements: List[AchievementModel] = Field(default_factory=list, description="Achievements")
    personalDetails: PersonalDetailsModel = Field(default_factory=PersonalDetailsModel, description="Personal details")
    
    # Metadata and Audit
    attachmentsMetadata: AttachmentsMetadataModel = Field(default_factory=AttachmentsMetadataModel, description="File metadata")
    audit: AuditModel = Field(default_factory=AuditModel, description="Audit trail")

    # Data-loss prevention extensions
    unmappedData: Dict[str, Any] = Field(
        default_factory=dict,
        description="Source-scoped unmapped details that could not be mapped to canonical fields",
    )
    sourceSnapshots: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw/source snapshots captured during extraction and normalization",
    )
    mappingWarnings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Warnings generated while mapping source data into canonical fields",
    )
    
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        json_schema_extra={
            "example": {
                "schema_version": "1.1",
                "cvId": "cv_12345",
                "sourceType": "audio_upload",
                "candidate": {
                    "fullName": "John Doe",
                    "email": "john.doe@example.com",
                    "phoneNumber": "1234567890",
                    "currentLocation": {
                        "city": "Mumbai",
                        "country": "India"
                    }
                },
                "skills": {
                    "primarySkills": ["Python", "FastAPI", "MongoDB"]
                }
            }
        }
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_empty_canonical_cv(cv_id: str = "", source_type: str = "") -> dict:
    """
    Create an empty Canonical CV Schema as a dictionary.
    
    Args:
        cv_id: Unique CV identifier
        source_type: Input source type (audio/bot/recording/docx)
        
    Returns:
        dict: Empty canonical CV as serializable dictionary
    """
    cv = CanonicalCVSchema(
        cvId=cv_id,
        sourceType=source_type,
        audit=AuditModel(
            createdAt=datetime.now().isoformat(),
            sourceChannel=source_type
        )
    )
    return cv.model_dump()


def validate_canonical_cv(cv_dict: dict) -> bool:
    """
    Validate if a dictionary conforms to Canonical CV Schema.
    
    Args:
        cv_dict: Dictionary to validate
        
    Returns:
        bool: True if valid, raises ValidationError if invalid
    """
    try:
        CanonicalCVSchema(**cv_dict)
        return True
    except Exception as e:
        raise ValueError(f"Invalid Canonical CV Schema: {str(e)}")


def get_canonical_schema_version() -> str:
    """Get current Canonical CV Schema version"""
    return "1.1"


def get_empty_schema(cv_id: str = "", source_type: str = "") -> CanonicalCVSchema:
    """
    Create an empty Canonical CV Schema object.
    
    Args:
        cv_id: Unique CV identifier
        source_type: Input source type (audio/bot/recording/docx)
        
    Returns:
        CanonicalCVSchema: Empty canonical CV instance
    """
    return CanonicalCVSchema(
        cvId=cv_id,
        sourceType=source_type,
        audit=AuditModel(
            createdAt=datetime.now().isoformat(),
            updatedAt=datetime.now().isoformat(),
            sourceChannel=source_type
        )
    )


def merge_partial_data(base_schema: CanonicalCVSchema, partial_data: dict) -> CanonicalCVSchema:
    """
    Merge partial data into an existing Canonical CV Schema.
    
    This function intelligently merges new data without overwriting existing values.
    Empty strings and empty lists in partial_data are ignored.
    
    Args:
        base_schema: Existing canonical CV schema
        partial_data: New data to merge (can be incomplete)
        
    Returns:
        CanonicalCVSchema: Updated schema with merged data
    """
    # Convert base schema to dict
    base_dict = base_schema.model_dump()
    
    # Recursively merge the partial data
    def deep_merge(base: dict, updates: dict) -> dict:
        """Recursively merge dictionaries, preserving existing non-empty values"""
        for key, value in updates.items():
            if key not in base:
                base[key] = value
            elif isinstance(value, dict) and isinstance(base[key], dict):
                base[key] = deep_merge(base[key], value)
            elif isinstance(value, list) and value:  # Only merge non-empty lists
                if isinstance(base[key], list):
                    # Merge lists, avoiding duplicates for strings
                    if base[key] and isinstance(base[key][0], str):
                        base[key] = list(set(base[key] + value))
                    else:
                        base[key].extend(value)
                else:
                    base[key] = value
            elif value not in [None, "", []]:  # Only update if new value is not empty
                base[key] = value
        return base
    
    merged_dict = deep_merge(base_dict, partial_data)
    
    # Update audit trail
    merged_dict["audit"]["updatedAt"] = datetime.now().isoformat()
    
    return CanonicalCVSchema(**merged_dict)


def mark_field_as_manually_edited(
    schema: CanonicalCVSchema,
    field_path: str,
    previous_value: str,
    new_value: str,
    edited_by: str = "user"
) -> CanonicalCVSchema:
    """
    Mark a field as manually edited and update audit trail.
    
    Args:
        schema: Canonical CV schema to update
        field_path: Dot-notation path to the field (e.g., "candidate.phoneNumber")
        previous_value: Previous value of the field
        new_value: New value of the field
        edited_by: User who made the edit
        
    Returns:
        CanonicalCVSchema: Updated schema with audit trail
    """
    # Create manual edit record
    manual_edit = ManualEditModel(
        field=field_path,
        previousValue=previous_value,
        newValue=new_value,
        editedBy=edited_by,
        editedAt=datetime.now().isoformat(),
        editReason="Manual edit via UI"
    )
    
    # Convert to dict, update, and recreate
    schema_dict = schema.model_dump()
    schema_dict["audit"]["manualEdits"].append(manual_edit.model_dump())
    schema_dict["audit"]["updatedAt"] = datetime.now().isoformat()
    
    return CanonicalCVSchema(**schema_dict)


# ============================================================================
# TYPE ALIASES FOR BACKWARD COMPATIBILITY
# ============================================================================

# These aliases allow importing classes without the "Model" suffix
# Example: from canonical_cv_schema import Candidate, Skills, etc.
CurrentLocation = LocationModel
Candidate = CandidateModel
Skills = SkillsModel
Experience = ExperienceModel
WorkHistory = WorkHistoryModel
Project = ProjectModel
Education = EducationModel
Certification = CertificationModel
Achievement = AchievementModel
PersonalDetails = PersonalDetailsModel
AttachmentsMetadata = AttachmentsMetadataModel
Audit = AuditModel
ManualEdit = ManualEditModel
