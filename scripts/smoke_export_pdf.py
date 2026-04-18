from __future__ import annotations

from pathlib import Path
from typing import Any

from src.application.services.export_service import ExportService


def _count_images_in_pdf(pdf_path: Path) -> int:
    try:
        from PyPDF2 import PdfReader
    except Exception:
        return -1

    reader = PdfReader(str(pdf_path))
    image_count = 0
    for page in reader.pages:
        resources = page.get("/Resources")
        if not resources:
            continue
        xobject = resources.get("/XObject") if hasattr(resources, "get") else None
        if not xobject:
            continue
        try:
            xobjects = xobject.get_object()
        except Exception:
            continue
        for _, obj in xobjects.items():
            try:
                candidate = obj.get_object()
                if candidate.get("/Subtype") == "/Image":
                    image_count += 1
            except Exception:
                continue
    return image_count


def _extract_text(pdf_path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except Exception:
        return ""

    reader = PdfReader(str(pdf_path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def main() -> int:
    export_service = ExportService()

    canonical_cv: dict[str, Any] = {
        "candidate": {
            "fullName": "Venkata Janga",
            "portalId": "229164",
            "email": "venkata.janga@nttdata.com",
            "phoneNumber": "9881248765",
            "currentDesignation": "System Intelligency Advisor",
            "currentOrganization": "Ntt Data",
            "totalExperienceYears": 16,
            "summary": "I have over 16 years in the IT industry specializing in development, deployment, and enterprise support.",
            "currentLocation": {
                "city": "Hyderabad",
                "country": "India",
                "fullAddress": "Hyderabad, India",
            },
        },
        "skills": {
            "primarySkills": ["Java", "Spring Boot", "microservices"],
            "secondarySkills": [
                "Python",
                "Langchain",
                "Langgraph",
                "Langsmith",
                "NumPy",
                "Pandas",
                "PySpark",
                "Databricks",
            ],
            "toolsAndPlatforms": ["Jenkins", "GitHub Actions"],
            "cloudTechnologies": ["AWS", "Azure"],
            "databases": ["MySQL"],
        },
        "experience": {
            "projects": [
                {
                    "projectName": "RECOMMENDED STOCK SYSTEM",
                    "role": "Lead Developer",
                    "durationFrom": "Jan 2022",
                    "durationTo": "till date",
                    "projectDescription": "Recommendation engine for stock analysis and decision support.",
                    "responsibilities": [
                        "Designed and developed the application architecture",
                        "Built front-end UI and back-end services",
                        "Completed CI/CD pipelines using Jenkins in Azure",
                    ],
                    "toolsUsed": ["Jenkins", "Azure", "Java"],
                },
                {
                    "projectName": "COMMON SPRINT HEALTHCARE",
                    "role": "Developer",
                    "projectDescription": "Healthcare data platform with curated reporting layers.",
                    "responsibilities": [
                        "Designed and developed end-to-end data pipelines",
                        "Ensured data quality and consistency",
                    ],
                    "toolsUsed": ["ADF", "ADLS", "Key Vault", "MySQL"],
                },
            ],
            "workHistory": [
                {
                    "organization": "Ntt Data",
                    "designation": "System Intelligency Advisor",
                    "employmentStartDate": "2009-01",
                    "employmentEndDate": "",
                    "isCurrentCompany": True,
                }
            ],
        },
        "education": [
            {
                "degree": "B.Tech",
                "institution": "JNTU",
                "yearOfPassing": "2008",
                "grade": "A",
            }
        ],
        "certifications": [{"name": "AWS Certified"}],
    }

    pdf_bytes = export_service.export_pdf(canonical_cv)

    out_dir = Path("data/storage/uploads")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "smoke_export_pdf_output.pdf"
    out_path.write_bytes(pdf_bytes)

    extracted_text = _extract_text(out_path)
    image_count = _count_images_in_pdf(out_path)

    checks = {
        "has_title": "Professional CV" in extracted_text,
        "has_name": "Venkata Janga" in extracted_text,
        "has_projects": "Project Experience" in extracted_text,
        "has_stock_project": "RECOMMENDED STOCK SYSTEM" in extracted_text,
        "has_secondary_skills": "Secondary Skills" in extracted_text,
        "has_healthcare_project": "COMMON SPRINT HEALTHCARE" in extracted_text,
        "has_logo_image_object": image_count > 0,
    }

    print(f"PDF path: {out_path}")
    print(f"PDF bytes: {len(pdf_bytes)}")
    print(f"Extracted text length: {len(extracted_text)}")
    print(f"Image objects: {image_count}")
    for key, ok in checks.items():
        print(f"{key}: {'PASS' if ok else 'FAIL'}")

    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
