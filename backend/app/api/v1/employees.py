from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db, get_current_user, require_roles
from backend.app.models.user import User
from backend.app.schemas.employee import EmployeeCreate, EmployeeListResponse, EmployeeRead, EmployeeUpdate
from backend.app.services.access_scope_service import AccessScopeService
from backend.app.services.employee_service import EmployeeService

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles("admin", "hrbp", "manager")),
) -> EmployeeRead:
    service = EmployeeService(db)
    try:
        employee = service.create_employee(payload)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_409_CONFLICT if message == 'Employee number already exists.' else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    return EmployeeRead.model_validate(employee)


@router.get("", response_model=EmployeeListResponse)
def list_employees(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    department: str | None = Query(default=None),
    job_family: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployeeListResponse:
    service = EmployeeService(db)
    items, total = service.get_employees(
        current_user=current_user,
        page=page,
        page_size=page_size,
        department=department,
        job_family=job_family,
        status=status_filter,
        keyword=keyword,
    )
    return EmployeeListResponse(
        items=[EmployeeRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmployeeRead:
    try:
        employee = AccessScopeService(db).ensure_employee_access(current_user, employee_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")
    return EmployeeRead.model_validate(employee)


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: str,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "hrbp", "manager")),
) -> EmployeeRead:
    try:
        accessible_employee = AccessScopeService(db).ensure_employee_access(current_user, employee_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if accessible_employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")

    service = EmployeeService(db)
    try:
        employee = service.update_employee(employee_id, payload)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_409_CONFLICT if message == 'Employee number already exists.' else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")
    return EmployeeRead.model_validate(employee)
