"""
CV Router - Phase 4: Canonical CV Only

This router handles CV operations reading from and writing to canonical_cv exclusively.
All endpoints use CanonicalCVSchema v1.1 with no cv_data fallbacks.
"""

import copy
import logging
import os
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel, ValidationError

from src.application.commands.upload_cv import UploadCVCommand
from src.application.services.conversation_service import ConversationService
from src.application.services.document_cv_service import DocumentCVService
from src.application.services.preview_service import PreviewService
from src.application.services.schema_validation_service import SchemaValidationService
from src.domain.cv.models.canonical_cv_schema import CanonicalCVSchema
from src.domain.cv.services.merge_cv import MergeCVService
from src.core.constants import MAX_FILE_SIZE_MB
from src.core.config.settings import settings
from src.interfaces.rest.dependencies.auth_dependencies import get_current_user

router = APIRouter(prefix="/cv", tags=["cv"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)

upload_cmd = UploadCVCommand()
conversation_service = ConversationService()
merge_service = MergeCVService()
schema_validation_service = SchemaValidationService()
document_cv_service = DocumentCVService(conversation_service=conversation_service)
preview_service = PreviewService()


def _ensure_file_size_limit(file_bytes: bytes) -> None:
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB} MB.",
        )


def _merge_legacy_cv_data(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow-recursive merge that keeps legacy cv_data structure intact."""
    base = copy.deepcopy(existing or {})
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _merge_legacy_cv_data(base[key], value)
        else:
            base[key] = value
    return base


# ============================================================================
# Preview-format → Canonical conversion helpers (used by review endpoint)
# ============================================================================

def _merge_preview_into_canonical(cv_data: Dict[str, Any], existing_canonical: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge preview-format CV data (from the UI form) into the existing canonical schema.

    The existing canonical_cv (from audio / document processing) is used as the base so
    that audio-extracted details (e.g., project descriptions, responsibilities) are
    preserved.  Form fields that were filled in by the user take priority.
    """
    canonical = copy.deepcopy(existing_canonical) if existing_canonical else {}

    # Ensure required top-level sections exist
    canonical.setdefault("candidate", {})
    canonical.setdefault("skills", {})
    canonical.setdefault("experience", {})
    canonical["experience"].setdefault("projects", [])
    canonical["experience"].setdefault("workHistory", [])

    # Pull data from both 'personal_details' and 'header' (frontend may send either).
    personal_details = cv_data.get("personal_details") or {}
    header_data = cv_data.get("header") or {}
    personal = {**header_data, **personal_details}
    summary_data = cv_data.get("summary") or {}
    skills_data = cv_data.get("skills") or {}

    candidate = canonical["candidate"]

    # --- Candidate fields -------------------------------------------------------
    if personal.get("full_name"):
        candidate["fullName"] = personal["full_name"]
    if personal.get("current_title"):
        candidate["currentDesignation"] = personal["current_title"]
    if personal.get("current_organization"):
        candidate["currentOrganization"] = personal["current_organization"]
    if personal.get("email"):
        candidate["email"] = personal["email"]
    phone = personal.get("phone") or personal.get("contact_number")
    if phone:
        candidate["phoneNumber"] = phone
    portal_id = personal.get("portal_id") or personal.get("employee_id")
    if portal_id:
        candidate["portalId"] = str(portal_id)
    if personal.get("total_experience") is not None:
        try:
            candidate["totalExperienceYears"] = int(round(float(personal["total_experience"])))
        except (ValueError, TypeError):
            pass
    loc = personal.get("location")
    if loc:
        if isinstance(loc, str):
            loc_obj: Dict[str, str] = {"fullAddress": loc}
            parts = [p.strip() for p in loc.split(",")]
            if len(parts) >= 2:
                loc_obj["city"] = parts[0]
                loc_obj["country"] = parts[-1]
            candidate["currentLocation"] = loc_obj
        elif isinstance(loc, dict):
            candidate["currentLocation"] = loc
    if personal.get("linkedin"):
        canonical.setdefault("personalDetails", {})["linkedinUrl"] = personal["linkedin"]

    # --- Summary / objective ----------------------------------------------------
    if summary_data.get("professional_summary"):
        candidate["summary"] = summary_data["professional_summary"]
    if summary_data.get("target_role"):
        candidate["careerObjective"] = summary_data["target_role"]

    # --- Skills -----------------------------------------------------------------
    canonical_skills = canonical["skills"]
    if skills_data.get("primary_skills"):
        canonical_skills["primarySkills"] = skills_data["primary_skills"]
    if skills_data.get("secondary_skills"):
        canonical_skills["secondarySkills"] = skills_data["secondary_skills"]
    if skills_data.get("tools_and_platforms"):
        canonical_skills["toolsAndPlatforms"] = skills_data["tools_and_platforms"]
    if cv_data.get("ai_frameworks"):
        canonical_skills["aiToolsAndFrameworks"] = cv_data["ai_frameworks"]
    if cv_data.get("cloud_platforms"):
        canonical_skills["cloudTechnologies"] = cv_data["cloud_platforms"]
    if cv_data.get("databases"):
        canonical_skills["databases"] = cv_data["databases"]
    if cv_data.get("operating_systems"):
        canonical_skills["operatingSystems"] = cv_data["operating_systems"]
    domain_expertise = (
        skills_data.get("domain_expertise")
        or cv_data.get("domain_expertise")
        or []
    )
    if domain_expertise:
        canonical["experience"]["domainExperience"] = domain_expertise

    # --- Education --------------------------------------------------------------
    if cv_data.get("education"):
        existing_education = canonical.get("education") or []
        canonical["education"] = _convert_preview_education_to_canonical(
            cv_data["education"],
            existing_education,
        )

    # --- Projects ---------------------------------------------------------------
    if cv_data.get("project_experience"):
        existing_projects = canonical["experience"].get("projects") or []
        canonical["experience"]["projects"] = _convert_preview_projects_to_canonical(
            cv_data["project_experience"],
            existing_projects,
        )

    # --- Work history -----------------------------------------------------------
    if cv_data.get("work_experience"):
        canonical["experience"]["workHistory"] = _convert_preview_work_to_canonical(
            cv_data["work_experience"]
        )

    # --- Certifications ---------------------------------------------------------
    if cv_data.get("certifications"):
        canonical["certifications"] = _convert_preview_certifications_to_canonical(
            cv_data["certifications"]
        )

    # Ensure schema version
    if not canonical.get("schema_version") and not canonical.get("schemaVersion"):
        canonical["schema_version"] = "1.1.0"

    return canonical


def _convert_preview_education_to_canonical(
    education_list: List,
    existing_education: Optional[List[Dict]] = None,
) -> List[Dict]:
    result = []
    existing_education = existing_education or []
    for edu in education_list:
        if not isinstance(edu, dict):
            continue
        idx = len(result)
        existing_edu = (
            existing_education[idx]
            if idx < len(existing_education) and isinstance(existing_education[idx], dict)
            else {}
        )

        mapped = copy.deepcopy(existing_edu)

        degree = edu.get("degree") or edu.get("qualification") or edu.get("title")
        institution = edu.get("institution") or edu.get("college")
        university = edu.get("university")
        specialization = edu.get("specialization") or edu.get("field")

        year_of_passing = (
            edu.get("yearOfPassing")
            or edu.get("year_of_passing")
            or edu.get("year")
            or edu.get("graduation_year")
            or edu.get("year_of_completion")
        )
        grade = (
            edu.get("grade")
            or edu.get("percentage")
            or edu.get("gpa")
            or edu.get("cgpa")
            or edu.get("percentile")
        )

        if degree not in [None, ""]:
            mapped["degree"] = degree
        else:
            mapped.setdefault("degree", "")

        if institution not in [None, ""]:
            mapped["institution"] = institution
        else:
            mapped.setdefault("institution", "")

        if university not in [None, ""]:
            mapped["university"] = university
        else:
            mapped.setdefault("university", "")

        if specialization not in [None, ""]:
            mapped["specialization"] = specialization
        else:
            mapped.setdefault("specialization", "")

        if year_of_passing not in [None, ""]:
            mapped["yearOfPassing"] = str(year_of_passing)
        else:
            mapped.setdefault("yearOfPassing", str(existing_edu.get("yearOfPassing") or ""))

        if grade not in [None, ""]:
            mapped["grade"] = grade
        else:
            mapped.setdefault("grade", existing_edu.get("grade") or "")

        # Preserve extended canonical education fields when present.
        if edu.get("board") not in [None, ""]:
            mapped["board"] = edu.get("board")
        elif "board" in existing_edu:
            mapped.setdefault("board", existing_edu.get("board") or "")

        if edu.get("location") not in [None, ""]:
            mapped["location"] = edu.get("location")
        elif "location" in existing_edu:
            mapped.setdefault("location", existing_edu.get("location") or "")

        if edu.get("percentage") not in [None, ""]:
            mapped["percentage"] = edu.get("percentage")
        elif "percentage" in existing_edu:
            mapped.setdefault("percentage", existing_edu.get("percentage") or "")

        if edu.get("cgpa") not in [None, ""]:
            mapped["cgpa"] = edu.get("cgpa")
        elif "cgpa" in existing_edu:
            mapped.setdefault("cgpa", existing_edu.get("cgpa") or "")

        if edu.get("percentile") not in [None, ""]:
            mapped["percentile"] = edu.get("percentile")
        elif "percentile" in existing_edu:
            mapped.setdefault("percentile", existing_edu.get("percentile") or "")

        result.append(mapped)
    return result


def _convert_preview_projects_to_canonical(projects_list: List, existing_projects: Optional[List[Dict]] = None) -> List[Dict]:
    result = []
    existing_projects = existing_projects or []
    for proj in projects_list:
        if not isinstance(proj, dict):
            continue
        idx = len(result)
        existing_proj = existing_projects[idx] if idx < len(existing_projects) and isinstance(existing_projects[idx], dict) else {}

        role = (
            proj.get("role")
            or proj.get("designation")
            or proj.get("role_title")
            or proj.get("position")
            or existing_proj.get("role")
            or existing_proj.get("designation")
            or ""
        )
        project_name = (
            proj.get("project_name")
            or proj.get("name")
            or proj.get("title")
            or existing_proj.get("projectName")
            or existing_proj.get("name")
            or ""
        )
        client_name = (
            proj.get("client_name")
            or proj.get("client")
            or existing_proj.get("clientName")
            or existing_proj.get("client")
            or ""
        )
        duration_from = ""
        duration_to = ""
        duration_str = proj.get("duration", "")
        if duration_str and " to " in str(duration_str):
            parts = str(duration_str).split(" to ", 1)
            duration_from = parts[0].strip()
            duration_to = parts[1].strip()
        elif duration_str:
            duration_from = str(duration_str)

        result.append({
            "projectName": project_name,
            "clientName": client_name,
            "role": role,
            "durationFrom": duration_from,
            "durationTo": duration_to,
            "teamSize": proj.get("team_size") or existing_proj.get("teamSize"),
            "toolsUsed": proj.get("technologies") or proj.get("technologies_used") or existing_proj.get("toolsUsed") or [],
            "responsibilities": proj.get("responsibilities") or existing_proj.get("responsibilities") or [],
            "outcomes": proj.get("outcomes") or existing_proj.get("outcomes") or [],
            "projectDescription": proj.get("description") or proj.get("project_description") or existing_proj.get("projectDescription") or existing_proj.get("description") or "",
        })
    return result


def _convert_preview_work_to_canonical(work_list: List) -> List[Dict]:
    result = []
    for work in work_list:
        if not isinstance(work, dict):
            continue
        result.append({
            "organization": work.get("organization") or work.get("company") or work.get("company_name") or "",
            "designation": work.get("designation") or work.get("role_title") or work.get("position") or "",
            "employmentStartDate": str(work.get("start_date") or ""),
            "employmentEndDate": str(work.get("end_date") or ""),
            "isCurrentCompany": work.get("is_current", False),
            "location": work.get("location") or "",
            "responsibilities": work.get("responsibilities") or [],
            "achievements": work.get("achievements") or [],
        })
    return result


def _convert_preview_certifications_to_canonical(cert_list: List) -> List[Dict]:
    result = []
    for cert in cert_list:
        if isinstance(cert, str):
            result.append({"name": cert})
        elif isinstance(cert, dict):
            result.append({
                "name": cert.get("name") or cert.get("certification_name") or "",
                "issuingOrganization": cert.get("issuing_organization") or cert.get("organization") or "",
                "issueDate": str(cert.get("issue_date") or ""),
                "expiryDate": str(cert.get("expiry_date") or ""),
                "credentialId": cert.get("credential_id") or "",
            })
    return result


def _tokenize_field_path(path: str) -> List[Any]:
    tokens: List[Any] = []
    for part in (path or "").split("."):
        segment = part.strip()
        if not segment:
            continue
        while "[" in segment and "]" in segment:
            before, rest = segment.split("[", 1)
            if before:
                tokens.append(before)
            index_text, remainder = rest.split("]", 1)
            if index_text.isdigit():
                tokens.append(int(index_text))
            segment = remainder
        if segment:
            tokens.append(segment)
    return tokens


def _coerce_value_for_target(target_path: str, value: Any) -> Any:
    if isinstance(value, str):
        trimmed = value.strip()
    else:
        trimmed = value

    list_like_targets = (
        "skills.primarySkills",
        "skills.secondarySkills",
        "skills.toolsAndPlatforms",
        "skills.aiToolsAndFrameworks",
        "skills.cloudTechnologies",
        "skills.databases",
        "skills.operatingSystems",
        "experience.domainExperience",
    )

    if isinstance(trimmed, str) and target_path in list_like_targets:
        return [item.strip() for item in trimmed.split(",") if item.strip()]

    if isinstance(trimmed, str):
        return trimmed

    return value


def _set_value_at_path(target: Dict[str, Any], field_path: str, value: Any) -> Optional[Any]:
    tokens = _tokenize_field_path(field_path)
    if not tokens:
        return None

    current: Any = target
    for i, token in enumerate(tokens[:-1]):
        next_token = tokens[i + 1]
        if isinstance(token, int):
            if not isinstance(current, list):
                return None
            while len(current) <= token:
                current.append({} if isinstance(next_token, str) else [])
            current = current[token]
            continue

        if not isinstance(current, dict):
            return None
        if token not in current or current[token] is None:
            current[token] = [] if isinstance(next_token, int) else {}
        current = current[token]

    last = tokens[-1]
    previous = None
    if isinstance(last, int):
        if not isinstance(current, list):
            return None
        while len(current) <= last:
            current.append(None)
        previous = current[last]
        current[last] = value
        return previous

    if not isinstance(current, dict):
        return None
    previous = current.get(last)
    current[last] = value
    return previous


def _remove_unmapped_entry(canonical_cv: Dict[str, Any], source: str, key: str) -> None:
    unmapped = canonical_cv.get("unmappedData")
    if not isinstance(unmapped, dict):
        return

    source_bucket = unmapped.get(source)
    if not isinstance(source_bucket, dict):
        return

    if key in source_bucket:
        source_bucket.pop(key, None)
    if not source_bucket:
        unmapped.pop(source, None)


def _apply_others_mappings(canonical_cv: Dict[str, Any], mappings: List[Dict[str, Any]]) -> Dict[str, int]:
    allowed_roots = {
        "candidate",
        "skills",
        "experience",
        "education",
        "certifications",
        "personalDetails",
    }
    applied = 0
    skipped = 0

    if not mappings:
        return {"applied": applied, "skipped": skipped}

    canonical_cv.setdefault("audit", {})
    canonical_cv["audit"].setdefault("manualEdits", [])

    for mapping in mappings:
        target_path = str(mapping.get("target_path") or "").strip()
        raw_value = mapping.get("value")
        source = str(mapping.get("source") or "")
        key = str(mapping.get("key") or "")

        if not target_path or not raw_value:
            skipped += 1
            continue

        root = target_path.split(".", 1)[0]
        if root not in allowed_roots:
            skipped += 1
            continue

        new_value = _coerce_value_for_target(target_path, raw_value)
        previous_value = _set_value_at_path(canonical_cv, target_path, new_value)
        if previous_value is None and new_value is None:
            skipped += 1
            continue

        canonical_cv["audit"]["manualEdits"].append({
            "field": target_path,
            "previousValue": "" if previous_value is None else str(previous_value),
            "newValue": "" if new_value is None else str(new_value),
            "editedBy": "ui_review",
            "editedAt": datetime.now().isoformat(),
            "editReason": f"Mapped from Others ({source}/{key})",
        })

        if source and key:
            _remove_unmapped_entry(canonical_cv, source, key)

        applied += 1

    canonical_cv["audit"]["updatedAt"] = datetime.now().isoformat()
    return {"applied": applied, "skipped": skipped}


class EditCVRequest(BaseModel):
    """Request to edit CV data (Phase 4: Canonical only)"""
    canonical_cv: Dict[str, Any]


class ReviewCVRequest(BaseModel):
    """Request from the UI HITL review form (preview/formatter format)"""
    cv_data: Dict[str, Any]


class EditCVResponse(BaseModel):
    """Response after editing CV"""
    session_id: str
    canonical_cv: Dict[str, Any]
    validation_results: Dict[str, Any]
    review_status: str
    can_export: bool


class ValidateCVResponse(BaseModel):
    """Response from validation"""
    session_id: str
    validation_results: Dict[str, Any]
    can_save: bool
    can_export: bool


# ============================================================================
# Phase 4: Edit Operations (Canonical CV Only)
# ============================================================================

@router.get("/{session_id}")
def get_cv(session_id: str):
    """
    Get canonical CV for editing (Phase 4: Canonical-only)
    
    Returns:
        - canonical_cv: Current canonical CV data
        - validation_results: Latest validation results from session
        - review_status: Current review status
    """
    session = conversation_service.get_session(session_id)
    if "error" in session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    canonical_cv = session.get("canonical_cv")
    if not canonical_cv:
        raise HTTPException(
            status_code=400,
            detail="No canonical CV data found in session. Please complete CV creation first."
        )
    
    validation_results = session.get("validation_results", {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "can_save": True,
        "can_export": False,
        "completeness_score": 0.0
    })
    
    review_status = session.get("review_status", "pending")
    
    return {
        "schemaVersion": canonical_cv.get("schema_version", "1.1.0"),
        "candidate": canonical_cv.get("candidate", {}),
        "experience": canonical_cv.get("experience", {}),
        "skills": canonical_cv.get("skills", {}),
        "education": canonical_cv.get("education", []),
        "certifications": canonical_cv.get("certifications", []),
        "languages": canonical_cv.get("languages", []),
        "additionalSections": canonical_cv.get("additional_sections", {}),
        "metadata": canonical_cv.get("metadata", {}),
        "_validation": validation_results,
        "_review_status": review_status
    }


@router.put("/{session_id}")
def update_cv(session_id: str, request: EditCVRequest):
    """
    Update canonical CV after user edits (Phase 4: Canonical-only)
    
    This endpoint:
    1. Validates the edited canonical CV against CanonicalCVSchema
    2. Runs domain validation rules via SchemaValidationService
    3. Updates session with edited canonical_cv
    4. Stores validation results in session
    5. Tracks review status for export gating
    
    Returns:
        - canonical_cv: Updated canonical CV
        - validation_results: Validation results with can_save/can_export
        - review_status: Current review status
        - can_export: Whether CV is ready for export
    """
    # Get the existing session
    session = conversation_service.get_session(session_id)
    if "error" in session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    raw_canonical_cv = request.canonical_cv
    
    # 1. Structural validation with Pydantic CanonicalCVSchema
    try:
        canonical_cv = CanonicalCVSchema(**raw_canonical_cv)
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid canonical CV structure: {e.errors()}"
        )
    
    # 2. Domain validation via SchemaValidationService (Phase 5)
    canonical_cv_dict = canonical_cv.model_dump()
    validation_result = schema_validation_service.validate(canonical_cv_dict)
    validation_results_dict = validation_result.to_dict()
    
    # 3. Determine review status and export eligibility
    can_export = validation_result.can_export
    review_status = "completed" if can_export else "in_progress"
    
    # 4. Persist canonical CV and validation results to session
    session["canonical_cv"] = canonical_cv_dict
    session["review_status"] = review_status
    session["has_user_edits"] = True
    session["validation_results"] = validation_results_dict
    conversation_service.save_session(session_id, session)
    
    return EditCVResponse(
        session_id=session_id,
        canonical_cv=canonical_cv_dict,
        validation_results=validation_results_dict,
        review_status=review_status,
        can_export=can_export,
    )


