from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.app.schemas.department import DepartmentRead


def _validate_password_complexity(value: str) -> str:
    """Enforce: >=8 chars, 1+ uppercase, 1+ lowercase, 1+ digit or symbol."""
    if not re.search(r'[A-Z]', value):
        raise ValueError('Password must contain at least one uppercase letter.')
    if not re.search(r'[a-z]', value):
        raise ValueError('Password must contain at least one lowercase letter.')
    if not re.search(r'[0-9!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?`~]', value):
        raise ValueError('Password must contain at least one digit or special character.')
    return value


ROLE_OPTIONS = ('admin', 'hrbp', 'manager', 'employee')


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    role: str
    id_card_no: Optional[str] = None
    must_change_password: bool = False
    employee_id: Optional[str] = None
    employee_name: Optional[str] = None
    employee_no: Optional[str] = None
    departments: list[DepartmentRead] = []
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default='employee', min_length=2, max_length=50)
    id_card_no: Optional[str] = Field(default=None, max_length=32)

    @field_validator('password')
    @classmethod
    def password_complexity(cls, value: str) -> str:
        return _validate_password_complexity(value)


class UserEmployeeBindingUpdate(BaseModel):
    employee_id: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def new_password_complexity(cls, value: str) -> str:
        return _validate_password_complexity(value)


class AdminPasswordUpdateRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def new_password_complexity(cls, value: str) -> str:
        return _validate_password_complexity(value)


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'


class AuthResponse(BaseModel):
    user: UserRead
    tokens: TokenPair


class UserAdminCreate(UserCreate):
    department_ids: list[str] = Field(default_factory=list, max_length=50)


class UserDepartmentBindingUpdate(BaseModel):
    department_ids: list[str] = Field(default_factory=list, max_length=50)


class UserListResponse(BaseModel):
    items: list[UserRead]
    total: int
    page: int
    page_size: int


class BulkUserFailure(BaseModel):
    identifier: str
    message: str


class BulkUserCreateRequest(BaseModel):
    items: list[UserAdminCreate] = Field(min_length=1, max_length=100)


class BulkUserCreateResponse(BaseModel):
    created: list[UserRead]
    failed: list[BulkUserFailure]
    total_requested: int


class BulkUserDeleteRequest(BaseModel):
    user_ids: list[str] = Field(min_length=1, max_length=100)


class BulkUserDeleteResponse(BaseModel):
    deleted_user_ids: list[str]
    failed: list[BulkUserFailure]
    total_requested: int


class AdminBindRequest(BaseModel):
    employee_id: str


class SelfBindRequest(BaseModel):
    id_card_no: str = Field(min_length=1, max_length=32)


class SelfBindPreview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    employee_no: str
    name: str
    department: str
