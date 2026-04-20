from src.application.services.export_service import ExportService
from src.infrastructure.rendering.docx_renderer import DocxRenderer
from docx import Document


def test_format_experience_section_uses_canonical_fields() -> None:
    service = ExportService()
    work_history = [
        {
            "organization": "Dell services /NTTDATA",
            "designation": "System Integration Sr. Analyst",
            "employmentStartDate": "Aug 16rd, 2016",
            "employmentEndDate": "Till Date",
            "responsibilities": ["Handled incidents", "Managed production fixes"],
        }
    ]

    text = service._format_experience_section(work_history)

    assert "System Integration Sr. Analyst | Dell services /NTTDATA" in text
    assert "Aug 16rd, 2016 - Till Date" in text
    assert "• Handled incidents" in text


def test_format_projects_section_renders_required_labeled_fields() -> None:
    service = ExportService()
    projects = [
        {
            "projectName": "Hanover Insurance",
            "clientName": "US",
            "projectDescription": "Baseline support and enhancements",
            "role": "System Integration Specialist",
            "durationFrom": "03/2021",
            "durationTo": "Till Date",
            "environment": ["Informatica 10.5.1", "Toad 12X"],
            "responsibilities": ["Production support", "Code migration"],
            "teamSize": "10",
        }
    ]

    text = service._format_projects_section(projects)

    assert "Project Name: Hanover Insurance" in text
    assert "Client: US" in text
    assert "Description: Baseline support and enhancements" in text
    assert "Duration: 03/2021 - Till Date" in text
    assert "Team Size: 10" in text
    assert "Technologies: Informatica 10.5.1, Toad 12X" in text
    assert "Roles and Responsibilities:" in text


def test_parse_work_experience_accepts_structured_list() -> None:
    renderer = DocxRenderer()
    parsed = renderer._parse_work_experience(
        [
            {
                "organization": "Accenture",
                "designation": "Sr. Software Engineer",
                "employmentStartDate": "Oct 15th ,2013",
                "employmentEndDate": "Apr 15th ,2015",
            }
        ]
    )

    assert len(parsed) == 1
    assert parsed[0]["company"] == "Accenture"
    assert parsed[0]["title"] == "Sr. Software Engineer"
    assert parsed[0]["duration"] == "Oct 15th ,2013 - Apr 15th ,2015"


def test_split_summary_lines_dedupes_repeated_experience_phrase() -> None:
    renderer = DocxRenderer()
    lines = renderer._split_summary_lines(
        "I have 10 + Years IT of experience 10.0+ years, ETL testing and production support."
    )

    assert len(lines) == 1
    normalized = lines[0].lower()
    # Keep one experience phrase while removing duplicate mention.
    assert normalized.count("years") == 1


def test_extract_project_fields_from_noisy_text_recovers_labeled_values() -> None:
    service = ExportService()
    recovered = service._extract_project_fields_from_text(
        raw_name="Hanover Insurance Client US Project Description Baseline support model",
        raw_description=(
            "Environment Informatica 10.5.1, Toad 12X Duration From (mm/yy) 03/2021 "
            "To (mm/yy) tilldate Role / Responsibility System Integration Specialist "
            "Contributions As part of baseline team Team Size 10"
        ),
    )

    assert recovered["name"] == "Hanover Insurance"
    assert recovered["client"] == "US"
    assert recovered["duration"] == "03/2021 - tilldate"
    assert "Informatica" in recovered["environment"]
    assert "System Integration Specialist" in recovered["role"]
    assert recovered["team_size"] == "10"


def test_render_project_lines_bolds_required_labels() -> None:
    renderer = DocxRenderer()
    doc = Document()
    paragraph = doc.add_paragraph()

    renderer._render_project_lines_with_bold_labels(
        paragraph,
        "Project Name: Hanover Insurance\nClient: US\nRole: System Integration Specialist\nDuration: 03/2021 - Till Date\nDescription: Baseline support",
    )

    bold_texts = [run.text for run in paragraph.runs if run.bold]
    assert "Project Name:" in bold_texts
    assert "Client:" in bold_texts
    assert "Role:" in bold_texts
    assert "Duration:" in bold_texts
    assert "Description:" in bold_texts
