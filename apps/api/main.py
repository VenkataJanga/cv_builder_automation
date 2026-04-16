# Load environment variables first
from src.core.env_loader import load_environment_variables
load_environment_variables()

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.interfaces.rest.routers.chat_router import router as chat_router
from src.interfaces.rest.routers.cv_router import router as cv_router
from src.interfaces.rest.routers.export_router import router as export_router
from src.interfaces.rest.routers.preview_router import router as preview_router
from src.interfaces.rest.routers.retrieval_router import router as retrieval_router
from src.interfaces.rest.routers.session_router import router as session_router
from src.interfaces.rest.routers.speech_router import router as speech_router
from src.interfaces.rest.routers.validation_router import router as validation_router

# Import logging early and initialize file logging
from src.core.logging.logger import get_logger
logger = get_logger(__name__)

# Get the project root directory (2 levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEMO_UI_DIR = BASE_DIR / "demo-ui"

# Validate and fallback if needed
if not DEMO_UI_DIR.exists():
    logger.warning(f"DEMO_UI_DIR not found at {DEMO_UI_DIR}, trying current working directory")
    DEMO_UI_DIR = Path.cwd() / "demo-ui"

if not DEMO_UI_DIR.exists():
    logger.error(f"Cannot locate demo-ui directory at {DEMO_UI_DIR}")
    raise FileNotFoundError(f"demo-ui directory not found. Tried: {BASE_DIR / 'demo-ui'} and {Path.cwd() / 'demo-ui'}")

# Log directory paths for debugging
logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"DEMO_UI_DIR: {DEMO_UI_DIR.resolve()}")
logger.info(f"DEMO_UI_DIR exists: {DEMO_UI_DIR.exists()}")

if DEMO_UI_DIR.exists():
    files = list(DEMO_UI_DIR.iterdir())
    logger.info(f"Files in DEMO_UI_DIR ({len(files)} files): {[f.name for f in files]}")

app = FastAPI(title="Conversational CV Builder API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(chat_router)
app.include_router(session_router)
app.include_router(preview_router)
app.include_router(export_router)
app.include_router(cv_router)
app.include_router(validation_router)
app.include_router(retrieval_router)
app.include_router(speech_router)

@app.get("/")
def home():
    return FileResponse(str(DEMO_UI_DIR / "index.html"))

@app.get("/index.html")
def index():
    return FileResponse(str(DEMO_UI_DIR / "index.html"))

@app.get("/styles.css")
def styles():
    css_path = DEMO_UI_DIR / "styles.css"
    logger.info(f"Serving styles.css from: {css_path.resolve()}")
    logger.info(f"File exists: {css_path.exists()}")
    if not css_path.exists():
        logger.error(f"styles.css not found at {css_path.resolve()}")
        return {"error": "styles.css not found"}, 404
    return FileResponse(str(css_path), media_type="text/css")

@app.get("/app.js")
def app_js():
    js_path = DEMO_UI_DIR / "app.js"
    logger.info(f"Serving app.js from: {js_path.resolve()}")
    logger.info(f"File exists: {js_path.exists()}")
    if not js_path.exists():
        logger.error(f"app.js not found at {js_path.resolve()}")
        return {"error": "app.js not found"}, 404
    return FileResponse(str(js_path), media_type="application/javascript")

# Mount static files after defining routes to avoid conflicts
if DEMO_UI_DIR.exists():
    try:
        app.mount("/static", StaticFiles(directory=str(DEMO_UI_DIR)), name="static")
        logger.info(f"Static files mounted successfully from: {DEMO_UI_DIR}")
    except Exception as e:
        logger.error(f"Failed to mount static files from {DEMO_UI_DIR}: {e}")
        raise
else:
    logger.error(f"Static files directory not found: {DEMO_UI_DIR}")
    raise FileNotFoundError(f"demo-ui directory not found at {DEMO_UI_DIR}")
