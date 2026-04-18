# Load environment variables first
from src.core.env_loader import load_environment_variables
load_environment_variables()

import builtins
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.core.config.settings import settings
from src.core.constants import APP_JS_PATH, HEALTH_PATH, HEALTH_STATUS_OK, INDEX_PATH, ROOT_PATH, STYLES_PATH
from src.infrastructure.persistence.mysql.database import ensure_schema_initialized
from src.interfaces.rest.routers.auth_router import router as auth_router
from src.interfaces.rest.routers.chat_router import router as chat_router
from src.interfaces.rest.routers.cv_router import router as cv_router
from src.interfaces.rest.routers.export_router import router as export_router
from src.interfaces.rest.routers.preview_router import router as preview_router
from src.interfaces.rest.routers.questionnaire_router import router as questionnaire_router
from src.interfaces.rest.routers.retrieval_router import router as retrieval_router
from src.interfaces.rest.routers.review_router import router as review_router
from src.interfaces.rest.routers.session_router import router as session_router
from src.interfaces.rest.routers.speech_router import router as speech_router
from src.interfaces.rest.routers.template_router import router as template_router
from src.interfaces.rest.routers.validation_router import router as validation_router
from apps.api.middleware.auth import AuthMiddleware


if settings.SUPPRESS_CONSOLE_PRINTS:
    # Keep logging intact and suppress legacy/debug print() noise in server console.
    builtins.print = lambda *args, **kwargs: None

# Import logging early and initialize file logging
from src.core.logging.logger import get_logger
logger = get_logger(__name__)

# Get the project root directory (2 levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
WEB_UI_DIR = BASE_DIR / "web-ui"
WEB_UI_TEMPLATES_DIR = WEB_UI_DIR / "templates"
WEB_UI_STATIC_DIR = WEB_UI_DIR / "static"

# Validate and fallback if needed
if not WEB_UI_DIR.exists():
    logger.warning(f"WEB_UI_DIR not found at {WEB_UI_DIR}, trying current working directory")
    WEB_UI_DIR = Path.cwd() / "web-ui"

if not WEB_UI_DIR.exists():
    logger.error(f"Cannot locate web UI directory at {WEB_UI_DIR}")
    raise FileNotFoundError(f"web UI directory not found. Tried: {BASE_DIR / 'web-ui'} and {Path.cwd() / 'web-ui'}")

if not WEB_UI_TEMPLATES_DIR.exists() or not WEB_UI_STATIC_DIR.exists():
    logger.error(
        f"Invalid web UI structure. templates={WEB_UI_TEMPLATES_DIR.exists()} static={WEB_UI_STATIC_DIR.exists()}"
    )
    raise FileNotFoundError(
        f"web UI structure invalid. Expected: {WEB_UI_TEMPLATES_DIR} and {WEB_UI_STATIC_DIR}"
    )

# Log directory paths for debugging
logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"WEB_UI_DIR: {WEB_UI_DIR.resolve()}")
logger.info(f"WEB_UI_DIR exists: {WEB_UI_DIR.exists()}")
logger.info(f"WEB_UI_TEMPLATES_DIR exists: {WEB_UI_TEMPLATES_DIR.exists()}")
logger.info(f"WEB_UI_STATIC_DIR exists: {WEB_UI_STATIC_DIR.exists()}")

if WEB_UI_DIR.exists():
    files = list(WEB_UI_DIR.iterdir())
    logger.info(f"Files in WEB_UI_DIR ({len(files)} files): {[f.name for f in files]}")

# Initialize database schema on startup
logger.info("Initializing database schema...")
try:
    ensure_schema_initialized()
    logger.info("Database schema validated successfully")
except Exception as e:
    logger.error(f"Failed to initialize database schema: {e}")
    raise

app = FastAPI(title="Conversational CV Builder API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add auth middleware — runs after CORS, populates request-scoped user context
app.add_middleware(AuthMiddleware)

@app.get(HEALTH_PATH)
def health():
    return {"status": HEALTH_STATUS_OK}

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(session_router)
app.include_router(preview_router)
app.include_router(export_router)
app.include_router(cv_router)
app.include_router(validation_router)
app.include_router(retrieval_router)
app.include_router(speech_router)
app.include_router(questionnaire_router)
app.include_router(template_router)
app.include_router(review_router)

@app.get(ROOT_PATH)
def home():
    return FileResponse(str(WEB_UI_TEMPLATES_DIR / "index.html"))

@app.get(INDEX_PATH)
def index():
    return FileResponse(str(WEB_UI_TEMPLATES_DIR / "index.html"))

@app.get("/preview-renderer-test.html")
def preview_renderer_test():
    return FileResponse(str(WEB_UI_TEMPLATES_DIR / "preview-renderer-test.html"))

@app.get(STYLES_PATH)
def styles():
    css_path = WEB_UI_STATIC_DIR / "css" / "styles.css"
    logger.info(f"Serving styles.css from: {css_path.resolve()}")
    logger.info(f"File exists: {css_path.exists()}")
    if not css_path.exists():
        logger.error(f"styles.css not found at {css_path.resolve()}")
        return {"error": "styles.css not found"}, 404
    return FileResponse(str(css_path), media_type="text/css")

@app.get(APP_JS_PATH)
def app_js():
    js_path = WEB_UI_STATIC_DIR / "js" / "app.js"
    logger.info(f"Serving app.js from: {js_path.resolve()}")
    logger.info(f"File exists: {js_path.exists()}")
    if not js_path.exists():
        logger.error(f"app.js not found at {js_path.resolve()}")
        return {"error": "app.js not found"}, 404
    return FileResponse(str(js_path), media_type="application/javascript")

@app.get("/nttdata_logo.png")
def serve_logo():
    logo_path = WEB_UI_STATIC_DIR / "img" / "nttdata_logo.png"
    logger.info(f"Serving logo from: {logo_path.resolve()}")
    logger.info(f"File exists: {logo_path.exists()}")
    if not logo_path.exists():
        logger.error(f"Logo not found at {logo_path.resolve()}")
        return {"error": "Logo not found"}, 404
    return FileResponse(str(logo_path), media_type="image/png")

# Mount static files after defining routes to avoid conflicts
if WEB_UI_STATIC_DIR.exists():
    try:
        app.mount("/static", StaticFiles(directory=str(WEB_UI_STATIC_DIR)), name="static")
        logger.info(f"Static files mounted successfully from: {WEB_UI_STATIC_DIR}")
    except Exception as e:
        logger.error(f"Failed to mount static files from {WEB_UI_STATIC_DIR}: {e}")
        raise
else:
    logger.error(f"Static files directory not found: {WEB_UI_STATIC_DIR}")
    raise FileNotFoundError(f"web UI static directory not found at {WEB_UI_STATIC_DIR}")