@router.put("/review/{session_id}")
def review_cv(session_id: str, request: ReviewCVRequest):
    """
    HITL Review endpoint used by the UI's "Save & Validate" and "Save Changes" buttons.

    Accepts CV data in the preview/formatter format that the UI works with, converts
    it to canonical schema (merging with the existing audio-extracted canonical_cv so
    that verbatim project descriptions and other audio-extracted details are preserved),
    validates the result, and saves everything back to the session.

    Returns:
        - cv_data: the preview-format data that was submitted
        - canonical_cv: the updated canonical CV stored in the session
        - validation: validation results including can_export, errors/issues, warnings
        - review_status: 'completed' if validation passed, 'in_progress' otherwise
        - can_export: whether the CV is ready for export
    """
    session = conversation_service.get_session(session_id)
    if "error" in session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    cv_data = copy.deepcopy(request.cv_data)
    others_mappings = cv_data.pop("_others_mappings", [])
    existing_canonical = session.get("canonical_cv") or {}

    logger.info(f"HITL review: session={session_id}, incoming keys={list(cv_data.keys())}")

    # Convert/merge preview format → canonical (preserve audio-extracted fields)
    canonical_cv = _merge_preview_into_canonical(cv_data, existing_canonical)

    # Apply manual mappings from the UI Others panel
    mapping_result = _apply_others_mappings(canonical_cv, others_mappings if isinstance(others_mappings, list) else [])
    if mapping_result["applied"]:
        logger.info(
            "Applied %s Others mappings (skipped=%s) for session=%s",
            mapping_result["applied"],
            mapping_result["skipped"],
            session_id,
        )

    # Validate
    validation_result = schema_validation_service.validate(canonical_cv)
    validation_dict = validation_result.to_dict()
    # Add 'issues' as an alias for 'errors' so the UI's displayValidationFeedback works
    validation_dict["issues"] = validation_dict.get("errors", [])

    can_export = validation_result.can_export
    review_status = "completed" if can_export else "in_progress"

    # Persist to session
    session["canonical_cv"] = canonical_cv
    session["review_status"] = review_status
    session["has_user_edits"] = True
    session["validation_results"] = validation_dict
    session["validation"] = validation_dict
    conversation_service.save_session(session_id, session)

    logger.info(
        f"HITL review saved: can_export={can_export}, review_status={review_status}, "
        f"errors={len(validation_dict.get('errors', []))}"
    )

    return {
        "session_id": session_id,
        "cv_data": cv_data,
        "canonical_cv": canonical_cv,
        "validation": validation_dict,
        "review_status": review_status,
        "can_export": can_export,
    }


