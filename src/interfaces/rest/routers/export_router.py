from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from io import BytesIO
from pathlib import Path
import logging

from src.application.services.conversation_service import ConversationService, get_session_persistence_service
from src.application.services.transaction_logging_service import get_transaction_logging_service
from src.application.services.preview_service import PreviewService
from src.application.services.export_service import ExportService
from src.infrastructure.rendering.template_engine import TemplateEngine
from src.infrastructure.rendering.pdf_renderer import PdfRenderer
from src.core.config.settings import settings
from src.interfaces.rest.dependencies.auth_dependencies import get_current_user

# router MUST be defined before any @router.get / @router.post decorators
router = APIRouter(prefix="/export", tags=["export"], dependencies=[Depends(get_current_user)])

conversation_service = ConversationService()
preview_service = PreviewService()
export_service = ExportService()
template_engine = TemplateEngine()
pdf_renderer = PdfRenderer()
session_persistence_service = get_session_persistence_service()
transaction_logging_service = get_transaction_logging_service()
logger = logging.getLogger(__name__)


class ExportRequest(BaseModel):
    session_id: Optional[str] = None
    cv_data: Optional[dict] = None
    template_style: Optional[str] = "standard"  # Options: "standard", "modern", "hybrid"


def _log_export_event(
    operation: str,
    status: str,
    session_id: str | None = None,
    export_format: str | None = None,
    http_status: int | None = None,
    error_message: str | None = None,
    payload: dict | None = None,
) -> None:
    transaction_logging_service.log_transaction(
        module_name="export",
        operation=operation,
        status=status,
        session_id=session_id,
        source_channel="export",
        export_format=export_format,
        http_status=http_status,
        error_message=error_message,
        payload=payload,
    )


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


def _cleanup_export_source_files(session: dict, session_id: str) -> None:
    """Best-effort deletion of stored upload source files after successful export."""
    try:
        metadata = session.get("document_metadata") or {}
        saved_path = metadata.get("saved_path")
        if not saved_path:
            return

        path = Path(str(saved_path)).resolve()
        uploads_root = Path("data/storage/uploads").resolve()

        # Safety guard: only delete files under the uploads folder.
        if uploads_root not in path.parents:
            logger.warning(
                "Skipping source cleanup for session %s because path is outside uploads root: %s",
                session_id,
                path,
            )
            return

        if path.exists() and path.is_file():
            path.unlink()
            logger.info("Deleted upload source file after export for session %s: %s", session_id, path)
    except Exception as exc:
        # Export response should not fail if cleanup fails.
        logger.warning("Post-export source cleanup failed for session %s: %s", session_id, exc)


# Legacy GET endpoints for backward compatibility
@router.get("/docx/{session_id}")
def export_docx_get(session_id: str, template_style: str = "standard"):
    """
    Phase 4: Export CV to DOCX format from canonical_cv (GET endpoint for backward compatibility)
    
    Query Parameters:
    - template_style: Template style to use ("standard", "modern", or "hybrid")
    """
    try:
        session = conversation_service.get_session(session_id)
        if "error" in session:
            _log_export_event(
                operation="export_docx_get",
                status="failed",
                session_id=session_id,
                export_format="docx",
                http_status=404,
                error_message="Session not found",
            )
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
        _cleanup_export_source_files(session, session_id)
        _log_export_event(
            operation="export_docx_get",
            status="success",
            session_id=session_id,
            export_format="docx",
            http_status=200,
        )

        return StreamingResponse(
            BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=cv_{session_id}.docx"}
        )
    except HTTPException as exc:
        _log_export_event(
            operation="export_docx_get",
            status="failed",
            session_id=session_id,
            export_format="docx",
            http_status=exc.status_code,
            error_message=str(exc.detail),
        )
        raise
    except Exception as exc:
        _log_export_event(
            operation="export_docx_get",
            status="failed",
            session_id=session_id,
            export_format="docx",
            http_status=500,
            error_message=str(exc),
        )
        raise


@router.get("/pdf/{session_id}")
def export_pdf_get(session_id: str):
    """Phase 4: Export CV to PDF format from canonical_cv"""
    try:
        session = conversation_service.get_session(session_id)
        if "error" in session:
            _log_export_event(
                operation="export_pdf_get",
                status="failed",
                session_id=session_id,
                export_format="pdf",
                http_status=404,
                error_message="Session not found",
            )
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
        _cleanup_export_source_files(session, session_id)
        _log_export_event(
            operation="export_pdf_get",
            status="success",
            session_id=session_id,
            export_format="pdf",
            http_status=200,
        )

        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=cv_{session_id}.pdf"}
        )
    except HTTPException as exc:
        _log_export_event(
            operation="export_pdf_get",
            status="failed",
            session_id=session_id,
            export_format="pdf",
            http_status=exc.status_code,
            error_message=str(exc.detail),
        )
        raise
    except Exception as exc:
        _log_export_event(
            operation="export_pdf_get",
            status="failed",
            session_id=session_id,
            export_format="pdf",
            http_status=500,
            error_message=str(exc),
        )
        raise


