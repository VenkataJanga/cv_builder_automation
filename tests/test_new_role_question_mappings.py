from src.questionnaire.question_selector import select_questions
from src.questionnaire.role_resolver import resolve_role


def test_new_titles_resolve_to_expected_roles() -> None:
    assert resolve_role("Tech Lead") == "tech_lead"
    assert resolve_role("Software Development Senior Specialist") == "software_development_senior_specialist"
    assert resolve_role("Software Development Analyst") == "software_development_analyst"
    assert resolve_role("SDM") == "software_development_manager"
    assert resolve_role("Software Development Manager") == "software_development_manager"
    assert resolve_role("Business Intelligence Advisor") == "business_intelligence_advisor"


def test_each_new_role_returns_role_specific_questions() -> None:
    assert "How many engineers have you led, and what were their roles?" in select_questions("tech_lead", locale="en")
    assert "What is your primary software specialization area?" in select_questions("software_development_senior_specialist", locale="en")
    assert "How do you analyze business requirements before implementation?" in select_questions("software_development_analyst", locale="en")
    assert "What is the size and structure of the teams you manage?" in select_questions(resolve_role("SDM"), locale="en")
    assert "What is the size and structure of the teams you manage?" in select_questions("software_development_manager", locale="en")
    assert "Which BI tools and platforms do you use most often?" in select_questions("business_intelligence_advisor", locale="en")


def test_new_role_questions_are_localized_in_german() -> None:
    assert "Wie viele Ingenieurinnen und Ingenieure haben Sie gefuhrt und in welchen Rollen?" in select_questions("tech_lead", locale="de")
    assert "Was ist Ihr primares Spezialisierungsgebiet in der Softwareentwicklung?" in select_questions("software_development_senior_specialist", locale="de")
    assert "Wie analysieren Sie fachliche Anforderungen vor der Umsetzung?" in select_questions("software_development_analyst", locale="de")
    assert "Wie gross sind die Teams, die Sie fuhren, und wie sind sie strukturiert?" in select_questions("software_development_manager", locale="de")
    assert "Welche BI-Tools und Plattformen nutzen Sie am haufigsten?" in select_questions("business_intelligence_advisor", locale="de")
