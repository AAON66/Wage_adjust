from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db, require_roles
from backend.app.models.user import User
from backend.app.schemas.user import (
    AdminPasswordUpdateRequest,
    BulkUserCreateRequest,
    BulkUserCreateResponse,
    BulkUserDeleteRequest,
    BulkUserDeleteResponse,
    BulkUserFailure,
    UserAdminCreate,
    UserDepartmentBindingUpdate,
    UserEmployeeBindingUpdate,
    UserListResponse,
    UserRead,
)
from backend.app.services.user_admin_service import UserAdminService

router = APIRouter(prefix='/users', tags=['users'])


@router.get('', response_model=UserListResponse)
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    role: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> UserListResponse:
    service = UserAdminService(db)
    try:
        items, total = service.list_users(operator=current_user, page=page, page_size=page_size, role=role, keyword=keyword)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserListResponse(
        items=[UserRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post('', response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserAdminCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> UserRead:
    service = UserAdminService(db)
    try:
        user = service.create_user(payload, operator=current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserRead.model_validate(user)


@router.post('/bulk-create', response_model=BulkUserCreateResponse)
def bulk_create_users(
    payload: BulkUserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> BulkUserCreateResponse:
    service = UserAdminService(db)
    created, failed = service.bulk_create_users(payload.items, operator=current_user)
    return BulkUserCreateResponse(
        created=[UserRead.model_validate(item) for item in created],
        failed=[BulkUserFailure(identifier=item.identifier, message=item.message) for item in failed],
        total_requested=len(payload.items),
    )


@router.patch('/{user_id}/binding', response_model=UserRead)
def update_user_employee_binding(
    user_id: str,
    payload: UserEmployeeBindingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> UserRead:
    service = UserAdminService(db)
    try:
        user = service.bind_employee(user_id, employee_id=payload.employee_id, operator=current_user)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if message in {'User not found.', 'Employee not found.'} else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    return UserRead.model_validate(user)


@router.patch('/{user_id}/password', response_model=dict[str, str])
def update_user_password(
    user_id: str,
    payload: AdminPasswordUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> dict[str, str]:
    service = UserAdminService(db)
    try:
        updated_user_id = service.update_user_password(user_id, new_password=payload.new_password, operator=current_user)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if message == 'User not found.' else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    return {'updated_user_id': updated_user_id, 'message': 'Password updated successfully.'}


@router.patch('/{user_id}/departments', response_model=UserRead)
def update_user_departments(
    user_id: str,
    payload: UserDepartmentBindingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> UserRead:
    service = UserAdminService(db)
    try:
        user = service.update_user_departments(user_id, department_ids=payload.department_ids, operator=current_user)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if message in {'User not found.', 'One or more departments were not found.'} else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    return UserRead.model_validate(user)


@router.delete('/{user_id}', response_model=dict[str, str])
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> dict[str, str]:
    service = UserAdminService(db)
    try:
        deleted_user_id = service.delete_user(user_id, operator=current_user)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if message == 'User not found.' else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    return {'deleted_user_id': deleted_user_id}


@router.post('/bulk-delete', response_model=BulkUserDeleteResponse)
def bulk_delete_users(
    payload: BulkUserDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> BulkUserDeleteResponse:
    service = UserAdminService(db)
    deleted_user_ids, failed = service.bulk_delete_users(payload.user_ids, operator=current_user)
    return BulkUserDeleteResponse(
        deleted_user_ids=deleted_user_ids,
        failed=[BulkUserFailure(identifier=item.identifier, message=item.message) for item in failed],
        total_requested=len(payload.user_ids),
    )
