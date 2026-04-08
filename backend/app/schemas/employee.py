from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EmployeeBase(BaseModel):
    employee_no: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    id_card_no: Optional[str] = Field(default=None, max_length=32)
    department: str = Field(min_length=1, max_length=128)
    sub_department: Optional[str] = Field(default=None, max_length=128)
    job_family: str = Field(min_length=1, max_length=128)
    job_level: str = Field(min_length=1, max_length=64)
    manager_id: Optional[str] = None
    status: str = Field(default="active", min_length=1, max_length=32)


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    employee_no: Optional[str] = Field(default=None, min_length=1, max_length=64)
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    id_card_no: Optional[str] = Field(default=None, max_length=32)
    department: Optional[str] = Field(default=None, min_length=1, max_length=128)
    sub_department: Optional[str] = Field(default=None, max_length=128)
    job_family: Optional[str] = Field(default=None, min_length=1, max_length=128)
    job_level: Optional[str] = Field(default=None, min_length=1, max_length=64)
    manager_id: Optional[str] = None
    status: Optional[str] = Field(default=None, min_length=1, max_length=32)


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bound_user_id: Optional[str] = None
    bound_user_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class EmployeeListResponse(BaseModel):
    items: List[EmployeeRead]
    total: int
    page: int
    page_size: int
