from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db, require_roles
from backend.app.schemas.department import DepartmentCreate, DepartmentListResponse, DepartmentRead, DepartmentUpdate
from backend.app.services.department_service import DepartmentService

router = APIRouter(prefix='/departments', tags=['departments'])


@router.get('', response_model=DepartmentListResponse)
def list_departments(
    db: Session = Depends(get_db),
    _: object = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> DepartmentListResponse:
    service = DepartmentService(db)
    items, total = service.list_departments()
    return DepartmentListResponse(items=[DepartmentRead.model_validate(item) for item in items], total=total)


@router.post('', response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles('admin')),
) -> DepartmentRead:
    service = DepartmentService(db)
    try:
        department = service.create_department(name=payload.name, description=payload.description, status=payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DepartmentRead.model_validate(department)


@router.patch('/{department_id}', response_model=DepartmentRead)
def update_department(
    department_id: str,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles('admin')),
) -> DepartmentRead:
    service = DepartmentService(db)
    try:
        department = service.update_department(
            department_id,
            name=payload.name,
            description=payload.description,
            status=payload.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if department is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found.')
    return DepartmentRead.model_validate(department)


@router.delete('/{department_id}', response_model=dict[str, str])
def delete_department(
    department_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles('admin')),
) -> dict[str, str]:
    service = DepartmentService(db)
    deleted_department_id = service.delete_department(department_id)
    if deleted_department_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found.')
    return {'deleted_department_id': deleted_department_id}