@router.post("/{session_id}/validate")
def validate_cv(session_id: str):
    """
    Validate canonical CV using SchemaValidationService (Phase 4)
    
    This endpoint:
    1. Reads canonical_cv from session
    2. Validates using SchemaValidationService
    3. Stores validation results in session
    4. Returns validation results with can_save/can_export flags
    
    Returns:
        - validation_results: Full validation results
        - can_save: Whether CV can be saved (partial data allowed)
        - can_export: Whether CV can be exported (all mandatory fields present)
    """
    # Get the existing session
    session = conversation_service.get_session(session_id)
    if "error" in session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    canonical_cv = session.get("canonical_cv")
    if not canonical_cv:
        raise HTTPException(
            status_code=400,
            detail="No canonical CV data found in session. Please complete CV creation first."
        )
    
    # Validate using SchemaValidationService (Phase 5)
    validation_result = schema_validation_service.validate(canonical_cv)
    validation_results_dict = validation_result.to_dict()
    
    # Store validation results in session
    session["validation_results"] = validation_results_dict
    conversation_service.save_session(session_id, session)
    
    # Phase 5: Export gating based on validation results
    can_save = True  # Always allow saving partial data
    can_export = validation_result.can_export
    
    return ValidateCVResponse(
        session_id=session_id,
        validation_results=validation_results_dict,
        can_save=can_save,
        can_export=can_export,
    )


