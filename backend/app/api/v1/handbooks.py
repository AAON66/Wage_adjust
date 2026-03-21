from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.dependencies import get_app_settings, get_db, require_roles
from backend.app.models.user import User
from backend.app.schemas.handbook import EmployeeHandbookDeleteResponse, EmployeeHandbookListResponse, EmployeeHandbookRead
from backend.app.services.employee_handbook_service import EmployeeHandbookService

router = APIRouter(prefix='/handbooks', tags=['handbooks'])


@router.get('', response_model=EmployeeHandbookListResponse)
def list_handbooks(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> EmployeeHandbookListResponse:
    service = EmployeeHandbookService(db, settings)
    items = service.list_handbooks()
    return EmployeeHandbookListResponse(items=[EmployeeHandbookRead.model_validate(item) for item in items], total=len(items))


@router.post('', response_model=EmployeeHandbookRead, status_code=status.HTTP_201_CREATED)
def upload_handbook(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> EmployeeHandbookRead:
    service = EmployeeHandbookService(db, settings)
    try:
        handbook = service.upload_handbook(file, operator=current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return EmployeeHandbookRead.model_validate(handbook)


@router.delete('/{handbook_id}', response_model=EmployeeHandbookDeleteResponse)
def delete_handbook(
    handbook_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> EmployeeHandbookDeleteResponse:
    service = EmployeeHandbookService(db, settings)
    try:
        deleted_handbook_id = service.delete_handbook(handbook_id)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if message == 'Employee handbook not found.' else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    return EmployeeHandbookDeleteResponse(deleted_handbook_id=deleted_handbook_id)
