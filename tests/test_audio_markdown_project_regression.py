from src.infrastructure.parsers.canonical_audio_parser import CanonicalAudioParser


def test_markdown_audio_project_preserves_details():
    parser = CanonicalAudioParser()
    transcript = (
        "**Project Experience:**\n"
        "**Recommended Stock**\n"
        "**Client:** Acme Corp\n"
        "**Project Description:** Developed an AI-driven stock recommendation platform for retail traders.\n"
        "**Responsibilities:** Designed microservices, built APIs, and optimized model serving.\n"
        "**Technologies:** Python, FastAPI, Azure."
    )

    result = parser.parse(transcript)
    projects = ((result.get("experience") or {}).get("projects") or [])

    assert len(projects) == 1
    project = projects[0]
    assert project.get("projectName") == "Recommended Stock"
    assert project.get("clientName") == "Acme Corp"
    assert "stock recommendation platform" in (project.get("projectDescription") or "").lower()

    tools = project.get("toolsUsed") or []
    assert "Python" in tools
    assert "FastAPI" in tools
    assert "Azure" in tools

    responsibilities = project.get("responsibilities") or []
    assert responsibilities
    assert "microservices" in responsibilities[0].lower()


def test_placeholder_project_is_filtered_from_audio():
    parser = CanonicalAudioParser()
    transcript = "Project Experience: my first project is Recommended Stock. Responsibilities: Worked on Recommended Stock."

    result = parser.parse(transcript)
    projects = ((result.get("experience") or {}).get("projects") or [])

    assert projects == []


def test_details_phrasing_extracts_project_client_and_domain():
    parser = CanonicalAudioParser()
    transcript = (
        "Project details: Recommended Stock System. "
        "Client details: Volkswagen. "
        "Responsibilities: Built ETL workflows and dashboards. "
        "Domain details: Automotive, Banking."
    )

    result = parser.parse(transcript)
    experience = result.get("experience") or {}
    projects = experience.get("projects") or []
    domains = experience.get("domainExperience") or []

    assert len(projects) == 1
    assert projects[0].get("projectName") == "Recommended Stock System"
    assert projects[0].get("clientName") == "Volkswagen"
    assert "Built ETL workflows and dashboards." in (projects[0].get("responsibilities") or [])
    assert "Automotive" in domains
    assert "Banking" in domains
