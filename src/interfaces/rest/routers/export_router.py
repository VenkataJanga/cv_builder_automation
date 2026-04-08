from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from io import BytesIO

from src.application.services.conversation_service import ConversationService
from src.application.services.preview_service import PreviewService
from src.application.services.export_service import ExportService
from src.infrastructure.rendering.template_engine import TemplateEngine
from src.infrastructure.rendering.pdf_renderer import PdfRenderer

# router MUST be defined before any @router.get / @router.post decorators
router = APIRouter(prefix="/export", tags=["export"])

conversation_service = ConversationService()
preview_service = PreviewService()
export_service = ExportService()
template_engine = TemplateEngine()
pdf_renderer = PdfRenderer()


class ExportRequest(BaseModel):
    session_id: Optional[str] = None
    cv_data: Optional[dict] = None
    template_style: Optional[str] = "standard"  # Options: "standard", "modern", "hybrid"


# Legacy GET endpoints for backward compatibility
@router.get("/docx/{session_id}")
def export_docx_get(session_id: str, template_style: str = "standard"):
    """
    Export CV to DOCX format (GET endpoint for backward compatibility)
    
    Query Parameters:
    - template_style: Template style to use ("standard", "modern", or "hybrid")
    """
    session = conversation_service.get_session(session_id)
    if "error" in session:
        return session

    # Use DOCX export service to preserve structured data and formatted sections
    docx_bytes = export_service.export_docx(session["cv_data"], template_style=template_style)

    return StreamingResponse(
        BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=cv_{session_id}.docx"}
    )


@router.get("/pdf/{session_id}")
def export_pdf_get(session_id: str):
    session = conversation_service.get_session(session_id)
    if "error" in session:
        return session

    # Use template engine to properly format the data for rendering
    context = template_engine.render_context(session["cv_data"])
    pdf_bytes = pdf_renderer.render(context)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=cv_{session_id}.pdf"}
    )


# New POST endpoints to match frontend expectations
@router.post("/docx")
def export_docx_post(request: ExportRequest):
    """
    Export CV to DOCX format (POST endpoint)
    
    Request Body:
    - session_id: Optional session ID to retrieve CV data
    - cv_data: Optional CV data object (used if session_id not provided)
    - template_style: Template style to use ("standard", "modern", or "hybrid")
    
    Template Styles:
    - "standard": Traditional table-based NTT DATA format (for internal use)
    - "modern": Clean 2026 format with minimal tables (for external clients)
    - "hybrid": Best of both - structured tables for skills, clean format for experience
    """
    # If cv_data is provided directly, use it
    if request.cv_data:
        cv_data = request.cv_data
        session_id = request.session_id or "export"
    else:
        # Otherwise, get from session
        if not request.session_id:
            return {"error": "Either session_id or cv_data must be provided"}
        
        session = conversation_service.get_session(request.session_id)
        if "error" in session:
            return session
        
        cv_data = session["cv_data"]
        session_id = request.session_id

    # Use DOCX export service to preserve structured data and formatted sections
    template_style = request.template_style or "standard"
    docx_bytes = export_service.export_docx(cv_data, template_style=template_style)

    return StreamingResponse(
        BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=cv_{session_id}.docx"}
    )


@router.post("/pdf")
def export_pdf_post(request: ExportRequest):
    # If cv_data is provided directly, use it
    if request.cv_data:
        cv_data = request.cv_data
        session_id = request.session_id or "export"
    else:
        # Otherwise, get from session
        if not request.session_id:
            return {"error": "Either session_id or cv_data must be provided"}
        
        session = conversation_service.get_session(request.session_id)
        if "error" in session:
            return session
        
        cv_data = session["cv_data"]
        session_id = request.session_id

    # Use template engine to properly format the data for rendering
    context = template_engine.render_context(cv_data)
    pdf_bytes = pdf_renderer.render(context)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=cv_{session_id}.pdf"}
    )
