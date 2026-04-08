from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CycleDepartmentBudgetInput(BaseModel):
    department_id: str = Field(min_length=1)
    budget_amount: Decimal = Field(default=Decimal('0.00'), ge=0)


class CycleDepartmentBudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    department_id: str
    department_name: str
    budget_amount: Decimal
    created_at: datetime
    updated_at: datetime


class CycleBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    review_period: str = Field(min_length=1, max_length=128)
    budget_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    status: str = Field(default="draft", min_length=1, max_length=32)
    department_budgets: List[CycleDepartmentBudgetInput] = Field(default_factory=list)


class CycleCreate(CycleBase):
    pass


class CycleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    review_period: Optional[str] = Field(default=None, min_length=1, max_length=128)
    budget_amount: Optional[Decimal] = Field(default=None, ge=0)
    status: Optional[str] = Field(default=None, min_length=1, max_length=32)
    department_budgets: Optional[List[CycleDepartmentBudgetInput]] = None


class CycleRead(CycleBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    department_budgets: List[CycleDepartmentBudgetRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CycleListResponse(BaseModel):
    items: List[CycleRead]
    total: int
