from src.domain.versioning.services import VersioningService


class ApplicationVersioningService:
    def __init__(self) -> None:
        self.service = VersioningService()

    def snapshot(self, session_id: str, cv_data: dict, version_number: int) -> dict:
        return self.service.create_version(session_id, cv_data, version_number)
