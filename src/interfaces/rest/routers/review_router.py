from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.application.services.review_workflow_service import ReviewWorkflowService
from src.core.security.roles import Role
from src.interfaces.rest.dependencies.auth_dependencies import require_role


router = APIRouter(prefix="/review", tags=["review"])
service = ReviewWorkflowService()


class SubmitReviewRequest(BaseModel):
	session_id: str


class ApproveReviewRequest(BaseModel):
	session_id: str
	reviewer_id: str


class RequestChangesRequest(BaseModel):
	session_id: str
	reviewer_id: str
	comment: str


@router.post("/submit", dependencies=[Depends(require_role(Role.ADMIN, Role.CV_EDITOR, Role.DELIVERY_MANAGER))])
def submit_for_review(req: SubmitReviewRequest) -> dict:
	return service.submit(req.session_id)


@router.post("/approve", dependencies=[Depends(require_role(Role.ADMIN, Role.REVIEWER, Role.DELIVERY_MANAGER))])
def approve_review(req: ApproveReviewRequest) -> dict:
	return service.approve(req.session_id, req.reviewer_id)


@router.post("/request-changes", dependencies=[Depends(require_role(Role.ADMIN, Role.REVIEWER, Role.DELIVERY_MANAGER))])
def request_changes(req: RequestChangesRequest) -> dict:
	return service.request_changes(req.session_id, req.reviewer_id, req.comment)