# ============================================================================
# Phase 4: Document Upload with Canonical Schema Integration
# ============================================================================

@router.post("/upload/document")
async def upload_cv_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    """
    Phase 4: Upload CV document with canonical schema integration
    
    This endpoint:
    1. Parses the document to canonical schema v1.1 (deterministic extraction)
    2. Optionally applies LLM-assisted extraction if ENABLE_LLM_EXTRACTION is true (Phase 5)
    3. Merges with existing canonical CV (preserving manual edits)
    4. Validates the merged result using SchemaValidationService
    5. Updates the session with canonical CV and validation results
    
    LLM extraction (Phase 5):
    - Can be enabled via ENABLE_LLM_EXTRACTION config flag
    - Applies optional normalization and structured field extraction
    - Deterministic parsing results take priority
    - Falls back gracefully if LLM unavailable
    
    Returns:
        - canonical_cv: The merged canonical CV data
        - validation_results: Validation results with can_save/can_export flags
        - merge_stats: Statistics about the merge operation
    """
    try:
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file content
        file_content = await file.read()
        _ensure_file_size_limit(file_content)
        
        # Process the document upload (includes validation)
        result = document_cv_service.upload_cv_document(
            session_id=session_id,
            file_content=file_content,
            filename=file.filename
        )

        preview_data = preview_service.build_preview_from_canonical(result["canonical_cv"])
        return {
            "session_id": session_id,
            "canonical_cv": result["canonical_cv"],
            "cv_data": preview_data,
            "preview": preview_data,
            "validation_results": result["validation"],
            "merge_stats": result["merge_stats"],
            "message": "Document uploaded and processed successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Document upload failed: {str(e)}"
        )


