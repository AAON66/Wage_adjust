from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db, require_roles
from backend.app.models.user import User
from backend.app.schemas.audit import AuditLogListResponse, AuditLogRead
from backend.app.services.audit_service import AuditService

router = APIRouter(prefix='/audit', tags=['audit'])


@router.get('/', response_model=AuditLogListResponse)
def list_audit_logs(
    target_type: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    operator_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    from_dt: datetime | None = Query(default=None),
    to_dt: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles('admin')),
) -> AuditLogListResponse:
    items, total = AuditService(db).query(
        target_type=target_type,
        target_id=target_id,
        operator_id=operator_id,
        action=action,
        from_dt=from_dt,
        to_dt=to_dt,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(
        items=[AuditLogRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
