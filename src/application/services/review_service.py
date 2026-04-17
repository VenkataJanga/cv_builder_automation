from src.application.services.review_workflow_service import ReviewWorkflowService


class ReviewApplicationService:
	def __init__(self) -> None:
		self.workflow = ReviewWorkflowService()

	def submit(self, session_id: str) -> dict:
		return self.workflow.submit(session_id)

	def approve(self, session_id: str, reviewer_id: str) -> dict:
		return self.workflow.approve(session_id, reviewer_id)

	def request_changes(self, session_id: str, reviewer_id: str, comment: str) -> dict:
		return self.workflow.request_changes(session_id, reviewer_id, comment)
