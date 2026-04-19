from src.application.services.validation_service import ValidationService
from src.questionnaire.followup_engine import FollowupEngine


def test_followup_engine_returns_german_text() -> None:
    engine = FollowupEngine()
    msg = engine.generate_followup(
        question="Wie wurden Sie Ihr berufliches Profil in 2-3 Zeilen beschreiben?",
        answer="Kurz",
        analysis={"is_short": True},
        locale="de",
    )
    assert msg
    assert "Zusammenfassung" in msg or "erweitern" in msg


def test_validation_messages_are_localized_to_german() -> None:
    service = ValidationService()
    result = service.validate({}, operation="save", locale="de")
    warnings = result.get("warnings", [])
    assert warnings
    assert any("Pflichtfelder" in w or "vollstandig" in w for w in warnings)