@router.get("/status/{session_id}")
def get_cv_status(session_id: str):
    """
    Phase 4: Get CV status including validation and completeness
    
    Returns:
        - has_cv: Whether the session has canonical CV data
        - can_save: Whether the CV can be saved (partial data allowed)
        - can_export: Whether the CV can be exported (all mandatory fields present)
        - completeness_score: Score from 0.0 to 1.0
        - validation_results: Full validation results
    """
    try:
        status = document_cv_service.get_cv_status(session_id)
        return status
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get CV status: {str(e)}"
        )


# ============================================================================
# Additional Phase 4 Endpoints (Test Compatibility)
# ============================================================================

@router.get("/edit/{session_id}")
def get_cv_for_edit_explicit(session_id: str):
    """Alias for get_cv - explicit /edit/ path for test compatibility"""
    return get_cv(session_id)


@router.post("/save")
def save_cv_changes(request: dict):
    """Save CV changes - simplified endpoint for test compatibility"""
    session_id = request.get("session_id")
    canonical_cv = request.get("canonical_cv")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    if not canonical_cv:
        raise HTTPException(status_code=400, detail="canonical_cv is required")
    
    # Get the existing session
    session = conversation_service.get_session(session_id)
    if "error" in session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Update canonical_cv directly (preserve structure exactly as provided)
    session["canonical_cv"] = canonical_cv
    session["has_user_edits"] = True
    conversation_service.save_session(session_id, session)
    
    return {
        "status": "success",
        "message": "CV changes saved successfully",
        "session_id": session_id,
        "canonical_cv": canonical_cv
    }


