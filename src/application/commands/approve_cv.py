from src.application.services.review_service import ReviewApplicationService


class ApproveCVCommand:
	def __init__(self) -> None:
		self.service = ReviewApplicationService()

	def execute(self, session_id: str, reviewer_id: str) -> dict:
		return self.service.approve(session_id, reviewer_id)
