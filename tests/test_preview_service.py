import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai.agents.cv_formatting_agent import CVFormattingAgent
from src.application.services.preview_service import PreviewService
from src.application.services.export_service import ExportService
from src.questionnaire.mappers.answer_to_cv_field_mapper import AnswerToCVFieldMapper


def test_cv_formatting_agent_handles_professional_summary_object():
    cv_data = {
        "personal_details": {
            "full_name": "Jane Smith",
            "current_title": "Solution Architect",
            "location": "Bengaluru",
            "email": "jane.smith@example.com",
        },
        "summary": {
            "professional_summary": "Experienced architect leading cloud modernization programs.",
        },
        "education": [
            {
                "qualification": "Bachelor of Technology in Computer Science",
                "college": "ABC Institute",
                "university": "XYZ University",
                "year_of_passing": "2015",
            }
        ],
    }

    formatter = CVFormattingAgent()
    formatted = formatter.format_cv(cv_data)

    assert formatted["summary"] == "Experienced architect leading cloud modernization programs."
    assert formatted["header"]["full_name"] == "Jane Smith"
    assert formatted["education"] == cv_data["education"]


def test_cv_formatting_agent_handles_education_list_of_strings():
    cv_data = {
        "personal_details": {
            "full_name": "Raj Kumar",
            "current_title": "Tech Lead",
            "location": "Pune",
            "email": "raj.kumar@example.com",
        },
        "summary": "Lead engineer with strong backend and cloud experience.",
        "education": [
            "Master of Science in Computer Science, ABC University, 2018",
            "Bachelor of Engineering in Information Technology, XYZ University, 2015",
        ],
    }

    formatter = CVFormattingAgent()
    formatted = formatter.format_cv(cv_data)

    assert formatted["summary"] == "Lead engineer with strong backend and cloud experience."
    assert formatted["education"] == cv_data["education"]


def test_answer_to_cv_field_mapper_parses_newline_skill_lists():
    mapper = AnswerToCVFieldMapper()
    skills = mapper._parse_list("My primary skill is Java\nSpring Boot\nmicroservices.")
    assert skills == ["Java", "Spring Boot", "microservices"]


def test_answer_to_cv_field_mapper_parses_education_narrative():
    mapper = AnswerToCVFieldMapper()
    education = mapper._parse_education(
        "I completed a master in computer science applications. The branch is computers. My year of passing is 2007. The name of the college is ITM. University name is Kakatiya University. "
        "My second educational qualification is Bachelor of Science. Branch is computers. My college name is Sri Chaitanya Degree College. University is Kakatiya University. I got 59 percentage. "
        "Then I have completed my 12th standard. Branch is MPC. College is Sri Chaitanya Junior College. University is Board of Intermediate. I got 59 percentage. "
        "I have completed my 10th standard. My school name is ZPPSI School. University is School of Secondary. Year of passing is 2000."
    )
    assert len(education) == 4
    assert education[0]["qualification"].lower().startswith("master")
    assert education[0]["college"] == "ITM"
    assert education[0]["university"] == "Kakatiya University"
    assert education[0]["year"] == "2007"
    assert education[1]["qualification"].lower().startswith("bachelor")
    assert education[2]["qualification"].lower().startswith("12th")
    assert education[3]["qualification"].lower().startswith("10th")


def test_export_service_uses_preview_normalization_for_docx():
    raw_cv_data = {
        "personal_details": {
            "full_name": "Venkata janga",
            "current_title": "Tech Lead",
            "employee_id": "229164",
            "email": "venkata.janga@nttdata.com",
            "location": "Pune",
        },
        "summary": {
            "professional_summary": "I have over past 16 years in the IT industry specializing in the development and deployment and operational support for enterprise grade applications. My expertise span across Java, Python, PySpark, Databricks, AWS, Azure cloud services with strong focus on building scale web based and enterprise applications."
        },
        "skills": {
            "primary_skills": ["Java", "Spring Boot", "microservices"],
            "secondary_skills": ["Python", "Langchain", "Langgraph", "Langsmith", "NumPy", "Pandas", "PySpark", "Databricks"],
            "tools_and_platforms": ["Linux", "Windows", "MySQL", "Postgres", "DB2", "Oracle"]
        },
        "education": [
            {
                "qualification": "Master of Computer Applications",
                "college": "ITM",
                "university": "Kakatiya University",
                "year": "2007",
                "percentage": "70%"
            }
        ],
    }

    export_service = ExportService()
    normalized = export_service._normalize_cv_data(raw_cv_data)
    assert normalized["header"]["full_name"] == "Venkata janga"
    assert normalized["summary"].startswith("I have over past 16 years")
    assert isinstance(normalized["skills"], list)
    assert normalized["education"][0]["qualification"] == "Master of Computer Applications"


def test_cv_formatting_agent_handles_summary_list_with_nested_object():
    cv_data = {
        "personal_details": {
            "full_name": "Ravi Singh",
            "current_title": "Engineering Manager",
            "location": "Bangalore",
            "email": "ravi.singh@example.com",
        },
        "summary": [
            {"professional_summary": "Experienced leader in cloud and data engineering."}
        ],
        "education": [
            {
                "qualification": "Master of Computer Applications",
                "college": "ITM",
                "university": "Kakatiya University",
                "year_of_passing": "2007",
            }
        ],
    }

    formatter = CVFormattingAgent()
    formatted = formatter.format_cv(cv_data)

    assert formatted["summary"] == "Experienced leader in cloud and data engineering."
    assert formatted["header"]["full_name"] == "Ravi Singh"
    assert formatted["education"] == cv_data["education"]


def test_preview_service_builds_preview_from_cv_data():
    cv_data = {
        "personal_details": {
            "full_name": "Maya Rao",
            "current_title": "Data Engineer",
            "location": "Hyderabad",
            "email": "maya.rao@example.com",
        },
        "summary": {
            "professional_summary": "Experienced data engineer specializing in ETL and cloud data platforms.",
        },
        "education": [
            "Master of Data Science, ABC University, 2020",
        ],
    }

    preview_service = PreviewService()
    preview = preview_service.build_preview(cv_data)

    assert preview["summary"] == "Experienced data engineer specializing in ETL and cloud data platforms."
    assert preview["header"]["full_name"] == "Maya Rao"
    assert preview["education"] == cv_data["education"]
