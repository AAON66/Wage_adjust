from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmployeeBase(BaseModel):
    employee_no: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    department: str = Field(min_length=1, max_length=128)
    job_family: str = Field(min_length=1, max_length=128)
    job_level: str = Field(min_length=1, max_length=64)
    manager_id: str | None = None
    status: str = Field(default="active", min_length=1, max_length=32)


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bound_user_id: str | None = None
    bound_user_email: str | None = None
    created_at: datetime
    updated_at: datetime


class EmployeeListResponse(BaseModel):
    items: list[EmployeeRead]
    total: int
    page: int
    page_size: int
