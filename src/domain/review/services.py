from src.domain.review.enums import ReviewStatus
from src.domain.review.models import ReviewRecord


class ReviewService:
	def __init__(self) -> None:
		self._records: dict[str, ReviewRecord] = {}

	def submit_for_review(self, session_id: str) -> dict:
		record = self._records.get(session_id) or ReviewRecord(session_id=session_id)
		record.status = ReviewStatus.IN_REVIEW
		self._records[session_id] = record
		return record.model_dump()

	def approve(self, session_id: str, reviewer_id: str) -> dict:
		record = self._records.get(session_id) or ReviewRecord(session_id=session_id)
		record.status = ReviewStatus.APPROVED
		record.reviewer_id = reviewer_id
		self._records[session_id] = record
		return record.model_dump()

	def request_changes(self, session_id: str, reviewer_id: str, comment: str) -> dict:
		record = self._records.get(session_id) or ReviewRecord(session_id=session_id)
		record.status = ReviewStatus.CHANGES_REQUESTED
		record.reviewer_id = reviewer_id
		record.comment = comment
		self._records[session_id] = record
		return record.model_dump()