@router.post("/validate")
def validate_cv_direct(request: dict):
    """Validate CV - direct endpoint for test compatibility"""
    session_id = request.get("session_id")
    canonical_cv = request.get("canonical_cv")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    if not canonical_cv:
        raise HTTPException(status_code=400, detail="canonical_cv is required")
    
    # Update session with provided canonical_cv if different
    session = conversation_service.get_session(session_id)
    if "error" not in session:
        session["canonical_cv"] = canonical_cv
        conversation_service.save_session(session_id, session)
    
    # Use the validate_cv endpoint logic
    result = validate_cv(session_id)
    
    return {
        "status": "success",
        "session_id": session_id,
        "validation_results": result.validation_results,
        "can_save": result.can_save,
        "can_export": result.can_export
    }


# ============================================================================
# Legacy Endpoints (Deprecated in Phase 4)
# ============================================================================

@router.post("/upload")
async def upload_cv(
    file: UploadFile = File(...),
    session_id: str = Form(None),
):
    """
    DEPRECATED: Legacy upload endpoint (use /upload/document instead)
    
    This endpoint is maintained for backward compatibility only.
    New integrations should use /upload/document which works with canonical schema.
    """
    if not file:
        return {"error": "No file provided"}

    os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
    save_path = os.path.join(
        settings.LOCAL_STORAGE_PATH,
        f"{uuid4()}_{file.filename}"
    )

    content = await file.read()
    _ensure_file_size_limit(content)
    with open(save_path, "wb") as f:
        f.write(content)

    parsed_data = upload_cmd.execute(save_path)

    if session_id:
        session = conversation_service.get_session(session_id)
        if "error" in session:
            return session

        merged = _merge_legacy_cv_data(session.get("cv_data", {}), parsed_data)
        session["cv_data"] = merged

        return {
            "session_id": session_id,
            "parsed_data": parsed_data,
            "cv_data": merged,
            "message": "DEPRECATED: Please use /upload/document endpoint"
        }

    new_session = conversation_service.start_session()
    session = conversation_service.get_session(new_session["session_id"])
    merged = _merge_legacy_cv_data(session.get("cv_data", {}), parsed_data)
    session["cv_data"] = merged

    return {
        "session_id": session["session_id"],
        "parsed_data": parsed_data,
        "cv_data": merged,
        "question": new_session.get("question"),
        "message": "DEPRECATED: Please use /upload/document endpoint"
    }


@router.post("/import")
async def import_cv(
    file: UploadFile = File(...),
    session_id: str = Form(None),
):
    """
    DEPRECATED: Import a CV file - alias for legacy upload endpoint
    Use /upload/document instead
    """
    return await upload_cv(file, session_id)
