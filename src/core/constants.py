"""
Application-wide constants.
AI-related configurations should be in .env file.
"""

# CV Schema Version
CV_SCHEMA_VERSION = "1.0"

# Section Names
REQUIRED_SECTIONS = [
    "personal_details",
    "summary",
    "skills",
    "work_experience",
    "education"
]

OPTIONAL_SECTIONS = [
    "project_experience",
    "certifications",
    "publications",
    "awards",
    "languages",
    "leadership"
]

ALL_SECTIONS = REQUIRED_SECTIONS + OPTIONAL_SECTIONS

# Required Fields for Validation
REQUIRED_PERSONAL_FIELDS = [
    "full_name",
    "email",
    "phone"
]

# Skill Categories
SKILL_CATEGORIES = [
    "Primary Skills",
    "Operating Systems",
    "Languages",
    "Development Tools",
    "Frameworks",
    "Cloud Platforms",
    "Databases",
    "CRM Tools",
    "SQL Skills",
    "Other Tools"
]

# Quality Thresholds
COMPLETENESS_THRESHOLD_PREVIEW = 60  # Minimum % to allow preview
COMPLETENESS_THRESHOLD_EXPORT = 80   # Minimum % to allow export

# Extraction Methods
EXTRACTION_METHOD_AI = "AI"
EXTRACTION_METHOD_FALLBACK = "Fallback"

# Validation Priorities
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

# File Upload Limits
MAX_FILE_SIZE_MB = 10
ALLOWED_FILE_EXTENSIONS = [".pdf", ".docx", ".doc", ".txt"]

# Status Values
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
