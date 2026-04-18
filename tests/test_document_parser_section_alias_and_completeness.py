from __future__ import annotations

from src.infrastructure.parsers.canonical_document_parser import CanonicalDocumentParser


def test_document_parser_handles_aliases_designation_projects_and_multi_education() -> None:
    parser = CanonicalDocumentParser()

    sample_text = """
Name: Lokesh Kumar
Email: lokesh.kumar@example.com
Phone: +91-9876543210
Current Role: Software Development Senior Specialist

Experience Summary:
Experienced software engineer with enterprise integration expertise.

Technical Skills:
Primary Skills: Java, Spring Boot, Microservices
Databases: MySQL, PostgreSQL
Development Tools: Jenkins, Git

Project Details:
Project: Revenue Optimizer | Role: Lead Developer | Duration: Jan 2022 - Present
Key Responsibilities: Designed microservices; Led CI/CD rollout; Coordinated production support.
Technologies: Java, Spring Boot, Kubernetes

Project Name: Claims Automation Platform
Role: Software Development Analyst
Duration: Mar 2020 - Dec 2021
Responsibilities: Built API orchestration layer; Improved data validation.
Environment: Python, FastAPI, Azure

Qualification Details:
1 B.Tech Computer Science 2012 ABC Institute of Technology State University 8.1
2 M.Tech Software Engineering 2014 XYZ Institute of Technology National University 8.7

Training Attended / Certifications Done:
1. PMP
""".strip()

    canonical = parser.parse_document_to_canonical(
        file_path="dummy.pdf",
        extracted_text=sample_text,
        file_metadata={"filename": "lokesh_resume.pdf"},
    )

    candidate = canonical.get("candidate", {})
    assert candidate.get("currentDesignation") == "Software Development Senior Specialist"

    summary = str(candidate.get("summary") or "").lower()
    assert "experienced software engineer" in summary

    skills = canonical.get("skills", {})
    primary_skills = [str(item).lower() for item in skills.get("primarySkills", [])]
    assert "java" in primary_skills

    projects = (canonical.get("experience") or {}).get("projects") or []
    assert len(projects) >= 2
    project_names = [str(project.get("projectName") or "") for project in projects]
    assert any("Revenue Optimizer" in name for name in project_names)
    assert any("Claims Automation Platform" in name for name in project_names)

    education = canonical.get("education") or []
    assert len(education) >= 2

    degrees = [str(edu.get("degree") or "") for edu in education]
    assert any("B.Tech" in degree or "BTech" in degree for degree in degrees)
    assert any("M.Tech" in degree or "MTech" in degree for degree in degrees)


def test_document_parser_handles_lokesh_style_numbered_projects_and_labeled_education() -> None:
    parser = CanonicalDocumentParser()

    sample_text = """
Lokesh Kumar
Systems Integration Senior Analyst
Location: Bangalore
Professional Summary
I have an experience of 5 years and 9 months as Software Developer in finance domain.
I have good technical knowledge on Java, Spring Boot, REST API development, Microservices, Kafka, MYSQL, JPA, Hibernate, OpenShift, Git & Jenkins.
Technical Skills
Highlights of User Responsibilities
Work Experience
Organization : NTT DATA Services
Position : Systems Integration Senior Analyst
Tenure : July 2022 - Present

1) Citi Corporate Card (for NTT DATA Services) (Tenure October-2022 to March-2023)
Corporate Card project deals with the aspects of Corporate Customers.
Primary Responsibilities:
I was part of the team that created API to manage Corporate Customer.
I have worked on creating common service layer to call all the external APIs.

2) Wells Fargo Online Payment Services (for NTT DATA) (Tenure March 2023 to January-2025)
OPS is a payment service platform under Wells Fargo.
Primary Responsibilities:
I have worked on development activities related to IFI / Wires transfers.
I have worked on upgrading multiple JARS.

3) Citi iOS Container Services (for NTT DATA Services) (Tenure January-2025 till Current Date)
The iOS Container Services is a set of modular microservices.
Primary Responsibilities:
I have worked for WhatsNew Service and Navigation Service.
I have created multiple CMP for creating and updating Feature Flags.

Education
Institution: Gopalan College of Engineering and Management
Specialization: Bachelor of Engineering (Computer Science Engineering)
Institution: Kendriya Vidyalaya ASC Centre
Specialization: PCMC (CBSE 12th Standard)
Institution: Kendriya Vidyalaya ASC Centre
Specialization: CBSE 10th Standard
""".strip()

    canonical = parser.parse_document_to_canonical(
        file_path="dummy.docx",
        extracted_text=sample_text,
        file_metadata={"filename": "lokesh_style_resume.docx"},
    )

    candidate = canonical.get("candidate", {})
    assert candidate.get("currentDesignation") == "Systems Integration Senior Analyst"

    skills = canonical.get("skills", {})
    technical = [str(item).lower() for item in skills.get("technicalSkills", [])]
    assert "java" in technical
    assert "spring boot" in technical

    projects = (canonical.get("experience") or {}).get("projects") or []
    assert len(projects) >= 3
    project_names = [str(project.get("projectName") or "") for project in projects]
    assert any("Citi Corporate Card" in name for name in project_names)
    assert any("Wells Fargo Online Payment Services" in name for name in project_names)
    assert any("Citi iOS Container Services" in name for name in project_names)

    education = canonical.get("education") or []
    assert len(education) >= 3

    edu_degrees = [str(edu.get("degree") or "") for edu in education]
    assert any("Bachelor of Engineering" in degree for degree in edu_degrees)
    assert any("12th Standard" in degree for degree in edu_degrees)
    assert any("10th Standard" in degree for degree in edu_degrees)
