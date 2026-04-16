from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from io import BytesIO

from src.application.services.conversation_service import ConversationService, get_session_persistence_service
from src.application.services.preview_service import PreviewService
from src.application.services.export_service import ExportService
from src.infrastructure.rendering.template_engine import TemplateEngine
from src.infrastructure.rendering.pdf_renderer import PdfRenderer
from src.core.config.settings import settings

# router MUST be defined before any @router.get / @router.post decorators
router = APIRouter(prefix="/export", tags=["export"])

conversation_service = ConversationService()
preview_service = PreviewService()
export_service = ExportService()
template_engine = TemplateEngine()
pdf_renderer = PdfRenderer()
session_persistence_service = get_session_persistence_service()


class ExportRequest(BaseModel):
    session_id: Optional[str] = None
    cv_data: Optional[dict] = None
    template_style: Optional[str] = "standard"  # Options: "standard", "modern", "hybrid"


def _validate_export_eligibility(session: dict, session_id: str):
    """
    Phase 4: Validate that a CV session is eligible for export (canonical schema).
    
    Checks:
    1. canonical_cv exists
    2. validation_results exists and can_export is True
    3. (Optional) Review status is 'completed' if REQUIRE_REVIEW_BEFORE_EXPORT is enabled
    
    Raises HTTPException if not eligible.
    """
    # Check canonical_cv exists
    canonical_cv = session.get("canonical_cv")
    if not canonical_cv:
        raise HTTPException(
            status_code=400,
            detail="No canonical CV data found. Please complete CV creation before exporting."
        )
    
    # Check validation status
    validation_results = session.get("validation_results", {})
    can_export = validation_results.get("can_export", False)
    
    if not can_export:
        errors = validation_results.get("errors", [])
        error_details = ", ".join(errors[:3]) if errors else "Critical validation issues remain"
        raise HTTPException(
            status_code=400,
            detail=f"Cannot export: {error_details}. Please review and fix the CV before exporting."
        )
    
    # Check review status (if configured to require review)
    require_review = getattr(settings, "REQUIRE_REVIEW_BEFORE_EXPORT", False)
    if require_review:
        review_status = session.get("review_status", "pending")
        if review_status != "completed":
            raise HTTPException(
                status_code=400,
                detail="Please review and confirm the CV before exporting. Use the review endpoint to validate changes."
            )


def _mark_export_completed(session_id: str, export_format: str) -> None:
    """Best-effort exported marker update for persistence lifecycle."""
    try:
        session_persistence_service.mark_export_completed(session_id, export_format)
    except Exception:
        # Export response should not fail if lifecycle marker update fails.
        pass


# Legacy GET endpoints for backward compatibility
@router.get("/docx/{session_id}")
def export_docx_get(session_id: str, template_style: str = "standard"):
    """
    Phase 4: Export CV to DOCX format from canonical_cv (GET endpoint for backward compatibility)
    
    Query Parameters:
    - template_style: Template style to use ("standard", "modern", or "hybrid")
    """
    session = conversation_service.get_session(session_id)
    if "error" in session:
        return session

    # Validate export eligibility (human-in-the-loop gate)
    _validate_export_eligibility(session, session_id)

    # Phase 4: Read from canonical_cv only
    canonical_cv = session.get("canonical_cv")
    if not canonical_cv:
        raise HTTPException(
            status_code=400,
            detail="No canonical CV data found for export"
        )

    # Use DOCX export service to preserve structured data and formatted sections
    docx_bytes = export_service.export_docx(canonical_cv, template_style=template_style)
    _mark_export_completed(session_id, "docx")

    return StreamingResponse(
        BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=cv_{session_id}.docx"}
    )


@router.get("/pdf/{session_id}")
def export_pdf_get(session_id: str):
    """Phase 4: Export CV to PDF format from canonical_cv"""
    session = conversation_service.get_session(session_id)
    if "error" in session:
        return session

    # Validate export eligibility (human-in-the-loop gate)
    _validate_export_eligibility(session, session_id)

    # Phase 4: Read from canonical_cv only
    canonical_cv = session.get("canonical_cv")
    if not canonical_cv:
        raise HTTPException(
            status_code=400,
            detail="No canonical CV data found for export"
        )

    # Use export service to handle PDF generation
    pdf_bytes = export_service.export_pdf(canonical_cv)
    _mark_export_completed(session_id, "pdf")

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=cv_{session_id}.pdf"}
    )


# New POST endpoints to match frontend expectations
@router.post("/docx")
def export_docx_post(request: ExportRequest):
    """
    Phase 4: Export CV to DOCX format from canonical_cv (POST endpoint)
    
    Request Body:
    - session_id: Required session ID to retrieve CV data
    - template_style: Template style to use ("standard", "modern", or "hybrid")
    
    Template Styles:
    - "standard": Traditional table-based NTT DATA format (for internal use)
    - "modern": Clean 2026 format with minimal tables (for external clients)
    - "hybrid": Best of both - structured tables for skills, clean format for experience
    
    Note: cv_data parameter removed in Phase 4 - all exports must come from session canonical_cv
    """
    if not request.session_id:
        return {"error": "session_id is required for export"}
    
    session = conversation_service.get_session(request.session_id)
    if "error" in session:
        return session
    
    # Validate export eligibility (human-in-the-loop gate)
    _validate_export_eligibility(session, request.session_id)
    
    # Phase 4: Read from canonical_cv only
    canonical_cv = session.get("canonical_cv")
    if not canonical_cv:
        raise HTTPException(
            status_code=400,
            detail="No canonical CV data found for export"
        )

    # Use DOCX export service to preserve structured data and formatted sections
    template_style = request.template_style or "standard"
    docx_bytes = export_service.export_docx(canonical_cv, template_style=template_style)
    _mark_export_completed(request.session_id, "docx")

    return StreamingResponse(
        BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=cv_{request.session_id}.docx"}
    )


@router.post("/pdf")
def export_pdf_post(request: ExportRequest):
    """
    Phase 4: Export CV to PDF format from canonical_cv (POST endpoint)
    
    Note: cv_data parameter removed in Phase 4 - all exports must come from session canonical_cv
    """
    if not request.session_id:
        return {"error": "session_id is required for export"}
    
    session = conversation_service.get_session(request.session_id)
    if "error" in session:
        return session
    
    # Validate export eligibility (human-in-the-loop gate)
    _validate_export_eligibility(session, request.session_id)
    
    # Phase 4: Read from canonical_cv only
    canonical_cv = session.get("canonical_cv")
    if not canonical_cv:
        raise HTTPException(
            status_code=400,
            detail="No canonical CV data found for export"
        )

    # Use export service to handle PDF generation
    pdf_bytes = export_service.export_pdf(canonical_cv)
    _mark_export_completed(request.session_id, "pdf")

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=cv_{request.session_id}.pdf"}
    )
