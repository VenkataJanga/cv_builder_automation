import json
from pathlib import Path

from src.application.services.document_cv_service import DocumentCVService
from src.application.services.preview_service import PreviewService


def _pick_latest_lokesh_file(upload_dir: Path) -> Path:
    candidates = list(upload_dir.glob("*Lokesh Kumar Resume.docx"))
    if not candidates:
        raise FileNotFoundError("No Lokesh Kumar Resume DOCX file found in uploads directory")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def main() -> None:
    upload_dir = Path("data/storage/uploads")
    file_path = _pick_latest_lokesh_file(upload_dir)

    session_id = "lokesh_real_parse_check"
    session_store = {
        session_id: {
            "session_id": session_id,
            "canonical_cv": None,
            "validation_results": None,
        }
    }

    service = DocumentCVService(session_store=session_store)
    result = service.process_document_upload(
        session_id=session_id,
        file_path=str(file_path),
        file_metadata={
            "filename": file_path.name,
            "extension": file_path.suffix.lower(),
            "size_bytes": file_path.stat().st_size,
            "saved_path": str(file_path),
        },
    )

    canonical = result.get("canonical_cv", {}) or {}
    preview = PreviewService().build_preview_from_canonical(canonical)

    preview_header_title = None
    preview_summary_present = False
    preview_project_count = 0
    preview_education_count = 0

    if isinstance(preview, dict):
        header = preview.get("header")
        if isinstance(header, dict):
            preview_header_title = header.get("current_title")

        summary = preview.get("summary")
        if isinstance(summary, dict):
            preview_summary_present = bool((summary.get("professional_summary") or "").strip())
        elif isinstance(summary, str):
            preview_summary_present = bool(summary.strip())

        projects_preview = preview.get("project_experience")
        if isinstance(projects_preview, list):
            preview_project_count = len(projects_preview)

        education_preview = preview.get("education")
        if isinstance(education_preview, list):
            preview_education_count = len(education_preview)

    candidate = canonical.get("candidate", {}) or {}
    skills = canonical.get("skills", {}) or {}
    experience = canonical.get("experience", {}) or {}
    education = canonical.get("education", []) or []
    projects = experience.get("projects", []) or []

    report = {
        "source_file": str(file_path),
        "candidate": {
            "fullName": candidate.get("fullName"),
            "currentDesignation": candidate.get("currentDesignation"),
            "currentOrganization": candidate.get("currentOrganization"),
            "totalExperienceYears": candidate.get("totalExperienceYears"),
            "summary_present": bool((candidate.get("summary") or "").strip()),
        },
        "skills": {
            "primarySkills_count": len(skills.get("primarySkills") or []),
            "technicalSkills_count": len(skills.get("technicalSkills") or []),
            "technicalSkills_sample": (skills.get("technicalSkills") or [])[:10],
        },
        "projects": {
            "count": len(projects),
            "sample": [
                {
                    "projectName": p.get("projectName"),
                    "role": p.get("role"),
                    "duration": f"{p.get('durationFrom', '')} -> {p.get('durationTo', '')}".strip(" ->"),
                    "responsibilities_count": len(p.get("responsibilities") or []),
                    "tools_count": len(p.get("toolsUsed") or []),
                }
                for p in projects[:5]
            ],
        },
        "education": {
            "count": len(education),
            "entries": [
                {
                    "degree": e.get("degree"),
                    "institution": e.get("institution"),
                    "yearOfPassing": e.get("yearOfPassing"),
                }
                for e in education
            ],
        },
        "preview": {
            "header_current_title": preview_header_title,
            "summary_present": preview_summary_present,
            "project_experience_count": preview_project_count,
            "education_count": preview_education_count,
        },
        "validation": result.get("validation", {}),
    }

    print(json.dumps(report, indent=2, ensure_ascii=True, default=str))


if __name__ == "__main__":
    main()
