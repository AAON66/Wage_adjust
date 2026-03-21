from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


ROLE_OPTIONS = ('admin', 'hrbp', 'manager', 'employee')


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    role: str
    must_change_password: bool = False
    employee_id: str | None = None
    employee_name: str | None = None
    employee_no: str | None = None
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default='employee', min_length=2, max_length=50)


class UserEmployeeBindingUpdate(BaseModel):
    employee_id: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AdminPasswordUpdateRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


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
    pass


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