@router.get("/doc/{session_id}")
def export_doc_get(session_id: str, template_style: str = "standard"):
    """Export CV to DOC-compatible stream backed by DOCX generation."""
    try:
        session = conversation_service.get_session(session_id)
        if "error" in session:
            _log_export_event(
                operation="export_doc_get",
                status="failed",
                session_id=session_id,
                export_format="doc",
                http_status=404,
                error_message="Session not found",
            )
            return session

        _validate_export_eligibility(session, session_id)
        canonical_cv = session.get("canonical_cv")
        if not canonical_cv:
            raise HTTPException(
                status_code=400,
                detail="No canonical CV data found for export"
            )

        docx_bytes = export_service.export_docx(canonical_cv, template_style=template_style)
        _mark_export_completed(session_id, "doc")
        _cleanup_export_source_files(session, session_id)
        _log_export_event(
            operation="export_doc_get",
            status="success",
            session_id=session_id,
            export_format="doc",
            http_status=200,
        )

        return StreamingResponse(
            BytesIO(docx_bytes),
            media_type="application/msword",
            headers={"Content-Disposition": f"attachment; filename=cv_{session_id}.doc"}
        )
    except HTTPException as exc:
        _log_export_event(
            operation="export_doc_get",
            status="failed",
            session_id=session_id,
            export_format="doc",
            http_status=exc.status_code,
            error_message=str(exc.detail),
        )
        raise
    except Exception as exc:
        _log_export_event(
            operation="export_doc_get",
            status="failed",
            session_id=session_id,
            export_format="doc",
            http_status=500,
            error_message=str(exc),
        )
        raise


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
    try:
        if not request.session_id:
            _log_export_event(
                operation="export_docx_post",
                status="failed",
                export_format="docx",
                http_status=400,
                error_message="session_id is required for export",
            )
            return {"error": "session_id is required for export"}
        
        session = conversation_service.get_session(request.session_id)
        if "error" in session:
            _log_export_event(
                operation="export_docx_post",
                status="failed",
                session_id=request.session_id,
                export_format="docx",
                http_status=404,
                error_message="Session not found",
            )
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
        _cleanup_export_source_files(session, request.session_id)
        _log_export_event(
            operation="export_docx_post",
            status="success",
            session_id=request.session_id,
            export_format="docx",
            http_status=200,
        )

        return StreamingResponse(
            BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=cv_{request.session_id}.docx"}
        )
    except HTTPException as exc:
        _log_export_event(
            operation="export_docx_post",
            status="failed",
            session_id=request.session_id,
            export_format="docx",
            http_status=exc.status_code,
            error_message=str(exc.detail),
        )
        raise
    except Exception as exc:
        _log_export_event(
            operation="export_docx_post",
            status="failed",
            session_id=request.session_id,
            export_format="docx",
            http_status=500,
            error_message=str(exc),
        )
        raise


@router.post("/doc")
def export_doc_post(request: ExportRequest):
    """Export CV to DOC-compatible stream backed by DOCX generation (POST endpoint)."""
    try:
        if not request.session_id:
            _log_export_event(
                operation="export_doc_post",
                status="failed",
                export_format="doc",
                http_status=400,
                error_message="session_id is required for export",
            )
            return {"error": "session_id is required for export"}

        session = conversation_service.get_session(request.session_id)
        if "error" in session:
            _log_export_event(
                operation="export_doc_post",
                status="failed",
                session_id=request.session_id,
                export_format="doc",
                http_status=404,
                error_message="Session not found",
            )
            return session

        _validate_export_eligibility(session, request.session_id)
        canonical_cv = session.get("canonical_cv")
        if not canonical_cv:
            raise HTTPException(
                status_code=400,
                detail="No canonical CV data found for export"
            )

        template_style = request.template_style or "standard"
        docx_bytes = export_service.export_docx(canonical_cv, template_style=template_style)
        _mark_export_completed(request.session_id, "doc")
        _cleanup_export_source_files(session, request.session_id)
        _log_export_event(
            operation="export_doc_post",
            status="success",
            session_id=request.session_id,
            export_format="doc",
            http_status=200,
        )

        return StreamingResponse(
            BytesIO(docx_bytes),
            media_type="application/msword",
            headers={"Content-Disposition": f"attachment; filename=cv_{request.session_id}.doc"}
        )
    except HTTPException as exc:
        _log_export_event(
            operation="export_doc_post",
            status="failed",
            session_id=request.session_id,
            export_format="doc",
            http_status=exc.status_code,
            error_message=str(exc.detail),
        )
        raise
    except Exception as exc:
        _log_export_event(
            operation="export_doc_post",
            status="failed",
            session_id=request.session_id,
            export_format="doc",
            http_status=500,
            error_message=str(exc),
        )
        raise


@router.post("/pdf")
def export_pdf_post(request: ExportRequest):
    """
    Phase 4: Export CV to PDF format from canonical_cv (POST endpoint)
    
    Note: cv_data parameter removed in Phase 4 - all exports must come from session canonical_cv
    """
    try:
        if not request.session_id:
            _log_export_event(
                operation="export_pdf_post",
                status="failed",
                export_format="pdf",
                http_status=400,
                error_message="session_id is required for export",
            )
            return {"error": "session_id is required for export"}
        
        session = conversation_service.get_session(request.session_id)
        if "error" in session:
            _log_export_event(
                operation="export_pdf_post",
                status="failed",
                session_id=request.session_id,
                export_format="pdf",
                http_status=404,
                error_message="Session not found",
            )
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
        _cleanup_export_source_files(session, request.session_id)
        _log_export_event(
            operation="export_pdf_post",
            status="success",
            session_id=request.session_id,
            export_format="pdf",
            http_status=200,
        )

        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=cv_{request.session_id}.pdf"}
        )
    except HTTPException as exc:
        _log_export_event(
            operation="export_pdf_post",
            status="failed",
            session_id=request.session_id,
            export_format="pdf",
            http_status=exc.status_code,
            error_message=str(exc.detail),
        )
        raise
    except Exception as exc:
        _log_export_event(
            operation="export_pdf_post",
            status="failed",
            session_id=request.session_id,
            export_format="pdf",
            http_status=500,
            error_message=str(exc),
        )
        raise
