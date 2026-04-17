from fastapi import APIRouter, Depends, HTTPException

from src.application.services.template_service import TemplateService
from src.interfaces.rest.dependencies.auth_dependencies import get_current_user


router = APIRouter(
	prefix="/templates",
	tags=["templates"],
	dependencies=[Depends(get_current_user)],
)
service = TemplateService()


@router.get("")
def list_templates() -> dict:
	return {"templates": service.list_templates()}


@router.get("/{template_id}")
def get_template(template_id: str) -> dict:
	try:
		return service.get_template(template_id)
	except KeyError as exc:
		raise HTTPException(status_code=404, detail=str(exc))
