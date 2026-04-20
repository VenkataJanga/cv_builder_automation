from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from src.application.services.transaction_logging_service import get_transaction_logging_service
from src.core.security.roles import Role
from src.interfaces.rest.dependencies.auth_dependencies import require_role

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(require_role(Role.ADMIN, Role.DELIVERY_MANAGER))],
)

transaction_logging_service = get_transaction_logging_service()


@router.get("/events")
def list_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    module_name: str | None = None,
    operation: str | None = None,
    status: str | None = None,
    session_id: str | None = None,
    actor_username: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> dict:
    items = transaction_logging_service.list_transactions(
        limit=limit,
        module_name=module_name,
        operation=operation,
        status=status,
        session_id=session_id,
        actor_username=actor_username,
        created_from=created_from,
        created_to=created_to,
    )

    return {
        "count": len(items),
        "items": items,
    }
