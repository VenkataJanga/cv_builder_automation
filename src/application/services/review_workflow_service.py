from src.domain.review.services import ReviewService
from src.domain.audit.services import AuditService


class ReviewWorkflowService:
    def __init__(self) -> None:
        self.review_service = ReviewService()
        self.audit_service = AuditService()

    def submit(self, session_id: str) -> dict:
        result = self.review_service.submit_for_review(session_id)
        self.audit_service.log_event("submit_for_review", session_id=session_id)
        return result

    def approve(self, session_id: str, reviewer_id: str) -> dict:
        result = self.review_service.approve(session_id, reviewer_id)
        self.audit_service.log_event("approve_cv", session_id=session_id, user_id=reviewer_id)
        return result

    def request_changes(self, session_id: str, reviewer_id: str, comment: str) -> dict:
        result = self.review_service.request_changes(session_id, reviewer_id, comment)
        self.audit_service.log_event("request_changes", session_id=session_id, user_id=reviewer_id, details={"comment": comment})
        return result
