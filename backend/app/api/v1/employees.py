from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db, get_current_user, require_roles
from backend.app.schemas.employee import EmployeeCreate, EmployeeListResponse, EmployeeRead
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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return EmployeeRead.model_validate(employee)


@router.get("", response_model=EmployeeListResponse)
def list_employees(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    department: str | None = Query(default=None),
    job_family: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> EmployeeListResponse:
    service = EmployeeService(db)
    items, total = service.get_employees(
        page=page,
        page_size=page_size,
        department=department,
        job_family=job_family,
        status=status_filter,
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
    _: object = Depends(get_current_user),
) -> EmployeeRead:
    service = EmployeeService(db)
    employee = service.get_employee(employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")
    return EmployeeRead.model_validate(employee)
