"""Example usage for the session persistence service (development mode)."""

from src.domain.session import (
    InMemorySessionRepository,
    SessionService,
    SessionSourceType,
)


def main() -> None:
    repo = InMemorySessionRepository()
    service = SessionService(repository=repo, default_ttl_hours=24, exported_retention_hours=6)

    # 1. Start session
    session = service.initialize_session()
    session_id = session.session_id

    # 2. Merge from bot conversation
    service.merge_source_update(
        session_id=session_id,
        incoming_canonical_cv={
            "candidate": {
                "fullName": "Jane Doe",
                "currentDesignation": "Senior Backend Engineer",
                "email": "jane.doe@example.com",
                "phoneNumber": "+1-555-0100",
                "currentLocation": {"city": "Seattle", "country": "USA"},
                "summary": "Backend engineer with cloud-native microservices experience.",
            },
            "skills": {
                "primarySkills": ["Python", "FastAPI", "PostgreSQL"],
                "toolsAndPlatforms": ["Docker", "Kubernetes"],
            },
        },
        source_type=SessionSourceType.BOT_CONVERSATION,
        operation="bot_update",
    )

    # 3. Merge from manual edit
    service.merge_source_update(
        session_id=session_id,
        incoming_canonical_cv={
            "experience": {
                "projects": [
                    {
                        "projectName": "Claims Processing Platform",
                        "role": "Lead Engineer",
                        "projectDescription": "Designed event-driven claims workflows.",
                    }
                ]
            }
        },
        source_type=SessionSourceType.MANUAL_EDIT,
        operation="manual_save",
    )

    # 4. Preview/read latest
    payload = service.get_preview_payload(session_id)
    print("Session:", payload["session_id"])
    print("Status:", payload["status"])
    print("Candidate:", payload["canonical_cv"].get("candidate", {}).get("fullName"))

    # 5. Mark export completion
    service.mark_export_completed(session_id, export_format="docx")

    # 6. Cleanup when due (typically scheduled)
    removed_count = service.cleanup_expired_sessions()
    print("Cleanup removed:", removed_count)


if __name__ == "__main__":
    main()
