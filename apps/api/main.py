from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.interfaces.rest.routers.cv_router import router as cv_router
from src.interfaces.rest.routers.export_router import router as export_router
from src.interfaces.rest.routers.preview_router import router as preview_router
from src.interfaces.rest.routers.retrieval_router import router as retrieval_router
from src.interfaces.rest.routers.session_router import router as session_router
from src.interfaces.rest.routers.speech_router import router as speech_router
from src.interfaces.rest.routers.validation_router import router as validation_router

app = FastAPI(title="Conversational CV Builder API")

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(session_router)
app.include_router(preview_router)
app.include_router(export_router)
app.include_router(cv_router)
app.include_router(validation_router)
app.include_router(retrieval_router)
app.include_router(speech_router)

try:
    app.mount("/static", StaticFiles(directory="demo-ui"), name="static")

    @app.get("/")
    def home():
        return FileResponse("demo-ui/index.html")

    @app.get("/index.html")
    def index():
        return FileResponse("demo-ui/index.html")
except Exception:
    pass
