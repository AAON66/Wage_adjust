from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.dependencies import get_app_settings, get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.file import ContributorRead
from backend.app.services.file_service import FileService

logger = logging.getLogger(__name__)

router = APIRouter(tags=['contributors'])


class DisputeResolveRequest(BaseModel):
    resolution: str  # 'all_confirmed' | 'manager_override'
    new_pct: float | None = None


@router.post(
    '/projects/{project_id}/contributors/{contributor_id}/dispute',
    response_model=ContributorRead,
)
def dispute_contribution(
    project_id: str,
    contributor_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> ContributorRead:
    service = FileService(db, settings)

    # Resolve current user's employee_id
    employee_id = current_user.employee_id
    if employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='User is not linked to an employee record.',
        )

    try:
        updated = service.dispute_contribution(
            contributor_id=contributor_id,
            disputant_id=employee_id,
        )
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        # Status conflict (e.g., already disputed)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return ContributorRead.model_validate(updated)


@router.post(
    '/projects/{project_id}/contributors/{contributor_id}/resolve',
    response_model=ContributorRead,
)
def resolve_contribution_dispute(
    project_id: str,
    contributor_id: str,
    body: DisputeResolveRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> ContributorRead:
    service = FileService(db, settings)

    employee_id = current_user.employee_id
    if employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='User is not linked to an employee record.',
        )

    try:
        updated = service.resolve_dispute(
            contributor_id=contributor_id,
            resolution=body.resolution,
            resolver_employee_id=employee_id,
            new_pct=body.new_pct,
        )
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return ContributorRead.model_validate(updated)
