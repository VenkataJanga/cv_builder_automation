from src.questionnaire.question_selector import select_initial_questions, select_questions


def test_initial_questions_are_localized_for_german() -> None:
    questions = select_initial_questions(locale="de")
    assert questions
    assert questions[0] == "Wie lautet Ihr vollstandiger Name?"


def test_role_questions_fallback_to_source_text_when_translation_missing() -> None:
    questions = select_questions("technical_manager", locale="de")
    assert "Was sind Ihre wichtigsten Kernkompetenzen?" in questions
    # q_tm_001 is intentionally not in the locale catalog, so it should fall back.
    assert "What are your primary technical domains?" in questions


def test_unsupported_locale_falls_back_to_default() -> None:
    questions = select_initial_questions(locale="fr")
    assert questions
    assert questions[0] == "What is your full name?"
