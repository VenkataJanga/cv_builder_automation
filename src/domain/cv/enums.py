"""
CV Domain Enums

Enumerations for CV-related constants and types.
Part of Canonical CV Schema v1.1
"""

from enum import Enum


class SourceType(str, Enum):
    """
    Input source types for CV data.
    Used to track where the CV data originated from.
    """
    AUDIO_UPLOAD = "audio_upload"
    AUDIO_RECORDING = "audio_recording"  # For start_recording
    BOT_CONVERSATION = "bot_conversation"
    START_RECORDING = "start_recording"
    DOCX_UPLOAD = "docx_upload"
    PDF_UPLOAD = "pdf_upload"
    DOCUMENT_UPLOAD = "document_upload"  # Generic document upload
    MANUAL_ENTRY = "manual_entry"
    MANUAL_EDIT = "manual_edit"  # For manual edits/updates
    
    @classmethod
    def from_string(cls, value: str) -> "SourceType":
        """Convert string to SourceType enum"""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.MANUAL_ENTRY


class ValidationStatus(str, Enum):
    """CV validation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATED = "validated"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class EmploymentType(str, Enum):
    """Employment type options"""
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    FREELANCE = "Freelance"
    INTERNSHIP = "Internship"
    CONSULTANT = "Consultant"


class Gender(str, Enum):
    """Gender options"""
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "Prefer not to say"


class MaritalStatus(str, Enum):
    """Marital status options"""
    SINGLE = "Single"
    MARRIED = "Married"
    DIVORCED = "Divorced"
    WIDOWED = "Widowed"
    PREFER_NOT_TO_SAY = "Prefer not to say"


class SkillCategory(str, Enum):
    """Skill categorization"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TECHNICAL = "technical"
    FUNCTIONAL = "functional"
    SOFT = "soft"
    TOOLS = "tools_and_platforms"
    OS = "operating_systems"
    DATABASE = "databases"
    CLOUD = "cloud_technologies"
    FRAMEWORKS = "frameworks"
    LIBRARIES = "libraries"
    AI_ML = "ai_tools_and_frameworks"
