from datetime import datetime
from typing import Any


class VersioningService:
    def __init__(self) -> None:
        self._versions: dict[str, list[dict[str, Any]]] = {}

    def create_version(self, session_id: str, cv_data: dict, version_number: int) -> dict:
        version = {
            "session_id": session_id,
            "version_number": version_number,
            "cv_data": cv_data,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._versions.setdefault(session_id, []).append(version)
        return version
