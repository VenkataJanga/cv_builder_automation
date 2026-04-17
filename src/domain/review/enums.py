from enum import Enum


class ReviewStatus(str, Enum):
	PENDING = "pending"
	IN_REVIEW = "in_review"
	CHANGES_REQUESTED = "changes_requested"
	APPROVED = "approved"
