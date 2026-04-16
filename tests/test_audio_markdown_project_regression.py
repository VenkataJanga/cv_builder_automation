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
