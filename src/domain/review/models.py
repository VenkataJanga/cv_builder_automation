from pydantic import BaseModel

from src.domain.review.enums import ReviewStatus


class ReviewRecord(BaseModel):
	session_id: str
	status: ReviewStatus = ReviewStatus.PENDING
	reviewer_id: str | None = None
	comment: str | None = None
