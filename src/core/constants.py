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
MAX_FILE_SIZE_MB = 10          # CV documents (PDF, DOCX)
MAX_AUDIO_FILE_SIZE_MB = 25   # Audio uploads — ~12 min @ 256 kbps; OpenAI Whisper hard cap is 25 MB
ALLOWED_FILE_EXTENSIONS = [".pdf", ".docx", ".doc", ".txt"]

# Status Values
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# Security / Auth constants
AUTH_PREFIX = "/auth"
AUTH_TOKEN_PATH = "/token"
AUTH_TOKEN_URL = "/auth/token"
AUTH_ME_PATH = "/me"
AUTH_TAG = "auth"
BEARER_TOKEN_TYPE = "bearer"
AUTH_HEADER_NAME = "Authorization"
AUTH_HEADER_PREFIX = "Bearer "
WWW_AUTHENTICATE_HEADER = "WWW-Authenticate"
WWW_AUTHENTICATE_BEARER = "Bearer"

JWT_SUB_CLAIM = "sub"
JWT_USER_ID_CLAIM = "user_id"
JWT_ROLE_CLAIM = "role"
JWT_EMAIL_CLAIM = "email"
JWT_FULL_NAME_CLAIM = "full_name"
JWT_EXP_CLAIM = "exp"

ERR_NOT_AUTHENTICATED = "Not authenticated"
ERR_INVALID_TOKEN_PAYLOAD = "Invalid token payload"
ERR_USER_NOT_FOUND_OR_INACTIVE = "User not found or inactive"
ERR_COULD_NOT_VALIDATE_CREDENTIALS = "Could not validate credentials"
ERR_INCORRECT_USERNAME_OR_PASSWORD = "Incorrect username or password"
ERR_ACCOUNT_DISABLED = "Account is disabled"

DEV_USER_ID = 0
DEV_USERNAME = "dev_user"
DEV_EMAIL = "dev@local"
DEV_FULL_NAME = "Dev User"

# App/API route constants
HEALTH_PATH = "/health"
ROOT_PATH = "/"
INDEX_PATH = "/index.html"
STYLES_PATH = "/styles.css"
APP_JS_PATH = "/app.js"
HEALTH_STATUS_OK = "ok"

# Middleware/public paths
PUBLIC_PATHS = (
    AUTH_TOKEN_URL,
    "/docs",
    "/redoc",
    "/openapi.json",
    HEALTH_PATH,
    ROOT_PATH,
)

# Database constants
DB_DIALECT = "mysql"
DB_DRIVER = "pymysql"
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 20
