from src.core.config.loader import config_loader


def select_questions(role: str):
    question_bank = config_loader.load_question_bank()
    section_rules = config_loader.load_section_rules()

    role_sections = section_rules.get("role_sections", {}).get(role, [])
    questions = []

    for section in role_sections:
        section_obj = question_bank.get("sections", {}).get(section, {})
        section_questions = section_obj.get("questions", [])
        for q in section_questions:
            questions.append(q.get("text"))

    return questions